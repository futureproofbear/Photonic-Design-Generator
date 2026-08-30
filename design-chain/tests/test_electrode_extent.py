"""The electrode run, and the wavelength it acts at, on a device with no mirror.

The electro-optic stage sizes the capacitance, the lumped RC figure and the
travelling-wave bandwidth over the electrode length. That length was read from
the grating, which is correct for a mirror whose electrodes flank it and wrong
for every other electro-optic device. `grating.length_um` carries a schema
default whether or not a grating exists, so the figures returned for a device
without one described a 7250 um electrode and looked entirely ordinary.
"""

from __future__ import annotations

import pathlib

import pytest

from picchain.config import Design
from picchain.preflight import assert_ready, run_checks
from picchain.stages.s03_eo import electrode_extent

BASELINE = (pathlib.Path(__file__).resolve().parents[2]
            / "examples" / "edbr_tfln_baseline" / "design.yaml")


def _baseline() -> Design:
    return Design.load(BASELINE)


def test_a_mirror_takes_its_length_and_wavelength_from_the_grating():
    """The earlier behaviour, which is correct where a grating exists."""
    d = _baseline()
    d.electrodes.length_um = None
    grating = {"length_um": 7250.0, "bragg_wavelength_um": 1.5459}

    length, length_from, lam, lam_from = electrode_extent(d, grating)
    assert length == 7250.0
    assert length_from == "grating.length_um"
    assert lam == pytest.approx(1.5459)
    assert lam_from == "grating.bragg_wavelength_um"


def test_a_declared_length_is_preferred_to_the_grating():
    """A modulator states its own run, and the grating is not consulted."""
    d = _baseline()
    d.electrodes.length_um = 12900.0
    grating = {"length_um": 7250.0, "bragg_wavelength_um": 1.5459}

    length, length_from, lam, lam_from = electrode_extent(d, grating)
    assert length == 12900.0
    assert length_from == "electrodes.length_um"
    # and it acts at the wavelength the guide carries, not at a Bragg
    # wavelength belonging to a mirror the device does not contain
    assert lam == pytest.approx(d.waveguide.wavelength_um)
    assert lam_from == "waveguide.wavelength_um"


def test_a_disabled_grating_leaves_the_wavelength_with_the_guide():
    """With no grating payload there is no Bragg wavelength to take."""
    d = _baseline()
    d.electrodes.length_um = None
    length, length_from, lam, lam_from = electrode_extent(d, {})
    assert length == pytest.approx(d.grating.length_um)
    assert lam == pytest.approx(d.waveguide.wavelength_um)
    assert lam_from == "waveguide.wavelength_um"


def test_the_source_of_every_returned_value_is_reported():
    """Both rules name the field they read, so a run states which one applied."""
    d = _baseline()
    fields = {"electrodes.length_um", "grating.length_um",
              "grating.bragg_wavelength_um", "waveguide.wavelength_um"}
    for declared in (None, 9000.0):
        d.electrodes.length_um = declared
        _, length_from, _, lam_from = electrode_extent(
            d, {"length_um": 7250.0, "bragg_wavelength_um": 1.5459})
        assert length_from in fields
        assert lam_from in fields


def test_a_device_without_a_grating_must_declare_its_electrode_length():
    """The precondition, in both directions.

    Switching the grating off and leaving the length unset would size the
    electrode from a default the device does not contain. Declaring the length
    settles it, and the check must pass then, since a gate that refuses correct
    work trains the reader to bypass it.
    """
    d = _baseline()
    d.grating.enabled = False
    d.electrodes.enabled = True
    d.electrodes.length_um = None

    names = [f.check for f in run_checks(d)]
    assert "the_electrode_length_is_declared_where_no_grating_sets_it" in names

    d.electrodes.length_um = 12900.0
    names = [f.check for f in run_checks(d)]
    assert "the_electrode_length_is_declared_where_no_grating_sets_it" not in names


def test_the_gate_does_not_fire_where_the_electrodes_are_absent():
    """A study with no metal beside the guide has no electrode to size."""
    d = _baseline()
    d.grating.enabled = False
    d.electrodes.enabled = False
    d.electrodes.length_um = None
    names = [f.check for f in run_checks(d)]
    assert "the_electrode_length_is_declared_where_no_grating_sets_it" not in names


def test_a_length_that_is_not_a_length_is_refused():
    d = _baseline()
    d.grating.enabled = False
    d.electrodes.length_um = 0.0
    names = [f.check for f in run_checks(d)]
    assert "the_electrode_length_is_declared_where_no_grating_sets_it" in names


def test_the_baseline_laser_is_unaffected_by_any_of_this():
    """The change must leave every existing design exactly as it was."""
    d = _baseline()
    assert d.grating.enabled is True
    assert d.electrodes.length_um is None
    assert_ready(d)


def test_the_finite_element_stage_skips_a_post_comparison_it_cannot_make():
    """A device with no grating produces no post perturbation to compare against.

    The finite-difference stage returns null for `dn_eff_posts` rather than a
    number describing posts the device does not carry, and the cross-check read
    that null as a float and raised. The stage had never been run on a device
    without a grating, so nothing caught it.
    """
    import inspect

    from picchain.stages import s13_fem
    src = inspect.getsource(s13_fem)
    assert "cfg.with_posts and not design.grating.enabled" in src
    assert "dn_eff_posts_skipped" in src


def test_the_layout_offers_both_devices_and_defaults_to_the_laser():
    """A device selector, so the emission machinery is shared and not copied."""
    from picchain.config import LayoutCfg
    from picchain.stages.s05_layout import build_mzm_polygons

    assert LayoutCfg().device == "edbr"
    assert LayoutCfg(device="mach_zehnder").device == "mach_zehnder"
    assert callable(build_mzm_polygons)


def test_an_arm_sits_on_the_centre_line_of_its_gap():
    """The arm separation follows from the line and is not declared separately.

    Declaring it would let it drift from the electrode the electro-optic stage
    solved, and the push-pull factor of two rests on each arm seeing the field of
    one gap.
    """
    import pathlib

    from picchain.config import Design
    from picchain.stages.s05_layout import build_mzm_polygons

    d = Design.load(pathlib.Path(__file__).resolve().parents[2]
                    / "examples" / "edbr_tfln_baseline" / "design.yaml")
    d.layout.device = "mach_zehnder"
    d.grating.enabled = False
    d.electrodes.length_um = 5000.0
    d.electrodes.topology = "gsg"
    _, rec = build_mzm_polygons(d, None)

    expected = d.electrodes.width_um / 2.0 + d.electrodes.gap_um / 2.0
    assert abs(rec["arm_offset_um"] - expected) < 1e-9
    assert abs(rec["arm_separation_um"] - 2 * expected) < 1e-9
    # and the metal clears the ridge by the amount the rule is measured against
    assert rec["metal_to_ridge_clearance_um"] > 0


def test_the_splitter_junction_holds_the_minimum_space():
    """The two access tapers leave the multimode section already apart.

    This test previously asserted the opposite, on the belief that a 1x2
    splitter cannot hold a minimum-space rule through its junction because the
    gap between its outputs passes through zero. That belief was wrong, and it
    put four violations on a released mask and a question to the foundry.
    `lxt_pdk_gf.ltoi300.cells.mmi1x2_cband` is qualified on this stack and its
    access tapers leave the section 0.60 um apart, twice the rule. The gap is a
    drawn dimension, `port_separation_um - port_width_um`, and the junction
    holds the rule when that dimension does.
    """
    import pathlib

    from picchain.config import Design
    from picchain.stages.s05_layout import build_mzm_polygons

    d = Design.load(pathlib.Path(__file__).resolve().parents[2]
                    / "examples" / "edbr_tfln_baseline" / "design.yaml")
    d.layout.device = "mach_zehnder"
    d.grating.enabled = False
    d.electrodes.length_um = 5000.0
    _, rec = build_mzm_polygons(d, None)
    assert rec["min_space_um"] > 0.0
    # the narrowest point of the junction, and it clears the rule
    assert rec["port_gap_at_mmi_um"] >= rec["min_space_um"]
    # so no length of it falls below the rule
    assert rec["port_gap_below_min_space_um"] == 0.0


def test_a_closed_splitter_junction_is_still_measured():
    """Drawing the two ports meeting is reported rather than passing silently.

    The open junction above is the design. Where a port width is declared equal
    to the port separation the two meet at the end face, the gap starts at zero,
    and the length below the minimum space is reported so that the exception is
    a measured quantity rather than a surprise found by the rule deck.
    """
    import pathlib

    from picchain.config import Design
    from picchain.stages.s05_layout import build_mzm_polygons

    d = Design.load(pathlib.Path(__file__).resolve().parents[2]
                    / "examples" / "edbr_tfln_baseline" / "design.yaml")
    d.layout.device = "mach_zehnder"
    d.grating.enabled = False
    d.electrodes.length_um = 5000.0
    d.mzm.port_width_um = d.mzm.port_separation_um
    _, rec = build_mzm_polygons(d, None)
    assert rec["port_gap_at_mmi_um"] == 0.0
    assert rec["port_gap_below_min_space_um"] > 0.0
