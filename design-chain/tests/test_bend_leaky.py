"""The leaky bend by finite elements with an absorbing margin.

Added 2026-09-23. The conformal-transformation bend stage gives an index shift
and no loss, and returns no answer once the transformed cladding exceeds the
core index in its window. The finite-element solve on a widened window with an
imaginary permittivity ramp at its lateral edges returns a complex effective
index at every radius, and the loss it implies fell to a floor at wide radii
and rose steeply at a tight one on the ridge it was first run on.
"""
from __future__ import annotations

import pytest

from picchain.geometry import Shape, CrossSection, widen_cross_section
from picchain.solvers import femmode

pytestmark = pytest.mark.skipif(not femmode.available(), reason=femmode.unavailable_reason() or "no femwell")


def _ridge():
    # a strongly guiding ridge so that the mesh can stay coarse: n 2.0 core in 1.44 oxide
    xs = CrossSection(background="SiO2", window=(-3.0, 3.0, -1.5, 1.5), name="ridge")
    xs.add(Shape.rect("LiTaO3", -4.0, 4.0, 0.0, 0.12, "slab"))
    xs.add(Shape.rect("LiTaO3", -0.45, 0.45, 0.12, 0.30, "ridge"))
    return xs, {"SiO2": 1.444 ** 2, "LiTaO3": 2.12 ** 2}


def _te(res):
    # the absorbing margin carries modes of its own with imaginary indices of
    # order one; the guided or leaky mode is the TE mode with the smallest
    cands = [q for q in res.modes if q.te_fraction > 0.5]
    return min(cands, key=lambda q: abs(q.n_eff_imag))


def test_a_wide_bend_carries_the_straight_index_and_a_tight_one_radiates():
    xs, eps = _ridge()
    wide = widen_cross_section(xs, 4.0, 0.0)
    kw = dict(num_modes=4, element_order=1, resolution_max_um=0.4, fine_resolution_um=0.04,
              fine_distance_um=0.5, absorber_um=2.0, absorber_strength=0.3, n_guess=1.7)
    straight = _te(femmode.solve_cross_section(wide, eps, 1.55, **kw))
    gentle = _te(femmode.solve_cross_section(wide, eps, 1.55, radius_um=2000.0, **kw))
    tight = _te(femmode.solve_cross_section(wide, eps, 1.55, radius_um=15.0, **kw))
    assert abs(gentle.n_eff - straight.n_eff) < 2e-4
    assert gentle.loss_dB_per_m(1.55) < 10.0                       # at the floor of the absorber
    assert tight.n_eff > straight.n_eff                            # the mode moves to the outer wall
    assert tight.loss_dB_per_m(1.55) > 50 * max(gentle.loss_dB_per_m(1.55), 1e-3)


def test_the_absorber_is_confined_to_the_margin():
    """With no margin the loss is zero to numerical precision, the wall being electric."""
    xs, eps = _ridge()
    res = femmode.solve_cross_section(xs, eps, 1.55, num_modes=2, element_order=1, resolution_max_um=0.4,
                                      fine_resolution_um=0.04, fine_distance_um=0.5, radius_um=15.0, n_guess=1.7)
    assert abs(_te(res).n_eff_imag) < 1e-9
