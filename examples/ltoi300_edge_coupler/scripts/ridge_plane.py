"""The one plane of the edge coupler where the taper is not adiabatic.

The ridge does not grow from zero. It appears at the plane where the upper taper
begins, already at its full etch depth and at a quarter of a micrometre wide, so
the cross-section changes discontinuously there and the local-mode assumption
that holds everywhere else fails at that one station.

The loss is therefore measured directly. The cross-section is solved on either
side of the plane, on the same grid, and the fundamental of the first is
projected onto the guided set of the second. What fails to project leaves the
guided set, and since only one mode is guided on either side, that power
radiates rather than converting.

Both cross-sections are cut out of the emitted GDS. The slab strip is the same
on both sides of the plane, which is the point: the step is the ridge alone.

    python examples/ltoi300_edge_coupler/scripts/ridge_plane.py [oband|cband]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))
sys.path.insert(0, str(ROOT / "design-chain" / "tools"))
sys.path.insert(0, str(ROOT / "design-chain" / "pdk" / "lxt_pdk_gf"))

from picchain import eme                                   # noqa: E402
from picchain.materials import MaterialLibrary             # noqa: E402
from picchain.mmi_eme import cross_section_eps             # noqa: E402
from picchain.solvers.fdmode import solve_modes            # noqa: E402
from transition import CELLS, STACK, UPPER_UM, emit, graded, widths   # noqa: E402

MATERIALS = ROOT / "design-chain" / "pdk" / "LXT_LT_PRO" / "materials_lt_pro.yaml"


def main(argv: list[str]) -> int:
    key = argv[1] if len(argv) > 1 else "oband"
    c = CELLS[key]
    lam = c["lam"]
    gds = emit(c["cell"])
    n_modes = int(argv[2]) if len(argv) > 2 else 6

    lib = MaterialLibrary(MATERIALS) if MATERIALS.exists() else MaterialLibrary()
    stack = dict(STACK, n_film=float(lib["LiTaO3"].index(lam, "e")),
                 n_clad=float(lib["SiO2"].index(lam)))

    x = graded(3.5, 0.025, 8.0, 0.15)
    y = np.concatenate([np.arange(-4.0, -0.2, 0.12), np.arange(-0.2, 0.501, 0.010),
                        np.arange(0.51, 4.01, 0.12)])
    dA = np.outer(np.gradient(x), np.gradient(y))

    before = widths(gds, UPPER_UM - 1e-3)
    after = widths(gds, UPPER_UM + 1e-3)
    print(f"{key}: the plane at z = {UPPER_UM} um")
    print(f"  before  slab {before[0]:.4f} um, ridge {before[1]:.4f} um")
    print(f"  after   slab {after[0]:.4f} um, ridge {after[1]:.4f} um")

    sets = []
    for w_s, w_r in (before, after):
        h_r = STACK["etch_um"] if w_r > 0 else 0.0
        eps = cross_section_eps(x, y, [0.0], max(w_r, 1e-3),
                                dict(stack, slab_width_um=w_s, ridge_height_um=h_r))
        modes = solve_modes(x, y, eps, eps, lam, "TE", n_modes, None)
        sets.append(modes)

    n_clad = stack["n_clad"]
    for tag, modes in zip(("before", "after"), sets):
        guided = [m.n_eff for m in modes if m.n_eff > n_clad + 1e-4]
        print(f"  {tag:7} n_eff {[round(float(m.n_eff), 5) for m in modes[:4]]}, "
              f"{len(guided)} guided above the cladding at {n_clad:.5f}")

    a = eme.normalise(np.array([sets[0][0].field], dtype=float), dA)[0]
    B = eme.normalise(np.array([m.field for m in sets[1]], dtype=float), dA)

    amps = np.array([float(np.sum(a * b * dA)) for b in B])
    fund = float(amps[0])
    guided_mask = np.array([m.n_eff > n_clad + 1e-4 for m in sets[1]])
    power_fund = fund**2
    power_guided = float(np.sum(amps[guided_mask] ** 2))

    n0, n1 = float(sets[0][0].n_eff), float(sets[1][0].n_eff)
    r = (n0 - n1) / (n0 + n1)

    print(f"\n  n_eff before, after                 {n0:.5f}, {n1:.5f}")
    print(f"  index step                          {n1 - n0:+.5f}")
    print(f"  fundamental to fundamental overlap  {fund:.5f}")
    print(f"  power into the fundamental          {power_fund:.5f}")
    print(f"  power into the guided set           {power_guided:.5f}")
    print(f"  loss at that one plane              "
          f"{-10 * np.log10(max(power_fund, 1e-15)):.4f} dB")
    print(f"  reflection implied by the index step {r * r:.1e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
