"""Solver validation against closed-form results.

These are the tests that make the physics core trustworthy: each one checks a
solver against an answer that is known analytically, not against a previously
recorded output.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.optimize import brentq

from picchain import tmm
from picchain.geometry import CrossSection, RasterGrid, Shape, graded_axis, rasterise
from picchain.solvers.electrostatic import solve_potential
from picchain.solvers.fdmode import solve_modes, solve_slab


# --------------------------------------------------------------------------
# 1. slab waveguide against the analytic dispersion relation
# --------------------------------------------------------------------------
def _analytic_slab_te(n_core, n_clad, t_um, lam_um):
    """Fundamental TE mode of a symmetric slab, from tan(u) = w/u."""
    k0 = 2 * math.pi / lam_um
    V2 = (k0 * t_um / 2) ** 2 * (n_core**2 - n_clad**2)

    def f(u):
        return math.tan(u) - math.sqrt(max(V2 - u * u, 0.0)) / u

    u = brentq(f, 1e-6, min(math.pi / 2 - 1e-9, math.sqrt(V2) - 1e-9))
    w = math.sqrt(V2 - u * u)
    return math.sqrt(n_clad**2 + (w / (k0 * t_um / 2)) ** 2)


def _staggered_axis(lo, hi, h):
    """Uniform axis whose *cell faces* land on integer multiples of h, so a
    material interface at y=0 or y=t sits exactly between two nodes and every
    node is unambiguously one material.  A node sitting *on* the interface
    would widen the core by one cell and bias n_eff upward - which is why the
    production chain sub-pixel averages instead."""
    n = int(round((hi - lo) / h))
    return lo + h * (np.arange(n) + 0.5)


def test_slab_solver_matches_analytic():
    n_core, n_clad, t, lam = 2.1376, 1.4441, 0.200, 1.55
    y = _staggered_axis(-2.0, 2.2, 0.001)
    eps = np.where((y > 0) & (y < t), n_core**2, n_clad**2)
    n_fd = solve_slab(y, eps, lam, 1)[0]
    n_an = _analytic_slab_te(n_core, n_clad, t, lam)
    assert abs(n_fd - n_an) < 5e-4, f"FD {n_fd} vs analytic {n_an}"


def test_2d_solver_reduces_to_slab_when_x_invariant():
    """An x-invariant 2D problem must reproduce the 1D slab index."""
    n_core, n_clad, t, lam = 2.1376, 1.4441, 0.400, 1.55
    x = graded_axis(-4.0, 4.0, [], 0.05, 0.05)
    y = _staggered_axis(-1.6, 2.0, 0.002)
    eps_line = np.where((y > 0) & (y < t), n_core**2, n_clad**2)
    eps = np.tile(eps_line, (len(x), 1))
    m = solve_modes(x, y, eps, eps, lam, "TE", 1, n_core * 0.99)[0]
    n_an = _analytic_slab_te(n_core, n_clad, t, lam)
    # the finite x-window quantises the mode slightly *below* the true slab index
    assert n_an - 5e-3 < m.n_eff <= n_an + 2e-4


# --------------------------------------------------------------------------
# 2. electrostatics against a parallel-plate capacitor
# --------------------------------------------------------------------------
def test_parallel_plate_capacitor():
    """Two wide plates: E must be V/d and C must be eps0 eps_r A / d."""
    d, w, eps_r, V = 2.0, 40.0, 5.0, 1.0
    x = graded_axis(-25.0, 25.0, [-w / 2, w / 2], 0.25, 0.5, 1.0)
    y = graded_axis(-3.0, 3.0, [-d / 2, d / 2], 0.05, 0.2, 0.5)
    eps = np.full((len(x), len(y)), eps_r)
    inside = (np.abs(x)[:, None] <= w / 2)
    top = inside & (y[None, :] >= d / 2) & (y[None, :] <= d / 2 + 0.4)
    bot = inside & (y[None, :] <= -d / 2) & (y[None, :] >= -d / 2 - 0.4)
    res = solve_potential(x, y, eps, eps, [(top.astype(float), +V / 2),
                                           (bot.astype(float), -V / 2)])
    # field at the centre
    i0, j0 = np.argmin(np.abs(x)), np.argmin(np.abs(y))
    assert abs(res.Ey[i0, j0] - (-V / d)) < 0.02 * (V / d)
    # capacitance per unit length (fringing makes the numeric value larger)
    C = 2 * res.energy(eps, eps) / V**2          # in eps0 units, per um of depth
    C_ideal = eps_r * w / d
    assert C_ideal < C < 1.35 * C_ideal


# --------------------------------------------------------------------------
# 3. grating CMT / TMM
# --------------------------------------------------------------------------
def test_uniform_grating_peak_matches_tanh():
    kappa, L = 2.0e-4, 5000.0
    spec = tmm.compute_spectrum(kappa_per_um=kappa, L_um=L, n_bar=1.8, n_g=2.2,
                                period_um=1.28, order=3, span_GHz=300, points=8001)
    assert abs(spec.peak_R - math.tanh(kappa * L) ** 2) < 1e-4


def test_tmm_uniform_sections_match_closed_form():
    kappa, L = 1.5e-4, 4000.0
    delta = np.linspace(-6e-4, 6e-4, 51)
    closed = tmm.uniform_reflectivity(kappa, L, delta)
    secs = tmm.apodised_sections(L, kappa, 64, "uniform")
    piecewise = tmm.tmm_reflectivity(secs, delta)
    assert np.max(np.abs(np.abs(closed) ** 2 - np.abs(piecewise) ** 2)) < 1e-6


def test_apodisation_suppresses_sidelobes():
    kappa, L = 3.0e-4, 7000.0
    kw = dict(L_um=L, n_bar=1.8, n_g=2.2, period_um=1.28, order=3,
              span_GHz=400, points=6001, n_sections=401)
    uni = tmm.compute_spectrum(kappa_per_um=kappa, apodisation="uniform", **kw)
    gau = tmm.compute_spectrum(kappa_per_um=kappa, apodisation="gaussian", **kw)
    assert gau.sidelobe_suppression_dB() > uni.sidelobe_suppression_dB() + 5


def test_fwhm_never_below_transform_limit():
    """Whatever kappa we pick, a uniform grating cannot beat 0.886 c/(2 n_g L)."""
    L, n_g = 7250.0, 2.213
    floor = tmm.transform_limit_fwhm_Hz(L, n_g)
    for kL in (0.05, 0.3, 1.0, 2.1, 4.0):
        spec = tmm.compute_spectrum(kappa_per_um=kL / L, L_um=L, n_bar=1.789, n_g=n_g,
                                    period_um=1.27979, order=3, span_GHz=400, points=12001)
        assert spec.fwhm_Hz() > 0.97 * floor, f"kL={kL}"


def test_fourier_amplitude_signs_and_orders():
    dn, duty = 1e-3, 0.25
    a1 = tmm.fourier_amplitude(dn, duty, 1)
    a3 = tmm.fourier_amplitude(dn, duty, 3)
    assert a1 > 0 and a3 > 0
    # a 25% duty cycle nulls the 4th harmonic
    assert abs(tmm.fourier_amplitude(dn, duty, 4)) < 1e-15
    assert a1 > a3


def test_penetration_depth_limits():
    """L_pen = tanh(kL)/(2k) -> L/2 for a weak grating (light traverses the whole
    structure, so the mean turning point is the mid-plane) and -> 1/(2k) for a
    strong one (light never reaches the far end)."""
    L = 7000.0
    assert tmm.penetration_depth(1e-8, L) == pytest.approx(L / 2, rel=0.02)
    assert tmm.penetration_depth(2e-3, L) == pytest.approx(1 / (2 * 2e-3), rel=0.02)


# --------------------------------------------------------------------------
# 4. geometry / rasterisation
# --------------------------------------------------------------------------
def test_rasterise_subpixel_average():
    xs = CrossSection(background="A", window=(-1, 1, -1, 1))
    xs.add(Shape.rect("B", -0.5, 0.5, -0.5, 0.5))
    grid = RasterGrid(np.linspace(-1, 1, 41), np.linspace(-1, 1, 41))
    vals = rasterise(xs, grid, {"A": 0.0, "B": 1.0}, subsample=4)
    dx = np.gradient(grid.x); dy = np.gradient(grid.y)
    area = float(np.sum(vals * np.outer(dx, dy)))
    assert abs(area - 1.0) < 0.05        # the 1x1 um square


def test_graded_axis_snaps_features():
    ax = graded_axis(-4.0, 4.0, [-0.5, 0.5, 1.13], 0.01, 0.06, 0.4)
    for f in (-0.5, 0.5, 1.13):
        assert np.min(np.abs(ax - f)) < 1e-12
    assert np.all(np.diff(ax) > 0)


# --------------------------------------------------------------------------
# 5. loss is a loss
# --------------------------------------------------------------------------
def _R(kappa, L, alpha, sections=0):
    """Peak reflectivity. The cascade is evaluated by a Python loop over the
    detuning grid, so the grid is kept small; a uniform grating peaks at zero
    detuning and a few points either side establish that it does."""
    delta = np.linspace(-2e-5, 2e-5, 21)
    if sections:
        secs = tmm.apodised_sections(L, kappa, sections, "uniform", alpha)
        return float(np.max(np.abs(tmm.tmm_reflectivity(secs, delta)) ** 2))
    return float(np.max(np.abs(tmm.uniform_reflectivity(kappa, L, delta, alpha)) ** 2))


@pytest.mark.parametrize("sections", [0, 101])
def test_a_passive_grating_never_reflects_more_than_it_receives(sections):
    """The bound no coupling strength and no loss can breach.

    It was breached. The propagation loss entered the complex detuning with the
    sign of a gain, and the two evaluation paths disagreed about which sign that
    was. At kappa*L = 2.1 the error displaced the reflectivity by under 0.1 %
    and no target moved; at kappa*L = 3.2 it produced R = 1.003.
    """
    L = 7250.0
    for kL in (0.5, 1.0, 2.1, 3.2, 5.0):
        for alpha_dB in (0.0, 0.2, 1.0, 5.0):
            r = _R(kL / L, L, alpha_dB / (8.686e4), sections=sections)
            assert r <= 1.0, f"kL={kL}, alpha={alpha_dB} dB/cm gives R={r}"


@pytest.mark.parametrize("sections", [0, 101])
def test_reflectivity_falls_monotonically_with_loss(sections):
    """A bound alone is satisfied by a term of the right sign and the wrong
    magnitude. The gradient is what fixes the sign."""
    L, kappa = 7250.0, 3.2 / 7250.0
    values = [_R(kappa, L, a / (8.686e4), sections=sections)
              for a in (0.0, 0.2, 1.0, 5.0)]
    assert values == sorted(values, reverse=True), values
    assert values[0] == pytest.approx(math.tanh(kappa * L) ** 2, abs=1e-6)


def test_the_two_evaluation_paths_agree_when_the_grating_is_lossy():
    """The closed form and the piecewise cascade must agree with a loss present,
    not only without one. Comparing them at real detuning alone passes under
    either of two conjugate conventions and distinguishes nothing."""
    L, kappa = 7250.0, 3.2 / 7250.0
    for alpha_dB in (0.2, 1.0, 5.0):
        alpha = alpha_dB / (8.686e4)
        assert _R(kappa, L, alpha) == pytest.approx(
            _R(kappa, L, alpha, sections=101), rel=1e-6
        ), f"paths disagree at {alpha_dB} dB/cm"


# --- the longitudinal profile shape ----------------------------------------
# Added 2026-08-06. The closed-form coefficient assumes a rectangular profile.
# The assumption is silent, and it is not benign above first order: the
# suppression exponent carries the order squared, so a smoothing that costs the
# first harmonic 8 percent costs the third 54 percent.

def test_no_smoothing_is_the_identity():
    dn, duty, per = 1.1187e-3, 0.2344, 1.27979
    for m in (1, 2, 3, 4):
        assert tmm.profile_smoothing(m, per, 0.0) == 1.0
        assert (tmm.fourier_amplitude(dn, duty, m, per, 0.0)
                == tmm.fourier_amplitude(dn, duty, m))


def test_smoothing_matches_the_gaussian_transform():
    import math
    per, sig = 1.27979, 0.084
    for m in (1, 2, 3):
        expect = math.exp(-0.5 * (2 * math.pi * m * sig / per) ** 2)
        assert abs(tmm.profile_smoothing(m, per, sig) - expect) < 1e-15


def test_the_suppression_exponent_scales_as_the_order_squared():
    """The reason a rectangular profile is safe at m=1 and unsafe at m=3."""
    import math
    per, sig = 1.27979, 0.084
    s1 = tmm.profile_smoothing(1, per, sig)
    s3 = tmm.profile_smoothing(3, per, sig)
    assert abs(math.log(s3) / math.log(s1) - 9.0) < 1e-9
    assert s1 > 0.9 and s3 < 0.5


def test_smoothing_falls_monotonically_with_length_and_with_order():
    per = 1.27979
    prev = 1.0
    for sig in (0.02, 0.04, 0.08, 0.12):
        v = tmm.profile_smoothing(3, per, sig)
        assert v < prev
        prev = v
    prev = 1.0
    for m in (1, 2, 3, 4):
        v = tmm.profile_smoothing(m, per, 0.06)
        assert v < prev
        prev = v


def test_smoothing_reduces_kappa_by_exactly_that_factor():
    dn, duty, per, lam = 1.1187e-3, 0.2344, 1.27979, 1.5308
    bare = tmm.fourier_kappa(dn, duty, 3, lam)
    smoothed = tmm.fourier_kappa(dn, duty, 3, lam, per, 0.084)
    assert abs(smoothed / bare - tmm.profile_smoothing(3, per, 0.084)) < 1e-12


# --- the resonance condition on a non-monotonic phase -----------------------
# Added 2026-08-07. The round-trip phase of an extended cavity is not monotonic
# in frequency: a Bragg mirror steps by pi at each sidelobe null, and the
# apparent group delay there is large and negative. Inverting the phase by
# interpolation assumes monotonicity, returns a wrong root in silence, and made
# the tracked laser mode jump discontinuously by up to 12 GHz.

def test_a_monotonic_phase_gives_one_root_per_index():
    from picchain.stages.s04_cavity import resonance_roots
    f = np.linspace(0.0, 10.0, 1001)
    phase = 2 * np.pi * f          # one cycle per unit
    for k in (2, 5, 8):
        r = resonance_roots(f, phase, k)
        assert len(r) == 1
        assert abs(r[0] - k) < 1e-6


def test_every_root_is_found_when_the_phase_doubles_back():
    """Three crossings of the same level, which interpolation would report as
    one."""
    from picchain.stages.s04_cavity import resonance_roots
    f = np.linspace(0.0, 3.0, 3001)
    # rises to 3, falls to 1, rises to 3 again: level 2 is crossed three times
    phase = 2 * np.pi * np.interp(f, [0, 1, 2, 3], [0.0, 3.0, 1.0, 3.0])
    r = resonance_roots(f, phase, 2)
    assert len(r) == 3
    assert abs(r[0] - 2.0 / 3.0) < 1e-3
    assert abs(r[1] - 1.5) < 1e-3
    assert abs(r[2] - 2.5) < 1e-3


def test_a_level_never_reached_has_no_root():
    from picchain.stages.s04_cavity import resonance_roots
    f = np.linspace(0.0, 3.0, 301)
    phase = 2 * np.pi * np.interp(f, [0, 3], [0.0, 2.5])
    assert resonance_roots(f, phase, 4) == []


def test_the_roots_are_returned_in_increasing_frequency():
    from picchain.stages.s04_cavity import resonance_roots
    f = np.linspace(0.0, 4.0, 4001)
    phase = 2 * np.pi * np.interp(f, [0, 1, 2, 3, 4], [0.0, 3.0, 1.0, 3.0, 0.0])
    r = resonance_roots(f, phase, 2)
    assert len(r) == 4
    assert r == sorted(r)
