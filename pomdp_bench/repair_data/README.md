# Pinned real-task source snapshots

Each task directory contains a pre-fix text-file map, per-file hashes, source and
fix commits, an upstream source patch and exact edit actions for an artifact
control. The patch/actions/provenance are evaluator-side; only the pre-fix file
map is the agent workspace. No candidate source is imported on the host.

Packaging retains its Apache/BSD dual license. Werkzeug and attrs retain their
BSD/MIT licenses; urllib3 retains its MIT license. Exact upstream license files
are copied beside each snapshot and included inside its source map. No license
is replaced by the benchmark's own license.

The portfolio fixtures are reproduced by tools/import_repair_portfolio.py from
the pinned Git objects. They are public development tasks, not contamination-free
or independently sampled model-evaluation data.
