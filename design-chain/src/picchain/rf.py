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


def response_loaded(f_Hz: float, length_m: float, alpha_np_per_m: float,
                    n_microwave: float, n_optical: float,
                    reflection: float = 0.0, reference: str = "dc",
                    stub_m: float = 0.0) -> float:
    """The same, for a line whose far end is not matched to it.

    A matched line carries one forward wave and the expression above is
    complete. A line left open, which is what a bonding pad presents, returns a
    wave from that end, and the optical carrier meets both on its way forward.
    The returned wave travels against the carrier, so the two walk off at the
    sum of the indices rather than at their difference, and it therefore
    contributes at low frequency and disappears at high.

    Writing the propagation constant as ``g = alpha + j omega n_m / c``, the
    forward wave contributes ``(1 - exp(-u_f)) / u_f`` as before, and the
    returned wave contributes ``G exp(-2 g L) (exp(u_b) - 1) / u_b`` with

        u_f = (alpha + j (omega / c)(n_m - n_o)) L
        u_b = (alpha + j (omega / c)(n_m + n_o)) L

    ``reflection`` is the coefficient the far-end load presents to the line. It
    is zero where the two are matched, plus one at an open end and minus one at
    a short. At ``reflection = 0`` the expression reduces term by term to
    :func:`response`.

    The reference is the response of a lossless line at zero frequency, which is
    ``1 + reflection`` because an open end doubles the standing voltage and a
    matched end leaves it alone. Dividing by it makes the reflection change the
    shape of the response rather than its scale, and leaves the conductor loss
    where it belongs, in the roll-off. Normalising instead by the response at
    the same attenuation would divide the loss out of the result, and a 5 mm
    electrode then reports a 3 dB bandwidth of 1.4 THz.

    A shorted far end has no response at zero frequency, so no such reference
    exists and the magnitude is returned as it stands. That case is a bandpass
    and its 3 dB point is not the quantity the other two report.

    ``reference`` selects what the result is divided by, and the choice decides
    what the number means.

    ``"dc"``, the default, divides by this line's own zero-frequency value, which
    is the convention a modulation response is quoted in and the one
    :func:`bandwidth` needs. On an open line that reference is twice the matched
    one, so the roll-off it reports is the loss of a doubling the line had at
    zero frequency and not a loss against a terminated device.

    ``"incident"`` divides by nothing and returns the modulation index a given
    incident wave produces. Two lines driven by the same source are comparable
    in that unit and are comparable in no other, so it is the unit
    :func:`far_end_penalty` works in.

    **The distinction is not academic and it inverts the conclusion.** On the
    LTOI300 5 mm electrode the self-referred response of the open line falls
    3 dB by 4.2 GHz, which reads as a collapse. Against the terminated line
    driven identically the same electrode is 5.4 dB better at zero frequency,
    1.9 dB worse at its single null near 9.8 GHz, and within half a decibel of
    it above 49 GHz. The zero-frequency figure is 6.0 dB on a lossless line and
    less here, the conductor loss taking the rest. Those figures carry the stub
    described below; the study that produces them is at
    ``examples/ltoi300_mzm/scripts/far_end_load.py``.

    ``stub_m`` is the unmodulated line between the end of the modulation section
    and the load. The optical carrier does not travel it and the microwave does,
    twice, so it rotates the returned wave without contributing modulation. It
    moves the null and leaves the zero-frequency limit alone.

    The kit ships terminated and unterminated variants of every phase shifter
    and every modulator. The polygons say the two differ by more than the load:
    on the LTOI300 modulator the unterminated cell carries its signal metal
    175 um further, which is the stub this argument represents.
    """
    w = 2 * math.pi * f_Hz
    u_f = complex(alpha_np_per_m * length_m,
                  w * (n_microwave - n_optical) / C0 * length_m)
    total = 1.0 + 0j if abs(u_f) < 1e-12 else (1.0 - cmath.exp(-u_f)) / u_f

    if reflection != 0.0:
        u_b = complex(alpha_np_per_m * length_m,
                      w * (n_microwave + n_optical) / C0 * length_m)
        back = 1.0 + 0j if abs(u_b) < 1e-12 else (cmath.exp(u_b) - 1.0) / u_b
        reach = length_m + stub_m
        g2L = complex(2.0 * alpha_np_per_m * reach,
                      2.0 * w * n_microwave / C0 * reach)
        total = total + reflection * cmath.exp(-g2L) * back

    if reference == "incident":
        return abs(total)
    if reference != "dc":
        raise ValueError("reference is 'dc' or 'incident'")
    dc = abs(1.0 + reflection)
    return abs(total) / dc if dc > 1e-9 else abs(total)


def far_end_penalty(length_m: float, alpha_at: callable, n_microwave: float,
                    n_optical: float, reflection: float,
                    f_lo_Hz: float, f_hi_Hz: float,
                    points: int = 601, stub_m: float = 0.0) -> dict[str, float]:
    """What the far-end load costs against a matched line, over a stated band.

    Both lines are driven by the same incident wave, so the comparison is made
    on the unnormalised modulation index. The result is the worst and the best
    the reflection does across the band, each with the frequency it occurs at.

    A negative worst figure is a penalty in decibels. A positive best figure is
    the advantage an open end holds where the returned wave adds, which at zero
    frequency is 6 dB and which decays as the two dephase.

    This is the quantity a driver is sized against. The 3 dB point of the
    self-referred response is not: on an open line it measures the loss of that
    zero-frequency advantage and returns a figure tens of times below the
    frequency at which the device stops working.
    """
    if reflection == 0.0:
        return {"worst_dB": 0.0, "worst_at_Hz": f_lo_Hz,
                "best_dB": 0.0, "best_at_Hz": f_lo_Hz}
    ratio = math.log(f_hi_Hz / f_lo_Hz) / max(points - 1, 1)
    worst, worst_at = float("inf"), f_lo_Hz
    best, best_at = float("-inf"), f_lo_Hz
    for k in range(points):
        f = f_lo_Hz * math.exp(ratio * k)
        a = alpha_at(f)
        m = response_loaded(f, length_m, a, n_microwave, n_optical, 0.0, "incident")
        o = response_loaded(f, length_m, a, n_microwave, n_optical,
                            reflection, "incident", stub_m)
        if m <= 0:
            continue
        d = 20 * math.log10(max(o, 1e-15) / m)
        if d < worst:
            worst, worst_at = d, f
        if d > best:
            best, best_at = d, f
    return {"worst_dB": worst, "worst_at_Hz": worst_at,
            "best_dB": best, "best_at_Hz": best_at}


def load_reflection(load_ohm: float | None, z0_ohm: float) -> float:
    """What the far end returns to the line.

    ``None`` states a termination matched to the line, whatever impedance the
    line turns out to have, which is what the terminated cells carry and what
    returns nothing. A pad with nothing behind it is an open end, which is
    stated as an impedance at or above a gigaohm and returns everything.

        G = (Z_L - Z0) / (Z_L + Z0)
    """
    if load_ohm is None:
        return 0.0
    if load_ohm >= 1e9:
        return 1.0
    if z0_ohm <= 0:
        return 0.0
    return float((load_ohm - z0_ohm) / (load_ohm + z0_ohm))


def bandwidth(length_m: float, alpha_at: callable, n_microwave: float,
              n_optical: float, level: float = 1 / math.sqrt(2),
              f_start: float = 1e8, f_stop: float = 1e13,
              step: float = 1.02, tol: float = 1e-4,
              reflection: float = 0.0) -> float:
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
    def r(f):
        return response_loaded(f, length_m, alpha_at(f), n_microwave,
                              n_optical, reflection)

    if r(lo) <= level:
        return lo
    hi = lo * step
    while hi < f_stop:
        if r(hi) <= level:
            # bracketed between lo and hi; bisect on the crossing
            while (hi - lo) / hi > tol:
                mid = 0.5 * (lo + hi)
                if r(mid) <= level:
                    hi = mid
                else:
                    lo = mid
            return hi
        lo, hi = hi, hi * step
    return float("inf")
