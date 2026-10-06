"""Corners run side by side in a pool of worker processes.

One corner of a laser design with a converged edge-coupler port and a
calibrated chirp took about six minutes, and an 81-corner factorial run
serially took the better part of a working day (2026-10-06).
"""

from __future__ import annotations

import inspect

from picchain import cli


def test_a_corner_is_a_top_level_job_a_pool_can_run():
    assert callable(cli._corner_job)
    params = inspect.signature(cli._corner_job).parameters
    assert list(params)[:4] == ["design_path", "chosen", "names", "params"]


def test_the_corners_command_takes_a_worker_count():
    params = inspect.signature(cli.corners).parameters
    assert "workers" in params and params["workers"].default.default == 1
