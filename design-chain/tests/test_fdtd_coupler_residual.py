"""A unitarity guard set against unity is silent on every weak coupling.

The coupler solve checks that its two ports account for the input. The check was
absolute: a shortfall above one per cent of the input raised a finding. A point
coupler removes a small fraction of the input by design, so the shortfall falls
with the coupling and the guard falls silent exactly where the measurement
becomes hardest.

Measured across four gaps on one ring, with the coupling falling by three orders:

    gap um   kappa^2       residual    residual / kappa^2   absolute guard
    0.5      2.333816e-1   6.18768e-2  26.5 %               raised
    1.0      3.018435e-2   7.98510e-3  26.5 %               silent
    1.5      3.653423e-3   7.81800e-4  21.4 %               silent
    2.0      3.871091e-4   1.34600e-4  34.8 %               silent

The residual held between a fifth and 35 per cent of the coupling throughout
while falling by a factor of 460 in absolute terms. That is the signature of a
systematic, and the absolute guard reported it on the one gap whose coupling was
two orders too strong to be of any use.
"""

from __future__ import annotations

from pathlib import Path

from picchain.stages import s09_fdtd

SOURCE = Path(s09_fdtd.__file__).read_text(encoding="utf-8")


def test_the_residual_is_reported_as_a_fraction_of_the_coupling():
    assert '"unitarity_residual_over_kappa2"' in SOURCE


def test_a_finding_is_raised_on_the_relative_residual_and_not_only_the_absolute():
    assert "fdtd.coupler_residual_against_the_coupling" in SOURCE
    assert "residual / kappa2 > 0.05" in SOURCE


def test_the_absolute_guard_remains():
    """The two answer different questions and both are kept.

    The absolute guard asks whether the solve conserved power. The relative one
    asks whether it measured the coupling. A solve can pass the first and fail
    the second, which is the case this was written for.
    """
    assert "fdtd.coupler_unitarity" in SOURCE
    assert "residual > 0.01" in SOURCE


def test_the_relative_guard_would_have_caught_the_three_the_absolute_one_missed():
    """The arithmetic of the table above, evaluated against both thresholds."""
    rows = [(2.333816e-1, 6.18768e-2), (3.018435e-2, 7.98510e-3),
            (3.653423e-3, 7.81800e-4), (3.871091e-4, 1.34600e-4)]
    absolute = [r > 0.01 for _, r in rows]
    relative = [r / k > 0.05 for k, r in rows]
    assert absolute == [True, False, False, False]
    assert relative == [True, True, True, True]
