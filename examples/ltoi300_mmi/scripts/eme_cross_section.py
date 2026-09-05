"""The splitter solved in the full cross-section, and its length swept for free.

The planar reduction images seven to ten per cent beyond where the kit draws,
because collapsing the vertical dimension changes the spacing of the modal
propagation constants and that spacing fixes the imaging length. Keeping the
vertical dimension removes that error. Keeping it in an eigenmode expansion also
removes the other one: within a uniform section the phase is one exponential, so
the length of the multimode section carries no accumulated error and may be
swept at the cost of a cascade rather than a solve.

Every section is solved once. The sweep then re-cascades.

    python examples/ltoi300_mmi/scripts/eme_cross_section.py <cell>

with <cell> one of mmi1x2_oband, mmi2x2_oband, mmi1x2_cband, mmi2x2_cband.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain import mmi_eme                            # noqa: E402
from picchain.materials import MaterialLibrary          # noqa: E402

MATERIALS = ROOT / "design-chain" / "pdk" / "LXT_LT_PRO" / "materials_lt_pro.yaml"

#: geometry read from the builders of the kit, and nothing chosen here
CELLS = {
    "mmi1x2_oband": dict(width_um=0.7, port_width_um=1.7, mmi_width_um=4.50,
                         mmi_length_um=15.8, port_separation_um=2.45,
                         ports_in=1, wavelength_um=1.31),
    "mmi2x2_oband": dict(width_um=0.7, port_width_um=1.75, mmi_width_um=5.65,
                         mmi_length_um=97.5, port_separation_um=3.9,
                         ports_in=2, wavelength_um=1.31),
    "mmi1x2_cband": dict(width_um=0.9, port_width_um=1.95, mmi_width_um=4.50,
                         mmi_length_um=13.5, port_separation_um=2.55,
                         ports_in=1, wavelength_um=1.55),
    "mmi2x2_cband": dict(width_um=0.9, port_width_um=1.5, mmi_width_um=5.15,
                         mmi_length_um=67.5, port_separation_um=3.65,
                         ports_in=2, wavelength_um=1.55),
}

STACK = dict(film_um=0.300, etch_um=0.180, sidewall_deg=70.0)


def graded(half_fine, d_fine, half_total, d_coarse):
    fine = np.arange(0.0, half_fine + d_fine / 2, d_fine)
    coarse = np.arange(half_fine + d_coarse, half_total + d_coarse / 2, d_coarse)
    half = np.concatenate([fine, coarse])
    return np.concatenate([-half[:0:-1], half])


def build(cell: str) -> dict:
    g = dict(CELLS[cell])
    lam = g["wavelength_um"]
    lib = MaterialLibrary(MATERIALS) if MATERIALS.exists() else MaterialLibrary()
    stack = dict(STACK,
                 n_film=float(lib["LiTaO3"].index(lam, "e")),
                 n_clad=float(lib["SiO2"].index(lam)))

    half = max(g["mmi_width_um"], g["port_separation_um"] + 2 * g["width_um"]) / 2 + 2.0
    x = graded(half, 0.025, half + 3.0, 0.10)
    # the vertical axis is not symmetric: oxide below, film, oxide above
    y_fine = np.arange(-0.15, 0.451, 0.010)
    y_low = np.arange(-1.25, -0.15, 0.060)
    y_high = np.arange(0.46, 1.26, 0.060)
    y = np.concatenate([y_low, y_fine, y_high])

    g.update(x=x, y=y, stack=stack, taper_length_um=25.0, lead_um=2.0,
             taper_slices=int(g.get("taper_slices", 6)), num_modes=int(__import__('os').environ.get('EME_MODES', 12)),
             polarisation="TE")
    return g


def main(argv: list[str]) -> int:
    cell = argv[1] if len(argv) > 1 else "mmi1x2_oband"
    job = build(cell)
    print(f"{cell}: grid {len(job['x'])} by {len(job['y'])}, "
          f"{len(job['x']) * len(job['y'])} points, {job['num_modes']} modes per section")

    st = mmi_eme.stack_3d(job)
    print(f"  sections solved: {len(st['n_effs'])}, "
          f"modes {min(len(v) for v in st['n_effs'])} to "
          f"{max(len(v) for v in st['n_effs'])}")

    drawn = CELLS[cell]["mmi_length_um"]
    r = mmi_eme.solve_from_stack(st, drawn)
    print(f"\n  as drawn, L = {drawn} um")
    print(f"    transmission {r['transmission']:.4f}   excess "
          f"{r['excess_loss_dB']:.3f} dB   imbalance {r['imbalance_dB']:+.3f} dB"
          f"   reflection {r['reflection']:.2e}")

    print("\n  length swept, the sections solved once")
    best = (0.0, None)
    for L in np.round(np.linspace(drawn * 0.85, drawn * 1.20, 15), 2):
        rr = mmi_eme.solve_from_stack(st, float(L))
        flag = "  <- as drawn" if abs(L - drawn) < 1e-6 else ""
        print(f"    L {L:7.2f}  T {rr['transmission']:.4f}  "
              f"imbalance {rr['imbalance_dB']:+7.3f} dB{flag}")
        if rr["transmission"] > best[0]:
            best = (rr["transmission"], float(L))
    print(f"\n  best at L = {best[1]} um, T = {best[0]:.4f}, "
          f"being {100 * (best[1] / drawn - 1):+.1f} % from the drawn length")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
