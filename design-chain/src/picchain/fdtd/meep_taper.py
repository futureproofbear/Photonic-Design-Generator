#!/usr/bin/env python3
"""Meep runner for a width taper. Executed *inside* the meep environment.

This file is deliberately standalone: it imports meep and numpy and nothing
from picchain, because it runs under a different interpreter from the rest of
the chain (see ``picchain.fdtd.bridge`` for how it is invoked). Its contract is
two file paths on the command line, one JSON job in and one JSON result out.

Two runs are performed for every job, which is what makes the result a
transmission rather than an arbitrary flux:

1. a normalisation run through a straight guide of the input width, giving the
   incident mode amplitude and the incident flux;
2. the taper itself, giving the amplitude in the fundamental mode of the output
   guide, the amplitude reflected back into the input guide, and the total flux
   crossing the output plane.

The difference between the transmitted *flux* and the transmitted *fundamental
mode* is the quantity the eigenmode expansion could not reach: power that has
left the guided mode. In two dimensions it is the lateral radiation; the
vertical channel requires ``dimensions: 3``.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np


def taper_halfwidths(tip, full, length, profile, n):
    """Half-width of the guide at n stations along the taper."""
    u = np.linspace(0.0, 1.0, n)
    if profile == "linear":
        s = u
    elif profile == "raised_sine":
        s = u - np.sin(2 * np.pi * u) / (2 * np.pi)
    elif profile == "quadratic":
        s = u**2
    else:
        raise ValueError(f"unknown profile {profile!r}")
    return 0.5 * (tip + (full - tip) * s)


def build_geometry(job, straight_only: bool):
    """Polygon for the guide, from the input straight through to the output.

    Propagation is along x and the taper widens along y. ``straight_only``
    returns a guide of constant input width, which is the normalisation case.
    """
    tip, full = job["tip_width_um"], job["full_width_um"]
    L_t, L_in, L_out = job["length_um"], job["in_length_um"], job["out_length_um"]
    n_stations = job["taper_stations"]

    x0 = -(L_in + L_t / 2.0)
    if straight_only:
        total = L_in + L_t + L_out
        top = [mp.Vector3(x0, tip / 2), mp.Vector3(x0 + total, tip / 2)]
        bot = [mp.Vector3(x0 + total, -tip / 2), mp.Vector3(x0, -tip / 2)]
        verts = top + bot
    else:
        hw = taper_halfwidths(tip, full, L_t, job["profile"], n_stations)
        xs = np.linspace(-L_t / 2.0, L_t / 2.0, n_stations)
        top = [mp.Vector3(x0, tip / 2)]
        top += [mp.Vector3(float(x), float(h)) for x, h in zip(xs, hw)]
        top += [mp.Vector3(L_t / 2 + L_out, full / 2)]
        bot = [mp.Vector3(v.x, -v.y) for v in reversed(top)]
        verts = top + bot

    core = mp.Medium(index=job["n_core"])
    if job["dimensions"] == 2:
        return [mp.Prism(verts, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=core)]

    # three dimensions: the ridge sits on an unetched slab, both of the film
    # index, over a buried oxide of the cladding index
    # z = 0 is the top of the unetched slab: the slab occupies -t_slab..0 and the
    # ridge stands on it, occupying 0..t_ridge
    t_slab, t_ridge = job["slab_thickness_um"], job["ridge_height_um"]
    film = mp.Medium(index=job["n_film"])
    slab = mp.Block(
        size=mp.Vector3(mp.inf, mp.inf, t_slab),
        center=mp.Vector3(0, 0, -t_slab / 2),
        material=film,
    )
    ridge = mp.Prism(
        verts, height=t_ridge, axis=mp.Vector3(0, 0, 1),
        center=mp.Vector3(0, 0, t_ridge / 2), material=film,
    )
    return [slab, ridge]


def simulate(job, straight_only: bool):
    fcen = 1.0 / job["wavelength_um"]
    df = 0.1 * fcen
    dpml = job["pml_um"]
    L_t, L_in, L_out = job["length_um"], job["in_length_um"], job["out_length_um"]
    sx = L_in + L_t + L_out + 2 * dpml
    sy = job["width_um"]
    dims = job["dimensions"]
    sz = 0 if dims == 2 else job["height_um"]

    cell = mp.Vector3(sx, sy, sz)
    x_src = -(L_in + L_t / 2.0) + dpml + 0.5
    x_out = L_t / 2.0 + L_out - dpml - 0.5
    x_ref = x_src + 0.4

    parity = mp.ODD_Z if dims == 2 else mp.NO_PARITY
    mon_size = mp.Vector3(0, sy - 2 * dpml, 0 if dims == 2 else sz - 2 * dpml)

    sim = mp.Simulation(
        cell_size=cell,
        resolution=job["resolution"],
        boundary_layers=[mp.PML(dpml)],
        geometry=build_geometry(job, straight_only),
        default_material=mp.Medium(index=job["n_clad"]),
        sources=[
            mp.EigenModeSource(
                src=mp.GaussianSource(fcen, fwidth=df),
                center=mp.Vector3(x_src, 0, 0),
                size=mon_size,
                eig_band=1,
                eig_parity=parity,
                direction=mp.X,
            )
        ],
        force_complex_fields=False,
    )

    refl = sim.add_mode_monitor(fcen, 0, 1, mp.FluxRegion(center=mp.Vector3(x_ref, 0, 0), size=mon_size))
    tran = sim.add_mode_monitor(fcen, 0, 1, mp.FluxRegion(center=mp.Vector3(x_out, 0, 0), size=mon_size))

    # The run must not be stopped before the pulse has crossed the cell. A decay
    # criterion alone will do exactly that on a long cell, the field at the
    # output being still zero when the first check falls due, so a minimum run
    # time of twice the optical transit is imposed.
    transit = sx * job["n_core"]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        tol=1e-6, minimum_run_time=2.0 * transit))

    t_coeff = sim.get_eigenmode_coefficients(tran, [1], eig_parity=parity)
    r_coeff = sim.get_eigenmode_coefficients(refl, [1], eig_parity=parity)
    return {
        "forward_amplitude": complex(t_coeff.alpha[0, 0, 0]),
        "backward_amplitude": complex(r_coeff.alpha[0, 0, 1]),
        "transmitted_flux": float(mp.get_fluxes(tran)[0]),
        "reference_flux": float(mp.get_fluxes(refl)[0]),
    }


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    norm = simulate(job, straight_only=True)
    tap = simulate(job, straight_only=False)

    p_in = abs(norm["forward_amplitude"]) ** 2
    if p_in <= 0.0:
        raise RuntimeError(
            "the normalisation run carries no power in the fundamental mode. The usual "
            "cause is a run stopped before the pulse crossed the cell, or a guide below "
            "cut-off at this width and index contrast"
        )
    t_mode = abs(tap["forward_amplitude"]) ** 2 / p_in
    r_mode = abs(tap["backward_amplitude"]) ** 2 / p_in
    t_flux = tap["transmitted_flux"] / norm["transmitted_flux"]

    result = {
        "ok": True,
        "dimensions": job["dimensions"],
        "resolution": job["resolution"],
        "transmission_fundamental": t_mode,
        "transmission_total_flux": t_flux,
        "reflection_fundamental": r_mode,
        # power that crossed the plane but is not in the fundamental: the part a
        # guided-mode expansion cannot see
        "radiated_or_converted": max(0.0, t_flux - t_mode),
        "loss_dB": float(-10.0 * np.log10(t_mode)) if t_mode > 0 else float("inf"),
        "normalisation_check": norm["transmitted_flux"] / max(norm["reference_flux"], 1e-30),
    }
    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
