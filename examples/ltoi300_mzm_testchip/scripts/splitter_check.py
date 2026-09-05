"""The splitter this chip draws, which is no longer the kit's cell.

The design opened the access-port separation from the kit's 2.55 um to 2.80,
because 2.55 carrying the 2.5 um modulation arm brings the two guides within
50 nm of each other and the process requires 300. That is a change to the
splitter, and the report recorded it as an assumption: the multimode section was
left at the 13.5 um the kit draws, and 13.5 is the imaging length of a section
whose ports sit 2.55 um apart.

This settles whether that assumption costs anything. The section is solved once
in its full cross-section and the cascade is then re-evaluated at each length,
which is what makes a length sweep cost a cascade rather than a solve. Both
separations are put through the same instrument.

The question is narrow and worth stating. The imaging *length* of a multimode
section is fixed by the beat length of its guided modes and therefore by the
section width, which did not change. What the port separation changes is where
the images land, so the cost of moving the ports is a projection loss rather
than a change of length. The sweep is run anyway, because that reasoning is an
argument and the sweep is a measurement.

    python examples/ltoi300_mzm_testchip/scripts/splitter_check.py
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np

print = functools.partial(print, flush=True)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain import mmi_eme                            # noqa: E402
from picchain.materials import MaterialLibrary          # noqa: E402

MATERIALS = ROOT / "design-chain" / "pdk" / "LXT_LT_PRO" / "materials_lt_pro.yaml"
STACK = dict(film_um=0.300, etch_um=0.180, sidewall_deg=70.0)
LAM = 1.55
DRAWN_LENGTH = 13.5          # the kit's multimode section, kept by this design

#: the arm this chip carries and the port face the builder draws
ARM_UM, PORT_W_UM, MMI_W_UM = 2.5, 1.95, 4.50
SEPARATIONS = (2.55, 2.80)   # the kit's, and this design's


def graded(half_fine, d_fine, half_total, d_coarse):
    fine = np.arange(0.0, half_fine + d_fine / 2, d_fine)
    coarse = np.arange(half_fine + d_coarse, half_total + d_coarse / 2, d_coarse)
    half = np.concatenate([fine, coarse])
    return np.concatenate([-half[:0:-1], half])


def build(separation_um: float) -> dict:
    lib = MaterialLibrary(MATERIALS) if MATERIALS.exists() else MaterialLibrary()
    stack = dict(STACK, n_film=float(lib["LiTaO3"].index(LAM, "e")),
                 n_clad=float(lib["SiO2"].index(LAM)))
    half = max(MMI_W_UM, separation_um + 2 * ARM_UM) / 2 + 2.0
    x = graded(half, 0.025, half + 3.0, 0.10)
    y = np.concatenate([np.arange(-1.25, -0.15, 0.060),
                        np.arange(-0.15, 0.451, 0.010),
                        np.arange(0.46, 1.26, 0.060)])
    return dict(width_um=ARM_UM, port_width_um=PORT_W_UM, mmi_width_um=MMI_W_UM,
                mmi_length_um=DRAWN_LENGTH, port_separation_um=separation_um,
                ports_in=1, wavelength_um=LAM, x=x, y=y, stack=stack,
                taper_length_um=25.0, lead_um=2.0, taper_slices=6,
                num_modes=12, polarisation="TE")


def main() -> int:
    print(f"the 1x2 splitter of this chip: {MMI_W_UM} um section, "
          f"{PORT_W_UM} um ports, {ARM_UM} um arms, at {LAM} um\n")
    results = {}
    for sep in SEPARATIONS:
        job = build(sep)
        print(f"port separation {sep} um: grid {len(job['x'])} by {len(job['y'])}, "
              f"{job['num_modes']} modes per section")
        st = mmi_eme.stack_3d(job)
        r = mmi_eme.solve_from_stack(st, DRAWN_LENGTH)
        print(f"  at the drawn {DRAWN_LENGTH} um: transmission {r['transmission']:.4f}, "
              f"excess {r['excess_loss_dB']:.3f} dB, imbalance {r['imbalance_dB']:+.3f} dB")

        best = (0.0, None)
        for L in np.arange(10.0, 18.01, 0.25):
            rr = mmi_eme.solve_from_stack(st, float(L))
            if rr["transmission"] > best[0]:
                best = (rr["transmission"], float(L))
        print(f"  swept 10 to 18 um: best {best[0]:.4f} at {best[1]:.2f} um, "
              f"which is {100 * (best[1] - DRAWN_LENGTH) / DRAWN_LENGTH:+.1f} per cent "
              f"from the drawn length\n")
        results[sep] = (r, best)

    a, b = results[SEPARATIONS[0]][0], results[SEPARATIONS[1]][0]
    d = 10 * np.log10(max(b["transmission"], 1e-12) / max(a["transmission"], 1e-12))
    verb = "gains" if d > 0 else "costs"
    print(f"opening the ports from {SEPARATIONS[0]} to {SEPARATIONS[1]} um at the "
          f"drawn length {verb} {abs(d):.3f} dB")
    print("the imaging length is set by the section width, which did not change;")
    print("what the separation moves is where the images land")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
