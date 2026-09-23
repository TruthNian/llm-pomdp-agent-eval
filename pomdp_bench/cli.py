from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

from .agents import BUILTINS
from .collection import prepare_suite, resume_suite, run_status, run_suite, save_summary
from .worlds import CONDITIONS
from .evaluation import load_suite, replay_environment
from .generator import DOMAINS, FAMILIES, PROFILES, suite
from .reporting import validate_run
from .storage import collection_lock, read_json, write_json
from .studies import prepare_study, validate_plan
from .coverage import SCALES, DEPTH_SCALES, suite as coverage_suite
from .repair import suite as repair_suite
from .reconciliation import suite as reconciliation_suite
from .repair_portfolio import TASKS as REPAIR_TASKS
from .incident import suite as incident_suite
from .settlement import suite as settlement_suite
from .generator import digest


def show_study(report):
    for row in report.get("study_analysis", {}).get("primary_comparisons", []):
        print(f"{row['agent']}: paired difference={row['observed_success_difference']:.3f}; "
              f"interval={row['simultaneous_hoeffding_interval']}; {row['decision']}; {row['pilot_gate']}")


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
    coverage = commands.add_parser("generate-cover", help="Versioned planning scales; PRIVATE cases, no model calls")
    coverage.add_argument("--out", type=Path, required=True)
    coverage.add_argument("--count", type=int, default=12)
    coverage.add_argument("--scales", nargs="+", choices=(*SCALES, *DEPTH_SCALES))
    coverage.add_argument("--experimental", action="store_true", help="Use qualified depth profiles; model difficulty remains uncalibrated")
    coverage_seed = coverage.add_mutually_exclusive_group()
    coverage_seed.add_argument("--seed", type=int, default=0, help="Public development seed start")
    coverage_seed.add_argument("--fresh", action="store_true")
    coverage.add_argument("--stable", action="store_true", help="Recovery ablation")
    coverage.add_argument("--slack", type=int, default=0, help="Additional work in each epoch; a different task distribution")
    repair = commands.add_parser("prepare-repair-suite", help="Pin a real upstream repair task and container image; no code execution")
    repair.add_argument("--image", required=True, help="Immutable local Docker image ID (sha256:...)")
    repair.add_argument("--tasks", nargs="+", choices=REPAIR_TASKS, help="Select the real portfolio; omit for the original packaging anchor")
    repair.add_argument("--out", type=Path, required=True)
    reconciliation = commands.add_parser("prepare-reconciliation-suite", help="Prepare cross-component SQL reconciliation repair")
    reconciliation.add_argument("--out", type=Path, required=True)
    external = commands.add_parser("prepare-settlement-suite", help="Prepare external settlement with separate provider state")
    external.add_argument("--out", type=Path, required=True)
    incident = commands.add_parser("prepare-incident-suite", help="Prepare the executable checkout/settlement incident")
    incident.add_argument("--out", type=Path, required=True)
    study = commands.add_parser("prepare-study", help="Bind a preregistered two-condition plan and draw fresh seeds; no model calls")
    study.add_argument("--plan", type=Path, required=True)
    study.add_argument("--out", type=Path, required=True)
    for name in ("run", "prepare"):
        run = commands.add_parser(name, help="Execute a fresh matrix" if name == "run" else "Freeze a matrix without calling models")
        run.add_argument("--suite", type=Path, required=True)
        run.add_argument("--agents", type=Path, help="JSON array of named agent configurations")
        run.add_argument("--out", type=Path, required=True)
        run.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=["open"])
        run.add_argument("--replicates", type=int, default=1)
        run.add_argument("--wall-seconds", type=float, default=300)
    demo = commands.add_parser("demo", help="Offline positive/negative controls; consumes no model tokens")
    demo.add_argument("--out", type=Path, required=True)
    demo.add_argument("--count", type=int, default=12)
    for command in ("validate", "recheck", "summarize", "resume", "status"):
        item = commands.add_parser(command, help={"resume": "Collect only unstarted episodes; never retry failures",
                                                 "status": "Inspect coverage without calling models"}.get(
                                                     command, "Replay and check the entire matrix"))
        item.add_argument("run_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-reconciliation-suite":
            write_json(args.out, reconciliation_suite(), replace=False)
            print("Prepared two reconciliation contracts; strong-model difficulty remains uncalibrated.")
        elif args.command == "prepare-settlement-suite":
            write_json(args.out, settlement_suite(), replace=False)
            print("Prepared external settlement; provider state is separate from local books.")
        elif args.command == "prepare-incident-suite":
            write_json(args.out, incident_suite(), replace=False)
            print("Prepared the incident; run uses local HTTP/SQLite services, validate uses recorded behavior.")
        elif args.command == "prepare-repair-suite":
            write_json(args.out, repair_suite(args.image, args.tasks), replace=False)
            print("Prepared pinned repository source and runtime; no code or model execution.")
        elif args.command == "prepare-study":
            plan = read_json(args.plan)
            required = validate_plan(plan)
            manifest = prepare_study(plan, args.out)
            print(f"Prepared {manifest['expected_episodes']} episodes for {plan['purpose']} study {plan['study_id']}.")
            print(f"Independent seeds: {plan['independent_seeds']}; conservative precision requirement: {required}.")
            print(f"Plan SHA256: {manifest['study']['plan_sha256']}; no model requests made. Resume: {args.out}")
        elif args.command in ("generate", "generate-cover"):
            if args.count < 1 or args.out.exists():
                raise ValueError("Use count >= 1 and an unused output file")
            seeds = [secrets.randbits(128) for _ in range(args.count)] if args.fresh else list(range(args.seed, args.seed + args.count))
            data = (coverage_suite(seeds, args.scales, recovery=not args.stable, slack=args.slack, experimental=args.experimental)
                    if args.command == "generate-cover" else suite(seeds, args.families, args.profiles, args.domains))
            write_json(args.out, data)
            print(f"Generated {len(data['cases'])} cases. Keep this file private during evaluation.")
        elif args.command in ("run", "demo", "prepare"):
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
            if args.command == "prepare":
                manifest = prepare_suite(data, configs, conditions, replicates, args.out, wall)
                print(f"Prepared {manifest['expected_episodes']} episodes; no model requests made. Resume: {args.out}")
                return 0
            report = run_suite(data, configs, conditions, replicates, args.out, wall)
            for row in report["overall"]:
                print(f"{row['agent']} / {row['condition']}: {row['successes']}/{row['episodes']} accepted")
            print(f"Wrote {args.out / 'summary.json'}; replay with: python -m pomdp_bench validate <run_directory>")
        elif args.command == "resume":
            report = resume_suite(args.run_directory)
            print(f"Collected and validated {report['episodes']} episodes; existing attempts were not retried.")
            show_study(report)
        elif args.command == "status":
            print(json.dumps(run_status(args.run_directory), indent=2))
        else:
            if args.command == "summarize":
                with collection_lock(args.run_directory):
                    report = save_summary(args.run_directory)
                    count = report["episodes"]
                    show_study(report)
            else:
                manifest, records = validate_run(args.run_directory)
                if args.command == "recheck":
                    cases = {digest(c): c for c in manifest["cases"]}
                    for row in records:
                        replay_environment(row, cases[row["case_id"]], execute_checks=True)
                    print("External checks re-executed and compared with recorded behavior.")
                count = len(records)
            print(f"Validated {count} episodes: generator, observations, scores, and complete matrix.")
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
