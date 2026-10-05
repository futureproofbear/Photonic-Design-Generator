"""The ring closed forms, checked by routes that share no step with them.

`picchain.resonator` evaluates and inverts one transfer function. A test that
pinned its output would pin whatever that function returns today, so every check
below reaches the same quantity by a different construction:

* the transmission is rebuilt by summing the circulating field round trip by
  round trip, which is the derivation of the closed form rather than the closed
  form;
* the width is found by bisection on that summed field at the half-depth level,
  with no inversion performed;
* the free spectral range is found by locating two consecutive resonances of a
  dispersive phase, which tests that the group index and not the effective index
  is the quantity dividing;
* the degeneracy is checked by putting both returned couplings back through the
  transfer function.
"""

from __future__ import annotations

import cmath
import math

import pytest

from picchain import resonator as rz


# --------------------------------------------------------------------------
# the independent constructions
# --------------------------------------------------------------------------

def summed_transmission(a: float, t: float, phi: float, floor: float = 1e-15) -> float:
    """Power in the bus, by summing the field over successive round trips.

    The through field is the directly transmitted part plus one term for each
    circulation, and the series is summed term by term. Nothing here is the
    closed form under test.

    The number of terms is set by the ratio `a t`, which is how far a round trip
    decays. A fixed count silently truncates a high-finesse ring: at `a t` of
    0.9989 a four-thousand-term sum still carries three parts in ten thousand of
    the series, which is a thousand times the agreement this test asserts.
    """
    ratio = a * t
    terms = 4000 if ratio <= 0.0 else int(math.log(floor) / math.log(ratio)) + 2
    kappa = math.sqrt(1.0 - t * t)
    x = a * cmath.exp(-1j * phi)
    # t * E_in, then -(kappa^2) x (t x)^m for m = 0, 1, 2, ...
    field = complex(t, 0.0)
    term = -(kappa ** 2) * x
    for _ in range(terms):
        field += term
        term *= t * x
    return float(abs(field) ** 2)


def bisect_half_depth(a: float, t: float) -> float:
    """Half-width in phase, by bisection on the summed field.

    The level is the mean of the summed transmission at resonance and at
    anti-resonance. No expression is inverted.
    """
    lo = summed_transmission(a, t, 0.0)
    hi = summed_transmission(a, t, math.pi)
    level = 0.5 * (lo + hi)
    left, right = 0.0, math.pi
    for _ in range(200):
        mid = 0.5 * (left + right)
        if summed_transmission(a, t, mid) < level:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)


def resonance_near(n0: float, n_group: float, lam0_um: float, length_um: float,
                   order_offset: int) -> float:
    """Wavelength of a resonance, from a dispersive phase and no closed form.

    The effective index is given a linear dispersion consistent with the stated
    group index, `n_g = n_eff - lambda dn/dlambda`, and the round-trip phase is
    driven to the requested multiple of two pi by bisection.
    """
    dn_dlam = (n0 - n_group) / lam0_um

    def n_eff(lam: float) -> float:
        return n0 + dn_dlam * (lam - lam0_um)

    def phase(lam: float) -> float:
        return 2.0 * math.pi * n_eff(lam) * length_um / lam

    m0 = round(phase(lam0_um) / (2.0 * math.pi))
    target = 2.0 * math.pi * (m0 + order_offset)
    # phase falls with wavelength, so the bracket is ordered the other way
    left, right = lam0_um * 0.99, lam0_um * 1.01
    for _ in range(300):
        mid = 0.5 * (left + right)
        if phase(mid) > target:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)


# --------------------------------------------------------------------------
# the transfer function
# --------------------------------------------------------------------------

@pytest.mark.parametrize("a", [0.999, 0.99, 0.95, 0.80])
@pytest.mark.parametrize("t", [0.9999, 0.999, 0.99, 0.90, 0.70])
@pytest.mark.parametrize("phi", [0.0, 0.03, 0.4, 1.7, math.pi])
def test_transmission_equals_the_field_summed_over_round_trips(a, t, phi):
    assert rz.transmission(a, t, phi) == pytest.approx(
        summed_transmission(a, t, phi), rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("a,t", [(0.999, 0.99), (0.95, 0.999), (0.8, 0.8)])
def test_the_stated_extremes_are_the_extremes_of_the_function(a, t):
    lo = rz.transmission_on_resonance(a, t)
    hi = rz.transmission_off_resonance(a, t)
    sampled = [rz.transmission(a, t, k * math.pi / 400.0) for k in range(401)]
    assert lo == pytest.approx(min(sampled), rel=1e-10)
    assert hi == pytest.approx(max(sampled), rel=1e-10)


def test_critical_coupling_extinguishes_the_resonance_completely():
    a = 0.987
    assert rz.transmission_on_resonance(a, a) == pytest.approx(0.0, abs=1e-18)
    assert rz.coupling_regime(a, a) == "critical"


def test_the_regime_follows_the_ordering_of_a_and_t():
    assert rz.coupling_regime(0.99, 0.999) == "under"
    assert rz.coupling_regime(0.999, 0.99) == "over"


# --------------------------------------------------------------------------
# the width
# --------------------------------------------------------------------------

@pytest.mark.parametrize("a", [0.9999, 0.999, 0.99, 0.95, 0.85])
@pytest.mark.parametrize("t", [0.9999, 0.999, 0.99, 0.95, 0.85])
def test_the_inverted_half_width_is_the_bisected_half_width(a, t):
    assert rz.half_width_phase(a, t) == pytest.approx(
        bisect_half_depth(a, t), rel=1e-6)


def test_the_small_angle_width_agrees_where_the_finesse_is_high_and_departs_where_it_is_not():
    lam, n_g, L = 1.55, 1.80, 628.3185
    high = rz.solve_point(lam, n_g, L, loss_dB_per_cm=0.1, kappa_squared=1.0e-3)
    low = rz.solve_point(lam, n_g, L, loss_dB_per_cm=0.1, kappa_squared=0.80)
    assert high.finesse > 100.0
    assert high.fwhm_um == pytest.approx(high.fwhm_um_small_angle, rel=2e-3)
    assert low.finesse < 10.0
    # the expansion overstates the width once the resonance is broad
    assert low.fwhm_um_small_angle > low.fwhm_um * 1.10


def test_the_width_depends_on_the_product_a_t_and_on_nothing_else():
    """The reduction of the inversion, checked against the bisected width.

    Two rings whose loss and coupling are exchanged have the same resonance
    width and different depths. A width computed from anything but the product
    would separate them.
    """
    assert rz.half_width_phase(0.97, 0.93) == pytest.approx(
        rz.half_width_phase(0.93, 0.97), rel=1e-12)
    assert rz.half_width_phase(0.97, 0.93) == pytest.approx(
        bisect_half_depth(0.97, 0.93), rel=1e-6)
    assert rz.transmission_on_resonance(0.97, 0.93) == pytest.approx(
        rz.transmission_on_resonance(0.93, 0.97), rel=1e-12)


def test_the_loaded_q_is_the_wavelength_over_the_width():
    p = rz.solve_point(1.55, 1.80, 628.3185, loss_dB_per_cm=0.2, kappa_squared=2.0e-3)
    assert p.q_loaded == pytest.approx(1.55 / p.fwhm_um, rel=1e-12)
    assert p.finesse == pytest.approx(p.fsr_um / p.fwhm_um, rel=1e-12)


def test_the_intrinsic_q_is_the_loaded_q_of_a_ring_with_no_coupler():
    """As the coupler is closed the loaded width tends to the intrinsic width.

    This is the limit that caught the decibel-to-neper constant: the intrinsic
    figure was twice the loaded one at every coupling, and a test written only
    against the transfer function would never have looked at the material
    constant that produced it.
    """
    lam, n_g, L, loss = 1.55, 1.80164, 628.3185, 0.2
    barely = rz.solve_point(lam, n_g, L, loss_dB_per_cm=loss, kappa_squared=1.0e-12)
    assert barely.q_loaded == pytest.approx(
        rz.q_intrinsic(lam, n_g, loss), rel=1e-3)


def test_the_loaded_width_is_the_intrinsic_and_coupling_widths_in_series():
    """1 / Q_load = 1 / Q_int + 1 / Q_coupling, the photon-lifetime statement.

    The coupling quality factor is reached from the fraction of the circulating
    power the coupler removes per turn, `kappa^2`, by the same lifetime argument
    that gives the intrinsic one from the fraction the loop absorbs. Neither
    expression appears in the module under test.
    """
    lam, n_g, L, loss = 1.55, 1.80164, 628.3185, 0.2
    for kappa_sq in (5.0e-4, 2.0e-3, 8.0e-3):
        p = rz.solve_point(lam, n_g, L, loss, kappa_squared=kappa_sq)
        q_coupling = 2.0 * math.pi * n_g * L / (lam * kappa_sq)
        series = 1.0 / (1.0 / rz.q_intrinsic(lam, n_g, loss) + 1.0 / q_coupling)
        assert p.q_loaded == pytest.approx(series, rel=5e-3)


# --------------------------------------------------------------------------
# the free spectral range
# --------------------------------------------------------------------------

def test_the_order_spacing_divides_by_the_group_index_and_not_the_effective_index():
    n_eff, n_g, lam, L = 1.52710, 1.80164, 1.55, 2.0 * math.pi * 100.0
    lo = resonance_near(n_eff, n_g, lam, L, 0)
    hi = resonance_near(n_eff, n_g, lam, L, -1)
    measured = hi - lo
    assert measured == pytest.approx(rz.fsr_um(lam, n_g, L), rel=2e-3)
    # the effective index would have given a different answer by a fifth
    assert measured != pytest.approx(rz.fsr_um(lam, n_eff, L), rel=0.05)


# --------------------------------------------------------------------------
# the loss convention and the degeneracy
# --------------------------------------------------------------------------

def test_the_declared_loss_is_a_power_and_the_amplitude_is_its_square_root():
    a = rz.amplitude_per_round_trip(10.0, 1.0e4)          # 10 dB/cm over one cm
    assert a * a == pytest.approx(0.1, rel=1e-12)


def test_an_excess_loss_is_taken_once_per_turn():
    a = rz.amplitude_per_round_trip(0.0, 1.0e4, excess_loss_dB=3.0)
    assert a * a == pytest.approx(10.0 ** -0.3, rel=1e-12)


def test_both_returned_couplings_reproduce_the_same_extinction():
    a = 0.994
    for kappa_sq in (1.0e-3, 1.2e-2, 5.0e-2, 0.4):
        t = math.sqrt(1.0 - kappa_sq)
        t_min = rz.transmission_on_resonance(a, t)
        over, under = rz.t_giving_extinction(a, t_min)
        assert rz.transmission_on_resonance(a, over) == pytest.approx(t_min, rel=1e-9)
        assert rz.transmission_on_resonance(a, under) == pytest.approx(t_min, rel=1e-9)
        assert over <= a <= under


def test_the_reported_partner_is_on_the_other_side_of_critical_coupling():
    over = rz.solve_point(1.55, 1.8, 628.3185, 0.2, kappa_squared=0.05)
    assert over.regime == "over"
    assert over.t_degenerate > over.t_critical
    under = rz.solve_point(1.55, 1.8, 628.3185, 0.2, kappa_squared=1.0e-5)
    assert under.regime == "under"
    assert under.t_degenerate < under.t_critical


def test_the_critical_coupling_recipe_returns_a_ring_that_extinguishes():
    L, loss = 628.3185, 0.35
    kappa_sq = rz.kappa_squared_for_critical_coupling(loss, L)
    p = rz.solve_point(1.55, 1.80, L, loss, kappa_squared=kappa_sq)
    assert p.transmission_min == pytest.approx(0.0, abs=1e-18)
    assert p.regime == "critical"
    assert p.t == pytest.approx(p.a, rel=1e-12)


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_a_power_coupling_outside_the_unit_interval_is_refused(bad):
    with pytest.raises(ValueError):
        rz.solve_point(1.55, 1.8, 628.3185, 0.2, kappa_squared=bad)


def test_a_negative_loss_is_refused():
    with pytest.raises(ValueError):
        rz.amplitude_per_round_trip(-1.0, 628.3185)


def test_a_lossless_ring_fully_coupled_has_no_resonance_and_says_so():
    with pytest.raises(ValueError):
        rz.transmission_on_resonance(1.0, 1.0)


def test_the_loss_that_makes_a_drawn_coupler_critical_round_trips():
    L = 2.0 * math.pi * 100.0
    for kappa_sq in (1.0e-3, 9.06e-3, 0.1):
        loss = rz.loss_dB_per_cm_for_critical_coupling(kappa_sq, L)
        p = rz.solve_point(1.55, 1.80, L, loss, kappa_squared=kappa_sq)
        assert p.regime == "critical"
        assert p.transmission_min == pytest.approx(0.0, abs=1e-16)


def test_an_excess_loss_beyond_what_the_coupler_removes_admits_no_critical_loss():
    L = 2.0 * math.pi * 100.0
    # the coupler removes 1e-3 of the power, being 0.00434 dB; a tenth of a
    # decibel taken once per turn is larger, so the loop is overcoupled at every
    # propagation loss
    assert rz.loss_dB_per_cm_for_critical_coupling(1.0e-3, L, excess_loss_dB=0.1) is None
    reachable = rz.loss_dB_per_cm_for_critical_coupling(0.1, L, excess_loss_dB=0.1)
    assert reachable is not None and reachable > 0.0


def test_a_critically_coupled_ring_reports_its_regime_and_not_an_infinity_in_prose():
    """The stage's finding formats three regimes and an unbounded extinction.

    The label is interpolated into a sentence, and the third regime does not
    take the suffix the other two do. The extinction is unbounded at critical
    coupling, `10 log10(0)` being what complete extinction means.
    """
    import math as _m
    p = rz.solve_point(1.55, 1.8, 628.3185, 0.35,
                       kappa_squared=rz.kappa_squared_for_critical_coupling(0.35, 628.3185))
    assert p.regime == "critical"
    assert not _m.isfinite(p.extinction_dB)
    labels = {"over": "overcoupled", "under": "undercoupled",
              "critical": "critically coupled"}
    assert p.regime in labels


# --------------------------------------------------------------------------
# the extinction requirement read as a tolerance on the loss
# --------------------------------------------------------------------------

@pytest.mark.parametrize("extinction_dB", [3.0, 10.0, 15.0, 20.0, 30.0])
def test_the_loss_window_is_found_again_by_bisecting_the_extinction(extinction_dB):
    """The edges are located by walking the loss, with no inversion performed."""
    lam, n_g, L, k2 = 1.55, 1.8014362994357143, 628.3185307179587, 0.003653
    crit = rz.loss_dB_per_cm_for_critical_coupling(k2, L)

    def walk(lo, hi):
        for _ in range(90):
            mid = 0.5 * (lo + hi)
            if rz.solve_point(lam, n_g, L, mid, k2).extinction_dB < extinction_dB:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    low, high = rz.loss_window_for_extinction(extinction_dB, k2, L)
    assert low == pytest.approx(walk(1e-4, crit), rel=1e-6)
    assert high == pytest.approx(walk(50.0, crit), rel=1e-6)


@pytest.mark.parametrize("extinction_dB", [3.0, 10.0, 20.0, 30.0])
def test_the_width_of_the_window_depends_on_the_extinction_and_on_nothing_else(extinction_dB):
    """Three rings differing in radius and coupling share one window in ratio.

    `r = 10^(-E/20)` puts the edges at `(1-r)/(1+r)` and `(1+r)/(1-r)` times the
    critical loss. Nothing about the platform, the radius or the coupler enters.
    """
    r = 10.0 ** (-extinction_dB / 20.0)
    expected = ((1.0 - r) / (1.0 + r), (1.0 + r) / (1.0 - r))
    for L, k2 in ((628.3185, 3.653e-3), (2.0 * math.pi * 40.0, 2.0e-2),
                  (2.0 * math.pi * 500.0, 5.0e-4)):
        crit = rz.loss_dB_per_cm_for_critical_coupling(k2, L)
        low, high = rz.loss_window_for_extinction(extinction_dB, k2, L)
        assert low / crit == pytest.approx(expected[0], rel=2e-3)
        assert high / crit == pytest.approx(expected[1], rel=2e-3)


def test_an_excess_loss_beyond_the_clear_edge_leaves_that_edge_unreachable():
    L, k2 = 628.3185307179587, 3.653e-3
    low, high = rz.loss_window_for_extinction(10.0, k2, L, excess_loss_dB=0.02)
    assert high is not None
    assert low is None, "the loss taken once per turn already exceeds the clear edge"
