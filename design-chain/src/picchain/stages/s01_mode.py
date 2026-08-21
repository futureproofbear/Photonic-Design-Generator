"""Stage 1 - waveguide cross-section modes.

Produces, on one shared mesh:

* n_eff and n_g of the guided mode of the *bare* ridge,
* n_eff of the ridge *with* the Bragg posts present,
* dn_eff = n_eff(posts) - n_eff(bare), the index contrast the grating stage
  Fourier-analyses,
* confinement factors (in the electro-optic film, in the ridge, in the posts),

plus the field on the mesh, which stage 3 overlaps with the RF field.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import process
from ..artifacts import RunContext, dump_json
from ..config import Design
from ..geometry import CrossSection, build_grid, edbr_cross_section, material_mask, rasterise
from ..materials import MaterialLibrary
from ..solvers.fdmode import ModeResult, solve_modes, solve_slab


def _eps_maps(
    xs: CrossSection, grid, lib: MaterialLibrary, lam_um: float, cut: str, override: bool, subsample: int
) -> tuple[np.ndarray, np.ndarray]:
    exx, eyy = {}, {}
    for m in xs.materials_used():
        mat = lib[m]
        if mat.kind == "metal":
            # metal is opaque; a large real permittivity keeps the optical mode
            # out of it without introducing a complex eigenproblem.  The
            # electrodes sit >3 um from the ridge, so this is benign - stage 3
            # reports the mode overlap with the metal so it can be checked.
            exx[m] = eyy[m] = 1.0
        else:
            ex, ey, _ = mat.eps_optical_device(lam_um, cut, override)
            exx[m], eyy[m] = ex, ey
    return (
        rasterise(xs, grid, exx, subsample=subsample),
        rasterise(xs, grid, eyy, subsample=subsample),
    )


def _build(design: Design, *, with_posts: bool, electrodes: bool, name: str,
           film_delta_um: float = 0.0) -> CrossSection:
    """Optical cross-sections omit the electrodes and the handle wafer; the RF
    cross-section (``electrodes=True``) includes both.

    The cross-section is built in the frame named by ``process.simulate``, which
    is the **printed** geometry by default. What the light sees is what exists
    in silicon, and that differs from what is drawn on the mask wherever the
    process carries a bias. With no bias declared the two coincide and this has
    no effect.
    """
    p, e = design.platform, design.electrodes
    geom = process.geometry(design, design.process.simulate)
    return edbr_cross_section(
        film_material=p.film_material,
        film_thickness_um=p.film_thickness_um + film_delta_um,
        etch_depth_um=geom.etch_depth_um,
        wg_top_width_um=geom.wg_top_width_um,
        sidewall_deg=p.sidewall_deg,
        box_thickness_um=p.box_thickness_um,
        clad_thickness_um=p.clad_thickness_um,
        clad_material=p.clad_material,
        box_material=p.box_material,
        substrate_material=p.substrate_material,
        with_posts=with_posts,
        post_width_um=geom.post_width_um,
        post_gap_um=geom.post_gap_um,
        electrodes=electrodes,
        electrode_gap_um=geom.electrode_gap_um,
        electrode_width_um=geom.electrode_width_um,
        electrode_thickness_um=e.thickness_um,
        electrode_material=e.material,
        include_substrate=electrodes,
        window_pad_x_um=(e.rf_window_pad_um if electrodes else 3.0),
        window_pad_y_um=(e.rf_window_pad_um if electrodes else 0.0),
        name=name,
    )


def _n_guess(design: Design, lib: MaterialLibrary) -> float:
    p = design.platform
    lam = design.waveguide.wavelength_um
    n_film = max(lib[p.film_material].eps_optical_device(lam, p.cut, p.use_index_override)) ** 0.5
    return float(n_film) * 0.995


def _solve(design: Design, xs: CrossSection, grid, lib, lam_um: float, n_guess=None) -> ModeResult:
    p, m = design.platform, design.mesh
    exx, eyy = _eps_maps(xs, grid, lib, lam_um, p.cut, p.use_index_override, m.subsample)
    return solve_modes(
        grid.x, grid.y, exx, eyy, lam_um, m.polarisation, m.num_modes,
        n_guess if n_guess is not None else _n_guess(design, lib),
    )[0]


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    lam = design.waveguide.wavelength_um
    mesh = design.mesh
    dlam = 0.01

    # one mesh, built from the *superset* geometry so both solves share nodes
    xs_posts = _build(design, with_posts=True, electrodes=False, name="with_posts")
    xs_bare = _build(design, with_posts=False, electrodes=False, name="bare")
    xs_bare.window = xs_posts.window
    grid = build_grid(xs_posts, mesh.d_fine_um, mesh.d_coarse_um, mesh.fine_margin_um)

    m_bare = _solve(design, xs_bare, grid, lib, lam)
    m_bare_p = _solve(design, xs_bare, grid, lib, lam + dlam, m_bare.n_eff)
    m_bare_m = _solve(design, xs_bare, grid, lib, lam - dlam, m_bare.n_eff)
    n_g = m_bare.n_eff - lam * (m_bare_p.n_eff - m_bare_m.n_eff) / (2 * dlam)

    m_post = _solve(design, xs_posts, grid, lib, lam, m_bare.n_eff)
    dn_eff = m_post.n_eff - m_bare.n_eff

    # How hard the effective index leans on the film thickness. One extra solve
    # on a slightly thicker film, differenced against the bare one.
    #
    # This is what decides whether a long grating adds coherently. The Bragg
    # condition is set by n_eff, so a film that thins along the grating detunes
    # it, and the reflections stop adding in phase. On a 300 nm tantalate ridge
    # the sensitivity is near 1e-3 per nm of film, which puts the whole stop
    # band inside a twentieth of a nanometre of thickness. A corner sweep cannot
    # see this: it moves the film uniformly, which shifts the Bragg wavelength
    # and leaves the grating perfectly coherent.
    dn_dfilm = float("nan")
    if design.mesh.film_sensitivity:
        dt = 0.005  # um, small against the film and large against the mesh
        xs_thick = _build(design, with_posts=False, electrodes=False, name="bare_thick",
                          film_delta_um=dt)
        xs_thick.window = xs_posts.window
        m_thick = _solve(design, xs_thick, grid, lib, lam, m_bare.n_eff)
        dn_dfilm = (m_thick.n_eff - m_bare.n_eff) / dt

    film = design.platform.film_material
    mask_film = material_mask(xs_bare, grid, film, mesh.subsample)
    gamma_film = m_bare.confinement(mask_film)

    # Lateral-guidance floor: the unetched slab far from the ridge.  A ridge
    # mode exists only while n_eff > n_slab; counting against the *cladding*
    # index instead would count every discretised slab continuum state.
    exx_bare, _ = _eps_maps(
        xs_bare, grid, lib, lam, design.platform.cut, design.platform.use_index_override,
        mesh.subsample,
    )
    i_edge = int(np.argmin(np.abs(grid.x - 0.85 * grid.x[0])))
    n_slab = solve_slab(grid.y, exx_bare[i_edge, :], lam, 2)
    n_slab0 = float(n_slab[0]) if n_slab else 0.0
    guided = [n for n in m_bare.n_eff_all if n > n_slab0 + 1e-4]
    n_guided = int(len(guided))
    n_clad = float(np.sqrt(max(
        lib[design.platform.clad_material].eps_optical_device(lam)[0],
        lib[design.platform.box_material].eps_optical_device(lam)[0],
    )))

    payload = {
        "wavelength_um": lam,
        "polarisation": mesh.polarisation,
        # which of the three geometries was solved, so that no reader has to
        # infer whether this describes the mask or the wafer
        "geometry_frame": design.process.simulate,
        "geometry_um": process.geometry(design, design.process.simulate).as_dict(),
        "grid": {"nx": int(len(grid.x)), "ny": int(len(grid.y)),
                 "d_fine_um": mesh.d_fine_um, "d_coarse_um": mesh.d_coarse_um},
        "n_eff_bare": m_bare.n_eff,
        "n_eff_with_posts": m_post.n_eff,
        "dn_eff_posts": dn_eff,
        # per micron of film thickness; NaN where mesh.film_sensitivity is off
        "dn_eff_d_film_per_um": dn_dfilm,
        "n_g": float(n_g),
        "confinement_film": gamma_film,
        "n_guided_modes": n_guided,
        "n_eff_spectrum": [float(v) for v in m_bare.n_eff_all[:6]],
        "n_clad_max": n_clad,
        "n_slab_floor": n_slab0,
        "single_mode": bool(n_guided <= 1),
    }

    # the geometry itself, so that the cross-section can be drawn from the run
    # directory alone and the report stays reproducible without the design file
    dump_json(ctx.run_dir / "cross_section.json", {
        "window": list(xs_posts.window),
        "background": xs_posts.background,
        "wavelength_um": lam,
        "shapes": [
            {"material": s.material, "name": s.name,
             "points": [[float(px), float(py)] for px, py in s.points]}
            for s in xs_posts.shapes
        ],
    })

    ctx.put("mode", payload)
    ctx.write_stage(
        "mode",
        payload,
        {
            "x_um": grid.x,
            "y_um": grid.y,
            "field_bare": m_bare.field,
            "field_posts": m_post.field,
            "mask_film": mask_film,
        },
    )
    if not payload["single_mode"]:
        ctx.warn(
            f"cross-section supports {n_guided} guided modes; the E-DBR requires "
            "single-mode operation - reduce width or etch depth"
        )
    if dn_eff <= 0:
        ctx.warn("dn_eff from the Bragg posts is <= 0; check post geometry")

    # A measured index declared in the library and gated off is a value that was
    # adopted and never consumed. Measured thin-film indices replaced bulk
    # congruent ones for a tantalate stack, the provenance was rewritten, a
    # design report stated the replacement, and the release gate reported the
    # material data confirmed, while every solve continued to evaluate the bulk
    # fit because `use_index_override` defaults to false and no design set it.
    #
    # Enabling it on that cross-section moved the bare index by 1.18 %, the
    # electro-optic overlap by 2.46 %, the mirror tuning by 4.56 % and the
    # grating index perturbation by -19.3 %, so the coupling constant and every
    # quantity built on it move with it.
    #
    # The provenance gate cannot catch this. It tests whether a material is
    # tagged as needing confirmation, which is a statement about the tag and not
    # about the number the solver read.
    plat = design.platform
    if not plat.use_index_override:
        gated = sorted(
            name for name in {plat.film_material, plat.clad_material,
                              plat.box_material, plat.substrate_material}
            if "index_override_1550" in lib[name].spec
        )
        if gated:
            ctx.warn(
                "these materials declare a measured index that this run did not read: "
                + ", ".join(gated)
                + ". `platform.use_index_override` is false, so the Sellmeier fit was "
                "evaluated instead. Either set the flag and re-solve the period, since the "
                "Bragg wavelength follows the index, or record that the declared value is "
                "held for reference and is not in use",
                key="mode.index_override_declared_and_unread",
            )
    return payload
