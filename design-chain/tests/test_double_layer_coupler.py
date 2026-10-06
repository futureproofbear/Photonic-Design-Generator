"""The kit's double-layer edge coupler on the angled route, its slab-strip port,
and a facet placed on the outer chip boundary.

The LT-PRO kit reaches the outer chip boundary, which it labels the final chip
edge, with a strip of the slab layer across the exclusion zone, the ridge
confined to the contour. Until 2026-10-06 the chain could draw only a ridge
narrowed to a tip, ending at the contour, and solve the facet only on that tip.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from picchain.artifacts import RunContext
from picchain.config import Design, DoubleLayerCouplerCfg
from picchain.stages import s05_layout, s11_facet, s14_reticle

LAYER_MAP = {
    "WG": [2, 10], "SLAB": [3, 10], "SLAB_NEG": [3, 11], "METAL": [20, 0], "PAD": [20, 0],
    "SEAL": [300, 0], "MARK": [301, 0], "DICE": [302, 0], "FACET": [303, 0],
    "ORIENT": [304, 0], "FILL": [305, 0], "LABEL": [4, 0],
    "FLOORPLAN": [306, 0], "CHIP_INNER": [6, 0], "CHIP_OUTER": [6, 1],
}


def _design(**layout) -> Design:
    lay = {"layer_map": LAYER_MAP, "taper_tip_width_um": 0.26, "facet_route": "angled",
           "facet_bend_radius_um": 100.0, "input_facet_angle_deg": 13.36,
           "output_facet_angle_deg": 25.0, "draw_facets": True, "facet_recess_um": 5.0,
           "edge_coupler": "double_layer", "device_length_um": 2000.0}
    lay.update(layout)
    return Design.model_validate({
        "meta": {"name": "dlc", "title": "Double-layer coupler"},
        "waveguide": {"top_width_um": 0.9, "wavelength_um": 1.55},
        "grating": {"enabled": True, "period_um": 1.4, "length_um": 140.0},
        "cavity": {"enabled": True, "feed_length_um": 400.0},
        "layout": lay,
    })


def _polys(tmp_path, design):
    ctx = RunContext(design_dir=tmp_path, run_id="dlc").ensure()
    return s05_layout.build_polygons(design, ctx), ctx


def test_the_profiles_are_the_kits():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pdk"))
    try:
        from lxt_pdk_gf._utils import edge_couplers as kit
    except Exception:  # the kit is optional in a checkout
        pytest.skip("the open LT-PRO kit is not present")
    x = np.linspace(0.0, 1.0, 241)
    dl = DoubleLayerCouplerCfg()
    assert np.allclose(s05_layout._kit_lower(x, **dl.lower), kit._lin_lin_exp(x, **dl.lower))
    assert np.allclose(s05_layout._kit_upper(x, **dl.upper), kit._exp_growth(x, **dl.upper))


def test_the_coupler_is_drawn_on_three_layers_and_the_facets_are_reported(tmp_path):
    polys, ctx = _polys(tmp_path, _design())
    info = ctx.get("layout")
    assert info["facet_planes_um"] == [0.0, 2000.0]
    assert len(polys["SLAB_NEG"]) == 2
    dlr = info["double_layer"]
    assert dlr["port_width_um"] == pytest.approx(0.5)
    assert dlr["strip_beyond_facet_um"] == pytest.approx(5.0)
    # the ridge begins 85 um along the guide from the facet plane
    assert dlr["input_ridge_start_x_um"] == pytest.approx(85.0 * math.cos(math.radians(13.36)))
    # the ridge reaches no closer to either facet than its start
    xs = [x for p in polys["WG"] for x, _ in p]
    assert min(xs) >= dlr["input_ridge_start_x_um"] - 0.2
    assert max(xs) <= dlr["output_ridge_start_x_um"] + 0.2
    # the strip reaches past both facet planes
    sx = [x for p in polys["SLAB"] for x, _ in p]
    assert min(sx) < 0.0 and max(sx) > 2000.0


def test_the_band_meets_the_strip_without_an_acute_corner(tmp_path):
    polys, _ = _polys(tmp_path, _design())
    band = max(polys["SLAB"], key=lambda p: (max(y for _, y in p) - min(y for _, y in p)))
    pts = np.array(band)
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        u, v = a - b, c - b
        ang = math.degrees(math.acos(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))))
        assert ang >= 89.999, f"acute corner of {ang:.2f} degrees at {b}"


def test_the_facet_stage_solves_a_strip_port():
    src = Path(s11_facet.__file__).read_text(encoding="utf-8")
    assert "def _strip_cross_section(" in src
    assert 'getattr(cfg, "port", "ridge") == "slab_strip"' in src


def test_the_reticle_places_the_facet_plane_on_the_outer_boundary():
    src = Path(s14_reticle.__file__).read_text(encoding="utf-8")
    assert "facet_x = die_x0 - lane + (0.0 if facet_outer else ez_x)" in src
    assert "dev_dx = facet_x - float(_planes[0])" in src


def test_every_coupler_polygon_is_under_the_vertex_cap(tmp_path):
    """The kit's profiles are sampled densely, and drawn as one polygon each the
    ridge carried about 290 vertices and the strip 484, above the 200 the
    geometry check holds a polygon to (2026-10-06)."""
    polys, _ = _polys(tmp_path, _design())
    for layer in ("WG", "SLAB"):
        assert max(len(p) for p in polys[layer]) <= 200


def test_each_strip_merges_with_the_slab_band(tmp_path):
    """The strip and the band must be one piece of slab where the ridge hands
    over; a cut placed on o2 itself left a 1 nm gap at the output on
    2026-10-06, which no rule deck reads."""
    import klayout.db as kdb
    polys, _ = _polys(tmp_path, _design())
    r = kdb.Region()
    for p in polys["SLAB"]:
        r.insert(kdb.DPolygon([kdb.DPoint(x, y) for x, y in p]).to_itype(0.001))
    assert r.merged().count() == 1


def test_the_floor_plan_encloses_the_rotated_windows(tmp_path):
    """The rotated window reached past a floor plan stopped at the recess."""
    polys, _ = _polys(tmp_path, _design())
    fp = polys["FLOORPLAN"][0]
    fx = [x for x, _ in fp]
    for layer in ("SLAB_NEG", "SLAB", "WG"):
        for p in polys[layer]:
            assert min(x for x, _ in p) >= min(fx) - 1e-9
            assert max(x for x, _ in p) <= max(fx) + 1e-9


def test_the_strip_port_is_solved_on_a_converged_window_and_reports_its_margin():
    """Padded by 6 um, a 0.5 um strip at 1588 nm still carried a fifth of its
    field at the walls and read 1.27 dB where the converged figure is 2.10;
    each port now reports how far its mode sits above the cladding."""
    src = Path(s11_facet.__file__).read_text(encoding="utf-8")
    assert "window_pad_x_um=20.0, window_pad_y_um=18.0" in src
    assert '"guidance_margin": n_guide - _n_clad' in src
    assert 'key=f"facet.{label}_port_weakly_guided"' in src
