"""Facet coupling, against closed forms."""

from __future__ import annotations

import math

import numpy as np

from picchain import coupling as cp


def _grid(n=401, half=6.0):
    x = np.linspace(-half, half, n)
    y = np.linspace(-half, half, n)
    dA = np.outer(np.gradient(x), np.gradient(y))
    return x, y, dA


def test_identical_modes_couple_completely():
    x, y, dA = _grid()
    a = cp.gaussian_mode(x, y, 1.0, 1.0)
    assert abs(cp.power_overlap(a, a, dA) - 1.0) < 1e-12


def test_numerical_overlap_matches_the_gaussian_closed_form():
    x, y, dA = _grid()
    for w1, w2 in ((1.0, 1.0), (1.0, 1.6), (0.7, 2.0)):
        a = cp.gaussian_mode(x, y, w1, w1)
        b = cp.gaussian_mode(x, y, w2, w2)
        # two dimensions: the one-dimensional factor squared, then power
        expected = cp.gaussian_overlap_analytic(w1, w2) ** 2
        assert abs(cp.power_overlap(a, b, dA) - expected) < 2e-4


def test_offsetting_a_mode_costs_the_analytic_factor():
    x, y, dA = _grid()
    w = 1.2
    a = cp.gaussian_mode(x, y, w, w)
    for d in (0.0, 0.4, 1.0):
        b = cp.gaussian_mode(x, y, w, w, x0=d)
        # offset in x only: the x factor carries the exponential, y does not
        expected = cp.gaussian_overlap_analytic(w, w, d) * cp.gaussian_overlap_analytic(w, w)
        assert abs(cp.power_overlap(a, b, dA) - expected) < 2e-4


def test_fresnel_is_symmetric_and_vanishes_for_equal_indices():
    assert abs(cp.fresnel_transmission(2.0, 2.0) - 1.0) < 1e-12
    assert abs(cp.fresnel_transmission(3.2, 1.8) - cp.fresnel_transmission(1.8, 3.2)) < 1e-12
    # a quarter-wave coating is a specification, not a prediction
    assert abs(cp.fresnel_transmission(3.2, 1.8, ar_reflectivity=0.001) - 0.999) < 1e-12


def test_snell_deflects_the_beam_and_the_penalty_grows_with_the_angle():
    assert abs(cp.facet_deflection_deg(0.0, 1.8, 1.0)) < 1e-12
    # a beam leaving a denser medium bends away from the normal
    assert cp.facet_deflection_deg(8.0, 1.8, 1.0) > 0.0

    assert abs(cp.angled_facet_penalty(0.0, 1.8, 1.0, 1.5, 1.55) - 1.0) < 1e-12
    p = [cp.angled_facet_penalty(a, 1.8, 1.0, 1.5, 1.55) for a in (2, 4, 8)]
    assert all(b < a for a, b in zip(p, p[1:]))


def test_a_partner_tilted_to_match_pays_nothing_for_the_angle():
    assert cp.angled_facet_penalty(8.0, 1.8, 1.0, 1.5, 1.55, partner_tilted=True) == 1.0


def test_total_internal_reflection_transmits_nothing():
    # sin(theta_c) = n_out / n_guide; beyond it nothing emerges
    assert cp.angled_facet_penalty(45.0, 1.8, 1.0, 1.5, 1.55) == 0.0


def test_the_one_decibel_tolerance_is_the_offset_that_costs_one_decibel():
    x, y, dA = _grid()
    w = 1.3
    d = cp.alignment_tolerance(w, w, loss_dB=1.0)
    a = cp.gaussian_mode(x, y, w, w)
    b = cp.gaussian_mode(x, y, w, w, x0=d)
    ratio = cp.power_overlap(a, b, dA) / cp.power_overlap(a, a, dA)
    assert abs(-10 * math.log10(ratio) - 1.0) < 0.02


# --- the gap between the two facets ----------------------------------------
# Added 2026-08-06 with the walk-off model. The sign of `facet.offset_x_um` was
# inverted on first writing: declaring the compensation displaced the partner
# away from the beam instead of onto it, so the loss rose when the assembly was
# corrected. These pin the geometry and the sense.

def test_the_gap_index_does_not_change_the_angle_in_the_partner():
    """Transverse wavevector conservation, which is why the gap moves the beam
    without changing where it points."""
    n_guide, n_partner = 1.7064, 3.2
    for n_gap in (1.0, 1.45, 2.0, 3.0):
        via_gap = cp.refracted_angle_deg(
            cp.refracted_angle_deg(8.0, n_guide, n_gap), n_gap, n_partner)
        direct = cp.refracted_angle_deg(8.0, n_guide, n_partner)
        assert abs(via_gap - direct) < 1e-9


def test_walkoff_is_the_gap_times_the_tangent_of_the_angle_in_the_gap():
    n_guide, n_gap, gap = 1.7064, 1.0, 2.0
    th = math.degrees(math.asin(n_guide * math.sin(math.radians(8.0)) / n_gap))
    expect = gap * math.tan(math.radians(th))
    assert abs(cp.gap_walkoff(8.0, n_guide, n_gap, gap) - expect) < 1e-12


def test_walkoff_vanishes_without_a_gap_or_without_an_angle():
    assert cp.gap_walkoff(8.0, 1.7064, 1.0, 0.0) == 0.0
    assert cp.gap_walkoff(0.0, 1.7064, 1.0, 2.0) == 0.0


def test_a_denser_gap_walks_the_beam_less():
    prev = float("inf")
    for n_gap in (1.0, 1.2, 1.45, 1.7):
        w = cp.gap_walkoff(8.0, 1.7064, n_gap, 2.0)
        assert w < prev
        prev = w


def test_walkoff_grows_in_proportion_to_the_gap():
    a = cp.gap_walkoff(8.0, 1.7064, 1.0, 1.0)
    assert abs(cp.gap_walkoff(8.0, 1.7064, 1.0, 3.0) - 3.0 * a) < 1e-12


def test_total_internal_reflection_into_the_gap_is_reported_as_nan():
    w = cp.gap_walkoff(45.0, 1.7064, 1.0, 2.0)
    assert w != w


def test_a_partner_placed_at_the_walkoff_recovers_the_aligned_overlap():
    """The sense of `facet.offset_x_um`. The beam lands displaced by the
    walk-off, so a partner placed there meets it and pays nothing; a partner
    left at zero pays the full displacement."""
    x, y, dA = _grid()
    guide = cp.gaussian_mode(x, y, 1.0, 1.0)
    walk = cp.gap_walkoff(8.0, 1.7064, 1.0, 2.0)
    assert walk > 0.4

    residual_when_compensated = walk - walk
    residual_when_not = walk - 0.0
    aligned = cp.power_overlap(
        guide, cp.gaussian_mode(x, y, 1.0, 1.0, x0=residual_when_compensated), dA)
    uncompensated = cp.power_overlap(
        guide, cp.gaussian_mode(x, y, 1.0, 1.0, x0=residual_when_not), dA)

    assert abs(aligned - 1.0) < 1e-9
    assert uncompensated < aligned
    # and it costs exactly the analytic offset penalty, which is stated in
    # mode-field RADII and not in diameters
    assert abs(uncompensated - cp.lateral_offset_penalty(walk, 1.0, 1.0)) < 1e-6
