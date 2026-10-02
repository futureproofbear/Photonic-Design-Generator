"""The bend as its exact straight equivalent, against an invariance and a reference.

Added 2026-10-02. ``femwell.compute_modes`` treats a bend as an isotropic
permittivity scaled by (1 + x/R)^2. The exact equivalent is anisotropic, and the
two differ for a core confined in the direction normal to the plane of the bend.
On a 220 nm by 500 nm silicon strip the isotropic form returned 3.7 times the
index shift of a cylindrical eigenmode solve, and a minimum bend radius of 15.0
um against 8.2 um for a straight-to-bend mismatch of 0.1 per cent.

Two properties are tested. The first holds whatever the geometry: the angular
propagation constant nu = k0 n_eff R belongs to the physical bend, so it is
unchanged when the reference radius is moved and the guide is not. The second
is a comparison with an independent solver on the same cross-section.

The reference figures were computed on 2026-10-02 by the finite-difference
eigenmode solver of Ansys Lumerical MODE (installation v261), solving the bent
guide in cylindrical coordinates with an absorbing lateral boundary. The script
was ``bend_MODE.lsf`` of the public scripts accompanying Chrostowski and
Hochberg, *Silicon Photonics Design* (2015), chapter 3, at its default 10 nm
mesh: Si at n = 3.473425 and SiO2 at n = 1.444, a window of 4.5 um by 1.22 um
with electric walls above and below. ``power_coupling`` is the second output
of its ``overlap`` command, being the transmission of one junction.
"""
from __future__ import annotations

import math

import pytest

from picchain.geometry import CrossSection, Shape
from picchain.solvers import femmode

pytestmark = pytest.mark.skipif(not femmode.available(),
                                reason=femmode.unavailable_reason() or "no femwell")

LAM = 1.55
EPS = {"SiO2": 1.444 ** 2, "Si": 3.473425 ** 2}
# radius_um: (n_eff, power_coupling of one straight-to-bend junction)
LUMERICAL_STRAIGHT_N_EFF = 2.44195
LUMERICAL = {10.0: (2.44230, 0.99966095), 5.0: (2.44336, 0.99863512), 3.0: (2.44587, 0.996149)}


def _strip(dx: float = 0.0) -> CrossSection:
    xs = CrossSection(background="SiO2", window=(-2.25 + dx, 2.25 + dx, -0.5, 0.72), name="strip")
    xs.add(Shape.rect("Si", -0.25 + dx, 0.25 + dx, 0.0, 0.22, "ridge"))
    return xs


def _solve(xs: CrossSection, radius_um: float | None = None, n_guess: float = 2.44):
    res = femmode.solve_cross_section(xs, EPS, LAM, num_modes=1, element_order=2,
                                      resolution_max_um=0.15, fine_resolution_um=0.02,
                                      fine_distance_um=0.5, n_guess=n_guess, radius_um=radius_um)
    return res.modes[0]


def test_the_angular_propagation_constant_is_independent_of_the_reference_radius():
    """Moving the origin by d and the reference radius by -d leaves the guide where it is."""
    R, d = 10.0, 1.0
    k0 = 2 * math.pi / LAM
    nu_centred = k0 * _solve(_strip(), R).n_eff * R
    nu_moved = k0 * _solve(_strip(d), R - d, n_guess=2.44 * R / (R - d)).n_eff * (R - d)
    assert abs(nu_moved / nu_centred - 1.0) < 2e-5


def test_the_index_shift_and_the_junction_mismatch_agree_with_a_cylindrical_solve():
    straight = _solve(_strip())
    assert abs(straight.n_eff - LUMERICAL_STRAIGHT_N_EFF) < 2e-3
    for R, (n_ref, t_ref) in LUMERICAL.items():
        bend = _solve(_strip(), R, n_guess=straight.n_eff)
        dn, dn_ref = bend.n_eff - straight.n_eff, n_ref - LUMERICAL_STRAIGHT_N_EFF
        assert abs(dn / dn_ref - 1.0) < 0.05, (R, dn, dn_ref)
        loss, loss_ref = -10 * math.log10(straight.power_coupling(bend)), -10 * math.log10(t_ref)
        assert abs(loss / loss_ref - 1.0) < 0.03, (R, loss, loss_ref)


def test_identical_modes_couple_completely():
    m = _solve(_strip())
    assert abs(m.power_coupling(m) - 1.0) < 1e-9
