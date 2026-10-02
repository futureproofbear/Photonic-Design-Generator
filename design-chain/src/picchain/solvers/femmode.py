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
    import scipy.constants as _const
    import scipy.sparse.linalg as _spla
    import shapely.geometry as _sg
    from femwell.maxwell.waveguide import (
        Mode as _Mode,
        calculate_overlap as _calculate_overlap,
        compute_modes as _compute_modes,
    )
    from femwell.mesh import mesh_from_OrderedDict as _mesh_from_OrderedDict
    from skfem import (
        Basis as _Basis,
        BilinearForm as _BilinearForm,
        ElementTriN1 as _ElementTriN1,
        ElementTriN2 as _ElementTriN2,
        ElementTriP0 as _ElementTriP0,
        ElementTriP1 as _ElementTriP1,
        ElementTriP2 as _ElementTriP2,
        Functional as _Functional,
        condense as _condense,
        solve as _solve,
        solver_eigen_scipy as _solver_eigen_scipy,
    )
    from skfem.helpers import curl as _curl, dot as _dot, grad as _grad, inner as _inner
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
    #: the imaginary part of the effective index, non-zero only where the
    #: problem carried an absorbing margin or a lossy material
    n_eff_imag: float = 0.0

    def loss_dB_per_m(self, wavelength_um: float) -> float:
        """Power attenuation from the imaginary index: 20 log10(e) k0 Im(n)."""
        import math
        return 20.0 / math.log(10.0) * (2 * math.pi / (wavelength_um * 1e-6)) * abs(self.n_eff_imag)

    def power_coupling(self, other: "FemModeResult") -> float:
        """Fraction of the power of this mode coupled into ``other`` at a butt joint.

            T = |<a|b>|^2 / (Re<a|a> Re<b|b>),   <a|b> = 1/2 Int(E_a* x H_b + E_b x H_a*) . z

        This is the mode-mismatch transmission of a junction with no lateral
        offset, such as a straight guide joined to a bend. The fields of a bend
        solved by this module are the physical fields on the plane of the
        junction, so the figure is that of the junction itself. Where the two
        modes were solved on different meshes the second is interpolated.
        """
        a, b = self._mode, other._mode
        if a is None or b is None:
            return float("nan")
        ab = _calculate_overlap(a.basis, a.E, a.H, b.basis, b.E, b.H)
        aa = _calculate_overlap(a.basis, a.E, a.H, a.basis, a.E, a.H)
        bb = _calculate_overlap(b.basis, b.E, b.H, b.basis, b.E, b.H)
        return float(abs(ab) ** 2 / (np.real(aa) * np.real(bb)))

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
# the bend
# --------------------------------------------------------------------------
def _bent_modes(basis_eps, eps, wavelength_um: float, radius_um: float, *,
                num_modes: int, order: int, n_guess: float | None,
                metallic_boundaries: bool) -> list:
    """Modes of a guide bent to ``radius_um``, by its exact straight equivalent.

    The bend (r, phi, y) is mapped onto a straight guide by x = r - R and
    z = R phi, the centre of curvature lying at x = -R. Transformation optics
    gives the straight guide an anisotropic medium, with s = r/R:

        eps' = eps * diag(s, s, 1/s)     (x, y transverse; propagation along z)
        mu'  =       diag(s, s, 1/s)

    The transverse fields of the straight guide equal the physical fields on
    the radial plane, so a mode solved here is overlapped directly with a
    straight one. ``femwell.compute_modes`` instead scales an isotropic
    permittivity by s^2 and keeps mu = 1. That form agrees with this one for a
    guide uniform in y and departs from it for a core confined in y as well.
    On a 220 nm by 500 nm silicon strip at R = 10 um it gave an index shift
    3.7 times that of a cylindrical eigenmode solve, and this form agrees with
    that solve to the precision quoted in ``tests/test_bend_exact.py``.

    The variational form is that of ``femwell.compute_modes``, the transverse
    and longitudinal tensor components entering separately. H is projected
    from E with mu', so that the fields carried by each ``Mode`` are physical.
    """
    k0 = 2 * np.pi / wavelength_um
    element = (_ElementTriN1() * _ElementTriP1() if order == 1
               else _ElementTriN2() * _ElementTriP2())
    basis = basis_eps.with_element(element)
    basis_eps = basis.with_element(basis_eps.elem)
    R = float(radius_um)

    @_BilinearForm(dtype=complex)
    def aform(e_t, e_z, v_t, v_z, w):
        s = 1 + w.x[0] / R
        eps_t, eps_z, inv_mu_t, inv_mu_z = w.epsilon * s, w.epsilon / s, 1 / s, s
        return (inv_mu_z * _curl(e_t) * _curl(v_t) / k0 ** 2
                - eps_t * _dot(e_t, v_t)
                + inv_mu_t * _dot(_grad(e_z), v_t)
                + eps_t * _inner(e_t, _grad(v_z))
                - eps_z * e_z * v_z * k0 ** 2)

    @_BilinearForm(dtype=complex)
    def bform(e_t, e_z, v_t, v_z, w):
        return -(1 / (1 + w.x[0] / R)) * _dot(e_t, v_t) / k0 ** 2

    ev = basis_eps.interpolate(eps)
    A = aform.assemble(basis, epsilon=ev)
    B = bform.assemble(basis, epsilon=ev)
    sigma = k0 ** 2 * (n_guess ** 2 if n_guess else 1.1 * float(np.max(np.real(eps))))
    solver = _solver_eigen_scipy(k=num_modes, sigma=sigma)
    if metallic_boundaries:
        lams, xs = _solve(*_condense(-A, -B, D=basis.get_dofs(), x=basis.zeros(dtype=complex)),
                          solver=solver)
    else:
        lams, xs = _solve(-A, -B, solver=solver)
    xs[basis.split_indices()[1], :] /= 1j * np.sqrt(lams[np.newaxis, :] / k0 ** 4)

    @_BilinearForm(dtype=complex)
    def mass(e_t, e_z, v_t, v_z, w):
        return _dot(e_t, v_t) + e_z * v_z

    M = mass.assemble(basis)
    omega = k0 * _const.speed_of_light
    out = []
    for i, lam in enumerate(lams):
        beta = np.sqrt(lam)

        @_BilinearForm(dtype=complex)
        def curl_over_mu(e_t, e_z, v_t, v_z, w):
            s = 1 + w.x[0] / R
            return ((-1j * beta * e_t[1] + e_z.grad[1]) * v_t[0]
                    + (1j * beta * e_t[0] - e_z.grad[0]) * v_t[1]) / s + e_t.curl * v_z * s

        E = xs[:, i]
        H = _spla.spsolve(M, curl_over_mu.assemble(basis) @ E) * -1j / _const.mu_0 / omega
        power = _calculate_overlap(basis, E, H, basis, E, H)
        out.append(_Mode(frequency=_const.speed_of_light / wavelength_um, k=beta,
                         basis_epsilon_r=basis_eps, epsilon_r=eps, basis=basis,
                         E=E / np.sqrt(power), H=H / np.sqrt(power)))
    return out


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
    radius_um: float | None = None,
    absorber_um: float = 0.0,
    absorber_strength: float = 1.0,
) -> FemSolveResult:
    """Solve ``xs`` by finite elements at a scalar permittivity per material.

    ``radius_um`` bends the guide about an axis at x = -R, so the outer wall is
    the +x side. The bend is solved as its exact anisotropic straight
    equivalent (see ``_bent_modes``).

    ``absorber_um`` gives the lateral margin of the window an imaginary
    permittivity rising quadratically from zero at its inner edge to
    ``absorber_strength`` times the real part at the window edge. That margin
    is the absorbing boundary a leaky mode needs; without it a bend mode is
    reflected from the electric wall and its loss is unobservable. The
    imaginary part of each mode's effective index is returned, and the
    attenuation it implies is ``FemModeResult.loss_dB_per_m``.

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

    if absorber_um and absorber_um > 0:
        x0, x1 = xs.window[0], xs.window[1]
        xc = basis_eps.doflocs[0]                      # element centroids of the P0 basis
        d = np.maximum(0.0, xc - (x1 - absorber_um)) + np.maximum(0.0, (x0 + absorber_um) - xc)
        ramp = np.minimum(1.0, d / absorber_um) ** 2
        eps = eps.astype(complex) * (1.0 + 1j * float(absorber_strength) * ramp)

    if radius_um:
        modes = _bent_modes(basis_eps, eps, wavelength_um, float(radius_um),
                            num_modes=num_modes, order=element_order, n_guess=n_guess,
                            metallic_boundaries=bool(metallic_boundaries))
    else:
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
                n_eff_imag=float(np.imag(n_eff)),
            )
        )
    return FemSolveResult(
        modes=out,
        n_elements=int(mesh.t.shape[1]),
        n_dofs=int(basis_eps.N),
        element_order=int(element_order),
        resolution_max_um=float(resolution_max_um),
    )
