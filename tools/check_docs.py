"""Check repository-local Markdown destinations, excluding frozen historical reports."""
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / name for name in ("README.md", "README.zh-CN.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md")]
paths += list((ROOT / "docs").glob("*.md")) + list((ROOT / "studies").rglob("*.md"))
errors = []
for path in paths:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("http:", "https:", "mailto:", "#")):
            continue
        target = unquote(target.split("#")[0]).strip("<>")
        if target and not (path.parent / target).exists():
            errors.append(f"{path.relative_to(ROOT)} -> {target}")
if errors:
    raise SystemExit("Broken local links:\n" + "\n".join(errors))
print(f"Checked local links in {len(paths)} Markdown files.")
