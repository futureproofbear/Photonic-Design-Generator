"""A detached solve's result is reusable even when its waiter died before it landed.

The result normally carries the runner digest the reuse check compares; a
detached solve's waiter may be gone when the result is written, so the digest
is recorded at launch in a sidecar and read back from there.
"""
from __future__ import annotations

import json
from pathlib import Path

from picchain.fdtd.bridge import _find_prior, job_key, runner_digest


def test_a_result_without_a_digest_is_accepted_through_its_launch_sidecar(tmp_path: Path):
    runner = tmp_path / "runner.py"; runner.write_text("print('solver')\n")
    job = {"period_um": 1.4, "resolution": 30}
    prior_dir = tmp_path / "runs" / "20260923-000000-old"; prior_dir.mkdir(parents=True)
    (prior_dir / "meep_grating_job.json").write_text(json.dumps(job))
    (prior_dir / "meep_grating_result.json").write_text(json.dumps({"ok": True, "kappa_per_cm": 0.25}))
    work = tmp_path / "runs" / "20260923-000001-new"; work.mkdir()
    # without the sidecar the undigested result is declined
    assert _find_prior("grating", job_key(job), work, runner=runner) is None
    # with it, accepted, and attributed to the run it came from
    (prior_dir / "meep_grating_launch.json").write_text(json.dumps(
        {"job_key": job_key(job), "runner_digest": runner_digest(runner), "detached": True}))
    found = _find_prior("grating", job_key(job), work, runner=runner)
    assert found is not None and found[1] == "20260923-000000-old" and found[0]["kappa_per_cm"] == 0.25
    # a sidecar from a different runner is declined
    (prior_dir / "meep_grating_launch.json").write_text(json.dumps(
        {"job_key": job_key(job), "runner_digest": "not-this-runner", "detached": True}))
    assert _find_prior("grating", job_key(job), work, runner=runner) is None
