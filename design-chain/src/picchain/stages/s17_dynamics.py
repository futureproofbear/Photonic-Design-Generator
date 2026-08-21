"""Stage: carrier dynamics of the extended-cavity laser.

The `cavity` stage answers where the laser oscillates and how far it tunes. It
treats the optical power as given, so it cannot say what current is required,
what power results, how fast the laser may be modulated, how quiet it is, or
whether it is stable at all against the feedback that defines it.

Those five questions require the carrier density to be a dynamical variable.
This stage adds the rate equations that make it one, and reports:

* the photon lifetime of the *composite* cavity, taken from the round-trip
  survival rather than from the gain chip alone;
* the threshold carrier density and the threshold current;
* the light-current curve and the slope efficiency;
* the relaxation oscillation frequency, its damping, and the small-signal
  bandwidth that follows;
* the relative intensity noise spectrum;
* the Lang-Kobayashi feedback parameter and the regime it places the laser in.

The last is the one that bears on this architecture most directly. An
extended-cavity laser is a laser deliberately operated under strong optical
feedback. It is stable there only because the anti-reflection coating on the
chip facet has suppressed the chip's own cavity, and the margin by which it does
so is a reliability figure. A degraded coating moves the device toward coherence
collapse without changing any other quantity the chain reports.

Disabled by default, since the gain-chip parameters it consumes are properties
of a part rather than of the photonic design.
"""

from __future__ import annotations

import math

import numpy as np

from .. import laser
from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict:
    cfg = design.dynamics
    if not cfg.enabled:
        ctx.put("dynamics", {"enabled": False})
        return {"enabled": False}

    cav = ctx.get("cavity")
    if cav is None or not cav.get("enabled", False):
        raise RuntimeError("stage 'dynamics' requires stage 'cavity'")
    grat = ctx.get("grating") or {}

    rs = design.cavity.rsoa
    gm = rs.gain

    # ---------------- the composite cavity ----------------
    # The photon lifetime is taken from what survives one round trip with the
    # gain switched off. Reading it off the round trip rather than assembling it
    # from mirror and internal terms keeps it consistent with the delay budget
    # the cavity stage already computed, and removes any question of which
    # length each loss is referenced to.
    tau_rt = float(cav["tau_roundtrip_ps"]) * 1e-12
    tau_soa = float(cav["tau_soa_ps"]) * 1e-12
    F = float(cav["active_fraction_F"])

    L_a_cm = rs.length_um * 1e-4
    R_back = rs.back_facet_R
    R_ext = float(cav["effective_mirror_R_at_soa"])
    internal_pass = math.exp(-rs.internal_loss_per_cm * 2.0 * L_a_cm)
    survival = R_back * R_ext * internal_pass
    tau_p = laser.photon_lifetime_s(tau_rt, survival)

    lam_um = float(grat.get("bragg_wavelength_um") or 1.55)
    nu = laser.C0 / (lam_um * 1e-6)
    v_g_a = laser.C0 * 100.0 / rs.group_index          # cm/s

    # what fraction of the decay leaves through the DBR rather than being lost
    alpha_out = (1.0 / (2 * L_a_cm)) * math.log(1.0 / R_ext)
    alpha_tot = float(cav["modal_threshold_gain_per_cm"])
    eta_out = laser.output_coupling_fraction(alpha_out, alpha_tot)

    # ---------------- threshold ----------------
    V_a_cm3 = (gm.active_width_um * 1e-4) * (gm.active_thickness_um * 1e-4) * L_a_cm
    tau_c = gm.carrier_lifetime_ns * 1e-9
    n_th = laser.threshold_carrier_density_per_cm3(
        tau_p, v_g_a, rs.confinement_factor, F,
        gm.differential_gain_cm2, gm.transparency_density_per_cm3)
    I_th = laser.threshold_current_A(n_th, V_a_cm3, tau_c, gm.injection_efficiency)
    slope = laser.slope_efficiency_W_per_A(nu, eta_out, gm.injection_efficiency)

    # ---------------- the light-current curve ----------------
    curve = []
    for I_mA in cfg.current_sweep_mA:
        I = I_mA * 1e-3
        S = laser.photon_density_per_cm3(I, I_th, tau_p, V_a_cm3, gm.injection_efficiency)
        P = laser.output_power_W(S, V_a_cm3, tau_p, nu, eta_out)
        curve.append({"current_mA": I_mA, "photon_density_per_cm3": S,
                      "output_power_mW": P * 1e3})

    # ---------------- the operating point ----------------
    I_op = cfg.operating_current_mA * 1e-3
    S_op = laser.photon_density_per_cm3(I_op, I_th, tau_p, V_a_cm3, gm.injection_efficiency)
    P_op = laser.output_power_W(S_op, V_a_cm3, tau_p, nu, eta_out)

    f_r = laser.relaxation_oscillation_Hz(
        S_op, tau_p, v_g_a, rs.confinement_factor, F, gm.differential_gain_cm2)
    K = laser.damping_K_factor_s(tau_p, v_g_a, gm.differential_gain_cm2,
                                 gm.gain_compression_cm3)
    gamma = laser.damping_rate_per_s(f_r, K, tau_c)
    zeta = laser.damping_ratio(f_r, gamma)
    f_3dB = laser.modulation_bandwidth_Hz(f_r, gamma)

    # ---------------- intensity noise ----------------
    f_grid = np.linspace(1e6, cfg.rin_span_GHz * 1e9, cfg.rin_points)
    rin = laser.rin_spectrum_per_Hz(f_grid, f_r, gamma, S_op, tau_p, tau_c,
                                    gm.spontaneous_coupling_beta, n_th)
    rin_peak = laser.rin_peak_dB_per_Hz(rin)
    i_q = int(np.argmin(np.abs(f_grid - cfg.rin_quote_offset_GHz * 1e9)))
    rin_at = 10.0 * math.log10(rin[i_q]) if rin[i_q] > 0 else float("-inf")

    # ---------------- optical feedback ----------------
    # This is the check the architecture demands. The laser is defined by its
    # feedback, so the question is not whether feedback is present but whether
    # the external mirror dominates the chip facet by enough to own the cavity.
    kappa_f = laser.feedback_rate_per_s(rs.front_facet_R, R_ext, tau_soa)
    tau_ext = tau_rt - tau_soa
    C = laser.feedback_C(kappa_f, tau_ext, rs.linewidth_enhancement_alpha)
    regime, reason = laser.feedback_regime(C, R_ext, rs.front_facet_R)
    margin_dB = laser.coherence_collapse_margin_dB(R_ext, rs.front_facet_R)

    payload = {
        "enabled": True,
        # the cavity
        "photon_lifetime_ps": tau_p * 1e12,
        "roundtrip_survival": survival,
        "cold_cavity_Q": laser.cold_cavity_Q(tau_p, nu),
        "output_coupling_fraction": eta_out,
        # threshold
        "active_volume_um3": V_a_cm3 * 1e12,
        "threshold_carrier_density_per_cm3": n_th,
        "threshold_current_mA": I_th * 1e3,
        "slope_efficiency_W_per_A": slope,
        # the operating point
        "operating_current_mA": cfg.operating_current_mA,
        "operating_photon_density_per_cm3": S_op,
        "operating_output_power_mW": P_op * 1e3,
        "declared_output_power_mW": rs.output_power_mW,
        "light_current_curve": curve,
        # small signal
        "relaxation_oscillation_GHz": f_r / 1e9,
        "damping_K_factor_ns": K * 1e9,
        "damping_rate_per_ns": gamma * 1e-9,
        "damping_ratio": zeta,
        "small_signal_bandwidth_GHz": f_3dB / 1e9,
        # noise
        "rin_peak_dB_per_Hz": rin_peak,
        "rin_quote_offset_GHz": cfg.rin_quote_offset_GHz,
        "rin_at_quote_offset_dB_per_Hz": rin_at,
        # feedback
        "feedback_rate_per_ns": kappa_f * 1e-9,
        "external_delay_ps": tau_ext * 1e12,
        "feedback_C": C,
        "feedback_regime": regime,
        "feedback_regime_reason": reason,
        "external_over_facet_margin_dB": margin_dB,
        "compound_mode_spacing_GHz": laser.external_cavity_mode_spacing_Hz(tau_rt) / 1e9,
    }
    ctx.put("dynamics", payload)
    ctx.write_stage("dynamics", payload, {
        "rin_frequency_Hz": f_grid,
        "rin_per_Hz": rin,
    })

    # ---------------- what the numbers oblige us to say ----------------
    if S_op <= 0:
        ctx.warn(
            f"the operating current of {cfg.operating_current_mA:.0f} mA is below the "
            f"threshold of {I_th * 1e3:.1f} mA, so the laser does not oscillate at the "
            "declared operating point"
        )
    else:
        ratio = P_op * 1e3 / rs.output_power_mW if rs.output_power_mW else float("inf")
        # The linewidth is INVERSELY PROPORTIONAL to the declared power, so this
        # divergence passes into it at full weight. The band was 0.5 to 2.0
        # until 2026-08-12, which is a factor of four on a quantity whose
        # acceptance row is commonly written at +-100 %: a divergence inside the
        # old band could flip the verdict on its own, and did. See LESSONS T036.
        #
        # Tightened again the same day, from 10 % to 5 %. Raising the drive
        # current by 20 mA moved the computed power by 7.7 % and the reported
        # linewidth by the same, which was the whole difference between meeting
        # a target and missing it. The band must sit below the smallest
        # divergence that can change a verdict, and 5 % is that for a linewidth
        # row quoted to three figures.
        if not 0.95 <= ratio <= 1.05:
            drift = (1.0 / ratio - 1.0) * 100.0
            ctx.warn(
                f"the rate equations give {P_op * 1e3:.1f} mW at "
                f"{cfg.operating_current_mA:.0f} mA against the "
                f"{rs.output_power_mW:.1f} mW declared in cavity.rsoa.output_power_mW, "
                f"a divergence of {abs(ratio - 1.0) * 100:.0f} %. The declared figure "
                f"sets the linewidth and enters it inversely, so the reported linewidth "
                f"is {abs(drift):.0f} % {'low' if drift > 0 else 'high'} against the "
                f"power this design actually produces. Set "
                f"cavity.rsoa.output_power_mW to {P_op * 1e3:.2f} and re-run before "
                "quoting either figure"
            )

    if regime == "IV":
        ctx.warn(
            f"the feedback places this laser in regime IV, coherence collapse: {reason}. "
            f"The external mirror stands only {margin_dB:.0f} dB above the chip facet"
        )
    elif regime == "II":
        ctx.warn(
            f"the feedback places this laser in regime II: {reason}. The line will not "
            "be stable against the feedback phase, which the chirp drive sweeps"
        )

    if margin_dB < 25.0:
        ctx.warn(
            f"the external mirror exceeds the chip facet by only {margin_dB:.0f} dB. "
            "This margin is what holds the laser out of coherence collapse, and it is "
            "consumed by any degradation of the anti-reflection coating"
        )

    fsr_Hz = float(cav["fsr_GHz"]) * 1e9
    if 0 < f_r and abs(f_r - fsr_Hz) < 0.25 * fsr_Hz:
        ctx.warn(
            f"the relaxation oscillation at {f_r / 1e9:.2f} GHz lies within a quarter of "
            f"the compound-mode spacing of {fsr_Hz / 1e9:.2f} GHz. Relaxation-oscillation "
            "sidebands then fall on a neighbouring cavity mode, which is a mode-partition "
            "mechanism the single-mode equations solved here cannot represent"
        )

    if f_3dB > 0 and design.chirp.enabled:
        needed_Hz = 1.0 / (design.chirp.chirp_duration_us * 1e-6) * 10.0
        if f_3dB < needed_Hz:
            ctx.warn(
                f"the small-signal bandwidth of {f_3dB / 1e9:.2f} GHz is below the "
                f"{needed_Hz / 1e9:.3f} GHz the chirp harmonics require"
            )
    return payload
