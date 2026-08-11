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

What this does not give
-----------------------
A loss in decibels per turn. That requires a leaky-mode solve with an absorbing
boundary, or a time-domain solve of the bend itself. The stage reports the
radius at which the caustic enters the guide, which is the point at which such a
solve becomes necessary.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..geometry import build_grid
from ..materials import MaterialLibrary
from ..solvers.fdmode import bend_diagnostics, solve_bend_modes, solve_modes
from .s01_mode import _build, _eps_maps
from .s09_fdtd import _effective_indices


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
    }
    ctx.put("bend", payload)
    ctx.write_stage("bend", payload, {
        "radii_um": np.array([r["radius_um"] for r in rows]),
        "shift_um": np.array([r.get("shift_from_straight_um", np.nan) for r in rows]),
    })

    failed = [r for r in rows if not r.get("solved")]
    if failed:
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
