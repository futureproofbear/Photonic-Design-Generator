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


#: Which runners build a three-dimensional cell. `meep_taper.py` reads the layer
#: stack and extrudes it; the coupler, the grating and the multimode splitter
#: build their shapes with `mp.inf` in the third axis and are two-dimensional by
#: construction, the background being an effective index.
STRUCTURES_WITH_A_3D_RUNNER = frozenset({"taper"})


def _refuse_a_dimension_the_runner_does_not_build(cfg) -> None:
    """Raise where a structure is asked for three dimensions it cannot build.

    Until 2026-09-05 `fdtd.dimensions` was recorded in the payload of every
    structure and passed to the runner of one. A multimode-splitter run
    declaring three dimensions therefore emitted a payload stamped
    `dimensions: 3` carrying a two-dimensional result, and because the job
    dictionary never carried the field either, the cache matched the
    two-dimensional job and reused it. The transmission agreed to six decimals
    with the run it was supposed to differ from, which is how it was found.

    A result that misreports what produced it is worse than no result.
    """
    if int(cfg.dimensions) == 2:
        return
    if str(cfg.structure) in STRUCTURES_WITH_A_3D_RUNNER:
        return
    raise ValueError(
        f"fdtd.dimensions is {cfg.dimensions} and fdtd.structure is "
        f"{cfg.structure!r}, whose runner builds a two-dimensional cell only. "
        f"Three dimensions are built for: "
        f"{', '.join(sorted(STRUCTURES_WITH_A_3D_RUNNER))}. Set "
        f"fdtd.dimensions: 2, or use a structure that carries a "
        f"three-dimensional runner"
    )


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

    _refuse_a_dimension_the_runner_does_not_build(cfg)

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
    if cfg.structure == "coupler":
        return _run_coupler(design, ctx, cfg, backend, status, n_core, n_clad)
    if cfg.structure == "mmi":
        return _run_mmi(design, ctx, cfg, backend, status, n_core, n_clad)

    job = {
        "wavelength_um": design.waveguide.wavelength_um,
        "n_core": n_core,
        "n_clad": n_clad,
        "n_film": float(np.sqrt(lib[p.film_material].eps_optical_device(
            design.waveguide.wavelength_um, p.cut, p.use_index_override)[0])),
        # the surround of the three-dimensional cell: the cladding above and the
        # buried oxide below, whichever is the higher index. `n_clad` above is
        # the effective index of the unetched film and belongs to the plane
        # reduction alone.
        "n_ambient": float(np.sqrt(max(
            lib[p.clad_material].eps_optical_device(design.waveguide.wavelength_um)[0],
            lib[p.box_material].eps_optical_device(design.waveguide.wavelength_um)[0],
        ))),
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
        "structure": cfg.structure,
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
    _warn_if_power_exceeds_unity(ctx, {
        "transmission_fundamental": result.get("transmission_fundamental"),
        "transmission_total_flux": result.get("transmission_total_flux"),
        # graded by its own two monitors, so no other simulation enters it
        "self_normalised_taper": result.get("self_normalised_taper"),
        "self_normalised_narrow_guide": result.get("self_normalised_narrow_guide"),
        "self_normalised_wide_guide": result.get("self_normalised_wide_guide"),
    })
    _report_what_the_reference_asymmetry_can_explain(ctx, result)
    _warn_if_the_reference_is_not_finer_than_the_measurand(
        ctx, norm, result.get("transmission_fundamental", 1.0)
    )
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


#: Tolerance on a bound belonging to physics. A flux ratio formed from two DFT
#: monitors carries numerical noise of order one part in a million, and the
#: plane reduction's self-normalised budget reads 1.0000019 on a sound solve.
#: One part in ten thousand is far above that noise and far below the 0.8 per
#: cent excess this guard exists to catch.
PASSIVITY_TOLERANCE = 1.0e-4


def _warn_if_power_exceeds_unity(ctx, quantities: dict[str, float]) -> None:
    """Report any transmitted or reflected fraction above one.

    A passive structure returns at most the power it is given. The first
    three-dimensional taper solve returned a fundamental-mode transmission of
    1.00378 and a total flux of 1.00522, and nothing in the stage remarked on
    it. The excess is the size of the quantity such a run exists to measure, so
    a result above unity is reported rather than rounded down.
    """
    for name, value in quantities.items():
        if value is None:
            continue
        if float(value) > 1.0 + PASSIVITY_TOLERANCE:
            ctx.warn(
                f"the FDTD solve returns {name} of {float(value):.5f}, which exceeds "
                "unity for a passive structure by "
                f"{(float(value) - 1.0) * 100.0:.3f} per cent. No figure of this run "
                "is to be quoted. Candidate causes, to be separated by measurement "
                "rather than assumed: a normalisation guide less confined than the "
                "structure, which attenuates over its own length and makes the "
                "denominator too small; a monitor too small to contain the mode it "
                "grades; an ambient index that does not belong to the cell as built. "
                "Compare the excess against normalisation_check, and where the excess "
                "is the larger the reference is not the cause"
            )


def _report_what_the_reference_asymmetry_can_explain(ctx, result: dict) -> None:
    """State how much of an above-unity transmission the reference can account for.

    The normalisation guide is held at the launch width while a widening taper
    is better confined downstream, so the reference attenuates more than the
    structure and the quotient rises. That mechanism was proposed as the cause
    of a transmission of 1.008 and was never bounded. The third simulation
    measures the output width's own attenuation over the same span, and the
    difference between the two straight guides is the whole of what the
    asymmetry can contribute.
    """
    excess = float(result.get("transmission_fundamental", 1.0)) - 1.0
    if excess <= 1e-9:
        return
    asymmetry = result.get("reference_asymmetry")
    if asymmetry is None:
        return
    asymmetry = float(asymmetry)
    share = asymmetry / excess if excess > 0 else 0.0
    if share >= 0.5:
        ctx.warn(
            f"the transmission exceeds unity by {excess:.3%} and the two straight "
            f"guides differ in their own attenuation by {asymmetry:.3%}, which "
            "accounts for most of it. The reference is the cause: normalise "
            "against a guide of the output width, or move the output monitor to "
            "sit closer behind the taper"
        )
    else:
        ctx.warn(
            f"the transmission exceeds unity by {excess:.3%} while the two straight "
            f"guides differ in their own attenuation by only {asymmetry:.3%}. The "
            "reference accounts for at most that much, so the remaining "
            f"{excess - asymmetry:.3%} has another cause and the figure is not to be "
            "quoted. Read self_normalised_taper, which is graded by the taper run's "
            "own monitors and involves no other simulation"
        )


def _warn_if_the_reference_is_not_finer_than_the_measurand(
    ctx, normalisation_check: float, transmission: float
) -> None:
    """Report where the reference guide's own loss rivals the loss being reported.

    The tolerance on the normalisation run was two per cent, and a taper whose
    loss is a few tenths of a per cent was graded against it. A guard whose
    tolerance exceeds the measurand admits every result it exists to reject, so
    the two are compared to each other.
    """
    reference_loss = abs(1.0 - float(normalisation_check))
    measured_loss = abs(1.0 - float(transmission))
    if reference_loss <= 1e-12:
        return
    if measured_loss <= 3.0 * reference_loss:
        ctx.warn(
            f"the normalisation guide loses {reference_loss:.3%} over its own length "
            f"while the structure is reported to lose {measured_loss:.3%}. The "
            "reference is not finer than the quantity it grades, so the transmission "
            "is unresolved by this cell. Widen fdtd.cell_width_um and "
            "fdtd.cell_height_um, or raise fdtd.resolution, until the normalisation "
            "run transmits its own input to well inside the loss expected"
        )


def _run_mmi(design, ctx, cfg, backend, status, n_core, n_clad):
    """Transmission, balance and reflection of the multimode splitter.

    The splitter is drawn by the layout stage and was evaluated by nothing. Its
    excess loss enters every arm of an interferometer twice, and its imbalance
    sets the extinction the device can reach whatever the phase control does.

    The geometry is read from `mzm`, so the structure solved is the structure
    the mask carries. A passive splitter cannot return more than it is given,
    so the sum over the ports and the reflection is the solve's own check.
    """
    w, m = design.waveguide, design.mzm
    lam = w.wavelength_um
    half_band = cfg.coupler_bandwidth_frac
    job = {
        "wavelength_um": lam,
        "lambda_min_um": lam * (1.0 - half_band),
        "lambda_max_um": lam * (1.0 + half_band),
        "nfreq": cfg.coupler_frequencies,
        "n_core": n_core,
        "n_background": n_clad,
        "width_um": float(w.top_width_um),
        "mmi_width_um": float(m.mmi_width_um),
        "mmi_length_um": float(m.mmi_length_um),
        "port_width_um": float(m.port_width_um),
        "port_separation_um": float(m.port_separation_um),
        "taper_length_um": cfg.mmi_taper_length_um,
        "lead_um": cfg.mmi_lead_um,
        "ports_in": int(cfg.mmi_ports_in),
        "taper_stations": cfg.taper_stations,
        # The monitor may not reach the neighbouring port. Set to the port
        # separation it spans as far as the next guide's centre line, and the
        # eigenmode decomposition then solves the modes of a two-guide section
        # and calls the supermode band 1, which under-reports each port.
        "port_width_monitor_um": float(min(0.8 * m.port_separation_um,
                                           4.0 * w.top_width_um)),
        "margin_um": cfg.coupler_margin_um,
        "pml_um": cfg.pml_um,
        "resolution": cfg.resolution,
        "convergence_resolution": (
            cfg.convergence_resolution
            if cfg.convergence_resolution is not None
            else max(8, cfg.resolution // 2)
        ),
        "dimensions": cfg.dimensions,
    }
    result = bridge.run_mmi(job, ctx.run_dir, backend, timeout_s=cfg.timeout_s)
    guard = result.get("guard") or {}

    payload: dict[str, Any] = {
        "enabled": True,
        "structure": "mmi",
        "solver": "meep",
        "solver_version": status.get("version", "unknown"),
        "backend": backend.kind,
        "dimensions": cfg.dimensions,
        "resolution": cfg.resolution,
        "ports_in": int(cfg.mmi_ports_in),
        "n_core_effective_index": n_core,
        "n_slab_effective_index": n_clad,
        "mmi_width_um": float(m.mmi_width_um),
        "mmi_length_um": float(m.mmi_length_um),
        "transmission": result["transmission_at_design"],
        "excess_loss_dB": result["excess_loss_dB_at_design"],
        "imbalance_dB": result["imbalance_dB_at_design"],
        "reflection": result["reflection_at_design"],
        "accounted": result["accounted_at_design"],
        "transmission_spectrum": result["port_transmission"],
        "wavelength_um": result["wavelength_um"],
        "convergence": {
            "guarded": bool(guard),
            "coarse_resolution": guard.get("resolution"),
            "transmission_coarse": guard.get("transmission_at_design"),
            "shift_fraction": guard.get("shift_fraction"),
            "resolved": (abs(guard["shift_fraction"]) < 0.05) if guard else False,
        },
    }
    _warn_if_power_exceeds_unity(ctx, {
        "transmission": result["transmission_at_design"],
    })
    ctx.put("fdtd", payload)
    ctx.write_stage("fdtd", payload)

    if payload["accounted"] > 1.0 + 1e-3:
        ctx.warn(
            f"the splitter accounts for {payload['accounted']:.4f} of its input, which "
            "a passive structure cannot exceed. The solve is at fault: widen the "
            "monitors or raise fdtd.resolution",
            key="fdtd.mmi_gain")
    if payload["accounted"] < 0.97:
        ctx.warn(
            f"the ports and the reflection account for {payload['accounted']:.4f} of "
            "the input, so {:.1%} left laterally".format(1 - payload["accounted"]) +
            ". In two dimensions that is radiation from the multimode section rather "
            "than a numerical shortfall, and it is the excess loss of the splitter",
            key="fdtd.mmi_radiates")
    if abs(payload["imbalance_dB"]) > 0.2:
        ctx.warn(
            f"the two ports differ by {payload['imbalance_dB']:.2f} dB, which bounds "
            "the extinction any interferometer built on this splitter can reach",
            key="fdtd.mmi_imbalanced")
    if guard and abs(guard.get("shift_fraction") or 0.0) >= 0.05:
        ctx.warn(
            f"the transmission moves by {abs(guard['shift_fraction']):.1%} between "
            f"resolution {guard['resolution']} and {cfg.resolution}, so the mesh error "
            "is comparable with the excess loss being measured",
            key="fdtd.mmi_unconverged")
    if cfg.dimensions == 2:
        ctx.warn(
            "the splitter solve is two-dimensional by effective index, so the vertical "
            "radiation channel is absent and the excess loss reported is the lateral "
            "part alone",
            key="fdtd.mmi_two_dimensional")
    return payload


def _run_coupler(design, ctx, cfg, backend, status, n_core, n_clad):
    """Power coupling of a ring-to-bus point coupler, measured in the plane.

    The quantity a resonator turns on is the fraction of power the bus hands to
    the ring in one pass. A mode solver cannot supply it and the transfer matrix
    that closes the ring assumes it, so it is measured here.

    The clad index of the effective-index reduction is the film *beside* the
    ridge, which on a partially etched platform is the unetched slab. That is
    the index the evanescent field decays against, and it is a great deal
    closer to the mode index than the cladding is: taking the cladding instead
    overstates the decay constant and understates the coupling by an order of
    magnitude at a gap of a micrometre.

    The solve carries its own check. A point coupler at this separation has no
    radiation channel, so the through and cross powers must account for the
    input, and a departure from unity is a defect in the solve.
    """
    w = design.waveguide
    lam = w.wavelength_um
    half_band = cfg.coupler_bandwidth_frac
    job = {
        "wavelength_um": lam,
        "lambda_min_um": lam * (1.0 - half_band),
        "lambda_max_um": lam * (1.0 + half_band),
        "nfreq": cfg.coupler_frequencies,
        "n_core": n_core,
        "n_background": n_clad,
        "width_um": float(w.top_width_um),
        "gap_um": cfg.coupler_gap_um,
        "ring_width_um": (float(cfg.coupler_ring_width_um)
                          if cfg.coupler_ring_width_um else None),
        "ring_radius_um": cfg.coupler_ring_radius_um,
        "cross_bands": int(cfg.coupler_cross_bands),
        "half_length_um": cfg.coupler_half_length_um,
        "ring_stations": cfg.coupler_stations,
        "port_width_um": cfg.coupler_port_width_um,
        "margin_um": cfg.coupler_margin_um,
        "pml_um": cfg.pml_um,
        "resolution": cfg.resolution,
        "convergence_resolution": (
            cfg.convergence_resolution
            if cfg.convergence_resolution is not None
            else max(8, cfg.resolution // 2)
        ),
        "dimensions": cfg.dimensions,
    }
    result = bridge.run_coupler(job, ctx.run_dir, backend, timeout_s=cfg.timeout_s)

    kappa2 = float(result["kappa2_at_design"])
    unitarity = float(result["unitarity_at_design"])
    guard = result.get("guard") or {}

    # the loss at which a ring of this radius would be critically coupled, being
    # the single number that turns this measurement into a design statement
    circumference_cm = 2.0 * np.pi * cfg.coupler_ring_radius_um * 1e-4
    critical_loss = (
        float(-10.0 * np.log10(max(1.0 - kappa2, 1e-12)) / circumference_cm)
        if circumference_cm > 0 else float("nan")
    )

    payload: dict[str, Any] = {
        "enabled": True,
        "structure": "coupler",
        "solver": "meep",
        "solver_version": status.get("version", "unknown"),
        "backend": backend.kind,
        "processes": cfg.processes,
        "dimensions": cfg.dimensions,
        "resolution": cfg.resolution,
        "n_core_effective_index": n_core,
        "n_slab_effective_index": n_clad,
        "gap_um": cfg.coupler_gap_um,
        "ring_width_um": float(cfg.coupler_ring_width_um or w.top_width_um),
        "ring_radius_um": cfg.coupler_ring_radius_um,
        "kappa2": kappa2,
        "t2": float(result["t2_at_design"]),
        "unitarity": unitarity,
        "kappa2_spectrum": result["kappa2"],
        "kappa2_by_band": result.get("kappa2_by_band_at_design"),
        "wavelength_um": result["wavelength_um"],
        "critical_coupling_loss_dB_cm": critical_loss,
        "convergence": {
            "guarded": bool(guard),
            "coarse_resolution": guard.get("resolution"),
            "kappa2_coarse": guard.get("kappa2_at_design"),
            "shift_fraction": guard.get("shift_fraction"),
            "resolved": (abs(guard["shift_fraction"]) < 0.10) if guard else False,
        },
    }

    ctx.put("fdtd", payload)
    ctx.write_stage("fdtd", payload)

    if abs(unitarity - 1.0) > 0.01:
        ctx.warn(
            f"the coupler solve accounts for {unitarity:.4f} of its input across the "
            "two ports. A point coupler carries no radiation channel, so the shortfall "
            "is numerical: widen fdtd.coupler_port_width_um or fdtd.coupler_margin_um, "
            "or raise fdtd.resolution",
            key="fdtd.coupler_unitarity",
        )
    if guard and abs(guard.get("shift_fraction") or 0.0) >= 0.10:
        ctx.warn(
            f"the coupling moves by {abs(guard['shift_fraction']):.1%} between "
            f"resolution {guard['resolution']} and {cfg.resolution}, so the mesh error "
            "is comparable with the quantity. Raise fdtd.resolution until the shift "
            "falls well below the difference the measurement has to distinguish",
            key="fdtd.coupler_unconverged",
        )
    if not guard:
        ctx.warn(
            "the coupler solve carries no convergence guard, so its mesh error is "
            "unmeasured. Set fdtd.convergence_resolution to a coarser mesh",
            key="fdtd.coupler_unguarded",
        )
    if cfg.dimensions == 2:
        ctx.warn(
            "the coupler solve is two-dimensional by effective index. The lateral "
            "channel is represented and power radiated vertically out of the slab is "
            "not, and the reduction assumes the slab is continuous across the gap",
            key="fdtd.coupler_two_dimensional",
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
        "dimensions": cfg.dimensions,
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
        "dimensions": cfg.dimensions,
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
