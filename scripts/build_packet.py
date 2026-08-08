#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path
import re
import subprocess
import sys


HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)
POLICY_NAMES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
VALID_MODES = ("jungle", "garden", "zen")


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


def _decode_quoted_git_path(value):
    if not value.startswith('"'):
        if '"' in value:
            raise PacketError("undecodable quoted Git path")
        return value
    if len(value) < 2 or not value.endswith('"'):
        raise PacketError("undecodable quoted Git path")

    decoded = []
    index = 1
    end = len(value) - 1
    escapes = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    while index < end:
        character = value[index]
        if character != "\\":
            if ord(character) < 0x20:
                raise PacketError("undecodable quoted Git path")
            decoded.append(character)
            index += 1
            continue

        index += 1
        if index >= end:
            raise PacketError("undecodable quoted Git path")
        escape = value[index]
        if escape in escapes:
            decoded.append(escapes[escape])
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
            decoded.append(chr(codepoint))
            continue
        if escape in "01234567":
            digits = value[index : index + 3]
            if len(digits) != 3 or any(digit not in "01234567" for digit in digits):
                raise PacketError("undecodable quoted Git path")
            decoded.append(chr(int(digits, 8)))
            index += 3
            continue
        raise PacketError("undecodable quoted Git path")
    return "".join(decoded)


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


def parse_git_diff(text: str) -> list[SeedScope]:
    scopes = []
    header_old = None
    header_new = None
    marker_old = None
    marker_new = None
    have_header = False
    have_old_marker = False
    have_new_marker = False
    in_hunk = False

    for line in text.splitlines():
        if line.startswith("diff --git "):
            fields = _split_diff_header(line[len("diff --git ") :])
            header_old = _git_path(fields[0], "a/")
            header_new = _git_path(fields[1], "b/")
            marker_old = None
            marker_new = None
            have_header = True
            have_old_marker = False
            have_new_marker = False
            in_hunk = False
            continue

        if line.startswith("@@"):
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
            old_start, old_count, new_start, new_count = match.groups()
            scopes.append(
                SeedScope(
                    marker_old,
                    marker_new,
                    int(old_start),
                    int(old_count) if old_count is not None else 1,
                    int(new_start),
                    int(new_count) if new_count is not None else 1,
                )
            )
            in_hunk = True
            continue

        if in_hunk:
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
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _materialized_file(root, value, description):
    relative = _relative_path(value, description)
    candidate = root / relative
    if _has_symlink_component(root, relative):
        raise PacketError(f"{description} is not a materialized regular file")
    try:
        candidate.resolve(strict=True).relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise PacketError(f"{description} is not a materialized regular file") from error
    if not candidate.is_file():
        raise PacketError(f"{description} is not a materialized regular file")
    return candidate


def _directory_files(directory):
    files = []
    for child in sorted(directory.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            continue
        if child.is_file():
            files.append(child)
        elif child.is_dir():
            files.extend(_directory_files(child))
        else:
            raise PacketError("explicit directory contains a special file")
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
        except (OSError, RuntimeError, ValueError) as error:
            raise PacketError("explicit target is missing or outside the repository") from error
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(_directory_files(target))
        else:
            raise PacketError("explicit target is not a regular file or directory")
    return _sorted_unique_scopes(
        SeedScope(
            None,
            path.relative_to(root).as_posix(),
            None,
            None,
            None,
            None,
        )
        for path in files
    )


def _is_materialized_regular_file(root, path):
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return not _has_symlink_component(root, relative) and path.is_file()


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
    longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
    return "`" * max(4, longest + 1)


def render_packet(
    mode: str,
    scopes,
    policy_sources,
    user_constraints,
    capabilities,
    verification_commands,
) -> str:
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
            path = scope.new_path or scope.old_path
            if scope.old_start is None:
                lines.append(f"- `{path}`: whole file")
            else:
                lines.append(
                    f"- `{path}`: old {scope.old_start},{scope.old_count}; "
                    f"new {scope.new_start},{scope.new_count}"
                )
    else:
        lines.extend(("- Resolution: successful no-op.", "- None."))

    sections = (
        ("Policy sources", policy_sources, None),
        ("Exact user constraints", user_constraints, "text"),
        ("Environment capabilities", capabilities, None),
        ("Verification commands", verification_commands, "console"),
    )
    for title, values, language in sections:
        lines.extend(("", f"## {title}"))
        if not values:
            lines.append("- None.")
            continue
        for number, value in enumerate(values, 1):
            if language is None:
                lines.append(f"- `{value}`")
            else:
                fence = _fence(value)
                lines.extend((f"{number}. {fence}{language}", value, fence))

    lines.extend(
        (
            "",
            "## Required report",
            "- Effective mode",
            "- Policy sources read",
            "- Seed scopes",
            "- Reference expansion",
            "- Edits",
            "- Preserved and protected comments",
            "- Ambiguities",
            "- Verification commands and results",
            "- Packet fields or policy clauses that changed a verdict",
        )
    )
    return "\n".join(lines) + "\n"


def _run_jj(arguments, cwd, failure):
    try:
        result = subprocess.run(
            arguments,
            cwd=cwd,
            text=True,
            capture_output=True,
        )
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
        packet = render_packet(
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

    print(packet, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
