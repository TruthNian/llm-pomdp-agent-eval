# Contributing

Contributions that improve reproducibility, add balanced task families, strengthen statistical analysis, or make the harness easier to adapt are welcome.

## Development checks

The project uses the Python standard library. Before opening a pull request, run:

```bash
python -m compileall harness tests tools
python -m unittest discover -s tests -v
python tools/verify_release.py
```

If you change feature extraction, also regenerate the reviewed outputs:

```bash
python harness/analyze_results.py
```

## Experimental changes

Changes to prompts, costs, root-cause observations, scoring, model identifiers, CLI flags, or timeout policy alter the experiment. Document them explicitly and avoid mixing new trajectories with the released primary dataset.

New comparative datasets should remain balanced and paired across model arms.

## Data safety

Never commit:

- `runs/` directories;
- raw Codex JSONL event streams;
- bearer tokens or provider credentials;
- unrelated user data;
- model-readable copies of the simulator or answer key.

The repository `.gitignore` blocks the main transient artifacts, but contributors remain responsible for reviewing staged files.

## Pull requests

Describe:

1. the methodological or implementation change;
2. which experimental factors it affects;
3. tests performed;
4. whether released metrics change;
5. any new limitations introduced.

By contributing, you agree that your contribution is licensed under Apache-2.0.
