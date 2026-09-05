#!/usr/bin/env python3
"""Meep runner for a multimode interference splitter. Executed *inside* the meep
environment.

Standalone in the manner of ``meep_taper``: it imports meep and numpy and
nothing from picchain, and its contract is two paths on the command line, one
JSON job in and one JSON result out.

What is solved
--------------
Propagation is along x. An access taper carries each port from the guide width
to the port width, the multimode section is a rectangle, and the output tapers
return to the guide width. One input and two outputs, or two and two, according
to ``ports_in``. The ports are placed on the end faces at the declared
centre-to-centre separation, so the gap between them is
``port_separation - port_width`` and is drawn open.

In two dimensions the background index is the effective index of the film
*beside* the ridge, which on a partially etched platform is the unetched slab.
The same reduction the taper and the coupler use applies here, and it carries
the lateral channel only.

Two runs are performed for every job:

1. a straight guide of the input width alone, giving the incident amplitude;
2. the splitter, giving the amplitude in the fundamental mode of each output
   and the amplitude reflected into the input.

The transmission of each port is the second normalised by the first. Their sum
with the reflection is the model's own check, and a passive splitter cannot
exceed unity.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np


def _taper(x0: float, x1: float, w0: float, w1: float, yc: float, n: int):
    """Polygon of a linear width taper on the centre line ``yc``."""
    xs = np.linspace(x0, x1, n)
    hw = np.linspace(w0, w1, n) / 2.0
    top = [mp.Vector3(float(x), float(yc + h)) for x, h in zip(xs, hw)]
    bot = [mp.Vector3(float(x), float(yc - h)) for x, h in zip(xs, hw)][::-1]
    return top + bot


def port_centres(job) -> tuple[list[float], list[float]]:
    """Centre lines of the input and the output ports."""
    sep = job["port_separation_um"]
    n_in = job["ports_in"]
    ins = [0.0] if n_in == 1 else [+sep / 2, -sep / 2]
    outs = [+sep / 2, -sep / 2]
    return ins, outs


def build_geometry(job, straight_only: bool):
    w, wp = job["width_um"], job["port_width_um"]
    Lm, Wm, Lt = job["mmi_length_um"], job["mmi_width_um"], job["taper_length_um"]
    lead = job["lead_um"]
    core = mp.Medium(index=job["n_core"])
    n = job["taper_stations"]
    ins, outs = port_centres(job)

    x_in0 = -(Lm / 2 + Lt + lead)
    x_in1 = -(Lm / 2 + Lt)
    x_out0 = Lm / 2 + Lt
    x_out1 = Lm / 2 + Lt + lead

    if straight_only:
        return [mp.Block(size=mp.Vector3(2 * (Lm / 2 + Lt + lead) + 4.0, w, mp.inf),
                         center=mp.Vector3(0, ins[0], 0), material=core)]

    shapes = [mp.Block(size=mp.Vector3(Lm, Wm, mp.inf),
                       center=mp.Vector3(0, 0, 0), material=core)]
    for yc in ins:
        shapes.append(mp.Block(size=mp.Vector3(lead + 2.0, w, mp.inf),
                               center=mp.Vector3(x_in0 - 1.0 + (lead + 2.0) / 2, yc, 0),
                               material=core))
        shapes.append(mp.Prism(_taper(x_in1, -Lm / 2, w, wp, yc, n), height=mp.inf,
                               axis=mp.Vector3(0, 0, 1), material=core))
    for yc in outs:
        shapes.append(mp.Prism(_taper(Lm / 2, x_out0, wp, w, yc, n), height=mp.inf,
                               axis=mp.Vector3(0, 0, 1), material=core))
        shapes.append(mp.Block(size=mp.Vector3(lead + 2.0, w, mp.inf),
                               center=mp.Vector3(x_out1 + 1.0 - (lead + 2.0) / 2, yc, 0),
                               material=core))
    return shapes


def simulate(job, straight_only: bool, resolution: int):
    w = job["width_um"]
    Lm, Wm, Lt = job["mmi_length_um"], job["mmi_width_um"], job["taper_length_um"]
    lead, dpml = job["lead_um"], job["pml_um"]
    lam0 = job["wavelength_um"]
    fcen = 1.0 / lam0
    df = 1.0 / job["lambda_min_um"] - 1.0 / job["lambda_max_um"]

    ins, outs = port_centres(job)
    half_x = Lm / 2 + Lt + lead
    sx = 2 * half_x + 2 * dpml
    sy = max(Wm, job["port_separation_um"] + 2 * w) + 2 * job["margin_um"] + 2 * dpml

    x_src = -half_x + dpml + 0.5
    x_ref = x_src + 0.5
    x_out = half_x - dpml - 0.5

    parity = mp.ODD_Z
    port = mp.Vector3(0, job["port_width_monitor_um"], 0)
    y_src = ins[0]

    sim = mp.Simulation(
        cell_size=mp.Vector3(sx, sy, 0),
        resolution=resolution,
        boundary_layers=[mp.PML(dpml)],
        geometry=build_geometry(job, straight_only),
        default_material=mp.Medium(index=job["n_background"]),
        sources=[mp.EigenModeSource(
            src=mp.GaussianSource(fcen, fwidth=1.2 * df),
            center=mp.Vector3(x_src, y_src, 0), size=port,
            eig_band=1, eig_parity=parity, direction=mp.X)],
    )

    nfreq = job["nfreq"]
    ref = sim.add_mode_monitor(fcen, df, nfreq, mp.FluxRegion(
        center=mp.Vector3(x_ref, y_src, 0), size=port))
    mons = [sim.add_mode_monitor(fcen, df, nfreq, mp.FluxRegion(
        center=mp.Vector3(x_out, yc, 0), size=port)) for yc in outs]

    transit = sx * job["n_core"]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        tol=1e-6, minimum_run_time=2.5 * transit))

    def amp(mon, forward=True):
        c = sim.get_eigenmode_coefficients(
            mon, [1], eig_parity=parity,
            kpoint_func=lambda f, n: mp.Vector3(1, 0, 0))
        return np.abs(c.alpha[0, :, 0 if forward else 1]) ** 2

    return {
        "freqs": [float(f) for f in mp.get_flux_freqs(ref)],
        "outputs": [amp(m).tolist() for m in mons],
        "reflected": amp(ref, forward=False).tolist(),
        "incident": amp(ref).tolist(),
    }


def measure(job, resolution: int):
    norm = simulate(job, True, resolution)
    full = simulate(job, False, resolution)
    p_in = np.asarray(norm["incident"])
    if float(np.max(p_in)) <= 0.0:
        raise RuntimeError(
            "the normalisation run carries no power in the fundamental mode of the "
            "input guide. The usual cause is a guide below cut-off at this width and "
            "index contrast, or a run stopped before the pulse crossed the cell")
    outs = [np.asarray(o) / p_in for o in full["outputs"]]
    refl = np.asarray(full["reflected"]) / p_in
    lam = [1.0 / f for f in full["freqs"]]
    return lam, outs, refl


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    lam, outs, refl = measure(job, job["resolution"])
    i0 = int(np.argmin([abs(x - job["wavelength_um"]) for x in lam]))
    total = sum(outs) + refl
    imbalance = 10 * np.log10(np.clip(outs[0], 1e-12, None) /
                              np.clip(outs[1], 1e-12, None))

    result = {
        "ok": True,
        "resolution": job["resolution"],
        "wavelength_um": lam,
        "port_transmission": [o.tolist() for o in outs],
        "reflection": refl.tolist(),
        "accounted": total.tolist(),
        "imbalance_dB": imbalance.tolist(),
        "transmission_at_design": float(sum(o[i0] for o in outs)),
        "excess_loss_dB_at_design": float(
            -10 * np.log10(max(sum(o[i0] for o in outs), 1e-12))),
        "imbalance_dB_at_design": float(imbalance[i0]),
        "reflection_at_design": float(refl[i0]),
        "accounted_at_design": float(total[i0]),
    }

    guard = int(job.get("convergence_resolution") or 0)
    if guard and guard != job["resolution"]:
        _, outs_c, _ = measure(job, guard)
        coarse = float(sum(o[i0] for o in outs_c))
        result["guard"] = {
            "resolution": guard,
            "transmission_at_design": coarse,
            "shift_fraction": float(
                (result["transmission_at_design"] - coarse)
                / result["transmission_at_design"]),
        }

    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
