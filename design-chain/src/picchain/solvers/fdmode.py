"""Semi-vectorial finite-difference optical mode solver (numpy/scipy only).

Solves, on a graded tensor-product mesh with diagonally anisotropic eps,

    quasi-TE (dominant E_x):
        d/dx[ (1/eps_xx) d(eps_xx Ex)/dx ] + d2Ex/dy2 + k0^2 eps_xx Ex = beta^2 Ex

    quasi-TM (dominant E_y):
        d/dy[ (1/eps_yy) d(eps_yy Ey)/dy ] + d2Ey/dx2 + k0^2 eps_yy Ey = beta^2 Ey

This is the Stern semi-vectorial formulation.  Its dependencies are confined to
numpy and scipy, so the whole design chain executes without a graphical
interface wherever python does.  ``tests/test_solvers.py`` validates it against
the analytic slab dispersion relation.

``femmode`` provides an optional full-vectorial finite-element backend, reached
by the ``fem`` stage.  It exists to check this solver on the device
cross-section rather than on the slab, and to report the polarisation purity,
which is the quantity bounding the error of the semi-vectorial assumption made
here.

Accuracy note: absolute n_eff converges as O(h^2); the *differences* used by
the grating stage converge much faster because the perturbed and unperturbed
problems share a mesh.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


@dataclass
class ModeResult:
    n_eff: float
    field: np.ndarray  # (nx, ny) dominant transverse E component
    x: np.ndarray
    y: np.ndarray
    polarisation: str
    n_eff_all: np.ndarray  # all converged modes, descending

    def normalised_intensity(self) -> np.ndarray:
        """|E|^2 normalised so that sum(I * dA) == 1."""
        dx = np.gradient(self.x)
        dy = np.gradient(self.y)
        dA = np.outer(dx, dy)
        inten = np.abs(self.field) ** 2
        return inten / np.sum(inten * dA)

    def confinement(self, mask: np.ndarray) -> float:
        """Fraction of |E|^2 inside a fractional-occupancy mask."""
        dx = np.gradient(self.x)
        dy = np.gradient(self.y)
        dA = np.outer(dx, dy)
        inten = np.abs(self.field) ** 2
        return float(np.sum(inten * mask * dA) / np.sum(inten * dA))


def _second_derivative_matrix(t: np.ndarray) -> sp.csr_matrix:
    """Non-uniform 3-point d2/dt2 with Dirichlet ends."""
    n = len(t)
    h = np.diff(t)
    main = np.zeros(n)
    lower = np.zeros(n - 1)
    upper = np.zeros(n - 1)
    for i in range(1, n - 1):
        hm, hp = h[i - 1], h[i]
        s = 2.0 / (hm + hp)
        lower[i - 1] = s / hm
        upper[i] = s / hp
        main[i] = -s * (1.0 / hm + 1.0 / hp)
    return sp.diags([lower, main, upper], [-1, 0, 1], format="csr")


def _semivec_matrix(t: np.ndarray, eps_line: np.ndarray) -> sp.csr_matrix:
    """Non-uniform discretisation of d/dt[ (1/eps) d(eps F)/dt ] for one line."""
    n = len(t)
    h = np.diff(t)
    rows, cols, vals = [], [], []
    for i in range(1, n - 1):
        hm, hp = h[i - 1], h[i]
        s = 2.0 / (hm + hp)
        # face permeabilities: (1/eps) at i+-1/2 via arithmetic mean of eps
        inv_p = 2.0 / (eps_line[i] + eps_line[i + 1])
        inv_m = 2.0 / (eps_line[i - 1] + eps_line[i])
        cp = s * inv_p / hp
        cm = s * inv_m / hm
        rows += [i, i, i]
        cols += [i + 1, i, i - 1]
        vals += [cp * eps_line[i + 1], -(cp + cm) * eps_line[i], cm * eps_line[i - 1]]
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n))


def solve_modes(
    x: np.ndarray,
    y: np.ndarray,
    eps_xx: np.ndarray,
    eps_yy: np.ndarray,
    wavelength_um: float,
    polarisation: str = "TE",
    num_modes: int = 2,
    n_guess: float | None = None,
) -> list[ModeResult]:
    """Solve for the ``num_modes`` highest-n_eff guided modes.

    ``eps_xx``/``eps_yy`` are (nx, ny) arrays of *optical* relative permittivity
    in the device frame.
    """
    nx, ny = len(x), len(y)
    if eps_xx.shape != (nx, ny):
        raise ValueError(f"eps_xx shape {eps_xx.shape} != {(nx, ny)}")
    k0 = 2 * np.pi / wavelength_um

    eps_dom = eps_xx if polarisation.upper() == "TE" else eps_yy
    Ix, Iy = sp.identity(nx, format="csr"), sp.identity(ny, format="csr")

    if polarisation.upper() == "TE":
        # semi-vectorial operator along x (row-wise, eps varies along x)
        blocks = []
        for j in range(ny):
            blocks.append(_semivec_matrix(x, eps_dom[:, j]))
        # assemble kron-like: unknowns ordered (i, j) -> i*ny + j
        Lx = sp.lil_matrix((nx * ny, nx * ny))
        for j, B in enumerate(blocks):
            Bc = B.tocoo()
            Lx[Bc.row * ny + j, Bc.col * ny + j] = Bc.data
        Lx = Lx.tocsr()
        Ly = sp.kron(Ix, _second_derivative_matrix(y), format="csr")
    else:
        blocks = []
        for i in range(nx):
            blocks.append(_semivec_matrix(y, eps_dom[i, :]))
        Ly = sp.lil_matrix((nx * ny, nx * ny))
        for i, B in enumerate(blocks):
            Bc = B.tocoo()
            Ly[i * ny + Bc.row, i * ny + Bc.col] = Bc.data
        Ly = Ly.tocsr()
        Lx = sp.kron(_second_derivative_matrix(x), Iy, format="csr")

    A = (Lx + Ly + sp.diags(k0**2 * eps_dom.ravel(order="C"))).tocsc()

    n_max = float(np.sqrt(eps_dom.max()))
    sigma = (k0 * (n_guess if n_guess else n_max * 0.999)) ** 2
    k = min(num_modes + 2, nx * ny - 2)
    vals, vecs = spla.eigs(A, k=k, sigma=sigma, which="LM")

    beta2 = np.real(vals)
    order = np.argsort(-beta2)
    out: list[ModeResult] = []
    n_all = np.sqrt(np.clip(beta2[order], 0, None)) / k0
    for idx in order[:num_modes]:
        b2 = beta2[idx]
        if b2 <= 0:
            continue
        f = np.real(vecs[:, idx]).reshape(nx, ny)
        # deterministic sign: make the peak positive
        if f.ravel()[np.argmax(np.abs(f))] < 0:
            f = -f
        out.append(
            ModeResult(
                n_eff=float(np.sqrt(b2) / k0),
                field=f,
                x=x,
                y=y,
                polarisation=polarisation.upper(),
                n_eff_all=n_all,
            )
        )
    if not out:
        raise RuntimeError("no guided mode found - check geometry/window")
    return out


def bend_permittivity(eps: np.ndarray, x: np.ndarray, radius_um: float) -> np.ndarray:
    """Conformal transformation of a bend into an equivalent straight guide.

    A guide bent to radius R about a centre at ``x = -R`` is equivalent, for the
    purpose of a scalar or semi-vectorial solve, to a straight guide whose index
    is graded across the section:

        n_equivalent(x) = n(x) * exp(x / R)

    with x measured from the guide axis and positive toward the outside of the
    bend. The permittivity therefore carries a factor exp(2x/R). The grading is
    what pushes the mode outward and, beyond the radius at which the equivalent
    cladding index reaches the mode index, what allows it to radiate.
    """
    if radius_um <= 0:
        raise ValueError("bend radius must be positive")
    return eps * np.exp(2.0 * np.asarray(x, dtype=float) / radius_um)[:, None]


def bend_window_limit(x: np.ndarray, radius_um: float, n_core: float, n_clad: float) -> float:
    """Outermost lateral position at which the transformed problem is still sound.

    The grading raises the equivalent cladding index without bound, so beyond

        n_clad * exp(x / R) = n_core   =>   x_limit = R * ln(n_core / n_clad)

    the cladding of the transformed problem is more strongly guiding than the
    core itself. A discretised solve then returns a state bound to the outer
    wall of the window, with an effective index above the core index and no
    physical meaning. The domain must end before that point.
    """
    return float(radius_um * np.log(max(n_core / n_clad, 1.0 + 1e-12)))


def solve_bend_modes(
    x: np.ndarray,
    y: np.ndarray,
    eps_xx: np.ndarray,
    eps_yy: np.ndarray,
    wavelength_um: float,
    radius_um: float,
    polarisation: str = "TE",
    num_modes: int = 1,
    n_guess: float | None = None,
    n_core_eff: float | None = None,
    n_clad_eff: float | None = None,
) -> list[ModeResult]:
    """Modes of a bend of radius ``radius_um``, by conformal transformation.

    The lateral domain is truncated where the transformation ceases to be sound
    (see ``bend_window_limit``), so that the outer-wall state it would otherwise
    produce cannot be returned in place of the guided one. A mode returned with
    an effective index above the largest index present in the untransformed
    cross-section is rejected rather than reported.
    """
    eps_dom = eps_xx if polarisation.upper() == "TE" else eps_yy
    # The guard compares the guiding strength of the core against that of the
    # region beside it, and for a ridge on a slab both are *effective* indices of
    # the vertical stack, not material indices. Reading the maximum permittivity
    # of the edge column instead returns the film index, which is present on both
    # sides, and the guard then truncates the domain to nothing. The caller
    # supplies the pair where it knows them.
    # ``n_core_eff`` is the index of the mode to be tracked, not the index of the
    # material: the artefact appears as soon as the graded cladding out-guides
    # *that mode*, which is the caustic, and not only when it exceeds the core.
    n_core = float(n_core_eff) if n_core_eff else float(np.sqrt(eps_dom.max()))
    n_clad = float(n_clad_eff) if n_clad_eff else float(np.sqrt(eps_dom[0, :].max()))
    if n_core <= n_clad:
        raise ValueError(
            f"the bend guard needs a core index above the cladding index; "
            f"{n_core:.4f} against {n_clad:.4f} was supplied"
        )
    limit = bend_window_limit(x, radius_um, n_core, n_clad)

    # Where the caustic falls inside the window the mode is genuinely leaky, and
    # a Dirichlet wall placed near it manufactures a bound state instead. The
    # transformation cannot answer that case; a leaky or time-domain solve must.
    if limit < float(x[-1]):
        raise RuntimeError(
            f"at radius {radius_um:g} um the radiation caustic falls at "
            f"{limit:.2f} um, inside the window edge at {float(x[-1]):.2f} um. The "
            "bend is leaky there and the conformal transformation returns a state "
            "bound to the wall rather than a mode; use a leaky or time-domain solve"
        )

    keep = x <= min(float(x[-1]), 0.95 * limit)
    if keep.sum() < 8:
        raise RuntimeError(
            f"bend radius {radius_um:g} um is too tight for this cross-section: the "
            "conformal transformation exceeds the core index within a few nodes of "
            "the axis, so no sound domain remains. A leaky-mode solve is required"
        )
    xc = x[keep]
    modes = solve_modes(
        xc, y,
        bend_permittivity(eps_xx[keep, :], xc, radius_um),
        bend_permittivity(eps_yy[keep, :], xc, radius_um),
        wavelength_um, polarisation=polarisation, num_modes=num_modes,
        n_guess=n_guess,
    )
    # a genuine bend mode sits a little above the straight index; the outer-wall
    # artefact sits far above it. One per cent separates the two cleanly.
    kept = [m for m in modes if m.n_eff <= n_core * 1.01]
    if not kept:
        raise RuntimeError(
            f"every mode returned at radius {radius_um:g} um has an effective index "
            f"above the core index {n_core:.4f}, which identifies them as artefacts "
            "of the transformation rather than modes of the bend"
        )
    return kept


def bend_diagnostics(
    mode: ModeResult, eps_cladding: float, radius_um: float
) -> dict[str, float]:
    """Where the bend radiates, and how much of the mode has reached there.

    The caustic is the lateral position at which the equivalent cladding index
    of the transformed problem rises to the mode index,

        n_clad * exp(x_c / R) = n_eff   =>   x_c = R * ln(n_eff / n_clad)

    Beyond it the field is no longer bound and carries power away. The fraction
    of the mode lying beyond that position is reported as an indicator of the
    bend loss. It is **not** the loss itself, which requires a leaky-mode solve
    with an absorbing boundary; it is a monotone measure that rises as the bend
    tightens, and is intended for comparing radii rather than for a budget.

    **The caustic frequently falls outside the computation window.** For a
    well-confined guide it sits tens of micrometres out, and the fraction beyond
    it is then zero because the window ends first, not because no power is lost.
    ``caustic_inside_window`` states which case obtains, and the fraction is
    returned as NaN where the question was not actually asked.
    """
    n_clad = float(np.sqrt(eps_cladding))
    x_caustic = radius_um * float(np.log(mode.n_eff / n_clad))
    inside = bool(x_caustic <= mode.x[-1])

    inten = mode.normalised_intensity()
    dx = np.gradient(mode.x)
    dy = np.gradient(mode.y)
    dA = np.outer(dx, dy)
    beyond = mode.x >= x_caustic
    power_beyond = float(np.sum((inten * dA)[beyond, :])) if inside else float("nan")

    centroid = float(np.sum(mode.x[:, None] * inten * dA))
    return {
        "radius_um": float(radius_um),
        "n_eff": float(mode.n_eff),
        "caustic_x_um": x_caustic,
        "caustic_inside_window": inside,
        "power_beyond_caustic": power_beyond,
        "lateral_centroid_um": centroid,
    }


def solve_slab(
    y: np.ndarray, eps_line: np.ndarray, wavelength_um: float, num_modes: int = 1
) -> list[float]:
    """1D slab solve for the *unpatterned* film stack (E parallel to the
    interfaces, i.e. the TE slab problem).

    Its fundamental index is the guidance floor for a rib waveguide: a ridge
    mode is laterally guided only while n_eff exceeds it.  Counting modes above
    the *cladding* index instead would flag every discretised slab continuum
    state as a guided mode.
    """
    k0 = 2 * np.pi / wavelength_um
    A = (_second_derivative_matrix(y) + sp.diags(k0**2 * eps_line)).tocsc()
    k = min(num_modes + 2, len(y) - 2)
    vals, _ = spla.eigs(A, k=k, sigma=(k0 * float(np.sqrt(eps_line.max()))) ** 2, which="LM")
    b2 = np.sort(np.real(vals))[::-1]
    return [float(np.sqrt(v) / k0) for v in b2 if v > 0][:num_modes]


def group_index(
    x, y, eps_xx, eps_yy, wavelength_um, polarisation="TE", dlam_um=0.01, n_guess=None
) -> tuple[float, float]:
    """Return ``(n_eff, n_g)`` at ``wavelength_um``.

    Material dispersion is *not* re-evaluated here; callers that need the full
    n_g must pass eps arrays at the shifted wavelengths.  ``modes.py`` does
    that properly - this helper is the waveguide-dispersion-only shortcut used
    by unit tests.
    """
    n0 = solve_modes(x, y, eps_xx, eps_yy, wavelength_um, polarisation, 1, n_guess)[0].n_eff
    np_ = solve_modes(x, y, eps_xx, eps_yy, wavelength_um + dlam_um, polarisation, 1, n_guess)[0].n_eff
    nm = solve_modes(x, y, eps_xx, eps_yy, wavelength_um - dlam_um, polarisation, 1, n_guess)[0].n_eff
    ng = n0 - wavelength_um * (np_ - nm) / (2 * dlam_um)
    return n0, ng
