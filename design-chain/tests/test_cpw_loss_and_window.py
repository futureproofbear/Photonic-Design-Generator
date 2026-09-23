"""The coplanar conductor loss with edge crowding, and the widened cross-section the window check poses.

Both were added on 2026-09-23 after a full-wave mode solve of a gsg line read
2.4 to 2.7 times the chain's uniform skin-depth attenuation, and after the same
comparison found the electrostatic window's Neumann wall moving the impedance
by 3.6 per cent when the padding was widened. The loss figures below are from
that solve of a 60 um signal, 4.5 um gaps and 0.9 um gold at 10 and 15 GHz:
2.54 and 2.93 dB/cm.
"""
from __future__ import annotations

import math

import pytest

from picchain import rf
from picchain.geometry import Shape, CrossSection, widen_cross_section

SIGMA = 4.1e7
S, W, T = 60e-6, 4.5e-6, 0.9e-6
EPS_EFF = 2.05 ** 2


def test_the_finite_thickness_surface_resistance_has_the_two_limits():
    f = 1e10
    delta = math.sqrt(2.0 / (2 * math.pi * f * rf.MU0 * SIGMA))
    thick = rf.surface_resistance_finite(f, SIGMA, 20 * delta)
    assert thick == pytest.approx(1.0 / (SIGMA * delta), rel=1e-6)
    thin = rf.surface_resistance_finite(f, SIGMA, 0.02 * delta)
    assert thin == pytest.approx(1.0 / (SIGMA * 0.02 * delta), rel=0.02)
    # one skin depth: above the thick figure, below the thin one
    one = rf.surface_resistance_finite(f, SIGMA, delta)
    assert thick < one < 1.0 / (SIGMA * delta) * 1.5


def test_the_coplanar_loss_exceeds_the_uniform_model_and_lands_near_the_full_wave_figure():
    """On the measured line the closed form is within 30 per cent of the full-wave solve."""
    a10 = rf.cpw_conductor_loss_np_per_m(1e10, SIGMA, S, W, T, EPS_EFF) * rf.NEPER_TO_DB / 100
    a15 = rf.cpw_conductor_loss_np_per_m(1.5e10, SIGMA, S, W, T, EPS_EFF) * rf.NEPER_TO_DB / 100
    assert 2.54 * 0.7 < a10 < 2.54 * 1.3
    assert 2.93 * 0.7 < a15 < 2.93 * 1.3
    # and it is above the uniform skin-depth figure on the same line at the same impedance
    R = rf.skin_resistance_per_m(1e10, SIGMA, S, T, n_conductors=1.5)
    uniform = R / (2 * 36.0) * rf.NEPER_TO_DB / 100
    assert a10 > 1.5 * uniform


def test_the_coplanar_loss_rises_as_the_gap_closes_and_as_the_metal_thins():
    base = rf.cpw_conductor_loss_np_per_m(1e10, SIGMA, S, W, T, EPS_EFF)
    assert rf.cpw_conductor_loss_np_per_m(1e10, SIGMA, S, W / 2, T, EPS_EFF) > base
    assert rf.cpw_conductor_loss_np_per_m(1e10, SIGMA, S, W, T / 3, EPS_EFF) > base
    # thick metal: the frequency law tends to the square root
    thick = [rf.cpw_conductor_loss_np_per_m(f, SIGMA, S, W, 20e-6, EPS_EFF) for f in (1e10, 4e10)]
    assert thick[1] / thick[0] == pytest.approx(2.0, rel=0.08)


def test_widening_stretches_the_blanket_layers_and_leaves_the_features_alone():
    xs = CrossSection(background="SiO2", window=(-5.0, 5.0, -2.0, 3.0))
    xs.add(Shape.rect("Si", -6.0, 6.0, -3.0, -2.0, "substrate"))          # blanket: reaches both limits
    xs.add(Shape.rect("LiTaO3", -1.0, 1.0, 0.0, 0.12, "slab"))              # a slab of finite offset
    xs.add(Shape.rect("Au", 2.0, 4.0, 0.12, 1.02, "metal"))                 # a conductor
    w = widen_cross_section(xs, 10.0, 20.0)
    assert w.window == (-15.0, 15.0, -2.0, 23.0)
    sub = next(s for s in w.shapes if s.name == "substrate"); x0, x1, _, _ = sub.bbox()
    assert x0 <= -15.0 and x1 >= 15.0
    slab = next(s for s in w.shapes if s.name == "slab"); assert slab.bbox()[:2] == (-1.0, 1.0)
    metal = next(s for s in w.shapes if s.name == "metal"); assert metal.bbox() == (2.0, 4.0, 0.12, 1.02)
    assert w.materials_used() == xs.materials_used()
