#!/usr/bin/env python3
"""MPB runner: kappa from the photonic band gap. Executed inside the meep environment.

This is the instrument the time-domain check showed to be needed. Measuring a
coupling constant by propagation requires a length of order 1/kappa, which for a
weak grating is millimetres and beyond any finite-difference domain; and forcing
the grating strong enough to measure over a short length introduces radiation,
which coupled-mode theory does not model and which then confounds the
comparison.

A band-structure calculation avoids both. One period is solved under Bloch
boundary conditions, so there is no length, no propagation and no radiation
channel. At the Brillouin zone edge the guided band splits, and the width of
that split is the stop band:

    delta_omega = 2 kappa v_g       =>      kappa = pi n_g delta_f / a

with delta_f the gap in units of c/a and a the period. The relation is the
definition of kappa in coupled-mode theory, so what is tested is whether the
chain's Fourier construction of kappa from the index profile agrees with the
gap the structure actually possesses.

Band identification
-------------------
A supercell in the transverse direction carries many cladding states alongside
the guided pair. Bands are therefore selected by the fraction of their energy
inside the core, and the gap is taken between consecutive *guided* bands nearest
the expected Bragg frequency, rather than between whichever two bands happen to
be adjacent.
"""

from __future__ import annotations

import json
import sys

import meep as mp
import numpy as np
from meep import mpb


def build(job):
    """One period: a core strip along the periodic axis, with two posts."""
    w, pw, pl = job["width_um"], job["post_width_um"], job["post_length_um"]
    a = job["period_um"]
    y_c = w / 2 + job["post_gap_um"] + pw / 2
    core = mp.Medium(index=job["n_core"])

    items = [mp.Block(size=mp.Vector3(mp.inf, w / a, mp.inf),
                      center=mp.Vector3(0, 0, 0), material=core)]
    for sgn in (-1, 1):
        items.append(mp.Block(size=mp.Vector3(pl / a, pw / a, mp.inf),
                              center=mp.Vector3(0, sgn * y_c / a, 0), material=core))
    return items


def main() -> int:
    job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    out_path = sys.argv[2]

    a = job["period_um"]
    sy = job["cell_width_um"] / a          # transverse supercell, in units of a
    w = job["width_um"] / a

    # A high-order grating opens its gap far above the fundamental, and a wide
    # supercell puts hundreds of cladding states in between. Solving upward from
    # the lowest band would therefore return the first-order gap, which is not
    # the one the device uses. The solve is instead targeted at the frequency the
    # order implies, so that only the bands surrounding it are computed.
    f_expected = job["order"] / (2.0 * job["n_eff_guess"])

    # The lattice unit here is the grating period, not the micrometre, so the
    # declared resolution in pixels per micrometre is converted before it is
    # handed to MPB. Until 2026-08-06 the figure was passed through unconverted,
    # so every solve ran at 1/period of the density that was asked for, being a
    # factor of 1.28 on the validation baseline.
    res_per_lattice = max(1, int(round(job["resolution"] * a)))

    # Three settings that the size of the quantity demands. The band gap is of
    # order 1e-5 of the band frequency, so the two eigenvalues must be separated
    # far below their own discretisation error.
    #
    # MPB always averages the permittivity over a boundary pixel, and the
    # accuracy of that average is set by `mesh_size`, the sub-grid on which the
    # effective tensor is built. The default of 3 leaves a staircase residual
    # that does not cancel between two nearly degenerate bands. It costs setup
    # time only and does not enter the eigensolve. There is no `eps_averaging`
    # argument on the MPB solver, unlike the meep one.
    #
    # The tolerance is tightened because it is relative to the eigenvalue and the
    # quantity of interest is their difference.
    ms = mpb.ModeSolver(
        geometry_lattice=mp.Lattice(size=mp.Vector3(1, sy)),
        geometry=build(job),
        default_material=mp.Medium(index=job["n_clad"]),
        resolution=res_per_lattice,
        num_bands=job["num_bands"],
        k_points=[mp.Vector3(0.5, 0, 0)],   # the Brillouin zone edge
        target_freq=f_expected,
        tolerance=job.get("tolerance", 1e-9),
        mesh_size=job.get("mesh_size", 7),
    )
    ms.run_te()                              # in-plane E, matching the quasi-TE guide
    freqs = np.asarray(ms.all_freqs[0], dtype=float)

    # energy inside the core, band by band, to separate guided from continuum
    confinement = []
    for band in range(1, job["num_bands"] + 1):
        ms.get_dfield(band)
        ms.compute_field_energy()
        frac = ms.compute_energy_in_dielectric(job["n_core"] ** 2 - 0.01,
                                               job["n_core"] ** 2 + 0.01)
        confinement.append(float(frac))
    confinement = np.asarray(confinement)

    guided = np.where(confinement >= job["confinement_threshold"])[0]

    pairs = [(i, j) for i, j in zip(guided, guided[1:]) if j == i + 1]
    if not pairs:
        result = {"ok": False,
                  "reason": "no adjacent pair of guided bands was found",
                  "freqs": freqs.tolist(), "confinement": confinement.tolist()}
    else:
        # the pair whose midpoint lies nearest the expected Bragg frequency
        i, j = min(pairs, key=lambda p: abs(0.5 * (freqs[p[0]] + freqs[p[1]]) - f_expected))
        df = float(freqs[j] - freqs[i])
        f_mid = float(0.5 * (freqs[i] + freqs[j]))
        kappa = np.pi * job["n_g"] * df / a          # 1/um
        result = {
            "ok": True,
            "band_lower": int(i + 1),
            "band_upper": int(j + 1),
            "f_lower": float(freqs[i]),
            "f_upper": float(freqs[j]),
            "gap_df": df,
            "gap_midpoint_f": f_mid,
            "bragg_wavelength_nm": float(a / f_mid * 1000.0),
            "expected_f": float(f_expected),
            "kappa_per_um": float(kappa),
            "kappa_per_cm": float(kappa * 1e4),
            # what was actually solved, so the guard compares like with like
            "resolution_px_per_um": float(job["resolution"]),
            "resolution_px_per_period": int(res_per_lattice),
            "relative_gap": float(df / f_mid),
            "mesh_size": int(job.get("mesh_size", 7)),
            "tolerance": float(job.get("tolerance", 1e-9)),
            "confinement": confinement.tolist(),
            "freqs": freqs.tolist(),
        }

    if mp.am_master():
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
