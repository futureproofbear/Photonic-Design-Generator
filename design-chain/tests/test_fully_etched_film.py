"""A film etched to its full thickness has no slab, and three places assumed one.

Every design in this repository until 2026-09-14 declared a partial etch, so the
unetched slab beside the ridge was always present. It is the guidance floor for
the mode count, the background of the two-dimensional effective-index reduction,
and the cladding index the bend solve grades its caustic against. A silicon
nitride strip removes it, and each of the three reached the absent case for the
first time:

* the one-dimensional slab solve placed its spectral shift on the largest index
  in the column, which on a uniform column is an eigenvalue exactly, and the
  factorisation of the shifted matrix failed inside ARPACK;
* the mode stage substituted a guidance floor of zero, which admits every
  eigenvalue the solver returns, so a single-mode strip would have been counted
  as carrying four modes;
* the time-domain stage refused with a message naming neither the film nor the
  etch.

The first presented as a `RuntimeError` from three frames inside a linear-algebra
package. The second would have presented as a failed `must` row on a device that
meets it, which is the worse of the two.
"""

from __future__ import annotations

import numpy as np
import pytest

from picchain.solvers.fdmode import solve_slab


def _column(y: np.ndarray, n_bg: float, n_core: float,
            y0: float, y1: float) -> np.ndarray:
    eps = np.full_like(y, n_bg ** 2)
    eps[(y >= y0) & (y <= y1)] = n_core ** 2
    return eps


def test_a_uniform_column_returns_no_slab_mode_instead_of_failing_the_solver():
    y = np.linspace(-1.8, 1.8, 721)
    eps = np.full_like(y, 1.444 ** 2)
    assert solve_slab(y, eps, 1.55, 2) == []


def test_a_film_beside_a_fully_etched_ridge_is_such_a_column():
    """The cladding above and the buried oxide below are one material."""
    y = np.linspace(-1.8, 1.8, 721)
    eps = _column(y, 1.444, 1.444, 0.0, 0.0)    # a film of zero thickness
    assert solve_slab(y, eps, 1.55, 2) == []


def test_the_column_through_the_ridge_still_returns_its_mode():
    y = np.linspace(-1.8, 1.8, 1441)
    eps = _column(y, 1.444, 1.996, 0.0, 0.200)
    modes = solve_slab(y, eps, 1.55, 2)
    assert modes, "a 200 nm nitride film in silica guides one slab mode at 1550 nm"
    assert 1.50 < modes[0] < 1.70


def test_a_bound_mode_lies_above_the_medium_bounding_the_column():
    """The continuum is excluded, and it was not.

    The same column returned the oxide index itself as its second mode, which is
    a discretised radiation state and not a slab mode. Only the first entry is
    read downstream, so the defect had no consequence; it would have acquired one
    the moment a caller asked for two.
    """
    y = np.linspace(-1.8, 1.8, 1441)
    eps = _column(y, 1.444, 1.996, 0.0, 0.200)
    for n in solve_slab(y, eps, 1.55, 4):
        assert n > 1.444


def test_the_mode_stage_falls_back_to_the_cladding_and_says_which_floor_it_used():
    from pathlib import Path
    from picchain.stages import s01_mode
    source = Path(s01_mode.__file__).read_text(encoding="utf-8")
    assert "n_slab0 = float(n_slab[0]) if floor_is_the_slab else n_clad" in source
    assert '"guidance_floor_is"' in source


def test_the_effective_index_reduction_takes_the_cladding_where_there_is_no_slab():
    from pathlib import Path
    from picchain.stages import s09_fdtd
    source = Path(s09_fdtd.__file__).read_text(encoding="utf-8")
    assert "if clad:" in source
    assert "return float(core[0]), n_clad" in source


# --------------------------------------------------------------------------
# the bend proxy the resonator stage grades
# --------------------------------------------------------------------------

class _Ctx:
    def __init__(self, metrics):
        self.metrics = metrics

    def get(self, dotted, default=None):
        node = self.metrics
        for p in dotted.split("."):
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node


def test_the_graded_bend_proxy_is_the_caustic_distance_and_not_the_power_beyond_it():
    """The power beyond the caustic measures the window, so it is not graded.

    The bend solve integrates the field outside the caustic and returns nothing
    where the caustic lies outside the solved window, which is the case whenever
    the bend is comfortable. On the first silicon nitride ring the caustic sat at
    5.64 um against a window edge at 4.58 um, so a target reading that integral
    as zero would have passed for the reason that the instrument could not see
    the quantity.
    """
    from picchain.stages.s19_resonator import _bend_at_the_ring_radius

    ctx = _Ctx({"bend": {"enabled": True, "rows": [
        {"radius_um": 100.0, "solved": True, "caustic_x_um": 5.6358680746809595,
         "caustic_inside_window": False, "power_beyond_caustic": float("nan"),
         "dn_eff_from_straight": 3.673e-4},
    ]}})
    mode = {"n_eff_bare": 1.5273766016928247, "n_slab_floor": 1.444023621703261}
    out = _bend_at_the_ring_radius(ctx, 100.0, mode, 1.55)

    assert out["bend_solved_at_the_ring_radius"] is True
    # the unmeasurable quantity is reported as absent rather than as zero
    assert out["bend_power_beyond_caustic"] is None
    # gamma = k0 sqrt(n_eff^2 - n_floor^2), computed here from the two indices
    gamma = 2.0 * np.pi / 1.55 * np.sqrt(1.5273766016928247 ** 2 - 1.444023621703261 ** 2)
    assert out["bend_caustic_in_decay_lengths"] == pytest.approx(
        gamma * 5.6358680746809595, rel=1e-12)
    assert out["bend_caustic_in_decay_lengths"] > 5.0


def test_a_ring_radius_the_bend_stage_did_not_solve_returns_absence_not_a_neighbour():
    from picchain.stages.s19_resonator import _bend_at_the_ring_radius

    ctx = _Ctx({"bend": {"enabled": True, "rows": [
        {"radius_um": 200.0, "solved": True, "caustic_x_um": 11.2,
         "caustic_inside_window": False, "power_beyond_caustic": float("nan")},
        {"radius_um": 60.0, "solved": False, "reason": "leaky"},
    ]}})
    out = _bend_at_the_ring_radius(ctx, 100.0, {"n_eff_bare": 1.5, "n_slab_floor": 1.44}, 1.55)
    assert out["bend_solved_at_the_ring_radius"] is False
    assert out["bend_caustic_in_decay_lengths"] is None
