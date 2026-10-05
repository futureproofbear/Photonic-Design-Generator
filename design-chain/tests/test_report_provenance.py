"""A provenance row naming a metric no stage produces renders an empty cell.

The generated run report carries one row per stage: the question it answers, the
instrument, and the quantities it returned. The quantities are named by key, and
a key absent from the payload is skipped, so a row whose keys are all absent
renders `-`. That reads as a stage which produced nothing, and it is
indistinguishable from a stage that was switched off.

Two rows were in that state and neither had ever rendered a value:

* `bend` named `min_safe_radius_um`, which is produced by no stage in the chain.
  The stage returns `tightest_radius_solved_um` and
  `caustic_enters_window_at_um`.
* `fdtd` named the two quantities of its `grating` structure alone, so a run of
  its `coupler`, `bandstructure`, `mmi` or `taper` structure rendered nothing.
  The first design to run the coupler produced a report whose most expensive
  stage showed a dash.

A sibling test asserts that every registered stage has a provenance row at all.
This one asserts that the row can say something.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picchain.report import PROVENANCE

ROWS = {key: [f for f, _ in fields] for key, _, _, fields in PROVENANCE}


def test_no_row_names_a_key_that_appears_nowhere_in_the_source():
    """Every named key is written by some stage, or is a typo nobody can see."""
    src = Path(__file__).resolve().parents[1] / "src" / "picchain"
    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in (src / "stages").glob("*.py"))
    text += "\n".join(p.read_text(encoding="utf-8") for p in src.glob("*.py"))
    missing = sorted({f for fields in ROWS.values() for f in fields
                      if f'"{f}"' not in text})
    assert not missing, (
        f"these provenance keys are written by nothing: {missing}; the row renders "
        "an empty cell, which reads as a stage that produced no result")


def test_the_bend_row_names_what_the_bend_stage_returns():
    assert "tightest_radius_solved_um" in ROWS["bend"]
    assert "caustic_enters_window_at_um" in ROWS["bend"]
    assert "min_safe_radius_um" not in ROWS["bend"]


@pytest.mark.parametrize("key", ["kappa2", "unitarity", "critical_coupling_loss_dB_cm"])
def test_the_fdtd_row_covers_the_coupler_structure_and_not_the_grating_alone(key):
    assert key in ROWS["fdtd"]


def test_a_run_of_the_coupler_renders_a_result_for_every_stage_that_ran():
    """Against a real run tree where one is present, rather than in the abstract."""
    runs = sorted((Path(__file__).resolve().parents[2] / "examples" / "sin200_ring"
                   / "runs").glob("*/metrics.json"))
    solved = [p for p in runs
              if (p.parent / "fdtd.json").exists() and (p.parent / "resonator.json").exists()]
    if not solved:
        pytest.skip("no run in the tree carries both an fdtd and a resonator payload")
    metrics = json.loads(solved[-1].read_text(encoding="utf-8"))["metrics"]
    for key in ("fdtd", "bend", "resonator"):
        sec = metrics.get(key)
        if not sec or sec.get("enabled") is False:
            continue
        shown = [f for f in ROWS[key] if sec.get(f) is not None]
        assert shown, f"the {key!r} row would render an empty cell on this run"
