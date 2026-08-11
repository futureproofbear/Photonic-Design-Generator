"""Eigenmode expansion for a longitudinally varying waveguide.

The structure is approximated by a staircase of uniform sections.  Within a
section the field is a sum of that section's guided and discretised radiation
modes, propagating with their own phase; at each interface the mode sets are
matched by continuity of the transverse fields.  Sections are combined by the
Redheffer star product, so reflection is retained rather than discarded.

Field convention
----------------
The mode solver is semi-vectorial and returns the dominant transverse electric
component only.  The transverse magnetic component is therefore taken as

    H_i  =  n_eff,i * E_i / eta_0

which is exact for a plane wave and is the standard approximation for a mode
whose transverse profile is dominated by one component.  Two consequences are
used below: the power carried by mode ``i`` with amplitude ``a`` is
``n_eff,i |a|^2`` under the normalisation ``\\int |E_i|^2 dA = 1``, and a
single-mode interface between two sections reduces exactly to the Fresnel
result for two media of index ``n_eff,L`` and ``n_eff,R``.  Both are enforced by
the tests.

Why the Gram matrix appears
---------------------------
The semi-vectorial operator is not symmetric, so the modes of one section are
not exactly orthogonal under the plain overlap integral.  Projection onto the
left-hand basis is therefore performed through the Gram matrix
``G_ij = <E_i | E_j>`` rather than by assuming ``G = I``.  For a well-converged
mesh G is close to the identity, and the general form is retained because the
error it removes is of the same order as the taper loss being computed.

An S-matrix is held as the tuple ``(S11, S12, S21, S22)`` with the usual
partition: ``S11`` reflects back into the left port, ``S21`` transmits left to
right, ``S12`` transmits right to left, and ``S22`` reflects back into the right
port.

Two paths are provided, and the choice between them is a statement about the
structure rather than about the desired accuracy.

``slice_chain`` performs full mode matching and retains reflection. It requires
the expansion at each interface to be reasonably complete, since the electric
and magnetic continuity conditions are otherwise over-determined; a severely
truncated basis returns amplitudes above unity. It is the correct path for an
abrupt junction, and it reduces exactly to the Fresnel coefficients in the
single-mode limit.

``local_mode_chain`` propagates the local modes adiabatically and neglects
reflection, which is the appropriate statement for a taper designed to vary
slowly. Power leaving the retained set is reported as radiation rather than
being silently redistributed. This is the path used by the taper stage.
"""

from __future__ import annotations

from typing import Any

import numpy as np

SMatrix = tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def cell_areas(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Voronoi cell area of each node of a (possibly graded) tensor grid."""
    return np.outer(np.gradient(x), np.gradient(y))


def normalise(fields: np.ndarray, dA: np.ndarray) -> np.ndarray:
    """Scale each mode so that ``sum(|E|^2 dA) == 1``.

    ``fields`` is (m, nx, ny).  The sign of each mode is fixed by requiring the
    largest-magnitude sample to be positive, so that an overlap does not change
    sign between two solves of the same cross-section.
    """
    out = np.array(fields, dtype=float, copy=True)
    for i in range(out.shape[0]):
        f = out[i]
        norm = float(np.sqrt(np.sum(f * f * dA)))
        if norm <= 0.0:
            raise ValueError(f"mode {i} has zero norm")
        f /= norm
        if f.flat[np.argmax(np.abs(f))] < 0.0:
            f *= -1.0
        out[i] = f
    return out


def overlap(a: np.ndarray, b: np.ndarray, dA: np.ndarray) -> np.ndarray:
    """Matrix ``O_ij = <a_i | b_j>`` for two mode sets on a shared grid."""
    if a.shape[1:] != b.shape[1:] or a.shape[1:] != dA.shape:
        raise ValueError("mode sets and cell areas must share one grid")
    A = a.reshape(a.shape[0], -1)
    B = (b * dA).reshape(b.shape[0], -1)
    return A @ B.T


def interface_smatrix(
    n_left: np.ndarray, n_right: np.ndarray, O: np.ndarray, G_left: np.ndarray, G_right: np.ndarray
) -> SMatrix:
    """S-matrix of the abrupt junction between two mode sets.

    ``O`` is the overlap of the left modes against the right modes, and the two
    Gram matrices are the self-overlaps of each set.  Continuity of the
    transverse electric and magnetic fields gives, for incidence from the left,

        G_L (a + r) = O t                 (electric)
        G_L N_L (a - r) = O N_R t         (magnetic)

    from which ``t`` and ``r`` follow.  Incidence from the right is the same
    statement with the two sides exchanged and ``O`` transposed.
    """
    NL, NR = np.diag(n_left), np.diag(n_right)
    GLi, GRi = np.linalg.pinv(G_left), np.linalg.pinv(G_right)
    NLi, NRi = np.diag(1.0 / n_left), np.diag(1.0 / n_right)

    # left incidence
    M = GLi @ O + NLi @ GLi @ O @ NR
    S21 = 2.0 * np.linalg.pinv(M)
    S11 = GLi @ O @ S21 - np.eye(len(n_left))

    # right incidence
    OT = O.T
    M2 = GRi @ OT + NRi @ GRi @ OT @ NL
    S12 = 2.0 * np.linalg.pinv(M2)
    S22 = GRi @ OT @ S12 - np.eye(len(n_right))

    return S11, S12, S21, S22


def propagation_smatrix(n_eff: np.ndarray, length_um: float, wavelength_um: float) -> SMatrix:
    """S-matrix of a uniform section: phase only, no reflection."""
    k0 = 2.0 * np.pi / wavelength_um
    P = np.diag(np.exp(1j * k0 * np.asarray(n_eff, dtype=float) * length_um))
    Z = np.zeros_like(P)
    return Z, P, P, Z


def star(A: SMatrix, B: SMatrix) -> SMatrix:
    """Redheffer star product, combining A (ports 1,2) with B (ports 2,3)."""
    A11, A12, A21, A22 = (np.asarray(m, dtype=complex) for m in A)
    B11, B12, B21, B22 = (np.asarray(m, dtype=complex) for m in B)
    I = np.eye(A22.shape[0], dtype=complex)
    D = np.linalg.inv(I - A22 @ B11)
    F = np.linalg.inv(I - B11 @ A22)
    return (
        A11 + A12 @ D @ B11 @ A21,
        A12 @ D @ B12,
        B21 @ F @ A21,
        B22 + B21 @ F @ A22 @ B12,
    )


def cascade(sections: list[SMatrix]) -> SMatrix:
    """Star-product of a list of S-matrices, left to right."""
    if not sections:
        raise ValueError("no sections to cascade")
    total = sections[0]
    for s in sections[1:]:
        total = star(total, s)
    return total


def slice_chain(
    n_effs: list[np.ndarray],
    fields: list[np.ndarray],
    dA: np.ndarray,
    lengths_um: list[float],
    wavelength_um: float,
) -> SMatrix:
    """Assemble the staircase: propagate each slice, then match to the next.

    ``n_effs[k]`` and ``fields[k]`` describe slice ``k`` on the shared grid, and
    ``lengths_um[k]`` is its longitudinal extent.  Slices may carry different
    mode counts, the interface matrices then being rectangular and resolved in
    the least-squares sense.  See the module docstring for the completeness
    condition under which this path is applicable.
    """
    if not (len(n_effs) == len(fields) == len(lengths_um)):
        raise ValueError("n_effs, fields and lengths must be of equal length")

    norm = [normalise(f, dA) for f in fields]
    grams = [overlap(f, f, dA) for f in norm]

    parts: list[SMatrix] = []
    for k in range(len(n_effs)):
        parts.append(propagation_smatrix(n_effs[k], lengths_um[k], wavelength_um))
        if k + 1 < len(n_effs):
            O = overlap(norm[k], norm[k + 1], dA)
            parts.append(interface_smatrix(n_effs[k], n_effs[k + 1], O, grams[k], grams[k + 1]))
    return cascade(parts)


def local_mode_chain(
    fields: list[np.ndarray],
    dA: np.ndarray,
    n_effs: list[np.ndarray] | None = None,
    lengths_um: list[float] | None = None,
    wavelength_um: float | None = None,
) -> dict[str, Any]:
    """Adiabatic (local-mode) propagation through a staircase of slices.

    This is the path used for a taper, and it differs from ``slice_chain`` in
    what it assumes rather than in what it approximates. Mode matching by
    ``interface_smatrix`` requires the expansion at each interface to be
    complete; a truncated basis over-determines the two continuity conditions
    and returns amplitudes above unity. A taper, by contrast, is designed to be
    slowly varying, so reflection is negligible and only the projection of each
    local mode onto the next is required.

    The propagation phase between slices is applied where ``n_effs``,
    ``lengths_um`` and ``wavelength_um`` are supplied, and it is required for
    the conversion between guided modes to be evaluated correctly: without it,
    the contributions from successive steps add in phase and the conversion is
    over-stated.

    Amplitudes are held power-normalised, so that the squared amplitude vector
    is the fraction of the incident power still carried by the retained modes.

    **What the deficit means.** Only guided modes are to be passed. Power that
    fails to project onto the guided set of the next slice has, in this model,
    left the guided modes at a step. For a physical taper the steps are an
    artefact of the discretisation and that deficit falls as the slice count
    rises, tending to zero for a smoothly varying single-mode taper. It is
    therefore reported as ``staircase_deficit`` and is **not** an estimate of
    radiation loss, which requires the continuum and is outside this basis. The
    quantity that does converge, and that is physically meaningful, is the
    conversion into other guided modes.
    """
    if len(fields) < 2:
        raise ValueError("at least two slices are required")
    norm = [normalise(f, dA) for f in fields]
    phased = n_effs is not None and lengths_um is not None and wavelength_um is not None

    b = np.zeros(norm[0].shape[0], dtype=complex)
    b[0] = 1.0
    history = [float(abs(b[0]) ** 2)]
    for k in range(len(norm) - 1):
        if phased:
            k0 = 2.0 * np.pi / wavelength_um
            b = np.exp(1j * k0 * np.asarray(n_effs[k], dtype=float) * lengths_um[k]) * b
        C = overlap(norm[k + 1], norm[k], dA)     # rows: next slice, columns: this slice
        b = C @ b
        history.append(float(abs(b[0]) ** 2))

    retained = float(np.sum(np.abs(b) ** 2))
    fundamental = float(abs(b[0]) ** 2)
    converted = max(0.0, retained - fundamental)
    # the physical loss channel within this basis is conversion between guided
    # modes, so it is measured against the power still in the guided set rather
    # than against the input; the remainder is the numerical deficit
    frac = fundamental / retained if retained > 0 else 0.0
    return {
        "transmission_fundamental": fundamental,
        "transmission_guided": retained,
        "reflection": 0.0,
        "staircase_deficit": max(0.0, 1.0 - retained),
        "conversion_to_higher_order": converted,
        "conversion_loss_dB": -10.0 * np.log10(frac) if frac > 0 else float("inf"),
        "fundamental_by_slice": history,
    }


def adiabaticity(
    widths_um: np.ndarray, n_eff_fundamental: np.ndarray, n_reference: float,
    length_um: float, wavelength_um: float,
) -> dict[str, Any]:
    """Local adiabaticity margin along a taper.

    The standard criterion compares the rate at which the guide changes with the
    beat length against the state into which power would be lost. With

        L_beat = lambda / (n_eff - n_reference)

    the taper is adiabatic where the fractional change of width over one beat
    length is small. The margin returned is

        A = 1 / ( |dw/dz| * L_beat / w )

    so that A >> 1 denotes an adiabatic section and A of order unity denotes a
    section where power is expected to be lost. ``n_reference`` is the index of
    the state that sets the loss channel: the slab for radiation, or the next
    guided mode for conversion.
    """
    w = np.asarray(widths_um, dtype=float)
    n0 = np.asarray(n_eff_fundamental, dtype=float)
    dz = length_um / len(w)
    dwdz = np.gradient(w, dz)
    dn = np.maximum(n0 - n_reference, 1e-9)
    L_beat = wavelength_um / dn
    rate = np.abs(dwdz) * L_beat / w
    A = 1.0 / np.maximum(rate, 1e-12)
    i = int(np.argmin(A))
    return {
        "min_adiabaticity": float(A[i]),
        "min_adiabaticity_at_width_um": float(w[i]),
        "beat_length_at_minimum_um": float(L_beat[i]),
        "profile": A,
    }


def fundamental_transmission(S: SMatrix, n_in: np.ndarray, n_out: np.ndarray) -> dict[str, float]:
    """Power transmitted into, and reflected from, the fundamental mode.

    Power is ``n_eff |amplitude|^2`` under the field normalisation used here, so
    the transmitted fraction carries the ratio of the two effective indices.
    """
    S11, _, S21, _ = S
    t = S21[:, 0]
    r = S11[:, 0]
    p_in = float(n_in[0])
    t_fund = float(n_out[0] * abs(t[0]) ** 2 / p_in)
    t_total = float(np.sum(np.asarray(n_out) * np.abs(t) ** 2) / p_in)
    r_total = float(np.sum(np.asarray(n_in) * np.abs(r) ** 2) / p_in)
    loss_dB = -10.0 * np.log10(t_fund) if t_fund > 0 else float("inf")
    return {
        "transmission_fundamental": t_fund,
        "transmission_all_modes": t_total,
        "reflection": r_total,
        "loss_dB": loss_dB,
        "higher_order_fraction": max(0.0, t_total - t_fund),
        "power_balance": t_total + r_total,
    }
