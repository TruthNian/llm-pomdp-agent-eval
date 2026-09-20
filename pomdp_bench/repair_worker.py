"""Executed only inside the container, through python -I -S -c."""
import copy
import json
import pickle
from pathlib import Path
import sys


def main():
    payload = json.load(sys.stdin)
    root = Path("/work/repo")
    for name, content in payload["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    sys.path.insert(0, str(root / "src"))
    from packaging.requirements import Requirement

    values = []
    for query in payload["requests"]:
        try:
            operation = query["operation"]
            if operation == "invalid_state":
                restored = Requirement.__new__(Requirement)
                restored.__setstate__(query["state"])
                values.append({"error": None})
                continue
            original = Requirement(query["requirement"])
            original.specifier.prereleases = query["prereleases"]
            if operation == "pickle":
                restored = pickle.loads(pickle.dumps(original, protocol=query["protocol"]))
            elif operation == "copy":
                restored = copy.copy(original)
            elif operation == "deepcopy":
                restored = copy.deepcopy(original)
            else:
                restored = Requirement.__new__(Requirement)
                restored.__setstate__(dict(original.__dict__) if operation == "legacy_dict" else str(original))
            values.append({"text": str(restored), "name": restored.name, "extras": sorted(restored.extras),
                           "specifier": str(restored.specifier), "url": restored.url,
                           "marker": str(restored.marker) if restored.marker is not None else None,
                           "raw_prereleases": restored.specifier._prereleases,
                           "prereleases": restored.specifier.prereleases})
        except Exception as exc:
            values.append({"error": type(exc).__name__})
    print(json.dumps(values, allow_nan=False))


if __name__ == "__main__":
    main()
