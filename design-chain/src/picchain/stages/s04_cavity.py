"""Stage 4 - hybrid RSOA + E-DBR laser cavity.

This is where the device numbers become *laser* numbers, and it is the stage
that decides whether an E-DBR is usable as a frequency-swept coherent source.

The model
---------
Round-trip phase of the two-element cavity (gain chip butt-coupled to a passive
PIC that ends in the distributed mirror):

    Phi(f, V) = 2 pi f tau_ext + arg r_DBR(f - S V)

with

    tau_ext = 2 (n_g,SOA L_SOA + n_g,wg L_feed) / c      (lumped, non-tunable)
    tau_DBR = |d arg r_DBR / d omega|                    (distributed mirror)
    S       = Pockels tuning of the mirror, Hz/V, from stage 3

Two consequences fall straight out and they drive the whole design:

1. **Tuning lever**  r = tau_DBR / (tau_ext + tau_DBR).  Only the fraction of
   the round-trip delay that lives *inside the electro-optically tuned grating*
   follows the mirror, so the laser tunes at r x S, not S.  Getting the laser
   tuning efficiency to equal the mirror tuning efficiency requires r -> 1,
   i.e. a short gain chip, a short feed section, and a long, weakly-coupled
   grating.

2. **Mode-hop-free range**  a hop occurs once the mirror has slipped half a
   cavity FSR relative to the mode comb, i.e. after (1-r) x Df_mirror = FSR/2,
   so the continuous laser excursion is r/(1-r) x FSR/2.

Both are computed here numerically (by tracking the actual mode solutions of
Phi = 2 pi q against the actual complex r_DBR), not from the linearised
expressions, so grating dispersion and sidelobes show up as chirp nonlinearity.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary

C0 = 299792458.0
H = 6.62607015e-34

#: A root of the round-trip phase counts as a cavity mode only where the mirror
#: reflects. Expressed as a fraction of the peak reflectivity, this discards the
#: spurious resonances that the phase step at each sidelobe null would otherwise
#: contribute.
_MODE_R_FLOOR = 0.05


def resonance_roots(f_scan: np.ndarray, phase: np.ndarray, k: int) -> list[float]:
    """Every frequency at which the round-trip phase equals 2*pi*k.

    The phase of a Bragg mirror steps by pi at each sidelobe null, so the
    round-trip phase is not monotonic in frequency and a resonance index may be
    satisfied at more than one frequency. Interpolating the inverse function
    assumes monotonicity and returns one wrong root without complaint. Every
    root is therefore found by bracketing a sign change.
    """
    g = np.asarray(phase, dtype=float) - 2.0 * np.pi * k
    sb = np.signbit(g)
    out: list[float] = []
    for j in np.nonzero(sb[:-1] != sb[1:])[0]:
        g0, g1 = g[j], g[j + 1]
        if g1 == g0:
            continue
        out.append(float(f_scan[j] + (f_scan[j + 1] - f_scan[j]) * (-g0) / (g1 - g0)))
    return out


def _phase_interp(f_grid: np.ndarray, phase: np.ndarray):
    def _p(f):
        return np.interp(f, f_grid, phase)
    return _p


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cav = design.cavity
    if not cav.enabled:
        ctx.put("cavity", {"enabled": False})
        return {"enabled": False}

    grat = ctx.get("grating")
    if grat is None:
        raise RuntimeError("stage 'cavity' requires stage 'grating'")
    eo = ctx.get("eo") or {}

    npz = np.load(ctx.run_dir / "grating.npz")
    f_grid = npz["freq_Hz"]
    R_grid = npz["R"]
    phase = npz["phase_rad"]

    n_g_wg = float(grat["n_g"])
    rs = cav.rsoa

    tau_soa = 2 * rs.group_index * rs.length_um * 1e-6 / C0
    tau_feed = 2 * n_g_wg * cav.feed_length_um * 1e-6 / C0
    tau_ext = tau_soa + tau_feed

    # DBR group delay at the reflection peak; sign convention fixed here so
    # that the total round-trip delay is positive
    i_peak = int(np.argmax(R_grid))
    omega = 2 * np.pi * f_grid
    dphi = np.gradient(phase, omega)
    tau_dbr = float(abs(np.median(dphi[max(0, i_peak - 20): i_peak + 20])))
    sgn = 1.0 if np.median(dphi[max(0, i_peak - 20): i_peak + 20]) > 0 else -1.0

    tau_rt = tau_ext + tau_dbr
    fsr_Hz = 1.0 / tau_rt
    lever = tau_dbr / tau_rt

    S_Hz_per_V = abs(float(eo.get("tuning_MHz_per_V", 0.0))) * 1e6

    # ---------------- threshold, linewidth ----------------
    R_peak = float(grat["peak_reflectivity"])
    eta = 10 ** (-rs.coupling_loss_dB_per_facet / 10)          # power coupling, per pass
    feed_loss = 10 ** (-design.platform.propagation_loss_dB_per_cm * cav.feed_length_um * 1e-4 / 10)
    R2_eff = R_peak * (eta**2) * (feed_loss**2)
    L_a_cm = rs.length_um * 1e-4
    alpha_m_per_cm = (1.0 / (2 * L_a_cm)) * math.log(1.0 / (rs.back_facet_R * R2_eff))
    modal_gth_per_cm = rs.internal_loss_per_cm + alpha_m_per_cm

    v_g_a = C0 / rs.group_index
    nu = C0 / (float(grat["bragg_wavelength_um"]) * 1e-6)
    P0 = rs.output_power_mW * 1e-3
    F = tau_soa / tau_rt                                        # active fraction of round trip
    if P0 > 0:
        dnu_ST = (
            v_g_a**2 * H * nu * rs.spontaneous_emission_factor_nsp
            * (alpha_m_per_cm * 100) * (modal_gth_per_cm * 100)
            * (1 + rs.linewidth_enhancement_alpha**2)
        ) / (8 * math.pi * P0) * F**2
    else:
        dnu_ST = float("nan")

    # ---------------- mode tracking vs applied voltage ----------------
    phi_of = _phase_interp(f_grid, phase)
    R_of = _phase_interp(f_grid, R_grid)

    def Phi(f, shift):
        return 2 * np.pi * f * tau_ext + sgn * phi_of(f - shift)

    f_lo, f_hi = f_grid[0] + 0.15 * (f_grid[-1] - f_grid[0]), f_grid[-1] - 0.15 * (f_grid[-1] - f_grid[0])
    f_scan = np.linspace(f_lo, f_hi, 20001)

    # The round-trip phase is NOT monotonic in frequency. A Bragg mirror's phase
    # steps by pi at every sidelobe null, so the apparent group delay there is
    # large and negative; on the validation baseline the round-trip delay dips to
    # -2733 ps across 5.5 % of the scanned band. Until 2026-08-07 the resonance
    # condition was solved by `np.interp(k, q, f_scan)`, which requires q to be
    # increasing and returns a wrong root without complaint when it is not. The
    # tracked mode consequently jumped discontinuously, by 4 GHz on the baseline
    # and by 12 GHz on a short-cavity variant, and the mode-hop-free range was
    # measured across those jumps.
    #
    # Every root is now found by bracketing a sign change, which is correct
    # whether or not the phase is monotonic. Roots landing where the mirror does
    # not reflect are discarded: a resonance of the round-trip phase at a
    # reflectivity null is not a cavity mode, there being no mirror there.
    R_floor = _MODE_R_FLOOR * float(np.max(R_grid))

    def modes_at(shift: float, floor: float | None = None):
        """Cavity modes at a given mirror shift.

        `floor` discards roots landing where the mirror does not reflect, which
        is correct when following the lasing mode. It is NOT correct when
        looking for the side mode: a neighbouring mode lying outside the mirror
        band is suppressed by the mirror, and suppression is the quantity being
        measured. Pass zero there.
        """
        lim = R_floor if floor is None else floor
        P = Phi(f_scan, shift)
        out = []
        k0 = int(np.ceil(P.min() / (2 * np.pi)))
        k1 = int(np.floor(P.max() / (2 * np.pi)))
        for k in range(k0, k1 + 1):
            for f_m in resonance_roots(f_scan, P, k):
                r = float(R_of(f_m - shift))
                if r >= lim:
                    out.append((k, f_m, r))
        return out

    # voltage sweep: cover the requested chirp, or +-half the DBR bandwidth
    if design.chirp.enabled and S_Hz_per_V > 0:
        V_needed = design.chirp.bandwidth_GHz * 1e9 / (S_Hz_per_V * max(lever, 1e-6))
        V_max = 1.6 * V_needed
    else:
        V_max = (float(grat["fwhm_GHz"]) * 1e9 / S_Hz_per_V) if S_Hz_per_V > 0 else 0.0
        V_needed = float("nan")

    # A tuning range is only available if a driver can reach the voltage that
    # produces it. Where a limit is declared the search stops there, and the
    # metric then states whether the excursion ended at a mode hop or at the
    # end of the drive. The two are different findings: the first is a property
    # of the cavity, the second of the electronics.
    V_limit = float(design.electrodes.max_drive_voltage_V or 0.0)
    V_clamped = bool(V_limit and V_max > V_limit)
    if V_clamped:
        V_max = V_limit
    V_sweep = np.linspace(0.0, V_max, 241) if V_max > 0 else np.array([0.0])

    # A non-monotonic phase admits more than one root per index, so the mode is
    # followed by continuity of frequency rather than by index alone. The laser
    # occupies the lowest-threshold mode; when that ceases to be the mode it was
    # occupying, it hops.
    #
    # The excursion is measured BETWEEN hops and not from zero bias. Until
    # 2026-08-07 only the first segment was measured, which made the metric a
    # property of the arbitrary cavity phase at zero volts rather than of the
    # design: a laser happening to start near a hop boundary reported 0.41 GHz
    # while an otherwise identical design with a slightly different optical path
    # reported 7.7 GHz. A DC offset places the laser wherever in the mode is
    # wanted, so the span between hops is the quantity the design controls, and
    # it is what the acceptance target means. The zero-bias figure is retained
    # beside it, being what is obtained without such an offset.
    tracked_q = None
    tracked_f = None
    f_track: list[float] = []
    f_lase: list[float] = []
    hop_V = None
    hop_indices: list[int] = []
    for i, V in enumerate(V_sweep):
        shift = S_Hz_per_V * V
        ms = modes_at(shift)
        if not ms:
            break
        best = max(ms, key=lambda t: t[2])          # lowest threshold == highest |r|^2
        if tracked_q is None:
            tracked_q, tracked_f = best[0], best[1]
        if best[0] != tracked_q:
            if hop_V is None:
                hop_V = float(V)
            hop_indices.append(i)
            tracked_q, tracked_f = best[0], best[1]
        same = [m for m in ms if m[0] == tracked_q]
        pool = same if same else ms
        cur = min(pool, key=lambda t: abs(t[1] - tracked_f))
        tracked_f = cur[1]
        f_track.append(cur[1])
        f_lase.append(best[1])

    f_track_arr = np.asarray(f_track, dtype=float)
    f_lase_arr = np.asarray(f_lase, dtype=float)
    V_used = V_sweep[: len(f_track_arr)]

    # every continuous segment between hops, the last running to the drive limit
    bounds = [0] + hop_indices + [len(V_used)]
    segments = [(bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)
                if bounds[j + 1] - bounds[j] >= 3]

    def _excursion(lo: int, hi: int) -> float:
        seg = f_track_arr[lo:hi]
        return float(abs(seg[-1] - seg[0])) if len(seg) >= 2 else 0.0

    mhf_from_zero_Hz = _excursion(*segments[0]) if segments else 0.0
    if segments:
        best_seg = max(segments, key=lambda t: _excursion(*t))
        mhf_range_Hz = _excursion(*best_seg)
    else:
        best_seg = None
        mhf_range_Hz = 0.0

    if best_seg is not None and best_seg[1] - best_seg[0] >= 3:
        lo, hi = best_seg
        f_mhf = f_track_arr[lo:hi]
        V_mhf = V_used[lo:hi]
        slope, intercept = np.polyfit(V_mhf, f_mhf, 1)
        resid = f_mhf - (slope * V_mhf + intercept)
        rms_nonlin = float(np.sqrt(np.mean(resid**2)))
        laser_tuning_Hz_per_V = float(abs(slope))
        rel_nonlin = rms_nonlin / mhf_range_Hz if mhf_range_Hz > 0 else float("nan")
    else:
        laser_tuning_Hz_per_V = lever * S_Hz_per_V
        rms_nonlin = float("nan")
        rel_nonlin = float("nan")

    n_hops = len(hop_indices)

    # analytic cross-check
    mhf_analytic_Hz = lever / (1 - lever) * fsr_Hz / 2 if lever < 1 else float("inf")

    # ---------------- side-mode suppression ----------------
    # The side mode is the cavity mode adjacent in index to the lasing one,
    # wherever it falls. Where the free spectral range exceeds the mirror
    # bandwidth the neighbour lies outside the stop band and is suppressed by
    # the mirror rolloff, which is the most favourable case and not the absence
    # of a case. Restricting the search to modes inside the band reported no
    # side mode at all and returned a NaN, which reads as a defect and would
    # carry a target to an error.
    ms0_all = modes_at(0.0, floor=0.0)
    ms0 = [m for m in ms0_all if m[2] >= R_floor]
    n_in_band = len(ms0)
    smsr_dB = float("nan")
    dg_per_cm = float("nan")
    side_in_band = None
    if ms0_all:
        main = max(ms0 or ms0_all, key=lambda t: t[2])
        neighbours = [m for m in ms0_all if abs(m[0] - main[0]) == 1]
        if neighbours:
            side = max(neighbours, key=lambda t: t[2])
            side_in_band = bool(side[2] >= R_floor)
            R_main, R_side = main[2], side[2]
            if R_side > 0:
                # extra modal gain the side mode would need, per unit active length
                dg_per_cm = (1 / (2 * L_a_cm)) * math.log(R_main / R_side)
                deficit = 1.0 - math.exp(-2 * L_a_cm * dg_per_cm)
                denom = (
                    H * nu * v_g_a**2 * (alpha_m_per_cm * 100)
                    * rs.spontaneous_emission_factor_nsp * (modal_gth_per_cm * 100) * tau_rt
                )
                if denom > 0 and P0 > 0:
                    smsr_dB = 10 * math.log10(max(P0 * deficit / denom, 1e-30))

    payload: dict[str, Any] = {
        "enabled": True,
        "tau_soa_ps": tau_soa * 1e12,
        "tau_feed_ps": tau_feed * 1e12,
        "tau_dbr_ps": tau_dbr * 1e12,
        "tau_roundtrip_ps": tau_rt * 1e12,
        "fsr_GHz": fsr_Hz / 1e9,
        "pockels_lever": lever,
        "mirror_tuning_MHz_per_V": S_Hz_per_V / 1e6,
        "laser_tuning_MHz_per_V": laser_tuning_Hz_per_V / 1e6,
        "mode_hop_free_range_GHz": mhf_range_Hz / 1e9,
        "mode_hop_free_range_GHz_analytic": mhf_analytic_Hz / 1e9,
        "mode_hop_voltage_V": hop_V,
        "mode_hop_free_range_from_zero_bias_GHz": mhf_from_zero_Hz / 1e9,
        "n_mode_hops_in_sweep": n_hops,
        "bias_offset_needed": bool(n_hops and mhf_range_Hz > mhf_from_zero_Hz * 1.05),
        "drive_voltage_limit_V": V_limit or None,
        "sweep_clamped_by_drive_limit": V_clamped,
        "range_limited_by": ("mode hop" if hop_V is not None
                             else ("drive limit" if V_clamped else "sweep end")),
        "chirp_nonlinearity_rms_MHz": rms_nonlin / 1e6 if rms_nonlin == rms_nonlin else float("nan"),
        "chirp_nonlinearity_rms_percent": rel_nonlin * 100 if rel_nonlin == rel_nonlin else float("nan"),
        "mirror_reflectivity": R_peak,
        "effective_mirror_R_at_soa": R2_eff,
        "alpha_mirror_per_cm": alpha_m_per_cm,
        "modal_threshold_gain_per_cm": modal_gth_per_cm,
        "active_fraction_F": F,
        "schawlow_townes_henry_linewidth_Hz": dnu_ST,
        "schawlow_townes_henry_linewidth_kHz": dnu_ST / 1e3,
        "side_mode_gain_margin_per_cm": dg_per_cm,
        "smsr_dB": smsr_dB,
        "n_cavity_modes_in_band": n_in_band,
        # False is the favourable case: the neighbouring mode falls outside the
        # mirror band and is suppressed by the rolloff rather than competing.
        "side_mode_within_mirror_band": side_in_band,
        "drive_voltage_for_chirp_Vpp": V_needed,
    }

    if design.chirp.enabled:
        ch = design.chirp
        gamma = ch.bandwidth_GHz * 1e9 / (ch.chirp_duration_us * 1e-6)
        payload["chirp"] = {
            "bandwidth_GHz": ch.bandwidth_GHz,
            "duration_us": ch.chirp_duration_us,
            "sweep_rate_THz_per_s": gamma / 1e12,
            "ramp_rate_kHz": (1e6 / ch.chirp_duration_us) / 1e3,
            "range_resolution_cm": C0 / (2 * ch.bandwidth_GHz * 1e9) * 100,
            "drive_Vpp_required": V_needed,
            "mhf_headroom": (mhf_range_Hz / 1e9) / ch.bandwidth_GHz if ch.bandwidth_GHz else float("nan"),
        }
        # the electrode must pass the harmonics of a triangle ramp
        bw_needed_MHz = 10 * (1e6 / ch.chirp_duration_us) / 1e6
        payload["chirp"]["electrode_bandwidth_needed_MHz"] = bw_needed_MHz
        rc = float(eo.get("lumped_RC_bandwidth_MHz", float("inf")))
        payload["chirp"]["electrode_bandwidth_ok"] = bool(rc >= bw_needed_MHz)
        if rc < bw_needed_MHz:
            ctx.warn(
                f"electrode RC bandwidth {rc:.1f} MHz < {bw_needed_MHz:.1f} MHz needed for the "
                "10th harmonic of the chirp ramp - ramp corners will round off"
            )
        if mhf_range_Hz / 1e9 < ch.bandwidth_GHz:
            ctx.warn(
                f"mode-hop-free range {mhf_range_Hz/1e9:.2f} GHz < required chirp bandwidth "
                f"{ch.bandwidth_GHz} GHz - the laser will hop mid-ramp"
            )

    ctx.put("cavity", payload)
    ctx.write_stage(
        "cavity", payload,
        {"V_sweep": V_used, "f_laser_Hz": f_track_arr},
    )
    return payload
