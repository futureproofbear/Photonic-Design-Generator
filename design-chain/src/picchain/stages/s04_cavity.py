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
    # The facet loss the facet stage computed, where it ran, and the declared
    # figure otherwise.
    #
    # `coupling_loss_dB_per_facet` is a declared input, and a declared input can
    # be left behind by the geometry it describes. On one design the taper tip
    # moved from 0.20 to 0.26 um to clear a minimum-width rule and the declared
    # loss stayed at 1.096 dB while the stage computed 1.4266. The cavity used
    # the declared one, so the effective mirror, the threshold gain, and the
    # fitted active thickness that the output power and the linewidth descend
    # from were all optimistic by 0.66 dB of round trip. The facet stage warned
    # and the warning was acknowledged; nothing used the number it computed.
    _facet = ctx.get("facet") or {}
    _loss_dB = _facet.get("total_loss_dB")
    if _loss_dB is None:
        _loss_dB, _loss_from = rs.coupling_loss_dB_per_facet, "cavity.rsoa (declared)"
    else:
        _loss_dB, _loss_from = float(_loss_dB), "facet.total_loss_dB (computed)"
    eta = 10 ** (-_loss_dB / 10)                               # power coupling, per pass
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
    def _side_mode_at(extra_phase: float, shift: float = 0.0):
        """Side-mode suppression at one setting of the cavity phase.

        The cavity phase is the round-trip optical path modulo a wavelength, and
        no process holds a centimetre-long cavity to that. It is therefore not a
        property of the drawn design but of the particular die, unless the design
        carries an actuator that sets it.
        """
        all_m = modes_at(shift, floor=0.0, extra=extra_phase)
        in_band = [m for m in all_m if m[2] >= R_floor]
        smsr = float("nan")
        dg = float("nan")
        in_b = None
        if all_m:
            main = max(in_band or all_m, key=lambda t: t[2])
            nb = [m for m in all_m if abs(m[0] - main[0]) == 1]
            if nb:
                side = max(nb, key=lambda t: t[2])
                in_b = bool(side[2] >= R_floor)
                R_main, R_side = main[2], side[2]
                if R_side > 0:
                    dg = (1 / (2 * L_a_cm)) * math.log(R_main / R_side)
                    deficit = 1.0 - math.exp(-2 * L_a_cm * dg)
                    denom = (
                        H * nu * v_g_a**2 * (alpha_m_per_cm * 100)
                        * rs.spontaneous_emission_factor_nsp
                        * (modal_gth_per_cm * 100) * tau_rt
                    )
                    if denom > 0 and P0 > 0:
                        smsr = 10 * math.log10(max(P0 * deficit / denom, 1e-30))
        return {"smsr_dB": smsr, "side_mode_gain_margin_per_cm": dg,
                "n_cavity_modes_in_band": len(in_band),
                "side_mode_within_mirror_band": in_b}

    def _side_mode_over_the_drive(extra_phase: float, points: int = 9):
        """Side-mode suppression at its worst over the whole drive.

        Evaluating it at zero bias answers a question the radar never asks. The
        mirror is swept across the chirp on every ramp, and the side mode moves
        with it, so the figure that matters is the worst the suppression reaches
        anywhere on the ramp.

        On one design the difference decided the requirement: at the phase whose
        zero-bias suppression was highest, 44.17 dB, the suppression fell to
        27.47 dB by the top of the drive, 12.5 dB under a 40 dB bound. A separate
        phase held 43.10 dB across the whole ramp. A maximum taken at zero bias
        selects the first of those two and the second is the design.
        """
        Vs = np.linspace(0.0, V_span, max(int(points), 2)) if V_span > 0 else np.array([0.0])
        out = [_side_mode_at(extra_phase, shift=S_Hz_per_V * float(V)) for V in Vs]
        ok = [d for d in out if d["smsr_dB"] == d["smsr_dB"]]
        worst = min(ok, key=lambda d: d["smsr_dB"]) if ok else out[0]
        return {
            "smsr_dB": worst["smsr_dB"],
            "smsr_dB_at_zero_bias": out[0]["smsr_dB"],
            "smsr_dB_at_full_drive": out[-1]["smsr_dB"],
            "drive_points": len(Vs),
            "n_cavity_modes_in_band": max(d["n_cavity_modes_in_band"] for d in out),
            "side_mode_gain_margin_per_cm": worst["side_mode_gain_margin_per_cm"],
            "side_mode_within_mirror_band": worst["side_mode_within_mirror_band"],
        }

    _at_drawn = _side_mode_at(0.0)
    smsr_dB = _at_drawn["smsr_dB"]
    dg_per_cm = _at_drawn["side_mode_gain_margin_per_cm"]
    side_in_band = _at_drawn["side_mode_within_mirror_band"]
    n_in_band = _at_drawn["n_cavity_modes_in_band"]

    # The same quantities across one whole cycle of cavity phase.
    #
    # A design with no actuator gets whichever value its die happens to land on,
    # so the worst of these is what it can promise. A design that can set the
    # phase, and can show its actuator reaches a full mode spacing, gets the
    # best of them, and the setting is a commissioning step rather than a hope.
    # 96 stations, not 24.
    #
    # A quantity read at its maximum needs enough stations to establish that the
    # maximum is resolved rather than sampled. At 24 the spacing is 15 degrees of
    # cavity phase and a narrow peak between two stations would be missed
    # entirely, so the figure quoted could be neither the true best nor a
    # repeatable one.
    _N = 96
    _scan = [_side_mode_over_the_drive(2.0 * math.pi * k / _N) for k in range(_N)]
    _valid = [d for d in _scan if d["smsr_dB"] == d["smsr_dB"]]
    _best = max(_valid, key=lambda d: d["smsr_dB"]) if _valid else None
    _phase_scan = {
        "points": len(_scan),
        "smsr_dB_worst": min((d["smsr_dB"] for d in _valid), default=float("nan")),
        "smsr_dB_best": max((d["smsr_dB"] for d in _valid), default=float("nan")),
        "n_cavity_modes_in_band_worst": max(d["n_cavity_modes_in_band"] for d in _scan),
        "n_cavity_modes_in_band_best": min(d["n_cavity_modes_in_band"] for d in _scan),
        # the whole trace, so a reader can check the maximum rather than take it
        "smsr_dB_by_station": [d["smsr_dB"] for d in _scan],
    }

    # THE WIDTH OF THE WINDOW, which is what a commissioning setting needs.
    #
    # A row graded at the best of a scan states nothing about how precisely the
    # setting has to be found. Where the peak is a knife edge the figure is
    # unusable whatever its height, and where the whole cycle clears the bound
    # the setting hardly matters. The fraction of the cycle that clears the bound
    # is the tolerance, and it is reported beside the figure it qualifies.
    _floor = None
    for _t in getattr(design, "targets", []) or []:
        if getattr(_t, "metric", "") == "cavity.smsr_dB_settable":
            _floor = getattr(_t, "min", None)
    if _floor is not None and _valid:
        _ok = sum(1 for d in _scan if d["smsr_dB"] >= float(_floor))
        _phase_scan["bound_graded_against"] = float(_floor)
        _phase_scan["stations_clearing_the_bound"] = _ok
        _phase_scan["fraction_of_the_cycle_clearing_the_bound"] = _ok / float(_N)
        # the longest unbroken run of clearing stations, taken cyclically, which
        # is the window a single setting has to land in
        _flags = [d["smsr_dB"] >= float(_floor) for d in _scan]
        _run = _longest = 0
        for _f in _flags + _flags:
            _run = _run + 1 if _f else 0
            _longest = max(_longest, _run)
        _longest = min(_longest, _N)
        _phase_scan["widest_contiguous_window_stations"] = _longest
        _phase_scan["widest_contiguous_window_deg"] = 360.0 * _longest / _N

    # ---- BOTH CONDITIONS AT ONE PHASE ---------------------------------------
    #
    # A trimmer sets one variable, so two requirements graded on it must hold
    # together at a single setting. Suppression is a maximum over phase and the
    # hop-free excursion is a separate consequence of the same phase, and taking
    # each at its own optimum would describe two devices rather than one.
    #
    # Both are therefore evaluated at the same stations. `_sweep` already accepts
    # a further round-trip phase as a function of drive, so a constant function
    # holds the cavity phase while the drive runs, and the hop-free span at that
    # phase falls out of the segment the sweep exposes.
    _JN = 24
    _joint = []
    for _k in range(_JN):
        _ph = 2.0 * math.pi * _k / _JN
        _sm = _side_mode_over_the_drive(_ph)
        try:
            _sw = _sweep(lambda V, _p=_ph: _p)
            # `range_Hz` is the excursion of the longest hop-free segment the
            # sweep exposes at this cavity phase, which is exactly the quantity
            # a set comb is supposed to deliver.
            _span = float(_sw.get("range_Hz") or 0.0) / 1e9
            _nh = len(_sw.get("hop_indices") or [])
        except Exception:
            _span, _nh = float("nan"), -1
        _joint.append({
            "phase_deg": 360.0 * _k / _JN,
            "smsr_dB": _sm["smsr_dB"],
            "smsr_dB_at_zero_bias": _sm["smsr_dB_at_zero_bias"],
            "hop_free_span_GHz": _span,
            "hops_in_sweep": _nh,
        })
    _span_floor = None
    for _t in getattr(design, "targets", []) or []:
        if getattr(_t, "metric", "") == "cavity.mode_hop_free_range_degraded_GHz":
            _span_floor = getattr(_t, "min", None)
    _jn = {"points": _JN, "stations": _joint}
    if _floor is not None and _span_floor is not None:
        _fl, _sfl = float(_floor), float(_span_floor)
        _both = [(d["smsr_dB"] == d["smsr_dB"] and d["smsr_dB"] >= _fl
                  and d["hop_free_span_GHz"] >= _sfl) for d in _joint]
        _r = _l = 0
        for _f in _both + _both:
            _r = _r + 1 if _f else 0
            _l = max(_l, _r)
        _l = min(_l, _JN)
        _jn.update({
            "smsr_bound_dB": _fl,
            "span_bound_GHz": _sfl,
            "stations_meeting_both": sum(_both),
            "widest_contiguous_window_stations": _l,
            "widest_contiguous_window_deg": 360.0 * _l / _JN,
            "a_single_setting_meets_both": bool(_l > 0),
        })
        # THE SETTING THE DESIGN WILL ACTUALLY USE, and the figures there.
        #
        # Grading each requirement at its own optimum over phase describes two
        # devices. Grading both at the centre of the widest window in which both
        # hold describes one, and it is the setting a commissioning step should
        # aim for: furthest from either edge, so the tolerance is symmetric.
        #
        # The excursion at that setting is a measured span and is smaller than
        # `mode_hop_free_range_placed_GHz`, which is the analytic product
        # eta * V_span and is reached at no phase.
        if _l > 0:
            _ext = _both + _both
            _st = next(i for i in range(len(_ext))
                       if all(_ext[i:i + _l])) % _JN
            _mid = (_st + _l // 2) % _JN
            _win = [_joint[(_st + i) % _JN] for i in range(_l)]
            _jn.update({
                "setting_station": _mid,
                "setting_phase_deg": _joint[_mid]["phase_deg"],
                "window_starts_at_deg": _joint[_st]["phase_deg"],
                "smsr_dB_at_setting": _joint[_mid]["smsr_dB"],
                "hop_free_span_GHz_at_setting": _joint[_mid]["hop_free_span_GHz"],
                # the worst either quantity reaches anywhere inside the window,
                # which is what a setting found only to the window's width gives
                "smsr_dB_worst_in_window": min(d["smsr_dB"] for d in _win),
                "hop_free_span_GHz_worst_in_window": min(
                    d["hop_free_span_GHz"] for d in _win),
            })

        if _l == 0:
            ctx.warn(
                "no setting of the cavity phase meets the side-mode bound and "
                "the hop-free excursion together: the two are optima at "
                "different phases, so a design graded on both describes two "
                "devices rather than one",
                key="cavity.no_joint_phase_window",
            )
        elif _l <= 2:
            ctx.warn(
                f"the phase window meeting both bounds is only "
                f"{360.0 * _l / _JN:.0f} degrees wide of a full cycle, so the "
                "commissioning step has to find it to that precision and the "
                "sampling may not have resolved it",
                key="cavity.joint_phase_window_narrow",
            )
    _phase_scan["joint_with_the_hop_free_span"] = _jn

    # ---- the thermal phase trimmer, and whether it can place the comb -----
    #
    # A round trip accumulates 2 * (2 pi / lambda) * n * L of phase, so a change
    # dn over a length L moves it by 2 * (2 pi / lambda) * dn * L. Placing the
    # comb anywhere in the mode spacing needs a full 2 pi of that, which is
    # dn * L >= lambda / 2. The heater delivers dn = dn_dT * dT.
    #
    # Declaring a trimmer is not enough and this is checked rather than
    # believed: a trimmer that cannot move the comb through one whole mode
    # spacing cannot place it, and one the layout did not draw cannot set
    # anything at all.
    _pt = design.cavity.phase_trimmer
    _drawn = (ctx.get("layout") or {}).get("phase_trimmer")
    if not _pt.enabled or _pt.length_um <= 0:
        _trimmer = {
            "enabled": False,
            "covers_a_full_fsr": False,
            "reason": "no phase trimmer is declared, so the cavity phase cannot "
                      "be set and the guaranteed excursion is what the design "
                      "delivers",
        }
    else:
        # THE PHASE A HEATER REACHES IS AN EFFECTIVE-INDEX CHANGE, and this
        # calculation took a material one.
        #
        # It read `dn = dn_dT * dT` and multiplied that by the full geometric
        # length, which is the phase a plane wave in bulk material would pick up.
        # A guided mode carries only the fraction of its power that sits in the
        # heated film, so the phase it actually accumulates is smaller by that
        # fraction. Every other phase quantity in this stage is an effective
        # index: the Pockels section uses `dn_eff_per_volt` throughout.
        #
        # On one design the correction moved the reach from 13.29 rad to
        # 7.24 rad against the 6.283 rad of a mode spacing, so the margin fell
        # from 2.12 times to 1.15 and the temperature for a full spacing rose
        # from 18.9 K to 34.7 K. The claim survived; it had been overstated by
        # the reciprocal of the confinement.
        #
        # The film confinement is the conservative choice. A heater warms its
        # cladding too, and the cladding's own thermo-optic coefficient adds to
        # this rather than subtracting, so the figure reported is a floor. Where
        # the mode solve did not run, the confinement is unavailable and 1.0 is
        # used with a warning, which is the old behaviour and is flagged as
        # optimistic.
        _conf = (ctx.get("mode") or {}).get("confinement_film")
        _conf_from = "mode.confinement_film"
        if _conf is None or not (0.0 < float(_conf) <= 1.0):
            _conf, _conf_from = 1.0, "unavailable, taken as 1.0 and optimistic"
            ctx.warn(
                "the phase trimmer's reach is computed without a confinement "
                "factor because the mode stage supplied none, so it is the phase "
                "a plane wave in bulk material would accumulate and overstates "
                "what a guided mode reaches by the reciprocal of the film "
                "confinement",
                key="cavity.trimmer_confinement_unavailable",
            )
        _conf = float(_conf)
        # The cladding is heated too, and its own coefficient adds.
        #
        #   dn_eff/dT = Gamma_film * (dn/dT)_film + (1 - Gamma_film) * (dn/dT)_clad
        #
        # Omitting the second term understates the reach; omitting the first
        # OVERSTATES it by 1/Gamma, which is what this calculation did. Both are
        # carried so the figure is a computation rather than a bound.
        _dndt_clad = float(getattr(_pt, "dn_dT_cladding_per_K", 0.0) or 0.0)
        _dndt_eff = (_conf * float(_pt.dn_dT_per_K)
                     + (1.0 - _conf) * _dndt_clad)
        _dn_mat = float(_pt.dn_dT_per_K) * float(_pt.max_delta_T_K)
        _dn = _dndt_eff * float(_pt.max_delta_T_K)   # the effective-index change
        _lam_um = float(design.waveguide.wavelength_um)
        _phase_rad = 2.0 * (2.0 * math.pi / _lam_um) * _dn * float(_pt.length_um)
        _covers = _phase_rad >= 2.0 * math.pi
        if _drawn is not None and not _drawn.get("drawn"):
            _covers = False
        _trimmer = {
            "enabled": True,
            "length_um": float(_pt.length_um),
            "over": str(getattr(_pt, "over", "feed")),
            "dn_dT_per_K": float(_pt.dn_dT_per_K),
            "max_delta_T_K": float(_pt.max_delta_T_K),
            "film_confinement": _conf,
            "film_confinement_from": _conf_from,
            "dn_dT_cladding_per_K": _dndt_clad,
            "dn_dT_effective_per_K": _dndt_eff,
            "index_change_material": _dn_mat,
            "index_change": _dn,
            "round_trip_phase_rad": _phase_rad,
            "phase_needed_rad": 2.0 * math.pi,
            "delta_T_for_a_full_fsr_K": (
                _lam_um / (2.0 * _dndt_eff * float(_pt.length_um))
                if _dndt_eff > 0 else float("inf")),
            # THE COEFFICIENT AT WHICH THE ENTITLEMENT FLIPS.
            #
            # One boolean decides whether the design is graded on the best of the
            # phase scan or the worst, and this is the number that decides the
            # boolean. Reporting it turns an assumption into a stated condition
            # that a measurement can settle.
            "dn_dT_effective_break_even_per_K": (
                _lam_um / (2.0 * float(_pt.max_delta_T_K) * float(_pt.length_um))),
            "break_even_margin": (
                _dndt_eff / (_lam_um / (2.0 * float(_pt.max_delta_T_K)
                                        * float(_pt.length_um)))),
            # the layout stage runs after this one, so this is None on a normal
            # run and the layout stage carries the "is it drawn" check instead
            "drawn_at_cavity_time": _drawn,
            "covers_a_full_fsr": bool(_covers),
        }
        if not _covers:
            ctx.warn(
                f"the phase trimmer reaches {_phase_rad:.3f} rad of round-trip "
                f"phase against the {2 * math.pi:.3f} a full mode spacing needs, "
                f"or was not drawn, so it cannot place the comb and the degraded "
                f"excursion stays at the guaranteed figure. It needs "
                f"{_trimmer['delta_T_for_a_full_fsr_K']:.1f} K over "
                f"{_pt.length_um:.0f} um, or a longer heater")

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
        # Which of the two the design is entitled to, and why. The guaranteed
        # figure is the placed one divided by `ceil(hops) + 1`, and the divisor
        # is entirely the cavity phase: a design that cannot set that phase does
        # not know where in the comb its sweep begins. One that can, and can
        # show the actuator reaches a whole mode spacing, starts where it
        # chooses.
        "phase_trimmer": _trimmer,
        "mode_hop_free_range_degraded_GHz": (
            laser_tuning_Hz_per_V * V_span / 1e9 if _trimmer.get("covers_a_full_fsr")
            else mhf_guaranteed_Hz / 1e9),
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
        "coupling_loss_dB_per_facet_used": _loss_dB,
        "coupling_loss_dB_per_facet_from": _loss_from,
        "effective_mirror_R_at_soa": R2_eff,
        "alpha_mirror_per_cm": alpha_m_per_cm,
        "modal_threshold_gain_per_cm": modal_gth_per_cm,
        "active_fraction_F": F,
        "schawlow_townes_henry_linewidth_Hz": dnu_ST,
        "schawlow_townes_henry_linewidth_kHz": dnu_ST / 1e3,
        "side_mode_gain_margin_per_cm": dg_per_cm,
        "smsr_dB": smsr_dB,
        "n_cavity_modes_in_band": n_in_band,
        # across a whole cycle of cavity phase, and the figure a design with a
        # verified trimmer is entitled to
        "phase_scan": _phase_scan,
        # THE TWO QUANTITIES AT ONE SETTING OF THE PHASE, which is what a
        # commissioned device delivers. Both are absent where no single setting
        # meets both bounds, so a target written against either fails as missing
        # rather than passing on the other's optimum.
        "smsr_dB_at_joint_setting": (
            _phase_scan.get("joint_with_the_hop_free_span", {})
            .get("smsr_dB_at_setting")),
        "hop_free_span_GHz_at_joint_setting": (
            _phase_scan.get("joint_with_the_hop_free_span", {})
            .get("hop_free_span_GHz_at_setting")),
        "smsr_dB_worst_in_joint_window": (
            _phase_scan.get("joint_with_the_hop_free_span", {})
            .get("smsr_dB_worst_in_window")),
        "hop_free_span_GHz_worst_in_joint_window": (
            _phase_scan.get("joint_with_the_hop_free_span", {})
            .get("hop_free_span_GHz_worst_in_window")),
        "smsr_dB_settable": (_phase_scan["smsr_dB_best"]
                             if _trimmer.get("covers_a_full_fsr")
                             else _phase_scan["smsr_dB_worst"]),
        "n_cavity_modes_in_band_settable": (
            _phase_scan["n_cavity_modes_in_band_best"]
            if _trimmer.get("covers_a_full_fsr")
            else _phase_scan["n_cavity_modes_in_band_worst"]),
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
