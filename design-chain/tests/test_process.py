"""The drawn, printed and nominal geometries.

These are algebraic identities rather than simulation results, and they are the
identities on which an orderable mask rests. A sign error in any one of them
produces a mask that prints to the wrong dimension while every downstream figure
continues to look correct.
"""

from __future__ import annotations

import pytest

from picchain import process
from picchain.config import Design

NOMINAL = dict(
    wg_top_width_um=1.0,
    post_width_um=0.30,
    post_length_um=0.30,
    post_gap_um=0.63,
    etch_depth_um=0.20,
    electrode_gap_um=7.0,
    electrode_width_um=20.0,
)
BIAS = 0.040


def _resolve(frame, **kw):
    return process.resolve(frame=frame, **{**NOMINAL, **kw})


# --------------------------------------------------------------------------
# 1. no bias: the three frames coincide
# --------------------------------------------------------------------------
def test_zero_bias_leaves_every_frame_identical():
    frames = [_resolve(f) for f in ("nominal", "drawn", "printed")]
    for key in NOMINAL:
        values = {getattr(g, key) for g in frames}
        assert len(values) == 1, f"{key} differs across frames at zero bias"


def test_a_design_without_a_process_block_is_the_identity():
    d = Design(meta={"name": "x"}, grating={"period_um": 1.28})
    assert process.is_identity(d)
    assert process.geometry(d, "drawn") == process.geometry(d, "printed").__class__(
        **{**process.geometry(d, "printed").as_dict(), "frame": "drawn"}
    )


# --------------------------------------------------------------------------
# 2. a gap moves opposite to a width, which is the identity most easily lost
# --------------------------------------------------------------------------
def test_a_width_grows_and_a_gap_closes_under_a_positive_bias():
    """Both facing edges advance into a gap, so it loses the full bias while a
    width gains it. Reading the gap as though it followed the width is the
    error this test exists to catch."""
    printed = _resolve("printed", bias_um={"WG": BIAS}, precompensate=False)
    assert printed.wg_top_width_um == pytest.approx(NOMINAL["wg_top_width_um"] + BIAS)
    assert printed.post_width_um == pytest.approx(NOMINAL["post_width_um"] + BIAS)
    assert printed.post_gap_um == pytest.approx(NOMINAL["post_gap_um"] - BIAS)


def test_the_metal_bias_moves_the_electrodes_and_not_the_guide():
    printed = _resolve("printed", bias_um={"METAL": 0.10}, precompensate=False)
    assert printed.electrode_width_um == pytest.approx(NOMINAL["electrode_width_um"] + 0.10)
    assert printed.electrode_gap_um == pytest.approx(NOMINAL["electrode_gap_um"] - 0.10)
    assert printed.wg_top_width_um == pytest.approx(NOMINAL["wg_top_width_um"])


# --------------------------------------------------------------------------
# 3. pre-compensation is defined by the property it must have
# --------------------------------------------------------------------------
def test_precompensation_lands_the_printed_geometry_on_the_nominal_one():
    """This is the whole purpose of the operation: the drawing is displaced so
    that the wafer is not."""
    drawn = _resolve("drawn", bias_um={"WG": BIAS, "METAL": 0.10}, precompensate=True)
    printed = _resolve("printed", bias_um={"WG": BIAS, "METAL": 0.10}, precompensate=True)
    for key, value in NOMINAL.items():
        assert getattr(printed, key) == pytest.approx(value), key
    # and the drawing itself is displaced, or nothing was compensated
    assert drawn.wg_top_width_um == pytest.approx(NOMINAL["wg_top_width_um"] - BIAS)
    assert drawn.post_gap_um == pytest.approx(NOMINAL["post_gap_um"] + BIAS)


def test_without_precompensation_the_drawing_is_nominal_and_the_wafer_is_not():
    drawn = _resolve("drawn", bias_um={"WG": BIAS}, precompensate=False)
    printed = _resolve("printed", bias_um={"WG": BIAS}, precompensate=False)
    for key, value in NOMINAL.items():
        assert getattr(drawn, key) == pytest.approx(value), key
    assert printed.post_gap_um != pytest.approx(NOMINAL["post_gap_um"])


# --------------------------------------------------------------------------
# 4. a vertical bias cannot be compensated by a drawing
# --------------------------------------------------------------------------
def test_the_etch_depth_bias_reaches_the_wafer_and_not_the_mask():
    drawn = _resolve("drawn", depth_bias_um=0.005)
    printed = _resolve("printed", depth_bias_um=0.005)
    assert drawn.etch_depth_um == pytest.approx(NOMINAL["etch_depth_um"])
    assert printed.etch_depth_um == pytest.approx(NOMINAL["etch_depth_um"] + 0.005)


# --------------------------------------------------------------------------
# 5. a feature that closes is refused rather than clipped
# --------------------------------------------------------------------------
def test_a_bias_that_closes_a_gap_is_refused():
    with pytest.raises(ValueError, match="closes"):
        _resolve("printed", bias_um={"WG": 0.80}, precompensate=False)


# --------------------------------------------------------------------------
# 6. the bias is the quantity the sensitivity analysis already measured
# --------------------------------------------------------------------------
def test_a_twenty_nanometre_bias_moves_the_gap_by_twenty_nanometres():
    """The recorded decay of d(ln dn_eff)/d(gap) is about -5.4 /um, so this
    displacement is an 11 % change in the coupling constant. The test fixes the
    displacement itself, the sensitivity to it being the grating stage's."""
    printed = _resolve("printed", bias_um={"WG": 0.020}, precompensate=False)
    assert NOMINAL["post_gap_um"] - printed.post_gap_um == pytest.approx(0.020)


def test_summary_reports_all_three_frames():
    d = Design(meta={"name": "x"}, grating={"period_um": 1.28},
               process={"bias_um": {"WG": BIAS}})
    s = process.summary(d)
    assert not s["identity"]
    assert set(s) >= {"nominal", "drawn", "printed", "bias_um", "precompensate"}
    assert s["printed"]["post_gap_um"] == pytest.approx(s["nominal"]["post_gap_um"])
    assert s["drawn"]["post_gap_um"] == pytest.approx(s["nominal"]["post_gap_um"] + BIAS)
