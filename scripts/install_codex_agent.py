from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets/codex/comment-gardener.toml"
FILENAME = "comment-gardener.toml"


class InstallError(Exception):
    pass


def find_project_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".jj").exists() or (candidate / ".git").exists():
            return candidate
    raise InstallError("no project root found from the current directory")


def destination(project: bool, cwd: Path, environ: dict[str, str]) -> Path:
    if project:
        base = find_project_root(cwd) / ".codex"
    else:
        base = Path(environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return base / "agents" / FILENAME


def reject_symlinked_components(target: Path) -> None:
    for component in (target.parent.parent, target.parent, target):
        if component.is_symlink():
            raise InstallError(f"refusing symlinked agent path: {component}")


def install(template: bytes, target: Path) -> str:
    reject_symlinked_components(target)
    if target.exists():
        if target.read_bytes() == template:
            return f"already installed: {target}"
        raise InstallError(f"refusing to overwrite different agent: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(template)
    return f"installed: {target}"


def remove(template: bytes, target: Path) -> str:
    reject_symlinked_components(target)
    if not target.exists():
        return f"already absent: {target}"
    if target.read_bytes() != template:
        raise InstallError(f"refusing to remove different agent: {target}")
    target.unlink()
    return f"removed: {target}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", action="store_true")
    scope.add_argument("--global", dest="global_scope", action="store_true")
    parser.add_argument("--remove", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = destination(args.project, Path.cwd(), dict(os.environ))
        template = TEMPLATE.read_bytes()
        message = remove(template, target) if args.remove else install(template, target)
    except (InstallError, OSError) as error:
        print(f"comment-gardener: {error}", file=sys.stderr)
        return 2
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
