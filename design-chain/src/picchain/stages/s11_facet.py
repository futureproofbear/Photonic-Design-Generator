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


def _strip_cross_section(design: Design, width_um: float, name: str):
    """A strip of the slab layer alone, fully etched about it: the port of a
    double-layer edge coupler. The mode is weakly guided and wide, so the
    window is padded by 6 um. (added 2026-10-06)"""
    from ..geometry import edbr_cross_section
    from .. import process
    p = design.platform
    geom = process.geometry(design, design.process.simulate)
    slab_t = p.film_thickness_um - geom.etch_depth_um
    return edbr_cross_section(
        film_material=p.film_material, film_thickness_um=slab_t, etch_depth_um=0.0,
        wg_top_width_um=width_um, sidewall_deg=p.sidewall_deg,
        box_thickness_um=p.box_thickness_um, clad_thickness_um=p.clad_thickness_um,
        clad_material=p.clad_material, box_material=p.box_material,
        substrate_material=p.substrate_material, slab_offset_um=0.0,
        include_substrate=False, window_pad_x_um=6.0, window_pad_y_um=5.0, name=name)


def _port(design: Design, ctx: RunContext, lib: MaterialLibrary, cfg, angle: float,
          width: float, label: str) -> dict[str, Any]:
    """Everything the stage establishes at one facet: the mode at the taper
    tip, its overlap with the declared partner, the Fresnel and angle terms,
    the alignment the assembly must hold, and the reflection the facet returns
    into the guide."""
    # The facet is at the *tip* of the taper, not at the full ridge. Solving the
    # ridge mode instead would compare the wrong two profiles: the tip is
    # narrowed precisely so that the mode expands to meet the partner.
    from ..geometry import build_grid
    from ..solvers.fdmode import solve_modes
    from .s01_mode import _eps_maps
    from .s08_taper import _cross_section

    m, p_ = design.mesh, design.platform
    lam = design.waveguide.wavelength_um
    strip = getattr(cfg, "port", "ridge") == "slab_strip"
    if strip:
        xs = _strip_cross_section(design, float(width), f"facet_{label}_strip")
        grid = build_grid(xs, min(m.d_fine_um, 0.02), max(m.d_coarse_um, 0.15), m.fine_margin_um)
    else:
        xs = _cross_section(design, float(width), f"facet_{label}")
        grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, eyy = _eps_maps(xs, grid, lib, lam, p_.cut, p_.use_index_override, m.subsample)
    tip = solve_modes(grid.x, grid.y, exx, eyy, lam,
                      polarisation=m.polarisation, num_modes=1)[0]

    x, y, field = grid.x, grid.y, tip.field
    dA = np.outer(np.gradient(x), np.gradient(y))
    n_guide = float(tip.n_eff)

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
    _I = np.abs(field) ** 2
    _y_mode = float((_I * dA * y[None, :]).sum() / (_I * dA).sum()) if strip else 0.0
    partner = cp.gaussian_mode(x, y, cfg.partner_mfd_x_um / 2, cfg.partner_mfd_y_um / 2,
                               x0=residual, y0=cfg.offset_y_um + _y_mode)
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
                             x0=0.0, y0=cfg.offset_y_um + _y_mode),
            dA)
        walk_penalty = eta_overlap / centred if centred > 0 else 0.0
    else:
        walk_penalty = 1.0

    # --- what the facet returns into the guide (added 2026-10-06) ---------
    # A facet cut at an angle to the guide reflects the mode into a beam
    # tilted by twice that angle. The fraction of it that re-enters the guided
    # mode is the overlap of the mode with itself under a transverse phase
    # ramp k0 n_eff sin(2 theta) across the in-plane coordinate, which is
    # evaluated on the solved field rather than on a Gaussian of it; a shallow
    # ridge's tip mode is not Gaussian. The reflectivity of the face itself is
    # the coating's figure where one is declared and the bare Fresnel step
    # otherwise. Both are reported, since a coating is a specification and the
    # geometry is on the mask.
    inten = np.abs(field) ** 2
    q = 2 * np.pi / lam * n_guide * np.sin(np.radians(2 * angle))
    ramp = np.exp(1j * q * x)[:, None]
    num = float(abs(np.sum(inten * ramp * dA)) ** 2)
    den = float(np.sum(inten * dA)) ** 2
    eta_tilt = num / den if den > 0 else 0.0
    r_bare = ((n_guide - cfg.partner_index) / (n_guide + cfg.partner_index)) ** 2
    r_face = cfg.ar_reflectivity if cfg.ar_reflectivity is not None else r_bare
    refl_into_guide = r_face * eta_tilt
    refl_bare = r_bare * eta_tilt

    payload = {
        "enabled": True,
        "port": label,
        "port_guide": "slab strip" if strip else "ridge tip",
        "mode_height_centre_um": _y_mode,
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
        # the reflection
        "face_reflectivity": float(r_face),
        "face_reflectivity_bare": float(r_bare),
        "face_reflectivity_source": ("declared coating" if cfg.ar_reflectivity is not None
                                     else "bare Fresnel step at the tip mode's index"),
        "tilt_overlap": float(eta_tilt),
        "tilt_suppression_dB": to_dB(eta_tilt) if eta_tilt > 0 else float("inf"),
        "reflection_into_guide": float(refl_into_guide),
        "reflection_into_guide_dB": to_dB(refl_into_guide) if refl_into_guide > 0 else float("inf"),
        "reflection_into_guide_uncoated": float(refl_bare),
        "reflection_into_guide_uncoated_dB": to_dB(refl_bare) if refl_bare > 0 else float("inf"),
    }

    if cfg.gap_um > 0 and abs(residual) > 0.1 * tol_x:
        ctx.warn(
            f"at the {label} facet the beam crosses the {cfg.gap_um:g} um coupling gap at "
            f"{payload['angle_in_gap_deg']:.1f} deg and arrives {walk:.3f} um to one "
            f"side. {abs(residual):.3f} um of that is uncompensated, against an alignment "
            f"tolerance of {tol_x:.3f} um, so {100 * abs(residual) / tol_x:.0f} % of the "
            "budget is spent before the assembly begins. Offset the partner by the "
            "walk-off in facet.offset_x_um"
        )
    if tol_x < 0.3 or tol_y < 0.3:
        ctx.warn(
            f"a {cfg.tolerance_dB:.1f} dB alignment tolerance of {min(tol_x, tol_y):.2f} um "
            f"is demanded of the assembly at the {label} facet, which is tight for passive placement"
        )
    return payload


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.facet
    if not cfg.enabled:
        ctx.put("facet", {"enabled": False})
        return {"enabled": False}

    width = cfg.facet_width_um or design.layout.taper_tip_width_um
    payload = _port(design, ctx, lib, cfg, design.layout.input_facet_angle_deg, width, "input")
    payload["assumed_loss_dB_in_design"] = design.cavity.rsoa.coupling_loss_dB_per_facet

    # `coupling_loss_dB_per_facet` belongs to the reflective gain chip of a laser
    # cavity. On a design that declares no cavity it is a schema default, and
    # comparing a computed coupling against it grades the geometry on a figure
    # nobody wrote for it. The first design to reach this stage without a cavity
    # was a modulator test chip coupling to a lensed fibre, on 2026-09-06, whose
    # computed 1.93 dB was silently compared against the default 1.50.
    assumed = design.cavity.rsoa.coupling_loss_dB_per_facet
    if not design.cavity.enabled:
        payload["assumed_loss_dB_in_design"] = None
        payload["assumption_source"] = (
            "none: the design declares no cavity, so no coupling loss is assumed "
            "anywhere in it and the computed figure is graded against nothing"
        )
        ctx.warn(
            f"the facet is computed to lose {payload['total_loss_dB']:.2f} dB and the "
            "design states no coupling loss to compare it with, the assumed figure "
            "belonging to a laser cavity this design does not declare. Where the "
            "coupling budget matters, write it into an acceptance target rather than "
            "leaving it for a reader to infer from this stage"
        )
    elif payload["total_loss_dB"] > assumed + 0.5:
        ctx.warn(
            f"the facet is computed to lose {payload['total_loss_dB']:.2f} dB against the "
            f"{assumed:.2f} dB assumed in the design. The dominant term is "
            f"{max(('overlap', payload['mode_overlap_loss_dB']), ('Fresnel', payload['fresnel_loss_dB']), ('the facet angle', payload['angle_loss_dB']), key=lambda kv: kv[1])[0]}"
        )
    # The reverse direction, added 2026-08-16. The guard above catches an
    # assumption that is optimistic, which is the dangerous case. It said
    # nothing about one that is pessimistic, and a design carried a coupling
    # loss of 2.850 dB against a computed 1.981 for eight days, the 2.850 being
    # the figure computed for a different cross-section and inherited with the
    # rest of the file. A stale assumption is worth reporting whichever way it
    # points: the direction tells you whether the design is at risk or merely
    # understated, and neither is what the file claims to carry.
    elif assumed > payload["total_loss_dB"] + 0.5:
        payload["assumption_is_pessimistic_by_dB"] = assumed - payload["total_loss_dB"]
        ctx.warn(
            f"the design assumes {assumed:.2f} dB of coupling loss per facet and this geometry "
            f"is computed to lose {payload['total_loss_dB']:.2f} dB, so the assumption is "
            f"{assumed - payload['total_loss_dB']:.2f} dB pessimistic. The threshold gain, the "
            "output power and the linewidth all carry that margin. Confirm the figure belongs to "
            "this cross-section and was not inherited from another"
        )

    # --- the output port, where the design declares a partner there --------
    # The laser's output facet faces a fibre and the cavity's loss budget does
    # not contain it; what matters there is the coupling to the fibre and the
    # fraction the facet returns toward the mirror, which reaches the laser as
    # external feedback.
    if cfg.output is not None:
        o = cfg.output
        lay = design.layout
        w_out = (o.facet_width_um or lay.output_taper_tip_width_um
                 or lay.taper_tip_width_um)
        payload["output"] = _port(design, ctx, lib, o, lay.output_facet_angle_deg,
                                  float(w_out), "output")
        if payload["output"]["reflection_into_guide"] > 1.0e-3:
            ctx.warn(
                f"the output facet returns {payload['output']['reflection_into_guide']:.2e} of the "
                f"emitted power into the guide ({payload['output']['reflection_into_guide_dB']:.1f} dB), "
                f"the face reflecting {payload['output']['face_reflectivity']:.2e} "
                f"({payload['output']['face_reflectivity_source']}) and the "
                f"{lay.output_facet_angle_deg:g} degree angle suppressing "
                f"{payload['output']['tilt_suppression_dB']:.1f} dB of it. That return reaches "
                "the mirror as external feedback, which no cavity row grades; angle the "
                "facet further, coat it, or bound it in a target",
                key="facet.output_feedback")

    ctx.put("facet", payload)
    ctx.write_stage("facet", payload)
    return payload
