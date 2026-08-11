"""Eigenmode-expansion core, against closed-form results.

Three properties are checked, each of which has an answer that is known
analytically rather than recorded from a previous run:

1. a uniform guide sliced into sections transmits unity and reflects nothing,
   and accumulates exactly the expected phase;
2. a single-mode abrupt junction reproduces the Fresnel coefficients for two
   media whose indices are the two effective indices;
3. power is conserved across a junction between lossless sections.
"""

from __future__ import annotations

import numpy as np

from picchain import eme


def _grid(nx=24, ny=20):
    x = np.linspace(-3.0, 3.0, nx)
    y = np.linspace(-2.5, 2.5, ny)
    return x, y, eme.cell_areas(x, y)


def _gaussian_mode(x, y, w=0.8, x0=0.0):
    X, Y = np.meshgrid(x, y, indexing="ij")
    return np.exp(-((X - x0) ** 2 + Y**2) / w**2)


def test_uniform_guide_is_transparent_and_accumulates_phase():
    x, y, dA = _grid()
    f = _gaussian_mode(x, y)[None, :, :]
    n = np.array([1.8])
    lam, L = 1.55, 10.0

    S = eme.slice_chain([n, n, n], [f, f, f], dA, [L, L, L], lam)
    out = eme.fundamental_transmission(S, n, n)

    assert abs(out["transmission_fundamental"] - 1.0) < 1e-10
    assert out["reflection"] < 1e-20

    expected = np.exp(1j * 2 * np.pi / lam * n[0] * 3 * L)
    assert abs(S[2][0, 0] - expected) < 1e-8


def test_single_mode_junction_matches_fresnel():
    x, y, dA = _grid()
    f = _gaussian_mode(x, y)[None, :, :]
    n1, n2 = np.array([2.0]), np.array([1.5])

    # zero-length sections, so only the junction is exercised
    S = eme.slice_chain([n1, n2], [f, f], dA, [0.0, 0.0], 1.55)
    out = eme.fundamental_transmission(S, n1, n2)

    T = 4 * n1[0] * n2[0] / (n1[0] + n2[0]) ** 2
    R = ((n1[0] - n2[0]) / (n1[0] + n2[0])) ** 2

    assert abs(out["transmission_fundamental"] - T) < 1e-9
    assert abs(out["reflection"] - R) < 1e-9
    assert abs(out["power_balance"] - 1.0) < 1e-9


def test_junction_conserves_power():
    x, y, dA = _grid()
    f = _gaussian_mode(x, y)[None, :, :]
    for n_a, n_b in ((2.0, 1.5), (1.6, 1.61), (2.4, 1.0)):
        S = eme.slice_chain(
            [np.array([n_a]), np.array([n_b])], [f, f], dA, [0.0, 0.0], 1.55
        )
        out = eme.fundamental_transmission(S, np.array([n_a]), np.array([n_b]))
        assert abs(out["power_balance"] - 1.0) < 1e-9


def test_local_mode_chain_is_lossless_when_the_profile_does_not_change():
    """The adiabatic limit: a guide whose profile is invariant transmits unity
    however the effective index varies along it."""
    x, y, dA = _grid()
    f = _gaussian_mode(x, y)[None, :, :]
    out = eme.local_mode_chain(
        [f, f, f, f], dA,
        n_effs=[np.array([1.9]), np.array([1.8]), np.array([1.7]), np.array([1.6])],
        lengths_um=[5.0] * 4, wavelength_um=1.55,
    )
    assert abs(out["transmission_fundamental"] - 1.0) < 1e-12
    assert out["staircase_deficit"] < 1e-12


def test_local_mode_chain_matches_the_analytic_gaussian_overlap():
    """A single step between two Gaussians of differing width transmits the
    squared overlap, which for a separable 2D Gaussian is

        T = (2 w1 w2 / (w1^2 + w2^2))^2
    """
    x, y, dA = _grid(nx=241, ny=201)
    w1, w2 = 0.8, 1.1
    a = _gaussian_mode(x, y, w1)[None, :, :]
    b = _gaussian_mode(x, y, w2)[None, :, :]

    out = eme.local_mode_chain([a, b], dA)
    expected = (2 * w1 * w2 / (w1**2 + w2**2)) ** 2
    assert abs(out["transmission_fundamental"] - expected) < 2e-4
    assert abs(out["staircase_deficit"] - (1.0 - expected)) < 2e-4


def test_local_mode_chain_counts_conversion_separately_from_radiation():
    """Power reaching a second guided mode is conversion, not loss; power
    leaving the retained set altogether is radiation."""
    x, y, dA = _grid(nx=241, ny=201)
    even = _gaussian_mode(x, y, 0.8)
    odd = even * x[:, None]
    basis = eme.normalise(np.stack([even, odd]), dA)

    theta = 0.3
    rotated = np.stack([
        np.cos(theta) * basis[0] + np.sin(theta) * basis[1],
        -np.sin(theta) * basis[0] + np.cos(theta) * basis[1],
    ])

    out = eme.local_mode_chain([basis, rotated], dA)
    assert abs(out["transmission_guided"] - 1.0) < 1e-9    # a rotation loses nothing
    assert abs(out["staircase_deficit"]) < 1e-9
    assert abs(out["transmission_fundamental"] - np.cos(theta) ** 2) < 1e-9
    assert abs(out["conversion_to_higher_order"] - np.sin(theta) ** 2) < 1e-9


def test_staircase_deficit_falls_as_the_slice_count_rises():
    """A smoothly varying single-mode guide is adiabatic: the deficit is an
    artefact of the discretisation and must fall as the steps are refined."""
    x, y, dA = _grid(nx=161, ny=141)

    def chain(n):
        widths = np.linspace(0.7, 1.2, n)
        fields = [_gaussian_mode(x, y, w)[None, :, :] for w in widths]
        return eme.local_mode_chain(fields, dA)["staircase_deficit"]

    coarse, fine = chain(6), chain(24)
    assert fine < coarse
    assert fine < 0.4 * coarse


def test_adiabaticity_margin_falls_where_the_taper_is_steepest():
    n = 40
    widths = np.linspace(0.4, 1.0, n)
    n_eff = np.linspace(1.70, 1.79, n)
    out = eme.adiabaticity(widths, n_eff, n_reference=1.66, length_um=150.0,
                           wavelength_um=1.55)
    # a linear taper changes fastest in fractional terms at the narrow end,
    # where the beat length against the slab is also longest
    assert out["min_adiabaticity_at_width_um"] < 0.5
    assert out["min_adiabaticity"] > 0.0
    assert len(out["profile"]) == n


def test_two_mode_overlap_and_normalisation():
    """A mode set that is orthogonal by construction gives a unit Gram matrix,
    and a rotated pair still conserves power across a junction."""
    x, y, dA = _grid()
    even = _gaussian_mode(x, y)
    odd = even * x[:, None]
    f = eme.normalise(np.stack([even, odd]), dA)

    G = eme.overlap(f, f, dA)
    assert abs(G[0, 0] - 1.0) < 1e-12 and abs(G[1, 1] - 1.0) < 1e-12
    assert abs(G[0, 1]) < 1e-12          # odd against even

    n_a, n_b = np.array([2.0, 1.9]), np.array([1.7, 1.6])
    S = eme.slice_chain([n_a, n_b], [f, f], dA, [0.0, 0.0], 1.55)
    out = eme.fundamental_transmission(S, n_a, n_b)
    assert abs(out["transmission_all_modes"] + out["reflection"] - 1.0) < 1e-9
