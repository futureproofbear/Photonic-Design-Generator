"""Stage 2 - Bragg grating: CMT coupling constant and TMM spectrum.

Consumes ``dn_eff``/``n_g`` from stage 1, applies the spatial-Fourier step that
isolates the working harmonic of a high-order grating, then runs the TMM to get
reflectivity, bandwidth, sidelobe level, group delay and penetration depth.

Also produces the (post width x post gap) design-space map that arXiv:2408.01743
shows as Fig. 1d, by re-solving the perturbed cross-section on the sweep grid.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import tmm
from .. import process
from ..artifacts import RunContext
from ..config import Design
from ..geometry import build_grid, edbr_cross_section
from ..materials import MaterialLibrary
from .s01_mode import _build, _solve

C0 = 299792458.0


def _dn_for_geometry(design: Design, lib, post_w: float, post_gap: float, n_bare: float) -> float:
    """Re-solve dn_eff for one (post width, gap) point of the sweep."""
    d = design.model_copy(deep=True)
    d.grating.post_width_um = post_w
    d.grating.post_gap_um = post_gap
    xs_p = _build(d, with_posts=True, electrodes=False, name="sweep_posts")
    xs_b = _build(d, with_posts=False, electrodes=False, name="sweep_bare")
    xs_b.window = xs_p.window
    grid = build_grid(xs_p, d.mesh.d_fine_um, d.mesh.d_coarse_um, d.mesh.fine_margin_um)
    lam = d.waveguide.wavelength_um
    nb = _solve(d, xs_b, grid, lib, lam, n_bare)
    npst = _solve(d, xs_p, grid, lib, lam, n_bare)
    return npst.n_eff - nb.n_eff


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    g = design.grating
    mode = ctx.get("mode")
    if mode is None:
        raise RuntimeError("stage 'grating' requires stage 'mode' to have run")

    n_bare = float(mode["n_eff_bare"])
    dn_eff = float(mode["dn_eff_posts"])
    n_g = float(mode["n_g"])

    # the duty cycle is a ratio of printed dimensions: what reflects is what
    # exists in silicon, and a process bias moves it
    post_len = process.geometry(design, design.process.simulate).post_length_um

    # -- period / Bragg wavelength ---------------------------------------
    if g.period_um is not None:
        period = g.period_um
        duty = post_len / period
        n_bar = tmm.mean_index(n_bare, dn_eff, duty)
        lam_B = tmm.bragg_wavelength_um(n_bar, period, g.order)
    else:
        lam_t = g.target_wavelength_um
        # self-consistent: duty depends on the period we are solving for
        period = tmm.period_for_bragg_um(n_bare, lam_t, g.order)
        for _ in range(20):
            duty = post_len / period
            n_bar = tmm.mean_index(n_bare, dn_eff, duty)
            new = tmm.period_for_bragg_um(n_bar, lam_t, g.order)
            if abs(new - period) < 1e-9:
                period = new
                break
            period = new
        duty = post_len / period
        n_bar = tmm.mean_index(n_bare, dn_eff, duty)
        lam_B = tmm.bragg_wavelength_um(n_bar, period, g.order)

    sig = g.profile_sigma_um
    a_m = tmm.fourier_amplitude(dn_eff, duty, g.order, period, sig)
    kappa = tmm.fourier_kappa(dn_eff, duty, g.order, lam_B, period, sig)
    kL = kappa * g.length_um
    n_periods = g.length_um / period

    spec = tmm.compute_spectrum(
        kappa_per_um=kappa,
        L_um=g.length_um,
        n_bar=n_bar,
        n_g=n_g,
        period_um=period,
        order=g.order,
        span_GHz=g.span_GHz,
        points=g.points,
        alpha_dB_per_cm=design.platform.propagation_loss_dB_per_cm,
        apodisation=g.apodisation,
        apod_fraction=g.apod_fraction,
        n_sections=g.n_sections,
    )

    L_pen = tmm.penetration_depth(kappa, g.length_um)
    tau_dbr = 2 * n_g * L_pen * 1e-6 / C0  # round-trip group delay through the mirror

    payload: dict[str, Any] = {
        "order": g.order,
        "period_um": period,
        "period_nm": period * 1e3,
        "duty_cycle": duty,
        "n_periods": n_periods,
        "n_bar": n_bar,
        "n_g": n_g,
        "dn_eff": dn_eff,
        "fourier_amplitude_a_m": a_m,
        "profile_sigma_um": sig,
        "profile_smoothing_factor": tmm.profile_smoothing(g.order, period, sig),
        "kappa_per_um": kappa,
        "kappa_per_cm": kappa * 1e4,
        "kappa_L": kL,
        "length_um": g.length_um,
        "bragg_wavelength_um": lam_B,
        "bragg_wavelength_nm": lam_B * 1e3,
        "bragg_frequency_THz": spec.f_B_Hz / 1e12,
        "peak_reflectivity": spec.peak_R,
        "peak_reflectivity_analytic": tmm.peak_reflectivity(kappa, g.length_um),
        "fwhm_GHz": spec.fwhm_Hz() / 1e9,
        "fwhm_nm": spec.fwhm_Hz() / 1e9 * (lam_B**2 * 1e-3) / (C0 / 1e6) * 1e9 if spec.fwhm_Hz() == spec.fwhm_Hz() else float("nan"),
        "sidelobe_suppression_dB": spec.sidelobe_suppression_dB(),
        "transform_limit_fwhm_GHz": tmm.transform_limit_fwhm_Hz(g.length_um, n_g) / 1e9,
        "fwhm_over_transform_limit": (
            spec.fwhm_Hz() / tmm.transform_limit_fwhm_Hz(g.length_um, n_g)
        ),
        "group_delay_peak_ps": spec.group_delay_at_peak_s() * 1e12,
        "penetration_depth_um": L_pen,
        "penetration_depth_mm": L_pen / 1e3,
        "mirror_round_trip_delay_ps": tau_dbr * 1e12,
        "apodisation": g.apodisation,
    }
    # nm bandwidth, computed cleanly
    if spec.fwhm_Hz() == spec.fwhm_Hz():
        payload["fwhm_nm"] = spec.fwhm_Hz() * (lam_B * 1e-6) ** 2 / C0 * 1e9

    # ---- radiation from the lower diffraction orders, stated as a budget ----
    #
    # A grating of order m phase-matches m diffraction orders, and every order
    # below the Bragg one radiates: for m = 3, the m = 1 and m = 2 orders leave
    # the guide into the cladding and the substrate. Coupled-mode theory keeps
    # only the backward-coupled Bragg order, so this loss channel is absent from
    # every figure this stage reports. The chain carries no solver for it here;
    # the honest statement is the margin the design has against it, not a value.
    #
    # The bound is set by the threshold-gain requirement: the radiation adds to
    # the distributed loss inside the mirror, and the room left under the
    # threshold-gain ceiling is the loss the design survives.
    tg = next((tt for tt in design.targets
               if tt.metric == "cavity.modal_threshold_gain_per_cm"), None)
    if design.grating.order > 1 and tg is not None and tg.max:
        payload["radiation_orders_unmodelled"] = list(range(1, design.grating.order))
        ctx.warn(
            f"order-{design.grating.order} grating: diffraction orders "
            f"{list(range(1, design.grating.order))} radiate out of the guide and no stage "
            "models that loss. The reflectivity and the threshold quoted here assume it is "
            "zero. The margin under the threshold-gain ceiling is the budget the design has "
            "against it; read cavity.modal_threshold_gain_per_cm against its target"
        )

    # ---- will the grating add coherently along its own length? -------------
    #
    # Everything above assumes one Bragg wavelength over the whole mirror. The
    # Bragg condition is set by the effective index, the effective index follows
    # the film thickness, and a film that thins along the grating detunes it.
    # The reflections then stop adding in phase: the peak falls and the stop
    # band broadens and distorts.
    #
    # A corner sweep cannot see this. It moves the film uniformly, which shifts
    # the Bragg wavelength and leaves the grating perfectly coherent. This is a
    # different failure and it is the one that scales with mirror length.
    #
    # The budget is set over the penetration depth rather than the drawn length,
    # because that is the distance the light actually samples.
    dn_dfilm = float(mode.get("dn_eff_d_film_per_um") or float("nan"))
    if dn_dfilm == dn_dfilm and dn_dfilm != 0.0 and L_pen > 0:
        lam_m = lam_B * 1e-6
        # an index error of this size costs pi of Bragg phase over L_pen
        dn_pi = lam_m / (2.0 * (L_pen * 1e-6))
        budget_um = dn_pi / dn_dfilm
        payload["dn_eff_d_film_per_um"] = dn_dfilm
        payload["film_uniformity_for_pi_phase_um"] = budget_um
        payload["film_uniformity_for_pi_phase_nm"] = budget_um * 1e3
        payload["film_uniformity_budget_percent"] = (
            budget_um / design.platform.film_thickness_um * 100.0
        )
        declared = getattr(design.platform, "film_nonuniformity_nm", 0.0) or 0.0
        if declared:
            payload["film_nonuniformity_declared_nm"] = declared
            payload["bragg_phase_error_rad"] = 3.14159265358979 * declared / (budget_um * 1e3)
            if declared > budget_um * 1e3:
                ctx.warn(
                    f"the film is declared non-uniform by {declared:.3f} nm over the device and "
                    f"the grating tolerates {budget_um * 1e3:.3f} nm before the Bragg phase slips "
                    f"by pi across the {L_pen / 1e3:.2f} mm penetration depth. The reflections "
                    "will not add in phase over the whole mirror: expect a lower peak and a "
                    "broader, distorted stop band than this stage reports"
                )
        else:
            ctx.warn(
                f"this grating tolerates {budget_um * 1e3:.3f} nm of film non-uniformity "
                f"({budget_um / design.platform.film_thickness_um * 100:.3f} % of the film) "
                f"before the Bragg phase slips by pi over its {L_pen / 1e3:.2f} mm penetration "
                "depth, and platform.film_nonuniformity_nm is not declared. Coherent addition "
                "over the mirror is assumed and not established"
            )

    arrays = {
        "freq_Hz": spec.freq_Hz,
        "R": spec.R,
        "phase_rad": np.unwrap(np.angle(spec.r)),
        "group_delay_s": spec.group_delay_s(),
    }

    # -- optional design-space sweep (Fig. 1d equivalent) ------------------
    if g.sweep_post_width_um and g.sweep_post_gap_um:
        ws = np.asarray(g.sweep_post_width_um, dtype=float)
        gs = np.asarray(g.sweep_post_gap_um, dtype=float)
        Rmap = np.zeros((len(ws), len(gs)))
        Bmap = np.zeros((len(ws), len(gs)))
        Kmap = np.zeros((len(ws), len(gs)))
        for i, w in enumerate(ws):
            for j, gp in enumerate(gs):
                dn = _dn_for_geometry(design, lib, float(w), float(gp), n_bare)
                dty = (g.post_length_um or float(w)) / period
                nb = tmm.mean_index(n_bare, dn, dty)
                lb = tmm.bragg_wavelength_um(nb, period, g.order)
                kap = tmm.fourier_kappa(dn, dty, g.order, lb, period, g.profile_sigma_um)
                sp = tmm.compute_spectrum(
                    kappa_per_um=kap, L_um=g.length_um, n_bar=nb, n_g=n_g,
                    period_um=period, order=g.order, span_GHz=g.span_GHz,
                    points=1501,
                    alpha_dB_per_cm=design.platform.propagation_loss_dB_per_cm,
                )
                Rmap[i, j] = sp.peak_R
                Bmap[i, j] = sp.fwhm_Hz() / 1e9
                Kmap[i, j] = kap
        payload["sweep"] = {
            "post_width_um": ws.tolist(),
            "post_gap_um": gs.tolist(),
            "peak_reflectivity": Rmap.tolist(),
            "fwhm_GHz": Bmap.tolist(),
        }
        arrays.update({"sweep_R": Rmap, "sweep_BW_GHz": Bmap, "sweep_kappa": Kmap,
                       "sweep_w": ws, "sweep_g": gs})

    ctx.put("grating", payload)
    ctx.write_stage("grating", payload, arrays)

    # A passive grating cannot return more power than it receives. This is not a
    # design criterion and it is not a tolerance: a value above unity means the
    # model is wrong, so it is raised rather than warned about. It went
    # undetected while the coupling was moderate, the error being under 0.1 % at
    # kappa*L = 2.1, and appeared only once kappa*L passed 3.
    if spec.peak_R > 1.0:
        raise RuntimeError(
            f"peak reflectivity {spec.peak_R:.6f} exceeds unity on a passive grating, "
            f"at kappa*L = {kL:.2f} and {design.platform.propagation_loss_dB_per_cm} dB/cm. "
            "Energy is not conserved by the model; the loss term is the first thing "
            "to examine, a sign error there presenting as gain"
        )

    tl = tmm.transform_limit_fwhm_Hz(g.length_um, n_g)
    if spec.fwhm_Hz() == spec.fwhm_Hz() and spec.fwhm_Hz() < tl:
        ctx.warn(
            f"reported FWHM {spec.fwhm_Hz()/1e9:.2f} GHz is below the {tl/1e9:.2f} GHz "
            "transform limit of this grating length - check n_g and the spectrum span"
        )
    if kL < 0.5:
        ctx.warn(f"kappa*L = {kL:.2f} is low; peak reflectivity {spec.peak_R:.1%} may be "
                 "insufficient to reach threshold with a typical RSOA")
    if g.apodisation == "uniform":
        ctx.warn("uniform (unapodised) grating: expect the sidelobes reported here to show "
                 "up as mode-hop risk and as chirp nonlinearity in the laser")
    return payload
