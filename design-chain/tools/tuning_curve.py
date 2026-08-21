"""Draw the laser frequency against drive voltage, and where the mode hops.

The tuning curve is the one figure in which a mode hop is visible as the thing it
is: a discontinuity in the frequency the laser emits. A table reports the
excursion as a number and says nothing about where the break falls or how much
of the drive lies either side of it.

The tracks come from `cavity.npz` of a named run, so the figure shows what the
mode tracking measured. Where a design carries an intracavity phase section, the
run also stores the second track taken with that section driven, and both are
drawn together: the comparison is the whole argument for the architecture.

    $PY tools/tuning_curve.py \\
        --design ../examples/edbr_tfln_baseline="baseline" --tag TAPEOUT \\
        --out tuning.png

Each --design takes a directory, optionally =label, and --tag names the run.
Repeat --design to place several devices side by side; --tag applies to all of
them unless given as many times as --design.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def load(design: pathlib.Path, tag: str):
    runs = sorted(glob.glob(str(design / "runs" / f"*{tag}" / "metrics.json")))
    if not runs:
        raise SystemExit(f"no run tagged {tag} under {design}")
    run_dir = pathlib.Path(runs[-1]).parent
    m = json.loads((run_dir / "metrics.json").read_text())["metrics"]["cavity"]
    npz = np.load(run_dir / "cavity.npz")
    return run_dir, m, npz


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append", required=True, metavar="DIR[=LABEL]")
    ap.add_argument("--tag", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()

    tags = a.tag if len(a.tag) == len(a.design) else [a.tag[0]] * len(a.design)
    panels = []
    for spec, tag in zip(a.design, tags):
        d_path, _, label = spec.partition("=")
        p = pathlib.Path(d_path).resolve()
        run_dir, m, npz = load(p, tag)
        panels.append((label or p.name, run_dir, m, npz))

    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(7.4 * n, 6.0), squeeze=False, sharey=True)

    for ax, (label, run_dir, m, npz) in zip(axes[0], panels):
        V = np.asarray(npz["V_sweep"], dtype=float)
        f = np.asarray(npz["f_laser_Hz"], dtype=float)
        if len(f) == 0:
            continue
        shift = (f - f[0]) / 1e9

        # break the line at each hop so the discontinuity is drawn as one
        jump = np.abs(np.diff(shift))
        cuts = np.nonzero(jump > 0.5 * float(m.get("fsr_GHz", 10.0)))[0]
        segs = np.split(np.arange(len(V)), cuts + 1)

        for k, idx in enumerate(segs):
            if len(idx) < 2:
                continue
            ax.plot(V[idx], shift[idx], lw=2.6, color="#1a73e8",
                    label="mirror alone" if k == 0 else None)
        for c in cuts:
            ax.axvline(V[c], color="0.45", ls="--", lw=1.1)
            ax.annotate(f"hop\n{V[c]:.1f} V", (V[c], ax.get_ylim()[1]),
                        xytext=(4, -28), textcoords="offset points",
                        fontsize=8, color="0.35")

        has_sync = "f_laser_Hz_synchronous" in npz.files
        if has_sync:
            Vs = np.asarray(npz["V_sweep_synchronous"], dtype=float)
            fs = np.asarray(npz["f_laser_Hz_synchronous"], dtype=float)
            ax.plot(Vs, (fs - fs[0]) / 1e9, lw=2.6, color="#137333",
                    label="phase section driven")

        n_hop = int(m.get("n_mode_hops_in_sweep", 0))
        bits = [f"mirror alone: {m['mode_hop_free_range_placed_GHz']:.2f} GHz, "
                f"{n_hop} hop" + ("s" if n_hop != 1 else "")]
        if has_sync:
            bits.insert(0, "phase section driven: "
                           f"{m['mode_hop_free_range_synchronous_GHz']:.2f} GHz, no hop")
        ax.set_title(f"{label}\n" + "\n".join(bits), fontsize=10)
        ax.set_xlabel("drive voltage  V", fontsize=9)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="upper left", framealpha=0.9)

    axes[0][0].set_ylabel("laser frequency shift from zero bias  GHz", fontsize=9)
    fig.suptitle("Laser frequency against drive voltage, and where the mode hops\n"
                 "tracks taken from cavity.npz of each run of record", fontsize=11)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.82, bottom=0.10, wspace=0.10)

    out = pathlib.Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=a.dpi)
    print(f"written {out}")
    for label, run_dir, m, npz in panels:
        sync = m.get("mode_hop_free_range_synchronous_GHz")
        print(f"  {label}: run {run_dir.name}  placed "
              f"{m['mode_hop_free_range_placed_GHz']:.3f} GHz  hops "
              f"{m.get('n_mode_hops_in_sweep')}"
              + (f"  synchronous {sync:.3f} GHz" if sync == sync else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
