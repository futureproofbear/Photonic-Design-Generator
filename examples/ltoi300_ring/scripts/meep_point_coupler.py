#!/usr/bin/env python3
"""Meep runner for a ring-to-bus point coupler. Executed *inside* the meep
environment.

The file is standalone, in the manner of ``picchain.fdtd.meep_taper``: it
imports meep and numpy and nothing from picchain, because it runs under a
different interpreter. Its contract is two paths on the command line, one JSON
job in and one JSON result out.

Geometry
--------
Propagation is along x. The bus is a straight strip of width ``w`` centred on
y = 0. The ring is the same strip displaced by ``w + gap`` and curved away as
a circle of radius R, which over the window is written exactly as

    y_ring(x) = -(w + gap) - (R - sqrt(R^2 - x^2))

Both guides sit on the continuous 120 nm slab that the PDK cross-section draws
6 um either side of every ridge, so the background index of the two-dimensional
model is the slab index and not the oxide index. That distinction dominates the
answer: the evanescent field decays at a rate set by the difference between the
ridge index and the slab index, which is far slower than a decay into oxide.

Two runs are performed for every job:

1. the bus alone, giving the incident amplitude in its fundamental mode;
2. bus and ring together, giving the amplitude remaining in the bus and the
   amplitude that has crossed into the ring.

The power coupling is the second normalised by the first. Their sum tests the
model: a point coupler with no radiation channel returns unity.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np


def ring_offset(x, R: float):
    """Lateral displacement of the ring centre-line from its closest approach."""
    return R - np.sqrt(np.maximum(R * R - np.asarray(x, float) ** 2, 0.0))


def build_geometry(job, bus_only: bool):
    w, gap, R = job["width_um"], job["gap_um"], job["ring_radius_um"]
    X = job["half_length_um"]
    core = mp.Medium(index=job["n_core"])

    bus = mp.Block(
        size=mp.Vector3(2 * X + 2 * job["pml_um"] + 2.0, w, mp.inf),
        center=mp.Vector3(0, 0, 0),
        material=core,
    )
    if bus_only:
        return [bus]

    xs = np.linspace(-X - job["pml_um"] - 1.0, X + job["pml_um"] + 1.0,
                     job["ring_stations"])
    yc = -(w + gap) - ring_offset(xs, R)
    top = [mp.Vector3(float(x), float(y + w / 2)) for x, y in zip(xs, yc)]
    bot = [mp.Vector3(float(x), float(y - w / 2)) for x, y in zip(xs, yc)][::-1]
    ring = mp.Prism(top + bot, height=mp.inf, axis=mp.Vector3(0, 0, 1),
                    material=core)
    return [bus, ring]


def simulate(job, bus_only: bool):
    w, gap, R = job["width_um"], job["gap_um"], job["ring_radius_um"]
    X, dpml = job["half_length_um"], job["pml_um"]
    lam0 = job["wavelength_um"]
    fcen = 1.0 / lam0
    fmin, fmax = 1.0 / job["lambda_max_um"], 1.0 / job["lambda_min_um"]
    df = fmax - fmin
    nfreq = job["nfreq"]

    y_ring_out = -(w + gap) - float(ring_offset(X - 1.0, R))
    y_lo = y_ring_out - job["margin_um"]
    y_hi = w / 2 + job["margin_um"]

    sx = 2 * X + 2 * dpml
    sy = (y_hi - y_lo) + 2 * dpml
    y_mid = 0.5 * (y_hi + y_lo)

    x_src = -X + dpml + 0.5
    x_ref = x_src + 0.5
    x_out = X - dpml - 0.5

    parity = mp.ODD_Z
    sim = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        geometry_center=mp.Vector3(0, y_mid, 0),
        resolution=job["resolution"],
        boundary_layers=[mp.PML(dpml)],
        geometry=build_geometry(job, bus_only),
        default_material=mp.Medium(index=job["n_background"]),
        sources=[
            mp.EigenModeSource(
                src=mp.GaussianSource(fcen, fwidth=1.2 * df),
                center=mp.Vector3(x_src, 0, 0),
                size=mp.Vector3(0, job["port_width_um"], 0),
                eig_band=1,
                eig_parity=parity,
                direction=mp.X,
            )
        ],
    )

    port = mp.Vector3(0, job["port_width_um"], 0)
    ref = sim.add_mode_monitor(
        fcen, df, nfreq,
        mp.FluxRegion(center=mp.Vector3(x_ref, 0, 0), size=port))
    thru = sim.add_mode_monitor(
        fcen, df, nfreq,
        mp.FluxRegion(center=mp.Vector3(x_out, 0, 0), size=port))
    cross = sim.add_mode_monitor(
        fcen, df, nfreq,
        mp.FluxRegion(center=mp.Vector3(x_out, y_ring_out, 0), size=port))

    transit = sx * job["n_core"]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        tol=1e-6, minimum_run_time=2.0 * transit))

    def amps(mon, y0):
        c = sim.get_eigenmode_coefficients(
            mon, [1], eig_parity=parity,
            kpoint_func=lambda f, n: mp.Vector3(1, 0, 0))
        return np.abs(c.alpha[0, :, 0]) ** 2

    return {
        "freqs": [float(f) for f in mp.get_flux_freqs(ref)],
        "ref": amps(ref, 0.0).tolist(),
        "thru": amps(thru, 0.0).tolist(),
        "cross": amps(cross, y_ring_out).tolist(),
    }


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    norm = simulate(job, bus_only=True)
    full = simulate(job, bus_only=False)

    p_in = np.asarray(norm["thru"])
    if float(np.max(p_in)) <= 0.0:
        raise RuntimeError(
            "the normalisation run carries no power in the fundamental mode of "
            "the bus. The usual cause is a guide below cut-off at this width and "
            "index contrast, or a run stopped before the pulse crossed the cell"
        )
    kappa2 = np.asarray(full["cross"]) / p_in
    t2 = np.asarray(full["thru"]) / p_in

    lam = [1.0 / f for f in full["freqs"]]
    i0 = int(np.argmin([abs(l - job["wavelength_um"]) for l in lam]))
    result = {
        "ok": True,
        "job": job,
        "wavelength_um": lam,
        "kappa2": kappa2.tolist(),
        "t2": t2.tolist(),
        "unitarity": (kappa2 + t2).tolist(),
        "kappa2_at_design": float(kappa2[i0]),
        "t2_at_design": float(t2[i0]),
        "unitarity_at_design": float(kappa2[i0] + t2[i0]),
    }
    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
