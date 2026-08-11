"""The search primitives, against cases evaluable by hand.

Each test corresponds to a failure mode the procedure exists to detect, and the
cases are drawn from the ones the TFLN baseline actually produced.
"""

from __future__ import annotations

import math

import pytest

from picchain import search as S
from picchain.config import Design, Target


# --- reducing a target to an interval --------------------------------------

def test_a_relative_tolerance_becomes_an_interval():
    r = S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20))
    assert r.lo == pytest.approx(0.60)
    assert r.hi == pytest.approx(0.90)
    assert r.describe() == "0.6 to 0.9"


def test_an_absolute_tolerance_overrides_the_relative_one():
    r = S.requirement_from_target(Target(metric="x", value=10.0, rel_tol=0.5, abs_tol=1.0))
    assert (r.lo, r.hi) == (9.0, 11.0)


def test_a_one_sided_target_leaves_the_other_side_open():
    r = S.requirement_from_target(Target(metric="mhf", min=8.0))
    assert r.lo == 8.0 and r.hi is None
    assert r.describe() == ">= 8"


def test_the_direction_says_which_way_the_metric_must_move():
    r = S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20))
    assert r.direction(0.913) == -1        # too high, must fall
    assert r.direction(0.50) == 1          # too low, must rise
    assert r.direction(0.75) == 0


def test_shortfall_is_relative_so_targets_in_different_units_can_be_ranked():
    r_R = S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20))
    r_M = S.requirement_from_target(Target(metric="mhf", min=8.0))
    # 0.913 against a 0.90 bound is a 1.4 % miss; 4.59 against 8 is a 43 % miss
    assert r_R.shortfall(0.913) == pytest.approx(0.0148, abs=1e-3)
    assert r_M.shortfall(4.59) == pytest.approx(0.4263, abs=1e-3)
    assert r_M.shortfall(4.59) > r_R.shortfall(0.913)


def test_a_satisfied_target_has_no_shortfall_and_no_direction():
    r = S.requirement_from_target(Target(metric="mhf", min=8.0))
    assert r.shortfall(9.34) == 0.0
    assert r.direction(9.34) == 0
    assert r.satisfied_by(9.34)


def test_a_missing_or_nan_metric_is_never_satisfied():
    r = S.requirement_from_target(Target(metric="x", min=1.0))
    assert not r.satisfied_by(None)
    assert not r.satisfied_by(float("nan"))
    assert r.shortfall(None) == float("inf")


# --- elasticity ------------------------------------------------------------

def test_elasticity_recovers_a_known_power_law():
    """A metric going as the square of the parameter has elasticity 2."""
    assert S.elasticity(1.0, 1.1, 1.0, 1.1**2) == pytest.approx(2.0)
    assert S.elasticity(1.0, 1.1, 1.0, 1.1**-3) == pytest.approx(-3.0)


def test_the_measured_kappa_gap_elasticity_matches_the_decay_rate():
    """kappa falls with the post gap at about 5.5 /um on this cross-section, so
    at a 630 nm gap the elasticity is that rate times the gap."""
    e = S.elasticity(0.63, 0.70, 2.747, 1.862)
    assert -4.0 < e < -3.3
    assert abs(e) / 0.63 == pytest.approx(5.86, abs=0.4)   # back to per-micrometre


def test_elasticity_is_undefined_where_a_quantity_crosses_zero():
    for args in ((1.0, 1.1, 1.0, -1.0), (0.0, 1.0, 1.0, 2.0), (1.0, 1.0, 1.0, 2.0)):
        v = S.elasticity(*args)
        assert v != v                       # NaN


def test_the_dominant_metric_is_the_one_moved_most():
    sv = S.Sensitivity(parameter="p", nominal=1.0, probed=1.1,
                       elasticity={"a": 0.2, "b": -3.7, "c": float("nan")})
    assert sv.dominant(["a", "b", "c"]) == ("b", -3.7)
    assert sv.dominant(["c"]) is None


# --- reachability ----------------------------------------------------------

def test_a_requirement_inside_the_span_is_reachable():
    rc = S.Reach(parameter="gap", metric="R", at_min=0.98, at_max=0.06, monotone=True)
    req = S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20))
    assert rc.can_reach(req)


def test_a_requirement_beyond_every_bound_is_not_reachable():
    """The case the procedure exists for: weakening the mirror asymptotes at
    7.47 GHz against an 8 GHz requirement, so no value of the gap reaches it."""
    rc = S.Reach(parameter="gap", metric="mhf", at_min=4.2, at_max=7.47, monotone=True)
    req = S.requirement_from_target(Target(metric="mhf", min=8.0))
    assert not rc.can_reach(req)


def test_an_open_ended_requirement_is_reachable_if_the_span_reaches_into_it():
    rc = S.Reach(parameter="p", metric="m", at_min=2.0, at_max=12.0, monotone=True)
    assert rc.can_reach(S.requirement_from_target(Target(metric="m", min=8.0)))


def test_a_span_needs_both_bounds_to_exist():
    rc = S.Reach(parameter="p", metric="m", at_min=None, at_max=5.0, monotone=True)
    assert rc.interval is None
    assert not rc.can_reach(S.requirement_from_target(Target(metric="m", min=1.0)))


# --- monotonicity ----------------------------------------------------------

def test_a_monotone_bracket_is_searchable():
    assert S.bracket_is_monotone([1.0, 2.0, 3.0])
    assert S.bracket_is_monotone([3.0, 2.0, 1.0])
    assert S.bracket_is_monotone([1.0, 1.0, 1.0])


def test_a_bracket_that_doubles_back_is_not():
    """The zero-bias tuning range behaved this way, and bisecting it would have
    converged on the starting phase rather than on the design."""
    assert not S.bracket_is_monotone([0.41, 7.68, 4.10])


def test_too_few_samples_cannot_disprove_monotonicity():
    assert S.bracket_is_monotone([1.0, 5.0])


# --- constraints -----------------------------------------------------------

def _design_with(feed: float, taper: float) -> Design:
    d = Design.model_validate({"meta": {"name": "t"},
                               "grating": {"period_um": 1.28}})
    d.cavity.feed_length_um = feed
    d.layout.taper_length_um = taper
    return d


def test_a_satisfied_constraint_reports_nothing():
    d = _design_with(1000.0, 150.0)
    assert S.check_constraints(d, ["cavity.feed_length_um >= layout.taper_length_um"]) == []


def test_a_violated_constraint_names_both_values():
    """The feed contains the taper, so a 200 um feed cannot hold a 450 um taper."""
    d = _design_with(200.0, 450.0)
    bad = S.check_constraints(d, ["cavity.feed_length_um >= layout.taper_length_um"])
    assert len(bad) == 1
    assert "200" in bad[0] and "450" in bad[0]


def test_a_field_may_be_compared_against_a_number():
    d = _design_with(1000.0, 150.0)
    assert S.check_constraints(d, ["cavity.feed_length_um >= 500"]) == []
    assert len(S.check_constraints(d, ["cavity.feed_length_um <= 500"])) == 1


def test_an_unparseable_constraint_counts_as_violated():
    """A typo must not silently disable a check."""
    d = _design_with(1000.0, 150.0)
    bad = S.check_constraints(d, ["feed is bigger than taper"])
    assert len(bad) == 1 and "unparseable" in bad[0]


def test_a_constraint_naming_a_field_that_does_not_exist_counts_as_violated():
    d = _design_with(1000.0, 150.0)
    bad = S.check_constraints(d, ["cavity.no_such_field >= 1"])
    assert len(bad) == 1 and "not found" in bad[0]


# --- bisection -------------------------------------------------------------

def test_bisection_finds_a_value_inside_the_interval():
    req = S.requirement_from_target(Target(metric="m", value=0.75, rel_tol=0.02))
    found, trail = S.bisect_to_requirement(lambda x: math.exp(-x), 0.0, 2.0, req)
    assert found is not None
    assert req.satisfied_by(math.exp(-found))


def test_bisection_returns_a_bound_that_already_satisfies():
    req = S.requirement_from_target(Target(metric="m", min=0.0))
    found, trail = S.bisect_to_requirement(lambda x: x, 1.0, 2.0, req)
    assert found == 1.0
    assert len(trail) == 1


def test_bisection_refuses_a_bracket_that_does_not_straddle():
    """Both ends miss on the same side, so there is nothing to bisect toward."""
    req = S.requirement_from_target(Target(metric="m", min=10.0))
    found, _ = S.bisect_to_requirement(lambda x: x, 0.0, 5.0, req)
    assert found is None


def test_bisection_reports_every_point_it_evaluated():
    req = S.requirement_from_target(Target(metric="m", value=0.5, rel_tol=0.001))
    found, trail = S.bisect_to_requirement(lambda x: x, 0.0, 1.0, req)
    assert found is not None
    assert len(trail) >= 3
    assert all(isinstance(t[0], float) for t in trail)


# --- scoring a candidate against every requirement -------------------------
# Added 2026-08-07 after the search produced a candidate worse than the design it
# started from. Two requirements shared one control, each was solved in turn, and
# the second overwrote the first.

def _reqs():
    return [
        S.requirement_from_target(Target(metric="modes", max=1.0)),
        S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20)),
        S.requirement_from_target(Target(metric="fwhm", min=5.0, max=14.0)),
        S.requirement_from_target(Target(metric="dnu", value=2.8, rel_tol=1.0)),
    ]


def test_a_point_meeting_everything_scores_highest_and_has_no_shortfall():
    met, short = S.score_point({"modes": 1.0, "R": 0.75, "fwhm": 10.0, "dnu": 2.8}, _reqs())
    assert met == 4
    assert short == 0.0


def test_the_candidate_the_sequential_solve_produced_scores_worse_than_the_baseline():
    """The regression, as numbers. Solving the bandwidth after the reflectivity
    on the same control moved three met requirements to unmet."""
    baseline = {"modes": 1.0, "R": 0.9133, "fwhm": 16.55, "dnu": 4.263}
    candidate = {"modes": 2.0, "R": 0.0607, "fwhm": 8.46, "dnu": 22.16}
    sb = S.score_point(baseline, _reqs())
    sc = S.score_point(candidate, _reqs())
    assert sb[0] == 2 and sc[0] == 1
    assert S.better(sb, sc)
    assert not S.better(sc, sb)


def test_more_requirements_met_always_beats_a_smaller_shortfall():
    """Three met and a large miss outranks two met and a small one."""
    assert S.better((3, 5.0), (2, 0.01))


def test_a_smaller_shortfall_breaks_a_tie():
    assert S.better((2, 0.1), (2, 0.9))
    assert not S.better((2, 0.9), (2, 0.1))


def test_a_missing_metric_is_penalised_rather_than_ignored():
    """A candidate whose metric could not be computed must not outrank one that
    was computed and merely missed."""
    missing = S.score_point({"modes": 1.0, "R": None, "fwhm": 10.0, "dnu": 2.8}, _reqs())
    present = S.score_point({"modes": 1.0, "R": 0.95, "fwhm": 10.0, "dnu": 2.8}, _reqs())
    assert present[0] == missing[0] == 3
    assert present[1] < missing[1]


# --- the scan --------------------------------------------------------------

def test_the_grid_spans_the_range_inclusive_of_both_bounds():
    g = S.scan_grid(0.5, 1.0, 6)
    assert len(g) == 6
    assert g[0] == pytest.approx(0.5)
    assert g[-1] == pytest.approx(1.0)
    assert all(b > a for a, b in zip(g, g[1:]))


def test_a_degenerate_grid_returns_the_midpoint():
    assert S.scan_grid(0.5, 1.0, 1) == [0.75]


def test_the_scan_finds_the_intersection_of_two_intervals_on_one_control():
    """The reflectivity wants the gap open, the bandwidth wants it further open,
    and only the overlap satisfies both. A scan finds it; two bisections do not."""
    reqs = [S.requirement_from_target(Target(metric="R", value=0.75, rel_tol=0.20)),
            S.requirement_from_target(Target(metric="fwhm", min=5.0, max=14.0))]

    def model(gap):
        # monotone falsework matching the measured trend
        R = {0.63: 0.913, 0.70: 0.748, 0.75: 0.580, 0.80: 0.411, 1.00: 0.061}
        F = {0.63: 16.55, 0.70: 12.84, 0.75: 11.10, 0.80: 9.97, 1.00: 8.46}
        return {"R": R[gap], "fwhm": F[gap]}

    scored = [(g, S.score_point(model(g), reqs)) for g in (0.63, 0.70, 0.75, 0.80, 1.00)]
    best = max(scored, key=lambda t: (t[1][0], -t[1][1]))
    assert best[0] == 0.70            # the only gap meeting both
    assert best[1][0] == 2
