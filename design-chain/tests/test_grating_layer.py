"""The grating posts are drawn where the design says, and nowhere by default.

The posts were appended to the guide layer unconditionally, so a process that
reserves a layer for small repeating features could not be met. By the time a
layer map or a derived layer sees them they are the same polygons as the ridge,
and no later stage can separate what one list has merged.

LT-PRO reserves 2/11 for such features and draws the ridge on 2/10. LN-CORE has
no such layer and draws the ridge on 2/0, so the default leaves the posts where
they were and every mask already emitted is unchanged.
"""

from __future__ import annotations

import pytest

from picchain import preflight
from picchain.artifacts import RunContext
from picchain.config import Design
from picchain.stages import s05_layout

RIDGE = [2, 10]
PERIODIC = [2, 11]


def _design(grating_layer=None, with_map_entry=True) -> Design:
    layer_map = {
        "WG": RIDGE, "SLAB": [3, 10], "METAL": [20, 0], "PAD": [21, 0],
        "SEAL": [200, 0], "MARK": [201, 0], "DICE": [202, 0], "FACET": [203, 0],
        "ORIENT": [204, 0], "FILL": [205, 0], "LABEL": [4, 0],
        "FLOORPLAN": [206, 0], "CHIP_INNER": [6, 0], "CHIP_OUTER": [6, 1],
    }
    if with_map_entry:
        layer_map["RIDGE_PERIODIC"] = PERIODIC
    d = {
        "meta": {"name": "post_layer", "title": "Posts on their own layer"},
        "waveguide": {"top_width_um": 0.7, "wavelength_um": 1.31},
        "grating": {"enabled": True, "period_um": 0.4322, "length_um": 40.0},
        "layout": {"layer_map": layer_map},
    }
    if grating_layer is not None:
        d["layout"]["grating_layer"] = grating_layer
    return Design.model_validate(d)


def _polygons(tmp_path, design):
    ctx = RunContext(design_dir=tmp_path, run_id="posts").ensure()
    return s05_layout.build_polygons(design, ctx)


def _post_count(polys, layer, post_width_um=0.3):
    """Polygons of about the post's own size, counted off the geometry."""
    n = 0
    for p in polys.get(layer, []):
        xs = [x for x, _ in p]
        ys = [y for _, y in p]
        if (max(xs) - min(xs)) < 2.0 and 0.5 * post_width_um < (max(ys) - min(ys)) < 2.0:
            n += 1
    return n


def test_by_default_the_posts_stay_on_the_guide_layer(tmp_path):
    polys = _polygons(tmp_path, _design())
    assert _post_count(polys, "WG") > 0
    assert _post_count(polys, "RIDGE_PERIODIC") == 0


def test_a_named_layer_receives_every_post(tmp_path):
    d = _design(grating_layer="RIDGE_PERIODIC")
    polys = _polygons(tmp_path, d)
    moved = _post_count(polys, "RIDGE_PERIODIC")
    assert moved > 0
    # the same posts, and not a copy: the guide layer keeps none of them
    default = _post_count(_polygons(tmp_path, _design()), "WG")
    assert moved == default
    assert _post_count(polys, "WG") == 0


def test_the_guide_itself_stays_on_the_guide_layer(tmp_path):
    """Moving the posts must not move the ridge they sit beside."""
    d = _design(grating_layer="RIDGE_PERIODIC")
    polys = _polygons(tmp_path, d)
    assert len(polys["WG"]) > 0
    widths = [max(y for _, y in p) - min(y for _, y in p) for p in polys["WG"]]
    assert max(widths) >= 0.7


def test_a_layer_absent_from_the_map_is_refused_before_the_run():
    d = _design(grating_layer="RIDGE_PERIODIC", with_map_entry=False)
    findings = [f for f in preflight.run_checks(d)
                if f.check == "the_grating_layer_is_in_the_layer_map"]
    assert findings, "a name the map does not carry must be refused"
    assert "RIDGE_PERIODIC" in findings[0].detail


def test_a_layer_present_in_the_map_passes():
    d = _design(grating_layer="RIDGE_PERIODIC", with_map_entry=True)
    assert not [f for f in preflight.run_checks(d)
                if f.check == "the_grating_layer_is_in_the_layer_map"]
