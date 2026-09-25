"""Offline package validation; does not run Blender or paid generation services."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".venv", ".checks", "work", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".svg", ".txt"}


def main() -> int:
    failures: list[str] = []
    files = [p for p in ROOT.rglob("*") if p.is_file() and not (set(p.relative_to(ROOT).parts) & IGNORED)]
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if not skills:
        failures.append("No skills found")
    for entry in skills:
        try:
            text = entry.read_text(encoding="utf-8")
            match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.S)
            if not match:
                raise ValueError("Missing YAML frontmatter")
            metadata = yaml.safe_load(match.group(1))
            name = metadata.get("name", "")
            if name != entry.parent.name or not re.fullmatch(r"[a-z0-9-]{1,64}", name):
                raise ValueError("Skill name must match its directory")
            if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
                raise ValueError("Missing description")
            if not (entry.parent / "LICENSE").is_file():
                raise ValueError("Missing installable license")
        except (ValueError, AttributeError, yaml.YAMLError) as exc:
            failures.append(f"{entry.relative_to(ROOT)}: {exc}")

    links = images = scripts = 0
    for path in files:
        relative = path.relative_to(ROOT)
        try:
            if path.suffix == ".png":
                with Image.open(path) as img:
                    img.verify()
                images += 1
                continue
            if path.suffix not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".py":
                ast.parse(text, filename=str(relative))
                scripts += 1
            elif path.suffix == ".json":
                json.loads(text)
            elif path.suffix in {".yaml", ".yml"}:
                yaml.safe_load(text)
            elif path.suffix == ".md":
                prose = re.sub(r"^```.*?^```[^\n]*$", "", text, flags=re.M | re.S)
                for href in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", prose):
                    url = urlsplit(href.strip("<>"))
                    if url.scheme or url.netloc or not url.path:
                        continue
                    destination = (path.parent / unquote(url.path)).resolve()
                    if not destination.is_relative_to(ROOT) or not destination.exists():
                        failures.append(f"{relative}: broken local link {href}")
                    links += 1
            if re.search(r"[A-Z]:[/\\](?:Users|work)[/\\]", text, re.I):
                failures.append(f"{relative}: private absolute path")
            if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)", text):
                failures.append(f"{relative}: possible credential; inspect locally")
        except (ValueError, SyntaxError, OSError, yaml.YAMLError) as exc:
            failures.append(f"{relative}: {exc}")
    for failure in failures:
        print("FAIL:", failure)
    print(f"Checked {len(skills)} skills, {scripts} Python files, {links} local links and {images} screenshots.")
    print("PASS" if not failures else f"FAILED: {len(failures)} issue(s)")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
