"""Stage 9 - taper transmission by FDTD.

This is the stage that answers the question the eigenmode expansion cannot. A
guided-mode basis reports where a taper stops being adiabatic; it cannot report
how much power is lost, because the power leaves for the continuum and the
continuum is not in the basis. A time-domain solve carries the continuum, so the
difference between the transmitted *flux* and the transmitted *fundamental mode*
is the radiation.

The solver is meep, which is open source and executes locally. There is no
Windows build, so on this platform it is reached through WSL by
``picchain.fdtd.bridge``. The stage is disabled by default: a two-dimensional
solve of a 150 um taper is minutes rather than seconds, and a three-dimensional
solve is an offline job.

The two-dimensional model
-------------------------
For a taper that varies only in width, the loss channel is lateral, and the
effective-index method reduces the problem to the plane. The two indices are
solved here from the same cross-section the rest of the chain uses, rather than
being entered by hand:

* ``n_core``  the 1D slab index of the column through the ridge;
* ``n_clad``  the 1D slab index of the unetched film either side.

The vertical channel is absent from that model. Where it matters,
``fdtd.dimensions: 3`` builds the layer stack instead, at a cost of roughly two
orders of magnitude in run time.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import process
from ..artifacts import RunContext
from ..config import Design
from ..fdtd import bridge
from ..geometry import build_grid
from ..materials import MaterialLibrary
from ..solvers.fdmode import solve_slab
from .s01_mode import _eps_maps
from .s08_taper import _cross_section


def _effective_indices(design: Design, lib: MaterialLibrary) -> tuple[float, float]:
    """Slab index through the ridge, and through the unetched film beside it."""
    p, m = design.platform, design.mesh
    lam = design.waveguide.wavelength_um
    xs = _cross_section(design, design.waveguide.top_width_um, "fdtd_ref")
    grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, _ = _eps_maps(xs, grid, lib, lam, p.cut, p.use_index_override, m.subsample)

    i_mid = int(np.argmin(np.abs(grid.x)))
    i_edge = int(np.argmin(np.abs(grid.x - 0.85 * grid.x[0])))
    core = solve_slab(grid.y, exx[i_mid, :], lam, 2)
    clad = solve_slab(grid.y, exx[i_edge, :], lam, 2)
    if not core or not clad:
        raise RuntimeError("the effective-index reduction found no slab mode")
    return float(core[0]), float(clad[0])


def _kappa_in_two_dimensions(design: Design, n_core: float, n_clad: float,
                             period_um: float) -> dict[str, float]:
    """The chain's own kappa, recomputed for the two-dimensional structure.

    A three-dimensional kappa cannot be set against a two-dimensional solve
    without confounding the mode solver with the coupled-mode treatment. The
    same effective-index reduction the runner uses is therefore applied here,
    and the index perturbation of the posts is obtained on that reduced problem,
    so that the comparison isolates coupled-mode theory alone.
    """
    from .. import tmm
    from ..solvers.fdmode import solve_slab

    g, w = design.grating, design.waveguide
    lam = w.wavelength_um
    geom = process.geometry(design, design.process.simulate)
    half = geom.wg_top_width_um / 2
    inner = half + geom.post_gap_um
    outer = inner + geom.post_width_um

    x = np.linspace(-(outer + 3.0), outer + 3.0, 4001)
    bare = np.where(np.abs(x) <= half, n_core**2, n_clad**2)
    posts = np.where((np.abs(x) >= inner) & (np.abs(x) <= outer), n_core**2, bare)

    n_bare = solve_slab(x, bare, lam, 1)
    n_post = solve_slab(x, posts, lam, 1)
    if not n_bare or not n_post:
        raise RuntimeError("the two-dimensional reduction supports no guided mode")

    dn = float(n_post[0] - n_bare[0])
    duty = geom.post_length_um / period_um
    n_bar = tmm.mean_index(float(n_bare[0]), dn, duty)
    lam_B = tmm.bragg_wavelength_um(n_bar, period_um, g.order)
    # The period and the profile smoothing are passed, or the comparison is not
    # like for like. They were omitted until 2026-08-10, so this reduction
    # applied NO smoothing while the grating stage applied whatever
    # `grating.profile_sigma_um` declared. The band-gap value was therefore set
    # against an unsmoothed coupled-mode figure and reported as though it were
    # set against the design's own. A calibration of the smoothing was derived
    # from that comparison and had to be withdrawn.
    kappa = tmm.fourier_kappa(dn, duty, g.order, lam_B, period_um,
                              g.profile_sigma_um)
    return {
        "chain_2d_n_eff": float(n_bare[0]),
        "chain_2d_dn_eff": dn,
        "chain_2d_bragg_wavelength_nm": float(lam_B * 1000.0),
        "chain_2d_kappa_per_cm": float(kappa * 1e4),
    }


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.fdtd
    if not cfg.enabled:
        ctx.put("fdtd", {"enabled": False})
        return {"enabled": False}

    backend = bridge.default_backend(processes=cfg.processes)
    backend.distro, backend.env = cfg.wsl_distro, cfg.environment
    status = bridge.probe(backend)
    if not status.get("available"):
        raise RuntimeError(
            f"the meep environment cannot be reached: {status.get('reason')}. "
            "Install it as described in PICCHAIN_REFERENCE.md, or set fdtd.enabled to false"
        )

    p, t = design.platform, design.taper
    tip = t.tip_width_um if t.tip_width_um is not None else design.layout.taper_tip_width_um
    length = t.length_um if t.length_um is not None else design.layout.taper_length_um
    n_core, n_clad = _effective_indices(design, lib)

    if cfg.structure == "grating":
        return _run_grating(design, ctx, cfg, backend, status, n_core, n_clad)
    if cfg.structure == "bandstructure":
        return _run_bands(design, ctx, cfg, backend, status, n_core, n_clad)

    job = {
        "wavelength_um": design.waveguide.wavelength_um,
        "n_core": n_core,
        "n_clad": n_clad,
        "n_film": float(np.sqrt(lib[p.film_material].eps_optical_device(
            design.waveguide.wavelength_um, p.cut, p.use_index_override)[0])),
        "tip_width_um": float(tip),
        "full_width_um": float(design.waveguide.top_width_um),
        "length_um": float(length),
        "in_length_um": cfg.in_length_um,
        "out_length_um": cfg.out_length_um,
        "profile": t.profile,
        "taper_stations": cfg.taper_stations,
        "dimensions": cfg.dimensions,
        "resolution": cfg.resolution,
        "pml_um": cfg.pml_um,
        "width_um": cfg.cell_width_um,
        "height_um": cfg.cell_height_um,
        "slab_thickness_um": p.film_thickness_um - p.etch_depth_um,
        "ridge_height_um": p.etch_depth_um,
    }

    result = bridge.run_taper(job, ctx.run_dir, backend, timeout_s=cfg.timeout_s)

    payload: dict[str, Any] = {
        "enabled": True,
        "solver": "meep",
        "solver_version": status.get("version", "unknown"),
        "backend": backend.kind,
        "processes": cfg.processes,
        "n_core_effective_index": n_core,
        "n_clad_effective_index": n_clad,
        "tip_width_um": float(tip),
        "length_um": float(length),
        "profile": t.profile,
        **{k: v for k, v in result.items() if k != "ok"},
    }

    # the quantity the eigenmode expansion could not supply
    taper_metrics = ctx.get("taper") or {}
    if taper_metrics.get("enabled"):
        payload["eme_min_adiabaticity"] = taper_metrics.get("min_adiabaticity")
        payload["eme_conversion_loss_dB"] = taper_metrics.get("conversion_loss_dB")

    ctx.put("fdtd", payload)
    ctx.write_stage("fdtd", payload)

    norm = result.get("normalisation_check", 1.0)
    if abs(norm - 1.0) > 0.02:
        ctx.warn(
            f"the FDTD normalisation run transmits {norm:.3f} of its own input; the "
            "reference guide is not clean, so the transmission reported is unreliable. "
            "Raise fdtd.resolution or widen fdtd.cell_width_um"
        )
    if result["reflection_fundamental"] > 0.01:
        ctx.warn(
            f"the taper reflects {result['reflection_fundamental']:.2%} into the input "
            "mode, which is high for an adiabatic structure and suggests the input "
            "straight section or the PML is too short"
        )
    if cfg.dimensions == 2:
        ctx.warn(
            "the FDTD solve is two-dimensional by effective index, so only the lateral "
            "radiation channel is represented. The vertical channel requires "
            "fdtd.dimensions: 3"
        )
    return payload


def _run_grating(design, ctx, cfg, backend, status, n_core, n_clad):
    """Reflection of a finite grating, against the coupled-mode prediction."""
    g, w = design.grating, design.waveguide
    grat = ctx.get("grating") or {}
    period = float(grat.get("period_um") or g.period_um or 0.0)
    if period <= 0:
        raise RuntimeError("stage 'fdtd' with structure 'grating' requires stage 'grating'")

    job = {
        "wavelength_um": w.wavelength_um,
        "n_core": n_core,
        "n_clad": n_clad,
        "width_um": w.top_width_um,
        "period_um": period,
        "n_periods": cfg.grating_periods,
        "post_width_um": g.post_width_um,
        "post_length_um": g.post_length_um or g.post_width_um,
        "post_gap_um": g.post_gap_um,
        "in_length_um": cfg.in_length_um,
        "out_length_um": cfg.out_length_um,
        "resolution": cfg.resolution,
        "pml_um": cfg.pml_um,
        "cell_width_um": cfg.cell_width_um,
        "n_frequencies": cfg.n_frequencies,
        "fractional_bandwidth": cfg.fractional_bandwidth,
    }
    result = bridge.run_grating(job, ctx.run_dir, backend, timeout_s=cfg.timeout_s)
    chain = _kappa_in_two_dimensions(design, n_core, n_clad, period)

    k_fdtd = result["kappa_per_cm"]
    k_chain = chain["chain_2d_kappa_per_cm"]
    ratio = k_fdtd / k_chain if k_chain else float("nan")

    payload = {
        "enabled": True,
        "structure": "grating",
        "solver": "meep",
        "solver_version": status.get("version", "unknown"),
        "n_core_effective_index": n_core,
        "n_clad_effective_index": n_clad,
        **chain,
        **{k: v for k, v in result.items()
           if k not in ("ok", "spectrum_wavelength_nm", "spectrum_reflectivity")},
        "kappa_ratio_fdtd_over_chain": ratio,
        "kappa_3d_chain_per_cm": grat.get("kappa_per_cm"),
    }
    ctx.put("fdtd", payload)
    ctx.write_stage("fdtd", payload, {
        "spectrum_wavelength_nm": np.array(result["spectrum_wavelength_nm"]),
        "spectrum_reflectivity": np.array(result["spectrum_reflectivity"]),
    })

    if abs(result["sum_at_peak"] - 1.0) > 0.05:
        ctx.warn(
            f"reflection and transmission sum to {result['sum_at_peak']:.3f} at the peak; "
            "the balance is the power radiated or absorbed, and a large value means the "
            "solve is not converged rather than that the grating is lossy"
        )
    if ratio == ratio and not (0.9 <= ratio <= 1.1):
        ctx.warn(
            f"the time-domain kappa is {ratio:.2f} times the coupled-mode value on the "
            "same two-dimensional structure. Coupled-mode theory assumes a weak "
            "perturbation, so a departure of this size bounds where that assumption "
            "ceases to hold"
        )
    return payload


def _run_bands(design, ctx, cfg, backend, status, n_core, n_clad):
    """Kappa from the photonic band gap of a single period."""
    g, w = design.grating, design.waveguide
    grat = ctx.get("grating") or {}
    mode = ctx.get("mode") or {}
    period = float(grat.get("period_um") or g.period_um or 0.0)
    if period <= 0:
        raise RuntimeError("stage 'fdtd' with structure 'bandstructure' requires 'grating'")

    chain = _kappa_in_two_dimensions(design, n_core, n_clad, period)
    job = {
        "period_um": period,
        "n_core": n_core,
        "n_clad": n_clad,
        "width_um": w.top_width_um,
        "post_width_um": g.post_width_um,
        "post_length_um": g.post_length_um or g.post_width_um,
        "post_gap_um": g.post_gap_um,
        "cell_width_um": cfg.cell_width_um,
        "resolution": cfg.resolution,
        "num_bands": cfg.num_bands,
        "confinement_threshold": cfg.confinement_threshold,
        "order": g.order,
        "n_eff_guess": chain["chain_2d_n_eff"],
        "n_g": float(mode.get("n_g") or chain["chain_2d_n_eff"]),
    }
    result = bridge.run_bandstructure(job, ctx.run_dir, backend, timeout_s=cfg.timeout_s)
    if not result.get("ok"):
        raise RuntimeError(
            "the band-structure solve did not identify a guided pair: "
            f"{result.get('reason')}. Raise fdtd.num_bands or lower "
            "fdtd.confinement_threshold"
        )

    k_mpb = result["kappa_per_cm"]
    k_chain = chain["chain_2d_kappa_per_cm"]
    ratio = k_mpb / k_chain if k_chain else float("nan")

    # --- the convergence guard -----------------------------------------
    # The band gap is the difference of two nearly degenerate bands. On the
    # TFLN validation baseline it is 5e-5 of the band frequency itself, and the
    # mesh moved kappa by 39 % between resolution 20 and resolution 40, which is
    # more than the 1.63x disagreement the comparison was being read to
    # establish. A verdict was reported from that solve, and it was worth
    # nothing. The structure is now solved a second time on a coarser mesh and
    # the shift bounds the discretisation error.
    guard_res = cfg.convergence_resolution
    if guard_res is None:
        guard_res = max(8, cfg.resolution // 2)
    conv: dict = {"guarded": False, "coarse_resolution": guard_res}
    if guard_res and guard_res != cfg.resolution:
        coarse = bridge.run_bandstructure(
            {**job, "resolution": guard_res}, ctx.run_dir, backend,
            timeout_s=cfg.timeout_s, name="bands_coarse")
        if coarse.get("ok"):
            k_coarse = coarse["kappa_per_cm"]
            shift = abs(k_mpb - k_coarse)
            diff = abs(k_chain - k_mpb)
            conv = {
                "guarded": True,
                "coarse_resolution": guard_res,
                "kappa_coarse_per_cm": k_coarse,
                "ratio_coarse": k_coarse / k_chain if k_chain else float("nan"),
                "mesh_shift_per_cm": shift,
                "difference_per_cm": diff,
                # the same criterion the fem cross-check applies: the effect must
                # stand clear of the mesh error by a factor of three
                "resolved": bool(diff > 3.0 * shift),
            }
        else:
            conv["reason"] = coarse.get("reason", "the coarse solve found no guided pair")

    payload = {
        "enabled": True,
        "structure": "bandstructure",
        "solver": "mpb",
        "solver_version": status.get("version", "unknown"),
        "n_core_effective_index": n_core,
        "n_clad_effective_index": n_clad,
        **chain,
        **{k: v for k, v in result.items() if k not in ("ok", "confinement", "freqs")},
        "kappa_ratio_mpb_over_chain": ratio,
        "kappa_3d_chain_per_cm": grat.get("kappa_per_cm"),
        "convergence": conv,
    }
    ctx.put("fdtd", payload)
    ctx.write_stage("fdtd", payload, {
        "band_frequencies": np.array(result["freqs"]),
        "band_confinement": np.array(result["confinement"]),
    })

    lam_gap = result["bragg_wavelength_nm"]
    lam_chain = chain["chain_2d_bragg_wavelength_nm"]
    if abs(lam_gap - lam_chain) > 0.02 * lam_chain:
        ctx.warn(
            f"the band gap sits at {lam_gap:.1f} nm against the coupled-mode "
            f"{lam_chain:.1f} nm. A disagreement of this size means the pair of bands "
            "identified may not be the intended order"
        )
    if not conv.get("guarded"):
        ctx.warn(
            "the band-structure comparison is unguarded, so no statement about the "
            "coupled-mode value can be drawn from it. Set fdtd.convergence_resolution "
            "to solve the same structure on a second mesh"
        )
    elif not conv["resolved"]:
        ctx.warn(
            f"the band-structure comparison is UNRESOLVED and establishes nothing. "
            f"Between resolution {guard_res} and {cfg.resolution} the mesh moves kappa by "
            f"{conv['mesh_shift_per_cm']:.3f} /cm, against a disagreement with the "
            f"coupled-mode value of {conv['difference_per_cm']:.3f} /cm. The band gap is "
            f"the difference of two nearly degenerate bands, so it converges slowly. "
            f"Raise fdtd.resolution until the shift falls below a third of the difference"
        )
    elif ratio == ratio and not (0.9 <= ratio <= 1.1):
        ctx.warn(
            f"the band-gap kappa is {ratio:.2f} times the coupled-mode value on the "
            "same structure, and the comparison is converged. There is no radiation "
            "channel in it, so the difference is attributable to the coupled-mode "
            "construction itself"
        )
    return payload
