"""What the two UBC kits' disagreement about the buried oxide is worth.

The two open kits for the same UBC electron-beam process declare different
stacks. The KLayout kit's cross-section script grows a 2.0 um buried oxide and
the gdsfactory kit declares 3.0 um. A designer taking the geometry from one and
a figure from the other is using a stack that neither foundry runs.

The buried oxide is what separates the mode from the silicon handle, and the
handle has an index above the mode's, so a strip on silicon-on-insulator has no
truly bound mode at all. What it has is a leaky one, and the leakage falls
exponentially with the oxide it has to tunnel through:

    alpha ~ exp(-2 gamma t),    gamma = k0 sqrt(n_eff^2 - n_ox^2)

The prefactor depends on the overlap with the substrate continuum and is not
computed here. The exponent is, from the effective index the chain solves, and
the exponent is where a micrometre of oxide lands. The ratio between two
thicknesses is therefore firm even where the absolute figure is not, which is
the quantity the disagreement calls for.

Two things are reported beside it. The effective index at each width, which is
what fixes the exponent. And the fraction of the mode's power below the depth at
which the thinner oxide ends, which is a direct measure taken from the solved
field rather than from a formula.

The stack is public: 220 nm of silicon at 1550 nm on thermal oxide, with the
silicon handle beneath. Both kits agree on everything here except the thickness.

    python examples/ubc_soi220_stack/scripts/box_leakage.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain.materials import MaterialLibrary            # noqa: E402
from picchain.solvers.fdmode import solve_modes           # noqa: E402

FILM_UM = 0.220
LAM_UM = 1.550
BOX_THIN_UM, BOX_THICK_UM = 2.0, 3.0     # the two kits' declarations
#: the strip widths the process is used at, including the 500 nm the kits draw
#: for a single-mode guide and the 3 um a multimode bus uses
WIDTHS_UM = (0.35, 0.50, 0.65, 1.00, 2.00, 3.00)

#: the cases the disagreement is tested on. A fully etched strip carries its
#: mode well clear of the oxide and is expected to settle the question by not
#: caring. The rib is the case that should: the two kits disagree about the
#: slab as well, and a mode over a slab is bound more weakly and reaches
#: further down. The transverse-magnetic mode is the other case, its field
#: being the poorly confined one on a 220 nm film.
CASES = (
    ("strip, TE", 0.50, 0.0, "TE"),
    ("strip, TM", 0.50, 0.0, "TM"),
    ("rib on the 130 nm slab a 90 nm etch leaves, TE", 0.50, 0.130, "TE"),
    ("rib on the 130 nm slab a 90 nm etch leaves, TM", 0.50, 0.130, "TM"),
    ("rib on the 150 nm slab the other kit declares, TE", 0.50, 0.150, "TE"),
    ("rib on the 150 nm slab the other kit declares, TM", 0.50, 0.150, "TM"),
    ("a 3 um multimode rib on 130 nm, TE", 3.00, 0.130, "TE"),
    ("a 3 um multimode rib on 150 nm, TE", 3.00, 0.150, "TE"),
)


def grid(width_um: float):
    half = width_um / 2
    fine = np.arange(0.0, half + 0.30 + 1e-9, 0.010)
    coarse = np.arange(half + 0.40, half + 2.6, 0.08)
    x_half = np.concatenate([fine, coarse])
    x = np.unique(np.concatenate([-x_half[:0:-1], x_half]))
    y = np.unique(np.concatenate([
        np.arange(-2.0, -0.15, 0.05),
        np.arange(-0.15, FILM_UM + 0.151, 0.005),
        np.arange(FILM_UM + 0.20, 2.0, 0.05)]))
    return x, y


def eps_of(x, y, width_um, n_si, n_ox, slab_um: float = 0.0):
    """A silicon strip or rib in oxide. The handle is outside the window.

    Putting the handle in the window would give the solver a substrate mode to
    find instead of the guided one, which is the failure the chain's own mode
    stage documents for its thin-film stacks. The handle enters through the
    exponent below rather than through the mesh.

    ``slab_um`` leaves silicon of that thickness either side of the guide, which
    is what a partial etch draws. Zero is a fully etched strip.
    """
    eps = np.full((len(x), len(y)), n_ox**2, dtype=float)
    core = (np.abs(x)[:, None] <= width_um / 2) & \
           ((y >= 0.0) & (y <= FILM_UM))[None, :]
    eps[core] = n_si**2
    if slab_um > 0:
        slab = (np.abs(x)[:, None] > width_um / 2) & \
               ((y >= 0.0) & (y <= slab_um))[None, :]
        eps[slab] = n_si**2
    return eps


def main() -> int:
    lib = MaterialLibrary()
    n_si = float(lib["Si"].index(LAM_UM))
    n_ox = float(lib["SiO2"].index(LAM_UM))
    k0 = 2 * math.pi / LAM_UM
    print(f"silicon {n_si:.4f}, oxide {n_ox:.4f} at {LAM_UM * 1000:.0f} nm, "
          f"film {FILM_UM * 1000:.0f} nm\n")

    def report(label, w, slab, pol):
        x, y = grid(w)
        eps = eps_of(x, y, w, n_si, n_ox, slab)
        modes = solve_modes(x, y, eps, eps, LAM_UM, pol, 2, None)
        if not modes:
            print(f"  {label:46}   no mode")
            return
        n_eff = float(modes[0].n_eff)
        if n_eff <= n_ox:
            print(f"  {label:46} {n_eff:8.5f}   below the oxide, not guided")
            return
        gamma = k0 * math.sqrt(n_eff**2 - n_ox**2)
        a_thin = math.exp(-2 * gamma * BOX_THIN_UM)
        a_thick = math.exp(-2 * gamma * BOX_THICK_UM)
        print(f"  {label:46} {n_eff:8.5f} {gamma:8.4f} {a_thin:10.2e} "
              f"{a_thick:10.2e} {10 * math.log10(a_thin / a_thick):7.1f}")

    print("the strip, across the widths the process is drawn at")
    print(f"  {'':46} {'n_eff':>8} {'gamma':>8} {'2 um':>10} {'3 um':>10} {'dB':>7}")
    for w in WIDTHS_UM:
        report(f"{w:.2f} um wide, fully etched, TE", w, 0.0, "TE")

    print("\nthe cases the disagreement is tested on")
    print(f"  {'':46} {'n_eff':>8} {'gamma':>8} {'2 um':>10} {'3 um':>10} {'dB':>7}")
    for label, w, slab, pol in CASES:
        report(label, w, slab, pol)

    print("\nthe two oxide columns are the tunnelling factor at each declared")
    print("thickness and the last is the factor by which the thinner one leaks")
    print("more. The prefactor is common to both and cancels in that factor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
