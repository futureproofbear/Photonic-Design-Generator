"""Steady-state heat conduction in a die cross-section, for a heater over a guide.

A resistive wire above a waveguide sets the guide's temperature, and it sets the
temperature of everything else on the die as well. Three quantities follow from
one solve of the conduction equation across the die's cross-section, and the
chain had estimated all three rather than computing them: how many kelvin the
guide rises per milliwatt of heater power, which sizes the trimmer's drive; how
much of that rise reaches a neighbouring device, which is the coupling between
two trimmers on one die; and how the rise decays with lateral distance, which is
what a mirror beside a heater sees.

The model is two-dimensional, in the plane transverse to the guide, and treats
the heater as a line source of uniform power per unit length. That is the right
plane for a wire many times longer than the die is thick. It carries no heat
along the guide, so the temperature at the end of a wire, or at a mirror beyond
it, is not this model's answer; the lateral decay it does return is the same
spreading mechanism in the other direction, and is quoted for that purpose with
the plane stated.

The equation is  -div(k grad T) = q  with k piecewise constant by layer, a fixed
temperature at the bottom of the handle where the cooler sits, and no flux
through the top surface and the far sides, which are taken far enough out that
the choice does not matter. Air above the cladding is treated as insulating,
which is the conservative direction for the guide's rise and the neutral one for
the lateral spread, since the spread is carried by the handle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Layer:
    name: str
    thickness_um: float
    k_W_per_mK: float


@dataclass
class HeaterStack:
    """The die from the cooler up, with the heater on top of the last layer."""
    layers: list[Layer] = field(default_factory=list)
    #: half-width of the model, um. The far side is insulated, so it is to be
    #: several handle thicknesses out.
    half_width_um: float = 1500.0
    #: the heater as a line source: width and the power per unit length
    heater_width_um: float = 1.5
    #: x positions at which the temperature is wanted, um, e.g. a neighbour
    probes_um: list[float] = field(default_factory=list)


# thermal conductivities at room temperature, W/(m K)
K_SI = 148.0
K_SIO2 = 1.4
K_LITAO3 = 4.6      # bulk, c-axis and a-axis within ~10 % of one another
K_LINBO3 = 5.6


def _grid(stack: HeaterStack, dx_min_um: float, dz_min_um: float):
    """A graded tensor grid: fine over the heater and the film, coarse far out."""
    W = stack.half_width_um
    # lateral: fine within a few heater widths, geometric growth outward
    xs = [0.0]
    dx = dx_min_um
    while xs[-1] < W:
        xs.append(xs[-1] + dx)
        if xs[-1] > 5 * stack.heater_width_um:
            dx = min(dx * 1.08, 25.0)
    x_half = np.array(xs)
    x = np.concatenate([-x_half[::-1][:-1], x_half])
    # vertical: every interface is a node; thin layers get dz_min, thick ones grow
    z_nodes = [0.0]
    z = 0.0
    for L in stack.layers:
        n = max(2, int(np.ceil(L.thickness_um / dz_min_um)))
        if L.thickness_um > 50.0:
            # geometric growth away from the top of the thick layer, so the
            # handle is resolved where the heat enters and coarse at the sink
            n = max(n, 30)
            t = np.linspace(0, 1, n + 1)
            seg = z + L.thickness_um * (1 - (1 - t) ** 2.2)[::-1]
            seg = z + L.thickness_um * (1 - (1 - t) ** 2.2)
            z_nodes.extend(seg[1:].tolist())
        else:
            z_nodes.extend((z + np.linspace(0, L.thickness_um, n + 1)[1:]).tolist())
        z += L.thickness_um
    zz = np.array(z_nodes)
    return x, zz


def solve(stack: HeaterStack, power_W_per_m: float = 1.0,
          dx_min_um: float = 0.25, dz_min_um: float = 0.1) -> dict[str, Any]:
    """Temperature rise field for a line heater of the given power per length.

    Returns the rise at the top of the film under the heater, at every probe,
    and the whole field, in kelvin per (W/m). Linear in the power, so any drive
    is a scaling.
    """
    x, z = _grid(stack, dx_min_um, dz_min_um)
    nx, nz = len(x), len(z)
    # conductivity per cell (cells are between nodes)
    kz = np.empty(nz - 1)
    zc = 0.5 * (z[:-1] + z[1:])
    top = 0.0
    bounds = []
    for L in stack.layers:
        bounds.append((top, top + L.thickness_um, L.k_W_per_mK)); top += L.thickness_um
    for j, zj in enumerate(zc):
        for lo, hi, k in bounds:
            if lo <= zj < hi or (j == nz - 2 and zj <= hi):
                kz[j] = k
                break
    k_cell = np.tile(kz[None, :], (nx - 1, 1))             # (nx-1, nz-1), uniform in x

    # finite volumes on the tensor grid; unknowns at nodes
    N = nx * nz
    idx = lambda i, j: i * nz + j
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    A = lil_matrix((N, N)); b = np.zeros(N)
    dx = np.diff(x) * 1e-6; dz = np.diff(z) * 1e-6
    # node control volumes
    wx = np.zeros(nx); wx[:-1] += dx / 2; wx[1:] += dx / 2
    wz = np.zeros(nz); wz[:-1] += dz / 2; wz[1:] += dz / 2
    for i in range(nx):
        for j in range(nz):
            p = idx(i, j)
            if j == 0:                       # bottom of the handle: the cooler
                A[p, p] = 1.0; b[p] = 0.0
                continue
            diag = 0.0
            # west / east faces
            for di, ii in ((-1, i - 1), (1, i + 1)):
                if 0 <= ii < nx:
                    ci = min(i, ii)
                    # conductance through the face: harmonic in k over the two
                    # half-cells is not needed, k is uniform in x within a layer
                    kf = 0.0
                    if j > 0: kf += k_cell[ci, j - 1] * dz[j - 1] / 2
                    if j < nz - 1: kf += k_cell[ci, j] * dz[j] / 2
                    g = kf / dx[ci]
                    A[p, idx(ii, j)] -= g; diag += g
            # south / north faces
            for dj, jj in ((-1, j - 1), (1, j + 1)):
                if 0 <= jj < nz:
                    cj = min(j, jj)
                    g = k_cell[min(i, nx - 2), cj] * wx[i] / dz[cj]
                    A[p, idx(i, jj)] -= g; diag += g
            A[p, p] += diag
    # the heater: power per length spread over its width on the top surface
    hw = stack.heater_width_um
    top_nodes = [i for i in range(nx) if abs(x[i]) <= hw / 2 + 1e-9]
    if not top_nodes:
        top_nodes = [int(np.argmin(np.abs(x)))]
    for i in top_nodes:
        b[idx(i, nz - 1)] += power_W_per_m * (wx[i] / (hw * 1e-6)) if len(top_nodes) > 1 else power_W_per_m
    T = spsolve(A.tocsr(), b).reshape(nx, nz)

    # the film's top surface: the layer boundary below the cladding
    z_film_top = sum(L.thickness_um for L in stack.layers[:-1])
    jf = int(np.argmin(np.abs(z - z_film_top)))
    i0 = int(np.argmin(np.abs(x)))
    out = {
        "power_W_per_m": power_W_per_m,
        "rise_at_guide_K": float(T[i0, jf]),
        "rise_at_top_under_heater_K": float(T[i0, nz - 1]),
        "probes": {},
        "x_um": x, "z_um": z, "T_K": T,
        "grid": [int(nx), int(nz)],
    }
    for px in stack.probes_um:
        ip = int(np.argmin(np.abs(x - px)))
        out["probes"][f"{px:g}"] = float(T[ip, jf])
    return out


def report(stack: HeaterStack, wire_length_um: float, drive_mW: float,
           dx_min_um: float = 0.25, dz_min_um: float = 0.1) -> dict[str, Any]:
    """The three quantities a trimmer needs, at a stated drive."""
    r = solve(stack, 1.0, dx_min_um, dz_min_um)
    P_per_m = drive_mW * 1e-3 / (wire_length_um * 1e-6)
    K_per_mW = r["rise_at_guide_K"] * (1e-3 / (wire_length_um * 1e-6))
    out = {
        "wire_length_um": wire_length_um,
        "drive_mW": drive_mW,
        "power_W_per_m": P_per_m,
        "K_per_mW": K_per_mW,
        "rise_at_guide_K": r["rise_at_guide_K"] * P_per_m,
        "mW_for_60K": 60.0 / K_per_mW if K_per_mW > 0 else float("inf"),
        "probes_K": {k: v * P_per_m for k, v in r["probes"].items()},
        "probes_fraction_of_guide": {k: v / r["rise_at_guide_K"] for k, v in r["probes"].items()},
        "grid": r["grid"],
    }
    return out
