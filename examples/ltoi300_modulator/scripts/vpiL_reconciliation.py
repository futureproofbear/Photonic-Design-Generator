"""Where the chain and the published half-wave figures meet, term by term.

Three figures are placed on one convention, the interferometer driven push-pull,
and the two corrections that stand between the run and the claim are applied in
order and drawn as a waterfall.

The first correction is the electrostatic mesh. The overlap converges as about
the square root of the cell, and the ladder fitted by `mesh_convergence.py`
gives the limit; the factor is the ratio of that limit to the overlap at the
cell every run in this study was posed on.

The second is the normalisation of the perturbation integral, computed for each
cross-section by `perturbation_normalisation.py`.

Neither is fitted to the published figures. The mesh factor comes from a ladder
of four solves of one cross-section and the normalisation from the mode profile
of each. Both are supplied on the command line so that the arithmetic drawn here
is the arithmetic those two scripts printed.

    python examples/ltoi300_modulator/scripts/vpiL_reconciliation.py \
        --mesh-factor 1.09107 \
        --case <run_dir> <normalisation> <published> <label> \
        [--case ...] [--out figures/vpiL_reconciliation.png]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def read(run_dir: Path) -> dict:
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    m = m.get("metrics", m)
    return {
        "device": float(m["modulator"]["VpiL_device_V_cm"]),
        "arm": float(m["eo"]["VpiL_V_cm"]),
        "gamma": float(m["eo"]["eo_overlap_gamma"]),
        "r33": float(m["eo"]["r_pm_per_V"]),
        "n_e": float(m["eo"]["n_extraordinary"]),
        "gap": float(m["eo"]["electrode_gap_um"]),
        "lam": float(m["eo"]["wavelength_um"]),
        "run": run_dir.name,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh-factor", type=float, required=True,
                    help="the ratio of the extrapolated overlap to the overlap "
                         "at the cell the runs were posed on")
    ap.add_argument("--case", nargs=4, action="append", required=True,
                    metavar=("RUN_DIR", "NORMALISATION", "PUBLISHED", "LABEL"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    here = Path(__file__).resolve().parent.parent
    out = Path(a.out) if a.out else here / "figures" / "vpiL_reconciliation.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    cases = []
    for run_dir, norm, published, label in a.case:
        r = read(Path(run_dir))
        norm, published = float(norm), float(published)
        stages = [
            ("as the run reports it", r["device"]),
            ("mesh limit", r["device"] / a.mesh_factor),
            ("energy-normalised", r["device"] / a.mesh_factor / norm),
        ]
        cases.append({"label": label, "stages": stages, "published": published,
                      "r": r, "norm": norm})

        final = stages[-1][1]
        gamma_final = r["gamma"] * a.mesh_factor * norm
        need = (r["lam"] * 1e-6) * (r["gap"] * 1e-6) / \
               (r["n_e"] ** 3 * 2 * published * 1e-2)
        print(f"{label}   ({r['run']})")
        for name, v in stages:
            print(f"   {name:24s} {v:8.4f} V.cm   "
                  f"{100 * (v / published - 1):+7.2f} per cent of the claim")
        print(f"   the claim                {published:8.4f} V.cm")
        print(f"   overlap {r['gamma']:.5f} as reported, {gamma_final:.5f} "
              f"after both corrections")
        print(f"   r33 * Gamma {r['r33'] * gamma_final:.3f} pm/V against the "
              f"{need * 1e12:.3f} pm/V the claim requires, a residual of "
              f"{100 * (r['r33'] * gamma_final / (need * 1e12) - 1):+.2f} per cent")
        print()

    fig, ax = plt.subplots(figsize=(8.4, 4.6), constrained_layout=True)
    n = len(cases)
    width = 0.24
    colours = ["#c26a3a", "#d79a6a", "#e8c9a8"]
    xs = np.arange(n)
    for j in range(3):
        vals = [c["stages"][j][1] for c in cases]
        ax.bar(xs + (j - 1) * width, vals, width, color=colours[j],
               label=cases[0]["stages"][j][0], zorder=3)
        for x, v in zip(xs + (j - 1) * width, vals):
            ax.text(x, v + 0.03, f"{v:.2f}", ha="center", fontsize=7.5)
    for i, c in enumerate(cases):
        ax.plot([i - 1.7 * width, i + 1.7 * width], [c["published"]] * 2,
                color="#2f6f4f", lw=2.2, zorder=4)
        ax.text(i + 1.75 * width, c["published"], f" {c['published']:.3f}",
                va="center", fontsize=8, color="#2f6f4f")
    ax.plot([], [], color="#2f6f4f", lw=2.2, label="the published figure")
    ax.set_xticks(xs)
    ax.set_xticklabels([c["label"] for c in cases], fontsize=8.5)
    ax.set_ylabel("$V_{\\pi} L$ of the interferometer, push-pull (V.cm)")
    ax.set_title("The chain against the published figures, correction by correction")
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.legend(fontsize=8)
    fig.savefig(out, dpi=150)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
