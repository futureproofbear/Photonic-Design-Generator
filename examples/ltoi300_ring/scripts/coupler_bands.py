"""Both single-mode ring cells, on what the chain measured for each.

The two cells are the same structure at two wavelengths, and they behave
differently enough that neither stands for the other. The coupling is read from
the run tree rather than from a script's own solve, so the figure carries what
the stage published.

    python examples/ltoi300_ring/scripts/coupler_bands.py <runs_dir> <out.png>
"""

from __future__ import annotations

import glob
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = 200.0
L = 2 * np.pi * R
L_CM = L * 1e-4

#: name, run-directory suffix, group index, design wavelength, drawn gap,
#: the loss bracket transferred to that cross-section, and a colour
BANDS = (
    ("O band, 0.7 um ridge, 1.05 um gap", "oband_coupler", 2.189394, 1.31, 1.05,
     (0.436, 1.798), "tab:blue"),
    ("C band, 0.9 um ridge, 1.50 um gap", "cband_coupler", 2.130398, 1.55, 1.50,
     (0.310, 0.947), "tab:red"),
)


def latest(runs: str, suffix: str) -> dict:
    hits = sorted(glob.glob(f"{runs}/*{suffix}/metrics.json"))
    if not hits:
        raise SystemExit(f"no run of {suffix} under {runs}")
    return json.loads(open(hits[-1]).read())["metrics"]["fdtd"]


def extinction(kappa2: float, loss_dB_cm) -> np.ndarray:
    t = np.sqrt(1.0 - kappa2)
    a = 10 ** (-np.asarray(loss_dB_cm) * L_CM / 20.0)
    return 10 * np.log10(np.clip(((t - a) / (1 - t * a)) ** 2, 1e-12, None))


def main() -> int:
    runs, out = sys.argv[1], sys.argv[2]
    fig, axs = plt.subplots(1, 2, figsize=(12.4, 4.9))
    loss = np.logspace(np.log10(0.02), np.log10(3.0), 600)

    for name, suffix, ng, lam0, gap, bracket, colour in BANDS:
        m = latest(runs, suffix)
        lam = np.asarray(m["wavelength_um"])
        k2 = np.asarray(m["kappa2_spectrum"])
        order = np.argsort(lam)
        axs[0].plot(1e3 * lam[order], 100 * k2[order], "o-", ms=3, lw=1.2,
                    color=colour, label=name)
        axs[0].plot([1e3 * lam0], [100 * m["kappa2"]], "*", ms=13, color=colour)

        ax = axs[1]
        ax.plot(loss, extinction(m["kappa2"], loss), lw=1.4, color=colour,
                label=f"{name.split(',')[0]}, {100*m['kappa2']:.3f} %")
        ax.axvspan(*bracket, color=colour, alpha=0.10)
        ax.axvline(m["critical_coupling_loss_dB_cm"], color=colour, ls=":", lw=1.0)
        ax.annotate(f"critical at {m['critical_coupling_loss_dB_cm']:.3f} dB/cm",
                    (m["critical_coupling_loss_dB_cm"], -1.5), rotation=90,
                    fontsize=7, color=colour, ha="right", va="top")

    axs[0].set_xlabel("wavelength [nm]")
    axs[0].set_ylabel(r"power coupling $\kappa^2$ [%]")
    axs[0].set_title("What each coupler gives across its band", fontsize=10)
    axs[0].grid(alpha=0.3, lw=0.5)
    axs[0].legend(fontsize=8, loc="upper left")

    axs[1].set_xscale("log")
    axs[1].set_xlabel("propagation loss [dB/cm]")
    axs[1].set_ylabel("through-port extinction [dB]")
    axs[1].set_ylim(-45, 2)
    axs[1].set_title("The ring closed on it, over the transferred loss", fontsize=10)
    axs[1].grid(alpha=0.3, lw=0.5, which="both")
    axs[1].legend(fontsize=8, loc="lower right")

    fig.suptitle("ltoi300 single-mode rings, R = 200 um: the coupler measured by "
                 "the chain, and what it decides", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)
    for name, suffix, ng, lam0, gap, bracket, _ in BANDS:
        m = latest(runs, suffix)
        lo, hi = extinction(m["kappa2"], bracket)
        print(f"{name}: kappa2 {100*m['kappa2']:.3f} %, critical at "
              f"{m['critical_coupling_loss_dB_cm']:.3f} dB/cm, extinction "
              f"{lo:.1f} to {hi:.1f} dB across {bracket[0]} to {bracket[1]} dB/cm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
