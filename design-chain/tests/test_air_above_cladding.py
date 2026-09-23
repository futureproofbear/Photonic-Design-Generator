"""Air above the declared cladding, in the cross-section the RF problem is solved on.

The cross-section's background is the cladding material and the optical
window stops inside the cladding, so the optical problem never needed an air
shape. The RF problem pads its window by tens of micrometres, and until
2026-09-23 that padding was cladding oxide to the top edge of the window:
the electrostatic solve saw 40 um of permittivity 3.9 above a stack that
declares 2 um of it. On one gsg line that put the microwave index at 2.28
where a full-wave solve of the same line read 2.12 to 2.14, and the impedance
at 32.3 ohm where it read 35.5. Air is now drawn wherever the window reaches
above the declared cladding, and nowhere else.
"""
from __future__ import annotations

from picchain.geometry import build_grid, edbr_cross_section, material_mask


def _section(**kw):
    args = dict(
        film_material="LiTaO3", film_thickness_um=0.30, etch_depth_um=0.18,
        wg_top_width_um=0.9, sidewall_deg=70.0, box_thickness_um=7.0,
        clad_thickness_um=2.0, electrodes=True, electrode_gap_um=4.5,
        electrode_width_um=60.0, electrode_thickness_um=0.9,
        electrode_topology="gsg", ground_width_um=40.0, slab_offset_um=6.0,
        include_substrate=True, box_model_depth_um=7.0)
    args.update(kw)
    return edbr_cross_section(**args)


def test_the_rf_window_carries_air_above_the_declared_cladding():
    xs = _section(window_pad_x_um=40.0, window_pad_y_um=40.0)
    assert "Air" in xs.materials_used()
    grid = build_grid(xs, 0.05, 1.0, 0.6)
    air = material_mask(xs, grid, "Air", subsample=3)
    ix = int(abs(grid.x - 0.0).argmin())
    # just above the cladding top at 2.3 um: air; just below it: cladding
    assert air[ix, int(abs(grid.y - 2.6).argmin())] > 0.99
    assert air[ix, int(abs(grid.y - 2.0).argmin())] < 0.01
    # and the padded region far above is air to the window's top
    assert air[ix, int(abs(grid.y - 30.0).argmin())] > 0.99


def test_the_optical_window_is_unchanged_because_it_stops_inside_the_cladding():
    xs = _section(window_pad_x_um=3.0, window_pad_y_um=0.0, electrodes=False, include_substrate=False,
                  box_model_depth_um=1.8)
    assert "Air" not in xs.materials_used()
    assert xs.window[3] <= 0.30 + 2.0 + 1e-9
