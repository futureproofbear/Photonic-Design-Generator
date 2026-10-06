"""A corner is judged on every target row its metrics carry.

The grader once mapped each metric to the last row declared on it, so a
metric carried both as a `must` band and as an `info` tolerance was judged at
`info` alone and its `must` band was never applied at any corner.
"""
from picchain.cli import _judge_corner
from picchain.config import Target

KAPPA = "grating.kappa_per_cm"
ROWS = [Target(metric=KAPPA, min=1.56, max=2.18, severity="must"),
        Target(metric=KAPPA, value=1.9, rel_tol=0.10, severity="info")]


def _judge(value, rows=ROWS):
    return _judge_corner([KAPPA], rows, {KAPPA: value}.get)


def test_must_band_is_applied_when_an_info_row_follows_it():
    must, should, judged = _judge(1.43)
    assert must == [KAPPA] and should == [] and judged == 1


def test_must_band_is_applied_in_either_declaration_order():
    must, _, _ = _judge(2.32, rows=list(reversed(ROWS)))
    assert must == [KAPPA]


def test_info_row_alone_does_not_fail_the_corner():
    # 2.15 is inside the must band and outside the 10 per cent tolerance.
    must, should, judged = _judge(2.15)
    assert must == [] and should == [] and judged == 1


def test_should_row_is_reported_when_the_must_row_is_met():
    rows = [Target(metric=KAPPA, min=1.0, severity="must"),
            Target(metric=KAPPA, max=2.0, severity="should")]
    must, should, _ = _judge(2.1, rows=rows)
    assert must == [] and should == [KAPPA]
