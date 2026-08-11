#!/usr/bin/env python3
"""Meep runner for a finite Bragg grating. Executed inside the meep environment.

The purpose is a check on κ that owes nothing to coupled-mode theory. The chain
obtains κ by Fourier analysis of the index profile and then evaluates the
spectrum by transfer matrices; this runner instead propagates a pulse through
the drawn structure and measures what comes back.

**The comparison is made in two dimensions, on both sides.** The chain's κ comes
from a three-dimensional cross-section and cannot be set against a
two-dimensional solve without confounding two questions at once. The stage that
invokes this runner therefore recomputes the index perturbation for the same
two-dimensional structure, so that what is tested here is the coupled-mode and
transfer-matrix machinery alone, with the mode solver held identical.

Two runs are performed: the grating itself, and a straight guide of the same
length, which normalises out the source spectrum and the residual reflection of
the source and boundaries.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np


def geometry(job, with_posts: bool):
    """Guide along x, with square posts either side when requested."""
    core = mp.Medium(index=job["n_core"])
    w = job["width_um"]
    total = job["in_length_um"] + job["n_periods"] * job["period_um"] + job["out_length_um"]
    x0 = -total / 2.0

    items = [mp.Block(size=mp.Vector3(total, w, mp.inf),
                      center=mp.Vector3(x0 + total / 2, 0, 0), material=core)]
    if not with_posts:
        return items

    pw, pl = job["post_width_um"], job["post_length_um"]
    y_c = w / 2 + job["post_gap_um"] + pw / 2
    g0 = x0 + job["in_length_um"]
    for k in range(int(job["n_periods"])):
        xc = g0 + (k + 0.5) * job["period_um"]
        for sgn in (-1, 1):
            items.append(mp.Block(size=mp.Vector3(pl, pw, mp.inf),
                                  center=mp.Vector3(xc, sgn * y_c, 0), material=core))
    return items


def simulate(job, with_posts: bool):
    lam = job["wavelength_um"]
    fcen = 1.0 / lam
    df = job["fractional_bandwidth"] * fcen
    dpml = job["pml_um"]
    total = job["in_length_um"] + job["n_periods"] * job["period_um"] + job["out_length_um"]
    sx = total + 2 * dpml
    sy = job["cell_width_um"]

    x0 = -total / 2.0
    x_src = x0 + dpml + 0.5
    x_ref = x_src + 0.6
    x_out = -x0 - dpml - 0.5

    mon = mp.Vector3(0, sy - 2 * dpml, 0)
    sim = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        resolution=job["resolution"],
        boundary_layers=[mp.PML(dpml)],
        geometry=geometry(job, with_posts),
        default_material=mp.Medium(index=job["n_clad"]),
        sources=[mp.EigenModeSource(
            src=mp.GaussianSource(fcen, fwidth=df),
            center=mp.Vector3(x_src, 0, 0), size=mon,
            eig_band=1, eig_parity=mp.ODD_Z, direction=mp.X)],
    )
    nfreq = job["n_frequencies"]
    refl = sim.add_mode_monitor(fcen, df, nfreq,
                                mp.FluxRegion(center=mp.Vector3(x_ref, 0, 0), size=mon))
    tran = sim.add_mode_monitor(fcen, df, nfreq,
                                mp.FluxRegion(center=mp.Vector3(x_out, 0, 0), size=mon))

    transit = sx * job["n_core"]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        tol=1e-6, minimum_run_time=3.0 * transit))

    r = sim.get_eigenmode_coefficients(refl, [1], eig_parity=mp.ODD_Z)
    t = sim.get_eigenmode_coefficients(tran, [1], eig_parity=mp.ODD_Z)
    return {
        "freq": [float(f) for f in mp.get_flux_freqs(refl)],
        "backward": np.abs(r.alpha[0, :, 1]) ** 2,
        "forward": np.abs(t.alpha[0, :, 0]) ** 2,
    }


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    straight = simulate(job, with_posts=False)
    grating = simulate(job, with_posts=True)

    incident = np.asarray(straight["forward"])
    reflected = np.asarray(grating["backward"]) - np.asarray(straight["backward"])
    R = np.clip(reflected / np.maximum(incident, 1e-30), 0.0, 1.0)
    T = np.asarray(grating["forward"]) / np.maximum(incident, 1e-30)

    freq = np.asarray(grating["freq"])
    lam_um = 1.0 / freq
    i_peak = int(np.argmax(R))
    R_peak = float(R[i_peak])

    L = float(job["n_periods"] * job["period_um"])
    # R = tanh^2(kappa L) inverted for kappa, which is the quantity the chain
    # predicts from coupled-mode theory
    kappa = float(np.arctanh(min(np.sqrt(R_peak), 1 - 1e-12)) / L)

    result = {
        "ok": True,
        "n_periods": job["n_periods"],
        "grating_length_um": L,
        "resolution": job["resolution"],
        "peak_reflectivity": R_peak,
        "bragg_wavelength_nm": float(lam_um[i_peak] * 1000.0),
        "kappa_per_um": kappa,
        "kappa_per_cm": kappa * 1e4,
        "kappa_L": kappa * L,
        "transmission_at_peak": float(T[i_peak]),
        "sum_at_peak": float(R_peak + T[i_peak]),
        "spectrum_wavelength_nm": (lam_um * 1000.0).tolist(),
        "spectrum_reflectivity": R.tolist(),
    }
    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
