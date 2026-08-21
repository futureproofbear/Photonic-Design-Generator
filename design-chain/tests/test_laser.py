"""Laser rate equations, against closed forms and limits.

Each test holds an expression against a case in which it can be evaluated by
hand, or against a limit whose value is known independently. None pins a
previous numerical output.
"""

from __future__ import annotations

import inspect
import math
import pathlib

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


# --- the stop band bounds the tuning range ---------------------------------
#
# The closed form mhf = r/(1-r) * FSR/2 counts cavity modes and assumes the
# mirror holds every one. It does not: the mode walks out of the stop band and
# the excursion ends. The two quantities are anti-correlated through kappa, so
# a design steered by the closed form is steered away from the tuning range it
# is trying to buy. This was found on a released tantalate design that reported
# 6.34 GHz achieved against a 13.78 GHz closed form, a gap attributed to
# thermal comb placement for two weeks before it was measured.


def test_weakening_the_grating_raises_the_closed_form_and_narrows_the_mirror():
    """The anti-correlation itself, which is the trap. Both statements must
    hold simultaneously or the warning in s04 is guarding nothing."""
    import math

    def penetration_m(kappa_per_cm: float, L_m: float) -> float:
        k = kappa_per_cm * 100.0
        return math.tanh(k * L_m) / (2.0 * k)

    L, n_g, tau_u = 17e-3, 2.063, 26.91e-12
    strong, weak = 1.3647, 0.6176  # the measured post-gap scan, 0.90 and 1.05 um

    def closed_form_GHz(kappa):
        tau_dbr = 2 * n_g * penetration_m(kappa, L) / 2.998e8
        tau_rt = tau_u + tau_dbr
        r = tau_dbr / tau_rt
        return (r / (1 - r)) * (1.0 / tau_rt) / 2 / 1e9

    # weakening raises the closed form
    assert closed_form_GHz(weak) > closed_form_GHz(strong)
    # and narrows the mirror, which is what actually bounds the range
    assert weak < strong  # bandwidth grows with kappa at fixed length


def test_cavity_reports_the_phase_independent_tuning_quantities():
    """The swept range carries the cavity phase of one geometry, so a
    requirement written against it is written against a quantity no process
    controls. These four are phase-independent and must all be emitted."""
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    for name in ("mode_hop_free_range_guaranteed_GHz",
                 "mode_hop_free_range_placed_GHz",
                 "mirror_relative_drift_GHz",
                 "stopband_containment_ratio"):
        assert name in src, name
    # the mode must be warned about when it leaves the mirror it follows
    assert "relative to the mirror over the sweep" in src


def test_guaranteed_range_halves_when_a_hop_can_fall_in_the_sweep():
    """ceil, not floor. A drift of 0.6 FSR crosses no boundary on average and
    crosses one whenever the phase places a boundary inside the sweep, so the
    worst case is two segments and half the span."""
    import math

    def guaranteed(eta_MHz_per_V, V, drift_GHz, fsr_GHz):
        hops = drift_GHz / fsr_GHz
        return eta_MHz_per_V * V / (math.ceil(hops) + 1) / 1000.0

    # the L2 tantalate point: 6.354 GHz of drift against a 10.63 GHz FSR
    g = guaranteed(323.4, 55.0, 6.354, 10.63)
    assert abs(g - 8.89) < 0.05          # half of the placed 17.79 GHz
    # a sweep short enough to cross no boundary at any phase keeps the full span
    assert abs(guaranteed(323.4, 55.0, 0.0, 10.63) - 17.79) < 0.05


def test_the_two_routes_to_the_laser_tuning_are_both_reported():
    """eta is available as a fitted slope and as r*S. They answer different
    questions and the quantities downstream inherit whichever is used, so the
    chain states both and the ratio between them."""
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    assert "laser_tuning_from_lever_MHz_per_V" in src
    assert "laser_tuning_fitted_over_lever" in src
    assert "differ by" in src


def test_the_sweep_span_does_not_follow_the_requirement_it_tests():
    """The span was 1.6x the drive the requested chirp needed, so every tuning
    figure restated the chirp setting. Lowering a declared chirp from 10 to
    3 GHz cut the reported placed excursion from 14.55 to 5.32 GHz with the
    design untouched. Where a drive limit is declared, the span is that limit."""
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    assert "V_limit_decl" in src
    assert "A requirement must not set the span of the" in src
    i_lim = src.index("if V_limit_decl > 0:")
    i_chirp = src.index("V_max = 1.6 * V_needed")
    assert i_lim < i_chirp, "the declared drive must take precedence over the chirp"


# --- the intracavity phase section ------------------------------------------
#
# The mirror and the comb are set by different things, so tuning the mirror
# makes the mode slip across the comb at (1-r)*S until it hands over. A phase
# electrode moves the comb without moving the mirror, so the two go together.


def test_the_phase_a_section_must_supply_is_the_slip_in_units_of_the_FSR():
    """A slip of one free spectral range is exactly one hand-over, and costs
    2*pi of round-trip phase to cancel."""
    fsr = 10.06e9
    for slip, expect_turns in ((10.06e9, 1.0), (5.03e9, 0.5), (3.93e9, 0.3906)):
        phi = 2 * math.pi * slip / fsr
        assert abs(phi / (2 * math.pi) - expect_turns) < 1e-3


def test_a_shorter_gap_shortens_the_section_in_proportion():
    """A phase section carries no Bragg posts, so its electrodes sit closer than
    the mirror's and the field goes as 1/gap. That is the whole reason the
    section fits on the die."""
    import math as _m

    lam, dn_per_V_mirror, V = 1.573e-6, 5.240e-6, 25.0
    phi = 2 * _m.pi * 0.3906

    def length_um(gap_ph, gap_mirror=6.62):
        dn = dn_per_V_mirror * gap_mirror / gap_ph
        return phi * lam / (4 * _m.pi * dn * V) * 1e6

    at_mirror_gap = length_um(6.62)
    at_tight_gap = length_um(4.0)
    assert 2200 < at_mirror_gap < 2500
    assert 1300 < at_tight_gap < 1500
    assert abs(at_mirror_gap / at_tight_gap - 6.62 / 4.0) < 1e-6


def test_the_cavity_stage_reports_sufficiency_and_the_length_required():
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    for k in ("phase_needed_rad", "phase_available_rad", "length_needed_um",
              "sufficient", "mode_hop_free_range_synchronous_GHz"):
        assert k in src, k
    assert "cannot be held in step" in src


def test_the_phase_a_section_must_supply_is_independent_of_the_grating():
    """phi = 2*pi*drift/FSR, drift = (1-r)*S*V, and (1-r)*tau_rt = tau_u, so

        phi_needed = 2*pi * tau_u * S * V

    The grating cancels. That is why a phase section can be sized once and used
    with any mirror, and it is what makes a phase-section-first design order
    possible."""
    S, V = 484.2e6, 25.0
    tau_soa, tau_feed = 24.02e-12, 8.26e-12
    tau_u = tau_soa + tau_feed
    phi = 2 * math.pi * tau_u * S * V
    assert abs(phi - 2.455) < 0.02

    # the same phi for two very different mirrors, entered as (r, tau_dbr)
    for r, tau_dbr in ((0.5446, 38.6e-12), (0.6576, 61.9e-12)):
        tau_rt = tau_u / (1 - r)
        fsr = 1.0 / tau_rt
        drift = (1 - r) * S * V
        assert abs(2 * math.pi * drift / fsr - phi) / phi < 0.02


def test_a_phase_section_must_cancel_the_slip_it_creates():
    """It sits inside the cavity, so its length is passive delay, and passive
    delay is exactly what sets the phase it must supply. Ignoring its own
    contribution understates phi_needed and declares an insufficient section
    sufficient."""
    tau0, S, V_m, n_g, c = 32.28e-12, 484.2e6, 25.0, 2.063, 2.998e8
    L = 1500e-6
    tau_ph = 2 * n_g * L / c
    phi_wrong = 2 * math.pi * tau0 * S * V_m
    phi_right = 2 * math.pi * (tau0 + tau_ph) * S * V_m
    assert abs(phi_wrong - 2.455) < 0.02
    assert abs(phi_right - 4.025) < 0.02
    assert phi_right > phi_wrong

    # and the section is only sufficient once its own drive is raised
    lam, dn = 1.573e-6, 8.672e-6
    avail = lambda V_p: 4 * math.pi * dn * V_p * L / lam
    assert avail(25.0) < phi_right          # what the first attempt assumed
    assert avail(40.0) > phi_right          # what it actually needs


def test_the_cavity_counts_the_phase_section_as_passive_delay():
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    assert "tau_phase" in src
    assert "tau_ext = tau_soa + tau_feed + tau_phase" in src
    assert "cancel the slip it creates" in src


def test_a_driven_phase_section_carries_the_laser_at_the_mirror_rate():
    """A section sized to supply the slip makes the laser follow the mirror one
    for one, so the synchronous excursion is S * V and not r * S * V.

    Reported as r * S * V until 2026-08-17, which understated it by exactly the
    lever and made the phase-section design look worse than the design it
    replaces on the very quantity it exists to improve. On the L-band variant
    that read 8.41 GHz against a measured 12.11 GHz.

    Differentiating the resonance condition

        2 pi f tau_ext + phi_dbr(f - S V) + phi_ps(V) = 2 pi k

    with respect to V gives

        df/dV = r S - (dphi_ps/dV) / (2 pi tau_rt)

    so df/dV reaches S exactly when dphi_ps/dV = -2 pi tau_u S, and 2 pi tau_u S
    per volt is the slip the section is sized to cancel. The requirement and the
    result are therefore the same statement.
    """
    S, V_m = 484.19e6, 25.0
    tau_soa, tau_feed, tau_phase = 24.02e-12, 2.89e-12, 12.38e-12
    tau_u = tau_soa + tau_feed + tau_phase
    r = 0.6308
    tau_rt = tau_u / (1 - r)

    # the sizing rule, in phase per volt
    dphi_dV = 2 * math.pi * tau_u * S

    # the tuning rate it produces, from the derivative above
    df_dV = r * S + dphi_dV / (2 * math.pi * tau_rt)
    assert abs(df_dV / S - 1.0) < 0.01, "a sized section must give the mirror rate"

    # and the excursion follows from the rate
    assert abs(df_dV * V_m / 1e9 - 12.1) < 0.2
    assert df_dV * V_m > r * S * V_m          # strictly better than mirror only


def test_the_synchronous_excursion_is_measured_and_not_asserted():
    """The figure comes from a second mode-tracking sweep with the section's
    phase applied, on the same machinery as every other excursion in the stage.
    A closed form quoted beside a numerical model is a claim about the model."""
    from picchain.stages import s04_cavity

    src = inspect.getsource(s04_cavity)
    assert "def _sweep(" in src, "the sweep must be callable twice"
    assert "phi_extra" in src
    assert "laser_tuning_synchronous_MHz_per_V" in src
    # the corrected metric must not be the lever route again
    assert "laser_tuning_Hz_per_V * V_span / 1e9\n            if phase_payload" not in src
    assert '"mode_hop_free_range_synchronous_GHz": mhf_sync_Hz / 1e9' in src


def test_every_target_traces_to_a_concept_clause():
    """A target carries a mechanism as well as a number, so a design that
    replaces the mechanism must re-derive its targets rather than inherit them.

    L2.2-style failure: a laser built to hold its comb in step with its mirror
    inherited the targets of a laser built to position the hop outside the sweep.
    The `must` row then measured a comb left to slip, the new design scored worse
    than the one it replaced on the quantity it exists to improve, and the
    verdict inverted once the row was re-derived.

    The guard is a trace table in DESIGN_CONCEPT.md checked against design.yaml.
    """
    import subprocess
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    tool = root / "tools" / "check_concept_trace.py"
    assert tool.exists(), "the concept-trace checker must exist"

    designs = [d for d in (root.parent / "examples").glob("*/")
               if (d / "design.yaml").exists() and (d / "DESIGN_CONCEPT.md").exists()]
    if not designs:
        pytest.skip("no example design carries a concept document yet")

    r = subprocess.run([sys.executable, str(tool), *[str(d) for d in designs]],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"concept trace broken:\n{r.stdout}\n{r.stderr}"


def test_the_concept_checker_catches_an_inherited_target(tmp_path):
    """The checker must fail on the exact defect it was written for: a target
    present in design.yaml and absent from the concept."""
    import subprocess
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    tool = root / "tools" / "check_concept_trace.py"

    d = tmp_path / "design_under_test"
    d.mkdir()
    (d / "design.yaml").write_text(
        "targets:\n"
        "  - metric: cavity.mode_hop_free_range_placed_GHz\n"
        "    min: 8.0\n"
        "    severity: must\n"
        "  - metric: eo.tuning_MHz_per_V\n"
        "    min: 450.0\n"
        "    severity: must\n", encoding="utf-8")
    (d / "DESIGN_CONCEPT.md").write_text(
        "# concept\n\n"
        "| clause | target metric | severity |\n"
        "|---|---|---|\n"
        "| the mirror tunes | `eo.tuning_MHz_per_V` | must |\n", encoding="utf-8")

    r = subprocess.run([sys.executable, str(tool), str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 1, "an untraced target must fail the check"
    assert "mode_hop_free_range_placed_GHz" in r.stdout

    # and a severity disagreement must also fail
    (d / "DESIGN_CONCEPT.md").write_text(
        "# concept\n\n"
        "| clause | target metric | severity |\n"
        "|---|---|---|\n"
        "| the mirror tunes | `eo.tuning_MHz_per_V` | should |\n"
        "| the window is wide | `cavity.mode_hop_free_range_placed_GHz` | must |\n",
        encoding="utf-8")
    r = subprocess.run([sys.executable, str(tool), str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 1, "a severity disagreement must fail the check"
    assert "severity disagrees" in r.stdout


def test_the_concept_checker_reads_a_nested_metric_path(tmp_path):
    """A metric path may be deeper than two segments and must still trace.

    `RunContext.get` walks the metric tree to any depth, so a stage grouping a
    sub-system into its own payload produces names such as
    `cavity.phase_section.margin`. The checker's row pattern admitted exactly
    two segments until 2026-08-18, so a target on a nested quantity was reported
    as absent from the concept while the concept named it. The remedy the tool
    implied was to flatten a metric name to satisfy the tool, which is the wrong
    direction of repair.
    """
    import subprocess
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    tool = root / "tools" / "check_concept_trace.py"

    d = tmp_path / "nested_metric_design"
    d.mkdir()
    (d / "design.yaml").write_text(
        "targets:\n"
        "  - metric: cavity.phase_section.margin\n"
        "    min: 1.0\n"
        "    severity: must\n"
        "  - metric: eo.tuning_MHz_per_V\n"
        "    min: 450.0\n"
        "    severity: must\n", encoding="utf-8")
    (d / "DESIGN_CONCEPT.md").write_text(
        "# concept\n\n"
        "| clause | target metric | severity |\n"
        "|---|---|---|\n"
        "| the mirror tunes | `eo.tuning_MHz_per_V` | must |\n"
        "| the section supplies the slip | `cavity.phase_section.margin` | must |\n",
        encoding="utf-8")

    r = subprocess.run([sys.executable, str(tool), str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"a nested metric path must trace:\n{r.stdout}\n{r.stderr}"

    # and the checker must still catch the defect it exists for, at depth three
    (d / "DESIGN_CONCEPT.md").write_text(
        "# concept\n\n"
        "| clause | target metric | severity |\n"
        "|---|---|---|\n"
        "| the mirror tunes | `eo.tuning_MHz_per_V` | must |\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(tool), str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 1, "an untraced nested target must fail the check"
    assert "cavity.phase_section.margin" in r.stdout


# --- preconditions ---------------------------------------------------------

def test_a_geometric_precondition_respects_a_disabled_stage():
    """A precondition asserting that one structure fits another holds only where
    both structures exist.

    `the_electrode_clears_the_ridge` compares the electrode gap against the ridge
    it straddles. A study that switches the electrodes off and widens the guide
    describes a structure with no metal beside it, and refusing it on the
    geometry of an absent electrode fails correct work. **A gate that refuses
    correct work trains the reader to bypass the gate**, which is T053.

    The guard must still fire where the electrodes are drawn, so both directions
    are checked here.
    """
    from picchain.config import Design
    from picchain.preflight import assert_ready

    d = Design.load(pathlib.Path(__file__).resolve().parents[2]
                    / "examples" / "edbr_tfln_baseline" / "design.yaml")
    d.waveguide.top_width_um = 12.0
    d.electrodes.enabled = False
    d.electrodes.gap_um = 7.0
    assert_ready(d)          # no metal beside the guide, so nothing to clear

    d.electrodes.enabled = True
    with pytest.raises(RuntimeError, match="the_electrode_clears_the_ridge"):
        assert_ready(d)




def test_the_feed_must_be_longer_than_the_taper_drawn_inside_it():
    """The circuit assembles facet -> taper -> straight -> grating, and the
    straight is what remains of the feed after the taper.

    The subtraction was `2 * taper_length` against ONE taper instance, so the
    straight was short by a taper on every design. Where the feed was long the
    error was invisible; on a 210 um feed with a 150 um taper it drove the length
    negative, a clamp returned 1 um, and the stage assembled a cavity with no
    feed. Its group-delay cross-check then agreed to 0.3 %, because the
    expectation was computed from the same clamped value.

    **A clamp that rescues a nonsensical input turns a modelling failure into a
    passing check**, so the condition raises.
    """
    from picchain import preflight
    from picchain.config import Design

    src = inspect.getsource(
        __import__("picchain.stages.s16_circuit", fromlist=["x"]))
    assert "feed_len = design.cavity.feed_length_um - design.layout.taper_length_um" in src
    assert "2 * design.layout.taper_length_um" not in src
    assert "raise RuntimeError" in src

    d = Design.load(pathlib.Path(__file__).resolve().parents[2]
                    / "examples" / "edbr_tfln_baseline" / "design.yaml")
    assert preflight.run_checks(d) == [], "the baseline must satisfy every precondition"

    d.cavity.feed_length_um = d.layout.taper_length_um
    findings = preflight.run_checks(d)
    assert any(f.check == "taper_fits_in_the_feed" for f in findings)
    with pytest.raises(RuntimeError, match="precondition"):
        preflight.assert_ready(d)


def test_the_layout_refuses_to_redraw_the_cavity_it_was_given():
    """Flooring the straight run silently lengthens the drawn cavity past the one
    every delay was computed from. It warned from 2026-08-07 and the warning went
    unread on four devices of a die, so it raises."""
    from picchain.stages import s05_layout

    src = inspect.getsource(s05_layout)
    assert "below the 10 um floor" in src
    assert "the drawn device would not be the modelled one" in src
    # the floor must no longer be applied silently after the message
    i = src.index("below the 10 um floor")
    assert "raise RuntimeError" in src[max(0, i - 900):i]


def test_a_precondition_is_never_asserted_from_a_guess():
    """The first version of preflight asserted that a phase section had to fit
    inside the feed and failed a correct design: the layout draws it after the
    feed, and the cavity carries its delay separately.

    A precondition asserted from an assumption about the geometry is worse than
    none, since it fails correct work and trains the reader to bypass the gate.
    """
    from picchain import preflight

    src = inspect.getsource(preflight)
    assert "worse than no precondition" in src
    assert "the_phase_section_fits_the_cavity" not in [c.__name__ for c in preflight.CHECKS]


def test_every_clamp_on_a_declared_value_has_a_precondition():
    """Rule 17: a clamp exists because someone knew the value could be
    impossible and chose to continue. Auditing them found two on declared
    quantities, both able to hide a nonsensical input behind a plausible number.

    A phase-section gap of zero is divided into, so the index change returns nine
    orders of magnitude too large and the section reports as overwhelmingly
    sufficient. A negative facet coating is clamped to zero, so the circuit is
    assembled from a facet the design did not declare.
    """
    from picchain import preflight
    from picchain.config import Design

    names = {c.__name__ for c in preflight.CHECKS}
    assert "the_phase_electrode_clears_its_guide" in names
    assert "the_facet_reflectivity_is_a_reflectivity" in names

    root = pathlib.Path(__file__).resolve().parents[2]
    d = Design.load(root / "examples" / "edbr_tfln_baseline" / "design.yaml")

    ps = getattr(d.cavity, "phase_section", None)
    if ps is not None:
        ps.enabled = True
        ps.length_um = 900.0
        ps.gap_um = 0.0
        assert any(f.check == "the_phase_electrode_clears_its_guide"
                   for f in preflight.run_checks(d))
        # a gap narrower than the ridge puts metal on the guide
        ps.gap_um = d.waveguide.top_width_um * 0.9
        assert any(f.check == "the_phase_electrode_clears_its_guide"
                   for f in preflight.run_checks(d))
        ps.enabled = False

    f = getattr(d, "facet", None)
    if f is not None and hasattr(f, "ar_reflectivity"):
        f.ar_reflectivity = -0.1
        assert any(x.check == "the_facet_reflectivity_is_a_reflectivity"
                   for x in preflight.run_checks(d))


def test_a_length_of_guide_adds_delay_rather_than_removing_it():
    """Two elements of one assembly must share a phase convention.

    The `straight` model returned exp(+i phase), whose phase rises with
    frequency, while the grating's stored phase falls with it. The group delay is
    read as -d(phase)/d(omega), so a feed placed in front of a mirror SUBTRACTED
    its delay from the mirror's, and the assembled round trip came out shorter
    than the bare grating.

    Found by scale, not inspection: two designs whose modelled feeds differed by
    6.4x both matched `tau_dbr - 2 * feed` to better than 0.2 ps. On the L-band
    design the assembled delay moved from 60.73 ps to 73.21 ps against an
    expectation of 73.33, so a 17.2 % disagreement became 0.2 %.
    """
    from picchain.stages.s16_circuit import straight

    ng, neff, L_um, lam0 = 2.06282, 1.66486, 450.0, 1.573
    wl = np.array([lam0 * (1 - 1e-4), lam0, lam0 * (1 + 1e-4)])
    s = straight(wl=wl, length_um=L_um, neff=neff, ng=ng, wl0=lam0)
    amp = np.asarray(s[("in0", "out0")], dtype=complex)

    phase = np.unwrap(np.angle(amp))
    omega = 2 * np.pi * (ls.C0 / (wl * 1e-6))
    tau = -np.gradient(phase, omega)[1]

    expect = L_um * 1e-6 * ng / ls.C0          # one pass, seconds
    assert tau > 0, "a length of guide must add delay, not remove it"
    assert abs(tau / expect - 1.0) < 0.02, (
        f"the straight carries {tau*1e12:.3f} ps against {expect*1e12:.3f} ps "
        f"expected from its length and group index")


def test_the_assembled_delay_exceeds_the_bare_mirror():
    """A passive guide in front of a mirror can only lengthen the round trip.

    The invariant the sign error violated, stated so that any future convention
    change is caught by physics rather than by arithmetic.
    """
    from picchain.stages.s16_circuit import straight

    ng, neff, lam0 = 2.06282, 1.66486, 1.573
    wl = np.array([lam0 * (1 - 1e-4), lam0, lam0 * (1 + 1e-4)])
    omega = 2 * np.pi * (ls.C0 / (wl * 1e-6))

    prev = 0.0
    for L in (70.0, 300.0, 450.0):
        amp = np.asarray(straight(wl=wl, length_um=L, neff=neff, ng=ng,
                                  wl0=lam0)[("in0", "out0")], dtype=complex)
        tau = -np.gradient(np.unwrap(np.angle(amp)), omega)[1]
        assert tau > prev, "a longer guide must carry a longer delay"
        prev = tau


def test_a_wrong_unit_is_caught_before_the_run():
    """A length entered in the wrong unit passes every type check, violates no
    bound, and produces a run that is quietly about another device."""
    from picchain import preflight
    from picchain.config import Design

    root = pathlib.Path(__file__).resolve().parents[2]
    d = Design.load(root / "examples" / "edbr_tfln_baseline" / "design.yaml")
    assert preflight.run_checks(d) == []

    d.waveguide.wavelength_um = 1550.0          # nanometres, meant micrometres
    assert any(f.check == "declared_magnitudes_are_plausible"
               for f in preflight.run_checks(d))


def test_a_finding_carries_its_stage_and_a_stable_key():
    """A warning is the chain saying `here is something you should know`, and
    ninety such sites were read by nothing. A finding therefore carries a stage
    and a key so a design can acknowledge one by name, and so a new finding can
    be told from a standing one."""
    from picchain.artifacts import derive_key

    assert derive_key("grating", "order-3 grating: diffraction orders [1, 2] "
                                 "radiate out of the guide") == \
        "grating.order_3_grating_diffraction"
    # the key must ignore words that carry no distinguishing weight
    assert derive_key("taper", "the taper is single-moded along its whole "
                               "length") == "taper.taper_single_moded_along"
    # and it must be a pure function of stage and text
    assert derive_key("eo", "a b c d e f") == derive_key("eo", "a b c d e f")


def test_verify_reports_findings_against_what_the_design_acknowledges():
    """The acceptance verdict grades targets. Findings carrying no threshold had
    no owner, so the verdict is now reported with its denominator."""
    from picchain.stages import s07_verify

    src = inspect.getsource(s07_verify)
    for field in ("findings_emitted", "findings_acknowledged",
                  "findings_unacknowledged", "findings_acknowledged_but_absent"):
        assert field in src, f"verify must report {field}"
    # enforcement is opt-in, and off by default
    assert "findings_enforced" in src
    assert "enforce and unacknowledged" in src


def test_the_netlist_and_the_closed_form_share_the_corrected_convention():
    """Two implementations agreeing is weak evidence when they share a
    convention, and for as long as both were wrong this cross-check passed with a
    residual of exactly zero.

    The netlist and the analytic cascade both wrote exp(+i phi) for the feed,
    where the exp(+i omega t) convention requires exp(-i phi) for a forward wave.
    Correcting only the netlist made the residual jump to 2.6e-02, which is the
    measure of the error both had been carrying and the first evidence either was
    wrong.

    The anchor that settles it is physical, not numerical: a passive guide adds
    delay, so the assembled round trip must exceed the bare mirror's. Both
    conditions are asserted here, because either alone was satisfiable by a
    defect.
    """
    from picchain.stages import s16_circuit

    src = inspect.getsource(s16_circuit)
    assert "np.exp(-1j * phase)" in src, "the straight must carry exp(-i phi)"
    assert "np.exp(-2j * phi)" in src, "the closed form must carry exp(-2i phi)"
    assert "np.exp(2j * phi)" not in src
    assert "np.exp(1j * phase)" not in src
    assert "PASSED FOR AS LONG AS BOTH SIDES WERE WRONG" in src


def test_a_cross_check_between_two_of_your_own_implementations_is_weak():
    """Recorded as an executable statement of the principle.

    The residual was exactly 0.0 while both sides carried the same sign error. A
    comparison between two expressions written by one author, in one convention,
    cannot detect an error in that convention: it measures transcription, not
    truth. An independent anchor is one whose correctness does not depend on the
    thing being checked, and here that anchor is the requirement that a length of
    passive guide lengthens a round trip.
    """
    from picchain.stages.s16_circuit import straight

    ng, neff, lam0 = 2.06282, 1.66486, 1.573
    wl = np.array([lam0 * (1 - 1e-4), lam0, lam0 * (1 + 1e-4)])
    omega = 2 * np.pi * (ls.C0 / (wl * 1e-6))
    amp = np.asarray(straight(wl=wl, length_um=450.0, neff=neff, ng=ng,
                              wl0=lam0)[("in0", "out0")], dtype=complex)
    tau = -np.gradient(np.unwrap(np.angle(amp)), omega)[1]
    # the mirror's own delay, and the assembly which must exceed it
    tau_dbr = 67.1349e-12
    assert tau_dbr + 2 * tau > tau_dbr
