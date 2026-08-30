"""Travelling-wave electrode, against results that are known in closed form."""

from __future__ import annotations

import math

import numpy as np

from picchain import rf


def test_a_line_without_dielectric_travels_at_the_speed_of_light():
    p = rf.line_parameters(c_per_m=1.0e-10, c_air_per_m=1.0e-10)
    assert abs(p["microwave_index"] - 1.0) < 1e-12
    assert abs(p["characteristic_impedance_ohm"] - 1.0 / (rf.C0 * 1.0e-10)) < 1e-6


def test_the_microwave_index_is_the_square_root_of_the_capacitance_ratio():
    p = rf.line_parameters(c_per_m=4.0e-10, c_air_per_m=1.0e-10)
    assert abs(p["microwave_index"] - 2.0) < 1e-12
    # and the impedance falls as the dielectric raises the capacitance
    q = rf.line_parameters(c_per_m=1.0e-10, c_air_per_m=1.0e-10)
    assert p["characteristic_impedance_ohm"] < q["characteristic_impedance_ohm"]


def test_a_matched_lossless_line_has_no_bandwidth_limit():
    """Equal velocities and no loss: the response is unity at every frequency."""
    for f in (1e9, 1e11, 1e13):
        assert abs(rf.response(f, 0.01, 0.0, 2.2, 2.2) - 1.0) < 1e-12


def test_loss_alone_gives_the_analytic_attenuation_factor():
    """With the velocities matched, m = (1 - exp(-aL)) / (aL)."""
    aL = 0.7
    L = 0.01
    m = rf.response(1e10, L, aL / L, 2.2, 2.2)
    assert abs(m - (1 - math.exp(-aL)) / aL) < 1e-12


def test_velocity_mismatch_alone_gives_the_sinc_walk_off():
    """With no loss, |m| = |sinc(dL/2)|, the first null at dL = 2 pi."""
    L, n_m, n_g = 0.01, 2.5, 2.2
    f_null = rf.C0 / ((n_m - n_g) * L)          # where d L = 2 pi
    assert rf.response(f_null, L, 0.0, n_m, n_g) < 1e-9
    half = rf.response(f_null / 2, L, 0.0, n_m, n_g)
    assert abs(half - abs(np.sinc(0.5))) < 1e-9


def test_the_skin_depth_scales_as_the_inverse_square_root_of_frequency():
    r1 = rf.skin_resistance_per_m(1e9, 4.1e7, 20e-6, 10e-6)
    r2 = rf.skin_resistance_per_m(4e9, 4.1e7, 20e-6, 10e-6)
    assert abs(r2 / r1 - 2.0) < 1e-9          # four times the frequency, twice the loss


def test_a_thin_conductor_stops_improving_with_frequency():
    """Once the skin depth exceeds the metal, the resistance is set by thickness."""
    thin = 0.05e-6
    r1 = rf.skin_resistance_per_m(1e8, 4.1e7, 20e-6, thin)
    r2 = rf.skin_resistance_per_m(1e9, 4.1e7, 20e-6, thin)
    assert abs(r1 - r2) < 1e-12


def test_bandwidth_falls_as_the_electrode_lengthens():
    def alpha(f):
        return rf.skin_resistance_per_m(f, 4.1e7, 20e-6, 0.9e-6) / (2 * 70.0)

    f_short = rf.bandwidth(0.002, alpha, 2.54, 2.21)
    f_long = rf.bandwidth(0.020, alpha, 2.54, 2.21)
    assert f_long < f_short


def test_the_bandwidth_is_resolved_and_not_quantised_on_the_walk():
    """Two lines differing slightly must not return an identical bandwidth.

    The coarse walk returned its first grid point, so any two crossings inside
    one 2 per cent step gave a figure identical in the last bit. Two electrode
    gaps whose capacitance, microwave index and conductor loss all differed
    reported the same bandwidth, and the equality was read as physics.
    """
    a = rf.bandwidth(0.010, lambda f: 20.0, 2.5600, 2.0893)
    b = rf.bandwidth(0.010, lambda f: 20.0, 2.5675, 2.0893)
    assert a != b
    # the slower line walks off sooner, so its bandwidth is the lower
    assert b < a
    assert abs(a - b) / a < 0.05          # and only slightly


def test_the_resolved_bandwidth_sits_on_the_declared_level():
    """The returned frequency is where the response actually crosses."""
    f = rf.bandwidth(0.013, lambda _f: 15.0, 2.5422, 2.0893)
    m = rf.response(f, 0.013, 15.0, 2.5422, 2.0893)
    assert abs(m - 1 / math.sqrt(2)) < 1e-3


def test_a_finer_tolerance_does_not_move_the_answer_materially():
    """The default tolerance is fine enough for the figure to be quoted."""
    coarse = rf.bandwidth(0.013, lambda _f: 15.0, 2.5422, 2.0893, tol=1e-4)
    fine = rf.bandwidth(0.013, lambda _f: 15.0, 2.5422, 2.0893, tol=1e-7)
    assert abs(coarse - fine) / fine < 1e-3
