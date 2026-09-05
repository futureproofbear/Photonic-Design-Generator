"""What the two radio-frequency permittivities predict, as a function of length.

At the 5 mm the ltoi300 cell draws, both candidate permittivities put the 3 dB
electro-optic bandwidth above the figure the vendor page claims, so that claim
does not distinguish them. The two differ in the microwave index, and a
velocity mismatch is felt in proportion to the electrode run. Sweeping the
length therefore shows where the choice matters and by how much.

Nothing is re-solved. The microwave index, the characteristic impedance and the
conductor geometry are read from the runs, and the response is evaluated with
the same `picchain.rf` functions the electro-optic stage itself calls, so the
curve passes through the figure each run reported.

    python examples/ltoi300_modulator/scripts/bandwidth_vs_length.py \
        <run_dir_A> <run_dir_B> [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "design-chain" / "src"))
from picchain import rf  # noqa: E402


def load(run_dir: Path) -> dict:
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    m = m.get("metrics", m)
    d = json.loads((run_dir / "design.resolved.json").read_text(encoding="utf-8")) \
        if (run_dir / "design.resolved.json").exists() else {}
    eo, tw = m["eo"], m["eo"]["travelling_wave"]
    return {
        "run": run_dir.name,
        "name": (d.get("meta") or {}).get("name", run_dir.name),
        "n_m": tw["microwave_index"],
        "n_g": tw["optical_group_index"],
        "Z0": tw["characteristic_impedance_ohm"],
        "width_m": eo["electrode_width_um"] * 1e-6,
        "thickness_m": (d.get("electrodes") or {}).get("thickness_um", 0.9) * 1e-6,
        "sigma": (d.get("electrodes") or {}).get("conductivity_S_per_m", 4.1e7),
        "n_cond": tw.get("conductors_carrying_the_return", 2.0),
        "L_um": eo["electrode_length_um"],
        "f3dB_reported": tw["electro_optic_3dB_GHz"],
    }


def curve(p: dict, lengths_mm: np.ndarray) -> np.ndarray:
    def alpha(f_Hz: float) -> float:
        R = rf.skin_resistance_per_m(f_Hz, p["sigma"], p["width_m"],
                                     p["thickness_m"], n_conductors=p["n_cond"])
        return R / (2.0 * p["Z0"])
    return np.array([rf.bandwidth(L * 1e-3, alpha, p["n_m"], p["n_g"]) / 1e9
                     for L in lengths_mm])


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    here = Path(__file__).resolve().parent.parent
    a, b = load(Path(args[0])), load(Path(args[1]))
    out = Path(args[2]) if len(args) > 2 else here / "figures" / "bandwidth_vs_length.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    # The search in `picchain.rf.bandwidth` walks up from 100 MHz and returns
    # that floor where the response is already below the level there, so a
    # length long enough to put the 3 dB point under 100 MHz reports 0.1 GHz
    # rather than a bandwidth. Such points are dropped rather than drawn.
    lengths = np.geomspace(1.0, 30.0, 60)
    fa, fb = curve(a, lengths), curve(b, lengths)
    ok = (fa > 0.11) & (fb > 0.11)
    lengths, fa, fb = lengths[ok], fa[ok], fb[ok]

    for p, f in ((a, fa), (b, fb)):
        at = float(np.interp(p["L_um"] * 1e-3, lengths, f))
        print(f"{p['name']}: n_m {p['n_m']:.4f}, n_g {p['n_g']:.4f}, "
              f"mismatch {p['n_m'] - p['n_g']:+.4f}, Z0 {p['Z0']:.2f} ohm")
        print(f"   at {p['L_um'] * 1e-3:.2f} mm this curve gives {at:.1f} GHz "
              f"against the {p['f3dB_reported']:.1f} GHz the run reported")
        over = lengths[f >= 110.0]
        if len(over):
            print(f"   110 GHz is held out to {over.max():.2f} mm")
        else:
            print("   110 GHz is not reached at any length swept")

    print("\nlength    " + a["name"] + "   " + b["name"] + "   ratio")
    for L in (2.0, 5.0, 10.0, 18.0, 25.0):
        ga = float(np.interp(L, lengths, fa))
        gb = float(np.interp(L, lengths, fb))
        print(f"{L:6.1f} mm  {ga:9.1f} GHz  {gb:9.1f} GHz  {gb / ga:6.3f}")

    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.loglog(lengths, fa, lw=1.8, label=f"{a['name']}  ($n_m$ {a['n_m']:.4f})")
    ax.loglog(lengths, fb, lw=1.8, ls="--", label=f"{b['name']}  ($n_m$ {b['n_m']:.4f})")
    ax.axhline(110.0, color="0.4", lw=1.0, ls=":")
    ax.text(1.1, 116.0, "the 110 GHz the vendor page claims", fontsize=8, color="0.3")
    ax.axvline(a["L_um"] * 1e-3, color="0.6", lw=1.0)
    ax.text(a["L_um"] * 1e-3 * 1.05, ax.get_ylim()[0] * 1.4,
            f"the {a['L_um'] * 1e-3:.0f} mm the cell draws", fontsize=8, color="0.3")
    ax.set_xlabel("electrode length (mm)")
    ax.set_ylabel("3 dB electro-optic bandwidth (GHz)")
    ax.set_title("Where the choice of radio-frequency permittivity is felt")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    fig.savefig(out, dpi=150)
    print(f"\n{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
