"""Transfer of a published propagation loss to the ring cross-section.

Wang et al. measure their loss on a guide 2.0 um wide etched 500 nm into a
600 nm film. The ltoi300 ring is 0.7 um wide etched 180 nm into a 300 nm film.
The same number cannot be carried across, because the same paper separates the
loss by thermal response spectroscopy and finds absorption to be 2.0 MHz of a
26.8 MHz total. Ninety-three per cent of the loss is scattering, and scattering
is a property of the geometry as much as of the process.

Payne and Lacey give the scattering loss of a guide as proportional to the
field intensity at the etched wall, the roughness statistics entering as a
separate factor. Where two geometries share a process, the ratio of

    S = (integral of |E|^2 along both sidewalls) / (integral of |E|^2 over the
        cross-section)

is the ratio of their sidewall scattering. Both fields are solved by the chain
on the same stack and the same material file, so the comparison is like for
like in everything but the geometry.

The transfer assumes the two processes leave the same roughness, and that
assumption is the weakest step. It is stated rather than hidden, and the result
is a bracket rather than a figure.
"""

from __future__ import annotations

import glob
import json
import sys

import numpy as np
from scipy.interpolate import RegularGridInterpolator

# Wang et al., Nature 629, 784 (2024)
PUBLISHED = (
    ("unreduced LiTaO3, best resonator", 5.6),
    ("unreduced LiTaO3, typical", 7.3),
    ("reduced LTOI substrate, best field", 8.8),
    ("reduced LTOI substrate, wafer mean", 17.1),
)
ABSORBED_FRACTION = 2.0 / 26.8      # kappa_abs / kappa_0, thermal response


def load(pattern: str):
    run = sorted(glob.glob(f"{pattern}"))[-1]
    d = np.load(run + "/mode.npz")
    xs = json.load(open(run + "/cross_section.json"))
    ridge = [s for s in xs["shapes"] if s["name"] == "ridge"][0]["points"]
    return d["x_um"], d["y_um"], d["field_bare"], np.asarray(ridge, float), xs["wavelength_um"]


def sidewall_factor(x, y, F, ridge) -> float:
    P = np.abs(F) ** 2
    norm = np.trapezoid(np.trapezoid(P, y, axis=1), x)
    yy = np.linspace(ridge[:, 1].min(), ridge[:, 1].max(), 400)
    right = ridge[ridge[:, 0] > 0]
    order = np.argsort(right[:, 1])
    hw = np.interp(yy, right[order, 1], right[order, 0])
    itp = RegularGridInterpolator((x, y), P, bounds_error=False, fill_value=0.0)
    line = itp(np.column_stack([hw, yy])) + itp(np.column_stack([-hw, yy]))
    return float(np.trapezoid(line, yy) / norm)


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "examples/ltoi300_ring/runs"
    cases = {
        "ring, 0.7 um wide, 180 nm etch, 1310 nm": f"{root}/*oband_ltpro/",
        "reference, 2.0 um wide, 500 nm etch, 1310 nm": f"{root}/*racetrack_xs_1310/",
        "reference, 2.0 um wide, 500 nm etch, 1550 nm": f"{root}/*racetrack_xs/",
    }
    S = {}
    for name, pat in cases.items():
        x, y, F, ridge, lam = load(pat)
        S[name] = sidewall_factor(x, y, F, ridge)
        print(f"{name:46} S = {S[name]:8.5f} /um")

    ring = S["ring, 0.7 um wide, 180 nm etch, 1310 nm"]
    for ref_name in list(cases)[1:]:
        r = ring / S[ref_name]
        print(f"\nagainst the {ref_name}: ratio {r:.2f}")
        print(f"{'published':38} {'scattering':>12} {'transferred':>14}")
        for label, dBm in PUBLISHED:
            scat = dBm * (1 - ABSORBED_FRACTION)
            absb = dBm * ABSORBED_FRACTION
            out = (scat * r + absb) / 100.0        # dB/m -> dB/cm
            print(f"{label:38} {scat:9.1f} dB/m {out:11.3f} dB/cm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
