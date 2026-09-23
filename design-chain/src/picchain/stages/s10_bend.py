"""Stage 10 - bend modes and the radius at which a bend begins to radiate.

A bend is not a straight guide with a label. The mode shifts toward the outer
wall, its effective index changes, and beyond a radius that depends on the index
contrast it ceases to be bound at all. None of that is visible to a stage that
solves only the straight cross-section, and the radius chosen for a routing bend
is otherwise an assumption like any other.

Method
------
The bend is mapped onto an equivalent straight guide by conformal
transformation, which grades the index across the section as exp(x/R). The same
mode solver then applies. Two quantities follow: the effective index of the bend
mode, and the position of the radiation caustic, being the point at which the
graded cladding index rises to meet the mode index. The fraction of the mode
lying beyond that point rises as the bend tightens and is reported as an
indicator, not as a loss.

The leaky solve, added 2026-09-23
--------------------------------
Where the finite-element solver is available, the same radii are solved a
second time by finite elements on a window widened by several micrometres with
an absorbing margin at its lateral edges, the bend entering through the
(1 + x/R)^2 scaling of the permittivity. The imaginary part of the effective
index gives the radiation loss in decibels per centimetre, which the conformal
solve cannot, and the solve returns an answer at radii where the conformal one
cannot, the leaky mode having a boundary to leak into. The two index shifts are
reported side by side; on a 0.9 um tantalate ridge the conformal shift read
1.33 times the finite-element one at every radius, which is the second-order
signature of a semi-vectorial operator under the transformation and is
recorded as such rather than adjudicated.

What this does not give
-----------------------
A time-domain solve of the bend itself, or a loss at a radius the absorbing
margin cannot reach. The conformal stage reports the radius at which the
caustic enters the guide; the leaky solve reports what happens there.
"""

from __future__ import annotations

import math

from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..geometry import build_grid
from ..materials import MaterialLibrary
from ..solvers.fdmode import bend_diagnostics, solve_bend_modes, solve_modes
from .s01_mode import _build, _eps_maps
from .s09_fdtd import _effective_indices


def _leaky_solve(design: Design, ctx: RunContext, lib: MaterialLibrary, xs, lam: float,
                 radii: list[float], n_straight_fd: float) -> dict[str, Any]:
    """The bend by finite elements with an absorbing margin, at each radius."""
    from ..geometry import widen_cross_section
    from ..solvers import femmode
    from .s13_fem import _eps_scalar
    if not femmode.available():
        return {"performed": False, "reason": femmode.unavailable_reason()}
    p, m, cfg = design.platform, design.mesh, design.fem
    extra = float(getattr(design.bend, "leaky_margin_um", 6.0))
    absorber = 3.0
    wide = widen_cross_section(xs, extra, 0.0, name="bend_leaky")
    eps = _eps_scalar(wide, lib, lam, p.cut, p.use_index_override, 0)
    kw = dict(num_modes=4, element_order=1, resolution_max_um=max(cfg.resolution_max_um, 0.35),
              fine_resolution_um=cfg.resolution_fine_um, fine_distance_um=cfg.fine_distance_um,
              n_guess=n_straight_fd, absorber_um=absorber, absorber_strength=0.3)

    def _te(res):
        # The absorbing margin supports modes of its own, with imaginary
        # indices of order one; the guided or leaky mode is the TE mode with
        # the smallest imaginary part, its loss being small against those.
        cands = [q for q in res.modes if q.te_fraction > 0.5]
        return min(cands, key=lambda q: abs(q.n_eff_imag)) if cands else None

    try:
        straight = _te(femmode.solve_cross_section(wide, eps, lam, **kw))
    except Exception as ex:  # pragma: no cover - the solver's own failure is reported, not raised
        return {"performed": False, "reason": f"the straight reference failed: {ex}"}
    if straight is None:
        return {"performed": False, "reason": "no TE mode on the widened window"}
    rows = []
    for R in radii:
        try:
            md = _te(femmode.solve_cross_section(wide, eps, lam, radius_um=float(R), **kw))
        except Exception as ex:  # pragma: no cover
            rows.append({"radius_um": float(R), "solved": False, "reason": str(ex)}); continue
        if md is None:
            rows.append({"radius_um": float(R), "solved": False, "reason": "no TE mode"}); continue
        rows.append({"radius_um": float(R), "solved": True, "n_eff": md.n_eff,
                     "dn_eff_from_straight": md.n_eff - straight.n_eff,
                     "loss_dB_per_cm": md.loss_dB_per_m(lam) / 100.0,
                     "loss_dB_per_quarter_turn": md.loss_dB_per_m(lam) * (math.pi / 2) * float(R) * 1e-6,
                     "te_fraction": md.te_fraction})
    return {"performed": True,
            "method": "finite elements on a window widened by %.1f um with a %.1f um absorbing margin, "
                      "the bend as the (1 + x/R)^2 scaling of the permittivity" % (extra, absorber),
            "window_um": list(wide.window), "straight_n_eff": straight.n_eff,
            "straight_loss_floor_dB_per_cm": straight.loss_dB_per_m(lam) / 100.0,
            "rows": rows}


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.bend
    if not cfg.enabled or not cfg.radii_um:
        ctx.put("bend", {"enabled": False})
        return {"enabled": False}

    p, m = design.platform, design.mesh
    lam = design.waveguide.wavelength_um
    xs = _build(design, with_posts=False, electrodes=False, name="bend")
    grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, eyy = _eps_maps(xs, grid, lib, lam, p.cut, p.use_index_override, m.subsample)

    straight = solve_modes(grid.x, grid.y, exx, eyy, lam,
                           polarisation=m.polarisation, num_modes=1)[0]
    # The guard compares the guiding strength of the ridge against that of the
    # slab beside it, and both are indices of the *vertical* stack: 1.87 under
    # the ridge against 1.66 beside it on the validation baseline. The guided
    # mode index is not the right ceiling, being lower than the ridge stack and
    # lower than the bend mode it is meant to admit.
    n_ridge, n_beside = _effective_indices(design, lib)
    # the cladding the mode radiates into is the unetched slab, not the oxide
    n_slab = float((ctx.get("mode") or {}).get("n_slab_floor") or 0.0)
    if n_slab <= 0:
        raise RuntimeError("stage 'bend' requires stage 'mode' for the slab index floor")

    rows: list[dict[str, Any]] = []
    for R in sorted(cfg.radii_um, reverse=True):
        try:
            mode = solve_bend_modes(grid.x, grid.y, exx, eyy, lam, radius_um=float(R),
                                    polarisation=m.polarisation, num_modes=1,
                                    n_guess=straight.n_eff,
                                    n_core_eff=straight.n_eff, n_clad_eff=n_slab)[0]
        except RuntimeError as exc:
            rows.append({"radius_um": float(R), "solved": False, "reason": str(exc)})
            continue
        d = bend_diagnostics(mode, n_slab**2, float(R))
        d["solved"] = True
        d["dn_eff_from_straight"] = float(mode.n_eff - straight.n_eff)
        d["shift_from_straight_um"] = float(
            d["lateral_centroid_um"]
            - bend_diagnostics(straight, n_slab**2, 1e9)["lateral_centroid_um"]
        )
        rows.append(d)

    solved = [r for r in rows if r.get("solved")]
    inside = [r for r in solved if r.get("caustic_inside_window")]

    # the same radii by finite elements with an absorbing margin, which gives
    # the radiation loss and an answer where the conformal solve has none
    leaky = _leaky_solve(design, ctx, lib, xs, lam,
                         [float(r) for r in sorted(cfg.radii_um, reverse=True)], float(straight.n_eff))
    if leaky.get("performed"):
        by_r = {r["radius_um"]: r for r in leaky["rows"] if r.get("solved")}
        for r in rows:
            q = by_r.get(r["radius_um"])
            if q:
                r["leaky_loss_dB_per_cm"] = q["loss_dB_per_cm"]
                r["leaky_dn_eff_from_straight"] = q["dn_eff_from_straight"]

    payload: dict[str, Any] = {
        "enabled": True,
        "method": "conformal transformation of the bend into a straight guide",
        "n_eff_straight": float(straight.n_eff),
        "n_slab_floor": n_slab,
        "radii_um": [float(r) for r in sorted(cfg.radii_um, reverse=True)],
        "rows": rows,
        "tightest_radius_solved_um": min((r["radius_um"] for r in solved), default=None),
        "caustic_enters_window_at_um": max(
            (r["radius_um"] for r in inside), default=None),
        "leaky": leaky,
        "tightest_radius_with_loss_below_0p1_dB_per_cm_um": min(
            (r["radius_um"] for r in leaky.get("rows", []) if r.get("solved") and r["loss_dB_per_cm"] < 0.1),
            default=None) if leaky.get("performed") else None,
    }
    ctx.put("bend", payload)
    ctx.write_stage("bend", payload, {
        "radii_um": np.array([r["radius_um"] for r in rows]),
        "shift_um": np.array([r.get("shift_from_straight_um", np.nan) for r in rows]),
    })

    failed = [r for r in rows if not r.get("solved")]
    if failed:
        answered = [r for r in failed if r.get("leaky_loss_dB_per_cm") is not None]
        if answered:
            ctx.warn(
                f"{len(failed)} of {len(rows)} radii could not be solved by conformal "
                "transformation, the graded cladding exceeding the core index within the "
                "window. The leaky finite-element solve answers there: "
                + ", ".join(f"{r['radius_um']:.0f} um radiates {r['leaky_loss_dB_per_cm']:.3g} dB/cm" for r in answered)
            )
        else:
            ctx.warn(
                f"{len(failed)} of {len(rows)} radii could not be solved by conformal "
                "transformation, the graded cladding exceeding the core index within the "
                "window. Those radii require a leaky-mode or time-domain solve"
            )
    if payload["caustic_enters_window_at_um"] is not None:
        ctx.warn(
            f"the radiation caustic enters the computation window at a radius of "
            f"{payload['caustic_enters_window_at_um']:.0f} um. At and below that "
            "radius the bend is expected to radiate and the loss is not computed here"
        )
    return payload
