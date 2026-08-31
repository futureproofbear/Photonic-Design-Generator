"""The items a mask needs before it can be sent anywhere.

Each test states the property the emitted data must have and measures it off
the written file, rather than off the parameters that produced it. Several of
these check that a declared quantity actually reaches a polygon, which is the
failure mode the group was written for: a facet angle that fed a coupling
calculation and drew nothing.
"""

from __future__ import annotations

import math

import klayout.db as db
import pytest

from picchain.artifacts import RunContext
from picchain.config import Design, DRCRule, get_dotted, set_dotted
from picchain.stages import s05_layout, s06_drc, s14_reticle

DBU = 0.001


def _design(**layout_kw):
    d = Design(
        meta={"name": "f"},
        grating={"period_um": 1.28, "length_um": 128.0},
        layout={"draw_periods": 10, **layout_kw},
    )
    d.drc.rules = [
        DRCRule(name="WG_min_width", kind="min_width", layer="WG", value_um=0.20,
                ignore_angle_deg=80.0),
        DRCRule(name="WG_min_space", kind="min_space", layer="WG", value_um=0.30),
        DRCRule(name="METAL_to_WG", kind="min_separation", layer="METAL",
                other_layer="WG", value_um=2.0),
    ]
    return d


def _run_layout(d, tmp_path, tag="r"):
    ctx = RunContext(design_dir=tmp_path, run_id=tag).ensure()
    return ctx, s05_layout.run(d, ctx, None)


def _region(gds, layer):
    ly = db.Layout()
    ly.read(str(gds))
    return db.Region(ly.top_cell().begin_shapes_rec(ly.layer(*layer))).merged()


def _tip_shear(gds, d) -> float:
    """Longitudinal spread of the two vertices forming the input end face.

    A square end puts both at the same x; an angled one separates them by twice
    the shear. Measured off the written file rather than off the parameters.
    """
    wg = _region(gds, d.layout.layer_map["WG"])
    tip = min(wg.each(), key=lambda p: p.bbox().left)
    xs = sorted(pt.x * DBU for pt in tip.each_point_hull())
    return xs[1] - xs[0]


# --------------------------------------------------------------------------
# 1. the facet is drawn, not merely declared
# --------------------------------------------------------------------------
def test_the_facet_angle_reaches_a_polygon(tmp_path):
    """It did not. The angle fed the coupling calculation and the emitted guide
    had square ends, so the angle suppressed no reflection."""
    d = _design()
    d.layout.input_facet_angle_deg = 8.0
    _, payload = _run_layout(d, tmp_path)
    shear = 0.5 * d.layout.taper_tip_width_um * math.tan(math.radians(8.0))
    assert _tip_shear(payload["gds"], d) == pytest.approx(2 * shear, abs=2e-3), \
        "the tip end face is square; the angle did not reach the polygon"


def test_a_zero_angle_leaves_the_end_square(tmp_path):
    d = _design()
    d.layout.input_facet_angle_deg = 0.0
    _, payload = _run_layout(d, tmp_path)
    assert _tip_shear(payload["gds"], d) == pytest.approx(0.0, abs=1e-6)


def test_the_facet_plane_and_its_recess_are_drawn(tmp_path):
    """The band the cleave or the polish removes is marked, so that nothing is
    placed where it will be destroyed."""
    d = _design()
    _, payload = _run_layout(d, tmp_path)
    facet = _region(payload["gds"], d.layout.layer_map["FACET"])
    assert facet.count() >= 2, "no facet plane was drawn"
    assert facet.area() * DBU * DBU > 0


def test_facets_can_be_switched_off_and_the_omission_is_reported(tmp_path):
    d = _design(draw_facets=False)
    ctx, payload = _run_layout(d, tmp_path)
    assert not _region(payload["gds"], d.layout.layer_map["FACET"]).count()
    assert any("facets are not drawn" in w for w in ctx.warnings)


# --------------------------------------------------------------------------
# 2. the manufacturing grid
# --------------------------------------------------------------------------
@pytest.mark.parametrize("grid_nm", [1.0, 5.0, 10.0])
def test_every_vertex_lands_on_the_declared_grid(tmp_path, grid_nm):
    """Data off the grid is either refused by the foundry or snapped without
    notice. Snapping here makes the emitted mask the one that will be printed."""
    d = _design()
    d.process.grid_nm = grid_nm
    _, payload = _run_layout(d, tmp_path, tag=f"g{grid_nm}")

    ly = db.Layout()
    ly.read(payload["gds"])
    step = int(round(grid_nm))
    for name, layer in d.layout.layer_map.items():
        idx = ly.find_layer(*layer)
        if idx is None:
            continue
        region = db.Region(ly.top_cell().begin_shapes_rec(idx))
        assert region.grid_check(step, step).count() == 0, f"{name} is off the grid"


def test_the_snap_reports_what_it_cost(tmp_path):
    d = _design()
    d.process.grid_nm = 10.0
    _, payload = _run_layout(d, tmp_path)
    grid = payload["grid"]
    assert grid["grid_nm"] == 10.0
    assert grid["vertices"] > 0
    # Half a grid step per axis, so the Euclidean displacement of a vertex that
    # moves on both is sqrt(2)/2 of a step. That bound was written as half a
    # step, which holds only while every polygon is rectilinear: a quadratic
    # facet taper's vertices sit off-grid in x and y at once and reach 6.25 nm
    # on a 10 nm grid.
    assert 0.0 < grid["max_displacement_nm"] <= 5.0 * math.sqrt(2.0) + 1e-9


def test_a_snap_beyond_the_declared_limit_is_refused(tmp_path):
    d = _design()
    d.process.grid_nm = 50.0
    d.process.max_snap_displacement_nm = 5.0
    ctx = RunContext(design_dir=tmp_path, run_id="lim").ensure()
    with pytest.raises(RuntimeError, match="max_snap_displacement_nm"):
        s05_layout.run(d, ctx, None)


def test_the_period_dither_is_computed_from_the_grid():
    """A post at k times the period lands on the nearest grid point, so a period
    that is not an integer number of steps walks. Over several thousand periods
    that is a distortion of the Bragg condition."""
    on = s05_layout.period_dither(1.280, 500, 10.0)
    assert on["period_on_grid"] is True
    assert on["period_dither_nm_rms"] == pytest.approx(0.0, abs=1e-9)

    off = s05_layout.period_dither(1.27979, 500, 10.0)
    assert off["period_on_grid"] is False
    assert 0.0 < off["period_dither_nm_rms"] < 5.0
    assert off["period_dither_nm_max"] <= 5.0 + 1e-9


def test_a_finer_grid_dithers_the_period_less():
    coarse = s05_layout.period_dither(1.27979, 400, 10.0)["period_dither_nm_rms"]
    fine = s05_layout.period_dither(1.27979, 400, 1.0)["period_dither_nm_rms"]
    assert fine < coarse


# --------------------------------------------------------------------------
# 3. the split ladder
# --------------------------------------------------------------------------
def _die(tmp_path, values, **split_kw):
    d = _design()
    d.reticle.enabled = True
    d.reticle.monitors.enabled = False
    d.reticle.split.enabled = True
    d.reticle.split.values = values
    for k, v in split_kw.items():
        setattr(d.reticle.split, k, v)
    ctx = RunContext(design_dir=tmp_path, run_id="die").ensure()
    s05_layout.run(d, ctx, None)
    return d, ctx, s14_reticle.run(d, ctx, None)


def test_the_ladder_draws_one_copy_per_value(tmp_path):
    values = [0.60, 0.66, 0.72]
    d, _, payload = _die(tmp_path, values)
    assert payload["split"]["copies"] == len(values)
    assert payload["devices_on_die"] == len(values) + 1
    assert [r["value"] for r in payload["split"]["rows"]] == values


def test_each_copy_carries_the_geometry_its_value_implies(tmp_path):
    """A ladder whose copies are identical brackets nothing. The gap is measured
    back off the polygons of each cell."""
    d, _, payload = _die(tmp_path, [0.60, 0.72])
    ly = db.Layout()
    ly.read(payload["gds"])
    wg_layer = d.layout.layer_map["WG"]
    measured = []
    for row in payload["split"]["rows"]:
        cell = ly.cell(row["cell"])
        region = db.Region(cell.begin_shapes_rec(ly.layer(*wg_layer)))
        posts = [p for p in region.each() if p.bbox().width() * DBU < 0.5]
        assert posts, f"no posts in {row['cell']}"
        inner = min(p.bbox().bottom * DBU for p in posts if p.bbox().bottom > 0)
        measured.append(round(inner - d.waveguide.top_width_um / 2, 4))
    assert measured == [0.60, 0.72]


def test_the_ladder_widens_the_electrode_where_the_rule_requires_it(tmp_path):
    """Opening the post gap moves the posts toward the electrodes, so the
    weak-coupling end of the ladder walks into the metal-to-guide rule. That is
    the end the ladder exists to reach."""
    d, _, payload = _die(tmp_path, [0.63, 0.90])
    rows = payload["split"]["rows"]
    assert rows[0]["electrode_gap_widened_to_um"] is None
    assert rows[1]["electrode_gap_widened_to_um"] is not None
    # the widened gap clears the rule with the posts at their new position
    need = 2 * (d.waveguide.top_width_um / 2 + 0.90 + d.grating.post_width_um + 2.0)
    assert rows[1]["electrode_gap_widened_to_um"] == pytest.approx(need, abs=1e-3)


def test_the_die_carrying_a_ladder_still_passes_the_rules(tmp_path):
    d, ctx, payload = _die(tmp_path, [0.60, 0.66, 0.72, 0.90])
    d.drc.target = "die"
    result = s06_drc.run(d, ctx, None)
    assert result["checked"] == "die"
    assert result["error_violations"] == 0, result["results"]


# --------------------------------------------------------------------------
# 4. the crystal orientation
# --------------------------------------------------------------------------
def test_the_orientation_key_is_drawn_and_the_axis_reported(tmp_path):
    d = _design()
    _, payload = _run_layout(d, tmp_path)
    assert _region(payload["gds"], d.layout.layer_map["ORIENT"]).count() >= 1
    orient = payload["orientation"]
    assert orient["cut"] == "x"
    assert orient["eo_coefficient"] == "r33"
    assert "c-axis" in orient["required_axis"]


def test_a_declared_misalignment_is_reported(tmp_path):
    d = _design()
    d.layout.crystal_misalignment_deg = 15.0
    ctx, _ = _run_layout(d, tmp_path)
    assert any("from the crystal axis" in w for w in ctx.warnings)


def test_omitting_the_key_is_reported(tmp_path):
    d = _design(draw_orientation_key=False)
    ctx, _ = _run_layout(d, tmp_path)
    assert any("no orientation key" in w for w in ctx.warnings)


# --------------------------------------------------------------------------
# 5. geometry, formats and the layer table
# --------------------------------------------------------------------------
def test_the_emitted_device_is_geometrically_sound(tmp_path):
    d = _design()
    _, payload = _run_layout(d, tmp_path)
    geo = payload["geometry"]
    assert geo["performed"] and geo["clean"], geo


def test_a_self_intersecting_polygon_is_detected(tmp_path):
    """Legal to a width rule and to a spacing rule, and it does not survive
    mask fracture."""
    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell("T")
    bowtie = db.DPolygon([db.DPoint(0, 0), db.DPoint(10, 10),
                          db.DPoint(0, 10), db.DPoint(10, 0)])
    top.shapes(ly.layer(1, 0)).insert(bowtie)
    path = tmp_path / "bad.gds"
    ly.write(str(path))

    result = s05_layout.check_geometry(path, {"WG": [1, 0]},
                                       min_angle_deg=0.0, max_vertices=0)
    assert result["by_layer"]["WG"]["strange_polygons"] > 0
    assert not result["clean"]


def test_an_acute_corner_is_detected(tmp_path):
    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell("T")
    wedge = db.DPolygon([db.DPoint(0, 0), db.DPoint(50, 1), db.DPoint(50, -1)])
    top.shapes(ly.layer(1, 0)).insert(wedge)
    path = tmp_path / "wedge.gds"
    ly.write(str(path))

    result = s05_layout.check_geometry(path, {"WG": [1, 0]},
                                       min_angle_deg=30.0, max_vertices=0)
    entry = result["by_layer"]["WG"]
    assert entry["acute_corners"] == 1
    assert entry["min_interior_angle_deg"] < 5.0


def test_a_vertex_cap_is_enforced(tmp_path):
    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell("T")
    pts = [db.DPoint(50 * math.cos(t * 2 * math.pi / 64),
                     50 * math.sin(t * 2 * math.pi / 64)) for t in range(64)]
    top.shapes(ly.layer(1, 0)).insert(db.DPolygon(pts))
    path = tmp_path / "circle.gds"
    ly.write(str(path))

    ok = s05_layout.check_geometry(path, {"WG": [1, 0]},
                                   min_angle_deg=0.0, max_vertices=200)
    tight = s05_layout.check_geometry(path, {"WG": [1, 0]},
                                      min_angle_deg=0.0, max_vertices=32)
    assert ok["by_layer"]["WG"]["over_vertex_cap"] == 0
    assert tight["by_layer"]["WG"]["over_vertex_cap"] == 1


def test_oasis_is_written_and_carries_the_same_geometry(tmp_path):
    """A mask in one format only is a mask a recipient may not be able to read."""
    d = _design()
    _, payload = _run_layout(d, tmp_path)
    assert payload["oasis"] and payload["oasis"].endswith(".oas")
    for layer in ("WG", "METAL"):
        a = _region(payload["gds"], d.layout.layer_map[layer])
        b = _region(payload["oasis"], d.layout.layer_map[layer])
        assert (a ^ b).area() == 0, f"{layer} differs between the two formats"


def test_the_layer_table_is_written_and_lists_every_layer(tmp_path):
    d = _design()
    ctx, payload = _run_layout(d, tmp_path)
    table = ctx.run_dir / "f.layermap.txt"
    lyp = ctx.run_dir / "f.lyp"
    assert table.exists() and lyp.exists()
    text = table.read_text(encoding="utf-8")
    for name, (num, dt) in d.layout.layer_map.items():
        assert f"{name}, {num}, {dt}" in text
    assert "<layer-properties>" in lyp.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# 6. the rule that the facet angle interacts with
# --------------------------------------------------------------------------
def test_an_angled_facet_needs_the_corner_threshold_set(tmp_path):
    """Every convex corner brings two edges arbitrarily close together, so a
    width check reports the corner itself unless a threshold is given. An 8
    degree facet necessarily produces an 82 degree corner, and the engine
    default of 90 degrees reports it."""
    d = _design()
    d.layout.input_facet_angle_deg = 8.0
    ctx, _ = _run_layout(d, tmp_path)

    d.drc.rules = [DRCRule(name="w", kind="min_width", layer="WG", value_um=0.20,
                           ignore_angle_deg=90.0)]
    assert s06_drc.run(d, ctx, None)["error_violations"] > 0

    d.drc.rules = [DRCRule(name="w", kind="min_width", layer="WG", value_um=0.20,
                           ignore_angle_deg=80.0)]
    assert s06_drc.run(d, ctx, None)["error_violations"] == 0


# --------------------------------------------------------------------------
# 7. the dotted-path helpers the split and the corner study share
# --------------------------------------------------------------------------
def test_dotted_access_reaches_attributes_and_mapping_keys():
    d = _design()
    assert get_dotted(d, "grating.post_gap_um") == pytest.approx(0.63)
    set_dotted(d, "grating.post_gap_um", 0.70)
    assert d.grating.post_gap_um == pytest.approx(0.70)
    set_dotted(d, "process.bias_um.WG", 0.04)
    assert d.process.bias_um == {"WG": 0.04}


# --------------------------------------------------------------------------
# 5. how the guide reaches the end face
#
# The angle exists to steer the facet reflection out of the guide, and it may be
# obtained two ways. Under `sheared` the guides stay parallel and the whole array
# is diced at the angle. Under `angled` the die edge is perpendicular and each
# guide is routed to meet it at the angle. The tests below hold the properties
# that distinguish them, each measured off the written file.
# --------------------------------------------------------------------------
def _lead_polygon(gds, d):
    """The polygon carrying the input end face, as drawn."""
    wg = _region(gds, d.layout.layer_map["WG"])
    return min(wg.each(), key=lambda p: p.bbox().left)


def _input_facet_band(gds, d):
    """The facet plane and its recess at the input end, merged as drawn."""
    face = _region(gds, d.layout.layer_map["FACET"])
    return min(face.each(), key=lambda p: p.bbox().left)


def test_the_angled_route_carries_the_guide_off_the_die_axis(tmp_path):
    """The distinguishing cost of a perpendicular die edge.

    A sheared end face needs no lateral excursion. Routing the guide to meet a
    perpendicular edge does, and the device pitch has to carry it.
    """
    sh = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="sheared")
    an = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled",
                 facet_bend_radius_um=500.0)
    _, m_sh = _run_layout(sh, tmp_path, "sh")
    _, m_an = _run_layout(an, tmp_path, "an")

    assert m_sh["facet_lead_in_excursion_um"] == 0.0
    assert m_an["facet_lead_in_excursion_um"] > 20.0

    # and it is on the mask, not merely in the payload
    y_sh = _lead_polygon(m_sh["gds"], sh).bbox().height() * DBU
    y_an = _lead_polygon(m_an["gds"], an).bbox().height() * DBU
    assert y_an > y_sh + 20.0


def test_the_angled_route_leaves_the_die_edge_square(tmp_path):
    """The angle is carried by the guide, so it must not also shear the face.

    Applying it in both places would angle the end face of a guide that already
    meets it at the angle, which is the angle applied twice.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled")
    _, m = _run_layout(d, tmp_path)
    band = _input_facet_band(m["gds"], d)
    # the plane and the recess merge into one band, 5 um deep by declaration.
    # A square band spans exactly that in z; a sheared one spans more.
    assert band.bbox().width() * DBU == pytest.approx(5.0, abs=0.01)


def test_the_sheared_route_still_shears_the_face(tmp_path):
    """The converse, so the test above cannot pass by drawing nothing.

    Across a 30 um keep-out an 8 degree face spans 4.2 um in z, so a sheared band
    is measurably wider in z than the 5 um recess it carries.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="sheared")
    _, m = _run_layout(d, tmp_path)
    band = _input_facet_band(m["gds"], d)
    assert band.bbox().width() * DBU > 8.0


def test_the_routed_guide_arrives_on_the_die_axis(tmp_path):
    """Nothing downstream of the lead-in may move.

    The route is displaced so that it lands on the axis where the feed begins. A
    lead-in ending off-axis would leave a step at the joint, which is a
    reflection and which no rule deck reports.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled")
    _, m = _run_layout(d, tmp_path)
    lead = _lead_polygon(m["gds"], d)
    far = max(pt.x for pt in lead.each_point_hull())
    ys = [pt.y * DBU for pt in lead.each_point_hull()
          if abs(pt.x - far) * DBU < 1.0]
    assert sum(ys) / len(ys) == pytest.approx(0.0, abs=0.05)


def test_the_arc_is_counted_in_the_facet_to_grating_distance(tmp_path):
    """The guide travels further than it advances, and the delay follows the path.

    `cavity.feed_length_um` is the facet-to-grating distance the cavity stage
    computes its round-trip delay from. Deducting only the axial extent would
    draw a cavity longer than the modelled one by the difference between the arc
    and its chord.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled",
                facet_bend_radius_um=500.0, taper_length_um=150.0)
    _, m = _run_layout(d, tmp_path)
    # 150 um of straight plus a 500 um arc through 8 degrees
    assert m["facet_lead_in_path_um"] == pytest.approx(150.0 + 500.0 * math.radians(8.0),
                                                       rel=1e-9)


def test_a_feed_shorter_than_the_route_is_refused(tmp_path):
    """The lead-in is drawn inside the feed, so it cannot exceed it.

    The clamp this replaces would have drawn a stub and reported nothing, and the
    drawn cavity would then have borne no relation to the computed delay.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled",
                facet_bend_radius_um=500.0, taper_length_um=150.0)
    d.cavity.feed_length_um = 180.0        # shorter than 150 + 69.8
    with pytest.raises(RuntimeError, match="facet-to-grating"):
        _run_layout(d, tmp_path)


def test_the_slab_reaches_past_the_excursion(tmp_path):
    """A lead-in outside the etch-clear region is a guide with no cladding."""
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled",
                facet_bend_radius_um=500.0)
    _, m = _run_layout(d, tmp_path)
    slab = _region(m["gds"], d.layout.layer_map["SLAB"])
    lead = _lead_polygon(m["gds"], d)
    assert (db.Region(lead) - slab).is_empty()


def test_the_routed_lead_in_butts_cleanly_against_the_feed(tmp_path):
    """The junction must carry no sliver.

    The rails were offset perpendicular to a heading differenced from the
    neighbouring points, and over the last arc chord that heading is not axial.
    The two rails therefore ended a nanometre apart in z and the joint carried a
    notch, which both the in-process engine and the foundry runset reported as a
    minimum-gap violation. The tangent is known in closed form and is now used,
    so the check here is that the emitted layer has no space violation at all.
    """
    d = _design(draw_facets=True, input_facet_angle_deg=8.0, facet_route="angled",
                facet_bend_radius_um=250.0, taper_length_um=150.0)
    d.cavity.feed_length_um = 400.0
    ctx, m = _run_layout(d, tmp_path)
    res = s06_drc.run(d, ctx, None)
    space = [r for r in res["results"] if r["name"] == "WG_min_space"]
    assert space and space[0]["violations"] == 0, res["results"]


def test_the_floor_plan_encloses_the_bond_pads(tmp_path):
    """A pad outside the usable area is a pad the foundry will not accept.

    The floor plan was sized off the electrodes with a 30 um allowance while the
    pads reach 80 um beyond the outer electrode edge, so the pads lay outside it
    by 45 um. The foundry runset reported them as outside CHIP_INNER.
    """
    d = _design(draw_facets=True)
    d.electrodes.enabled = True
    _, m = _run_layout(d, tmp_path)
    fp = _region(m["gds"], d.layout.layer_map["FLOORPLAN"])
    pads = _region(m["gds"], d.layout.layer_map["PAD"])
    assert not pads.is_empty()
    assert (pads - fp).is_empty()


# --- a check that cannot fail has established nothing -----------------------
#
# Every error of one working session had the same shape: a check was confirmed
# to have RUN, and never confirmed to have been CAPABLE OF FAILING. The deck
# returned zero violations against a mask whose layers it did not read; the
# corner sweep returned nine of nine on a list that did not contain the failing
# row. Both are guarded here.


def test_deck_layers_are_read_from_the_runset():
    from picchain.stages.s06_drc import deck_layers

    text = (
        "RIDGE = input(2, 10) # LT etch\n"
        "SLAB = input(3, 10) # LT etch full\n"
        "M1 = input(20, 0) # first metal\n"
        "not_a_layer = something_else(1, 2)\n"
    )
    assert deck_layers(text) == {"RIDGE": (2, 10), "SLAB": (3, 10), "M1": (20, 0)}


def test_the_two_luxtelligence_decks_differ_in_the_numbers_that_matter():
    """The niobate and tantalate runsets are near-identical in rule values and
    differ in layer numbers, which is why pointing a design at the wrong one
    yields a clean report rather than an obvious failure."""
    import pathlib

    from picchain.stages.s06_drc import deck_layers

    pdk = pathlib.Path(__file__).resolve().parents[1] / "pdk" / "LXT_KLayout_DRC_Runsets"
    ln = deck_layers((pdk / "LN_CORE_lnoi400.lydrc").read_text(encoding="utf-8", errors="replace"))
    lt = deck_layers((pdk / "LT_PRO_ltoi300.lydrc").read_text(encoding="utf-8", errors="replace"))
    assert ln["RIDGE"] == (2, 0) and lt["RIDGE"] == (2, 10)
    assert ln["SLAB"] == (3, 0) and lt["SLAB"] == (3, 10)
    # the metal move is the silent one: 21/0 holds no rule on the LT deck
    assert ln["M1"] == (21, 0) and lt["M1"] == (20, 0)


def test_the_deck_runner_reports_layers_it_could_not_see():
    import inspect

    from picchain.stages import s06_drc

    src = inspect.getsource(s06_drc)
    assert "layers_named_and_empty" in src
    assert "cannot have failed" in src


def test_a_must_target_absent_from_the_corner_list_is_added_where_reachable():
    """Updated 2026-08-16. The first version of this guard added every absent
    `must` row, which dragged layout and drc into a physics sweep and failed 24
    of 24 corners on rows a corner cannot move. Reachability is the resolved
    stage closure: `mode` runs as a dependency of `grating` whether or not a
    metric names it, so `mode.n_guided_modes` is evaluable."""
    import inspect

    from picchain import cli

    src = inspect.getsource(cli)
    assert "must_absent" in src
    # reachable ones are added
    assert "addable" in src and "they have been added" in src
    # the rest are named, not forced in and not dropped
    assert "unreachable" in src
    assert "properties of the mask rather than of the process point" in src
    # reachability uses the closure, not the directly named stages
    assert "_resolve_stages(_declared" in src


def test_the_deck_runner_names_what_occupies_each_layer_it_reads():
    """A layer map written for one stack carries auxiliary layers chosen because
    that stack ignored them. The seal ring, dicing lane and facet marks sat on
    20/0, 22/0 and 23/0: unread by the niobate deck, read as M1, M2 and HRL by
    the tantalate one."""
    import inspect

    from picchain.stages import s06_drc

    src = inspect.getsource(s06_drc)
    assert "deck_layer_sources" in src
    assert "more than one design layer lands on" in src


# --- the platform is bound to its deck ---------------------------------------
#
# A tantalate design was drawn on the niobate stack's layer numbers and checked
# against the niobate deck. It returned zero violations, ten of ten release
# conditions and a signed manifest. Nothing connected the declared platform to
# the deck, so nothing could contradict it.


def test_a_deck_declares_its_own_stack():
    import pathlib

    from picchain.stages.s06_drc import deck_identity

    pdk = pathlib.Path(__file__).resolve().parents[1] / "pdk" / "LXT_KLayout_DRC_Runsets"
    ln = deck_identity((pdk / "LN_CORE_lnoi400.lydrc").read_text(encoding="utf-8", errors="replace"))
    lt = deck_identity((pdk / "LT_PRO_ltoi300.lydrc").read_text(encoding="utf-8", errors="replace"))
    assert "lnoi400" in ln and "ltoi300" in lt


def test_a_deck_for_another_stack_is_refused_before_it_runs():
    import pytest

    from picchain.config import Design
    from picchain.stages.s06_drc import DeckPlatformMismatch, check_deck_matches_platform

    d = Design(meta={"name": "x"}, grating={"period_um": 1.417},
               platform={"stack": "ltoi300"})
    # the deck it belongs to
    check_deck_matches_platform(d, "<description>LT-PRO ltoi300 DRC</description>")
    # a deck from the other stack of the same foundry
    with pytest.raises(DeckPlatformMismatch):
        check_deck_matches_platform(d, "<description>LN-CORE lnoi400 DRC</description>")
    # a deck that names no stack at all cannot be matched, so it is refused too
    with pytest.raises(DeckPlatformMismatch):
        check_deck_matches_platform(d, "# a runset with no identity")


def test_an_undeclared_stack_leaves_the_check_off():
    """The bind is opt-in, so existing designs are not broken by adding it."""
    from picchain.config import Design
    from picchain.stages.s06_drc import check_deck_matches_platform

    d = Design(meta={"name": "x"}, grating={"period_um": 1.417})
    assert d.platform.stack is None
    check_deck_matches_platform(d, "<description>LN-CORE lnoi400 DRC</description>")


def test_a_stack_mismatch_is_not_filed_as_an_environment_failure():
    """`run` downgrades an unrunnable deck to a warning and lets the release gate
    refuse on 'no deck executed'. A wrong-stack deck would run perfectly, so it
    must not take that path."""
    import inspect

    from picchain.stages import s06_drc

    src = inspect.getsource(s06_drc.run)
    # scope to the deck block: `run` has an earlier generic handler inside the
    # per-rule loop, so a whole-function index comparison tests nothing
    block = src[src.index("deck_result = run_deck"):]
    assert "except DeckPlatformMismatch:" in block
    assert block.index("except DeckPlatformMismatch:") < block.index("except Exception as exc:")
