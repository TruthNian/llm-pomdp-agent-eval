"""Reproduce the three pinned fixtures from authenticated Git clones; no imports."""
import difflib
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    "werkzeug_routing": ("werkzeug", "pallets/werkzeug", "0b472374af1ab91000ea244a0da44d49c04c7cce",
                         2834, 2860, ["tests/test_routing.py", "docs/routing.rst"]),
    "attrs_preinit": ("attrs", "python-attrs/attrs", "937b1e232803cc4ec9b9375ef525fc57c24ec498",
                      1427, 1428, ["tests/test_make.py", "docs/init.md"]),
    "urllib3_read": ("urllib3", "urllib3/urllib3", "54b6f7eb0784a3e1e76e763c359d058363195319",
                     3636, 4960, ["test/test_response.py", "docs/advanced-usage.rst"]),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True, help="Fresh directory; never overwrite released fixtures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    for task, (local, repo, fix, issue, pr, extra) in TASKS.items():
        checkout = ROOT / "artifacts" / (local + "-upstream")
        def git(*args):
            return subprocess.check_output(["git", "-C", str(checkout), *args])
        base = git("rev-parse", fix + "^").decode().strip()
        names = git("ls-tree", "-r", "--name-only", base).decode().splitlines()
        selected = [n for n in names if n.startswith("src/") and n.endswith((".py", ".pyi", "py.typed"))]
        selected += [n for n in names if "/" not in n and n.startswith(("LICENSE", "COPYING", "README", "pyproject.toml"))]
        selected += [n for n in extra if n in names]
        files = {n: git("show", base + ":" + n).decode("utf-8") for n in sorted(set(selected))}
        generated = {}
        if task == "urllib3_read":
            # Upstream's VCS build backend normally creates this untracked file.
            generated["src/urllib3/_version.py"] = '__version__ = "0+benchmark"\n'
            files.update(generated)
        changed = git("diff", "--name-only", base, fix, "--", "src/").decode().splitlines()
        actions = []
        for name in changed:
            old = files[name]
            new = git("show", fix + ":" + name).decode("utf-8")
            a, b = old.splitlines(keepends=True), new.splitlines(keepends=True)
            working = old
            for group in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_grouped_opcodes(3):
                before = "".join(a[group[0][1]:group[-1][2]])
                after = "".join(b[group[0][3]:group[-1][4]])
                if not before or working.count(before) != 1:
                    raise ValueError("Ambiguous upstream hunk")
                actions.append({"command": "edit", "target": {"path": name, "old": before, "new": after}})
                working = working.replace(before, after, 1)
            assert working == new
        actions += [{"command": "verify"}, {"command": "finish"}]
        patch = git("diff", base, fix, "--", "src/")
        provenance = {"repository": "https://github.com/" + repo,
                      "issue": f"https://github.com/{repo}/issues/{issue}",
                      "fix_pull_request": f"https://github.com/{repo}/pull/{pr}",
                      "base_commit": base, "fix_commit": fix,
                      "selection": "Complete package Python source/type stubs, root licenses/metadata, selected pre-fix docs/tests; no future fix in workspace",
                      "file_sha256": {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items() if n not in generated},
                      "upstream_patch_sha256": hashlib.sha256(patch).hexdigest()}
        if generated:
            provenance["generated_files"] = generated
            provenance["generated_file_sha256"] = {n: hashlib.sha256(t.encode()).hexdigest() for n, t in generated.items()}
        destination = args.out / task
        destination.mkdir(exist_ok=False)
        for name, data in (("base.json", files), ("provenance.json", provenance), ("upstream-actions.json", actions)):
            (destination / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (destination / "upstream.patch").write_bytes(patch)
        for name in files:
            if "/" not in name and name.startswith(("LICENSE", "COPYING")):
                (destination / name).write_bytes(files[name].encode())
        print(task, len(files), sum(len(t.encode()) for t in files.values()), base)


if __name__ == "__main__":
    main()
