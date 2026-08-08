#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import os
from pathlib import Path
import re
import subprocess
import sys


HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)
POLICY_NAMES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
VALID_MODES = ("jungle", "garden", "zen")
PACKET_HEADINGS = (
    "Mode",
    "Seed scopes",
    "Policy sources",
    "Exact user constraints",
    "Environment capabilities",
    "Verification commands",
    "Required report",
)
REPORT_FIELDS = (
    "Effective mode",
    "Policy sources read",
    "Seed scopes",
    "Reference expansion",
    "Edits",
    "Preserved and protected comments",
    "Ambiguities",
    "Verification commands and results",
    "Packet fields or policy clauses that changed a verdict",
)
FENCE_OPEN_RE = re.compile(r"^(?:\d+\. )?(`{4,})(?:text|console)$")


class PacketError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class SeedScope:
    old_path: str | None
    new_path: str | None
    old_start: int | None
    old_count: int | None
    new_start: int | None
    new_count: int | None


def _scope_key(scope):
    ranges = (
        scope.old_start,
        scope.old_count,
        scope.new_start,
        scope.new_count,
    )
    return (
        scope.old_path is None,
        scope.old_path or "",
        scope.new_path is None,
        scope.new_path or "",
        *(-1 if value is None else value for value in ranges),
    )


def _sorted_unique_scopes(scopes):
    return sorted(set(scopes), key=_scope_key)


def _append_filesystem_character(target, character):
    try:
        target.extend(os.fsencode(character))
    except UnicodeEncodeError as error:
        raise PacketError("undecodable quoted Git path") from error


def _decode_quoted_git_path(value):
    if not value.startswith('"'):
        if '"' in value:
            raise PacketError("undecodable quoted Git path")
        return value
    if len(value) < 2 or not value.endswith('"'):
        raise PacketError("undecodable quoted Git path")

    decoded = bytearray()
    index = 1
    end = len(value) - 1
    byte_escapes = {
        '"': ord('"'),
        "\\": ord("\\"),
        "/": ord("/"),
        "b": 0x08,
        "f": 0x0C,
        "n": 0x0A,
        "r": 0x0D,
        "t": 0x09,
    }
    while index < end:
        character = value[index]
        if character != "\\":
            if ord(character) < 0x20:
                raise PacketError("undecodable quoted Git path")
            _append_filesystem_character(decoded, character)
            index += 1
            continue

        index += 1
        if index >= end:
            raise PacketError("undecodable quoted Git path")
        escape = value[index]
        if escape in byte_escapes:
            decoded.append(byte_escapes[escape])
            index += 1
            continue
        if escape == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise PacketError("undecodable quoted Git path")
            codepoint = int(digits, 16)
            index += 5
            if 0xD800 <= codepoint <= 0xDBFF:
                if value[index : index + 2] != "\\u":
                    raise PacketError("undecodable quoted Git path")
                low_digits = value[index + 2 : index + 6]
                if len(low_digits) != 4 or any(
                    digit not in "0123456789abcdefABCDEF" for digit in low_digits
                ):
                    raise PacketError("undecodable quoted Git path")
                low = int(low_digits, 16)
                if not 0xDC00 <= low <= 0xDFFF:
                    raise PacketError("undecodable quoted Git path")
                codepoint = 0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)
                index += 6
            elif 0xDC00 <= codepoint <= 0xDFFF:
                raise PacketError("undecodable quoted Git path")
            _append_filesystem_character(decoded, chr(codepoint))
            continue
        if escape in "01234567":
            digits = value[index : index + 3]
            if len(digits) != 3 or any(digit not in "01234567" for digit in digits):
                raise PacketError("undecodable quoted Git path")
            decoded.append(int(digits, 8))
            index += 3
            continue
        raise PacketError("undecodable quoted Git path")
    return os.fsdecode(bytes(decoded))


def _split_diff_header(value):
    fields = []
    index = 0
    while index < len(value):
        while index < len(value) and value[index] == " ":
            index += 1
        if index == len(value):
            break
        start = index
        if value[index] == '"':
            index += 1
            while index < len(value):
                if value[index] == "\\":
                    index += 2
                elif value[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise PacketError("undecodable quoted Git path")
            if index < len(value) and value[index] != " ":
                raise PacketError("invalid diff --git header")
        else:
            while index < len(value) and value[index] != " ":
                index += 1
        fields.append(_decode_quoted_git_path(value[start:index]))
    if len(fields) != 2:
        raise PacketError("invalid diff --git header")
    return fields


def _git_path(value, prefix):
    if value == "/dev/null":
        return None
    if not value.startswith(prefix):
        raise PacketError("invalid Git path")
    relative = value[len(prefix) :]
    path = Path(relative)
    if (
        not relative
        or path.is_absolute()
        or ".." in path.parts
        or path == Path(".")
        or "\0" in relative
    ):
        raise PacketError("unsafe Git path")
    return path.as_posix()


def _marker_path(line, prefix):
    value = line[4:].split("\t", 1)[0]
    return _git_path(_decode_quoted_git_path(value), prefix)


def _rename_path(line, prefix):
    value = _decode_quoted_git_path(line.split(" ", 2)[2])
    return _git_path(prefix + value, prefix)


def _parse_hunk_numbers(match):
    try:
        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) is not None else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) is not None else 1
    except ValueError as error:
        raise PacketError("invalid numeric hunk range") from error
    if (old_start == 0 and old_count != 0) or (new_start == 0 and new_count != 0):
        raise PacketError("invalid zero-start hunk range")
    if old_count == 0 and new_count == 0:
        raise PacketError("hunk contains no lines")
    return old_start, old_count, new_start, new_count


def parse_git_diff(text: str) -> list[SeedScope]:
    scopes = []
    header_old = None
    header_new = None
    marker_old = None
    marker_new = None
    rename_old = None
    rename_new = None
    have_header = False
    have_old_marker = False
    have_new_marker = False
    had_hunk = False
    expected_old = None
    expected_new = None
    seen_old = 0
    seen_new = 0

    def finish_hunk():
        nonlocal expected_old, expected_new, seen_old, seen_new
        if expected_old is not None and (
            seen_old != expected_old or seen_new != expected_new
        ):
            raise PacketError("hunk body does not match declared ranges")
        expected_old = None
        expected_new = None
        seen_old = 0
        seen_new = 0

    def finish_file():
        finish_hunk()
        if not have_header:
            return
        if (rename_old is None) != (rename_new is None):
            raise PacketError("incomplete rename header")
        if rename_old is not None:
            if rename_old != header_old or rename_new != header_new:
                raise PacketError("rename path does not match diff header")
            if not had_hunk:
                scopes.append(
                    SeedScope(rename_old, rename_new, None, None, None, None)
                )

    for line in text.splitlines():
        if line.startswith("diff --git "):
            finish_file()
            fields = _split_diff_header(line[len("diff --git ") :])
            header_old = _git_path(fields[0], "a/")
            header_new = _git_path(fields[1], "b/")
            marker_old = None
            marker_new = None
            rename_old = None
            rename_new = None
            have_header = True
            have_old_marker = False
            have_new_marker = False
            had_hunk = False
            continue

        if line.startswith("@@"):
            finish_hunk()
            match = HUNK_RE.fullmatch(line)
            if match is None:
                raise PacketError("malformed hunk header")
            if not (have_header and have_old_marker and have_new_marker):
                raise PacketError("hunk without complete file header")
            if marker_old is None and marker_new is None:
                raise PacketError("hunk without a file path")
            if marker_old is not None and marker_old != header_old:
                raise PacketError("old Git path does not match diff header")
            if marker_new is not None and marker_new != header_new:
                raise PacketError("new Git path does not match diff header")
            old_start, old_count, new_start, new_count = _parse_hunk_numbers(match)
            scopes.append(
                SeedScope(
                    marker_old,
                    marker_new,
                    old_start,
                    old_count,
                    new_start,
                    new_count,
                )
            )
            expected_old = old_count
            expected_new = new_count
            had_hunk = True
            continue

        if expected_old is not None:
            if line == "\\ No newline at end of file":
                continue
            if not line:
                raise PacketError("malformed hunk body")
            marker = line[0]
            if marker == " ":
                seen_old += 1
                seen_new += 1
            elif marker == "-":
                seen_old += 1
            elif marker == "+":
                seen_new += 1
            else:
                raise PacketError("malformed hunk body")
            if seen_old > expected_old or seen_new > expected_new:
                raise PacketError("hunk body exceeds declared ranges")
            continue

        if line.startswith("--- "):
            if not have_header or have_old_marker or have_new_marker:
                raise PacketError("file marker without diff header")
            marker_old = _marker_path(line, "a/")
            have_old_marker = True
        elif line.startswith("+++ "):
            if not have_header or not have_old_marker or have_new_marker:
                raise PacketError("file marker without diff header")
            marker_new = _marker_path(line, "b/")
            have_new_marker = True
        elif line.startswith("rename from "):
            if not have_header or rename_old is not None or had_hunk:
                raise PacketError("invalid rename header")
            rename_old = _rename_path(line, "a/")
        elif line.startswith("rename to "):
            if not have_header or rename_new is not None or had_hunk:
                raise PacketError("invalid rename header")
            rename_new = _rename_path(line, "b/")

    finish_file()
    return _sorted_unique_scopes(scopes)


def _relative_path(value, description):
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or path == Path(".")
        or "\0" in value
    ):
        raise PacketError(f"unsafe {description}")
    return path


def _resolved_root(root):
    try:
        resolved = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise PacketError("repository root is unavailable") from error
    if not resolved.is_dir():
        raise PacketError("repository root is not a directory")
    return resolved


def _has_symlink_component(root, relative):
    current = root
    try:
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return True
    except OSError as error:
        raise PacketError("filesystem traversal failed") from error
    return False


def _materialized_file(root, value, description):
    relative = _relative_path(value, description)
    candidate = root / relative
    if _has_symlink_component(root, relative):
        raise PacketError(f"{description} is not a materialized regular file")
    try:
        candidate.resolve(strict=True).relative_to(root)
        is_file = candidate.is_file()
    except (OSError, RuntimeError, ValueError) as error:
        raise PacketError(f"{description} is not a materialized regular file") from error
    if not is_file:
        raise PacketError(f"{description} is not a materialized regular file")
    return candidate


def _directory_files(directory):
    try:
        children = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError as error:
        raise PacketError("explicit directory traversal failed") from error
    files = []
    for child in children:
        try:
            if child.is_symlink():
                continue
            if child.is_file():
                files.append(child)
            elif child.is_dir():
                files.extend(_directory_files(child))
            else:
                raise PacketError("explicit directory contains a special file")
        except OSError as error:
            raise PacketError("explicit directory traversal failed") from error
    return files


def resolve_explicit_paths(root: Path, values) -> list[SeedScope]:
    root = _resolved_root(root)
    files = []
    for value in values:
        relative = _relative_path(value, "explicit target")
        target = root / relative
        if _has_symlink_component(root, relative):
            raise PacketError("explicit target is not materialized")
        try:
            target.resolve(strict=True).relative_to(root)
            is_file = target.is_file()
            is_dir = target.is_dir()
        except (OSError, RuntimeError, ValueError) as error:
            raise PacketError("explicit target is missing or outside the repository") from error
        if is_file:
            files.append(target)
        elif is_dir:
            files.extend(_directory_files(target))
        else:
            raise PacketError("explicit target is not a regular file or directory")
    return _sorted_unique_scopes(
        SeedScope(None, path.relative_to(root).as_posix(), None, None, None, None)
        for path in files
    )


def _is_materialized_regular_file(root, path):
    try:
        relative = path.relative_to(root)
        return not _has_symlink_component(root, relative) and path.is_file()
    except OSError as error:
        raise PacketError("filesystem traversal failed") from error
    except ValueError:
        return False


def discover_policy_sources(root: Path, scopes, explicit) -> list[str]:
    root = _resolved_root(root)
    automatic = []
    for scope in scopes:
        for value in (scope.old_path, scope.new_path):
            if value is None:
                continue
            relative = _relative_path(value, "scope path")
            directory = root.joinpath(*relative.parts[:-1])
            while True:
                for name in POLICY_NAMES:
                    candidate = directory / name
                    if _is_materialized_regular_file(root, candidate):
                        automatic.append(candidate.relative_to(root).as_posix())
                if directory == root:
                    break
                directory = directory.parent

    automatic = sorted(
        set(automatic),
        key=lambda value: (
            len(Path(value).parts),
            POLICY_NAMES.index(Path(value).name),
            value,
        ),
    )
    supplementary = sorted(
        {
            _materialized_file(root, value, "policy source")
            .relative_to(root)
            .as_posix()
            for value in explicit
        }
    )
    return list(dict.fromkeys(automatic + supplementary))


def _fence(value):
    if not isinstance(value, str):
        raise PacketError("packet scalar is not text")
    longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
    return "`" * max(4, longest + 1)


def _safe_inline(value, description):
    if not isinstance(value, str) or not value:
        raise PacketError(f"invalid {description}")
    if "`" in value or any(
        ord(character) < 0x20 or ord(character) == 0x7F
        for character in value
    ):
        raise PacketError(f"unsafe {description}")
    if any(character in "\u0085\u2028\u2029" for character in value):
        raise PacketError(f"unsafe {description}")
    return value


def _validated_scope(scope):
    old_path = (
        _safe_inline(scope.old_path, "old scope path")
        if scope.old_path is not None
        else None
    )
    new_path = (
        _safe_inline(scope.new_path, "new scope path")
        if scope.new_path is not None
        else None
    )
    if old_path is None and new_path is None:
        raise PacketError("scope has no path")
    ranges = (
        scope.old_start,
        scope.old_count,
        scope.new_start,
        scope.new_count,
    )
    if all(value is None for value in ranges):
        return old_path, new_path, ranges
    if any(type(value) is not int or value < 0 for value in ranges):
        raise PacketError("invalid scope ranges")
    if (scope.old_start == 0 and scope.old_count != 0) or (
        scope.new_start == 0 and scope.new_count != 0
    ):
        raise PacketError("invalid zero-start scope range")
    return old_path, new_path, ranges


def validate_packet(text: str) -> None:
    headings = []
    title_count = 0
    fence = None
    for line in text.splitlines():
        if fence is not None:
            if line == fence:
                fence = None
            continue
        opening = FENCE_OPEN_RE.fullmatch(line)
        if opening is not None:
            fence = opening.group(1)
            continue
        if line.startswith("# "):
            title_count += 1
            if line != "# Comment Gardener Job Packet":
                raise PacketError("invalid packet title")
        elif line.startswith("## "):
            headings.append(line[3:])
    if fence is not None:
        raise PacketError("unterminated packet fence")
    if title_count != 1 or tuple(headings) != PACKET_HEADINGS:
        raise PacketError("invalid canonical packet headings")


def render_packet(
    mode: str,
    scopes,
    policy_sources,
    user_constraints,
    capabilities,
    verification_commands,
) -> str:
    if mode not in VALID_MODES:
        raise PacketError("invalid packet mode")
    lines = [
        "# Comment Gardener Job Packet",
        "",
        "## Mode",
        f"`{mode}`",
        "",
        "## Seed scopes",
    ]
    if scopes:
        for scope in scopes:
            old_path, new_path, ranges = _validated_scope(scope)
            if old_path is not None and new_path is not None and old_path != new_path:
                label = f"old `{old_path}`; new `{new_path}`"
            else:
                label = f"`{new_path or old_path}`"
            if all(value is None for value in ranges):
                kind = (
                    "rename-only whole file"
                    if old_path is not None and new_path is not None and old_path != new_path
                    else "whole file"
                )
                lines.append(f"- {label}: {kind}")
            else:
                lines.append(
                    f"- {label}: old {scope.old_start},{scope.old_count}; "
                    f"new {scope.new_start},{scope.new_count}"
                )
    else:
        lines.extend(("- Resolution: successful no-op.", "- None."))

    sections = (
        ("Policy sources", policy_sources, None, "policy source"),
        ("Exact user constraints", user_constraints, "text", "user constraint"),
        ("Environment capabilities", capabilities, None, "capability"),
        (
            "Verification commands",
            verification_commands,
            "console",
            "verification command",
        ),
    )
    for title, values, language, description in sections:
        lines.extend(("", f"## {title}"))
        if not values:
            lines.append("- None.")
            continue
        for number, value in enumerate(values, 1):
            if language is None:
                lines.append(f"- `{_safe_inline(value, description)}`")
            else:
                fence = _fence(value)
                lines.extend((f"{number}. {fence}{language}", value, fence))

    lines.extend(("", "## Required report", *(f"- {field}" for field in REPORT_FIELDS)))
    packet = "\n".join(lines) + "\n"
    validate_packet(packet)
    return packet


def _run_jj(arguments, cwd, failure):
    try:
        result = subprocess.run(arguments, cwd=cwd, text=True, capture_output=True)
    except OSError as error:
        raise PacketError(failure) from error
    if result.returncode != 0:
        raise PacketError(failure)
    return result.stdout


def _diff_scopes(invocation_root, revision):
    root_output = _run_jj(
        ["jj", "--no-pager", "root"],
        invocation_root,
        "Jujutsu is required for diff-derived targets",
    )
    root_value = root_output.rstrip("\r\n")
    if not root_value:
        raise PacketError("Jujutsu did not report a repository root")
    root = _resolved_root(Path(root_value))
    diff = _run_jj(
        ["jj", "--no-pager", "diff", "-r", revision, "--git"],
        root,
        "Jujutsu could not resolve the requested diff target",
    )
    return root, parse_git_diff(diff)


def _argument_parser():
    parser = argparse.ArgumentParser()
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--path", action="append")
    targets.add_argument("--changeset", action="store_true")
    targets.add_argument("--stack", action="store_true")
    targets.add_argument("-r", "--revset")
    parser.add_argument("--mode", default="garden")
    parser.add_argument("--policy", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--verify", action="append", default=[])
    return parser


def main(argv=None) -> int:
    arguments = _argument_parser().parse_args(argv)
    try:
        if arguments.mode not in VALID_MODES:
            raise PacketError(f"unknown mode: {arguments.mode}")

        root = _resolved_root(Path.cwd())
        if arguments.path:
            scopes = resolve_explicit_paths(root, arguments.path)
        elif arguments.changeset:
            root, scopes = _diff_scopes(root, "@")
        elif arguments.stack:
            root, scopes = _diff_scopes(root, "immutable_heads()..@")
        elif arguments.revset is not None:
            if not arguments.revset:
                raise PacketError("revset must not be empty")
            root, scopes = _diff_scopes(root, arguments.revset)
        else:
            scopes = []

        policies = discover_policy_sources(root, scopes, arguments.policy)
        result = render_packet(
            arguments.mode,
            scopes,
            policies,
            arguments.constraint,
            arguments.capability,
            arguments.verify,
        )
    except PacketError as error:
        print(f"comment-gardener: {error}", file=sys.stderr)
        return 2

    print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
