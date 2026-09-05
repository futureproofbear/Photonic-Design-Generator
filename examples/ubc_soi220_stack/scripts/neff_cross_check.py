"""The kit's own effective-index table against this chain's mode solver.

`ubcpdk` ships `simulation/find_neff_vs_width.csv`, four modes of a 220 nm
silicon strip against width. It is the one quantitative artifact in the kit that
can be reproduced without the foundry, and reproducing it tests two things at
once: whether this chain's solver agrees with an independent one, and whether
the table is converged.

The table's provenance is readable from the kit. It is MPB, through
`gplugins.modes.find_neff_vs_width`, at 1.55 um with the core index held at 3.47
and the cladding at 1.44, on a rectangular cross-section 220 nm thick, over a
2 by 2 um window, with no parity imposed so the four modes are ordered by
effective index and mix the polarisations.

**Those constants are used here rather than the chain's own materials.** A
cross-check compares solvers, and feeding one a dispersion and the other a
constant would compare material files instead. The chain's silicon is 3.4757 at
1550 nm against the 3.47 assumed there, which alone moves the effective index by
about four thousandths, and that is a separate matter from what this measures.

Chain rule 15 applies: the comparison is read only after the convergence guard
passes, so the mesh is refined until this solver stops moving and the residual
against MPB is set against the mesh error rather than quoted bare.

    python examples/ubc_soi220_stack/scripts/neff_cross_check.py [csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

print = __import__('functools').partial(print, flush=True)

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain.solvers.fdmode import solve_modes           # noqa: E402

#: exactly what the kit's table was made with
LAM_UM = 1.550
N_CORE, N_CLAD = 3.47, 1.44
THICK_UM = 0.220
WINDOW_UM = 2.0            # sy and sz of the MPB cell

DEFAULT_CSV = (ROOT / "design-chain" / ".venv-ubcpdk" / "Lib" / "site-packages"
               / "ubcpdk" / "simulation" / "find_neff_vs_width.csv")


def grid(width_um: float, cell_um: float):
    """A mesh over MPB's window whose nodes fall on the dielectric interfaces.

    A uniform mesh laid across a high-contrast interface staircases it: the
    discretised core is whichever whole number of cells is nearest, so refining
    the mesh moves the boundary as well as the sampling and the answer wanders
    instead of converging. On this 3.47 against 1.44 strip a uniform mesh moved
    the fundamental by 7e-3 between 10 and 5 nm cells and reversed direction,
    which is a guard failure and not a solver that is nearly right.

    Each region is meshed separately here, so the core edges at plus and minus
    half the width and the film faces at 0 and 220 nm are grid lines at every
    refinement and only the sampling changes.
    """
    half_w = width_um / 2
    half = WINDOW_UM / 2

    def span(a, b, cell):
        n = max(2, int(round(abs(b - a) / cell)))
        return np.linspace(a, b, n + 1)

    x = np.unique(np.concatenate([
        span(-half, -half_w, cell_um), span(-half_w, half_w, cell_um),
        span(half_w, half, cell_um)]))
    y0, y1 = -half + THICK_UM / 2, half + THICK_UM / 2
    y = np.unique(np.concatenate([
        span(y0, 0.0, cell_um), span(0.0, THICK_UM, cell_um),
        span(THICK_UM, y1, cell_um)]))
    return x, y


def eps_of(x, y, width_um):
    eps = np.full((len(x), len(y)), N_CLAD**2, dtype=float)
    core = (np.abs(x)[:, None] <= width_um / 2) & \
           ((y >= 0.0) & (y <= THICK_UM))[None, :]
    eps[core] = N_CORE**2
    return eps


def solve(width_um: float, cell_um: float, pol: str, n: int = 3):
    x, y = grid(width_um, cell_um)
    eps = eps_of(x, y, width_um)
    modes = solve_modes(x, y, eps, eps, LAM_UM, pol, n, None)
    return [float(m.n_eff) for m in modes]


def guided_set(width_um: float, cell_um: float, n: int = 4) -> list[float]:
    """Every guided mode of either polarisation, ordered by effective index.

    MPB was run with no parity imposed, so its four columns are ordered by
    effective index and mix the polarisations. Matching column two against this
    solver's fundamental magnetic mode is therefore right only while that mode
    is the second of the structure, and above about 0.65 um the second electric
    mode overtakes it. The comparison is made on the ordered union instead.
    """
    both = solve(width_um, cell_um, "TE", n) + solve(width_um, cell_um, "TM", n)
    return sorted((v for v in both if v > N_CLAD + 1e-4), reverse=True)[:n]


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    if not path.exists():
        print(f"the kit's table is not at {path}")
        return 1
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    table = [(float(r["width"]), [float(r[k]) for k in ("1", "2", "3", "4")])
             for r in rows]

    print(f"the kit's table: {len(table)} widths from {table[0][0]:.3f} to "
          f"{table[-1][0]:.3f} um, four modes each")
    print(f"reproduced at {LAM_UM} um with core {N_CORE}, cladding {N_CLAD}, "
          f"thickness {THICK_UM} um, window {WINDOW_UM} um\n")

    # ---- the convergence guard, at the width the kit draws its guides -------
    print("the guard: this solver against its own mesh, at 0.5 um")
    ladder = (0.040, 0.020, 0.010, 0.005)
    prev, moves = None, []
    for cell in ladder:
        te = solve(0.5, cell, "TE", 1)[0]
        move = None if prev is None else abs(te - prev)
        moves.append(move)
        tail = "" if move is None else f"  moved {move:.2e}"
        print(f"  cell {cell * 1000:6.2f} nm   TE0 {te:.6f}{tail}")
        prev = te
    mesh_error = moves[-1]
    fine = ladder[-1]
    print(f"  the last halving moved the answer by {mesh_error:.2e}, and that is "
          f"the mesh error the disagreement below is set against")
    if mesh_error > 3e-3:
        print("  THE GUARD DOES NOT PASS. Nothing below is to be read as a "
              "statement about the other solver.")
    print()

    # ---- the comparison ----------------------------------------------------
    print("the ordered guided set, the kit's column against this solver's")
    print(f"{'width':>7} {'mode 1':>19} {'mode 2':>19} {'mode 3':>19}")
    print(f"{'':7} {'kit':>8}{'this':>9}{'d':>7}  " * 1
          + f"{'kit':>8}{'this':>8}{'d':>7}  {'kit':>8}{'this':>8}{'d':>7}")
    worst = 0.0
    for w, theirs in table:
        mine = guided_set(w, fine, 4)
        cells = []
        for k in range(3):
            t = theirs[k] if k < len(theirs) else float("nan")
            m = mine[k] if k < len(mine) else float("nan")
            if t > N_CLAD + 1e-4 and m == m:
                d = m - t
                worst = max(worst, abs(d))
                cells.append(f"{t:8.4f}{m:9.4f}{d:+7.3f}")
            else:
                cells.append(f"{t:8.4f}{'--':>9}{'':>7}")
        print(f"{w:7.4f} " + "  ".join(cells))

    print(f"\nthe worst disagreement over the guided modes is {worst:.4f} in "
          f"effective index")
    if mesh_error and mesh_error > 0:
        print(f"this solver's mesh error is {mesh_error:.2e}, so the disagreement "
              f"is {worst / mesh_error:.1f} times it")
        if worst < 3 * mesh_error:
            print("which does not clear the guard, so the two solvers are not "
                  "distinguished by this comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
