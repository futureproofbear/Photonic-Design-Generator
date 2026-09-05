"""A computed coupling is graded against a figure the design actually states.

`cavity.rsoa.coupling_loss_dB_per_facet` belongs to the reflective gain chip of
a laser. On a design declaring no cavity it is a schema default, so comparing a
computed coupling against it grades the geometry on a number nobody wrote for
it. The first design to reach this stage without a cavity was a modulator test
chip coupling to a lensed fibre, whose computed 1.93 dB was compared against the
default 1.50 and passed, the difference falling inside the 0.5 dB deadband.
"""

from pathlib import Path

from picchain.stages import s11_facet

SOURCE = Path(s11_facet.__file__).read_text(encoding="utf-8")


def test_a_design_without_a_cavity_is_not_graded_against_the_gain_chip_figure():
    assert "if not design.cavity.enabled:" in SOURCE
    assert '"assumption_source"' in SOURCE
    # the laser comparisons remain, on the branch that has a laser
    assert "elif payload[\"total_loss_dB\"] > assumed + 0.5:" in SOURCE
    assert "assumption_is_pessimistic_by_dB" in SOURCE


def test_the_assumed_figure_is_cleared_rather_than_left_misleading():
    """Recording the default beside the computed figure invites a reader to
    compare them, which is the thing the branch exists to prevent."""
    i = SOURCE.index("if not design.cavity.enabled:")
    block = SOURCE[i:i + 900]
    assert '"assumed_loss_dB_in_design"] = None' in block
