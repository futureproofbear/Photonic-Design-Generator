#!/usr/bin/env python
"""Draw where the electrodes and their bond pads sit on a device.

The mask plan the chain already draws puts the electrodes and the pads on one
layer in one colour, because a process that patterns them in one lithographic
step gives them one layer number. A reader of that figure can see that metal
exists and cannot see which metal is which, nor which pair drives which section
on a device carrying more than one.

This draws the same geometry with each run identified, each gap stated, and each
pad located. It reads the emitted layout rather than the design file, so what it
shows is what the mask carries.

    $PY tools/electrode_plan.py <design-dir> --tag L22K --out figures/electrode_plan.png

Electrodes and pads are told apart by shape: a pad is compact and an electrode
is long and thin. The classification is reported so that a reader can check it.

Exit codes: 0 written, 2 the run or its layout is missing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def _metal_shapes(gds: pathlib.Path, layer: tuple[int, int]):
    """Bounding boxes on the metal layer, in micrometres."""
    import klayout.db as db

    ly = db.Layout()
    ly.read(str(gds))
    top, dbu = ly.top_cell(), ly.dbu
    li = ly.layer(*layer)
    out = []
    for sh in top.shapes(li).each():
        b = sh.polygon.bbox() if sh.is_polygon() else sh.box
        out.append((b.left * dbu, b.bottom * dbu, b.right * dbu, b.top * dbu))
    return out


def _classify(boxes, aspect: float = 4.0):
    """Split into electrodes and pads. A pad is compact; an electrode is not."""
    elec, pads = [], []
    for x0, y0, x1, y1 in boxes:
        w, h = x1 - x0, y1 - y0
        (elec if max(w, h) / max(min(w, h), 1e-9) >= aspect else pads).append((x0, y0, x1, y1))
    return elec, pads


def _pairs(items, tol: float = 1.0):
    """Group boxes into pairs sharing an x-run, which is one electrode pair."""
    out: list[list] = []
    for b in sorted(items, key=lambda t: (t[0], t[1])):
        for grp in out:
            if abs(grp[0][0] - b[0]) < tol and abs(grp[0][2] - b[2]) < tol:
                grp.append(b)
                break
        else:
            out.append([b])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", type=pathlib.Path)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--dpi", type=int, default=170)
    a = ap.parse_args()

    runs = sorted((a.design / "runs").glob(f"*-{a.tag}"))
    if not runs:
        print(f"no run tagged {a.tag} under {a.design}", file=sys.stderr)
        return 2
    run = runs[-1]
    layout = json.loads((run / "layout.json").read_text(encoding="utf-8"))
    gds = run / pathlib.Path(layout["gds"]).name
    if not gds.exists():
        print(f"{run.name}: the emitted layout is absent, so nothing can be drawn",
              file=sys.stderr)
        return 2

    lmap = layout["layer_map"]
    metal = tuple(lmap.get("METAL") or lmap.get("PAD") or (20, 0))
    wg = tuple(lmap.get("WG") or (2, 10))

    boxes = _metal_shapes(gds, metal)
    elec, pads = _classify(boxes)
    e_pairs, p_pairs = _pairs(elec), _pairs(pads)
    if not e_pairs:
        print(f"{run.name}: no electrode-shaped metal found on layer {metal}",
              file=sys.stderr)
        return 2

    # a run and the pads whose x-centre falls inside it belong together
    groups = []
    for grp in sorted(e_pairs, key=lambda g: g[0][0]):
        x0, x1 = grp[0][0], grp[0][2]
        mine = [p for p in p_pairs if x0 <= (p[0][0] + p[0][2]) / 2 <= x1]
        gap = 0.0
        if len(grp) >= 2:
            ys = sorted(grp, key=lambda b: b[1])
            gap = ys[1][1] - ys[0][3]
            gap = ys[-1][1] - ys[0][3]
        groups.append({"x0": x0, "x1": x1, "gap": gap, "pads": mine})

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    dev = float(layout.get("device_length_um") or max(g["x1"] for g in groups))
    names = ["phase section", "mirror", "third run", "fourth run"]
    if len(groups) == 1:
        names = ["mirror"]

    fig = plt.figure(figsize=(13.5, 7.2))
    gs = fig.add_gridspec(2, len(groups), height_ratios=[1.0, 1.25], hspace=0.42,
                          wspace=0.22)
    ax = fig.add_subplot(gs[0, :])

    def draw(ax, boxes_e, boxes_p, colour_e="#c9a227", colour_p="#8c6d1f"):
        for x0, y0, x1, y1 in boxes_e:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                                   fc=colour_e, ec="none", zorder=3))
        for x0, y0, x1, y1 in boxes_p:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                                   fc=colour_p, ec="none", zorder=3))

    # ---- the whole device -------------------------------------------------
    ax.axhline(0.0, color="#b03a2e", lw=1.6, zorder=4)
    draw(ax, elec, pads)
    gstart = float(layout.get("grating_start_um") or 0.0)
    glen = float(layout.get("drawn_grating_length_um") or 0.0)
    if glen:
        ax.add_patch(Rectangle((gstart, -1.2), glen, 2.4, fc="#b03a2e",
                               ec="none", alpha=0.35, zorder=2))
        ax.annotate(f"Bragg grating, {glen/1000:.1f} mm",
                    xy=(gstart + glen / 2, -1.2), xytext=(gstart + glen / 2, -95),
                    ha="center", fontsize=10, color="#7b241c",
                    arrowprops=dict(arrowstyle="->", color="#7b241c", lw=1.0))
    for name, g in zip(names, groups):
        xm = (g["x0"] + g["x1"]) / 2
        ax.annotate(f"{name} electrodes\n{g['x1'] - g['x0']:.0f} µm long, "
                    f"gap {g['gap']:.2f} µm",
                    xy=(xm, 22), xytext=(xm, 132), ha="center", fontsize=10,
                    color="#7d6608",
                    arrowprops=dict(arrowstyle="->", color="#7d6608", lw=1.2))
        for p in g["pads"]:
            px = (p[0][0] + p[0][2]) / 2
            ax.annotate(f"{name} pads\n{p[0][2]-p[0][0]:.0f} × "
                        f"{p[0][3]-p[0][1]:.0f} µm",
                        xy=(px, -120), xytext=(px, -190), ha="center", fontsize=10,
                        color="#4a3708",
                        arrowprops=dict(arrowstyle="->", color="#4a3708", lw=1.2))
    ax.set_xlim(-400, dev + 400)
    ax.set_ylim(-230, 175)
    ax.set_xlabel("distance from the facet, µm")
    ax.set_yticks([])
    ax.set_title(f"where the metal sits on the device — {run.name}\n"
                 f"{len(groups)} electrode run(s), {sum(len(g['pads']) for g in groups)*2} "
                 f"pads, all on layer {metal[0]}/{metal[1]}", fontsize=11)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    # ---- one panel per electrode run --------------------------------------
    for i, (name, g) in enumerate(zip(names, groups)):
        axz = fig.add_subplot(gs[1, i])
        # Zoom on the pads and not on the whole run. A 17 mm electrode drawn to
        # its full length renders its own 100 um pad as a sliver, which is the
        # thing the panel exists to show.
        pad_x = [p[0] for p in g["pads"]]
        if pad_x:
            c = sum((p[0] + p[2]) / 2 for p in pad_x) / len(pad_x)
            half = 320.0
            lo, hi = c - half, c + half
        else:
            lo, hi = g["x0"] - 60, g["x1"] + 60
        axz.axhline(0.0, color="#b03a2e", lw=2.0, zorder=4)
        draw(axz, elec, pads)
        axz.set_xlim(lo, hi)
        axz.set_ylim(-150, 150)
        axz.set_xlabel("µm")
        axz.set_yticks([-100, 0, 100])
        axz.set_ylabel("µm")
        axz.set_title(f"{name}: pads and gap, {g['gap']:.2f} µm", fontsize=10)
        axz.annotate("", xy=(lo + (hi - lo) * 0.5, g["gap"] / 2),
                     xytext=(lo + (hi - lo) * 0.5, -g["gap"] / 2),
                     arrowprops=dict(arrowstyle="<->", color="#1b4f72", lw=1.4))
        axz.text(lo + (hi - lo) * 0.53, 42, f"gap {g['gap']:.2f} µm",
                 va="center", fontsize=9, color="#1b4f72")
        axz.grid(alpha=0.25)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=a.dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"written {a.out}")
    for name, g in zip(names, groups):
        print(f"  {name:16s} x {g['x0']:8.1f} .. {g['x1']:8.1f}  "
              f"gap {g['gap']:.2f} um  pads {len(g['pads'])*2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
