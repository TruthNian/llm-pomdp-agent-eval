# Pinned upstream source fixture

This directory contains code from pypa/packaging at the immutable base revision
recorded in provenance.json. The 32 files in base.json preserve the complete
package source, licenses, project metadata, selected public documentation and
the pre-fix requirements tests. Other repository files and Git history are
deliberately absent from the agent workspace.

packaging is available under either Apache-2.0 or BSD-2-Clause; its original
LICENSE, LICENSE.APACHE and LICENSE.BSD are preserved here and in the snapshot.
It is third-party source data, never imported or executed on the evaluator host.

upstream.patch and upstream-actions.json reproduce the maintainers' fix as an
artifact acceptance control. They are evaluator-only inputs and must not enter a
model's file listing, prompt or observation. They are not an observation-only
solving agent or an independent expert baseline. The fix remains publicly
discoverable upstream: this historical case is a public development fixture.
