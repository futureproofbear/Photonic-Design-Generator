"""The steps between a working design and a mask that can be sent.

Five capabilities are covered: the submission manifest and its gate, derived
layers and mask polarity, the layout regression, the circuit assembly, and fill
placement with the connectivity comparison.
"""

from __future__ import annotations

import json

import klayout.db as db
import pytest

from picchain.artifacts import RunContext
from picchain.config import Design, DerivedLayer, DRCRule, SchematicNet
from picchain.stages import s05_layout, s12_mask, s15_release, s16_circuit

DBU = 0.001


def _design(**layout_kw):
    d = Design(
        meta={"name": "r"},
        grating={"period_um": 1.28, "length_um": 128.0},
        layout={"draw_periods": 10, **layout_kw},
    )
    d.drc.rules = [
        DRCRule(name="WG_min_width", kind="min_width", layer="WG", value_um=0.20,
                ignore_angle_deg=80.0),
    ]
    return d


def _layout(d, tmp_path, tag="r"):
    ctx = RunContext(design_dir=tmp_path, run_id=tag).ensure()
    return ctx, s05_layout.run(d, ctx, None)


def _region(gds, layer):
    ly = db.Layout()
    ly.read(str(gds))
    return db.Region(ly.top_cell().begin_shapes_rec(ly.layer(*layer))).merged()


# --------------------------------------------------------------------------
# 1. the submission manifest
# --------------------------------------------------------------------------
def test_the_manifest_inventories_the_files_with_checksums(tmp_path):
    d = _design()
    d.release.enabled = True
    d.release.strict = False
    ctx, _ = _layout(d, tmp_path)
    payload = s15_release.run(d, ctx, None)

    names = {f["file"] for f in payload["files"]}
    assert "r.gds" in names and "r.oas" in names
    assert all(len(f["sha256"]) == 64 for f in payload["files"])
    assert "drc_markers" not in " ".join(names), "a review aid is not a deliverable"


def test_the_checksum_follows_the_file(tmp_path):
    """A manifest whose checksum does not track the artifact records nothing."""
    d = _design()
    d.release.enabled = True
    d.release.strict = False
    ctx, payload_a = _layout(d, tmp_path, tag="a")
    a = s15_release.run(d, ctx, None)

    d.grating.post_gap_um = 0.70
    ctx2, _ = _layout(d, tmp_path, tag="b")
    b = s15_release.run(d, ctx2, None)

    sa = {f["file"]: f["sha256"] for f in a["files"]}
    sb = {f["file"]: f["sha256"] for f in b["files"]}
    assert sa["r.gds"] != sb["r.gds"]


def test_a_design_that_fails_its_conditions_is_refused(tmp_path):
    """The only place in the chain where a condition stops the work."""
    d = _design()
    d.release.enabled = True
    d.release.strict = True
    ctx, _ = _layout(d, tmp_path)
    with pytest.raises(RuntimeError, match="blocked on"):
        s15_release.run(d, ctx, None)


def test_a_waiver_is_recorded_rather_than_removing_the_row(tmp_path):
    d = _design()
    d.release.enabled = True
    d.release.strict = False
    ctx, _ = _layout(d, tmp_path)
    payload = s15_release.run(d, ctx, None)
    unmet = [r["condition"] for r in payload["readiness"] if not r["met"]]
    assert unmet

    d.release.waive = unmet
    ctx2, _ = _layout(d, tmp_path, tag="w")
    waived = s15_release.run(d, ctx2, None)
    assert waived["released"] is True
    assert waived["conditions_waived"] == sorted(unmet)
    # the rows are still present and still record that they were not met
    still_unmet = [r for r in waived["readiness"] if not r["met"]]
    assert still_unmet and all(r["waived"] for r in still_unmet)


def test_an_unknown_waiver_is_refused(tmp_path):
    d = _design()
    d.release.enabled = True
    d.release.waive = ["the mask is beautiful"]
    ctx, _ = _layout(d, tmp_path)
    with pytest.raises(ValueError, match="do not exist"):
        s15_release.run(d, ctx, None)


def test_the_manifest_is_written_in_both_forms(tmp_path):
    d = _design()
    d.release.enabled = True
    d.release.strict = False
    ctx, _ = _layout(d, tmp_path)
    s15_release.run(d, ctx, None)
    doc = json.loads((ctx.run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    md = (ctx.run_dir / "MANIFEST.md").read_text(encoding="utf-8")
    assert doc["design"] == "r"
    assert "BLOCKED" in md and "Readiness" in md


# --------------------------------------------------------------------------
# 2. derived layers and mask polarity
# --------------------------------------------------------------------------
def test_an_inverse_layer_is_the_field_minus_the_feature(tmp_path):
    """Mask polarity, expressed as an operation rather than drawn twice."""
    d = _design()
    d.layout.derived_layers = [
        DerivedLayer(name="WG_DARK", op="not", a="FLOORPLAN", b="WG", layer=[30, 0]),
    ]
    _, payload = _layout(d, tmp_path)

    field = _region(payload["gds"], d.layout.layer_map["FLOORPLAN"])
    guide = _region(payload["gds"], d.layout.layer_map["WG"])
    dark = _region(payload["gds"], [30, 0])

    assert (dark & guide).area() == 0, "the inverse overlaps the feature"
    assert (dark + guide).merged().area() == pytest.approx(field.area(), rel=1e-9)


def test_a_sized_layer_grows_by_the_amount_declared(tmp_path):
    d = _design()
    d.layout.derived_layers = [
        DerivedLayer(name="WG_GROWN", op="size", a="WG", by_um=1.0, layer=[31, 0]),
    ]
    _, payload = _layout(d, tmp_path)
    grown = _region(payload["gds"], [31, 0])
    guide = _region(payload["gds"], d.layout.layer_map["WG"])
    assert grown.area() > guide.area()
    assert (guide - grown).area() == 0, "the grown layer must contain the original"


def test_a_derived_layer_reading_a_layer_that_is_not_drawn_is_refused(tmp_path):
    d = _design()
    d.layout.derived_layers = [
        DerivedLayer(name="X", op="not", a="NOT_A_LAYER", b="WG", layer=[32, 0]),
    ]
    ctx = RunContext(design_dir=tmp_path, run_id="bad").ensure()
    with pytest.raises(ValueError, match="not drawn"):
        s05_layout.run(d, ctx, None)


def test_derived_layers_are_reported_with_their_expression(tmp_path):
    d = _design()
    d.layout.derived_layers = [
        DerivedLayer(name="WG_DARK", op="not", a="FLOORPLAN", b="WG", layer=[30, 0]),
    ]
    _, payload = _layout(d, tmp_path)
    row = payload["derived_layers"][0]
    assert row["expression"] == "FLOORPLAN not WG"
    assert row["layer"] == [30, 0]
    assert row["polygons"] >= 1


# --------------------------------------------------------------------------
# 3. the layout regression
# --------------------------------------------------------------------------
def test_the_regression_detects_a_geometric_change(tmp_path):
    """The layout stage has no closed-form anchor. The only statement available
    about a floor plan is that it has not changed since it was examined."""
    d = _design()
    _, a = _layout(d, tmp_path, tag="a")
    d2 = _design()
    d2.grating.post_gap_um = 0.64
    _, b = _layout(d2, tmp_path, tag="b")

    same = s05_layout.compare_backends(a["gds"], a["gds"], d.layout.layer_map)
    changed = s05_layout.compare_backends(a["gds"], b["gds"], d.layout.layer_map)
    assert same["agree"] is True
    assert changed["agree"] is False
    assert "WG" in changed["residual_by_layer_um2"]


# --------------------------------------------------------------------------
# 4. the circuit assembly
# --------------------------------------------------------------------------
pytestmark_circuit = pytest.mark.skipif(
    not s16_circuit.available(),
    reason=f"circuit extras absent ({s16_circuit.unavailable_reason()})",
)


@pytestmark_circuit
def test_a_straight_section_is_unit_amplitude_without_loss():
    s = s16_circuit.straight(wl=1.55, length_um=1000.0, neff=1.8, ng=2.2,
                             wl0=1.55, loss_dB_per_cm=0.0)
    import numpy as np
    assert abs(abs(s[("in0", "out0")]) - 1.0) < 1e-12


@pytestmark_circuit
def test_a_straight_section_attenuates_by_the_declared_loss():
    import numpy as np
    s = s16_circuit.straight(wl=1.55, length_um=10000.0, neff=1.8, ng=2.2,
                             wl0=1.55, loss_dB_per_cm=3.0)
    # 1 cm at 3 dB/cm is 3 dB of power, which is half
    assert abs(abs(s[("in0", "out0")]) ** 2 - 0.5) < 2e-3


@pytestmark_circuit
def test_a_straight_section_carries_the_group_delay_it_was_given():
    """The phase slope against frequency is the delay, and the delay is what
    sets the free spectral range the cavity stage reports."""
    import numpy as np

    C0 = 299792458.0
    length, ng, neff = 1000.0, 2.2, 1.8
    wl = np.linspace(1.549, 1.551, 4001)
    s = s16_circuit.straight(wl=wl, length_um=length, neff=neff, ng=ng, wl0=1.55)
    phase = np.unwrap(np.angle(s[("in0", "out0")]))
    omega = 2 * np.pi * C0 / (wl * 1e-6)
    tau = float(np.mean(np.gradient(phase, omega)))
    expected = length * 1e-6 * ng / C0
    assert abs(abs(tau) - expected) / expected < 2e-3


@pytestmark_circuit
def test_the_assembly_matches_the_closed_form_two_mirror_result():
    """The anchor. A facet and a grating separated by a guide form an etalon,
    and the netlist solver must reproduce the analytic cascade."""
    import numpy as np
    import sax

    wl = np.linspace(1.54, 1.56, 401)
    r_g, t_f, t_t, r_f = 0.9 + 0j, 0.8, 0.95, 0.05
    neff, length = 1.8, 500.0

    grating = s16_circuit.make_grating_model(
        wl, np.full_like(wl, r_g, dtype=complex),
        np.full_like(wl, np.sqrt(1 - abs(r_g) ** 2), dtype=complex))
    netlist = {
        "instances": {"facet": "coupler", "taper": "coupler",
                      "feed": "straight", "grating": "grating"},
        "connections": {"facet,out0": "taper,in0", "taper,out0": "feed,in0",
                        "feed,out0": "grating,in0"},
        "ports": {"chip": "facet,in0", "far": "grating,out0"},
    }
    circuit, _ = sax.circuit(netlist=netlist, models={
        "coupler": s16_circuit.lossy_coupler,
        "straight": s16_circuit.straight,
        "grating": grating,
    })
    S = circuit(wl=wl,
                facet={"transmission": t_f, "reflection": r_f ** 2},
                taper={"transmission": t_t, "reflection": 0.0},
                feed={"length_um": length, "neff": neff, "ng": neff, "wl0": 1.55,
                      "loss_dB_per_cm": 0.0})
    assembled = np.abs(np.asarray(S[("chip", "chip")])) ** 2

    phi = 2 * np.pi * neff * length / wl
    round_trip = t_t * r_g * np.exp(2j * phi)
    closed = np.abs(r_f + t_f * round_trip / (1 - r_f * round_trip)) ** 2
    assert float(np.max(np.abs(assembled - closed))) < 1e-12


@pytestmark_circuit
def test_a_perfect_coating_removes_the_etalon():
    """With no facet reflection the cascade is a single pass, so the assembly
    must reduce to the product. A ripple surviving here would be an artefact."""
    import numpy as np
    import sax

    wl = np.linspace(1.54, 1.56, 201)
    grating = s16_circuit.make_grating_model(
        wl, np.full_like(wl, 0.9 + 0j), np.full_like(wl, 0.43589 + 0j))
    circuit, _ = sax.circuit(
        netlist={
            "instances": {"facet": "coupler", "feed": "straight", "grating": "grating"},
            "connections": {"facet,out0": "feed,in0", "feed,out0": "grating,in0"},
            "ports": {"chip": "facet,in0", "far": "grating,out0"},
        },
        models={"coupler": s16_circuit.lossy_coupler,
                "straight": s16_circuit.straight, "grating": grating},
    )
    S = circuit(wl=wl, facet={"transmission": 0.6, "reflection": 0.0},
                feed={"length_um": 500.0, "neff": 1.8, "ng": 1.8, "wl0": 1.55,
                      "loss_dB_per_cm": 0.0})
    R = np.abs(np.asarray(S[("chip", "chip")])) ** 2
    assert float(np.ptp(R)) < 1e-12
    assert abs(float(np.mean(R)) - 0.6 * 0.6 * 0.81) < 1e-9


# --------------------------------------------------------------------------
# 5. fill placement and the schematic comparison
# --------------------------------------------------------------------------
def _mask_design(tmp_path, **fill_kw):
    d = _design()
    d.mask.density_windows = [["WG", 0.02, 0.80]]
    d.mask.density_tile_um = 200.0
    d.mask.fill.enabled = True
    for k, v in fill_kw.items():
        setattr(d.mask.fill, k, v)
    ctx, _ = _layout(d, tmp_path)
    return d, ctx, s12_mask.run(d, ctx, None)


def test_fill_raises_the_density_toward_the_window(tmp_path):
    """The placer cannot promise every tile. Where the exclusion around the
    existing features leaves no room, a tile stays below its window and the
    stage says so. What it must do is improve the density and never reduce it."""
    d, _, payload = _mask_design(tmp_path)
    fill = payload["fill"]
    assert fill["performed"] and fill["elements_placed"] > 0
    before = payload["density"]["WG"]
    after = fill["density_after"]["WG"]
    assert after["tiles_below_window"] < before["tiles_below_window"]
    assert after["minimum_density"] > before["minimum_density"]
    assert after["fill_area_required_um2"] < before["fill_area_required_um2"]


def test_fill_stands_off_the_features_by_the_declared_exclusion(tmp_path):
    """Fill placed against a guide is a scattering surface, so the exclusion is
    the whole point of a placer rather than a detail of it."""
    d, _, payload = _mask_design(tmp_path, exclusion_um={"WG": 5.0})
    ly = db.Layout()
    ly.read(payload["filled_gds"])
    top = ly.top_cell()
    fill = db.Region(top.begin_shapes_rec(ly.layer(*d.layout.layer_map["FILL"]))).merged()
    guide = db.Region(top.begin_shapes_rec(ly.layer(*d.layout.layer_map["WG"]))).merged()
    assert not fill.is_empty()
    assert (fill & guide.sized(int(round(5.0 / DBU)))).area() == 0


def test_the_filled_mask_is_written_beside_the_original(tmp_path):
    d, ctx, payload = _mask_design(tmp_path)
    assert payload["filled_gds"] and payload["filled_gds"].endswith(".filled.gds")
    assert payload["gds"] != payload["filled_gds"]


def test_labels_name_the_nets_they_sit_on(tmp_path):
    d = _design()
    ctx, _ = _layout(d, tmp_path)
    payload = s12_mask.run(d, ctx, None)
    named = {tuple(n["labels"]) for n in payload["netlist"]["named_nets"]}
    assert ("E_L_ELEC", "E_L_PAD") in named
    assert ("E_R_ELEC", "E_R_PAD") in named


def test_the_schematic_comparison_passes_on_a_correct_layout(tmp_path):
    d = _design()
    d.mask.schematic = [
        SchematicNet(name="LEFT", labels=["E_L_PAD", "E_L_ELEC"]),
        SchematicNet(name="RIGHT", labels=["E_R_PAD", "E_R_ELEC"]),
    ]
    ctx, _ = _layout(d, tmp_path)
    payload = s12_mask.run(d, ctx, None)
    assert payload["lvs"]["performed"] and payload["lvs"]["matches"]


def test_the_schematic_comparison_detects_a_pad_that_reaches_nothing(tmp_path):
    """The question a count of connected regions cannot answer."""
    d = _design()
    d.mask.schematic = [
        SchematicNet(name="LEFT", labels=["E_L_PAD", "E_L_ELEC"]),
    ]
    # a label naming a net that does not exist stands in for a broken connection
    d.mask.schematic.append(SchematicNet(name="GHOST", labels=["NOT_PLACED"]))
    ctx, _ = _layout(d, tmp_path)
    payload = s12_mask.run(d, ctx, None)
    lvs = payload["lvs"]
    assert lvs["performed"] and not lvs["matches"]
    ghost = [r for r in lvs["rows"] if r["net"] == "GHOST"][0]
    assert ghost["labels_not_found"] == ["NOT_PLACED"]


def test_the_comparison_states_that_it_recognises_no_device(tmp_path):
    """It establishes connectivity. What the connected thing *is* remains
    undetermined, and the payload is required to say so."""
    d = _design()
    d.mask.schematic = [SchematicNet(name="LEFT", labels=["E_L_PAD", "E_L_ELEC"])]
    ctx, _ = _layout(d, tmp_path)
    lvs = s12_mask.run(d, ctx, None)["lvs"]
    assert "no device recognition" in lvs["note"]
