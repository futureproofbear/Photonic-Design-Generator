"""The mesh ladder, its convergence order, and the limit it extrapolates to.

The electro-optic overlap of a shallow-etched ridge converges slowly in the
electrostatic cell, the sloped sidewall carrying a permittivity step of about
eleven and being staircased by the raster. The convergence guard in the stage
reports the shift between one cell and half of it, which establishes that the
figure is still moving; it does not say where it is moving to. That is what a
ladder of four cells and a fit supply.

The model fitted is

    Q(h) = Q_inf - C h^p

with p free, which is the ordinary form for a quantity limited by a geometric
discretisation. It is fitted to the three intervals rather than assumed, and the
order it returns is reported beside the limit so that a reader can see whether
the extrapolation is a short one.

    python examples/ltoi300_modulator/scripts/mesh_convergence.py \
        <run_dir> <run_dir> <run_dir> ... [--plot out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def read(run_dir: Path) -> dict:
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    m = m.get("metrics", m)
    tw = m["eo"]["travelling_wave"]
    return {
        "h": m["eo"]["rf_mesh"]["d_fine_um"],
        "Gamma": m["eo"]["eo_overlap_gamma"],
        "VpiL": m["eo"]["VpiL_V_cm"],
        "C": m["eo"]["capacitance_pF_per_cm"],
        "n_m": tw["microwave_index"],
        "Z0": tw["characteristic_impedance_ohm"],
        "f3dB": tw["electro_optic_3dB_GHz"],
        "run": run_dir.name,
    }


def fit(h: np.ndarray, q: np.ndarray) -> tuple[float, float, float]:
    """Q_inf, C and p of Q(h) = Q_inf - C h^p, by search on p.

    The residual is linear in Q_inf and C once p is fixed, so the fit is one
    least-squares solve inside a scan over p rather than a general optimiser.
    """
    best = (float("inf"), 0.0, 0.0, 0.0)
    for p in np.linspace(0.05, 4.0, 3951):
        A = np.column_stack([np.ones_like(h), -(h ** p)])
        sol, *_ = np.linalg.lstsq(A, q, rcond=None)
        r = float(np.sum((A @ sol - q) ** 2))
        if r < best[0]:
            best = (r, float(sol[0]), float(sol[1]), float(p))
    return best[1], best[2], best[3]


def main() -> int:
    argv = sys.argv[1:]
    plot = None
    if "--plot" in argv:
        i = argv.index("--plot")
        plot = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 3:
        print(__doc__)
        return 2

    rows = sorted((read(Path(a)) for a in args), key=lambda r: -r["h"])
    keys = ["Gamma", "VpiL", "C", "n_m", "Z0", "f3dB"]
    h = np.array([r["h"] for r in rows])

    print("cell (um)  " + "  ".join(k.rjust(10) for k in keys))
    for r in rows:
        print(f"{r['h']:9.5f}  " + "  ".join(f"{r[k]:10.5g}" for k in keys))

    print("\nfitted limit of Q(h) = Q_inf - C h^p, where the ladder is monotone")
    print("quantity     at the finest cell         limit   order  residual"
          "     spread")
    out = {}
    for k in keys:
        q = np.array([r[k] for r in rows])
        d = np.diff(q)
        monotone = bool(np.all(d > 0) or np.all(d < 0))
        spread = (q.max() - q.min()) / abs(q.mean())
        if monotone:
            q_inf, _c, p = fit(h, q)
            resid = (q_inf - q[-1]) / q_inf if q_inf else float("nan")
            out[k] = q_inf
            print(f"{k:12s}  {q[-1]:16.5g}  {q_inf:12.5g}  {p:6.2f}  "
                  f"{100 * resid:+7.2f}%  {100 * spread:8.2f}%")
        else:
            out[k] = float(q[-1])
            print(f"{k:12s}  {q[-1]:16.5g}  {'not monotone':>12s}  {'-':>6s}  "
                  f"{'-':>8s}  {100 * spread:8.2f}%")
    print("\nA quantity whose ladder is not monotone is not extrapolated. The "
          "spread over the")
    print("ladder is the uncertainty to carry and the finest cell supplies the "
          "value.")

    print(f"\nthe half-wave figure of the interferometer at the fitted overlap "
          f"is {out['VpiL'] / 2:.4f} V.cm")

    if plot is not None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        q = np.array([r["Gamma"] for r in rows])
        q_inf, c, p = fit(h, q)
        fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
        hh = np.linspace(0.0, h.max() * 1.05, 200)
        ax.plot(hh * 1000, q_inf - c * hh ** p, lw=1.4, color="0.5",
                label=f"$\\Gamma_\\infty - C h^{{{p:.2f}}}$")
        ax.plot(h * 1000, q, "o", color="#c26a3a", label="the ladder")
        ax.axhline(q_inf, color="#4a7fb5", ls="--", lw=1.0,
                   label=f"$\\Gamma_\\infty$ = {q_inf:.4f}")
        ax.set_xlabel("electrostatic cell (nm)")
        ax.set_ylabel("electro-optic overlap $\\Gamma$")
        ax.set_title("The overlap against the cell it was solved on")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        plot.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(plot, dpi=150)
        print(f"\n{plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
