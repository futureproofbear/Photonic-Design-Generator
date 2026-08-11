"""Stage 11 - coupling across the facet to the gain chip or a fibre.

The interface between the photonic circuit and whatever feeds it is carried in
most design files as a single figure in decibels. It is the product of four
things, and quoting them together makes the budget impossible to improve,
because the dominant term cannot be identified.

This stage separates them: the overlap of the two mode profiles, the Fresnel
reflection at the index step, the penalty for an angled facet where the partner
is not rotated to match, and the alignment the assembly must hold.

What is assumed
---------------
The mode on the other side of the facet is not solved. It is described by its
mode-field diameters, which is what a vendor datasheet supplies, and it is
approximated by an elliptical Gaussian. That approximation is stated in the
metrics rather than buried: ``partner_model`` records it on every run.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import coupling as cp
from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.facet
    if not cfg.enabled:
        ctx.put("facet", {"enabled": False})
        return {"enabled": False}

    # The facet is at the *tip* of the taper, not at the full ridge. Solving the
    # ridge mode instead would compare the wrong two profiles: the tip is
    # narrowed precisely so that the mode expands to meet the partner.
    from ..geometry import build_grid
    from ..solvers.fdmode import solve_modes
    from .s01_mode import _eps_maps
    from .s08_taper import _cross_section

    m, p_ = design.mesh, design.platform
    lam = design.waveguide.wavelength_um
    width = cfg.facet_width_um or design.layout.taper_tip_width_um
    xs = _cross_section(design, float(width), "facet")
    grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, eyy = _eps_maps(xs, grid, lib, lam, p_.cut, p_.use_index_override, m.subsample)
    tip = solve_modes(grid.x, grid.y, exx, eyy, lam,
                      polarisation=m.polarisation, num_modes=1)[0]

    x, y, field = grid.x, grid.y, tip.field
    dA = np.outer(np.gradient(x), np.gradient(y))
    n_guide = float(tip.n_eff)

    angle = design.layout.input_facet_angle_deg

    # --- where the beam actually lands ----------------------------------
    # Snell conserves the transverse wavevector, so the angle *inside* the
    # partner does not depend on what lies between the two facets. The position
    # does: across a gap the beam travels at the angle that medium imposes,
    # which is steeper than the angle it will have in a higher-index partner,
    # and it arrives displaced. `facet.offset_x_um` is where the partner has
    # been placed, so what the overlap sees is the difference between the two.
    walk = cp.gap_walkoff(angle, n_guide, cfg.gap_index, cfg.gap_um)
    residual = (walk if walk == walk else 0.0) - cfg.offset_x_um

    # the partner, as an elliptical Gaussian of the declared mode-field radii,
    # displaced by whatever the walk-off leaves uncompensated
    partner = cp.gaussian_mode(x, y, cfg.partner_mfd_x_um / 2, cfg.partner_mfd_y_um / 2,
                               x0=residual, y0=cfg.offset_y_um)
    eta_overlap = cp.power_overlap(field, partner, dA)

    t_fresnel = cp.fresnel_transmission(n_guide, cfg.partner_index,
                                        cfg.ar_reflectivity)
    w_eff = 0.5 * (cfg.partner_mfd_x_um + cfg.partner_mfd_y_um) / 2
    eta_angle = cp.angled_facet_penalty(angle, n_guide, cfg.partner_index, w_eff, lam,
                                        partner_tilted=cfg.partner_tilted)

    total = eta_overlap * t_fresnel * eta_angle
    to_dB = lambda v: float(-10 * np.log10(v)) if v > 0 else float("inf")

    # what the assembly must hold, from the closed form for two Gaussians
    w_guide = cfg.partner_mfd_x_um / 2      # only the partner radius is declared;
    tol_x = cp.alignment_tolerance(w_guide, cfg.partner_mfd_x_um / 2, cfg.tolerance_dB)
    tol_y = cp.alignment_tolerance(cfg.partner_mfd_y_um / 2,
                                   cfg.partner_mfd_y_um / 2, cfg.tolerance_dB)

    # What the residual displacement costs, isolated for diagnosis. It is
    # already inside the overlap above and is not multiplied in again.
    #
    # Taken as the ratio of the overlap at the residual to the overlap with the
    # partner centred, so the guide mode enters as the field that was solved.
    # The closed-form penalty in `coupling` requires both modes to be Gaussian,
    # and the guide mode on a shallow-etched ridge is not.
    if residual:
        centred = cp.power_overlap(
            field,
            cp.gaussian_mode(x, y, cfg.partner_mfd_x_um / 2, cfg.partner_mfd_y_um / 2,
                             x0=0.0, y0=cfg.offset_y_um),
            dA)
        walk_penalty = eta_overlap / centred if centred > 0 else 0.0
    else:
        walk_penalty = 1.0

    payload = {
        "enabled": True,
        "facet_width_um": float(width),
        "n_eff_at_facet": n_guide,
        "n_eff_at_full_ridge": float((ctx.get("mode") or {}).get("n_eff_bare") or 0.0),
        "partner_model": "elliptical Gaussian of the declared mode-field diameters",
        "partner_mfd_x_um": cfg.partner_mfd_x_um,
        "partner_mfd_y_um": cfg.partner_mfd_y_um,
        "partner_index": cfg.partner_index,
        "facet_angle_deg": angle,
        "partner_tilted": cfg.partner_tilted,
        "beam_deflection_deg": cp.facet_deflection_deg(angle, n_guide, cfg.partner_index),
        "mode_overlap": eta_overlap,
        "mode_overlap_loss_dB": to_dB(eta_overlap),
        "fresnel_transmission": t_fresnel,
        "fresnel_loss_dB": to_dB(t_fresnel),
        "angle_penalty": eta_angle,
        "angle_loss_dB": to_dB(eta_angle),
        "total_coupling": total,
        "total_loss_dB": to_dB(total),
        "gap_um": cfg.gap_um,
        "gap_index": cfg.gap_index,
        "angle_in_gap_deg": cp.refracted_angle_deg(angle, n_guide, cfg.gap_index),
        "gap_walkoff_um": walk,
        "declared_offset_x_um": cfg.offset_x_um,
        "uncompensated_walkoff_um": abs(residual),
        "walkoff_penalty_dB": to_dB(walk_penalty) if walk_penalty > 0 else float("inf"),
        "alignment_tolerance_x_um": tol_x,
        "alignment_tolerance_y_um": tol_y,
        "tolerance_criterion_dB": cfg.tolerance_dB,
        "assumed_loss_dB_in_design": design.cavity.rsoa.coupling_loss_dB_per_facet,
    }
    ctx.put("facet", payload)
    ctx.write_stage("facet", payload)

    if cfg.gap_um > 0 and abs(residual) > 0.1 * tol_x:
        ctx.warn(
            f"the beam crosses the {cfg.gap_um:g} um coupling gap at "
            f"{payload['angle_in_gap_deg']:.1f} deg and arrives {walk:.3f} um to one "
            f"side. {abs(residual):.3f} um of that is uncompensated, against an alignment "
            f"tolerance of {tol_x:.3f} um, so {100 * abs(residual) / tol_x:.0f} % of the "
            "budget is spent before the assembly begins. Offset the partner by the "
            "walk-off in facet.offset_x_um"
        )

    assumed = design.cavity.rsoa.coupling_loss_dB_per_facet
    if payload["total_loss_dB"] > assumed + 0.5:
        ctx.warn(
            f"the facet is computed to lose {payload['total_loss_dB']:.2f} dB against the "
            f"{assumed:.2f} dB assumed in the design. The dominant term is "
            f"{max(('overlap', payload['mode_overlap_loss_dB']), ('Fresnel', payload['fresnel_loss_dB']), ('the facet angle', payload['angle_loss_dB']), key=lambda kv: kv[1])[0]}"
        )
    if tol_x < 0.3 or tol_y < 0.3:
        ctx.warn(
            f"a {cfg.tolerance_dB:.1f} dB alignment tolerance of {min(tol_x, tol_y):.2f} um "
            "is demanded of the assembly, which is tight for passive placement"
        )
    return payload
