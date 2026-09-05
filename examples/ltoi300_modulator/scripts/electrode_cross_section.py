"""The coplanar line the PDK draws, the field it sets up, and where the arms sit.

The electro-optic stage writes the electrostatic solution on its own mesh into
`eo.npz`, over the whole radio-frequency window rather than over the optical
one. That window is what shows the device: a signal conductor between two
grounds, a guide on the centre line of each gap, and the field in the film that
the overlap integral weights.

    python examples/ltoi300_modulator/scripts/electrode_cross_section.py \
        <run_dir> <out.png>

With no run directory the most recent run beneath `runs/` is taken.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    args = sys.argv[1:]
    if args and Path(args[0]).is_dir():
        run_dir, args = Path(args[0]), args[1:]
    else:
        run_dir = sorted((here / "runs").glob("*/eo.npz"))[-1].parent
    out = Path(args[0]) if args else here / "figures" / "electrode_cross_section.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    d = np.load(run_dir / "eo.npz")
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    eo = m.get("metrics", m)["eo"]

    x, y, Ex = d["rf_x_um"], d["rf_y_um"], d["rf_Ex"]
    gap = eo["electrode_gap_um"]
    w = eo["electrode_width_um"]
    arm = w / 2 + gap / 2

    film = eo.get("film_thickness_um") or 0.300
    fig, ax = plt.subplots(2, 1, figsize=(9.6, 7.2), constrained_layout=True)

    # --- the line, across the whole gap-to-ground span ---------------------
    span = w / 2 + gap + 12.0
    keep_x = (x >= -span) & (x <= span)
    keep_y = (y >= -1.5) & (y <= 2.2)
    X, Y = x[keep_x], y[keep_y]
    F = Ex[np.ix_(keep_x, keep_y)]
    lim = float(np.percentile(np.abs(F), 99.0))
    im = ax[0].pcolormesh(X, Y, F.T, shading="auto", cmap="RdBu_r",
                          vmin=-lim, vmax=lim)
    for s in (-1.0, 1.0):
        ax[0].axvline(s * w / 2, color="k", lw=0.7, ls=":")
        ax[0].axvline(s * (w / 2 + gap), color="k", lw=0.7, ls=":")
        ax[0].axvline(s * arm, color="k", lw=1.3)
    ax[0].axhline(0.0, color="0.3", lw=0.7)
    ax[0].set_xlabel("x (um), zero on the signal conductor axis")
    ax[0].set_ylabel("y (um)")
    ax[0].set_title(
        f"RF $E_x$ (V/um) at {eo['test_voltage_V']:.0f} V, gap {gap:.1f} um, "
        f"signal {w:.0f} um; the arms sit {arm:.2f} um either side of the axis",
        fontsize=10)
    fig.colorbar(im, ax=ax[0])

    # --- the film under one arm, with the mode that samples it -------------
    ox, oy = d["x_um"], d["y_um"]
    inten = d["intensity"]
    keep = (oy >= -1.0) & (oy <= 1.4)
    G = d["Ex"][:, keep]
    hi = float(np.percentile(G, 98.0))
    im2 = ax[1].pcolormesh(ox, oy[keep], G.T, shading="auto", cmap="magma",
                           vmin=0.0, vmax=hi)
    ax[1].contour(ox, oy[keep], (inten[:, keep] / inten.max()).T,
                  levels=[0.05, 0.5], colors="w", linewidths=0.9)
    ax[1].axhline(0.0, color="w", lw=0.6, ls=":")
    ax[1].axhline(film, color="w", lw=0.6, ls=":")
    ax[1].set_xlabel("x (um), zero on the arm")
    ax[1].set_ylabel("y (um)")
    ax[1].set_title(
        f"the same field on the optical mesh, mode at 5 and 50 per cent; "
        f"$\\Gamma$ = {eo['eo_overlap_gamma']:.4f}, "
        f"$V_{{\\pi}} L$ = {eo['VpiL_V_cm']:.3f} V.cm per arm",
        fontsize=10)
    fig.colorbar(im2, ax=ax[1])

    fig.savefig(out, dpi=150)
    print(f"{out}  from  {run_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
