"""Measure a written GDS file, layer by layer, at cuts through it.

Rule 11 of the chain requires every geometric parameter to be measured back off
the written file. The chain has held that rule for its own designs since the
facet angle was found to draw nothing, and it has been applied to a vendor kit
nowhere: every study conducted on the LTOI300 cells rebuilt each geometry from
the parameters its builder declares. A difference between a builder's parameters
and what the layout engine draws from them is therefore untested, and it is
exactly the difference the wafer would carry.

What is offered here is one instrument. A cut is taken through the emitted
polygons at a stated station, and the intervals the material occupies along that
cut are returned. That is the same quantity a mode solver consumes, so a cut
through the file may be set against the cross-section a study assumed, term by
term. Areas and bounding boxes per layer are returned beside it, which localises
a difference the cuts do not happen to pass through.

The measurement is taken from the file and not from the component in memory, so
anything the writer does on its way out is included.

    python tools/measure_layout.py <file.gds> [--cut x=10.0] [--layer 2/10]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import klayout.db as kdb


@dataclass(frozen=True)
class Layer:
    """One layer of a written file, and what it holds."""

    layer: int
    datatype: int
    polygons: int
    area_um2: float
    bbox_um: tuple[float, float, float, float] | None

    @property
    def spec(self) -> str:
        return f"{self.layer}/{self.datatype}"


def open_layout(path: str) -> tuple[kdb.Layout, kdb.Cell]:
    """The file, and the one cell that contains every other."""
    ly = kdb.Layout()
    ly.read(path)
    tops = ly.top_cells()
    if len(tops) != 1:
        names = ", ".join(c.name for c in tops)
        raise ValueError(f"{path} holds {len(tops)} top cells: {names}")
    return ly, tops[0]


def region(ly: kdb.Layout, cell: kdb.Cell, layer: int, datatype: int) -> kdb.Region:
    """Every polygon on one layer, hierarchy flattened and overlaps merged.

    Merging matters. A kit draws a taper as a run of abutting trapezoids and a
    cut landing on a shared edge would otherwise return two intervals where the
    material is continuous.
    """
    index = ly.layer(layer, datatype)
    r = kdb.Region(cell.begin_shapes_rec(index))
    r.merge()
    return r


def inventory(path: str) -> list[Layer]:
    """What every layer of the file holds, in the order the file declares them."""
    ly, cell = open_layout(path)
    dbu = ly.dbu
    out: list[Layer] = []
    for info in ly.layer_infos():
        r = region(ly, cell, info.layer, info.datatype)
        n = r.count()
        if n == 0:
            continue
        b = r.bbox()
        out.append(Layer(
            layer=info.layer,
            datatype=info.datatype,
            polygons=n,
            area_um2=r.area() * dbu * dbu,
            bbox_um=(b.left * dbu, b.bottom * dbu, b.right * dbu, b.top * dbu),
        ))
    return out


def cut(path: str, layer: int, datatype: int, axis: str, position_um: float,
        window_nm: float = 2.0) -> list[tuple[float, float]]:
    """The intervals one layer occupies along a cut, in micrometres.

    ``axis`` is the axis the cut position is measured along, so ``x`` takes a
    vertical cut at that x and returns intervals in y. The cut is a box of
    ``window_nm`` rather than a line, a line having no area to intersect, and
    the box is centred on the station. Two nanometres is two database units on
    a kit drawn at a nanometre grid.

    A slanted edge crossing the window makes the interval it returns uncertain
    by the window times the tangent of the slant, which on a taper of one part
    in a hundred is two hundredths of a nanometre.
    """
    ly, cell = open_layout(path)
    dbu = ly.dbu
    r = region(ly, cell, layer, datatype)
    if r.is_empty():
        return []
    b = r.bbox()
    p = int(round(position_um / dbu))
    # dbu is in micrometres, so the window is converted before it is divided
    h = max(1, int(round(window_nm * 1e-3 / 2.0 / dbu)))
    if axis == "x":
        box = kdb.Box(p - h, b.bottom - 1, p + h, b.top + 1)
    elif axis == "y":
        box = kdb.Box(b.left - 1, p - h, b.right + 1, p + h)
    else:
        raise ValueError("axis is 'x' or 'y'")

    pieces = r & kdb.Region(box)
    pieces.merge()
    spans = []
    for poly in pieces.each():
        pb = poly.bbox()
        if axis == "x":
            spans.append((pb.bottom * dbu, pb.top * dbu))
        else:
            spans.append((pb.left * dbu, pb.right * dbu))
    return sorted(spans)


def widths_and_gaps(spans: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
    """The material widths along a cut, and the clearances between them."""
    widths = [hi - lo for lo, hi in spans]
    gaps = [spans[i + 1][0] - spans[i][1] for i in range(len(spans) - 1)]
    return widths, gaps


def _parse_layer(text: str) -> tuple[int, int]:
    a, _, b = text.partition("/")
    return int(a), int(b or 0)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("gds")
    ap.add_argument("--cut", action="append", default=[],
                    help="a station, as x=12.5 or y=0. Repeatable")
    ap.add_argument("--layer", action="append", default=[],
                    help="restrict the cuts to this layer, as 2/10. Repeatable")
    ap.add_argument("--window-nm", type=float, default=2.0)
    a = ap.parse_args(argv[1:])

    layers = inventory(a.gds)
    print(f"{a.gds}\n")
    print(f"{'layer':>8} {'polygons':>9} {'area (um2)':>13}  bounding box (um)")
    for L in layers:
        x0, y0, x1, y1 = L.bbox_um
        print(f"{L.spec:>8} {L.polygons:9d} {L.area_um2:13.4f}  "
              f"({x0:.3f}, {y0:.3f}) to ({x1:.3f}, {y1:.3f})")

    wanted = [_parse_layer(s) for s in a.layer] or [(L.layer, L.datatype) for L in layers]
    for station in a.cut:
        axis, _, value = station.partition("=")
        pos = float(value)
        print(f"\ncut at {axis} = {pos} um")
        for spec in wanted:
            spans = cut(a.gds, spec[0], spec[1], axis, pos, a.window_nm)
            if not spans:
                continue
            widths, gaps = widths_and_gaps(spans)
            w = ", ".join(f"{v:.4f}" for v in widths)
            g = ", ".join(f"{v:.4f}" for v in gaps)
            print(f"  {spec[0]}/{spec[1]:<4} widths {w}" + (f"   gaps {g}" if gaps else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
