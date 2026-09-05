#!/usr/bin/env python3
"""Meep runner for a ring-to-bus point coupler. Executed *inside* the meep
environment.

The file is standalone, in the manner of ``meep_taper``: it imports meep and
numpy and nothing from picchain, because it runs under a different interpreter
from the rest of the chain. Its contract is two paths on the command line, one
JSON job in and one JSON result out.

What is solved
--------------
Propagation is along x. The bus is a straight strip of width ``w`` centred on
y = 0. The ring is a strip of width ``w_r``, which is the bus width unless the
job states otherwise, displaced so that the gap between the two ridge edges is
``gap`` and curved away as a circle of radius R:

    y_ring(x) = -(w/2 + gap + w_r/2) - (R - sqrt(R^2 - x^2))

Where the two widths differ the guides are asynchronous, their propagation
constants differing, and the coupling is then governed by that mismatch as much
as by the gap. Power crossing into the ring is therefore resolved by band as
well as in total, since a wider ring carries more than one mode to receive it.

In two dimensions the background index is the effective index of the film
*beside* the ridge, which on a partially etched platform is the unetched slab
and not the cladding. That distinction dominates the answer: the evanescent
field decays at a rate set by the difference between the ridge index and the
slab index, and taking the cladding instead overstates the decay by a large
factor. The reduction is therefore only valid where the slab is continuous
across the coupling region, which a partially etched process draws by default.

Two runs are performed for every job:

1. the bus alone, giving the incident amplitude in its fundamental mode;
2. bus and ring together, giving the amplitude remaining in the bus and the
   amplitude that has crossed into the ring.

The power coupling is the second normalised by the first. Their sum is the
model's own check: a point coupler at a separation of this order has no
radiation channel, so a sum departing from unity is a defect in the solve
rather than a physical loss.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np


def ring_offset(x, R: float):
    """Lateral displacement of the ring centre-line from its closest approach."""
    return R - np.sqrt(np.maximum(R * R - np.asarray(x, float) ** 2, 0.0))


def ring_centre(job) -> float:
    """Centre line of the ring at its closest approach.

    The gap is measured between the two ridge edges, so the centres are half of
    each width plus the gap apart. The two widths differ on a multimode ring,
    where the kit pairs a single-mode bus with a wider ring.
    """
    return -(job["width_um"] / 2.0 + job["gap_um"] + ring_width(job) / 2.0)


def ring_width(job) -> float:
    """Width of the ring guide, which is the bus width unless stated."""
    return float(job.get("ring_width_um") or job["width_um"])


def build_geometry(job, bus_only: bool):
    w, R = job["width_um"], job["ring_radius_um"]
    wr = ring_width(job)
    X, dpml = job["half_length_um"], job["pml_um"]
    core = mp.Medium(index=job["n_core"])

    bus = mp.Block(
        size=mp.Vector3(2 * X + 2 * dpml + 2.0, w, mp.inf),
        center=mp.Vector3(0, 0, 0),
        material=core,
    )
    if bus_only:
        return [bus]

    xs = np.linspace(-X - dpml - 1.0, X + dpml + 1.0, job["ring_stations"])
    yc = ring_centre(job) - ring_offset(xs, R)
    top = [mp.Vector3(float(x), float(y + wr / 2)) for x, y in zip(xs, yc)]
    bot = [mp.Vector3(float(x), float(y - wr / 2)) for x, y in zip(xs, yc)][::-1]
    ring = mp.Prism(top + bot, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=core)
    return [bus, ring]


def simulate(job, bus_only: bool, resolution: int):
    w, R = job["width_um"], job["ring_radius_um"]
    X, dpml = job["half_length_um"], job["pml_um"]
    lam0 = job["wavelength_um"]
    fcen = 1.0 / lam0
    df = 1.0 / job["lambda_min_um"] - 1.0 / job["lambda_max_um"]
    nfreq = job["nfreq"]

    y_ring_out = ring_centre(job) - float(ring_offset(X - 1.0, R))
    y_lo = y_ring_out - job["margin_um"]
    y_hi = w / 2 + job["margin_um"]

    sx = 2 * X + 2 * dpml
    sy = (y_hi - y_lo) + 2 * dpml
    y_mid = 0.5 * (y_hi + y_lo)

    x_src = -X + dpml + 0.5
    x_ref = x_src + 0.5
    x_out = X - dpml - 0.5

    parity = mp.ODD_Z
    port = mp.Vector3(0, job["port_width_um"], 0)

    sim = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        geometry_center=mp.Vector3(0, y_mid, 0),
        resolution=resolution,
        boundary_layers=[mp.PML(dpml)],
        geometry=build_geometry(job, bus_only),
        default_material=mp.Medium(index=job["n_background"]),
        sources=[
            mp.EigenModeSource(
                src=mp.GaussianSource(fcen, fwidth=1.2 * df),
                center=mp.Vector3(x_src, 0, 0),
                size=port,
                eig_band=1,
                eig_parity=parity,
                direction=mp.X,
            )
        ],
    )

    ref = sim.add_mode_monitor(
        fcen, df, nfreq, mp.FluxRegion(center=mp.Vector3(x_ref, 0, 0), size=port))
    thru = sim.add_mode_monitor(
        fcen, df, nfreq, mp.FluxRegion(center=mp.Vector3(x_out, 0, 0), size=port))
    cross = sim.add_mode_monitor(
        fcen, df, nfreq, mp.FluxRegion(center=mp.Vector3(x_out, y_ring_out, 0), size=port))

    transit = sx * job["n_core"]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        tol=1e-6, minimum_run_time=2.0 * transit))

    def power(mon, bands=(1,)):
        c = sim.get_eigenmode_coefficients(
            mon, list(bands), eig_parity=parity,
            kpoint_func=lambda f, n: mp.Vector3(1, 0, 0))
        return np.abs(c.alpha[:, :, 0]) ** 2          # (band, frequency)

    n_bands = int(job.get("cross_bands", 1))
    cross_by_band = power(cross, tuple(range(1, n_bands + 1)))
    return {
        "freqs": [float(f) for f in mp.get_flux_freqs(ref)],
        "thru": power(thru)[0].tolist(),
        "cross": cross_by_band.sum(axis=0).tolist(),
        "cross_by_band": [row.tolist() for row in cross_by_band],
    }


def measure(job, resolution: int):
    """Power coupling across the band, at one mesh."""
    norm = simulate(job, True, resolution)
    full = simulate(job, False, resolution)
    p_in = np.asarray(norm["thru"])
    if float(np.max(p_in)) <= 0.0:
        raise RuntimeError(
            "the normalisation run carries no power in the fundamental mode of the "
            "bus. The usual cause is a guide below cut-off at this width and index "
            "contrast, or a run stopped before the pulse crossed the cell"
        )
    kappa2 = np.asarray(full["cross"]) / p_in
    t2 = np.asarray(full["thru"]) / p_in
    by_band = [np.asarray(b) / p_in for b in full.get("cross_by_band", [])]
    lam = [1.0 / f for f in full["freqs"]]
    return lam, kappa2, t2, by_band


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    lam, kappa2, t2, by_band = measure(job, job["resolution"])
    i0 = int(np.argmin([abs(x - job["wavelength_um"]) for x in lam]))

    result = {
        "ok": True,
        "resolution": job["resolution"],
        "wavelength_um": lam,
        "kappa2": kappa2.tolist(),
        "t2": t2.tolist(),
        "unitarity": (kappa2 + t2).tolist(),
        "kappa2_by_band": [b.tolist() for b in by_band],
        "kappa2_by_band_at_design": [float(b[i0]) for b in by_band],
        "kappa2_at_design": float(kappa2[i0]),
        "t2_at_design": float(t2[i0]),
        "unitarity_at_design": float(kappa2[i0] + t2[i0]),
    }

    guard = int(job.get("convergence_resolution") or 0)
    if guard and guard != job["resolution"]:
        _, k_coarse, _, _ = measure(job, guard)
        result["guard"] = {
            "resolution": guard,
            "kappa2_at_design": float(k_coarse[i0]),
            "shift_fraction": float(
                (kappa2[i0] - k_coarse[i0]) / kappa2[i0]) if kappa2[i0] else float("nan"),
        }

    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
