"""Full-vectorial finite-element optical mode solver, by femwell.

This module exists as an *independent instrument*, not as a replacement for
``fdmode``. The two differ in every respect that matters to a cross-check:

===================  ==============================  ============================
                     ``fdmode``                      ``femmode``
===================  ==============================  ============================
discretisation       finite difference, structured   finite element, unstructured
geometry             staircased, sub-pixel averaged  conforming triangulation
formulation          semi-vectorial (Stern)          full-vectorial (E-field curl)
element              3-point stencil                 Nedelec + Lagrange, order 1/2
permittivity         diagonally anisotropic          scalar, per element
===================  ==============================  ============================

The two accordingly disagree for reasons that can be separated. A sloped
sidewall is a staircase to one and a straight edge to the other, so the
geometric error differs. The semi-vectorial operator carries only the dominant
transverse field component, so the minor components are absent from one and
present in the other. Where the two agree, the agreement is evidence; where they
disagree, the size of the disagreement bounds the error of the cheaper solver.

The permittivity model
----------------------
``compute_modes`` carries one scalar permittivity per element, so an anisotropic
film cannot be described to it directly. This is less of a restriction than it
appears. The semi-vectorial quasi-TE operator of ``fdmode`` reads ``eps_xx``
alone and never touches ``eps_yy``, so a finite-element solve performed at
``eps = eps_xx`` compares like with like: the permittivity model is held fixed
and the comparison isolates the operator and the mesh.

What the full-vectorial solve then adds is a measurement of what that model
omits. The minor field components physically sample the other principal indices,
and two quantities report how much that matters:

* ``te_fraction`` gives the share of the transverse electric energy carried by
  the dominant component, and hence the weight attaching to the omission;
* a second solve at ``eps = eps_yy`` brackets the anisotropic answer, the true
  value lying between the two solves for a diagonal tensor.

Availability
------------
``femwell``, ``scikit-fem`` and ``gmsh`` are optional extras. ``available()``
reports whether the import succeeded, and callers are required to check it
rather than to catch an ImportError from a solve.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..geometry import CrossSection

_IMPORT_ERROR: str | None = None
try:  # pragma: no cover - exercised by the availability test
    import shapely.geometry as _sg
    from femwell.maxwell.waveguide import compute_modes as _compute_modes
    from femwell.mesh import mesh_from_OrderedDict as _mesh_from_OrderedDict
    from skfem import Basis as _Basis, ElementTriP0 as _ElementTriP0, Functional as _Functional
    from skfem.io.meshio import from_meshio as _from_meshio

    _AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _AVAILABLE = False
    _IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def available() -> bool:
    """Whether a finite-element solve can be performed in this environment."""
    return _AVAILABLE


def unavailable_reason() -> str | None:
    """The import failure, where there was one."""
    return _IMPORT_ERROR


def version() -> str | None:
    if not _AVAILABLE:
        return None
    import femwell

    return getattr(femwell, "__version__", "unknown")


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------
@dataclass
class FemModeResult:
    """One mode of the finite-element solve.

    ``confinement`` is defined identically to ``fdmode.ModeResult.confinement``,
    being the fraction of the transverse electric energy lying within a region,
    so that the two solvers' figures are comparable without a conversion.
    """

    n_eff: float
    te_fraction: float
    transversality: float
    _mode: Any = field(repr=False, default=None)
    _subdomains: dict[str, list[str]] = field(repr=False, default_factory=dict)

    def confinement(self, material: str) -> float:
        """Fraction of |E_t|^2 within the regions made of ``material``."""
        if self._mode is None:
            return float("nan")
        basis = self._mode.basis
        keys = [k for k in self._subdomains.get(material, []) if k in basis.mesh.subdomains]
        if not keys:
            return float("nan")

        @_Functional
        def energy(w):
            return np.abs(w["E"][0][0]) ** 2 + np.abs(w["E"][0][1]) ** 2

        total = energy.assemble(basis, E=basis.interpolate(self._mode.E))
        elements = np.unique(np.concatenate([basis.mesh.subdomains[k] for k in keys]))
        sub = basis.with_elements(elements)
        part = energy.assemble(sub, E=sub.interpolate(self._mode.E))
        return float(np.real(part / total))

    def eo_overlap(self, rf_field, active_material: str, gap_um: float,
                   voltage: float) -> float:
        """Electro-optic overlap assembled on this solver's own triangulation.

            Gamma = (G/V) * Int_active( E_rf |E_t|^2 ) / Int_all( |E_t|^2 )

        which is the definition `solvers.electrostatic.eo_overlap` evaluates on
        a rectangular grid. `rf_field` is a callable taking two arrays of
        coordinates and returning the radio-frequency field at them, so the two
        figures share that field and differ only in the optical field and the
        quadrature that integrates it.

        Point evaluation of the finite-element field is not available: the
        vector basis raises on `probes`, so the optical field cannot be resampled
        onto the rectangular grid and the integral is assembled here instead.
        That leaves the quadrature differing between the two figures as well as
        the field, and a disagreement cannot be attributed to the field alone
        without a mesh ladder.
        """
        if self._mode is None:
            return float("nan")
        basis = self._mode.basis
        keys = [k for k in self._subdomains.get(active_material, [])
                if k in basis.mesh.subdomains]
        if not keys:
            return float("nan")

        @_Functional
        def energy(w):
            return np.abs(w["E"][0][0]) ** 2 + np.abs(w["E"][0][1]) ** 2

        @_Functional
        def weighted(w):
            inten = np.abs(w["E"][0][0]) ** 2 + np.abs(w["E"][0][1]) ** 2
            erf = rf_field(np.asarray(w.x[0]), np.asarray(w.x[1]))
            return erf * inten

        den = energy.assemble(basis, E=basis.interpolate(self._mode.E))
        elements = np.unique(np.concatenate([basis.mesh.subdomains[k] for k in keys]))
        sub = basis.with_elements(elements)
        num = weighted.assemble(sub, E=sub.interpolate(self._mode.E))
        if not np.isfinite(np.real(den)) or np.real(den) == 0.0:
            return float("nan")
        return float((gap_um / voltage) * np.real(num) / np.real(den))


@dataclass
class FemSolveResult:
    modes: list[FemModeResult]
    n_elements: int
    n_dofs: int
    element_order: int
    resolution_max_um: float

    def select(self, polarisation: str, n_guess: float | None = None) -> FemModeResult:
        """The mode corresponding to the requested polarisation.

        Ordering by effective index alone is not sufficient. A cross-section
        close to cut-off can place a mode of the opposite polarisation above the
        one being tracked, and the comparison would then be drawn against a
        different mode of a different family. The polarisation fraction
        identifies the family, and the guess, where supplied, resolves the
        remaining choice between members of it.
        """
        want_te = polarisation.upper() == "TE"
        family = [m for m in self.modes if (m.te_fraction >= 0.5) == want_te]
        if not family:
            raise RuntimeError(
                f"the finite-element solve returned no {polarisation.upper()}-like mode "
                f"among {len(self.modes)}; the polarisation fractions were "
                + ", ".join(f"{m.te_fraction:.3f}" for m in self.modes)
                + ". Raise num_modes, or the cross-section does not guide this polarisation"
            )
        if n_guess is None:
            return max(family, key=lambda m: m.n_eff)
        return min(family, key=lambda m: abs(m.n_eff - n_guess))


# --------------------------------------------------------------------------
# meshing
# --------------------------------------------------------------------------
def _shape_key(index: int, shape) -> str:
    """A unique, separator-free name for one shape, as gmsh requires of a
    physical group."""
    return f"s{index:02d}_{(shape.name or shape.material).replace(' ', '_')}"


def cross_section_polygons(xs: CrossSection) -> tuple["OrderedDict[str, Any]", dict[str, list[str]]]:
    """Convert a ``CrossSection`` into meshable polygons, ordered by priority.

    Two conventions must be reconciled. A ``CrossSection`` is painted in order,
    so a later shape overrides an earlier one. ``mesh_from_OrderedDict`` resolves
    an overlap in favour of the *earlier* key, differencing every later shape
    against those before it. The shape list is therefore reversed here.

    Blanket layers are drawn a micrometre beyond the window by
    ``edbr_cross_section``, so that sub-pixel averaging at the boundary column
    still sees solid material. A finite-element mesh has no such column and no
    such need, and an unclipped polygon would extend the domain past the window
    the finite-difference solve used. Every shape is therefore clipped to the
    window, and the two solvers are posed on the same domain.

    Returns the polygons and a map from material name to the keys made of it,
    the latter being required for a confinement figure over a material rather
    than over one shape.
    """
    if not _AVAILABLE:  # pragma: no cover
        raise RuntimeError(f"femwell is not available: {_IMPORT_ERROR}")

    x0, x1, y0, y1 = xs.window
    clip = _sg.box(x0, y0, x1, y1)

    polys: OrderedDict[str, Any] = OrderedDict()
    by_material: dict[str, list[str]] = {}
    for i, s in reversed(list(enumerate(xs.shapes))):
        poly = _sg.Polygon(s.points).buffer(0).intersection(clip)
        if poly.is_empty or poly.area <= 0.0:
            continue
        key = _shape_key(i, s)
        polys[key] = poly
        by_material.setdefault(s.material, []).append(key)

    # the background fills whatever the shapes have not claimed, and is last
    polys["background"] = clip
    by_material.setdefault(xs.background, []).append("background")
    return polys, by_material


def _build_mesh(
    polys: "OrderedDict[str, Any]",
    resolution_max_um: float,
    fine: dict[str, tuple[float, float]] | None,
):
    resolutions = None
    if fine:
        resolutions = {
            k: {"resolution": r, "distance": d} for k, (r, d) in fine.items() if k in polys
        }
    return _from_meshio(
        _mesh_from_OrderedDict(
            polys,
            resolutions=resolutions,
            default_resolution_max=resolution_max_um,
            filename=None,
            verbose=False,
        )
    )


# --------------------------------------------------------------------------
# the solve
# --------------------------------------------------------------------------
def solve_cross_section(
    xs: CrossSection,
    eps_of_material: dict[str, float],
    wavelength_um: float,
    *,
    num_modes: int = 4,
    element_order: int = 2,
    resolution_max_um: float = 0.35,
    fine_resolution_um: float | None = 0.02,
    fine_distance_um: float = 0.6,
    fine_shapes: tuple[str, ...] = ("ridge", "post_L", "post_R"),
    n_guess: float | None = None,
    metallic_boundaries: bool = True,
) -> FemSolveResult:
    """Solve ``xs`` by finite elements at a scalar permittivity per material.

    ``fine_shapes`` names the shapes across which the mesh is refined, matched
    against the ``name`` given to each ``Shape``. The guiding features are small
    against the window, and a mesh uniform enough to resolve them everywhere is
    an order of magnitude more expensive than one graded toward them.

    ``metallic_boundaries`` forces the tangential electric field to zero at the
    window edge, which is the condition the finite-difference solver imposes on
    its dominant component and the one under which the two are comparable. The
    natural condition of the curl-curl formulation is the magnetic wall
    instead, and it forces the tangential *magnetic* field to zero. That
    condition is incompatible with a mode extending to the boundary: a film
    reaching the lateral edge of the window was found to lose 4e-3 in effective
    index under it, against 4e-5 for the electric wall on the same problem.
    """
    if not _AVAILABLE:  # pragma: no cover
        raise RuntimeError(f"femwell is not available: {_IMPORT_ERROR}")
    if element_order not in (1, 2):
        raise ValueError("element_order must be 1 or 2")

    polys, by_material = cross_section_polygons(xs)
    missing = {m for m in xs.materials_used()} - set(eps_of_material)
    if missing:
        raise KeyError(f"no permittivity supplied for {sorted(missing)}")

    fine = None
    if fine_resolution_um:
        wanted = {_shape_key(i, s) for i, s in enumerate(xs.shapes) if s.name in fine_shapes}
        fine = {k: (fine_resolution_um, fine_distance_um) for k in polys if k in wanted}

    mesh = _build_mesh(polys, resolution_max_um, fine)
    basis_eps = _Basis(mesh, _ElementTriP0())

    eps = basis_eps.zeros() + float(eps_of_material[xs.background])
    key_material = {k: m for m, keys in by_material.items() for k in keys}
    for key, material in key_material.items():
        if key in mesh.subdomains:
            eps[basis_eps.get_dofs(elements=key)] = float(eps_of_material[material])

    modes = _compute_modes(
        basis_eps,
        eps,
        wavelength=wavelength_um,
        num_modes=num_modes,
        order=element_order,
        n_guess=n_guess,
        metallic_boundaries=bool(metallic_boundaries),
    )

    out: list[FemModeResult] = []
    for m in modes:
        n_eff = complex(m.n_eff)
        out.append(
            FemModeResult(
                n_eff=float(np.real(n_eff)),
                te_fraction=float(np.real(m.te_fraction)),
                transversality=float(np.real(m.transversality)),
                _mode=m,
                _subdomains=by_material,
            )
        )
    return FemSolveResult(
        modes=out,
        n_elements=int(mesh.t.shape[1]),
        n_dofs=int(basis_eps.N),
        element_order=int(element_order),
        resolution_max_um=float(resolution_max_um),
    )
