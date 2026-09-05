"""The die's thermal response to a heater, checked against what can be solved by hand."""
from __future__ import annotations

import math

import numpy as np

from picchain import thermal as th


def test_a_uniform_slab_under_uniform_flux_rises_linearly():
    """One layer, flux over the whole top: the rise is q H / k exactly.

    The finite-volume assembly is checked against the one case with a closed
    form before it is trusted on a stack. A heater as wide as the model makes
    the problem one-dimensional.
    """
    H, k = 100.0, 10.0
    stack = th.HeaterStack(layers=[th.Layer("slab", H, k)], half_width_um=50.0,
                           heater_width_um=100.0)
    r = th.solve(stack, power_W_per_m=1.0, dx_min_um=2.0, dz_min_um=2.0)
    q = 1.0 / (100.0e-6)                     # W/m spread over the 100 um width
    expect = q * H * 1e-6 / k
    assert abs(r["rise_at_top_under_heater_K"] / expect - 1.0) < 1e-3


def test_the_rise_is_linear_in_the_power():
    """Conduction is linear, so doubling the drive doubles every temperature."""
    stack = th.HeaterStack(layers=[th.Layer("Si", 100.0, th.K_SI), th.Layer("ox", 5.0, th.K_SIO2)],
                           half_width_um=300.0, heater_width_um=2.0, probes_um=[50.0])
    a = th.solve(stack, 1.0, dx_min_um=0.5, dz_min_um=0.25)
    b = th.solve(stack, 2.0, dx_min_um=0.5, dz_min_um=0.25)
    assert abs(b["rise_at_guide_K"] / a["rise_at_guide_K"] - 2.0) < 1e-9
    assert abs(b["probes"]["50"] / a["probes"]["50"] - 2.0) < 1e-9


def test_the_rise_falls_with_distance_and_a_thicker_oxide_raises_it():
    """Two things a reader can predict without solving.

    Heat spreads, so the film is cooler further from the wire. And oxide is a
    poor conductor, so a thicker buried oxide under a heated film holds more of
    the rise in the film.
    """
    base = [th.Layer("Si", 200.0, th.K_SI), th.Layer("box", 4.0, th.K_SIO2),
            th.Layer("film", 0.3, th.K_LITAO3), th.Layer("clad", 2.0, th.K_SIO2)]
    thick = [th.Layer("Si", 200.0, th.K_SI), th.Layer("box", 8.0, th.K_SIO2),
             th.Layer("film", 0.3, th.K_LITAO3), th.Layer("clad", 2.0, th.K_SIO2)]
    s1 = th.HeaterStack(layers=base, half_width_um=400.0, heater_width_um=1.5, probes_um=[20.0, 100.0])
    s2 = th.HeaterStack(layers=thick, half_width_um=400.0, heater_width_um=1.5)
    r1 = th.solve(s1, 1.0, dx_min_um=0.25, dz_min_um=0.1)
    r2 = th.solve(s2, 1.0, dx_min_um=0.25, dz_min_um=0.1)
    assert r1["rise_at_guide_K"] > r1["probes"]["20"] > r1["probes"]["100"] > 0.0
    assert r2["rise_at_guide_K"] > r1["rise_at_guide_K"]


def test_the_report_scales_to_a_stated_drive():
    stack = th.HeaterStack(layers=[th.Layer("Si", 100.0, th.K_SI), th.Layer("ox", 3.0, th.K_SIO2)],
                           half_width_um=200.0, heater_width_um=1.5, probes_um=[40.0])
    rep = th.report(stack, wire_length_um=1000.0, drive_mW=50.0, dx_min_um=0.5, dz_min_um=0.25)
    assert rep["power_W_per_m"] == 50.0e-3 / 1000.0e-6
    assert math.isclose(rep["rise_at_guide_K"], rep["K_per_mW"] * 50.0, rel_tol=1e-9)
    assert 0.0 < rep["probes_fraction_of_guide"]["40"] < 1.0
