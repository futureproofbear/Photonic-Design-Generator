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

    # A phase section sits INSIDE the cavity, so its length is passive delay
    # like the feed. Omitting it understates tau_u, and tau_u is exactly what
    # sets the phase the section has to supply: phi_needed = 2*pi*tau_u*S*V.
    #
    # The section therefore has to cancel the slip it creates by existing. At a
    # 25 V phase drive the self-consistent length runs to 3583 um and does not
    # fit the die; the way out is a phase drive above the mirror's, which raises
    # what the section supplies without raising what it must supply.
    _ps = getattr(cav, "phase_section", None)
    tau_phase = (2 * n_g_wg * _ps.length_um * 1e-6 / C0) if (_ps and _ps.enabled) else 0.0
    tau_ext = tau_soa + tau_feed + tau_phase

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

    def Phi(f, shift, extra=0.0):
        """Round-trip phase.

        `extra` is any further round-trip phase applied at this drive point,
        which is how an intracavity phase electrode enters. It is zero for a
        cavity whose only tunable element is the mirror.
        """
        return 2 * np.pi * f * tau_ext + sgn * phi_of(f - shift) + extra

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

    def modes_at(shift: float, floor: float | None = None, extra=0.0):
        """Cavity modes at a given mirror shift.

        `floor` discards roots landing where the mirror does not reflect, which
        is correct when following the lasing mode. It is NOT correct when
        looking for the side mode: a neighbouring mode lying outside the mirror
        band is suppressed by the mirror, and suppression is the quantity being
        measured. Pass zero there.
        """
        lim = R_floor if floor is None else floor
        P = Phi(f_scan, shift, extra)
        out = []
        k0 = int(np.ceil(P.min() / (2 * np.pi)))
        k1 = int(np.floor(P.max() / (2 * np.pi)))
        for k in range(k0, k1 + 1):
            for f_m in resonance_roots(f_scan, P, k):
                r = float(R_of(f_m - shift))
                if r >= lim:
                    out.append((k, f_m, r))
        return out

    # Voltage sweep. The span decides what the tuning metrics can report, so it
    # is chosen from the design's own capability and not from the requirement.
    #
    # CORRECTED 2026-08-16. The span was 1.6 times the drive the requested chirp
    # needs. That made every tuning figure a restatement of the chirp setting:
    # reducing a declared chirp from 10 GHz to 3 GHz cut the reported placed
    # excursion from 14.55 to 5.32 GHz with the design untouched, because the
    # sweep simply stopped earlier. A requirement must not set the span of the
    # measurement that tests it.
    #
    # Where a drive limit is declared, the sweep covers it: that is the
    # excursion the electronics can actually deliver. Whether the chirp fits
    # inside that drive is a separate question, and `drive_Vpp_required` answers
    # it.
    V_needed = (design.chirp.bandwidth_GHz * 1e9 / (S_Hz_per_V * max(lever, 1e-6))
                if design.chirp.enabled and S_Hz_per_V > 0 else float("nan"))
    V_limit_decl = float(design.electrodes.max_drive_voltage_V or 0.0)
    if V_limit_decl > 0:
        V_max = V_limit_decl
    elif V_needed == V_needed:
        V_max = 1.6 * V_needed
    else:
        V_max = (float(grat["fwhm_GHz"]) * 1e9 / S_Hz_per_V) if S_Hz_per_V > 0 else 0.0

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
    # The sweep is expressed as a function of the applied phase so that it can be
    # run a second time with an intracavity phase electrode driven alongside the
    # mirror. What that architecture delivers is then measured on the same
    # machinery as the mirror-only case, rather than argued from the lever.
    def _sweep(phi_extra=None) -> dict[str, Any]:
        """Follow the lasing mode across the drive.

        `phi_extra` is called with the drive voltage and returns the further
        round-trip phase applied at that point, over the frequency grid.
        """
        tracked_q = None
        tracked_f = None
        f_track: list[float] = []
        f_lase: list[float] = []
        hop_V = None
        hop_indices: list[int] = []
        for i, V in enumerate(V_sweep):
            shift = S_Hz_per_V * V
            extra = 0.0 if phi_extra is None else phi_extra(V)
            ms = modes_at(shift, extra=extra)
            if not ms:
                break
            best = max(ms, key=lambda t: t[2])      # lowest threshold == highest |r|^2
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

        f_arr = np.asarray(f_track, dtype=float)
        V_arr = V_sweep[: len(f_arr)]

        # every continuous segment between hops, the last running to the drive limit
        bounds = [0] + hop_indices + [len(V_arr)]
        segs = [(bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)
                if bounds[j + 1] - bounds[j] >= 3]

        def _exc(lo: int, hi: int) -> float:
            seg = f_arr[lo:hi]
            return float(abs(seg[-1] - seg[0])) if len(seg) >= 2 else 0.0

        b_seg = max(segs, key=lambda t: _exc(*t)) if segs else None
        slope_Hz_per_V = float("nan")
        rms = float("nan")
        if b_seg is not None and b_seg[1] - b_seg[0] >= 3:
            lo, hi = b_seg
            s, c = np.polyfit(V_arr[lo:hi], f_arr[lo:hi], 1)
            slope_Hz_per_V = float(abs(s))
            resid = f_arr[lo:hi] - (s * V_arr[lo:hi] + c)
            rms = float(np.sqrt(np.mean(resid**2)))

        return {
            "f_track": f_arr, "f_lase": np.asarray(f_lase, dtype=float),
            "V_used": V_arr, "hop_V": hop_V, "hop_indices": hop_indices,
            "segments": segs, "best_seg": b_seg,
            "range_Hz": _exc(*b_seg) if b_seg else 0.0,
            "from_zero_Hz": _exc(*segs[0]) if segs else 0.0,
            "slope": slope_Hz_per_V, "rms_nonlin": rms,
        }

    _nom = _sweep()
    f_track_arr = _nom["f_track"]
    f_lase_arr = _nom["f_lase"]
    V_used = _nom["V_used"]
    hop_V = _nom["hop_V"]
    hop_indices = _nom["hop_indices"]
    segments = _nom["segments"]
    best_seg = _nom["best_seg"]
    mhf_range_Hz = _nom["range_Hz"]
    mhf_from_zero_Hz = _nom["from_zero_Hz"]
    rms_nonlin = _nom["rms_nonlin"]
    laser_tuning_Hz_per_V = (_nom["slope"] if _nom["slope"] == _nom["slope"]
                             else lever * S_Hz_per_V)
    rel_nonlin = rms_nonlin / mhf_range_Hz if mhf_range_Hz > 0 else float("nan")

    n_hops = len(hop_indices)

    # analytic cross-check
    mhf_analytic_Hz = lever / (1 - lever) * fsr_Hz / 2 if lever < 1 else float("inf")

    # The closed form counts cavity modes and assumes the mirror holds every one
    # of them. It does not. The mode walks out of the stop band, the round-trip
    # phase stops following the mirror, and the excursion ends there. So the
    # achieved range is bounded by the mirror bandwidth, and the two numbers
    # answer different questions.
    #
    # The two are anti-correlated through kappa: weakening the grating raises
    # the lever and the closed form with it, while narrowing the stop band and
    # lowering what is achieved. A design steered by the closed form is steered
    # away from the tuning range it is trying to buy. Measured on a third-order
    # tantalate mirror over a post gap of 0.90 to 1.05 um, the closed form rose
    # from 12.04 to 14.16 GHz while the achieved range fell from 10.32 to 6.51.
    fwhm_Hz = float(grat.get("fwhm_GHz") or 0.0) * 1e9
    mhf_over_fwhm = (mhf_range_Hz / fwhm_Hz) if fwhm_Hz > 0 else float("nan")

    # ---- the phase-robust tuning range -------------------------------------
    #
    # mhf_range_Hz above is read off one swept solve, so it carries the cavity
    # phase of that particular geometry. The phase is the round-trip optical
    # path modulo one wavelength, and no process holds a 17 mm cavity to that.
    # Changing the feed by 200 nm moved the hop from 51.6 V to 9.6 V with the
    # stop band unchanged, and a corner sweep reports the scatter rather than a
    # property of the design. The three quantities below are phase-independent
    # and are the ones a requirement is to be written against.
    #
    #   drift    the mode's excursion relative to the mirror centre over the
    #            whole sweep. The laser follows the mirror at eta = r*S and the
    #            mirror moves at S, so the mode slips at (1-r)*S.
    #   hops     drift / FSR, the number of mode boundaries crossed. Below one,
    #            a hop may or may not fall inside the sweep depending on phase.
    #   guaranteed  the excursion available at the WORST phase, when a hop lands
    #            mid-sweep and halves the usable span. With n hops the sweep is
    #            cut into n+1 segments and the worst case is the even split.
    #
    # Thermal placement of the comb recovers the full eta*V_max. The guaranteed
    # figure is what the design delivers before that step is performed.
    # The laser tuning is available by two routes and they answer slightly
    # different questions. The fitted slope is taken over the hop-free segment
    # the sweep happened to expose, so it carries the dispersion of that part of
    # the stop band and, through the segment's position, a trace of the cavity
    # phase. The lever route, r * S, is phase-independent and carries no
    # dispersion at all. Both are reported and the ratio is stated, because the
    # quantities downstream of eta inherit whichever is used.
    eta_lever_Hz_per_V = lever * S_Hz_per_V
    eta_ratio = (laser_tuning_Hz_per_V / eta_lever_Hz_per_V
                 if eta_lever_Hz_per_V > 0 else float("nan"))
    if eta_ratio == eta_ratio and not 0.85 <= eta_ratio <= 1.20:
        ctx.warn(
            f"the fitted laser tuning {laser_tuning_Hz_per_V/1e6:.1f} MHz/V and the lever route "
            f"r*S = {eta_lever_Hz_per_V/1e6:.1f} MHz/V differ by {abs(eta_ratio-1)*100:.0f} %. "
            "The fitted slope is taken over one hop-free segment, so a large divergence means the "
            "segment sits where the mirror dispersion is steep and the figure is not the whole band"
        )

    V_span = float(V_used[-1] - V_used[0]) if len(V_used) >= 2 else 0.0
    drift_Hz = (1.0 - lever) * S_Hz_per_V * V_span
    hops_in_sweep = (drift_Hz / fsr_Hz) if fsr_Hz > 0 else float("nan")
    # ceil, not floor. A drift of 0.6 FSR crosses no mode boundary on average
    # and crosses one whenever the phase places a boundary inside the sweep, so
    # the worst case is one hop and two segments. Using floor would report the
    # no-hop case as guaranteed and would restate the phase assumption it is
    # here to remove.
    n_seg = math.ceil(hops_in_sweep) + 1 if hops_in_sweep == hops_in_sweep else 1
    mhf_guaranteed_Hz = laser_tuning_Hz_per_V * V_span / max(n_seg, 1)
    # the mode must also stay inside the mirror it is following
    containment = (drift_Hz / fwhm_Hz) if fwhm_Hz > 0 else float("nan")

    # ---- the intracavity phase section --------------------------------------
    #
    # The slip above is what forces a hop. A phase electrode over a passive
    # stretch changes the round-trip path, so the comb can be driven in step
    # with the mirror and the slip is cancelled rather than tolerated.
    #
    # What the slip costs, in round-trip phase:
    #
    #     phi_needed = 2*pi * drift / FSR
    #
    # What a section of length L at drive V_ph supplies. The index change per
    # volt is taken from the mirror electrode and scaled by the gap ratio, the
    # field going as 1/gap; a phase section carries no Bragg posts, so its
    # electrodes may sit far closer than the mirror's.
    #
    #     dn_per_V   = S * n_g / nu           from the mirror's own tuning
    #     phi_avail  = 4*pi * dn_per_V * V_ph * L / lambda
    ps = getattr(design.cavity, "phase_section", None)
    phase_payload: dict[str, Any] = {"enabled": bool(ps and ps.enabled)}
    mhf_sync_Hz = float("nan")
    eta_sync_Hz_per_V = float("nan")
    _sync_track: dict | None = None
    if ps and ps.enabled and fsr_Hz > 0 and S_Hz_per_V > 0:
        lam_m = C0 / nu
        dn_per_V = S_Hz_per_V * n_g_wg / nu
        dn_per_V_ph = dn_per_V * (design.electrodes.gap_um / max(ps.gap_um, 1e-9))
        phi_needed = 2.0 * math.pi * drift_Hz / fsr_Hz
        V_ph = float(ps.max_drive_voltage_V or 0.0)
        phi_avail = 4.0 * math.pi * dn_per_V_ph * V_ph * (ps.length_um * 1e-6) / lam_m
        L_needed_um = (phi_needed * lam_m
                       / (4.0 * math.pi * dn_per_V_ph * max(V_ph, 1e-9))) * 1e6
        ok = phi_avail >= phi_needed
        phase_payload.update({
            "length_um": ps.length_um,
            "gap_um": ps.gap_um,
            "drive_V": V_ph,
            "dn_eff_per_volt": dn_per_V_ph,
            "phase_needed_rad": phi_needed,
            "phase_needed_in_FSR": phi_needed / (2.0 * math.pi),
            "phase_available_rad": phi_avail,
            "length_needed_um": L_needed_um,
            "sufficient": bool(ok),
            "margin": (phi_avail / phi_needed) if phi_needed > 0 else float("inf"),
        })
        if not ok:
            ctx.warn(
                f"the phase section supplies {phi_avail:.2f} rad and the mirror-to-comb slip over "
                f"the sweep costs {phi_needed:.2f} rad, so the comb cannot be held in step across "
                f"the whole excursion. It needs {L_needed_um:.0f} um at {V_ph:.0f} V against the "
                f"{ps.length_um:.0f} um drawn, or a higher phase drive"
            )

        # ---- what the section delivers, measured on the same sweep ----------
        #
        # The mirror-only figures above describe a cavity whose comb is left to
        # slip, and the laser then follows the mirror at r*S. Driving the
        # section in step with the mirror supplies the slip instead, and the
        # laser follows the mirror at the full S. That is the whole purpose of
        # the section, and it is measured here rather than asserted: the phase
        # is added to the round trip and the lasing mode is followed again.
        #
        # The section is driven to supply exactly the slip over the sweep, so
        # the drive is phi_needed/phi_avail of its rated voltage and the
        # remainder is headroom. Electrode polarity is a wiring choice, so both
        # are tried and the one that carries the comb with the mirror is taken.
        if ok and V_max > 0:
            V_ph_req = V_ph * phi_needed / phi_avail if phi_avail > 0 else 0.0

            def _phi_ps(V: float, s: float):
                dn = dn_per_V_ph * V_ph_req * (V / V_max)
                return s * 4.0 * math.pi * dn * (ps.length_um * 1e-6) * f_scan / C0

            runs = [(s, _sweep(lambda V, s=s: _phi_ps(V, s))) for s in (1.0, -1.0)]
            pol, sync = max(runs, key=lambda t: t[1]["range_Hz"])
            mhf_sync_Hz = sync["range_Hz"]
            eta_sync_Hz_per_V = sync["slope"]
            _sync_track = sync
            phase_payload.update({
                "synchronous_drive_V": V_ph_req,
                "electrode_polarity": int(pol),
                "laser_tuning_synchronous_MHz_per_V": eta_sync_Hz_per_V / 1e6,
                "hops_with_section": len(sync["hop_indices"]),
                "synchronous_gain_over_mirror_only": (
                    mhf_sync_Hz / mhf_range_Hz if mhf_range_Hz > 0 else float("nan")),
            })
            # the section is sized to make the laser follow the mirror one for
            # one, so a fitted slope far from S means the sizing and the sweep
            # disagree and the figure is not to be relied upon
            if S_Hz_per_V > 0 and eta_sync_Hz_per_V == eta_sync_Hz_per_V:
                dev = abs(eta_sync_Hz_per_V / S_Hz_per_V - 1.0)
                if dev > 0.15:
                    ctx.warn(
                        f"with the phase section driven the laser tunes at "
                        f"{eta_sync_Hz_per_V/1e6:.1f} MHz/V against the mirror's "
                        f"{S_Hz_per_V/1e6:.1f} MHz/V, a {dev*100:.0f} % shortfall. A section sized "
                        "to cancel the slip should carry the laser with the mirror one for one, so "
                        "the synchronous figures are not to be relied upon until this is understood"
                    )
    if containment == containment and containment > 1.0:
        ctx.warn(
            f"the mode slips {drift_Hz/1e9:.2f} GHz relative to the mirror over the sweep, against "
            f"a stop band of {fwhm_Hz/1e9:.2f} GHz FWHM. The mode leaves the reflection peak before "
            "the sweep ends, so the far end of the chirp is not held by this mirror. Widen the stop "
            "band with a stronger or shorter grating, or reduce the drive span"
        )

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
        "mode_hop_free_range_over_stopband_FWHM": mhf_over_fwhm,
        # phase-independent; write requirements against these
        "mode_hop_free_range_guaranteed_GHz": mhf_guaranteed_Hz / 1e9,
        "mode_hop_free_range_placed_GHz": laser_tuning_Hz_per_V * V_span / 1e9,
        "mirror_relative_drift_GHz": drift_Hz / 1e9,
        "laser_tuning_from_lever_MHz_per_V": eta_lever_Hz_per_V / 1e6,
        "laser_tuning_fitted_over_lever": eta_ratio,
        "mode_hops_in_sweep_analytic": hops_in_sweep,
        "tau_phase_section_ps": tau_phase * 1e12,
        "phase_section": phase_payload,
        # With a sufficient phase section the comb is driven in step with the
        # mirror, so no hand-over occurs and the whole swept excursion is
        # continuous without commissioning. Without one, the guaranteed figure
        # stands and the placed figure needs the comb set thermally.
        #
        # CORRECTED 2026-08-17. This was reported as laser_tuning * V_span,
        # which is the rate of a cavity whose comb is left to slip. A section
        # driven in step supplies the slip, so the laser follows the mirror at S
        # rather than at r*S, and the figure was understated by exactly the
        # lever. It is now taken from a second sweep with the section's phase
        # applied, so the number is measured on the same mode tracking as every
        # other excursion in this stage.
        "mode_hop_free_range_synchronous_GHz": mhf_sync_Hz / 1e9,
        "laser_tuning_synchronous_MHz_per_V": eta_sync_Hz_per_V / 1e6,
        "stopband_containment_ratio": containment,
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
    arrays: dict[str, Any] = {"V_sweep": V_used, "f_laser_Hz": f_track_arr}
    # the second track, where a phase section was driven alongside the mirror.
    # Written so that a figure of the tuning shows the measured excursion rather
    # than a line drawn from the reported slope.
    if _sync_track is not None:
        arrays["V_sweep_synchronous"] = _sync_track["V_used"]
        arrays["f_laser_Hz_synchronous"] = _sync_track["f_track"]
    ctx.write_stage("cavity", payload, arrays)
    return payload
