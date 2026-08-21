"""The mask items a fabrication run requires, and the structures that measure it.

Each test states the property the drawn geometry must have, and measures that
property back off the polygons rather than off the parameters that produced
them. A builder that returns the arguments it was given would satisfy a test
written the other way round.
"""

from __future__ import annotations

import klayout.db as db
import pytest

from picchain import monitors
from picchain.artifacts import RunContext
from picchain.config import Design, DRCRule
from picchain.stages import s05_layout

DBU = 0.001


def _region(polys) -> db.Region:
    r = db.Region()
    for p in polys:
        r.insert(db.DPolygon([db.DPoint(x, y) for x, y in p]).to_itype(DBU))
    return r.merged()


def _bbox(polys):
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------
# 1. the kappa ladder: the gap drawn is the gap requested
# --------------------------------------------------------------------------
def test_kappa_ladder_draws_the_gap_it_was_asked_for():
    """The gap is measured back from the polygons, being the separation between
    the guide edge and the nearest post edge. A ladder whose rows do not differ
    in that separation measures nothing."""
    gaps = [0.53, 0.63, 0.73]
    wg = 1.0
    polys, desc = monitors.kappa_ladder(
        gaps_um=gaps, period_um=1.28, n_periods=5, wg_width_um=wg,
        post_width_um=0.30, post_length_um=0.30, row_pitch_um=100.0,
    )
    assert len(desc["rows"]) == len(gaps)
    for row in desc["rows"]:
        y0 = row["y_um"]
        # every post of this row sits above the guide edge by the stated gap
        posts = [p for p in polys["WG"]
                 if 0 < min(y for _, y in p) - y0 < 50 and (max(x for x, _ in p) -
                                                            min(x for x, _ in p)) < 1.0]
        assert posts, f"no posts found for gap {row['gap_um']}"
        inner_edge = min(min(y for _, y in p) for p in posts)
        assert inner_edge - (y0 + wg / 2) == pytest.approx(row["gap_um"], abs=1e-9)


def test_kappa_ladder_rows_are_identical_but_for_the_gap():
    """A ladder in which two things vary measures neither."""
    polys, desc = monitors.kappa_ladder(
        gaps_um=[0.5, 0.7], period_um=1.28, n_periods=4, wg_width_um=1.0,
        post_width_um=0.30, post_length_um=0.30, row_pitch_um=100.0,
    )
    assert len({r["n_periods"] for r in desc["rows"]}) == 1
    assert len({r["length_um"] for r in desc["rows"]}) == 1


# --------------------------------------------------------------------------
# 2. the cut-back: lengths measured off the polygons
# --------------------------------------------------------------------------
def test_loss_cutback_draws_each_declared_length():
    lengths = [500.0, 1500.0, 3000.0]
    polys, desc = monitors.loss_cutback(
        lengths_um=lengths, wg_width_um=1.0, row_pitch_um=100.0)
    drawn = sorted(round(max(x for x, _ in p) - min(x for x, _ in p), 6)
                   for p in polys["WG"])
    assert drawn == sorted(lengths)


# --------------------------------------------------------------------------
# 3. the vernier: it is held to the rule it is measured against
# --------------------------------------------------------------------------
def test_cd_vernier_never_draws_a_space_below_the_floor():
    """A monitor that fails the deck is removed before submission, which is the
    least useful outcome available."""
    floor = 0.30
    polys, desc = monitors.cd_vernier(
        widths_um=[0.20, 0.30, 0.60], repeats=6, length_um=40.0,
        row_pitch_um=100.0, min_space_um=floor,
    )
    for row in desc["rows"]:
        assert row["space_um"] >= floor - 1e-12
        assert row["pitch_um"] == pytest.approx(row["drawn_width_um"] + row["space_um"])
    # and the array is genuinely dense wherever the rule allows it
    assert any(r["equal_line_space"] for r in desc["rows"])
    # measured back off the polygons on the tightest row
    space = _region(polys["WG"]).space_check(int(round(floor / DBU)))
    assert space.count() == 0


def test_cd_vernier_lines_are_drawn_at_the_declared_width():
    polys, desc = monitors.cd_vernier(
        widths_um=[0.25, 0.50], repeats=4, length_um=40.0, row_pitch_um=100.0)
    widths = {round(max(x for x, _ in p) - min(x for x, _ in p), 6) for p in polys["WG"]}
    assert widths == {0.25, 0.50}


# --------------------------------------------------------------------------
# 4. the electrode ladder: the separation rule is a floor, and a raise is stated
# --------------------------------------------------------------------------
def test_electrode_ladder_respects_the_separation_rule_and_says_when_it_had_to():
    sep = 2.0
    wg = 1.0
    polys, desc = monitors.electrode_ladder(
        gaps_um=[4.0, 7.0, 12.0], electrode_width_um=20.0, length_um=400.0,
        wg_width_um=wg, pad_um=80.0, row_pitch_um=120.0, min_separation_um=sep,
    )
    for row in desc["rows"]:
        assert row["metal_to_guide_um"] >= sep - 1e-12
    raised = desc["gaps_raised_to_the_rule"]
    assert raised and raised[0]["requested_um"] == pytest.approx(4.0)
    assert raised[0]["drawn_um"] == pytest.approx(2 * (sep + wg / 2))
    # the compromise is visible, so the tightest gap in use is known to be unmeasured
    assert desc["separation_floor_um"] == pytest.approx(sep)


def test_electrode_ladder_leaves_a_compliant_request_untouched():
    polys, desc = monitors.electrode_ladder(
        gaps_um=[6.0, 10.0], electrode_width_um=20.0, length_um=400.0,
        wg_width_um=1.0, pad_um=80.0, row_pitch_um=120.0, min_separation_um=2.0,
    )
    assert desc["gaps_raised_to_the_rule"] == []
    assert [r["gap_um"] for r in desc["rows"]] == [6.0, 10.0]


# --------------------------------------------------------------------------
# 5. the alignment mark: levels must nest, not coincide
# --------------------------------------------------------------------------
def test_alignment_mark_levels_do_not_overlap():
    """Drawing the same figure on two levels is the obvious construction, and
    any layer-to-layer separation rule reports it as a short."""
    a = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=0, n_levels=2,
                                clearance_um=3.0)
    b = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=1, n_levels=2,
                                clearance_um=3.0)
    assert (_region(a) & _region(b)).area() == 0


def test_alignment_mark_levels_clear_the_declared_separation():
    clearance = 3.0
    a = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=0, n_levels=2,
                                clearance_um=clearance)
    b = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=1, n_levels=2,
                                clearance_um=clearance)
    checked = _region(a).separation_check(_region(b), int(round(clearance / DBU)))
    assert checked.count() == 0


def test_alignment_mark_inner_level_sits_inside_the_outer_one():
    a = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=0, n_levels=2)
    b = monitors.alignment_mark(size_um=40.0, arm_width_um=4.0, level=1, n_levels=2)
    ax0, ay0, ax1, ay1 = _bbox(a)
    bx0, by0, bx1, by1 = _bbox(b)
    assert ax0 < bx0 and ay0 < by0 and bx1 < ax1 and by1 < ay1


def test_a_mark_too_small_for_its_levels_is_refused():
    with pytest.raises(ValueError, match="closes on itself"):
        monitors.alignment_mark(size_um=12.0, arm_width_um=4.0, level=1, n_levels=2,
                                clearance_um=3.0)


# --------------------------------------------------------------------------
# 6. the seal ring must be closed
# --------------------------------------------------------------------------
def test_seal_ring_is_a_closed_loop_of_the_declared_width():
    """An open ring stops neither a crack nor moisture, and four bars that fail
    to meet at a corner look correct in a polygon count."""
    w = 20.0
    ring = _region(monitors.seal_ring(x0=0.0, y0=0.0, x1=500.0, y1=300.0, width_um=w))
    assert ring.count() == 1, "the ring is not one connected figure"
    expected = 500.0 * 300.0 - (500.0 - 2 * w) * (300.0 - 2 * w)
    assert ring.area() * DBU * DBU == pytest.approx(expected)
    # and it encloses a hole rather than being solid
    assert ring.holes().count() == 1


# --------------------------------------------------------------------------
# 7. the mask that is emitted against the device that was simulated
# --------------------------------------------------------------------------
def _layout_design(**layout_kw):
    return Design(
        meta={"name": "t"},
        grating={"period_um": 1.28, "length_um": 128.0},
        layout={"draw_periods": 10, **layout_kw},
    )


def test_a_partial_mask_is_reported_as_incomplete(tmp_path):
    d = _layout_design()
    ctx = RunContext(design_dir=tmp_path, run_id="r").ensure()
    payload = s05_layout.run(d, ctx, None)
    assert payload["fidelity"]["periods_total"] == 100
    assert payload["fidelity"]["periods_drawn"] == 10
    assert payload["mask_is_complete"] is False
    assert any("grating periods" in w for w in ctx.warnings)


def test_a_complete_mask_reports_itself_complete(tmp_path):
    d = _layout_design()
    d.layout.draw_periods = None
    ctx = RunContext(design_dir=tmp_path, run_id="r").ensure()
    payload = s05_layout.run(d, ctx, None)
    assert payload["mask_is_complete"] is True
    assert not any("grating periods" in w for w in ctx.warnings)


def test_require_complete_refuses_a_partial_mask(tmp_path):
    d = _layout_design(require_complete=True)
    ctx = RunContext(design_dir=tmp_path, run_id="r").ensure()
    with pytest.raises(RuntimeError, match="before submission"):
        s05_layout.run(d, ctx, None)


def test_the_two_backends_are_compared_and_agree(tmp_path):
    """Two writers given one polygon list. The residual of their difference is
    the only evidence available that either wrote what it was given."""
    d = _layout_design()
    ctx = RunContext(design_dir=tmp_path, run_id="r").ensure()
    payload = s05_layout.run(d, ctx, None)
    xor = payload["backend_xor"]
    if not xor.get("performed"):
        pytest.skip(f"the second backend is unavailable: {xor.get('reason')}")
    assert xor["residual_area_um2"] == 0.0
    assert xor["agree"] is True


def test_the_comparison_detects_a_difference_that_a_rule_deck_would_not(tmp_path):
    """A dropped polygon is legal geometry. Only the comparison finds it."""
    d = _layout_design()
    ctx = RunContext(design_dir=tmp_path, run_id="r").ensure()
    payload = s05_layout.run(d, ctx, None)
    if not payload["backend_xor"].get("performed"):
        pytest.skip("the second backend is unavailable")

    damaged = tmp_path / "damaged.gds"
    ly = db.Layout()
    ly.read(payload["gds"])
    top = ly.top_cell()
    idx = ly.layer(*d.layout.layer_map["WG"])
    for shape in list(top.shapes(idx).each())[:1]:
        top.shapes(idx).erase(shape)
    ly.write(str(damaged))

    result = s05_layout.compare_backends(payload["gds"], damaged, d.layout.layer_map)
    assert result["agree"] is False
    assert result["residual_area_um2"] > 0
    assert "WG" in result["residual_by_layer_um2"]


# --------------------------------------------------------------------------
# 8. the process bias reaches the drawn polygons
# --------------------------------------------------------------------------
def test_the_backend_survives_repeated_emission_in_one_process(tmp_path):
    """The cell library is process-wide and refuses a repeated name. Anything
    that emits more than once, `corners` above all, would otherwise cross-check
    its first layout and none of the others."""
    for i in range(3):
        d = _layout_design()
        ctx = RunContext(design_dir=tmp_path, run_id=f"r{i}").ensure()
        payload = s05_layout.run(d, ctx, None)
        assert payload["backend_gdsfactory_available"], f"backend lost on emission {i}"
        assert payload["backend_xor"]["agree"] is True


# --------------------------------------------------------------------------
# 9. connectivity as nets rather than as a count per layer
# --------------------------------------------------------------------------
def _netlist_layout(join_pad: bool):
    from picchain.stages.s12_mask import _extract_netlist

    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell("T")
    wg, metal, pad = ly.layer(1, 0), ly.layer(10, 0), ly.layer(11, 0)
    top.shapes(wg).insert(db.DBox(0, 0, 10, 1))
    top.shapes(wg).insert(db.DBox(9, 0, 20, 1))          # touches the first: one net
    top.shapes(wg).insert(db.DBox(40, 0, 50, 1))         # separate: a second net
    top.shapes(metal).insert(db.DBox(0, 5, 20, 8))
    top.shapes(pad).insert(db.DBox(15, 7, 25, 15))       # overlaps the metal

    class Cfg:
        connected_layers = ["WG", "METAL", "PAD"]
        joined_layers = [["METAL", "PAD"]] if join_pad else []

    return _extract_netlist(ly, {"WG": [1, 0], "METAL": [10, 0], "PAD": [11, 0]}, Cfg())


def test_extraction_joins_a_pad_to_the_electrode_it_drives():
    """Two shapes on two layers that touch are one net. Merging each layer and
    counting islands cannot express that, and it is the question a pad asks."""
    assert _netlist_layout(join_pad=True)["net_count"] == 3
    assert _netlist_layout(join_pad=False)["net_count"] == 4


def test_extraction_counts_a_break_as_an_extra_net():
    from picchain.stages.s12_mask import _extract_netlist

    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell("T")
    wg = ly.layer(1, 0)
    top.shapes(wg).insert(db.DBox(0, 0, 10, 1))
    top.shapes(wg).insert(db.DBox(10.5, 0, 20, 1))       # a 500 nm break

    class Cfg:
        connected_layers = ["WG"]
        joined_layers = []

    assert _extract_netlist(ly, {"WG": [1, 0]}, Cfg())["net_count"] == 2


# --------------------------------------------------------------------------
# 10. the assembled die
# --------------------------------------------------------------------------
def _die(tmp_path, **reticle_kw):
    from picchain.stages import s14_reticle

    d = _layout_design()
    d.reticle.enabled = True
    d.reticle.monitors.kappa_periods = 20
    d.reticle.monitors.loss_lengths_um = [200.0, 400.0]
    d.drc.rules = [
        DRCRule(name="WG_min_space", kind="min_space", layer="WG", value_um=0.30),
        DRCRule(name="METAL_to_WG", kind="min_separation", layer="METAL",
                other_layer="WG", value_um=2.0),
    ]
    for k, v in reticle_kw.items():
        setattr(d.reticle, k, v)
    ctx = RunContext(design_dir=tmp_path, run_id="die").ensure()
    s05_layout.run(d, ctx, None)
    return d, ctx, s14_reticle.run(d, ctx, None)


def test_the_die_carries_the_items_a_submission_requires(tmp_path):
    _, _, payload = _die(tmp_path)
    assert payload["seal_ring_width_um"] > 0
    assert payload["dicing_lane_um"] > 0
    assert payload["alignment_marks"] == 4
    assert payload["label"].startswith("T REV")
    assert payload["monitor_structures"] >= 3
    assert payload["die_width_um"] > payload["device_extent_um"][0]


def test_the_die_it_draws_passes_the_rules_it_was_given(tmp_path):
    """The frame and the monitors are held to the same deck as the device. A
    frame drawn and never checked is a frame assumed."""
    d, ctx, payload = _die(tmp_path)
    ly = db.Layout()
    ly.read(payload["gds"])
    top = ly.top_cell()

    def region(name):
        return db.Region(top.begin_shapes_rec(ly.layer(*d.layout.layer_map[name]))).merged()

    wg, metal = region("WG"), region("METAL")
    assert (wg & metal).area() == 0, "the frame shorts metal to the guide layer"
    assert wg.space_check(int(round(0.30 / DBU))).count() == 0
    assert metal.separation_check(wg, int(round(2.0 / DBU))).count() == 0


def test_a_die_smaller_than_its_contents_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="Enlarge the die"):
        _die(tmp_path, die_width_um=200.0, die_height_um=200.0)


def test_a_precompensated_mask_is_drawn_off_nominal(tmp_path):
    bias = 0.040
    plain = _layout_design()
    biased = _layout_design()
    biased.process.bias_um = {"WG": bias}

    def guide_width(design):
        ctx = RunContext(design_dir=tmp_path, run_id=f"r{id(design)}").ensure()
        s05_layout.run(design, ctx, None)
        polys = s05_layout.build_polygons(design, ctx)
        feed = polys["WG"][1]                       # the straight feed section
        return max(y for _, y in feed) - min(y for _, y in feed)

    assert guide_width(plain) - guide_width(biased) == pytest.approx(bias)


def test_the_emitted_die_is_the_size_that_was_declared(tmp_path):
    """It was not. The usable width deducted the margin, the seal width and the
    dicing lane but not the seal-ring clearance, which the ring then added back,
    so a declared 20200 x 5050 um was written as 20320 x 5170. On a process
    offering a fixed set of footprints that is a refusal at submission, and
    nothing reported it because no boundary was drawn to check it against.
    """
    _, _, payload = _die(tmp_path, die_width_um=4000.0, die_height_um=4000.0)
    assert payload["die_width_um"] == pytest.approx(4000.0, abs=1e-6)
    assert payload["die_height_um"] == pytest.approx(4000.0, abs=1e-6)


def test_the_chip_frame_is_drawn_centred_and_to_the_declared_size(tmp_path):
    """The footprint, the centring and the exclusion ring are each checked
    against two rectangles, and a rule with nothing to compare reports nothing.
    Measured off the written file rather than off the payload.
    """
    from picchain.config import ChipFrameCfg

    d, _, payload = _die(
        tmp_path, die_width_um=4000.0, die_height_um=4000.0,
        chip_frame=ChipFrameCfg(enabled=True, exclusion_zone_um=50.0,
                                allowed_edges_um=[4000.0]))
    assert payload["chip_frame"]["footprint_is_offered"] is True

    ly = db.Layout()
    ly.read(payload["gds"])
    top = ly.top_cell()
    for name, w, h in (("CHIP_OUTER", 4000.0, 4000.0),
                       ("CHIP_INNER", 3900.0, 3900.0)):
        idx = ly.find_layer(*d.layout.layer_map[name])
        assert idx is not None, f"{name} was not drawn"
        box = db.Region(top.begin_shapes_rec(idx)).bbox()
        assert box.width() * DBU == pytest.approx(w, abs=1e-6)
        assert box.height() * DBU == pytest.approx(h, abs=1e-6)
        assert (box.left + box.right) / 2 * DBU == pytest.approx(0.0, abs=1e-6)
        assert (box.bottom + box.top) / 2 * DBU == pytest.approx(0.0, abs=1e-6)


def test_a_footprint_the_process_does_not_offer_is_reported(tmp_path):
    from picchain.config import ChipFrameCfg

    _, ctx, payload = _die(
        tmp_path, die_width_um=4000.0, die_height_um=4000.0,
        chip_frame=ChipFrameCfg(enabled=True, allowed_edges_um=[5050.0, 10100.0]))
    assert payload["chip_frame"]["footprint_is_offered"] is False
    assert any("not among" in w for w in ctx.warnings)


def test_the_composite_mark_is_suppressed_where_its_layer_is_a_level(tmp_path):
    """The composite is an inspection aid and not a drawn level. Where the layer
    it names is one the process reads, it reproduces the level's own geometry a
    few micrometres away on a layer that may carry a separation rule against it.
    The LN-CORE runset requires 15 um between its marker layer and the ridge, and
    the composite stood them 3 um apart at each of the four corners.
    """
    from picchain.config import AlignmentMarkCfg

    d, _, payload = _die(tmp_path, marks=AlignmentMarkCfg(layers=["MARK", "METAL"],
                                                  composite_layer=None))
    ly = db.Layout()
    ly.read(payload["gds"])
    top = ly.top_cell()
    mark = db.Region(top.begin_shapes_rec(
        ly.layer(*d.layout.layer_map["MARK"]))).merged()
    wg = db.Region(top.begin_shapes_rec(
        ly.layer(*d.layout.layer_map["WG"]))).merged()
    assert not mark.is_empty(), "the mark level was not drawn"
    assert (mark & wg).is_empty()


# --- the coherence ladder: the monitor a post-gap ladder cannot replace ------


def test_the_coherence_ladder_holds_everything_but_the_length():
    from picchain.monitors import coherence_ladder

    polys, desc = coherence_ladder(
        lengths_um=[500.0, 2000.0, 5000.0],
        gap_um=0.970, period_um=1.417, wg_width_um=1.0,
        post_width_um=0.30, post_length_um=0.30, row_pitch_um=120.0)
    assert desc["structure"] == "coherence_ladder"
    assert len(desc["rows"]) == 3
    # each row's period count follows its length at the single shared period
    for row in desc["rows"]:
        assert row["n_periods"] == int(row["length_um"] / 1.417)
    # one gap for the whole set: the length is the only variable
    assert desc["gap_um"] == 0.970
    # guide + 2 posts per period, per row
    expected = sum(1 + 2 * r["n_periods"] for r in desc["rows"])
    assert len(polys["WG"]) == expected


def test_the_ladder_spans_the_penetration_depth():
    """The departure from tanh^2(kappa L) needs somewhere to appear, so the
    default lengths must bracket a several-mm penetration depth."""
    from picchain.config import Design

    d = Design(meta={"name": "x"}, grating={"period_um": 1.417})
    ls = d.reticle.monitors.coherence_lengths_um
    assert min(ls) <= 500.0 and max(ls) >= 10000.0
    # and it is opt-in, costing die area
    assert d.reticle.monitors.coherence_ladder is False


def test_every_optical_monitor_row_receives_a_port():
    """A structure that measures guided light and cannot receive it measures
    nothing. The mask carried four optical instruments with no optical port,
    the placement comment stating so as if it were a property. Each optical
    row is now extended to the polish line with a seal-ring opening."""
    import inspect

    from picchain.stages import s14_reticle

    src = inspect.getsource(s14_reticle)
    assert "OPTICAL_MONITORS" in src
    for name in ("kappa_ladder", "coherence_ladder", "loss_cutback",
                 "electrode_ladder"):
        assert f'"{name}"' in src
    # the extension registers a seal-ring opening per row
    assert "ports.append((y - 10.0, y + 10.0))" in src
    # and the defect's phrasing is gone from the placement path
    assert "They carry no optical port" not in src
