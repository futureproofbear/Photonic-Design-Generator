"""How much of the effective index follows the film's own, and the cladding's.

A heater warms the film and the cladding together, and the effective index moves
by the sensitivity-weighted sum of the two thermo-optic coefficients. The weight
required is dn_eff/dn for each material. The film confinement has been used as a
proxy for the first, and it is the fraction of the *power* in the film rather
than the fraction of the index that follows it, which are different numbers.

Each index is perturbed here and the mode re-solved, which is the measurement
the configuration of the phase trimmer asks for and records the need of. Nothing
is fitted: the derivative is taken by a central difference on the same solver the
rest of the chain uses.

    python examples/ltoi300_mzm/scripts/index_sensitivity.py <design.yaml> [...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain.config import Design                      # noqa: E402
from picchain.geometry import build_grid                # noqa: E402
from picchain.materials import MaterialLibrary          # noqa: E402
from picchain.solvers.fdmode import solve_modes         # noqa: E402
from picchain.stages.s01_mode import _eps_maps          # noqa: E402
from picchain.stages.s08_taper import _cross_section    # noqa: E402

DELTA = 2.0e-3          # index perturbation, central difference


def sensitivity(design: Design, lib: MaterialLibrary) -> dict:
    p, m, w = design.platform, design.mesh, design.waveguide
    lam = w.wavelength_um
    xs = _cross_section(design, w.top_width_um, "sensitivity")
    grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, eyy = _eps_maps(xs, grid, lib, lam, p.cut, p.use_index_override, m.subsample)

    n_film = float(lib[p.film_material].index(lam, "e", p.use_index_override))
    n_clad = float(lib[p.clad_material].index(lam, use_override=p.use_index_override))

    def n_eff_of(exx_, eyy_) -> float:
        modes = solve_modes(grid.x, grid.y, exx_, eyy_, lam,
                            m.polarisation, 1, None)
        if not modes:
            raise RuntimeError("the perturbed cross-section guides no mode")
        return float(modes[0].n_eff)

    base = n_eff_of(exx, eyy)

    #: the film and the cladding are identified by the index each carries, the
    #: permittivity map being built from those two materials and the box
    out: dict[str, float] = {"n_eff": base, "n_film": n_film, "n_clad": n_clad}
    for name, n0 in (("film", n_film), ("cladding", n_clad)):
        mask = np.isclose(np.sqrt(np.abs(exx)), n0, rtol=2e-3)
        if not mask.any():
            out[f"sensitivity_{name}"] = float("nan")
            continue
        up_xx, up_yy = np.array(exx), np.array(eyy)
        dn_xx, dn_yy = np.array(exx), np.array(eyy)
        up_xx[mask] = (n0 + DELTA) ** 2
        up_yy[mask] = (n0 + DELTA) ** 2
        dn_xx[mask] = (n0 - DELTA) ** 2
        dn_yy[mask] = (n0 - DELTA) ** 2
        out[f"sensitivity_{name}"] = (n_eff_of(up_xx, up_yy)
                                      - n_eff_of(dn_xx, dn_yy)) / (2 * DELTA)
        out[f"cells_{name}"] = int(mask.sum())
    return out


def main(argv: list[str]) -> int:
    for path in argv[1:]:
        d = Design.load(path)
        lib_path = d.materials_path()
        lib = MaterialLibrary(lib_path) if lib_path else MaterialLibrary()
        r = sensitivity(d, lib)
        s_film = r.get("sensitivity_film", float("nan"))
        s_clad = r.get("sensitivity_cladding", float("nan"))
        print(f"\n{Path(path).name}  width {d.waveguide.top_width_um} um  "
              f"lambda {d.waveguide.wavelength_um} um")
        print(f"  n_eff {r['n_eff']:.6f}   n_film {r['n_film']:.5f}   "
              f"n_clad {r['n_clad']:.5f}")
        print(f"  dn_eff/dn_film      {s_film:.5f}")
        print(f"  dn_eff/dn_cladding  {s_clad:.5f}")
        print(f"  the two together    {s_film + s_clad:.5f}   "
              "(unity where the mode sees nothing else)")
        # what it means for the heater the cells draw
        for dT, L in ((40.0, 700.0),):
            dn_dT_film, dn_dT_clad = 3.0e-5, 1.0e-5
            dn = (s_film * dn_dT_film + s_clad * dn_dT_clad) * dT
            phase = 2 * np.pi * dn * L / d.waveguide.wavelength_um
            print(f"  a {L:.0f} um heater at {dT:.0f} K, on the film alone: "
                  f"{2*np.pi*s_film*dn_dT_film*dT*L/d.waveguide.wavelength_um/np.pi:.3f} pi")
            print(f"  the same with the cladding at 1e-5/K as well:        "
                  f"{phase/np.pi:.3f} pi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
