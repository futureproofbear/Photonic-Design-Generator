"""Validation of the finite-element mode solver.

The finite-element backend exists to cross-check the finite-difference one, so
it is itself anchored to a closed-form result rather than to the solver it is
meant to check. Anchoring it to that solver would make the pair agree by
construction and the cross-check would attest to nothing.

The extras are optional, so every test here is skipped where they are absent.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from picchain.geometry import CrossSection, Shape
from picchain.solvers import femmode
from picchain.solvers.fdmode import solve_modes

from test_solvers import _analytic_slab_te

pytestmark = pytest.mark.skipif(
    not femmode.available(),
    reason=f"finite-element extras not installed ({femmode.unavailable_reason()})",
)

N_CORE, N_CLAD, T_UM, LAM_UM = 2.1376, 1.4441, 0.400, 1.55
WINDOW = (-3.0, 3.0, -2.0, 2.4)


# The mesh these tests solve on.
#
# It was 0.20 um with 0.02 um refinement, and that is 13 times slower than the
# mesh below for an answer identical to six decimal places. Measured 2026-08-09
# on the slab: 0.6/0.10 gives n_eff 1.865193 in 2.4 s, 0.4/0.05 gives 1.865197
# in 12.3 s, 0.3/0.03 gives 1.865197 in 47.7 s, and 0.2/0.02 gives 1.865197 in
# 159.6 s. Six tests at the finest setting is twenty minutes, which reads as a
# hang and was taken for one.
#
# The cost is superlinear because femwell normalises each mode by its power,
# which requires the magnetic field, which it obtains from a sparse direct
# solve. That solve dominates and scales far worse than the eigenproblem.
#
# `test_refinement_moves_the_answer_toward_the_analytic_value` deliberately
# keeps its own coarse and fine pair, that test being about the direction of the
# refinement rather than about the value.
RES_UM, FINE_UM = 0.40, 0.05


def _slab_cross_section() -> CrossSection:
    """A film uniform across the window, whose index is known analytically.

    The film is drawn past the lateral window edges so that the mesh carries no
    vertical material boundary within the domain; a boundary there would guide
    laterally and the problem would no longer be the one-dimensional slab.
    """
    x0, x1, y0, y1 = WINDOW
    xs = CrossSection(background="clad", window=WINDOW)
    xs.add(Shape.rect("core", x0 - 1.0, x1 + 1.0, 0.0, T_UM, "core"))
    return xs


EPS = {"core": N_CORE**2, "clad": N_CLAD**2}


# --------------------------------------------------------------------------
# 1. the closed-form anchor
# --------------------------------------------------------------------------
def test_fem_slab_matches_analytic():
    """A laterally uniform film must return the analytic slab index."""
    res = femmode.solve_cross_section(
        _slab_cross_section(), EPS, LAM_UM,
        num_modes=2, element_order=2, resolution_max_um=RES_UM,
        fine_resolution_um=FINE_UM, fine_distance_um=0.6, fine_shapes=("core",),
        n_guess=N_CORE * 0.95,
    )
    mode = res.select("TE")
    n_analytic = _analytic_slab_te(N_CORE, N_CLAD, T_UM, LAM_UM)
    assert abs(mode.n_eff - n_analytic) < 5e-4, f"FEM {mode.n_eff} vs analytic {n_analytic}"


def test_fem_slab_mode_is_polarisation_pure():
    """The slab TE mode carries no minor transverse component, so the
    semi-vectorial approximation is exact for it. A solver reporting otherwise
    has selected a different mode or mixed the components."""
    res = femmode.solve_cross_section(
        _slab_cross_section(), EPS, LAM_UM,
        num_modes=2, element_order=2, resolution_max_um=RES_UM,
        fine_resolution_um=FINE_UM, fine_shapes=("core",), n_guess=N_CORE * 0.95,
    )
    assert res.select("TE").te_fraction > 0.999


def test_fem_confinement_matches_the_analytic_slab_fraction():
    """The share of transverse electric energy inside the film, against the
    closed-form value for a symmetric slab.

    For the fundamental TE mode with transverse decay constant w and internal
    transverse wavenumber u, the fraction is obtained by integrating cos^2
    within the film and the matched exponential tails outside it.
    """
    res = femmode.solve_cross_section(
        _slab_cross_section(), EPS, LAM_UM,
        num_modes=2, element_order=2, resolution_max_um=RES_UM,
        fine_resolution_um=FINE_UM, fine_shapes=("core",), n_guess=N_CORE * 0.95,
    )
    mode = res.select("TE")

    k0 = 2 * math.pi / LAM_UM
    n_a = _analytic_slab_te(N_CORE, N_CLAD, T_UM, LAM_UM)
    u = k0 * math.sqrt(N_CORE**2 - n_a**2)          # transverse wavenumber, per um
    w = k0 * math.sqrt(n_a**2 - N_CLAD**2)          # decay constant, per um
    h = T_UM / 2
    inside = h + math.sin(2 * u * h) / (2 * u)      # integral of cos^2(u y) over the film
    outside = math.cos(u * h) ** 2 / w              # both tails, matched at the interface
    gamma = inside / (inside + outside)

    assert abs(mode.confinement("core") - gamma) < 0.02, (
        f"FEM {mode.confinement('core'):.4f} vs analytic {gamma:.4f}"
    )


# --------------------------------------------------------------------------
# 2. the two solvers on the same problem
# --------------------------------------------------------------------------
def test_the_two_solvers_agree_on_the_slab():
    """Both solvers, the same cross-section, the same permittivity model.

    The tolerance is the one the cross-check stage defaults to. Where this test
    fails, the disagreement the stage reports on a real cross-section cannot be
    attributed to the geometry.
    """
    x0, x1, y0, y1 = WINDOW
    x = np.linspace(x0, x1, 121)
    y = np.linspace(y0, y1, 1101)
    eps_line = np.where((y > 0) & (y < T_UM), N_CORE**2, N_CLAD**2)
    eps = np.tile(eps_line, (len(x), 1))
    n_fd = solve_modes(x, y, eps, eps, LAM_UM, "TE", 1, N_CORE * 0.95)[0].n_eff

    res = femmode.solve_cross_section(
        _slab_cross_section(), EPS, LAM_UM,
        num_modes=2, element_order=2, resolution_max_um=RES_UM,
        fine_resolution_um=FINE_UM, fine_shapes=("core",), n_guess=N_CORE * 0.95,
    )
    n_fem = res.select("TE").n_eff
    assert abs(n_fem - n_fd) / n_fd < 1.0e-3, f"FEM {n_fem} vs FD {n_fd}"


# --------------------------------------------------------------------------
# 3. mesh convergence, which is what makes a disagreement readable
# --------------------------------------------------------------------------
def test_refinement_moves_the_answer_toward_the_analytic_value():
    """A coarser mesh must be further from the closed-form result than a finer
    one. Without this the convergence guard in the stage would be comparing a
    shift that carries no direction."""
    n_analytic = _analytic_slab_te(N_CORE, N_CLAD, T_UM, LAM_UM)
    errors = []
    for res_um, fine_um in ((0.80, 0.20), (0.40, 0.05)):
        r = femmode.solve_cross_section(
            _slab_cross_section(), EPS, LAM_UM,
            num_modes=2, element_order=2, resolution_max_um=res_um,
            fine_resolution_um=fine_um, fine_shapes=("core",), n_guess=N_CORE * 0.95,
        )
        errors.append(abs(r.select("TE").n_eff - n_analytic))
    assert errors[1] < errors[0], f"coarse {errors[0]:.2e}, fine {errors[1]:.2e}"


# --------------------------------------------------------------------------
# 4. the geometry translation
# --------------------------------------------------------------------------
def test_polygon_priority_reverses_the_painting_order():
    """A ``CrossSection`` is painted in order and a later shape overrides an
    earlier one; the mesher resolves an overlap in favour of the earlier key.
    The translation must reverse the list, or every overlapping feature would be
    meshed as the material beneath it."""
    xs = CrossSection(background="clad", window=(-1, 1, -1, 1))
    xs.add(Shape.rect("slab", -1, 1, -0.2, 0.2, "under"))
    xs.add(Shape.rect("core", -0.3, 0.3, -0.2, 0.2, "over"))
    polys, by_material = cross_section_keys(xs)

    assert list(polys)[0].endswith("over"), "the overriding shape must take priority"
    # the overridden shape keeps only what the overriding one did not claim
    assert polys[list(polys)[1]].area == pytest.approx(2 * 0.4 - 0.6 * 0.4, abs=1e-9)
    assert by_material["core"] == [list(polys)[0]]


def cross_section_keys(xs):
    """The mesher differences later keys against earlier ones, so the areas
    reported here are the tiled ones the translation is checked against."""
    polys, by_material = femmode.cross_section_polygons(xs)
    keys = list(polys)
    tiled = {}
    for i, k in enumerate(keys):
        shape = polys[k]
        for earlier in keys[:i]:
            shape = shape.difference(polys[earlier])
        tiled[k] = shape
    return tiled, by_material
