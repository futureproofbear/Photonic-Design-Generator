"""Travelling-wave electrode: the closed-form parts, kept separate so they can be tested.

A lumped capacitance answers how fast a capacitor charges through a source
resistance. That is the right question only while the electrode is short against
the microwave wavelength. Beyond it the electrode is a transmission line, and
three quantities set the bandwidth: the mismatch between the microwave and
optical velocities, the attenuation of the conductor, and the distance of the
characteristic impedance from the driver.
"""

from __future__ import annotations

import cmath
import math

C0 = 299792458.0
MU0 = 4e-7 * math.pi
NEPER_TO_DB = 8.685889638065035


def line_parameters(c_per_m: float, c_air_per_m: float) -> dict[str, float]:
    """Microwave index and impedance from the two capacitances.

    A magnetostatic problem does not see the dielectrics, so the inductance
    follows from the same geometry solved in vacuum:

        L = 1 / (c^2 C_air),  n_m = c sqrt(L C) = sqrt(C / C_air),
        Z0 = sqrt(L / C) = 1 / (c sqrt(C C_air))
    """
    if c_per_m <= 0 or c_air_per_m <= 0:
        raise ValueError("both capacitances must be positive")
    return {
        "inductance_H_per_m": 1.0 / (C0**2 * c_air_per_m),
        "microwave_index": math.sqrt(c_per_m / c_air_per_m),
        "characteristic_impedance_ohm": 1.0 / (C0 * math.sqrt(c_per_m * c_air_per_m)),
    }


def skin_resistance_per_m(f_Hz: float, sigma: float, width_m: float,
                          thickness_m: float, n_conductors: int = 2) -> float:
    """Series resistance per unit length, the current occupying one skin depth."""
    if f_Hz <= 0 or sigma <= 0 or width_m <= 0 or thickness_m <= 0:
        return 0.0
    delta = math.sqrt(2.0 / (2 * math.pi * f_Hz * MU0 * sigma))
    return n_conductors / (sigma * min(delta, thickness_m) * width_m)


def response(f_Hz: float, length_m: float, alpha_np_per_m: float,
             n_microwave: float, n_optical: float) -> float:
    """Modulation response of a travelling-wave electrode, normalised to unity.

        m(f) = (1 - exp(-u)) / u,   u = alpha L + j (omega / c)(n_m - n_g) L

    The phasor sum along the electrode: the optical carrier accumulates phase at
    one velocity while the drive travels at another, and the loss removes drive
    as it goes.
    """
    w = 2 * math.pi * f_Hz
    u = complex(alpha_np_per_m * length_m,
                w * (n_microwave - n_optical) / C0 * length_m)
    if abs(u) < 1e-12:
        return 1.0
    return abs((1.0 - cmath.exp(-u)) / u)


def bandwidth(length_m: float, alpha_at: callable, n_microwave: float,
              n_optical: float, level: float = 1 / math.sqrt(2),
              f_start: float = 1e8, f_stop: float = 1e13,
              step: float = 1.02, tol: float = 1e-4) -> float:
    """Lowest frequency at which the response falls to ``level``.

    The coarse walk brackets the crossing and a bisection then resolves it to
    ``tol`` in fraction. Returning the first grid point of the walk, as this did
    until 2026-08-30, gives an upper bound biased high by up to one step, which
    was 2 per cent.

    That bias was not benign. Two electrode gaps whose capacitance, microwave
    index and conductor loss all differed returned a bandwidth identical in the
    last bit, because both crossings fell inside one step, and the equality was
    read as a physical result. A margin quoted at 0.3 per cent of the bound sat
    inside the step that produced it.
    """
    lo = f_start
    if response(lo, length_m, alpha_at(lo), n_microwave, n_optical) <= level:
        return lo
    hi = lo * step
    while hi < f_stop:
        if response(hi, length_m, alpha_at(hi), n_microwave, n_optical) <= level:
            # bracketed between lo and hi; bisect on the crossing
            while (hi - lo) / hi > tol:
                mid = 0.5 * (lo + hi)
                if response(mid, length_m, alpha_at(mid), n_microwave, n_optical) <= level:
                    hi = mid
                else:
                    lo = mid
            return hi
        lo, hi = hi, hi * step
    return float("inf")
