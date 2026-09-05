"""The die that is emitted is the die that was declared, ring or no ring.

The seal-ring width was deducted from the declared die whatever
`reticle.seal_ring.enabled` said, while the die edge was placed from that width
only where the ring is drawn. A design switching the ring off therefore emitted
a die two ring-widths smaller than it declared, and the footprint check passed
it because that check tested only for a die too large. A process offering a
fixed set of die sizes takes the drawn boundary, so the shortfall is a refusal
at submission.

The footprint is read off the stage, and the boundary is measured off the
polygons the stage wrote, rather than either being reconstructed from the fields
that produced them.
"""

from __future__ import annotations

import klayout.db as db
import pytest

from picchain.artifacts import RunContext
from picchain.config import Design
from picchain.stages import s05_layout, s14_reticle

DIE_W, DIE_H = 10100.0, 5050.0
RING_W = 20.0
CHIP_OUTER = (6, 1)


def _die(tmp_path, ring: bool):
    d = Design.model_validate({
        "meta": {"name": "footprint", "title": "A declared die"},
        "waveguide": {"top_width_um": 0.7, "wavelength_um": 1.31},
        "grating": {"enabled": True, "period_um": 0.4322, "length_um": 200.0},
        "layout": {"layer_map": {"WG": [2, 10], "SLAB": [3, 10], "METAL": [20, 0],
                                 "PAD": [21, 0], "SEAL": [200, 0], "MARK": [201, 0],
                                 "DICE": [202, 0], "FACET": [203, 0],
                                 "ORIENT": [204, 0], "FILL": [205, 0],
                                 "LABEL": [4, 0], "FLOORPLAN": [206, 0],
                                 "CHIP_INNER": [6, 0], "CHIP_OUTER": list(CHIP_OUTER)}},
        "reticle": {
            "enabled": True,
            "die_width_um": DIE_W,
            "die_height_um": DIE_H,
            "dicing_lane_um": 0.0,
            "seal_ring": {"enabled": ring, "width_um": RING_W},
            "chip_frame": {"enabled": True},
        },
    })
    ctx = RunContext(design_dir=tmp_path, run_id=f"die_{ring}").ensure()
    s05_layout.run(d, ctx, None)
    return d, ctx, s14_reticle.run(d, ctx, None)


@pytest.mark.parametrize("ring", [True, False])
def test_the_reported_footprint_is_the_declared_footprint(tmp_path, ring):
    _, _, payload = _die(tmp_path, ring)
    assert payload["die_width_um"] == pytest.approx(DIE_W, abs=1e-6)
    assert payload["die_height_um"] == pytest.approx(DIE_H, abs=1e-6)


@pytest.mark.parametrize("ring", [True, False])
def test_the_drawn_boundary_is_the_declared_footprint(tmp_path, ring):
    """Measured off the chip boundary the stage wrote, and not off its report."""
    _, ctx, _ = _die(tmp_path, ring)
    gds = next(p for p in ctx.run_dir.rglob("*.gds") if "die" in p.name.lower())
    layout = db.Layout()
    layout.read(str(gds))
    idx = layout.layer(*CHIP_OUTER)
    region = db.Region(layout.top_cell().begin_shapes_rec(idx)).merged()
    assert not region.is_empty(), "the die carries no chip boundary"
    box = region.bbox()
    assert box.width() * layout.dbu == pytest.approx(DIE_W, abs=0.002)
    assert box.height() * layout.dbu == pytest.approx(DIE_H, abs=0.002)


def test_a_die_smaller_than_declared_is_reported(tmp_path):
    """The check reads in both directions.

    The condition is forced by declaring a die the content does not fill and
    then shrinking what the stage draws, which is what the defect did silently.
    """
    d, ctx, payload = _die(tmp_path, ring=False)
    keys = [w.get("key") for w in ctx.warning_records]
    assert "reticle.die_smaller_than_declared" not in keys, (
        "a die drawn to its declared size must raise no shortfall")
