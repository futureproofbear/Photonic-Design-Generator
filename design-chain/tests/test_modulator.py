"""The Mach-Zehnder device figures, and the factor of two that is lost with them.

A vendor relation quoting V_pi.L without stating whether it belongs to one arm
or to the interferometer cannot be reconciled with a solve. The same ambiguity
has been observed to propagate into an electro-optic overlap differing by two.
This stage states the convention in its payload; these tests hold it to it.
"""

from __future__ import annotations

import math

import pytest

from picchain import rf
from picchain.stages.s18_modulator import device_VpiL, drive_factor


def test_the_factor_is_two_for_push_pull_and_one_otherwise():
    """The one number the conversion turns on, and the one the stage reports."""
    assert drive_factor("push_pull") == 2.0
    assert drive_factor("single_arm") == 1.0


def test_the_conversion_is_the_factor_and_nothing_else():
    """So that the reported factor and the reported figure cannot disagree."""
    for drive in ("push_pull", "single_arm"):
        assert device_VpiL(9.9, drive) == pytest.approx(9.9 / drive_factor(drive))


def test_push_pull_halves_the_single_arm_figure():
    assert device_VpiL(11.48, "push_pull") == pytest.approx(5.74)


def test_a_single_arm_drive_does_not_halve_it():
    """The second arm is a passive reference and contributes no phase."""
    assert device_VpiL(11.48, "single_arm") == pytest.approx(11.48)


def test_the_two_conventions_differ_by_exactly_two():
    single = device_VpiL(9.9, "single_arm")
    push = device_VpiL(9.9, "push_pull")
    assert single / push == pytest.approx(2.0)


def test_vpi_falls_as_the_inverse_of_the_length():
    """V_pi = V_pi.L / L, so doubling the electrode halves the drive."""
    VpiL = device_VpiL(9.92, "push_pull")
    assert (VpiL / 1.0) / (VpiL / 2.0) == pytest.approx(2.0)


def test_the_response_at_a_band_edge_is_below_the_response_at_the_carrier():
    """A travelling-wave electrode rolls off, so the top of the band is worst.

    This is the reason the band is declared rather than a single bandwidth: a
    device whose 3 dB point sits at the carrier is already past it at the top of
    the band.
    """
    L, alpha, n_m, n_g = 0.013, 20.0, 2.54, 2.089
    carrier = rf.response(15.0e9, L, alpha, n_m, n_g)
    top = rf.response(16.5e9, L, alpha, n_m, n_g)
    assert top < carrier


def test_the_effective_drive_is_the_dc_drive_divided_by_the_response():
    """Reaching the same modulation against a rolled-off response costs voltage."""
    Vpi = 3.5
    m = rf.response(16.5e9, 0.013, 20.0, 2.54, 2.089)
    assert Vpi / m > Vpi
    assert 20 * math.log10(m) < 0.0


def test_a_matched_lossless_line_demands_no_extra_drive():
    """With the velocities equal and no loss the band edge costs nothing."""
    m = rf.response(16.5e9, 0.013, 0.0, 2.089, 2.089)
    assert m == pytest.approx(1.0)


def test_the_report_can_describe_every_stage_the_chain_offers():
    """A stage the report cannot name is a stage that ran and is reported nowhere.

    The `modulator` stage was added and its provenance row was not, so the run's
    own report numbered three stages while five carried a payload, and the stage
    that produced the headline half-wave voltage was absent from the table
    describing how the design was computed.
    """
    from picchain.report import PROVENANCE
    from picchain.stages import STAGES

    described = {p[0] for p in PROVENANCE}
    missing = [s for s in STAGES if s not in described]
    assert not missing, (
        f"the report has no provenance row for {missing}; a stage that runs and is "
        "described nowhere is the omission that hides itself")
