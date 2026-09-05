"""The beat length of a multimode section, in the full cross-section and in the plane.

What a multimode interference device does is fixed by the spacing of the
propagation constants of its guided modes. The self-imaging length is
proportional to the beat length of the two lowest,

    L_pi = pi / (beta_0 - beta_1) = lambda / (2 (n_0 - n_1)),

and every image length of the device is a fixed multiple of it. A model that
gets that spacing wrong images at the wrong length, whatever else it does
correctly.

The companion study established that the effective-index reduction wants a
section between seven and ten per cent longer than the kit draws, on three cells
of two port counts and two bands. This computes the beat length twice for each
section: once in the reduction, from the modes of the lateral index profile, and
once in the full cross-section, from the modes of the ridge on its slab. The
ratio of the two predicts where the reduction's optimum should sit relative to
the true one, and that prediction is set against the optima already measured.

Nothing here is fitted. The two solves use the same material file, the same
wavelength and the same stack.

    python examples/ltoi300_mmi/scripts/beat_length_3d.py
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
from picchain.mmi_eme import lateral_profile            # noqa: E402
from picchain.solvers.fdmode import (                   # noqa: E402
    solve_lateral_modes, solve_modes)
from picchain.stages.s01_mode import _eps_maps          # noqa: E402
from picchain.stages.s08_taper import _cross_section    # noqa: E402

#: the four multimode sections of the kit, with the optimum each was measured to
#: want in the reduction and the length the kit draws
CELLS = (
    ("mmi1x2_oband", "examples/ltoi300_ring/design_oband_ltpro.yaml", 4.50, 15.8, 17.0),
    ("mmi2x2_oband", "examples/ltoi300_ring/design_oband_ltpro.yaml", 5.65, 97.5, 104.0),
    ("mmi1x2_cband", "examples/ltoi300_ring/design_cband_ltpro.yaml", 4.50, 13.5, None),
    ("mmi2x2_cband", "examples/ltoi300_ring/design_cband_ltpro.yaml", 5.15, 67.5, 74.0),
)


def beat_length_cross_section(design: Design, lib: MaterialLibrary,
                              width_um: float) -> tuple[float, float, float]:
    """The two lowest modes of the ridge as it is actually drawn."""
    p, m, w = design.platform, design.mesh, design.waveguide
    lam = w.wavelength_um
    xs = _cross_section(design, width_um, "mmi_section")
    grid = build_grid(xs, m.d_fine_um, m.d_coarse_um, m.fine_margin_um)
    exx, eyy = _eps_maps(xs, grid, lib, lam, p.cut, p.use_index_override, m.subsample)
    modes = solve_modes(grid.x, grid.y, exx, eyy, lam, m.polarisation, 3, None)
    if len(modes) < 2:
        raise RuntimeError(f"the {width_um} um section guides {len(modes)} modes")
    n0, n1 = float(modes[0].n_eff), float(modes[1].n_eff)
    return n0, n1, lam / (2.0 * (n0 - n1))


def beat_length_reduction(design: Design, lib: MaterialLibrary,
                          width_um: float) -> tuple[float, float, float]:
    """The two lowest modes of the lateral profile the planar model carries."""
    p, m, w = design.platform, design.mesh, design.waveguide
    lam = w.wavelength_um
    n_film = float(lib[p.film_material].index(lam, "e", p.use_index_override))

    def column(thickness_um: float) -> float:
        y = np.linspace(-3.0, 3.0, 24001)
        n_clad = float(lib[p.clad_material].index(lam, use_override=p.use_index_override))
        eps = np.full_like(y, n_clad ** 2)
        eps[(y >= 0) & (y <= thickness_um)] = n_film ** 2
        from picchain.solvers.fdmode import solve_slab
        got = solve_slab(y, eps, lam, 2)
        if not got:
            raise RuntimeError("the column guides no mode")
        return float(got[0])

    n_core = column(p.film_thickness_um)
    n_bg = column(p.film_thickness_um - p.etch_depth_um)
    x = np.linspace(-2.5 * width_um, 2.5 * width_um, 4001)
    prof = lateral_profile(x, [0.0], width_um, n_core, n_bg)
    ne, _ = solve_lateral_modes(x, prof, lam, 3)
    if len(ne) < 2:
        raise RuntimeError(f"the reduced {width_um} um section guides {len(ne)} modes")
    n0, n1 = float(ne[0]), float(ne[1])
    return n0, n1, lam / (2.0 * (n0 - n1))


def main() -> int:
    cache: dict[str, tuple[Design, MaterialLibrary]] = {}
    print(f"{'cell':>14} {'W':>6} {'L_pi plane':>11} {'L_pi section':>13} "
          f"{'ratio':>7} {'drawn':>7} {'plane opt':>10} {'predicted':>10}")
    for name, design_path, width, drawn, plane_opt in CELLS:
        if design_path not in cache:
            d = Design.load(design_path)
            lp = d.materials_path()
            cache[design_path] = (d, MaterialLibrary(lp) if lp else MaterialLibrary())
        d, lib = cache[design_path]
        _, _, lpi_plane = beat_length_reduction(d, lib, width)
        _, _, lpi_xs = beat_length_cross_section(d, lib, width)
        ratio = lpi_xs / lpi_plane
        pred = plane_opt * ratio if plane_opt else float("nan")
        print(f"{name:>14} {width:6.2f} {lpi_plane:11.3f} {lpi_xs:13.3f} "
              f"{ratio:7.4f} {drawn:7.1f} "
              f"{plane_opt if plane_opt else float('nan'):10.1f} {pred:10.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
