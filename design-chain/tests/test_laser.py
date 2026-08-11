"""Laser rate equations, against closed forms and limits.

Each test holds an expression against a case in which it can be evaluated by
hand, or against a limit whose value is known independently. None pins a
previous numerical output.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from picchain import laser as ls


# --- the composite cavity --------------------------------------------------

def test_a_round_trip_that_loses_one_neper_gives_a_lifetime_of_one_round_trip():
    assert abs(ls.photon_lifetime_s(50e-12, math.exp(-1.0)) - 50e-12) < 1e-24


def test_the_lifetime_is_the_round_trip_over_the_loss_in_nepers():
    tau_p = ls.photon_lifetime_s(60e-12, math.exp(-3.0))
    assert abs(tau_p - 20e-12) < 1e-24


def test_a_lossless_or_a_gaining_round_trip_is_refused():
    for bad in (0.0, 1.0, 1.5, -0.2):
        with pytest.raises(ValueError):
            ls.photon_lifetime_s(50e-12, bad)


def test_a_longer_lifetime_is_a_higher_Q():
    q1 = ls.cold_cavity_Q(10e-12, 1.93e14)
    q2 = ls.cold_cavity_Q(20e-12, 1.93e14)
    assert abs(q2 / q1 - 2.0) < 1e-12


# --- threshold -------------------------------------------------------------

def test_threshold_density_is_transparency_plus_the_loss_over_the_modal_gain():
    tau_p, v_g, G, F, a, n_tr = 20e-12, 8.33e9, 0.06, 0.417, 2.5e-16, 1e18
    n_th = ls.threshold_carrier_density_per_cm3(tau_p, v_g, G, F, a, n_tr)
    expect = n_tr + 1.0 / (F * G * v_g * a * tau_p)
    assert abs(n_th / expect - 1.0) < 1e-12


def test_at_threshold_the_modal_gain_exactly_balances_the_photon_decay():
    """The condition the expression is derived from, checked as an identity."""
    tau_p, v_g, G, F, a, n_tr = 20e-12, 8.33e9, 0.06, 0.417, 2.5e-16, 1e18
    n_th = ls.threshold_carrier_density_per_cm3(tau_p, v_g, G, F, a, n_tr)
    gain_rate = F * G * v_g * a * (n_th - n_tr)
    assert abs(gain_rate - 1.0 / tau_p) / (1.0 / tau_p) < 1e-12


def test_a_shorter_photon_lifetime_demands_more_carriers():
    args = (8.33e9, 0.06, 0.417, 2.5e-16, 1e18)
    lo = ls.threshold_carrier_density_per_cm3(40e-12, *args)
    hi = ls.threshold_carrier_density_per_cm3(10e-12, *args)
    assert hi > lo


def test_threshold_current_is_the_charge_needed_per_carrier_lifetime():
    n_th, V, tau_c = 2e18, 2e-10, 1e-9
    I = ls.threshold_current_A(n_th, V, tau_c, 1.0)
    assert abs(I - ls.Q_E * V * n_th / tau_c) < 1e-24


def test_imperfect_injection_raises_the_threshold_in_proportion():
    a = ls.threshold_current_A(2e18, 2e-10, 1e-9, 1.0)
    b = ls.threshold_current_A(2e18, 2e-10, 1e-9, 0.5)
    assert abs(b / a - 2.0) < 1e-12


# --- above threshold -------------------------------------------------------

def test_no_photons_below_threshold():
    assert ls.photon_density_per_cm3(0.05, 0.08, 20e-12, 2e-10) == 0.0
    assert ls.photon_density_per_cm3(0.08, 0.08, 20e-12, 2e-10) == 0.0


def test_photon_density_is_linear_in_the_excess_current():
    f = lambda I: ls.photon_density_per_cm3(I, 0.08, 20e-12, 2e-10)
    assert abs(f(0.12) / f(0.10) - 2.0) < 1e-12


def test_a_perfect_laser_converts_each_electron_into_one_photon_of_its_own_energy():
    """The quantum limit: at unit injection and unit output coupling the slope is
    the photon energy in volts, which at 1.55 um is 0.800 V."""
    nu = ls.C0 / 1.55e-6
    slope = ls.slope_efficiency_W_per_A(nu, 1.0, 1.0)
    assert abs(slope - ls.H_PLANCK * nu / ls.Q_E) < 1e-15
    assert abs(slope - 0.7999) < 1e-3


def test_the_light_current_curve_agrees_with_the_slope_efficiency():
    """Power computed from the photon density must equal threshold current times
    slope, these being two routes to the same quantity."""
    tau_p, V, nu, eta_out, eta_i = 20e-12, 2e-10, ls.C0 / 1.55e-6, 0.256, 0.8
    I_th = 0.078
    for I in (0.10, 0.15, 0.20):
        S = ls.photon_density_per_cm3(I, I_th, tau_p, V, eta_i)
        P = ls.output_power_W(S, V, tau_p, nu, eta_out)
        expect = ls.slope_efficiency_W_per_A(nu, eta_out, eta_i) * (I - I_th)
        assert abs(P - expect) / expect < 1e-12


def test_the_output_coupling_fraction_is_bounded_by_unity():
    assert ls.output_coupling_fraction(4.0, 14.0) == pytest.approx(4.0 / 14.0)
    with pytest.raises(ValueError):
        ls.output_coupling_fraction(4.0, 0.0)


# --- small signal ----------------------------------------------------------

def test_the_relaxation_oscillation_scales_as_the_square_root_of_the_power():
    f = lambda S: ls.relaxation_oscillation_Hz(S, 20e-12, 8.33e9, 0.06, 0.417, 2.5e-16)
    assert abs(f(4e16) / f(1e16) - 2.0) < 1e-12
    assert f(0.0) == 0.0


def test_the_relaxation_oscillation_is_the_geometric_mean_of_two_rates():
    S, tau_p, v_g, G, F, a = 3.66e16, 20.34e-12, 8.33e9, 0.06, 0.417, 2.5e-16
    f_r = ls.relaxation_oscillation_Hz(S, tau_p, v_g, G, F, a)
    expect = math.sqrt(F * G * v_g * a * S / tau_p) / (2 * math.pi)
    assert abs(f_r - expect) < 1e-3


def test_the_undamped_bandwidth_is_the_textbook_multiple_of_the_oscillation():
    """With no damping the two-pole response reaches half power at
    sqrt(1 + sqrt(2)) = 1.5538 times f_r."""
    f_r = 2.0e9
    f3 = ls.modulation_bandwidth_Hz(f_r, 0.0)
    assert abs(f3 / f_r - math.sqrt(1.0 + math.sqrt(2.0))) < 1e-9
    assert abs(f3 / f_r - 1.5538) < 1e-3


def test_damping_reduces_the_bandwidth():
    f_r = 2.0e9
    assert ls.modulation_bandwidth_Hz(f_r, 5e9) < ls.modulation_bandwidth_Hz(f_r, 0.0)


def test_the_K_factor_reduces_to_the_photon_lifetime_without_compression():
    K = ls.damping_K_factor_s(20e-12, 8.33e9, 2.5e-16, 0.0)
    assert abs(K - 4 * math.pi**2 * 20e-12) < 1e-24


def test_damping_is_the_K_factor_times_the_square_of_the_frequency():
    K = ls.damping_K_factor_s(20e-12, 8.33e9, 2.5e-16, 1.5e-17)
    g = ls.damping_rate_per_s(2e9, K, 1e-9)
    assert abs(g - (K * 4e18 + 1e9)) < 1e-3


# --- intensity noise -------------------------------------------------------

def test_the_noise_peaks_at_the_relaxation_oscillation():
    f = np.linspace(1e6, 2e10, 4001)
    f_r = 1.54e9
    rin = ls.rin_spectrum_per_Hz(f, f_r, 3.6e9, 3.66e16, 20.3e-12, 1e-9, 1e-4, 1.94e18)
    assert abs(f[int(np.argmax(rin))] - f_r) < 0.1 * f_r


def test_the_noise_falls_as_the_fourth_power_above_the_peak():
    f = np.array([8e9, 16e9])
    rin = ls.rin_spectrum_per_Hz(f, 1.54e9, 3.6e9, 3.66e16, 20.3e-12, 1e-9, 1e-4, 1.94e18)
    # far above f_r the denominator goes as w^4 and the numerator as w^2
    assert 3.0 < rin[0] / rin[1] < 5.0


def test_more_power_is_less_relative_noise():
    f = np.linspace(1e6, 2e10, 501)
    a = ls.rin_spectrum_per_Hz(f, 1.5e9, 3.6e9, 1e16, 20e-12, 1e-9, 1e-4, 2e18)
    b = ls.rin_spectrum_per_Hz(f, 1.5e9, 3.6e9, 4e16, 20e-12, 1e-9, 1e-4, 2e18)
    assert np.nanmax(b) < np.nanmax(a)


# --- optical feedback ------------------------------------------------------

def test_improving_the_coating_strengthens_the_feedback():
    """The coupling rate grows as the chip facet is suppressed, which is the
    intended behaviour of an external-cavity laser rather than a defect."""
    weak = ls.feedback_rate_per_s(1e-2, 0.48, 24e-12)
    strong = ls.feedback_rate_per_s(1e-4, 0.48, 24e-12)
    assert strong > weak
    # 1/sqrt(R2) from the field ratio, times (1 - R2) from the transmission of
    # the facet the returned field must cross. The second is what makes the
    # ratio 10.10 rather than 10.00.
    expect = (1 - 1e-4) / (1 - 1e-2) * math.sqrt(1e-2 / 1e-4)
    assert abs(strong / weak - expect) < 1e-9
    assert abs(expect - 10.1) < 1e-3


def test_C_is_linear_in_the_external_delay_and_carries_the_alpha_factor():
    k = ls.feedback_rate_per_s(1e-4, 0.48, 24e-12)
    assert abs(ls.feedback_C(k, 60e-12, 3.0) / ls.feedback_C(k, 30e-12, 3.0) - 2.0) < 1e-12
    ratio = ls.feedback_C(k, 30e-12, 3.0) / ls.feedback_C(k, 30e-12, 0.0)
    assert abs(ratio - math.sqrt(10.0)) < 1e-12


def test_a_facet_that_is_not_a_reflector_is_refused():
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError):
            ls.feedback_rate_per_s(bad, 0.48, 24e-12)


def test_the_margin_is_the_ratio_of_the_two_reflectors_in_decibels():
    assert abs(ls.coherence_collapse_margin_dB(0.48, 4.8e-3) - 20.0) < 1e-9


def test_a_well_coated_facet_reaches_the_stable_strong_feedback_regime():
    """The regime an external-cavity laser is designed to occupy. It is reached
    by suppressing the chip facet, not by weakening the feedback."""
    regime, _ = ls.feedback_regime(307.0, 0.484, 1e-4)
    assert regime == "V"


def test_a_degraded_coating_falls_into_coherence_collapse():
    regime, _ = ls.feedback_regime(43.0, 0.484, 5e-3)
    assert regime == "IV"


def test_weak_feedback_leaves_one_solution_and_is_stable():
    regime, _ = ls.feedback_regime(0.5, 1e-6, 1e-4)
    assert regime == "I"


def test_the_compound_mode_spacing_is_the_inverse_round_trip():
    assert abs(ls.external_cavity_mode_spacing_Hz(57.57e-12) - 1.0 / 57.57e-12) < 1.0
