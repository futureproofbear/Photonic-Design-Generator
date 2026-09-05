"""Travelling-wave electrode, against results that are known in closed form."""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

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


# ---------------------------------------------------------------------------
# The far-end load. Until 2026-09-04 every electrode was graded as though its
# far end were matched to it, so a kit shipping terminated and unterminated
# variants of the same modulator described both by one bandwidth.
# ---------------------------------------------------------------------------


def test_a_matched_far_end_reproduces_the_single_wave_model_exactly():
    """The one case where the two expressions must agree in the last bits."""
    for f in (1e8, 1e9, 1e10, 5e10, 2e11):
        one = rf.response(f, 5e-3, 400.0, 2.26, 2.18)
        two = rf.response_loaded(f, 5e-3, 400.0, 2.26, 2.18, reflection=0.0)
        assert abs(one - two) < 1e-15


def test_an_open_far_end_doubles_the_drive_and_the_response_is_still_unity():
    """The normalisation is the lossless response at zero frequency, 1 + G."""
    assert abs(rf.response_loaded(0.0, 5e-3, 0.0, 2.26, 2.18, 1.0) - 1.0) < 1e-12
    assert abs(rf.response_loaded(0.0, 5e-3, 0.0, 2.26, 2.18, 0.0) - 1.0) < 1e-12
    assert abs(rf.response_loaded(0.0, 5e-3, 0.0, 2.26, 2.18, 0.4) - 1.0) < 1e-12


def test_the_returned_wave_is_a_walk_off_at_the_sum_of_the_indices():
    """The closed form, on a lossless velocity-matched line.

    With n_m = n_o the forward wave never walks off and contributes unity at
    every frequency. The returned wave walks off at 2 n_m, so the pair is

        |1 + G exp(-j t) sinc(t / 2) exp(j t / 2)| / (1 + G),
        t = 2 omega n_m L / c

    A matched line is flat here and an open one is not, which is the whole
    content of the change.
    """
    L, n = 4e-3, 2.2
    for f in (5e9, 2e10, 6e10):
        w = 2 * math.pi * f
        t = 2 * w * n * L / rf.C0
        u_b = 1j * t
        expect = abs(1.0 + 1.0 * cmath.exp(-u_b) * (cmath.exp(u_b) - 1.0) / u_b) / 2.0
        got = rf.response_loaded(f, L, 0.0, n, n, reflection=1.0)
        assert abs(got - expect) < 1e-12
        assert abs(rf.response_loaded(f, L, 0.0, n, n, reflection=0.0) - 1.0) < 1e-12


def test_an_open_far_end_costs_bandwidth():
    """The reflected wave nulls the drive at the input before the walk-off does."""
    L = 5e-3
    def alpha(f):
        return 60.0 * math.sqrt(f / 1e9)
    matched = rf.bandwidth(L, alpha, 2.2587, 2.1834, reflection=0.0)
    open_end = rf.bandwidth(L, alpha, 2.2587, 2.1834, reflection=1.0)
    assert open_end < matched
    assert 3.0 < matched / open_end < 6.0


def test_the_loss_is_not_divided_out_by_the_normalisation():
    """The reference is the lossless zero-frequency value and not this line's.

    Normalising by the response at the same attenuation removes the conductor
    loss from the result altogether, and the first version of this function did
    so: a 5 mm electrode reported 1.4 THz. The guard is that a lossy line has
    less bandwidth than a lossless one carrying the same walk-off.
    """
    L = 5e-3
    lossless = rf.bandwidth(L, lambda f: 0.0, 2.2587, 2.1834)
    lossy = rf.bandwidth(L, lambda f: 60.0 * math.sqrt(f / 1e9), 2.2587, 2.1834)
    assert lossy < lossless
    assert lossy < 1e11


def test_the_reflection_of_a_declared_load():
    assert rf.load_reflection(None, 40.0) == 0.0          # matched, by declaration
    assert rf.load_reflection(40.0, 40.0) == 0.0          # matched, by arithmetic
    assert rf.load_reflection(1e9, 40.0) == 1.0           # an open pad
    assert rf.load_reflection(0.0, 40.0) == -1.0          # a short
    assert abs(rf.load_reflection(50.0, 40.0) - 1.0 / 9.0) < 1e-12
    assert rf.load_reflection(50.0, 0.0) == 0.0           # no line to reflect from


def test_a_load_further_from_the_line_returns_more():
    z0 = 38.0
    prev = 0.0
    for load in (40.0, 60.0, 100.0, 1e4):
        g = rf.load_reflection(load, z0)
        assert g > prev
        prev = g


def test_the_two_references_differ_by_the_doubling_an_open_end_gives():
    """The whole content of the correction of 2026-09-04.

    Referred to its own zero-frequency value the open line looks ruined and
    referred to the incident wave it does not, because its own zero-frequency
    value is twice the matched line's.
    """
    L, a, n_m, n_o = 5e-3, 300.0, 2.28, 2.18
    for f in (1e8, 1e10, 1e11):
        own = rf.response_loaded(f, L, a, n_m, n_o, 1.0, "dc")
        inc = rf.response_loaded(f, L, a, n_m, n_o, 1.0, "incident")
        assert abs(inc / own - 2.0) < 1e-12
    # and at zero reflection the two references coincide
    for f in (1e8, 1e10):
        assert abs(rf.response_loaded(f, L, a, n_m, n_o, 0.0, "dc")
                   - rf.response_loaded(f, L, a, n_m, n_o, 0.0, "incident")) < 1e-12


def test_an_open_end_doubles_the_modulation_at_zero_frequency():
    L, n = 4e-3, 2.2
    assert abs(rf.response_loaded(0.0, L, 0.0, n, n, 1.0, "incident") - 2.0) < 1e-9
    assert abs(rf.response_loaded(0.0, L, 0.0, n, n, 0.0, "incident") - 1.0) < 1e-9


def test_a_reference_that_is_not_one_is_refused():
    with pytest.raises(ValueError, match="reference"):
        rf.response_loaded(1e10, 5e-3, 300.0, 2.28, 2.18, 1.0, "peak")


def test_a_matched_far_end_is_penalised_by_nothing():
    p = rf.far_end_penalty(5e-3, lambda f: 300.0, 2.28, 2.18, 0.0, 1e8, 2e11)
    assert p["worst_dB"] == 0.0
    assert p["best_dB"] == 0.0


def test_an_open_end_helps_at_low_frequency_and_costs_at_one_null():
    """The finding the self-referred bandwidth hid.

    An open end is worth 6 dB where the returned wave adds, which is the low
    frequency limit, and costs where it subtracts. A 3 dB bandwidth read off
    the self-referred response reports the first as though it were the second.
    """
    L = 5e-3
    def alpha(f):
        return 62.5 * (f / 1e10) ** 0.5

    p = rf.far_end_penalty(L, alpha, 2.2783, 2.1834, 1.0, 1e8, 2e11)
    assert 5.5 < p["best_dB"] < 6.1
    assert p["best_at_Hz"] < 1e9
    assert -3.0 < p["worst_dB"] < -0.5
    assert 5e9 < p["worst_at_Hz"] < 2e10
    # and the self-referred bandwidth is far below the frequency of that null
    f3 = rf.bandwidth(L, alpha, 2.2783, 2.1834, reflection=1.0)
    assert f3 < p["worst_at_Hz"]


def test_the_two_lines_converge_where_the_returned_wave_has_dephased():
    """Well above the null the open cell asks for the same drive as the matched one."""
    L = 5e-3
    def alpha(f):
        return 62.5 * (f / 1e10) ** 0.5

    for f in (5e10, 1e11, 2e11):
        m = rf.response_loaded(f, L, alpha(f), 2.2783, 2.1834, 0.0, "incident")
        o = rf.response_loaded(f, L, alpha(f), 2.2783, 2.1834, 1.0, "incident")
        assert abs(20 * math.log10(o / m)) < 0.5


def test_a_stub_beyond_the_modulation_section_moves_the_null():
    """The 220 um the drawn unterminated cell carries past its modulation section.

    The microwave crosses it twice and the optical carrier does not cross it at
    all, so it rotates the returned wave. It deepens the null and moves it down.
    """
    L = 5e-3
    def alpha(f):
        return 62.5 * (f / 1e10) ** 0.5

    bare = rf.far_end_penalty(L, alpha, 2.2783, 2.1834, 1.0, 1e8, 2e11)
    stubbed = rf.far_end_penalty(L, alpha, 2.2783, 2.1834, 1.0, 1e8, 2e11,
                                 stub_m=220e-6)
    assert stubbed["worst_at_Hz"] < bare["worst_at_Hz"]
    assert stubbed["worst_dB"] < bare["worst_dB"]


def test_a_stub_does_nothing_where_the_far_end_is_matched():
    """There is no returned wave for it to rotate."""
    L = 5e-3
    for f in (1e9, 1e10, 1e11):
        without = rf.response_loaded(f, L, 300.0, 2.28, 2.18, 0.0, "dc", 0.0)
        with_stub = rf.response_loaded(f, L, 300.0, 2.28, 2.18, 0.0, "dc", 5e-4)
        assert without == with_stub


def test_a_stub_leaves_the_zero_frequency_limit_alone():
    """It is a phase rotation, and at zero frequency there is no phase."""
    L = 5e-3
    assert abs(rf.response_loaded(0.0, L, 0.0, 2.28, 2.18, 1.0, "incident", 1e-3)
               - 2.0) < 1e-9
