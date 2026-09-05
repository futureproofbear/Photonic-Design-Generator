"""What a non-dispersive extraction costs on a 200 nm silicon-nitride guide.

Every compact model in the CORNERSTONE SiN 200 nm kit is tabulated from a
simulation that declares `simulation.dispersive: false`, and every one is
tabulated against wavelength over a band about two per cent wide. Holding the
material index fixed across that band is not visible in the transmission, which
moves by a fraction of a per cent, and it is the whole of the group index.

A group index is what a delay line, a ring free spectral range and a
Mach-Zehnder period are made of, so a model that carries the wrong one is wrong
about the quantity a designer reads it for. This measures the error.

The instrument is one mode solve run twice. The guide is solved with silicon
nitride and silica dispersing as the literature says they do, and again with
both indices frozen at the centre of the band, which is what a non-dispersive
simulation does. The group index follows from a central difference in
wavelength in each case, and the difference between the two is the error.

    n_g = n_eff - lambda d(n_eff)/d(lambda)

Nothing of the kit is read. The stack is the public CORNERSTONE geometry, being
200 nm of stoichiometric nitride on thermal oxide under an oxide cladding, and
the widths are chosen here to hold the guide near single mode at each band
rather than taken from any cell. The two material models are Luke 2015 for the
nitride and Malitson 1965 for the oxide, both in the chain's own library.

    python examples/cs_sin200_models/scripts/dispersion_cost.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain.materials import MaterialLibrary            # noqa: E402
from picchain.solvers.fdmode import solve_modes           # noqa: E402

FILM_UM = 0.200                 # the CORNERSTONE nitride
#: one band per decade of the kit's coverage, with a width holding the guide
#: near the single-mode condition at that band. The widths are this study's
#: choice and are not read from any cell.
BANDS = [
    (0.532, 0.50), (0.637, 0.60), (0.780, 0.70), (0.850, 0.75),
    (1.064, 0.90), (1.310, 1.10), (1.550, 1.30),
]
DLAM = 0.010                    # the half-span of the central difference, um


def grid(width_um: float, lam_um: float):
    """A graded mesh, fine across the guide and coarse into the cladding."""
    half = width_um / 2
    x_fine = np.arange(-half - 0.25, half + 0.25 + 1e-9, 0.010)
    x_out = np.arange(0.30, 3.0 + 1e-9, 0.08)
    x = np.concatenate([-(half + x_out)[::-1], x_fine, half + x_out])
    y = np.concatenate([np.arange(-1.6, -0.12, 0.06),
                        np.arange(-0.12, FILM_UM + 0.121, 0.005),
                        np.arange(FILM_UM + 0.18, 1.8, 0.06)])
    return np.unique(x), np.unique(y)


def eps_of(x, y, width_um, n_core, n_clad):
    """A full-etch strip of nitride, buried in oxide."""
    eps = np.full((len(x), len(y)), n_clad**2, dtype=float)
    inside = (np.abs(x)[:, None] <= width_um / 2) & \
             ((y >= 0.0) & (y <= FILM_UM))[None, :]
    eps[inside] = n_core**2
    return eps


def n_eff_at(lam, width, lib, frozen_at=None):
    """The fundamental index at one wavelength, dispersing or frozen."""
    at = lam if frozen_at is None else frozen_at
    n_core = float(lib["Si3N4"].index(at))
    n_clad = float(lib["SiO2"].index(at))
    x, y = grid(width, lam)
    eps = eps_of(x, y, width, n_core, n_clad)
    modes = solve_modes(x, y, eps, eps, lam, "TE", 2, None)
    if not modes:
        raise RuntimeError(f"no mode at {lam} um, width {width}")
    return float(modes[0].n_eff)


def group_index(lam, width, lib, frozen: bool):
    at = lam if frozen else None
    lo = n_eff_at(lam - DLAM, width, lib, frozen_at=at)
    mid = n_eff_at(lam, width, lib, frozen_at=at)
    hi = n_eff_at(lam + DLAM, width, lib, frozen_at=at)
    return mid, mid - lam * (hi - lo) / (2 * DLAM)


def main() -> int:
    lib = MaterialLibrary()
    print(f"{'band':>7} {'width':>6} {'n_eff':>8} {'n_g dispersing':>15} "
          f"{'n_g frozen':>11} {'error':>8} {'per cent':>9}")
    for lam, width in BANDS:
        n_eff, ng_true = group_index(lam, width, lib, frozen=False)
        _, ng_frozen = group_index(lam, width, lib, frozen=True)
        err = ng_frozen - ng_true
        print(f"{lam:7.3f} {width:6.2f} {n_eff:8.5f} {ng_true:15.5f} "
              f"{ng_frozen:11.5f} {err:+8.5f} {100 * err / ng_true:+9.2f}")
    print("\nthe error is what a non-dispersive extraction leaves out of the group")
    print("index, being the material's own dispersion weighted by the fraction of")
    print("the mode that sits in the nitride")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
