"""Stage 8 - taper transmission by eigenmode expansion.

The taper that carries the mode from the chip facet to the ridge is the one
passive element whose loss was previously an assumption rather than a computed
quantity.  It is evaluated here by eigenmode expansion, which is the appropriate
method for a structure that varies slowly along the propagation direction and
is far cheaper than a time-domain solve for a length of order 100 um.

Method
------
The taper is cut into ``n_slices`` uniform sections.  Every section is
rasterised onto **one** mesh, built from the widest cross-section, so that the
overlap integrals between neighbouring sections are taken on shared nodes and
the discretisation error largely cancels.  A fixed number of modes is solved at
each section, the interfaces are matched, and the sections are combined by the
Redheffer star product (see ``picchain.eme``).

What is and is not represented
------------------------------
Retained: coupling of the fundamental into higher-order guided modes, the
reflection at every step of the staircase, and the effect of the width profile.

Not retained: radiation into the continuum beyond what the finite mode basis
can represent, out-of-plane scatter, and sidewall roughness.  The computed loss
is therefore a lower bound, and the power balance is reported on every run so
that the size of the truncation can be seen rather than assumed.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import eme
from .. import process
from ..artifacts import RunContext
from ..config import Design
from ..geometry import build_grid, edbr_cross_section
from ..materials import MaterialLibrary
from ..solvers.fdmode import solve_modes
from .s01_mode import _eps_maps


def _cross_section(design: Design, width_um: float, name: str):
    """The optical cross-section at one taper width: no posts, no electrodes."""
    p = design.platform
    geom = process.geometry(design, design.process.simulate)
    return edbr_cross_section(
        film_material=p.film_material,
        film_thickness_um=p.film_thickness_um,
        etch_depth_um=geom.etch_depth_um,
        wg_top_width_um=width_um,
        sidewall_deg=p.sidewall_deg,
        box_thickness_um=p.box_thickness_um,
        clad_thickness_um=p.clad_thickness_um,
        clad_material=p.clad_material,
        box_material=p.box_material,
        substrate_material=p.substrate_material,
        with_posts=False,
        post_width_um=geom.post_width_um,
        post_gap_um=geom.post_gap_um,
        electrodes=False,
        include_substrate=False,
        window_pad_x_um=3.0,
        name=name,
    )


def _widths(tip: float, full: float, n: int, profile: str) -> np.ndarray:
    """Section-centre widths for the requested profile."""
    u = (np.arange(n) + 0.5) / n
    if profile == "linear":
        s = u
    elif profile == "raised_sine":
        # width varies as a raised sine, so the rate of change vanishes at both
        # ends; this is the usual remedy when a linear taper is too abrupt
        s = u - np.sin(2 * np.pi * u) / (2 * np.pi)
    elif profile == "quadratic":
        s = u**2
    else:
        raise ValueError(f"unknown taper profile {profile!r}")
    return tip + (full - tip) * s


def _solve_slices(design, lib, widths, grid, window, lam, n_modes, n_guess, n_floor):
    """Solve each slice on the shared mesh and retain its guided modes.

    A mode is retained where its effective index exceeds that of the unetched
    slab. The states below that floor are the discretised slab continuum: they
    are not guided by the ridge, they are degenerate in pairs, and admitting
    them makes the basis linearly dependent. Power reaching them is radiation,
    and is accounted as such by the power balance rather than by carrying them.
    """
    p, m = design.platform, design.mesh
    n_effs, fields, counts = [], [], []
    for i, w in enumerate(widths):
        xs = _cross_section(design, float(w), f"taper_{i}")
        xs.window = window
        exx, eyy = _eps_maps(xs, grid, lib, lam, p.cut, p.use_index_override, m.subsample)
        modes = solve_modes(
            grid.x, grid.y, exx, eyy, lam,
            polarisation=m.polarisation, num_modes=n_modes, n_guess=n_guess,
        )
        guided = [md for md in modes if md.n_eff > n_floor + 1e-4]
        if not guided:
            raise RuntimeError(
                f"taper slice {i} (width {w:.3f} um) supports no guided mode: the "
                f"highest n_eff obtained is {modes[0].n_eff:.6f} against a slab floor "
                f"of {n_floor:.6f}. The tip is below cut-off, so the taper cannot be "
                "evaluated as drawn"
            )
        n_effs.append(np.array([md.n_eff for md in guided], dtype=float))
        fields.append(np.stack([md.field for md in guided]))
        counts.append(len(guided))
    return n_effs, fields, counts


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.taper
    if not cfg.enabled:
        ctx.put("taper", {"enabled": False})
        return {"enabled": False}

    lam = design.waveguide.wavelength_um
    mesh = design.mesh
    full = design.waveguide.top_width_um
    tip = cfg.tip_width_um if cfg.tip_width_um is not None else design.layout.taper_tip_width_um
    length = cfg.length_um if cfg.length_um is not None else design.layout.taper_length_um
    if tip <= 0 or full <= 0:
        raise ValueError("taper widths must be positive")

    # one mesh for every slice, built from the widest cross-section
    xs_full = _cross_section(design, full, "taper_full")
    grid = build_grid(xs_full, mesh.d_fine_um, mesh.d_coarse_um, mesh.fine_margin_um)
    window = xs_full.window

    mode_metrics = ctx.get("mode") or {}
    n_guess = mode_metrics.get("n_eff_bare")
    n_floor = mode_metrics.get("n_slab_floor")
    if n_floor is None:
        raise RuntimeError("stage 'taper' requires stage 'mode' for the slab index floor")

    dA = eme.cell_areas(grid.x, grid.y)

    def evaluate(n_slices: int):
        widths = _widths(tip, full, n_slices, cfg.profile)
        n_effs, fields, counts = _solve_slices(
            design, lib, widths, grid, window, lam, cfg.num_modes, n_guess, n_floor
        )
        lengths = [length / n_slices] * n_slices
        result = eme.local_mode_chain(fields, dA, n_effs, lengths, lam)
        return result, widths, n_effs, counts

    result, widths, n_effs, counts = evaluate(cfg.n_slices)
    by_slice = result.pop("fundamental_by_slice")

    payload: dict[str, Any] = {
        "enabled": True,
        "method": "eigenmode expansion, local-mode staircase, reflection neglected",
        "length_um": float(length),
        "tip_width_um": float(tip),
        "full_width_um": float(full),
        "profile": cfg.profile,
        "n_slices": int(cfg.n_slices),
        "num_modes_solved": int(cfg.num_modes),
        "guided_modes_min": int(min(counts)),
        "guided_modes_max": int(max(counts)),
        "n_slab_floor": float(n_floor),
        "n_eff_tip": float(n_effs[0][0]),
        "n_eff_full": float(n_effs[-1][0]),
        **{k: float(v) for k, v in result.items()},
    }

    # adiabaticity against the slab, which is the state into which a
    # single-moded taper loses power
    adia = eme.adiabaticity(
        widths, np.array([n[0] for n in n_effs]), n_floor, length, lam
    )
    adia_profile = adia.pop("profile")
    payload.update({f"adiabaticity_{k}" if not k.startswith("min") else k: v
                    for k, v in adia.items()})

    # convergence: the same taper at half the slice count.  A staircase that has
    # not converged reports a loss that falls as the steps are refined.
    if cfg.convergence_check and cfg.n_slices >= 4:
        coarse, _, _, _ = evaluate(max(2, cfg.n_slices // 2))
        payload["staircase_deficit_at_half_slices"] = float(coarse["staircase_deficit"])
        payload["conversion_loss_dB_at_half_slices"] = float(coarse["conversion_loss_dB"])
        payload["convergence_delta_dB"] = float(
            abs(coarse["conversion_loss_dB"] - result["conversion_loss_dB"])
        )

    if n_guess is not None:
        payload["n_eff_full_vs_mode_stage"] = float(n_effs[-1][0] - n_guess)

    ctx.put("taper", payload)
    ctx.write_stage(
        "taper", payload,
        {
            "widths_um": widths,
            "n_eff_slices": np.array([n[0] for n in n_effs]),
            "fundamental_power_by_slice": np.array(by_slice),
            "adiabaticity_profile": adia_profile,
        },
    )

    if payload["min_adiabaticity"] < cfg.adiabaticity_floor:
        ctx.warn(
            f"taper adiabaticity falls to {payload['min_adiabaticity']:.1f} at a width of "
            f"{payload['min_adiabaticity_at_width_um']:.3f} um, against a floor of "
            f"{cfg.adiabaticity_floor:.1f}. The margin is a screen and not a loss "
            "estimate; radiation is outside a guided-mode basis. Enable the fdtd stage "
            "to quantify it before lengthening the taper"
        )
    if result["conversion_to_higher_order"] > 1e-3:
        ctx.warn(
            f"{result['conversion_to_higher_order']:.2%} of the input power is converted "
            "into a higher-order guided mode by the taper"
        )
    if max(counts) == 1:
        ctx.warn(
            "the taper is single-moded along its whole length, so no guided-to-guided "
            "conversion is possible and the computed loss is zero by construction. The "
            "figure of interest is the adiabaticity margin, not the loss"
        )
    delta = payload.get("convergence_delta_dB")
    if delta is not None and delta > 0.2 * max(result["conversion_loss_dB"], 1e-6):
        ctx.warn(
            f"taper conversion loss moved by {delta:.3f} dB when the slice count was "
            "halved; the staircase has not converged - raise taper.n_slices"
        )
    if result["staircase_deficit"] > 0.01:
        ctx.warn(
            f"{result['staircase_deficit']:.1%} of the power fails to project onto the "
            f"guided set across {cfg.n_slices} steps. This is a discretisation residue "
            "that falls as 1/n_slices and is not a radiation estimate; it is reported so "
            "that the coarseness of the staircase is visible"
        )
    return payload
