"""The kit's effective-index table against a full-vectorial solve.

`ubcpdk` ships `simulation/find_neff_vs_width.csv`, four modes of a 220 nm
silicon strip against width, made with MPB at 1.55 um with the core index held
at 3.47 and the cladding at 1.44 over a 2 by 2 um window with no parity imposed.
It is the one quantitative artifact in the kit reproducible without the foundry.

The companion script attempts the same comparison with the chain's default
finite-difference solver and fails its own convergence guard, that solver being
semi-vectorial and this cross-section carrying an index contrast of 2.03. This
uses the finite-element path instead, which is full-vectorial on a conforming
triangulation and does not staircase the interface.

The two are set against each other in the study, and the difference between them
is the point: a semi-vectorial approximation is a statement about how weakly the
polarisations couple, and on silicon they do not.

    python examples/ubc_soi220_stack/scripts/neff_cross_check_fem.py [csv]
"""

from __future__ import annotations

import csv
import functools
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np

print = functools.partial(print, flush=True)

ROOT = Path(__file__).resolve().parents[3]

#: exactly what the kit's table was made with
LAM_UM = 1.550
N_CORE, N_CLAD = 3.47, 1.44
THICK_UM = 0.220
WINDOW_UM = 2.0

DEFAULT_CSV = (ROOT / "design-chain" / ".venv-ubcpdk" / "Lib" / "site-packages"
               / "ubcpdk" / "simulation" / "find_neff_vs_width.csv")


def solve(width_um: float, resolution_um: float, num_modes: int = 4) -> list[float]:
    """Every mode of the strip, ordered by effective index."""
    from femwell.maxwell.waveguide import compute_modes
    from femwell.mesh import mesh_from_OrderedDict
    from shapely.geometry import box
    from skfem import Basis, ElementTriP0
    from skfem.io.meshio import from_meshio

    half = WINDOW_UM / 2
    core = box(-width_um / 2, 0.0, width_um / 2, THICK_UM)
    clad = box(-half, -half + THICK_UM / 2, half, half + THICK_UM / 2)
    mesh = from_meshio(mesh_from_OrderedDict(
        OrderedDict(core=core, clad=clad),
        {"core": {"resolution": resolution_um, "distance": 0.5}},
        default_resolution_max=0.2))
    basis = Basis(mesh, ElementTriP0())
    eps = basis.zeros(dtype=complex)
    eps[basis.get_dofs(elements="clad")] = N_CLAD**2
    eps[basis.get_dofs(elements="core")] = N_CORE**2
    modes = compute_modes(basis, eps, wavelength=LAM_UM,
                          num_modes=num_modes, order=2)
    return sorted((float(np.real(m.n_eff)) for m in modes), reverse=True)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    if not path.exists():
        print(f"the kit's table is not at {path}")
        return 1
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    table = [(float(r["width"]), [float(r[k]) for k in ("1", "2", "3", "4")])
             for r in rows]

    print(f"the kit's table: {len(table)} widths from {table[0][0]:.3f} to "
          f"{table[-1][0]:.3f} um")
    print(f"reproduced at {LAM_UM} um, core {N_CORE}, cladding {N_CLAD}, "
          f"thickness {THICK_UM} um, window {WINDOW_UM} um\n")

    print("the guard: this solver against its own mesh, at 0.5 um")
    prev, move = None, None
    for res in (0.050, 0.025, 0.0125):
        n = solve(0.5, res, 2)[0]
        move = None if prev is None else abs(n - prev)
        tail = "" if move is None else f"   moved {move:.2e}"
        print(f"  resolution {res * 1000:6.1f} nm   n_eff {n:.6f}{tail}")
        prev = n
    print(f"  the last halving moved the answer by {move:.2e}\n")

    fine = 0.025
    print("the ordered guided set, the kit against this solver")
    print(f"{'width':>7}  {'kit m1':>8}{'fem':>9}{'d':>8}  "
          f"{'kit m2':>8}{'fem':>9}{'d':>8}  {'kit m3':>8}{'fem':>9}{'d':>8}")
    worst, worst_at = 0.0, 0.0
    for w, theirs in table:
        mine = [v for v in solve(w, fine, 4) if v > N_CLAD + 1e-4]
        cells = []
        for k in range(3):
            t = theirs[k]
            m = mine[k] if k < len(mine) else None
            if t > N_CLAD + 1e-4 and m is not None:
                d = m - t
                if abs(d) > worst:
                    worst, worst_at = abs(d), w
                cells.append(f"{t:8.4f}{m:9.4f}{d:+8.4f}")
            else:
                cells.append(f"{t:8.4f}{'--':>9}{'':>8}")
        print(f"{w:7.4f}  " + "  ".join(cells))

    print(f"\nthe worst disagreement over the guided modes is {worst:.4f}, "
          f"at {worst_at:.4f} um")
    print(f"this solver's mesh error is {move:.2e}, so the disagreement is "
          f"{worst / move:.0f} times it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
