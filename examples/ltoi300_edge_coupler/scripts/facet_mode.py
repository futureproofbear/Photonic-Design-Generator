"""The facet mode of the LTOI300 edge couplers, and what a fibre collects from it.

The cell is a double inverse taper. The lower taper is drawn on the slab layer
and runs the whole 160 um, and the upper taper is the ridge, which appears only
over the last 80 um. At the facet the ridge has ended, the surrounding slab has
been removed by the negative layer over a 20 um window, and what remains is one
strip of the 120 nm slab film in oxide. That strip carries the mode a fibre
sees, and its width is the tip of the lower taper: 0.35 um in the O band and
0.50 um in the C band.

The builder states the design target: the default values are optimised for an
O-band lensed fibre of 2.15 um mode-field diameter.

Four quantities are computed here, all from the same solved mode.

The mode-field diameters of the facet mode, taken as the 1/e^2 intensity widths
through the peak, which is the definition a fibre datasheet uses.

The power overlap with a circular Gaussian of the fibre's mode-field diameter,
maximised over the vertical offset, since a facet is aligned in assembly and a
figure taken at an arbitrary offset describes nothing.

The alignment tolerance, being the lateral and vertical displacements that cost
one decibel.

The Fresnel reflection at the facet, from the mode index against air and against
an index-matched medium.

    python examples/ltoi300_edge_coupler/scripts/facet_mode.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain.coupling import gaussian_mode, power_overlap   # noqa: E402
from picchain.materials import MaterialLibrary               # noqa: E402
from picchain.solvers.fdmode import solve_modes              # noqa: E402

MATERIALS = ROOT / "design-chain" / "pdk" / "LXT_LT_PRO" / "materials_lt_pro.yaml"

#: name, tip width of the lower taper, wavelength, the fibre the kit names
CASES = (
    ("O band", 0.35, 1.31, 2.15),
    ("C band", 0.50, 1.55, 2.15),
)
SLAB_UM = 0.12          # the film that remains where the ridge is etched away


def graded(half_fine: float, d_fine: float, half_total: float, d_coarse: float):
    """A symmetric axis, fine about the origin and coarse beyond."""
    fine = np.arange(0.0, half_fine + d_fine / 2, d_fine)
    coarse = np.arange(half_fine + d_coarse, half_total + d_coarse / 2, d_coarse)
    half = np.concatenate([fine, coarse])
    return np.concatenate([-half[:0:-1], half])


def facet_mode(width_um: float, lam_um: float, lib: MaterialLibrary):
    """The fundamental mode of one strip of slab film, surrounded by oxide."""
    n_lt = float(lib["LiTaO3"].index(lam_um, "e"))
    n_ox = float(lib["SiO2"].index(lam_um))

    x = graded(1.5, 0.010, 7.0, 0.10)
    y = graded(1.0, 0.006, 6.0, 0.10)
    eps = np.full((len(x), len(y)), n_ox ** 2)
    core = (np.abs(x)[:, None] <= width_um / 2) & \
           (y[None, :] >= -SLAB_UM / 2) & (y[None, :] <= SLAB_UM / 2)
    eps[core] = n_lt ** 2

    modes = solve_modes(x, y, eps, eps, lam_um, "TE", 1, None)
    if not modes:
        raise RuntimeError(f"the {width_um} um strip guides no mode at {lam_um} um")
    return x, y, modes[0], n_ox


def second_moment_diameter(x, y, field) -> tuple[float, float]:
    """The second-moment width, four sigma, which counts the tails.

    A guide whose index sits barely above its cladding carries most of its power
    outside the core. The width taken through the peak then measures the spike
    and misses the mode, and the two definitions part company by a factor of
    several. This is the definition a coupling calculation requires, since a
    fibre collects the tails as well.
    """
    inten = np.abs(field) ** 2
    dA = np.outer(np.gradient(x), np.gradient(y))
    total = float(np.sum(inten * dA))
    xc = float(np.sum(x[:, None] * inten * dA) / total)
    yc = float(np.sum(y[None, :] * inten * dA) / total)
    vx = float(np.sum((x[:, None] - xc) ** 2 * inten * dA) / total)
    vy = float(np.sum((y[None, :] - yc) ** 2 * inten * dA) / total)
    return 4.0 * np.sqrt(vx), 4.0 * np.sqrt(vy)


def mode_field_diameter(x, y, field) -> tuple[float, float]:
    """The 1/e^2 intensity widths through the peak, in each axis."""
    inten = np.abs(field) ** 2
    i, j = np.unravel_index(np.argmax(inten), inten.shape)

    def width(axis_vals, line) -> float:
        line = line / line.max()
        above = np.where(line >= np.exp(-2.0))[0]
        if len(above) < 2:
            return float("nan")
        lo, hi = above[0], above[-1]
        return float(axis_vals[hi] - axis_vals[lo])

    return width(x, inten[:, j]), width(y, inten[i, :])


def best_overlap(x, y, field, mfd_um: float):
    """Power overlap with a circular Gaussian, maximised over the vertical offset."""
    dA = np.outer(np.gradient(x), np.gradient(y))
    w0 = mfd_um / 2.0                     # 1/e field radius
    best = (0.0, 0.0)
    for y0 in np.linspace(-0.6, 0.6, 61):
        g = gaussian_mode(x, y, w0, w0, 0.0, float(y0))
        eta = power_overlap(np.abs(field), g, dA)
        if eta > best[0]:
            best = (float(eta), float(y0))
    return best


def offset_for_one_dB(x, y, field, mfd_um: float, y_opt: float, axis: str) -> float:
    """The displacement from the optimum that costs one decibel."""
    dA = np.outer(np.gradient(x), np.gradient(y))
    w0 = mfd_um / 2.0
    g0 = gaussian_mode(x, y, w0, w0, 0.0, y_opt)
    eta0 = power_overlap(np.abs(field), g0, dA)
    for d in np.arange(0.01, 3.0, 0.01):
        x0, y0 = (d, y_opt) if axis == "lateral" else (0.0, y_opt + d)
        g = gaussian_mode(x, y, w0, w0, float(x0), float(y0))
        if power_overlap(np.abs(field), g, dA) < eta0 * 10 ** (-0.1):
            return float(d)
    return float("nan")


def main() -> int:
    lib = MaterialLibrary(MATERIALS) if MATERIALS.exists() else MaterialLibrary()
    for name, width, lam, fibre in CASES:
        x, y, mode, n_ox = facet_mode(width, lam, lib)
        f = np.asarray(mode.field, dtype=float)
        mfd_x, mfd_y = mode_field_diameter(x, y, f)
        d4x, d4y = second_moment_diameter(x, y, f)
        eta, y_opt = best_overlap(x, y, f, fibre)
        r_air = ((mode.n_eff - 1.0) / (mode.n_eff + 1.0)) ** 2
        r_gel = ((mode.n_eff - n_ox) / (mode.n_eff + n_ox)) ** 2
        dx1 = offset_for_one_dB(x, y, f, fibre, y_opt, "lateral")
        dy1 = offset_for_one_dB(x, y, f, fibre, y_opt, "vertical")

        print(f"\n{name}: a {width:.2f} um strip of the {SLAB_UM*1e3:.0f} nm film "
              f"at {lam:.2f} um")
        print(f"  n_eff                        {mode.n_eff:.5f}")
        print(f"  width through the peak       {mfd_x:.3f} um lateral, "
              f"{mfd_y:.3f} um vertical")
        print(f"  second-moment width          {d4x:.3f} um lateral, "
              f"{d4y:.3f} um vertical")
        print(f"  overlap with a {fibre:.2f} um fibre  {eta:.4f}, being "
              f"{-10*np.log10(max(eta,1e-12)):.2f} dB, at an offset of {y_opt:+.3f} um")
        print(f"  one decibel of misalignment  {dx1:.2f} um lateral, "
              f"{dy1:.2f} um vertical")
        print(f"  facet reflection             {r_air:.4f} into air, "
              f"{r_gel:.2e} into an index-matched medium")

        for other in (1.8, 2.5, 3.0, 4.0):
            eta_o, _ = best_overlap(x, y, f, other)
            print(f"    against a {other:.1f} um fibre       {eta_o:.4f}, being "
                  f"{-10*np.log10(max(eta_o,1e-12)):.2f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
