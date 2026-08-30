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
