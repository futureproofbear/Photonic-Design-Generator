"""Render a factorial corner sweep as a heat map.

A factorial sweep over four parameters at three levels each produces 81 corners,
which a table reports as a pass count and a range. Both compress away the thing a
reader needs, which is where in the process window the failures sit. The 81
corners lay out on a 9 x 9 grid by pairing the parameters two and two, so every
corner keeps its own cell and its own address.

Usage, from design-chain/:

    $PY tools/corner_heatmap.py \\
        --design ../examples/edbr_tfln_baseline="baseline" \\
        --metric cavity.mode_hop_free_range_placed_GHz \\
        --threshold 8.0 --direction min --out corners.png

Each --design takes a design directory, optionally followed by =label, and reads
runs/corners.json beneath it. Where several are given they share one colour
scale, so a colour carries the same margin in every panel.

The sweep is required to be factorial over exactly four parameters. A one-factor
sweep has no grid to draw.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

LEVELS = (-1, 0, 1)


def corner_levels(label: str, params: list[str]) -> dict[str, int]:
    """The level of each parameter for one corner.

    A parameter held at its nominal value is omitted from the label, so the
    default is level zero.
    """
    out = dict.fromkeys(params, 0)
    if label == "nominal":
        return out
    for part in label.split(","):
        part = part.strip()
        for p in params:
            if part.startswith(p):
                suffix = part[len(p):]
                if suffix in ("+1", "-1"):
                    out[p] = 1 if suffix == "+1" else -1
    return out


def load(design: pathlib.Path, metric: str):
    """The 9 x 9 value grid, the failure mask and the sweep record."""
    path = design / "runs" / "corners.json"
    if not path.exists():
        raise SystemExit(f"no corner sweep at {path}")
    d = json.loads(path.read_text())
    params = list(d["parameters"])
    if d.get("mode") != "factorial" or len(params) != 4:
        raise SystemExit(
            f"{path} holds a {d.get('mode')} sweep over {len(params)} parameters; "
            "the heat map requires a factorial sweep over four")

    z = np.full((9, 9), np.nan)
    fail = np.zeros((9, 9), dtype=bool)
    seen = 0
    for r in d["rows"]:
        lv = corner_levels(r["corner"], params)
        row = (lv[params[0]] + 1) * 3 + (lv[params[1]] + 1)
        col = (lv[params[2]] + 1) * 3 + (lv[params[3]] + 1)
        v = r.get("metrics", {}).get(metric)
        if isinstance(v, (int, float)):
            z[row, col] = float(v)
            seen += 1
        fail[row, col] = metric in (r.get("must_failures") or [])
    if seen == 0:
        raise SystemExit(f"metric {metric} was not recorded at any corner of {path}")
    if seen < len(d["rows"]):
        print(f"  ! {design.name}: {len(d['rows']) - seen} corners carry no value "
              f"for {metric} and are drawn blank", file=sys.stderr)
    return z, fail, d, params


def tick_labels() -> list[str]:
    return [f"{a:+d}{b:+d}".replace("+0", " 0") for a in LEVELS for b in LEVELS]


def short(param: str) -> str:
    return param.split(".", 1)[-1].replace("_um", "").replace("_deg", "").replace("_", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append", required=True, metavar="DIR[=LABEL]",
                    help="design directory holding runs/corners.json; repeatable")
    ap.add_argument("--metric", required=True, help="dotted metric name to map")
    ap.add_argument("--threshold", type=float, required=True,
                    help="the requirement the metric is judged against")
    ap.add_argument("--direction", choices=("min", "max"), default="min",
                    help="min where the threshold is a floor, max where it is a ceiling")
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()

    panels = []
    for spec in a.design:
        d_path, _, label = spec.partition("=")
        p = pathlib.Path(d_path).resolve()
        z, fail, rec, params = load(p, a.metric)
        panels.append((label or p.name, z, fail, rec, params))

    allz = np.concatenate([p[1].ravel() for p in panels])
    lo, hi = float(np.nanmin(allz)), float(np.nanmax(allz))
    # the threshold is the neutral point of the scale, so the sign of the margin
    # is legible without reading the number
    norm = TwoSlopeNorm(vmin=min(lo, a.threshold - 1e-3), vcenter=a.threshold,
                        vmax=max(hi, a.threshold + 1e-3))
    cmap = "RdYlGn" if a.direction == "min" else "RdYlGn_r"

    n = len(panels)
    # a single panel still needs the width of the caption above it
    fig, axes = plt.subplots(1, n, figsize=(9.5 if n == 1 else 7.75 * n, 6.8),
                             squeeze=False)
    for ax, (label, z, fail, rec, params) in zip(axes[0], panels):
        im = ax.imshow(z, cmap=cmap, norm=norm, origin="lower")
        for i in range(9):
            for j in range(9):
                if np.isnan(z[i, j]):
                    continue
                ax.text(j, i, f"{z[i, j]:.2f}", ha="center", va="center",
                        fontsize=6.2, color="black")
                if fail[i, j]:
                    ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                               edgecolor="black", lw=2.0))
        ax.add_patch(plt.Rectangle((3.5, 3.5), 1, 1, fill=False, edgecolor="#1a73e8",
                                   lw=2.0, ls=":"))
        ax.set_xticks(range(9)); ax.set_xticklabels(tick_labels(), fontsize=7)
        ax.set_yticks(range(9)); ax.set_yticklabels(tick_labels(), fontsize=7)
        ax.set_xlabel(f"{short(params[2])} , {short(params[3])}", fontsize=9)
        ax.set_ylabel(f"{short(params[0])} , {short(params[1])}", fontsize=9)
        worst = np.nanmin(z) if a.direction == "min" else np.nanmax(z)
        ax.set_title(f"{label}\n{rec['n_pass']} of {rec['n_corners']} corners pass "
                     f"overall\n{int(fail.sum())} fail this metric (outlined) · "
                     f"worst {worst:.2f}", fontsize=10)

    cb = fig.colorbar(im, ax=axes[0].tolist(), fraction=0.046 if n == 1 else 0.060,
                      pad=0.03)
    cb.set_label(a.metric, fontsize=9)
    cb.ax.axhline(a.threshold, color="black", lw=1.4)

    rel = "floor" if a.direction == "min" else "ceiling"
    scale = "" if n == 1 else "one colour scale across all panels · "
    fig.suptitle(
        f"Factorial process window: {a.metric} against a {a.threshold:g} {rel}\n"
        f"{scale}white is the threshold · black outline fails at `must` · "
        "dotted blue is nominal",
        fontsize=10 if n == 1 else 11)
    if n == 1:
        fig.subplots_adjust(left=0.13, right=0.84, top=0.80, bottom=0.09)
    else:
        fig.subplots_adjust(left=0.06, right=0.86, top=0.80, bottom=0.09, wspace=0.22)

    out = pathlib.Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=a.dpi)
    print(f"written {out}")
    for label, z, fail, rec, _ in panels:
        print(f"  {label}: min {np.nanmin(z):.2f}  max {np.nanmax(z):.2f}  "
              f"fail this metric {int(fail.sum())}  overall "
              f"{rec['n_pass']}/{rec['n_corners']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
