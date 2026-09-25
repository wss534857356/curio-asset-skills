"""Copy selected skill directories; never overwrite existing installations."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def install(target: Path, names: list[str]) -> list[Path]:
    available = {p.name: p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file()}
    names = list(dict.fromkeys(names))
    if not names or any(name not in available for name in names):
        raise ValueError("Select valid skills: " + ", ".join(sorted(available)))
    target = target.expanduser().resolve()
    if target == SKILLS or SKILLS in target.parents:
        raise ValueError("The destination must be outside this repository's source skills.")
    destinations = [target / name for name in names]
    conflicts = [p for p in destinations if p.exists() or p.is_symlink()]
    if conflicts:
        raise FileExistsError("No files copied. Existing destinations: " + ", ".join(map(str, conflicts)))
    for name in names:
        if not (available[name] / "LICENSE").is_file():
            raise ValueError(f"Missing license for {name}")
    target.mkdir(parents=True, exist_ok=True)
    for name, destination in zip(names, destinations):
        shutil.copytree(
            available[name], destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
    return destinations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="Destination skills directory")
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument("--all", action="store_true", help="Install all bundled skills")
    select.add_argument("--skill", action="append", help="Skill name; repeat to select several")
    args = parser.parse_args()
    names = sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file()) if args.all else args.skill
    try:
        installed = install(args.target, names)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Installation stopped: {exc}\n")
    for path in installed:
        print(path)


if __name__ == "__main__":
    main()
