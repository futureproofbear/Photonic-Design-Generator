"""Coupling across a facet: overlap, Fresnel, facet angle and alignment.

The interface between a gain chip and a photonic circuit is usually carried in a
design file as a single number in decibels. It is in fact the product of four
separate things, each of which can be computed or bounded:

* the overlap of the two mode profiles, which is geometry;
* the Fresnel reflection at the index step, which an anti-reflection coating
  reduces but does not remove;
* the penalty for an angled facet, used to keep reflections out of the cavity;
* the loss incurred by the alignment achieved in assembly.

Reporting them separately is what allows the dominant term to be identified. A
budget quoted as one number cannot be improved because it cannot be attributed.

The mode of the other chip is not solved here. It is described by its
mode-field diameters, which is what a vendor datasheet provides, and the
approximation of that mode by a Gaussian is stated rather than hidden.
"""

from __future__ import annotations

import math

import numpy as np


def gaussian_mode(x: np.ndarray, y: np.ndarray, w_x: float, w_y: float,
                  x0: float = 0.0, y0: float = 0.0) -> np.ndarray:
    """Elliptical Gaussian field, ``w`` being the 1/e radius of the field."""
    X, Y = np.meshgrid(x, y, indexing="ij")
    return np.exp(-(((X - x0) / w_x) ** 2 + ((Y - y0) / w_y) ** 2))


def power_overlap(a: np.ndarray, b: np.ndarray, dA: np.ndarray) -> float:
    """Fraction of power transferred between two field profiles.

        eta = |<a|b>|^2 / (<a|a> <b|b>)
    """
    num = float(np.sum(a * b * dA)) ** 2
    den = float(np.sum(a * a * dA)) * float(np.sum(b * b * dA))
    return num / den if den > 0 else 0.0


def gaussian_overlap_analytic(w1: float, w2: float, offset: float = 0.0) -> float:
    """Closed form for two Gaussians in one dimension, offset by ``offset``.

        eta = (2 w1 w2 / (w1^2 + w2^2)) * exp(-2 offset^2 / (w1^2 + w2^2))

    Squared for two dimensions with the same expression in each.
    """
    s = w1**2 + w2**2
    return (2 * w1 * w2 / s) * math.exp(-2 * offset**2 / s)


def fresnel_transmission(n1: float, n2: float, ar_reflectivity: float | None = None) -> float:
    """Power transmitted across a normal-incidence index step.

    Where an anti-reflection coating is declared, its reflectivity is used in
    place of the bare Fresnel value; the coating is a specification rather than
    something this function can predict.
    """
    if ar_reflectivity is not None:
        return max(0.0, 1.0 - ar_reflectivity)
    r = ((n1 - n2) / (n1 + n2)) ** 2
    return 1.0 - r


def facet_deflection_deg(angle_deg: float, n_guide: float, n_outside: float) -> float:
    """Angle by which an angled facet deflects the emerging beam.

    Snell's law conserves the transverse wavevector, so an angled facet costs
    nothing in wavevector matching. What it does is deflect: a beam leaving at
    ``theta`` inside emerges at ``asin(n_guide sin(theta) / n_outside)``, and the
    difference is the angle by which the partner must be rotated.
    """
    th = math.radians(angle_deg)
    s_out = n_guide * math.sin(th) / n_outside
    if abs(s_out) >= 1.0:
        return float("nan")             # beyond the critical angle: nothing emerges
    return math.degrees(math.asin(s_out)) - angle_deg


def angled_facet_penalty(angle_deg: float, n_guide: float, n_outside: float,
                         w_um: float, wavelength_um: float,
                         partner_tilted: bool = False) -> float:
    """Loss from an angled facet where the partner is **not** tilted to match.

    A facet is angled so that its reflection does not return into the cavity.
    The transmitted beam is then deflected, and unless the receiving chip or
    fibre is rotated by the same amount the two meet at an angle. For a Gaussian
    of radius ``w`` an angular mismatch costs

        eta = exp(-(pi w n_outside dtheta / lambda)^2)

    Where the partner is tilted to match, which is the usual arrangement, the
    penalty is unity and the angle costs nothing but assembly tolerance.
    """
    if angle_deg == 0 or partner_tilted:
        return 1.0
    d = facet_deflection_deg(angle_deg, n_guide, n_outside)
    if d != d:                          # not a number: total internal reflection
        return 0.0
    dth = math.radians(d)
    return math.exp(-((math.pi * w_um * n_outside * dth / wavelength_um) ** 2))


def alignment_tolerance(w1: float, w2: float, loss_dB: float = 1.0) -> float:
    """Offset at which the overlap falls by ``loss_dB``, in the same units as w.

    From the closed form above, the offset that costs a factor f is

        offset = sqrt(-(w1^2 + w2^2) ln(f) / 2)
    """
    f = 10 ** (-loss_dB / 10)
    return math.sqrt(-(w1**2 + w2**2) * math.log(f) / 2)


def refracted_angle_deg(angle_deg: float, n_guide: float, n_outside: float) -> float:
    """Angle in the outer medium, by Snell's law.

    Returns NaN beyond the critical angle, where nothing emerges.
    """
    s = n_guide * math.sin(math.radians(angle_deg)) / n_outside
    if abs(s) >= 1.0:
        return float("nan")
    return math.degrees(math.asin(s))


def gap_walkoff(angle_deg: float, n_guide: float, n_gap: float, gap_um: float) -> float:
    """Lateral displacement of the beam across a coupling gap, in um.

    The transverse wavevector is conserved through every interface, so the angle
    *inside* the partner does not depend on what lies between the two facets.
    The position does. Across a gap of index ``n_gap`` the beam travels at the
    angle that medium imposes, which is steeper than the angle it will have in a
    higher-index partner, and it lands displaced by

        d = gap * tan(theta_gap)

    For a butt-coupled pair with an air gap this is a substantial fraction of
    the alignment tolerance, and it is a displacement to be designed in rather
    than a loss to be accepted.
    """
    if gap_um <= 0 or angle_deg == 0:
        return 0.0
    th = refracted_angle_deg(angle_deg, n_guide, n_gap)
    if th != th:                                    # NaN: totally internally reflected
        return float("nan")
    return float(gap_um * math.tan(math.radians(th)))


def lateral_offset_penalty(offset_um: float, w1_um: float, w2_um: float) -> float:
    """Power coupling between two Gaussians displaced laterally.

    eta = exp(-2 d^2 / (w1^2 + w2^2)) for radii at 1/e^2 of intensity.
    """
    if offset_um == 0:
        return 1.0
    return float(math.exp(-2.0 * offset_um**2 / (w1_um**2 + w2_um**2)))
