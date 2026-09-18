from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

from .agents import BUILTINS
from .environment import CONDITIONS
from .evaluation import load_suite, run_suite, write_json
from .generator import DOMAINS, FAMILIES, PROFILES, suite
from .reporting import summarize, validate_run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generative POMDP Agent Benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Write a PRIVATE versioned suite")
    generate.add_argument("--out", type=Path, required=True)
    generate.add_argument("--count", type=int, default=12, help="Number of independent generator seeds")
    seed_group = generate.add_mutually_exclusive_group()
    seed_group.add_argument("--seed", type=int, default=0, help="Development seed start; public seeds are not held-out")
    seed_group.add_argument("--fresh", action="store_true", help="Generate private 128-bit seeds")
    generate.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES))
    generate.add_argument("--profiles", nargs="+", choices=PROFILES, default=["standard"])
    generate.add_argument("--domains", nargs="+", choices=DOMAINS, default=["incident"])
    run = commands.add_parser("run", help="Run a complete agent/condition/replicate matrix")
    run.add_argument("--suite", type=Path, required=True)
    run.add_argument("--agents", type=Path, help="JSON array of named agent configurations")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=["open"])
    run.add_argument("--replicates", type=int, default=1)
    run.add_argument("--wall-seconds", type=float, default=300)
    demo = commands.add_parser("demo", help="Offline positive/negative controls; consumes no model tokens")
    demo.add_argument("--out", type=Path, required=True)
    demo.add_argument("--count", type=int, default=12)
    for command in ("validate", "summarize"):
        item = commands.add_parser(command, help="Replay and check the entire run before reading statistics")
        item.add_argument("run_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            if args.count < 1 or args.out.exists():
                raise ValueError("Use count >= 1 and an unused output file")
            seeds = [secrets.randbits(128) for _ in range(args.count)] if args.fresh else list(range(args.seed, args.seed + args.count))
            data = suite(seeds, args.families, args.profiles, args.domains)
            write_json(args.out, data)
            print(f"Generated {len(data['cases'])} cases. Keep this file private during evaluation.")
        elif args.command in ("run", "demo"):
            if args.command == "demo":
                if args.count < 1:
                    raise ValueError("count must be positive")
                data = suite(list(range(args.count)))
                configs = [{"name": kind, "kind": kind} for kind in BUILTINS]
                conditions, replicates, wall = ["open"], 1, 300
            else:
                data = load_suite(args.suite)
                configs = json.loads(args.agents.read_text(encoding="utf-8")) if args.agents else [{"name": "reference", "kind": "reference"}]
                conditions, replicates, wall = args.conditions, args.replicates, args.wall_seconds
            report = run_suite(data, configs, conditions, replicates, args.out, wall)
            for row in report["overall"]:
                print(f"{row['agent']} / {row['condition']}: {row['successes']}/{row['episodes']} accepted")
            print(f"Wrote {args.out / 'summary.json'}; replay with: python -m pomdp_bench validate <run_directory>")
        else:
            manifest, records = validate_run(args.run_directory)
            if args.command == "summarize":
                report = summarize(records)
                report["run"] = {k: v for k, v in manifest.items() if k != "cases"}
                report["complete"] = True
                write_json(args.run_directory / "summary.json", report)
            print(f"Validated {len(records)} episodes: generator, observations, scores, and complete matrix.")
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
