"""Stage 19 - an all-pass ring on a bus, assembled from the loop and the coupler.

Every other stage of this chain models a component. The `cavity` stage combines
components for one arrangement, being a gain chip behind a feed and a
distributed mirror, and the `circuit` stage opens by stating that the
arrangement it encodes "cannot be applied to a resonator on a bus". The
consequence was checkable before this stage existed: no design declared a target
on a loaded quality factor, on an extinction, on a finesse or on a free spectral
range, while a study of a ring computed all four in a script beside itself.

What is assembled
-----------------
One loop of circumference ``2 pi R`` carrying an amplitude ``a`` per turn, and
one lossless point coupler leaving an amplitude ``t`` in the bus. The closed
forms are in [`picchain.resonator`](../resonator.py), which is where the
arithmetic is tested. This stage supplies the two numbers and reports what
follows.

Where the two numbers come from
-------------------------------
``t`` comes from the power coupling. Where the `fdtd` stage has solved a point
coupler, its measured value is taken and the declared one is reported beside it.
Where it has not, ``resonator.kappa_squared`` must be declared, and the stage
refuses rather than reaching for a default. A ring assembled from a coupling
nobody measured and nobody wrote down is the failure this refusal prevents.

``a`` comes from ``platform.propagation_loss_dB_per_cm``, which on most stacks
is an assumption rather than a measurement. **The loss is therefore an axis and
not an input to an answer.** The stage reports the device at the declared value
and again at every value of ``resonator.loss_sweep_dB_per_cm``, and it reports
the loss at which the drawn coupler would be critically coupled, which is the
inverse a design actually needs: the coupler is drawn once and the loss of the
process is what is unknown.

What is not carried
-------------------
Bend radiation. The `bend` stage returns an index shift and the distance to the
radiation caustic, and no stage of this chain returns a loss in decibels per
centimetre for a curved guide. Where a figure for it is known by other means it
is declared as ``resonator.excess_loss_dB_per_turn`` and enters the round trip
there, marked as the assumption it is.

Dispersion of the coupler. The power coupling is taken at one wavelength and
held across the band, so the free spectral range is correct and the depth of a
resonance far from the design wavelength is not.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .. import resonator as rz
from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary


def _kappa_squared(design: Design, ctx: RunContext) -> tuple[float, str, float | None]:
    """The power coupling, its provenance, and the declared value beside it.

    A measurement is preferred to a declaration and the two are reported
    together. The guard is on the presence of a measurement of the right kind,
    and not on the absence of a declaration: an `fdtd` payload for a taper or a
    grating carries no coupling, and reading one from it would return whatever
    key happened to be there.
    """
    declared = design.resonator.kappa_squared
    fdtd = ctx.get("fdtd") or {}
    measured = None
    if fdtd.get("enabled") and fdtd.get("structure") == "coupler":
        measured = fdtd.get("kappa2")
    if measured is not None:
        return float(measured), "fdtd point-coupler solve", declared
    if declared is not None:
        return float(declared), "declared in the design file", None
    raise RuntimeError(
        "stage 'resonator' has no power coupling: declare resonator.kappa_squared, "
        "or run the fdtd stage with fdtd.structure: coupler"
    )


def _declared_extinction_floor(design: Design) -> float | None:
    """The extinction the design requires, taken from the design's own targets.

    The window of propagation loss over which a drawn coupler meets an
    extinction is the design statement this stage exists to make, and it needs
    the required depth. Reading it from a second field beside the target would
    let the two drift, and a drift between a requirement and the figure a report
    quotes against it is invisible while each remains internally consistent.
    """
    floors = [t.min for t in design.targets
              if t.metric == "resonator.extinction_dB" and t.min is not None]
    return max(floors) if floors else None


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.resonator
    if not cfg.enabled:
        ctx.put("resonator", {"enabled": False})
        return {"enabled": False}

    mode = ctx.get("mode") or {}
    n_g = mode.get("n_g")
    if not n_g:
        raise RuntimeError("stage 'resonator' requires stage 'mode' for the group index")
    n_eff = float(mode.get("n_eff_bare") or 0.0)

    lam = design.waveguide.wavelength_um
    radius = float(cfg.radius_um)
    length = 2.0 * math.pi * radius
    loss = float(design.platform.propagation_loss_dB_per_cm)
    excess = float(cfg.excess_loss_dB_per_turn)
    kappa2, kappa_source, kappa_declared = _kappa_squared(design, ctx)

    point = rz.solve_point(lam, float(n_g), length, loss, kappa2, excess)

    rows = []
    for value in sorted({*cfg.loss_sweep_dB_per_cm, loss}):
        p = rz.solve_point(lam, float(n_g), length, float(value), kappa2, excess)
        rows.append(p.as_dict())

    critical_loss = rz.loss_dB_per_cm_for_critical_coupling(kappa2, length, excess)
    kappa_critical = rz.kappa_squared_for_critical_coupling(loss, length, excess)
    bend = _bend_at_the_ring_radius(ctx, radius, mode, lam)

    floor_dB = _declared_extinction_floor(design)
    window: tuple[float | None, float | None] = (None, None)
    if floor_dB is not None:
        window = rz.loss_window_for_extinction(floor_dB, kappa2, length, excess)

    payload: dict[str, Any] = {
        "enabled": True,
        "topology": "all-pass, one bus and one point coupler",
        "radius_um": radius,
        "round_trip_um": length,
        "n_eff": n_eff,
        "n_group": float(n_g),
        "kappa_squared_source": kappa_source,
        "kappa_squared_declared": kappa_declared,
        # the operating point, flattened so that a target may name any of it
        **point.as_dict(),
        # the two inverses, which is what a design reads to place a gap
        "loss_dB_per_cm_for_critical_coupling": critical_loss,
        "kappa_squared_for_critical_coupling": kappa_critical,
        "loss_is_an_assumption": True,
        # the requirement read as a tolerance on the loss, which is what a stack
        # whose loss is unmeasured actually has to satisfy
        "declared_extinction_floor_dB": floor_dB,
        "loss_window_for_the_declared_extinction_dB_per_cm": list(window),
        "loss_rows": rows,
        **bend,
    }

    ctx.put("resonator", payload)
    ctx.write_stage("resonator", payload, {
        "loss_dB_per_cm": np.array([r["loss_dB_per_cm"] for r in rows]),
        "extinction_dB": np.array([
            r["extinction_dB"] if math.isfinite(r["extinction_dB"]) else np.nan
            for r in rows]),
        "q_loaded": np.array([r["q_loaded"] for r in rows]),
    })

    _report(design, ctx, payload, point, mode)
    return payload


def _bend_at_the_ring_radius(ctx: RunContext, radius_um: float,
                            mode: dict[str, Any], lam_um: float) -> dict[str, Any]:
    """What the bend solve says about a guide of exactly this radius.

    The `bend` stage reports a list of radii and two aggregates over it, and
    neither aggregate is addressable by an acceptance target: the radius at
    which the caustic first enters the window is absent altogether where no
    radius radiates, and a target on an absent metric grades nothing. This
    stage knows which radius the ring is drawn at, so it reads that row and
    returns the quantities as scalars.

    **The power beyond the caustic is a property of the window and not of the
    device**, and it is not the quantity to grade. The bend solve integrates the
    field outside the caustic, so it returns nothing at all where the caustic
    falls outside the solved window, which is the case whenever the bend is
    comfortable. A target reading that quantity as zero would pass every wide
    bend for the reason that the instrument could not see it, and would begin to
    fail only once the caustic came inside, which is already too late.

    The window-independent statement is how far the caustic sits in units of the
    mode's own lateral decay. The field falls as ``exp(-gamma x)`` beyond the
    guide, with ``gamma = k0 sqrt(n_eff^2 - n_floor^2)`` from the straight solve,
    so the distance to the caustic in decay lengths is what a tunnelling loss
    depends on. That figure is reported here and is the one carrying a target.
    """
    bend = ctx.get("bend") or {}
    absent = {
        "bend_solved_at_the_ring_radius": False,
        "bend_radius_um": None,
        "bend_dn_eff_from_straight": None,
        "bend_caustic_x_um": None,
        "bend_caustic_inside_window": None,
        "bend_caustic_in_decay_lengths": None,
        "bend_power_beyond_caustic": None,
    }
    if not bend.get("enabled"):
        return absent
    rows = [r for r in (bend.get("rows") or [])
            if r.get("solved") and abs(float(r["radius_um"]) - radius_um) <= 1e-6]
    if not rows:
        return absent
    row = rows[0]
    inside = bool(row.get("caustic_inside_window"))
    beyond = row.get("power_beyond_caustic")
    beyond = (float(beyond)
              if beyond is not None and math.isfinite(float(beyond)) else None)

    caustic = float(row.get("caustic_x_um") or 0.0)
    n_eff = float(mode.get("n_eff_bare") or 0.0)
    floor = float(mode.get("n_slab_floor") or 0.0)
    decay_lengths = None
    if n_eff > floor > 0.0 and caustic > 0.0:
        gamma = 2.0 * math.pi / lam_um * math.sqrt(n_eff * n_eff - floor * floor)
        decay_lengths = float(gamma * caustic)

    return {
        "bend_solved_at_the_ring_radius": True,
        "bend_radius_um": float(row["radius_um"]),
        "bend_dn_eff_from_straight": float(row.get("dn_eff_from_straight") or 0.0),
        "bend_caustic_x_um": caustic,
        "bend_caustic_inside_window": inside,
        "bend_caustic_in_decay_lengths": decay_lengths,
        "bend_power_beyond_caustic": beyond,
    }


def _report(design: Design, ctx: RunContext, payload: dict[str, Any],
            point: rz.RingPoint, mode: dict[str, Any]) -> None:
    """Findings the targets do not express."""
    cfg = design.resonator

    # The two widths are the same quantity by two derivations. Where they part,
    # the resonance is broad enough that the expansion about it has stopped
    # holding, and any figure quoted from the literature form is that far out.
    exact, approx = point.fwhm_um, point.fwhm_um_small_angle
    if exact > 0 and abs(approx - exact) / exact > rz.WIDTH_FORM_TOLERANCE:
        ctx.warn(
            f"the width by the small-angle form is {approx / exact - 1.0:+.1%} from the "
            f"exact inversion at a finesse of {point.finesse:.1f}. The exact figure is "
            "reported and a literature value computed from the expansion differs by "
            "this much",
            key="resonator.width_form_disagreement",
        )

    # The loss is the axis and the extinction is what moves along it.
    critical = payload["loss_dB_per_cm_for_critical_coupling"]
    if critical is None:
        ctx.warn(
            "the loss taken once per turn already exceeds what the coupler removes, so "
            "the ring is overcoupled at every propagation loss including zero. Open the "
            "gap or reduce resonator.excess_loss_dB_per_turn",
            key="resonator.critical_coupling_unreachable",
        )
    else:
        declared = float(design.platform.propagation_loss_dB_per_cm)
        where = {"over": "overcoupled", "under": "undercoupled",
                 "critical": "critically coupled"}[point.regime]
        depth = ("complete extinction" if not math.isfinite(point.extinction_dB)
                 else f"{point.extinction_dB:.1f} dB extinction")
        ctx.warn(
            f"the drawn coupling is critically coupled at {critical:.3f} dB/cm and at no "
            f"other loss. The design declares {declared:.3f} dB/cm, which places the ring "
            f"{where} at {depth}. The loss is an assumption on this platform and the "
            "extinction follows it",
            key="resonator.extinction_follows_an_assumed_loss",
        )

    lo, hi = payload["loss_window_for_the_declared_extinction_dB_per_cm"]
    floor_dB = payload["declared_extinction_floor_dB"]
    if floor_dB is not None and hi is not None:
        declared = float(design.platform.propagation_loss_dB_per_cm)
        edge = "below" if lo is not None and declared < lo else (
            "above" if declared > hi else None)
        span = f"{lo:.3f}" if lo is not None else "zero"
        if edge:
            ctx.warn(
                f"the {floor_dB:.0f} dB extinction the design requires is met for a "
                f"propagation loss between {span} and {hi:.3f} dB/cm, and the design "
                f"declares {declared:.3f}, which is {edge} that window",
                key="resonator.declared_loss_outside_the_extinction_window",
            )
        else:
            ctx.warn(
                f"the {floor_dB:.0f} dB extinction the design requires is met for a "
                f"propagation loss between {span} and {hi:.3f} dB/cm. The width of that "
                "window is a property of the required extinction alone, and the loss of "
                "this stack is an assumption rather than a measurement",
                key="resonator.extinction_requirement_is_a_loss_tolerance",
            )

    if not cfg.loss_sweep_dB_per_cm:
        ctx.warn(
            "no loss sweep is declared, so every figure here rests on one assumed "
            "propagation loss. Declare resonator.loss_sweep_dB_per_cm",
            key="resonator.loss_not_swept",
        )

    guided = mode.get("n_guided_modes")
    if guided is not None and int(guided) > 1:
        ctx.warn(
            f"the cross-section guides {int(guided)} modes, so the ring carries that many "
            "families of resonances and a transmission spectrum superimposes them. Every "
            "figure here describes the fundamental family alone",
            key="resonator.multimode_ring",
        )

    # The ring the coupler was solved on and the ring this stage assembles are
    # two declarations of one radius, and nothing else connects them.
    fdtd = ctx.get("fdtd") or {}
    solved_radius = fdtd.get("ring_radius_um") if fdtd.get("structure") == "coupler" else None
    if solved_radius and abs(float(solved_radius) - cfg.radius_um) > 1e-6:
        ctx.warn(
            f"the coupler was solved at a ring radius of {float(solved_radius):.1f} um and "
            f"the resonator is assembled at {cfg.radius_um:.1f} um. The coupling depends on "
            "the radius through the length over which the two guides stay close, so the "
            "measured value does not describe this ring",
            key="resonator.coupler_radius_disagreement",
        )

    bend = ctx.get("bend") or {}
    if bend.get("enabled"):
        caustic = bend.get("caustic_enters_window_at_um")
        if caustic is not None and cfg.radius_um <= float(caustic):
            ctx.warn(
                f"the radiation caustic enters the solved window at {float(caustic):.0f} um "
                f"and the ring is drawn at {cfg.radius_um:.0f} um, so the bend is radiating "
                "by an amount no stage of this chain computes. The round trip is modelled "
                "as a straight guide and the quality factor reported here is an upper bound",
                key="resonator.bend_radiates_and_is_not_computed",
            )
        if not payload.get("bend_solved_at_the_ring_radius"):
            ctx.warn(
                f"the bend stage solved no radius equal to the ring radius of "
                f"{cfg.radius_um:.1f} um, so the round trip is assembled from the straight "
                "cross-section with nothing establishing that a guide of this radius still "
                "guides. Add the ring radius to bend.radii_um",
                key="resonator.bend_radius_not_among_those_solved",
            )
    else:
        ctx.warn(
            "the bend stage is not enabled, so nothing has established that a guide of this "
            "radius still guides. Enable bend with the ring radius among bend.radii_um",
            key="resonator.bend_not_solved",
        )
