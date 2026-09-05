"""Measuring a written file, against shapes whose dimensions are known exactly."""

from __future__ import annotations

import sys
from pathlib import Path

import klayout.db as kdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from measure_layout import cut, inventory, widths_and_gaps  # noqa: E402

RIDGE, SLAB = (2, 10), (3, 10)


def write(tmp_path: Path, shapes: list[tuple[tuple[int, int], list[tuple[float, float]]]],
          name: str = "cell") -> str:
    """One top cell holding the given polygons, in micrometres."""
    ly = kdb.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)
    for (layer, datatype), points in shapes:
        idx = ly.layer(layer, datatype)
        pts = [kdb.Point(int(round(x / ly.dbu)), int(round(y / ly.dbu))) for x, y in points]
        top.shapes(idx).insert(kdb.Polygon(pts))
    path = str(tmp_path / f"{name}.gds")
    ly.write(path)
    return path


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def test_a_straight_guide_measures_its_own_width(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 10, 0.35)),
                         (SLAB, rect(0, -6.35, 10, 6.35))])
    assert widths_and_gaps(cut(g, *RIDGE, "x", 5.0))[0] == pytest.approx([0.7])
    assert widths_and_gaps(cut(g, *SLAB, "x", 5.0))[0] == pytest.approx([12.7])


def test_two_guides_return_a_width_each_and_the_gap_between_them(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, 1.6, 10, 2.3)),
                         (RIDGE, rect(0, -2.3, 10, -1.6))])
    w, gaps = widths_and_gaps(cut(g, *RIDGE, "x", 5.0))
    assert w == pytest.approx([0.7, 0.7])
    assert gaps == pytest.approx([3.2])


def test_the_cut_window_is_a_window_and_not_a_micrometre(tmp_path):
    """A taper is measured where the cut is taken.

    The window was converted from nanometres by dividing by the database unit
    without first converting to micrometres, which made it a thousand times too
    wide. On a taper the bounding box of the intersection then returned the
    width one micrometre downstream: a 0.7 um tip on a taper widening by 42 nm
    per micrometre measured 0.742.
    """
    g = write(tmp_path, [(RIDGE, [(0, -0.35), (25, -0.875), (25, 0.875), (0, 0.35)])])
    assert widths_and_gaps(cut(g, *RIDGE, "x", 0.0))[0] == pytest.approx([0.7], abs=1e-3)
    assert widths_and_gaps(cut(g, *RIDGE, "x", 25.0))[0] == pytest.approx([1.75], abs=1e-3)
    assert widths_and_gaps(cut(g, *RIDGE, "x", 12.5))[0] == pytest.approx([1.225], abs=2e-3)


def test_a_horizontal_cut_measures_along_the_other_axis(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 10, 0.35)),
                         (RIDGE, rect(20, -0.35, 34, 0.35))])
    w, gaps = widths_and_gaps(cut(g, *RIDGE, "y", 0.0))
    assert w == pytest.approx([10.0, 14.0])
    assert gaps == pytest.approx([10.0])


def test_abutting_polygons_are_one_piece_and_not_two(tmp_path):
    """A taper drawn as a run of trapezoids is continuous material."""
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 5, 0.35)),
                         (RIDGE, rect(5, -0.35, 10, 0.35))])
    assert widths_and_gaps(cut(g, *RIDGE, "x", 5.0))[0] == pytest.approx([0.7])


def test_a_layer_that_holds_nothing_returns_nothing(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 10, 0.35))])
    assert cut(g, 20, 0, "x", 5.0) == []


def test_the_inventory_reports_area_and_extent(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 10, 0.35)),
                         (SLAB, rect(0, -6.35, 10, 6.35))])
    by_spec = {L.spec: L for L in inventory(g)}
    assert set(by_spec) == {"2/10", "3/10"}
    assert by_spec["2/10"].area_um2 == pytest.approx(7.0)
    assert by_spec["3/10"].area_um2 == pytest.approx(127.0)
    assert by_spec["2/10"].bbox_um == pytest.approx((0.0, -0.35, 10.0, 0.35))
    assert by_spec["2/10"].polygons == 1


def test_a_file_with_two_top_cells_is_refused(tmp_path):
    ly = kdb.Layout()
    ly.dbu = 0.001
    for name in ("a", "b"):
        c = ly.create_cell(name)
        c.shapes(ly.layer(2, 10)).insert(kdb.Box(0, 0, 1000, 1000))
    path = str(tmp_path / "two.gds")
    ly.write(path)
    with pytest.raises(ValueError, match="2 top cells"):
        inventory(path)


def test_an_axis_that_is_not_an_axis_is_refused(tmp_path):
    g = write(tmp_path, [(RIDGE, rect(0, -0.35, 10, 0.35))])
    with pytest.raises(ValueError, match="axis"):
        cut(g, *RIDGE, "z", 5.0)
