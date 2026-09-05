"""Anisotropic 2D electrostatic solver (numpy/scipy only).

Solves  div( eps . grad V ) = 0  with diagonal eps(x, y) on the same graded
tensor-product mesh used by the mode solver, so the RF field and the optical
intensity can be overlapped node-for-node without interpolation.

Boundary conditions
-------------------
* Dirichlet on any node whose electrode mask is > 0.5.
* Natural (zero-flux / Neumann) on the outer boundary.  Put the window edges a
  few electrode gaps away from the electrodes so this is harmless.

This is the quasi-static approximation.  It is the right model for the DC and
low-MHz tuning regime that sets the Pockels tuning efficiency; the electrode
*bandwidth* is handled separately in ``eo.py`` via a lumped RC / travelling-wave
estimate, because at >1 GHz a lumped electrode is no longer quasi-static.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


@dataclass
class ElectrostaticResult:
    V: np.ndarray  # (nx, ny) potential
    Ex: np.ndarray  # (nx, ny) V/um
    Ey: np.ndarray
    x: np.ndarray
    y: np.ndarray

    def energy_density(self, eps_x: np.ndarray, eps_y: np.ndarray) -> np.ndarray:
        """Stored energy per cell, in eps0 * V^2 units."""
        dA = np.outer(np.gradient(self.x), np.gradient(self.y))
        return 0.5 * (eps_x * self.Ex**2 + eps_y * self.Ey**2) * dA

    def energy(self, eps_x: np.ndarray, eps_y: np.ndarray) -> float:
        """Stored electrostatic energy per unit length, in eps0 * V^2 units."""
        return float(np.sum(self.energy_density(eps_x, eps_y)))


def solve_potential(
    x: np.ndarray,
    y: np.ndarray,
    eps_x: np.ndarray,
    eps_y: np.ndarray,
    electrodes: list[tuple[np.ndarray, float]],
) -> ElectrostaticResult:
    """Finite-volume solve.

    ``electrodes`` is a list of ``(mask, potential_volts)``; ``mask`` is a
    (nx, ny) fractional-occupancy array (>0.5 counts as metal).
    """
    nx, ny = len(x), len(y)
    hx = np.diff(x)
    hy = np.diff(y)
    # control-volume widths
    wx = np.empty(nx)
    wx[0] = hx[0] / 2
    wx[-1] = hx[-1] / 2
    wx[1:-1] = (hx[:-1] + hx[1:]) / 2
    wy = np.empty(ny)
    wy[0] = hy[0] / 2
    wy[-1] = hy[-1] / 2
    wy[1:-1] = (hy[:-1] + hy[1:]) / 2

    N = nx * ny
    fixed = np.zeros((nx, ny), dtype=bool)
    fixed_val = np.zeros((nx, ny))
    for mask, volts in electrodes:
        sel = mask > 0.5
        fixed |= sel
        fixed_val[sel] = volts
    if not fixed.any():
        raise ValueError("no electrode node found - check the electrode masks")

    # harmonic-mean face permittivities
    eps_face_x = 2.0 / (1.0 / eps_x[:-1, :] + 1.0 / eps_x[1:, :])  # (nx-1, ny)
    eps_face_y = 2.0 / (1.0 / eps_y[:, :-1] + 1.0 / eps_y[:, 1:])  # (nx, ny-1)

    # five-point stencil, assembled vectorised (index p = i*ny + j)
    cW = np.zeros((nx, ny)); cE = np.zeros((nx, ny))
    cS = np.zeros((nx, ny)); cN = np.zeros((nx, ny))
    cW[1:, :] = eps_face_x * wy[None, :] / hx[:, None]
    cE[:-1, :] = eps_face_x * wy[None, :] / hx[:, None]
    cS[:, 1:] = eps_face_y * wx[:, None] / hy[None, :]
    cN[:, :-1] = eps_face_y * wx[:, None] / hy[None, :]
    diag = -(cW + cE + cS + cN)

    free = ~fixed
    cW *= free; cE *= free; cS *= free; cN *= free
    diag = np.where(fixed, 1.0, diag)

    A = sp.diags(
        [
            cW.ravel()[ny:],        # offset -ny  (i-1, j)
            cS.ravel()[1:],         # offset -1   (i,   j-1)
            diag.ravel(),
            cN.ravel()[:-1],        # offset +1   (i,   j+1)
            cE.ravel()[:-ny],       # offset +ny  (i+1, j)
        ],
        [-ny, -1, 0, 1, ny],
        shape=(N, N),
        format="csc",
    )
    rhs = np.where(fixed, fixed_val, 0.0).ravel()
    V = spla.spsolve(A, rhs).reshape(nx, ny)

    Ex = -np.gradient(V, x, axis=0)
    Ey = -np.gradient(V, y, axis=1)
    return ElectrostaticResult(V=V, Ex=Ex, Ey=Ey, x=x, y=y)


def eo_overlap(
    field_Erf: np.ndarray,
    intensity: np.ndarray,
    active_mask: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    gap_um: float,
    voltage: float,
) -> float:
    """Electro-optic overlap factor

        Gamma = (G/V) * Int_active( E_rf |E_opt|^2 ) / Int_all( |E_opt|^2 )

    which is the factor by which the naive parallel-plate estimate
    dn = 1/2 n^3 r33 (V/G) must be scaled to give the real dn_eff.  It folds in
    both the optical confinement in the electro-optic material and the
    non-uniformity of the RF field (which, in LN/LT, is substantial because the
    film permittivity is ~10x the cladding).
    """
    dx = np.gradient(x)
    dy = np.gradient(y)
    dA = np.outer(dx, dy)
    num = np.sum(field_Erf * intensity * active_mask * dA)
    den = np.sum(intensity * dA)
    return float((gap_um / voltage) * num / den)
