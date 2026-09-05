#!/usr/bin/env python3
"""Meep runner for a width taper. Executed *inside* the meep environment.

This file is deliberately standalone: it imports meep and numpy and nothing
from picchain, because it runs under a different interpreter from the rest of
the chain (see ``picchain.fdtd.bridge`` for how it is invoked). Its contract is
two file paths on the command line, one JSON job in and one JSON result out.

Three runs are performed for every job. The first two are what make the result
a transmission rather than an arbitrary flux; the third bounds the asymmetry
between them:

1. a normalisation run through a straight guide of the input width, giving the
   incident mode amplitude and the incident flux;
2. the taper itself, giving the amplitude in the fundamental mode of the output
   guide, the amplitude reflected back into the input guide, and the total flux
   crossing the output plane;
3. a straight guide of the *output* width, giving that guide's own attenuation
   over the same span. The normalisation guide is held at the launch width and
   the structure widens away from it, so the two differ in confinement over the
   section downstream of the taper. The difference between the two straight
   guides bounds what that asymmetry can contribute.

Every run also reports a self-normalised transmission, being its own output flux
over its own net input flux. That quotient involves no other simulation and is
at most one for a passive structure.

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


def build_geometry(job, straight_only: bool, straight_width=None):
    """Polygon for the guide, from the input straight through to the output.

    Propagation is along x and the taper widens along y. ``straight_only``
    returns a guide of constant input width, which is the normalisation case.
    """
    tip, full = job["tip_width_um"], job["full_width_um"]
    L_t, L_in, L_out = job["length_um"], job["in_length_um"], job["out_length_um"]
    n_stations = job["taper_stations"]

    # The guide runs through the absorber and out of the cell. Until 2026-09-05
    # it stopped at the inner face of the absorber, so the mode met an abrupt end
    # of the ridge exactly where the absorber began, at both ends of the cell.
    # That facet reflects, and it reflects by different amounts for guides of
    # different width, so a structure normalised against a straight guide of
    # another width inherited the difference. The two runs of one taper differed
    # by 1.15 per cent in net flux at the input monitor, where the source and the
    # input section were identical, and the quotient rose above unity. The slab
    # was built with an infinite extent throughout and was never affected.
    dpml = job["pml_um"]

    x0 = -(L_in + L_t / 2.0) - dpml
    x1 = L_t / 2.0 + L_out + dpml
    if straight_only:
        w = tip if straight_width is None else float(straight_width)
        top = [mp.Vector3(x0, w / 2), mp.Vector3(x1, w / 2)]
        bot = [mp.Vector3(x1, -w / 2), mp.Vector3(x0, -w / 2)]
        verts = top + bot
    else:
        hw = taper_halfwidths(tip, full, L_t, job["profile"], n_stations)
        xs = np.linspace(-L_t / 2.0, L_t / 2.0, n_stations)
        top = [mp.Vector3(x0, tip / 2)]
        top += [mp.Vector3(float(x), float(h)) for x, h in zip(xs, hw)]
        top += [mp.Vector3(x1, full / 2)]
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


def simulate(job, straight_only: bool, straight_width=None):
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
        geometry=build_geometry(job, straight_only, straight_width),
        # `n_clad` is the effective index of the unetched film beside the ridge,
        # which is the surround of the plane reduction. In three dimensions the
        # slab is built explicitly, so that index would place the slab twice and
        # the ambient would be a medium of 1.55 that exists nowhere in the
        # device. The surround there is the cladding and the buried oxide.
        default_material=mp.Medium(
            index=job["n_clad"] if dims == 2 else job["n_ambient"]
        ),
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

    # A third simulation, of a straight guide at the *output* width. The
    # normalisation guide is held at the launch width, which is the least
    # confined cross-section in the problem, while the structure widens away
    # from it. That asymmetry was proposed as the cause of a transmission above
    # unity and could not be bounded without measuring the wide guide's own
    # attenuation over the same span. It is measured here rather than assumed.
    wide = simulate(job, straight_only=True, straight_width=job["full_width_um"])

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

    # Self-normalised transmission: each run graded by its own two monitors and
    # by nothing else. `reference_flux` is the net flux just downstream of the
    # source, so incident less reflected, and `transmitted_flux` is the net flux
    # at the output plane. For a passive structure the quotient is at most one,
    # whatever any other run did. The reference simulation does not enter it, so
    # a value above unity cannot be attributed to the normalisation guide and
    # localises the defect to the run that produced it.
    def self_normalised(run):
        denom = run["reference_flux"]
        return run["transmitted_flux"] / denom if abs(denom) > 1e-30 else float("nan")

    result = {
        "ok": True,
        "dimensions": job["dimensions"],
        "resolution": job["resolution"],
        # the three self-normalised budgets, in the order the simulations ran
        "self_normalised_taper": self_normalised(tap),
        "self_normalised_narrow_guide": self_normalised(norm),
        "self_normalised_wide_guide": self_normalised(wide),
        # what the straight guides lose over the span between the two monitors
        # the raw fluxes and amplitudes of all three simulations, so that a
        # budget can be reconstructed by a reader without solving anything
        "raw": {
            name: {
                "transmitted_flux": run["transmitted_flux"],
                "reference_flux": run["reference_flux"],
                "forward_amplitude_sq": abs(run["forward_amplitude"]) ** 2,
                "backward_amplitude_sq": abs(run["backward_amplitude"]) ** 2,
            }
            for name, run in (("taper", tap), ("narrow_guide", norm), ("wide_guide", wide))
        },
        "narrow_guide_loss": 1.0 - self_normalised(norm),
        "wide_guide_loss": 1.0 - self_normalised(wide),
        # the quantity the reference asymmetry can contribute, being the excess
        # attenuation of the launch width over the output width
        "reference_asymmetry": self_normalised(wide) - self_normalised(norm),
        "full_width_um": float(job["full_width_um"]),
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
