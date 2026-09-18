# Historical study: GPT-5.6 Sol / GLM-5.3

This study motivated the project. It compares two model configurations on four fixed incident states under open, principle-based and procedural prompts, with three repeated runs per cell (72 trajectories total).

The original implementation, data and reports remain at their original paths to preserve links:

- [Simulator and runner](../../harness/)
- [72 environment traces and 71 final messages](../../results/)
- [Original analysis](../../harness/analyze_results.py)
- [Chinese report](../../reports/gpt56_glm53_pomdp_final_report.html)
- [Original method](../../docs/METHODOLOGY.md)
- [Original data card](../../docs/DATA_CARD.md)
- [Validity notes and errata](ERRATA.md)

Baseline commit: `cc44d68690db7dded3caf43183ac2908373ca635`. The original 72 traces, reports, derived statistics, harness source and method documents are protected by [SHA-256 hashes](manifest.sha256.json).

Hashes identify the committed Git bytes. The checker normalizes CRLF to LF for text checkouts so Windows and Linux agree; binary archives are hashed unchanged.

```bash
python tools/verify_study.py
python tools/verify_release.py
python harness/analyze_results.py
```

Recomputation may produce different final floating-point digits on different Python versions; compare the scientific quantities before interpreting byte changes. Never commit recomputed historical files over the frozen data. The integrity check intentionally flags any byte-level change.

The old model endpoints and CLI build may no longer behave identically. The archived runner has broad filesystem access and known observation-isolation limitations; use the v2 framework for new studies. Treat the old comparison as a local behavioral case study with the limitations below, not a representative ranking of all agents or an identified training experiment.
