"""Every layer the UBC kit's cells draw, against the layers it declares.

A kit says three things about a layer and they are meant to agree. Its layer map
gives the layer a name. Its layer stack gives that name a thickness and a
material, which is what a three-dimensional solve and a cross-section view
consume. And its cells draw polygons. A layer named and never drawn is dead
weight; a layer drawn and never named is worse, because nothing downstream can
say what it is.

This builds every cell in the kit, writes it, and sets the layers that carry
polygons against the two declarations.

It runs under the kit's own environment rather than the chain's, ubcpdk
requiring a gdsfactory the chain does not run. The remedy is one environment per
kit, and this expects to be run from the one built for it:

    design-chain/.venv-ubcpdk/Scripts/python.exe \\
        examples/ubc_soi220_stack/scripts/layer_audit.py
"""

from __future__ import annotations

import collections
import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

#: the layer names of the sibling KLayout kit, used only to say what an
#: undeclared number is likely to be. Taken from the published `EBeam.lyp`
#: recorded in `references/README.md`.
SIBLING = {
    (1, 0): "silicon", (2, 0): "the 90 nm rib", (4, 0): "silicon nitride",
    (6, 0): "oxide open", (10, 0): "text", (11, 0): "heater metal",
    (12, 0): "router metal", (13, 0): "pad opening", (40, 0): "via",
    (68, 0): "DevRec", (81, 0): "FbrTgt", (99, 0): "floor plan",
    (201, 0): "deep trench", (202, 0): "keep-out", (210, 0): "dicing",
    (290, 0): "chip design area",
}


def main() -> int:
    import klayout.db as kdb
    import ubcpdk
    from ubcpdk.tech import LAYER, LAYER_STACK

    ubcpdk.PDK.activate()

    named = {(n.layer, n.datatype): n.name for n in LAYER}
    extruded = set()
    for key, layer in LAYER_STACK.layers.items():
        spec = getattr(layer, "layer", None)
        name = getattr(spec, "name", None) or str(spec)
        extruded.add(name)

    out = Path(tempfile.mkdtemp(prefix="ubc_cells_"))
    built, failed = [], []
    for name in sorted(ubcpdk.PDK.cells):
        try:
            c = ubcpdk.PDK.cells[name]()
            c.write_gds(str(out / f"{name}.gds"))
            built.append(name)
        except Exception as exc:                       # noqa: BLE001
            failed.append((name, f"{type(exc).__name__}: {exc}"))

    drawn: collections.Counter = collections.Counter()
    area: collections.Counter = collections.Counter()
    by_layer: dict[tuple[int, int], list[str]] = collections.defaultdict(list)
    for name in built:
        ly = kdb.Layout()
        ly.read(str(out / f"{name}.gds"))
        top = ly.top_cell()
        for info in ly.layer_infos():
            r = kdb.Region(top.begin_shapes_rec(ly.layer(info.layer, info.datatype)))
            r.merge()
            if r.count():
                key = (info.layer, info.datatype)
                drawn[key] += 1
                area[key] += r.area() * ly.dbu * ly.dbu
                by_layer[key].append(name)

    print(f"ubcpdk {ubcpdk.__version__}: {len(built)} cells built, "
          f"{len(failed)} refused\n")
    for n, e in failed:
        print(f"  {n} -> {e[:80]}")
    if failed:
        print()

    print(f"{'layer':>9} {'named':14} {'extruded':>9} {'cells':>6} "
          f"{'area um2':>13}  what the sibling kit calls it")
    for key in sorted(drawn, key=lambda k: -drawn[k]):
        name = named.get(key, "")
        print(f"{key[0]:6d}/{key[1]:<2d} {name or '-- unnamed --':14} "
              f"{'yes' if name in extruded else 'no':>9} {drawn[key]:6d} "
              f"{area[key]:13.1f}  {SIBLING.get(key, '')}")

    unnamed = [k for k in drawn if k not in named]
    dead = [k for k, n in named.items() if k not in drawn]
    print(f"\n{len(drawn)} layer and datatype pairs carry polygons across the kit")
    print(f"{len(named)} are named by the layer map and "
          f"{len(extruded)} of those names are given a thickness by the layer stack")
    print(f"{len(unnamed)} carry polygons and are named by neither: "
          f"{', '.join(f'{a}/{b}' for a, b in sorted(unnamed))}")
    print(f"{len(dead)} are named and drawn by no cell: "
          f"{', '.join(sorted(named[k] for k in dead))}")

    for key in sorted(unnamed):
        if drawn[key] >= 5:
            print(f"\n{key[0]}/{key[1]} is drawn by {drawn[key]} cells, among them "
                  f"{', '.join(by_layer[key][:4])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
