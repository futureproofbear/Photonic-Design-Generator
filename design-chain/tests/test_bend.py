"""Bend solver, against limits that are known without computation.

The conformal transformation has no closed-form answer for a two-dimensional
guide, so the properties tested here are the ones that must hold whatever the
geometry: the straight limit, the direction of the shift, its monotonicity, and
the position of the radiation caustic.
"""

from __future__ import annotations

import numpy as np

from picchain.solvers.fdmode import (
    bend_diagnostics,
    bend_permittivity,
    solve_bend_modes,
    solve_modes,
)


def _ridge(nx=121, ny=101, n_core=2.2, n_clad=1.45, w=0.9, t=0.4):
    """A rectangular high-index core in a uniform cladding."""
    x = np.linspace(-3.0, 3.0, nx)
    y = np.linspace(-2.0, 2.0, ny)
    eps = np.full((nx, ny), n_clad**2)
    core = (np.abs(x)[:, None] <= w / 2) & (np.abs(y)[None, :] <= t / 2)
    eps[core] = n_core**2
    return x, y, eps


def test_transform_is_a_grading_that_vanishes_on_axis():
    x, _, eps = _ridge()
    out = bend_permittivity(eps, x, radius_um=100.0)
    i0 = int(np.argmin(np.abs(x)))
    assert abs(out[i0, 0] / eps[i0, 0] - 1.0) < 1e-9        # unchanged on axis
    assert out[-1, 0] > eps[-1, 0]                          # raised outside
    assert out[0, 0] < eps[0, 0]                            # lowered inside


def test_large_radius_recovers_the_straight_mode():
    x, y, eps = _ridge()
    straight = solve_modes(x, y, eps, eps, 1.55, num_modes=1)[0]
    bent = solve_bend_modes(x, y, eps, eps, 1.55, radius_um=1.0e5, num_modes=1)[0]
    assert abs(bent.n_eff - straight.n_eff) < 1e-5


def test_the_mode_moves_outward_and_does_so_monotonically():
    x, y, eps = _ridge()
    straight = solve_modes(x, y, eps, eps, 1.55, num_modes=1)[0]
    base = bend_diagnostics(straight, 1.45**2, 1.0e6)["lateral_centroid_um"]

    shifts = []
    for R in (400.0, 200.0, 100.0, 50.0):
        m = solve_bend_modes(x, y, eps, eps, 1.55, radius_um=R, num_modes=1,
                             n_guess=straight.n_eff)[0]
        shifts.append(bend_diagnostics(m, 1.45**2, R)["lateral_centroid_um"] - base)

    assert all(s > 0 for s in shifts)                       # outward, always
    assert all(b > a for a, b in zip(shifts, shifts[1:]))   # further as R falls


def test_the_caustic_closes_in_as_the_bend_tightens():
    x, y, eps = _ridge()
    prev = None
    for R in (400.0, 100.0, 40.0):
        m = solve_bend_modes(x, y, eps, eps, 1.55, radius_um=R, num_modes=1)[0]
        d = bend_diagnostics(m, 1.45**2, R)
        # x_c = R ln(n_eff/n_clad): the caustic sits outside the core and
        # approaches it as the radius falls
        assert d["caustic_x_um"] > 0.45
        if prev is not None:
            assert d["caustic_x_um"] < prev
        prev = d["caustic_x_um"]


def test_a_caustic_outside_the_window_is_reported_rather_than_counted_as_zero():
    """A well-confined guide puts the caustic tens of micrometres out. Returning
    zero there would read as "nothing is lost" when the question was not asked."""
    x, y, eps = _ridge()
    m = solve_bend_modes(x, y, eps, eps, 1.55, radius_um=400.0, num_modes=1)[0]
    d = bend_diagnostics(m, 1.45**2, 400.0)
    assert d["caustic_x_um"] > x[-1]
    assert d["caustic_inside_window"] is False
    assert np.isnan(d["power_beyond_caustic"])


def test_the_outer_wall_artefact_is_not_returned_as_a_mode():
    """At a tight radius the transformed cladding out-guides the core, and an
    unguarded solve returns a state bound to the window edge with n_eff far
    above the core index. The guard must exclude it."""
    from picchain.solvers.fdmode import bend_window_limit, solve_modes as _sm
    from picchain.solvers.fdmode import bend_permittivity as _bp

    x, y, eps = _ridge()
    R = 6.0
    assert bend_window_limit(x, R, 2.2, 1.45) < x[-1]        # the artefact regime

    unguarded = _sm(x, y, _bp(eps, x, R), _bp(eps, x, R), 1.55, num_modes=1)[0]
    assert unguarded.n_eff > 2.2                              # above the core index

    # the guard refuses the case rather than returning the artefact
    import pytest
    with pytest.raises(RuntimeError, match="leaky"):
        solve_bend_modes(x, y, eps, eps, 1.55, radius_um=R, num_modes=1)
