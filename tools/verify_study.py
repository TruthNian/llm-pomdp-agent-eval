"""Verify historical Git bytes (text checkout CRLF is normalized to LF)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "studies" / "2026-gpt56-glm53" / "manifest.sha256.json"


def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for relative, expected in data["files"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise SystemExit("Invalid archive path")
        if not path.is_file():
            raise SystemExit(f"Historical archive missing: {relative}")
        raw = path.read_bytes()
        if path.suffix != ".zip":
            raw = raw.replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"Historical archive changed: {relative}")
    print(f"Historical archive verified: {len(data['files'])} immutable files.")


if __name__ == "__main__":
    main()
