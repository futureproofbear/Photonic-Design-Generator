"""Every LTOI300 cell, measured off the polygons it writes.

Each study conducted on this kit rebuilt its geometry from the parameters the
builder declares. A difference between a builder's parameters and what the
layout engine draws from them is therefore untested, and it is the difference
the wafer would carry. Chain rule 11 requires a geometric parameter to be
measured back off the written file, and this applies the rule to the kit.

Every cell is built and written. Each declared quantity is then set against a
cut through the file at the station where that quantity is defined, taken by
[`tools/measure_layout.py`](../../../design-chain/tools/measure_layout.py). A
cut returns the intervals the material occupies, so a width, a gap and a port
separation are each read directly rather than inferred.

The tolerance is one nanometre, which is the database unit and the width the cut
window resolves on a slanted edge.

    python examples/ltoi300_mask/scripts/as_drawn.py [cell ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "tools"))
sys.path.insert(0, str(ROOT / "design-chain" / "pdk" / "lxt_pdk_gf"))

from measure_layout import cut, inventory, widths_and_gaps      # noqa: E402

GDS_DIR = Path(__file__).resolve().parents[1] / "runs" / "as_drawn"
RIDGE, SLAB, NEGATIVE, M1 = (2, 10), (3, 10), (3, 11), (20, 0)
TOL = 1.5e-3        # one nanometre, and the grid it is snapped to

#: Every check names the axis the station is measured along, the station, a
#: layer, and what the builder says should be found there. ``x`` takes a
#: vertical cut and reports intervals in y, which suits a device drawn along x;
#: ``y`` takes a horizontal one, which is how a ring with a vertical bus is
#: measured. ``kind`` selects the reading: ``widths`` the material intervals,
#: ``gaps`` the clearances between them, ``sep`` the first width plus the first
#: gap, ``span`` the extent along the cut, ``length`` the extent of the layer
#: along the axis the cut is taken across.
CHECKS: dict[str, list[tuple]] = {
    "straight_rwg700_oband": [
        ("guide width", "x", 5.0, RIDGE, "widths", [0.700]),
        ("slab width", "x", 5.0, SLAB, "widths", [12.700]),
        ("length", "x", None, RIDGE, "length", [10.000]),
    ],
    "straight_rwg900_cband": [
        ("guide width", "x", 5.0, RIDGE, "widths", [0.900]),
        ("length", "x", None, RIDGE, "length", [10.000]),
    ],
    "straight_rwg2500": [
        ("guide width", "x", 5.0, RIDGE, "widths", [2.500]),
        ("length", "x", None, RIDGE, "length", [10.000]),
    ],
    "mmi1x2_oband": [
        ("port width", "x", -24.999, RIDGE, "widths", [0.700]),
        ("taper at the face", "x", -0.001, RIDGE, "widths", [1.700]),
        ("section width", "x", 7.9, RIDGE, "widths", [4.500]),
        ("output tapers", "x", 15.801, RIDGE, "widths", [1.700, 1.700]),
        ("output gap", "x", 15.801, RIDGE, "gaps", [0.750]),
        ("port separation", "x", 15.801, RIDGE, "sep", [2.450]),
        ("total length", "x", None, RIDGE, "length", [65.800]),
    ],
    "mmi1x2_cband": [
        ("port width", "x", -24.999, RIDGE, "widths", [0.900]),
        ("taper at the face", "x", -0.001, RIDGE, "widths", [1.950]),
        ("section width", "x", 6.75, RIDGE, "widths", [4.500]),
        ("output gap", "x", 13.501, RIDGE, "gaps", [0.600]),
        ("port separation", "x", 13.501, RIDGE, "sep", [2.550]),
        ("total length", "x", None, RIDGE, "length", [63.500]),
    ],
    "mmi2x2_oband": [
        ("port width", "x", -25.0, RIDGE, "widths", [0.700, 0.700]),
        ("taper at the face", "x", -0.001, RIDGE, "widths", [1.750, 1.750]),
        ("input gap", "x", -0.001, RIDGE, "gaps", [2.150]),
        ("port separation", "x", -0.001, RIDGE, "sep", [3.900]),
        ("section width", "x", 48.75, RIDGE, "widths", [5.650]),
        ("total length", "x", None, RIDGE, "length", [147.500]),
    ],
    "mmi2x2_cband": [
        ("port width", "x", -25.0, RIDGE, "widths", [0.900, 0.900]),
        ("taper at the face", "x", -0.001, RIDGE, "widths", [1.500, 1.500]),
        ("input gap", "x", -0.001, RIDGE, "gaps", [2.150]),
        ("port separation", "x", -0.001, RIDGE, "sep", [3.650]),
        ("section width", "x", 33.75, RIDGE, "widths", [5.150]),
        ("total length", "x", None, RIDGE, "length", [117.500]),
    ],
    "ring_resonator_single_mode_point_coupler_oband": [
        ("ring and bus widths", "y", 0.0, RIDGE, "widths", [0.700, 0.700, 0.700]),
        ("coupler gap", "y", 0.0, RIDGE, "gaps", [399.300, 1.050]),
    ],
    "ring_resonator_single_mode_point_coupler_cband": [
        ("ring and bus widths", "y", 0.0, RIDGE, "widths", [0.900, 0.900, 0.900]),
        ("coupler gap", "y", 0.0, RIDGE, "gaps", [399.100, 1.500]),
    ],
    "ring_resonator_multimode_point_coupler_oband": [
        ("ring and bus widths", "y", 0.0, RIDGE, "widths", [1.500, 1.500, 0.700]),
        ("coupler gap", "y", 0.0, RIDGE, "gaps", [398.500, 0.750]),
    ],
    "ring_resonator_multimode_point_coupler_cband": [
        ("ring and bus widths", "y", 0.0, RIDGE, "widths", [1.500, 1.500, 0.900]),
        ("coupler gap", "y", 0.0, RIDGE, "gaps", [398.500, 1.200]),
    ],
    "edge_coupler_oband": [
        ("slab tip", "x", 0.0, SLAB, "widths", [0.350]),
        ("ridge tip", "x", 80.001, RIDGE, "widths", [0.250]),
        ("ridge at the output", "x", 159.999, RIDGE, "widths", [0.700]),
        ("slab at the output", "x", 159.999, SLAB, "widths", [5.600]),
        ("slab clearance window", "x", 80.0, NEGATIVE, "widths", [20.000]),
        ("ridge run", "x", None, RIDGE, "length", [80.000]),
    ],
    "edge_coupler_cband": [
        ("slab tip", "x", 0.0, SLAB, "widths", [0.500]),
        ("ridge tip", "x", 80.001, RIDGE, "widths", [0.250]),
        ("ridge at the output", "x", 159.999, RIDGE, "widths", [0.900]),
        ("slab at the output", "x", 159.999, SLAB, "widths", [5.600]),
        ("slab clearance window", "x", 80.0, NEGATIVE, "widths", [20.000]),
        ("ridge run", "x", None, RIDGE, "length", [80.000]),
    ],
    "terminated_eo_phase_shifter_oband": [
        ("signal on the rail", "x", 1000.0, M1, "widths", [50.0, 20.0, 50.0]),
        ("gap on the rail", "x", 1000.0, M1, "gaps", [5.500, 5.500]),
        ("signal in the cut", "x", 2500.0, M1, "widths", [45.0, 10.0, 45.0]),
        ("gap in the cut", "x", 2500.0, M1, "gaps", [15.500, 15.500]),
        ("guide in the gap", "x", 1000.0, RIDGE, "widths", [2.500]),
    ],
    "unterminated_eo_phase_shifter_oband": [
        ("signal on the rail", "x", 1000.0, M1, "widths", [50.0, 20.0, 50.0]),
        ("gap on the rail", "x", 1000.0, M1, "gaps", [5.500, 5.500]),
        ("signal in the cut", "x", 2500.0, M1, "widths", [45.0, 10.0, 45.0]),
        ("gap in the cut", "x", 2500.0, M1, "gaps", [15.500, 15.500]),
    ],
    "terminated_eo_phase_shifter_cband": [
        ("signal on the rail", "x", 1000.0, M1, "widths", [50.0, 16.0, 50.0]),
        ("gap on the rail", "x", 1000.0, M1, "gaps", [5.500, 5.500]),
        ("signal in the cut", "x", 2500.0, M1, "widths", [47.0, 10.0, 47.0]),
        ("gap in the cut", "x", 2500.0, M1, "gaps", [11.500, 11.500]),
    ],
    "unterminated_eo_phase_shifter_cband": [
        ("signal on the rail", "x", 1000.0, M1, "widths", [50.0, 16.0, 50.0]),
        ("gap on the rail", "x", 1000.0, M1, "gaps", [5.500, 5.500]),
        ("signal in the cut", "x", 2500.0, M1, "widths", [47.0, 10.0, 47.0]),
        ("gap in the cut", "x", 2500.0, M1, "gaps", [11.500, 11.500]),
    ],
}

#: The terminated cells carry a resistor on the high-resistance layer beyond the
#: far end of the signal metal, and the unterminated ones stop the layer short of
#: it. Presence of the layer settles nothing on an interferometer, whose bias
#: heater is drawn on the same layer at the input end and accounts for 94213 of
#: the 97125 square micrometres a terminated cell carries. The discriminator is
#: therefore the reach of the layer past the end of the line, and the resistor it
#: finds there is 2911.9 square micrometres on the O-band cells and 2815.9 on the
#: C-band ones.
#:
#: That one polygon is the whole physical difference between the two variants,
#: and it is what `electrodes.far_end_load_ohm` states to the chain. The kit
#: declares the resistor 58.112 um long and 1.5 um wide and declares no sheet
#: resistance for the layer, so its value cannot be computed from the kit and a
#: terminated cell is taken as matched by declaration.
HR_LAYER = (23, 0)
LINE_LAYER = (20, 0)
TERMINATION = {
    "terminated_eo_phase_shifter_oband": True,
    "terminated_eo_phase_shifter_cband": True,
    "unterminated_eo_phase_shifter_oband": False,
    "unterminated_eo_phase_shifter_cband": False,
    "terminated_mzm_1x2mmi_oband": True,
    "terminated_mzm_2x2mmi_oband": True,
    "terminated_mzm_1x2mmi_cband": True,
    "terminated_mzm_2x2mmi_cband": True,
    "unterminated_mzm_1x2mmi_oband": False,
    "unterminated_mzm_2x2mmi_oband": False,
    "unterminated_mzm_1x2mmi_cband": False,
    "unterminated_mzm_2x2mmi_cband": False,
}


def emit(cell: str) -> Path:
    path = GDS_DIR / f"{cell}.gds"
    if path.exists():
        return path
    import ltoi300
    from ltoi300 import cells

    ltoi300.PDK.activate()
    GDS_DIR.mkdir(parents=True, exist_ok=True)
    getattr(cells, cell)().write_gds(str(path))
    return path


def read(gds: Path, axis, station, layer, kind) -> list[float]:
    if kind == "length":
        inv = {L.spec: L for L in inventory(str(gds))}
        L = inv.get(f"{layer[0]}/{layer[1]}")
        if L is None:
            return []
        return [L.bbox_um[2] - L.bbox_um[0] if axis == "x"
                else L.bbox_um[3] - L.bbox_um[1]]
    spans = cut(str(gds), *layer, axis, float(station))
    widths, gaps = widths_and_gaps(spans)
    if kind == "widths":
        return widths
    if kind == "gaps":
        return gaps
    if kind == "sep":
        return [widths[0] + gaps[0]] if gaps else []
    if kind == "span":
        return [spans[-1][1] - spans[0][0]] if spans else []
    raise ValueError(kind)


def main(argv: list[str]) -> int:
    wanted = argv[1:] or list(CHECKS)
    bad = 0
    for cell in wanted:
        gds = emit(cell)
        print(f"\n{cell}")
        for name, axis, station, layer, kind, expect in CHECKS[cell]:
            got = read(gds, axis, station, layer, kind)
            ok = (len(got) == len(expect)
                  and all(abs(g - e) <= TOL for g, e in zip(got, expect)))
            mark = "  " if ok else "**"
            where = ("the whole cell" if station is None
                     else f"{axis} = {station:g} um")
            print(f"{mark} {name:24} {where:>18}  "
                  f"drawn {[round(v, 4) for v in got]}  declared {expect}")
            bad += 0 if ok else 1

    print()
    for cell, terminated in TERMINATION.items():
        if argv[1:] and cell not in wanted:
            continue
        gds = emit(cell)
        inv = {L.spec: L for L in inventory(str(gds))}
        hr = inv.get(f"{HR_LAYER[0]}/{HR_LAYER[1]}")
        line = inv.get(f"{LINE_LAYER[0]}/{LINE_LAYER[1]}")
        reaches = (hr is not None and line is not None
                   and hr.bbox_um[2] > line.bbox_um[2])
        ok = reaches == terminated
        if hr is None or line is None:
            where = "the layer holds no polygon at all"
        elif reaches:
            where = (f"the layer reaches {hr.bbox_um[2]:.1f} um and the line ends "
                     f"at {line.bbox_um[2]:.1f}")
        else:
            where = (f"the layer stops at {hr.bbox_um[2]:.1f} um, short of a line "
                     f"ending at {line.bbox_um[2]:.1f}")
        print(f"{'  ' if ok else '**'} {cell:40} "
              f"{'terminated' if reaches else 'open':<11} {where}")
        bad += 0 if ok else 1

    print(f"\n{bad} quantities differ from what the builder declares")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
