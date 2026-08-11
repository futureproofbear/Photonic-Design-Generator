"""The per-design dashboard.

The page exists to draw one distinction, and these tests hold it: a stage that
produced no result must never read as a stage that passed. A verdict covers the
targets it was given, a target can only name a metric some stage produced, and a
design whose cross-checks are all switched off therefore passes without any of
them having been performed.
"""

from __future__ import annotations

import json

import pytest

from picchain.dashboard import (
    classify_warning,
    collect,
    headroom,
    render,
    render_html,
)


def _run(tmp_path, run_id="20260809-113858-T", metrics=None, warnings=(),
         design="{}"):
    d = tmp_path / "runs" / run_id
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({
        "run_id": run_id, "status": "ok", "elapsed_s": 1.0,
        "warnings": list(warnings), "metrics": metrics or {},
    }), encoding="utf-8")
    (d / "design.resolved.json").write_text(design, encoding="utf-8")
    return d


# --------------------------------------------------------------------------
# headroom
# --------------------------------------------------------------------------
@pytest.mark.parametrize("criterion, actual, expect", [
    ("<= 10.0", 0.0, 1.0),
    ("<= 10.0", 10.0, 0.0),
    (">= 8.0", 16.0, 1.0),
    (">= 8.0", 8.0, 0.0),
    ("= 100.0 +-10%", 100.0, 1.0),
    ("= 100.0 +-10%", 110.0, 0.0),
    (">= 5.0 and <= 15.0", 10.0, 1.0),
    (">= 5.0 and <= 15.0", 15.0, 0.0),
])
def test_headroom_measures_the_distance_to_the_binding_bound(criterion, actual, expect):
    assert headroom(criterion, actual) == pytest.approx(expect, abs=1e-9)


def test_an_unparsed_criterion_yields_no_bar_rather_than_a_full_one():
    """A shape the page does not recognise must never read as comfortable."""
    assert headroom("within the usual range", 3.0) is None
    assert headroom(">= 8.0", "not a number") is None
    assert headroom(">= 8.0", float("nan")) is None


def test_a_value_outside_its_bound_reports_no_headroom_rather_than_negative():
    assert headroom("<= 10.0", 12.0) == 0.0
    assert headroom(">= 8.0", 4.0) == 0.0


# --------------------------------------------------------------------------
# what the page says about a stage that did not run
# --------------------------------------------------------------------------
def test_a_stage_that_produced_nothing_is_not_shown_as_passing(tmp_path):
    d = _run(tmp_path, metrics={"mode": {"n_eff_bare": 1.8}})
    state = collect(d)
    by = {s["name"]: s for s in state["stages"]}
    assert by["mode"]["state"] == "ran"
    assert by["bend"]["state"] == "not_run"
    html = render_html(state)
    assert "not executed" in html


def test_a_stage_switched_off_is_told_apart_from_one_never_asked(tmp_path):
    d = _run(tmp_path, metrics={"mode": {}, "bend": {"enabled": False,
                                                     "reason": "not requested"}})
    by = {s["name"]: s for s in collect(d)["stages"]}
    assert by["bend"]["state"] == "off"
    assert by["fem"]["state"] == "not_run"


def test_the_coverage_count_is_reported_beside_the_verdict(tmp_path):
    """A PASS over twelve targets while seven stages produced nothing is the
    condition the page was written for."""
    d = _run(tmp_path, metrics={
        "mode": {}, "verify": {"verdict": "PASS", "n_targets": 1, "n_pass": 1,
                               "n_fail": 0, "n_missing": 0, "rows": []}})
    html = render_html(collect(d))
    assert "2 of 17 stages produced a result" in html


# --------------------------------------------------------------------------
# when each stage last ran
# --------------------------------------------------------------------------
def test_a_stage_absent_now_reports_when_it_last_ran(tmp_path):
    """A subset run leaves the other stages untouched, and a reader wants to
    know when the bend was last looked at rather than that this run ignored it.
    """
    _run(tmp_path, run_id="20260801-101010-OLD",
         metrics={"mode": {}, "bend": {"radii": []}}, design='{"a": 1}')
    now = _run(tmp_path, run_id="20260809-113858-NEW",
               metrics={"mode": {}}, design='{"a": 2}')
    by = {s["name"]: s for s in collect(now)["stages"]}
    assert by["bend"]["state"] == "not_run"
    assert by["bend"]["last"]["run_id"] == "20260801-101010-OLD"
    assert by["bend"]["last"]["when"] == "2026-08-01 10:10"
    # the design moved between the two runs, so the earlier result predates it
    assert by["bend"]["last"]["same_design"] is False
    assert by["mode"]["last"]["same_design"] is True


def test_a_stage_never_run_says_so(tmp_path):
    d = _run(tmp_path, metrics={"mode": {}})
    by = {s["name"]: s for s in collect(d)["stages"]}
    assert by["bend"]["last"] is None
    assert "never run under this design" in render_html(collect(d))


# --------------------------------------------------------------------------
# the warnings, sorted by what must be done about them
# --------------------------------------------------------------------------
def test_a_warning_the_heuristic_does_not_recognise_is_only_ever_demoted():
    """Promotion by accident would misreport a note as a defect. The default is
    the least severe group."""
    assert classify_warning("something nobody anticipated") == "recorded"
    assert classify_warning("the laser will hop mid-ramp") == "blocking"
    assert classify_warning("2019641 um2 of fill is required") == "outstanding"


def test_the_page_is_one_file_with_no_external_reference(tmp_path):
    """It is opened from disk, so a stylesheet or a script fetched over the
    network would leave it unstyled or broken wherever it was sent."""
    d = _run(tmp_path, metrics={"mode": {}})
    out = render(d)
    html = out.read_text(encoding="utf-8")
    assert out.name == "dashboard.html"
    assert html.lstrip().startswith("<!doctype html>")
    for token in ("src=", "http://", "https://", "<script"):
        assert token not in html, f"the page reaches outside itself: {token}"


def test_it_renders_for_a_run_that_produced_almost_nothing(tmp_path):
    """A dashboard that raises on a partial run is of no use during the part of
    a design where it is most wanted."""
    d = _run(tmp_path, metrics={})
    html = render_html(collect(d))
    assert "0 of 17 stages produced a result" in html
    assert "No target was evaluated" in html


# --------------------------------------------------------------------------
# the flow itself: a comprehensive stage list must be runnable in the order the
# chain chooses, whatever order the design happens to declare it in
# --------------------------------------------------------------------------
def test_every_stage_runs_after_the_stages_it_depends_on():
    """It did not. The execution order was the registration order of `STAGES`,
    which is not a topological sort of the dependency map: `fdtd` is registered
    before `grating` and depends on it, so a run naming both executed `fdtd`
    first and raised. A design that declares the whole flow is exactly the case
    that exposes it.
    """
    from picchain.cli import _resolve_stages
    from picchain.stages import DEPENDENCIES, STAGES

    order = _resolve_stages(list(STAGES))
    assert len(order) == len(STAGES)
    at = {s: i for i, s in enumerate(order)}
    for stage in order:
        for dep in DEPENDENCIES[stage]:
            assert at[dep] < at[stage], f"{stage} runs before its input {dep}"


def test_the_declared_order_does_not_change_the_executed_order():
    """The author declares which stages, and the dependency map decides when."""
    from picchain.cli import _resolve_stages
    from picchain.stages import STAGES

    forward = _resolve_stages(list(STAGES))
    reverse = _resolve_stages(list(reversed(list(STAGES))))
    assert forward == reverse


def test_asking_for_one_stage_brings_in_what_it_needs():
    from picchain.cli import _resolve_stages

    order = _resolve_stages(["cavity"])
    assert order == ["mode", "grating", "eo", "cavity"]


# --------------------------------------------------------------------------
# the page checks itself
#
# Six defects in this page were reported by its reader rather than found by its
# author, across successive publishes. Every one was visible in the output.
# --------------------------------------------------------------------------
def test_a_stage_cannot_be_reported_as_run_and_in_flight_at_once(tmp_path):
    """A green chip beside a line saying the run was interrupted asserts two
    incompatible things, and the page was doing exactly that."""
    from picchain.dashboard import selfcheck

    d = _run(tmp_path, metrics={"mode": {}})
    state = collect(d)
    by = {s["name"]: s for s in state["stages"]}
    by["mode"]["running"] = {"run_id": "x", "elapsed_min": 5.0}
    assert any("at once" in p for p in selfcheck(state))


def test_a_verdict_of_pass_with_unmet_targets_is_refused(tmp_path):
    from picchain.dashboard import selfcheck

    d = _run(tmp_path, metrics={"verify": {"verdict": "PASS", "n_targets": 12,
                                           "n_pass": 11, "n_fail": 1,
                                           "n_missing": 0, "rows": []}})
    assert any("verdict PASS" in p for p in selfcheck(d and collect(d)))


def test_a_contradictory_page_is_not_written(tmp_path):
    """A page nobody can trust is worse than no page."""
    import picchain.dashboard as dash

    d = _run(tmp_path, metrics={"verify": {"verdict": "PASS", "n_targets": 3,
                                           "n_pass": 1, "n_fail": 2,
                                           "n_missing": 0, "rows": []}})
    with pytest.raises(RuntimeError, match="contradicts itself"):
        dash.render(d)
    assert not (d / "dashboard.html").exists()


def test_the_page_names_a_later_run_where_one_exists(tmp_path):
    """A page describing an older run is not wrong, but a reader cannot tell
    unless it says so, and a stale page is read as a current one."""
    from picchain.dashboard import newer_run

    old = _run(tmp_path, run_id="20260101-010101-OLD", metrics={"mode": {}})
    _run(tmp_path, run_id="20260202-020202-NEW", metrics={"mode": {}})
    assert newer_run(old.parent, "20260101-010101-OLD") == "20260202-020202-NEW"
    html = render(old).read_text(encoding="utf-8")
    assert "20260202-020202-NEW" in html
    assert "does not describe it" in html


def test_no_later_run_leaves_the_page_unqualified(tmp_path):
    d = _run(tmp_path, run_id="20260303-030303-ONLY", metrics={"mode": {}})
    assert "does not describe it" not in render(d).read_text(encoding="utf-8")
