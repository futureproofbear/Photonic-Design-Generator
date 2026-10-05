"""The output end of a laser is drawn to a declared device length, meets its
own facet at an angle under the angled route, carries its tip to the cell edge,
and the heater's landings sit clear of the electrodes.

Until 2026-10-06 the output taper was a four-point trapezoid that followed the
grating immediately and ended square, whatever the route; a device could not be
made to span a die; the taper tip stopped 5 um short of the chip contour the
process forms the facet at; and the heater's landings were drawn on the phase
electrode's metal, 1200 um2 of overlap per cell, which the process's own rule
(HRL to M1 separation 1.0 um) refuses.
"""

from __future__ import annotations

import math
from pathlib import Path

from picchain import monitors
from picchain.artifacts import RunContext
from picchain.config import Design
from picchain.stages import s05_layout, s11_facet

LAYER_MAP = {
    "WG": [2, 10], "SLAB": [3, 10], "METAL": [20, 0], "PAD": [20, 0],
    "HEATER": [23, 0], "M2": [22, 0], "VIA_M2_HRL": [41, 0],
    "SEAL": [300, 0], "MARK": [301, 0], "DICE": [302, 0], "FACET": [303, 0],
    "ORIENT": [304, 0], "FILL": [305, 0], "LABEL": [4, 0],
    "FLOORPLAN": [306, 0], "CHIP_INNER": [6, 0], "CHIP_OUTER": [6, 1],
}


def _design(**layout) -> Design:
    lay = {"layer_map": LAYER_MAP, "taper_length_um": 100.0, "taper_tip_width_um": 0.3,
           "facet_route": "angled", "facet_bend_radius_um": 100.0,
           "input_facet_angle_deg": 10.0, "draw_facets": True, "facet_recess_um": 5.0}
    lay.update(layout)
    d = {
        "meta": {"name": "outport", "title": "The output port"},
        "waveguide": {"top_width_um": 0.9, "wavelength_um": 1.55},
        "grating": {"enabled": True, "period_um": 1.4, "length_um": 140.0},
        "cavity": {"enabled": True, "feed_length_um": 300.0,
                   "phase_section": {"enabled": True, "length_um": 200.0, "gap_um": 4.8,
                                     "width_um": 20.0},
                   "phase_trimmer": {"enabled": True, "length_um": 200.0, "width_um": 1.5,
                                     "over": "phase_section", "pad_clearance_um": 30.0}},
        "layout": lay,
    }
    return Design.model_validate(d)


def _polys(tmp_path, design):
    ctx = RunContext(design_dir=tmp_path, run_id="outport").ensure()
    return s05_layout.build_polygons(design, ctx), ctx


def _xmax(polys, layer):
    return max(x for p in polys[layer] for x, _ in p)


def _xmin(polys, layer):
    return min(x for p in polys[layer] for x, _ in p)


def test_the_device_is_drawn_to_the_declared_length(tmp_path):
    polys, ctx = _polys(tmp_path, _design(device_length_um=2000.0))
    info = ctx.get("layout")
    assert abs(info["device_length_um"] - 2000.0) < 1e-6
    assert info["output_lead_um"] > 0
    # the ridge reaches the output facet plane and, with the tip carried to
    # the edge switched off, stops there
    assert abs(_xmax(polys, "WG") - 2000.0) < 1e-3


def test_a_length_the_device_already_exceeds_is_refused(tmp_path):
    import pytest
    with pytest.raises(RuntimeError, match="device_length_um"):
        _polys(tmp_path, _design(device_length_um=400.0))


def test_the_output_meets_its_facet_at_the_declared_angle(tmp_path):
    polys, ctx = _polys(tmp_path, _design(device_length_um=2000.0, output_facet_angle_deg=10.0))
    info = ctx.get("layout")
    assert info["output_route"] == "angled"
    # the same lateral excursion as the input, on the same side of the axis
    assert abs(info["facet_lead_out_excursion_um"] - info["facet_lead_in_excursion_um"]) < 1e-6
    ys = [y for p in polys["WG"] for x, y in p if x > 1999.0]
    assert min(ys) < -info["facet_lead_out_excursion_um"] + 1.0
    # and the facet band at that end is square to the die edge: the angle is
    # carried by the guide, so the band's edges are axis-aligned
    out_faces = [p for p in polys["FACET"] if min(x for x, _ in p) > 1990.0]
    assert out_faces
    xs = {round(x, 6) for p in out_faces for x, _ in p}
    assert xs <= {2000.0, 2000.5, 2005.0}


def test_the_tip_is_carried_to_the_cell_edge_when_asked(tmp_path):
    polys, ctx = _polys(tmp_path, _design(device_length_um=2000.0, output_facet_angle_deg=10.0,
                                          facet_tip_to_edge=True, facet_slab_extension_um=10.0))
    info = ctx.get("layout")
    assert info["cell_edges_um"] == [-5.0, 2005.0]
    assert abs(_xmin(polys, "WG") + 5.0) < 1e-6
    assert abs(_xmax(polys, "WG") - 2005.0) < 1e-6
    # the slab follows the guide past the contour by the declared extension
    assert abs(_xmin(polys, "SLAB") + 15.0) < 1e-6
    assert abs(_xmax(polys, "SLAB") - 2015.0) < 1e-6
    # the extension keeps the tip's width: cut square to the die edge, a guide
    # meeting it at 10 degrees presents its width divided by cos(10 deg)
    end = [p for p in polys["WG"] if max(x for x, _ in p) > 2004.9][0]
    edge_pts = [y for x, y in end if abs(x - 2005.0) < 1e-6]
    assert abs(abs(edge_pts[0] - edge_pts[1]) - 0.3 / math.cos(math.radians(10.0))) < 1e-6


def test_the_heater_landings_are_clear_of_the_electrode_metal(tmp_path):
    polys, ctx = _polys(tmp_path, _design(device_length_um=2000.0))
    import klayout.db as db

    def region(layer):
        r = db.Region()
        for p in polys[layer]:
            r.insert(db.DPolygon([db.DPoint(x, y) for x, y in p]).to_itype(0.001))
        return r

    hrl, m1 = region("HEATER"), region("METAL") + region("PAD")
    assert (hrl & m1).area() == 0
    assert hrl.separation_check(m1, 1000).count() == 0
    term = ctx.get("layout")["phase_trimmer"]["terminals"]
    assert term["m2_and_via"] is True
    assert len(polys["M2"]) == 2 and len(polys["VIA_M2_HRL"]) == 2
    # each opening lies inside its pad on both layers, inset by the declared amount
    via, m2 = region("VIA_M2_HRL"), region("M2")
    assert (via - m2).is_empty() and (via - hrl).is_empty()
    assert m2.enclosing_check(via, 2499).count() == 0


def test_without_a_clearance_the_old_landings_are_drawn(tmp_path):
    d = _design(device_length_um=2000.0)
    d.cavity.phase_trimmer.pad_clearance_um = None
    polys, ctx = _polys(tmp_path, d)
    assert ctx.get("layout")["phase_trimmer"]["terminals"]["m2_and_via"] is False
    assert not polys["M2"]


def test_the_seal_ring_opens_on_the_right_where_asked():
    bars = monitors.seal_ring(x0=0.0, y0=0.0, x1=100.0, y1=100.0, width_um=5.0,
                              left_openings=[(40.0, 60.0)], right_openings=[(40.0, 60.0)])
    right = [b for b in bars if min(x for x, _ in b) >= 95.0 - 1e-9]
    ys = sorted((min(y for _, y in b), max(y for _, y in b)) for b in right)
    assert ys == [(0.0, 40.0), (60.0, 100.0)]
    closed = monitors.seal_ring(x0=0.0, y0=0.0, x1=100.0, y1=100.0, width_um=5.0,
                                left_openings=[(40.0, 60.0)])
    right = [b for b in closed if min(x for x, _ in b) >= 95.0 - 1e-9]
    assert len(right) == 1


def test_the_facet_stage_evaluates_the_output_port_and_the_reflection():
    src = Path(s11_facet.__file__).read_text(encoding="utf-8")
    assert "def _port(" in src
    assert 'payload["output"] = _port(' in src
    for key in ("reflection_into_guide", "tilt_suppression_dB", "face_reflectivity_bare"):
        assert f'"{key}"' in src
    # the output's own warning names the feedback, which no cavity row grades
    assert 'key="facet.output_feedback"' in src
