#!/usr/bin/env python
"""Render a named window of an emitted mask, with a chosen subset of layers.

The chain's own mask shots are fixed views chosen when the chain had one
electrode pair and one interesting region. A device carrying a second pair, a
second gap or a second section has no view of it, and the fixed windows cannot
be pointed anywhere else.

This renders any window of any run, showing only the layers asked for. Hiding a
layer is what makes a crowded region legible: a metal run over a slab over a
fill pattern draws as one block until the fill and the slab are turned off.

    $PY tools/mask_view.py <design-dir> --tag L22K --window 180,-140,1160,140 \\
        --layers WG,METAL --out figures/phase_section.png

    $PY tools/mask_view.py <design-dir> --tag L22K --list-layers

The window is given in micrometres as x0,y0,x1,y1. Layers are named as the
design's own layer map names them, and `--list-layers` prints those names with
the layer numbers they resolve to and whether the mask draws anything on each.

Exit codes: 0 written, 2 the run, its layout or the viewer is unavailable.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def _run_dir(design: pathlib.Path, tag: str) -> pathlib.Path | None:
    runs = sorted((design / "runs").glob(f"*-{tag}"))
    return runs[-1] if runs else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", type=pathlib.Path)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--window", help="x0,y0,x1,y1 in micrometres")
    ap.add_argument("--layers", default="",
                    help="comma-separated layer-map names; default is every layer")
    ap.add_argument("--hide", default="",
                    help="comma-separated names to hide, applied after --layers")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--size", default="1400,520", help="pixels, w,h")
    ap.add_argument("--die", action="store_true",
                    help="render the assembled die rather than the device cell")
    ap.add_argument("--list-layers", action="store_true")
    a = ap.parse_args()

    run = _run_dir(a.design, a.tag)
    if run is None:
        print(f"no run tagged {a.tag} under {a.design}", file=sys.stderr)
        return 2
    layout = json.loads((run / "layout.json").read_text(encoding="utf-8"))
    lmap: dict[str, list[int]] = layout["layer_map"]

    key = "gds"
    if a.die:
        try:
            key = "gds"
            ret = json.loads((run / "reticle.json").read_text(encoding="utf-8"))
            gds = run / pathlib.Path(ret["gds"]).name
        except Exception:
            gds = run / pathlib.Path(layout[key]).name
    else:
        gds = run / pathlib.Path(layout[key]).name
    if not gds.exists():
        print(f"{run.name}: {gds.name} is absent, so nothing can be rendered",
              file=sys.stderr)
        return 2

    try:
        import klayout.db as kdb
        import klayout.lay as klay
    except ImportError:
        print("the klayout module is unavailable", file=sys.stderr)
        return 2

    if a.list_layers:
        ly = kdb.Layout()
        ly.read(str(gds))
        top = ly.top_cell()
        print(f"{gds.name}")
        print(f"  {'name':16s} {'layer':>10s}  shapes")
        for name, (l, d) in sorted(lmap.items(), key=lambda kv: kv[1]):
            li = ly.layer(l, d)
            n = top.shapes(li).size()
            note = "" if n else "   (nothing drawn on it)"
            print(f"  {name:16s} {f'{l}/{d}':>10s}  {n}{note}")
        return 0

    if not a.window or not a.out:
        print("--window and --out are required unless --list-layers is given",
              file=sys.stderr)
        return 2

    try:
        x0, y0, x1, y1 = (float(v) for v in a.window.split(","))
    except Exception:
        print("--window must be x0,y0,x1,y1 in micrometres", file=sys.stderr)
        return 2
    w, h = (int(v) for v in a.size.split(","))

    lv = klay.LayoutView()
    lv.load_layout(str(gds), 0)
    lyp = gds.with_suffix(".lyp")
    if lyp.exists():
        try:
            lv.load_layer_props(str(lyp))
        except Exception:
            pass
    lv.max_hier()

    # Resolve the requested names to layer/datatype pairs. A name the design does
    # not declare is refused rather than silently ignored, because a view that
    # quietly drops the layer somebody asked to see is a view of the wrong thing.
    def resolve(spec: str) -> set[tuple[int, int]]:
        out = set()
        for nm in (s.strip() for s in spec.split(",") if s.strip()):
            if nm not in lmap:
                raise KeyError(nm)
            out.add(tuple(lmap[nm]))
        return out

    try:
        show = resolve(a.layers)
        hide = resolve(a.hide)
    except KeyError as exc:
        print(f"unknown layer name {exc}. Known names: {', '.join(sorted(lmap))}",
              file=sys.stderr)
        return 2

    shown = []
    it = lv.begin_layers()
    while not it.at_end():
        lp = it.current()
        pair = (lp.source_layer, lp.source_datatype)
        vis = True
        if show:
            vis = pair in show
        if pair in hide:
            vis = False
        lp.visible = vis
        lv.set_layer_properties(it, lp)
        if vis:
            shown.append(f"{pair[0]}/{pair[1]}")
        it.next()

    lv.zoom_box(kdb.DBox(x0, y0, x1, y1))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lv.save_image(str(a.out), w, h)
    print(f"written {a.out}")
    print(f"  run     {run.name}")
    print(f"  window  {x0:.1f},{y0:.1f} .. {x1:.1f},{y1:.1f} um "
          f"({x1 - x0:.1f} x {y1 - y0:.1f})")
    print(f"  layers  {', '.join(sorted(set(shown))) or 'all'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
