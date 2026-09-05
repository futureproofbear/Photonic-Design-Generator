"""Figure for the point-coupler solve: the coupling measured, and what it decides.

Reads the JSON results written by ``meep_point_coupler.py`` and draws three
panels. The first is the power coupling across the O band at the drawn gap,
with the couplings that critical coupling would require at three propagation
losses. The second is the gap dependence, from which the decay constant is
fitted. The third is the through-port response of the ring closed by the
transfer matrix on the measured coupling, at those same three losses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R, NG, LAM0 = 200.0, 2.189394, 1.31
L = 2 * np.pi * R
LOSSES = ((0.056, "0.056 dB/cm", "tab:blue"),
          (0.171, "0.171 dB/cm", "tab:green"),
          (0.500, "0.500 dB/cm", "tab:red"))


def load(d: Path, tag: str) -> dict:
    return json.loads((d / f"out_{tag}.json").read_text())


def main() -> int:
    d = Path(sys.argv[1])
    out = sys.argv[2]
    design = load(d, "g1050_r50")
    guard = load(d, "g1050_r25")
    sweep = [load(d, t) for t in ("g850_r50", "g1050_r50", "g1250_r50")]

    lam = np.asarray(design["wavelength_um"])
    k2 = np.asarray(design["kappa2"])
    k2_design = design["kappa2_at_design"]

    fig, axs = plt.subplots(1, 3, figsize=(16, 4.9))

    ax = axs[0]
    ax.plot(1e3 * lam, 100 * k2, "o-", ms=3, lw=1.2, color="k",
            label="FDTD, gap 1.05 um")
    for lo, lab, c in LOSSES:
        a2 = 10 ** (-lo * L * 1e-4 / 10)
        ax.axhline(100 * (1 - a2), color=c, ls="--", lw=1.0,
                   label=f"critical at {lab}")
    ax.set_xlabel("wavelength [nm]")
    ax.set_ylabel(r"power coupling $\kappa^2$ [%]")
    ax.set_title("What the coupler gives, and what critical coupling asks",
                 fontsize=10)
    ax.grid(alpha=0.3, lw=0.5)
    ax.legend(fontsize=7.5, loc="upper left")

    ax = axs[1]
    g = np.array([s["job"]["gap_um"] for s in sweep])
    kk = np.array([s["kappa2_at_design"] for s in sweep])
    p = np.polyfit(g, np.log(kk), 1)
    gg = np.linspace(0.75, 1.45, 100)
    ax.semilogy(gg, 100 * np.exp(np.polyval(p, gg)), lw=1.0, color="tab:orange",
                label=fr"fit, $2\gamma$ = {-p[0]:.2f} /um")
    ax.semilogy(g, 100 * kk, "o", ms=6, color="k", label="FDTD, resolution 50")
    ax.semilogy([1.05], [100 * guard["kappa2_at_design"]], "s", ms=6, mfc="none",
                color="tab:red", label="resolution 25, the guard")
    for lo, lab, c in LOSSES:
        ax.axhline(100 * (1 - 10 ** (-lo * L * 1e-4 / 10)), color=c, ls="--", lw=0.9)
    ax.set_xlabel("coupler gap [um]")
    ax.set_ylabel(r"$\kappa^2$ at 1310 nm [%]")
    ax.set_title("Gap dependence and the mesh guard", fontsize=10)
    ax.grid(alpha=0.3, lw=0.5, which="both")
    ax.legend(fontsize=7.5, loc="upper right")

    ax = axs[2]
    t = np.sqrt(1 - k2_design)
    dl = np.linspace(-0.0016, 0.0016, 60001)
    lam_s = LAM0 + dl
    neff = 1.748261 - (NG - 1.748261) * dl / LAM0
    phi = 2 * np.pi * neff * L / lam_s
    for lo, lab, c in LOSSES:
        a = 10 ** (-lo * L * 1e-4 / 20)
        T = np.abs((t - a * np.exp(1j * phi)) / (1 - t * a * np.exp(1j * phi))) ** 2
        i0 = int(np.argmin(T))
        ax.plot(1e6 * (lam_s - lam_s[i0]), 10 * np.log10(T), lw=1.1, color=c,
                label=f"{lab}, {10*np.log10(T[i0]):.1f} dB")
    ax.set_xlim(-12, 12)
    ax.set_ylim(-40, 2)
    ax.set_xlabel("detuning from resonance [pm]")
    ax.set_ylabel("through-port transmission [dB]")
    ax.set_title(fr"The ring closed on $\kappa^2$ = {100*k2_design:.3f} %", fontsize=10)
    ax.grid(alpha=0.3, lw=0.5)
    ax.legend(fontsize=7.5, loc="lower right")

    fig.suptitle("ltoi300 O-band ring, point coupler by FDTD: 2D effective-index "
                 "model, n_core 1.84589 on a slab of 1.58654", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)
    print(f"kappa^2(1310 nm) = {100*k2_design:.3f} %, guard {100*guard['kappa2_at_design']:.3f} %")
    print(f"2*gamma from the gap sweep = {-p[0]:.3f} /um")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
