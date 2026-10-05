"""Closed forms of a travelling-wave resonator coupled to one bus.

The arrangement is the all-pass microring: a loop of round-trip length ``L``
carrying an amplitude transmission ``a`` per turn, coupled to a straight bus by
one lossless point coupler that leaves an amplitude ``t`` in the bus. Summing
the circulating field over every round trip gives

    T(phi) = (a^2 - 2 a t cos phi + t^2) / (1 - 2 a t cos phi + a^2 t^2)

and every quantity below is an evaluation or an inversion of that expression.
The reference is Bogaerts et al., Laser and Photonics Reviews 6, 47 (2012).

Two conventions are fixed here because both are routinely left implicit.

**``a`` is an amplitude and the declared loss is a power.** A propagation loss of
``A`` decibels per centimetre over a length ``L`` leaves ``10^(-A L_cm / 20)`` of
the amplitude. Reading the same number as an amplitude decay halves the round
trip and doubles the quality factor.

**The width of a resonance is measured between the half-depth points and not
between the half-power points.** A notch does not reach zero unless the device
is critically coupled, so the level at which the width is taken is the mean of
the on-resonance and the off-resonance transmission. The two definitions
coincide only at critical coupling.

The width is obtained by inverting the expression above rather than by the
small-angle form quoted with it. The inversion is linear in ``cos phi`` and
reduces to

    cos(phi_half) = 2 a t / (1 + (a t)^2)

so the width of a resonance is set by the product ``a t`` alone. The small-angle
form

    FWHM ~ (1 - a t) lambda^2 / (pi n_g L sqrt(a t))

is supplied separately as ``fwhm_nm_small_angle`` so that the two can be
compared. They diverge as the finesse falls, which is the regime a lossy
platform or a strong coupler places a device in, and the divergence is reported
rather than assumed away.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

#: decibels of POWER per neper of power, 10 / ln(10).
#:
#: The amplitude conversion is twice this, and taking one for the other moves
#: every quality factor by a factor of two. The closed-form test that
#: accompanies this module found exactly that: the intrinsic quality factor was
#: computed with 20 / ln(10) and disagreed by two with the loaded quality factor
#: of the same ring at a vanishing coupling, which is the limit the two must
#: meet in.
DB_PER_NEPER_POWER = 4.3429448190325175

#: how far apart the exact and small-angle widths may sit before the stage says so
WIDTH_FORM_TOLERANCE = 0.01


def amplitude_per_round_trip(loss_dB_per_cm: float, length_um: float,
                             excess_loss_dB: float = 0.0) -> float:
    """Amplitude ``a`` surviving one round trip.

    ``loss_dB_per_cm`` is a power attenuation distributed along the loop.
    ``excess_loss_dB`` is a power loss taken once per turn, for whatever the
    distributed figure does not carry: a bend, a coupler, a junction.
    """
    if loss_dB_per_cm < 0.0:
        raise ValueError("propagation loss is negative")
    if length_um <= 0.0:
        raise ValueError("round-trip length is not positive")
    if excess_loss_dB < 0.0:
        raise ValueError("excess loss is negative")
    power_dB = loss_dB_per_cm * (length_um * 1.0e-4) + excess_loss_dB
    return float(10.0 ** (-power_dB / 20.0))


def alpha_power_per_um(loss_dB_per_cm: float) -> float:
    """Power attenuation coefficient in inverse micrometres."""
    return float(loss_dB_per_cm / DB_PER_NEPER_POWER * 1.0e-4)


def transmission(a: float, t: float, phi: float) -> float:
    """All-pass power transmission at round-trip phase ``phi``."""
    c = math.cos(phi)
    num = a * a - 2.0 * a * t * c + t * t
    den = 1.0 - 2.0 * a * t * c + (a * t) ** 2
    return float(num / den)


def transmission_on_resonance(a: float, t: float) -> float:
    """``T`` at ``cos phi = 1``. Zero when ``t == a``."""
    den = 1.0 - a * t
    if den <= 0.0:
        raise ValueError("a t reaches unity: the loop is lossless and fully coupled")
    return float(((a - t) / den) ** 2)


def transmission_off_resonance(a: float, t: float) -> float:
    """``T`` at ``cos phi = -1``, which is the baseline a notch is measured from."""
    return float(((a + t) / (1.0 + a * t)) ** 2)


def coupling_regime(a: float, t: float,
                    tol: float = 1.0e-6) -> Literal["critical", "under", "over"]:
    """Which side of critical coupling the device sits on.

    ``t > a`` leaves more amplitude in the bus than survives the loop, so the
    loop is underfilled and the device is undercoupled.
    """
    if abs(t - a) <= tol:
        return "critical"
    return "under" if t > a else "over"


def t_giving_extinction(a: float, t_min: float) -> tuple[float, float]:
    """The two couplings that produce one on-resonance transmission.

    The transfer function is symmetric under exchange of ``a`` and ``t``, so an
    extinction measured on one spectrum admits an overcoupled and an
    undercoupled solution. Both are returned, overcoupled first. This is the
    degeneracy a single measurement does not resolve.
    """
    if not 0.0 <= t_min < 1.0:
        raise ValueError("on-resonance transmission lies outside [0, 1)")
    r = math.sqrt(t_min)
    over = (a - r) / (1.0 - r * a)
    under = (a + r) / (1.0 + r * a)
    return float(over), float(under)


def fsr_um(wavelength_um: float, n_group: float, length_um: float) -> float:
    """Spacing between orders, in micrometres of wavelength."""
    if n_group <= 0.0:
        raise ValueError("group index is not positive")
    return float(wavelength_um ** 2 / (n_group * length_um))


def half_width_phase(a: float, t: float) -> float:
    """Half of the resonance width, in round-trip phase, by exact inversion.

    The level is the mean of the on-resonance and off-resonance transmission.
    Solving ``T(phi) = h`` for ``cos phi`` is linear in ``cos phi``, so the
    inversion is exact and no expansion about the resonance is made.
    """
    if not 0.0 < a <= 1.0 or not 0.0 < t <= 1.0:
        raise ValueError("a and t lie in (0, 1]")
    if a * t >= 1.0:
        raise ValueError("a t reaches unity: the resonance has no width")
    at = a * t
    # Carrying the inversion through symbolically collapses it. Writing
    # p = a^2 + t^2, q = 1 + (a t)^2 and u = 2 a t, the half-depth level is
    # h = (p q - u^2) / (q^2 - u^2), and substituting it into the inversion
    # cancels p entirely:
    #
    #     cos phi_half = u / q = 2 a t / (1 + (a t)^2)
    #
    # so the width depends on the product a t and on nothing else. Evaluating
    # the unreduced expression instead subtracts two nearly equal transmissions
    # wherever the notch is shallow, and double precision then loses the
    # difference: at a power coupling of 1e-12 the unreduced form returned a
    # loaded quality factor 3.6 per cent from the intrinsic one, in the limit
    # where the two must coincide.
    cos_phi = 2.0 * at / (1.0 + at * at)
    # the expression cannot exceed unity for real a t, so the clamp guards the
    # last bit of floating point rather than an argument
    cos_phi = max(-1.0, min(1.0, cos_phi))
    return float(math.acos(cos_phi))


def fwhm_um(wavelength_um: float, n_group: float, length_um: float,
            a: float, t: float) -> float:
    """Resonance width in micrometres of wavelength, from the exact inversion.

    The phase runs at ``d phi / d lambda = -2 pi n_g L / lambda^2``, the group
    index being what converts a phase width into a wavelength width in the
    presence of dispersion.
    """
    d_phi = 2.0 * half_width_phase(a, t)
    return float(d_phi * wavelength_um ** 2 / (2.0 * math.pi * n_group * length_um))


def fwhm_um_small_angle(wavelength_um: float, n_group: float, length_um: float,
                        a: float, t: float) -> float:
    """The width by the form usually printed beside the transfer function.

    Retained for comparison against ``fwhm_um``. It expands the transfer
    function about the resonance and is accurate where the finesse is high.
    """
    at = a * t
    if at >= 1.0:
        raise ValueError("a t reaches unity: the resonance has no width")
    return float((1.0 - at) * wavelength_um ** 2
                 / (math.pi * n_group * length_um * math.sqrt(at)))


def q_intrinsic(wavelength_um: float, n_group: float, loss_dB_per_cm: float) -> float:
    """Quality factor the loop would have with the coupler removed."""
    alpha = alpha_power_per_um(loss_dB_per_cm)
    if alpha <= 0.0:
        return float("inf")
    return float(2.0 * math.pi * n_group / (wavelength_um * alpha))


@dataclass(frozen=True)
class RingPoint:
    """Every quantity of one all-pass ring at one operating point."""
    wavelength_um: float
    n_group: float
    length_um: float
    loss_dB_per_cm: float
    excess_loss_dB: float
    a: float
    t: float
    kappa_squared: float
    fsr_um: float
    fwhm_um: float
    fwhm_um_small_angle: float
    q_loaded: float
    q_intrinsic: float
    finesse: float
    transmission_min: float
    transmission_max: float
    extinction_dB: float
    regime: str
    t_critical: float
    t_degenerate: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "wavelength_um": self.wavelength_um,
            "n_group": self.n_group,
            "round_trip_um": self.length_um,
            "loss_dB_per_cm": self.loss_dB_per_cm,
            "excess_loss_dB_per_turn": self.excess_loss_dB,
            "round_trip_amplitude": self.a,
            "bus_amplitude_t": self.t,
            "kappa_squared": self.kappa_squared,
            "fsr_nm": self.fsr_um * 1.0e3,
            "fsr_GHz": 299792.458 / (self.wavelength_um ** 2) * self.fsr_um,
            "fwhm_pm": self.fwhm_um * 1.0e6,
            "fwhm_pm_small_angle": self.fwhm_um_small_angle * 1.0e6,
            "q_loaded": self.q_loaded,
            "q_intrinsic": self.q_intrinsic,
            "finesse": self.finesse,
            "transmission_min": self.transmission_min,
            "transmission_max": self.transmission_max,
            "extinction_dB": self.extinction_dB,
            "coupling_regime": self.regime,
            "t_for_critical_coupling": self.t_critical,
            "t_giving_the_same_extinction": self.t_degenerate,
        }


def solve_point(wavelength_um: float, n_group: float, length_um: float,
                loss_dB_per_cm: float, kappa_squared: float,
                excess_loss_dB: float = 0.0) -> RingPoint:
    """Assemble one operating point from the loop loss and the coupler."""
    if not 0.0 < kappa_squared < 1.0:
        raise ValueError("the power coupling lies in (0, 1)")
    a = amplitude_per_round_trip(loss_dB_per_cm, length_um, excess_loss_dB)
    t = math.sqrt(1.0 - kappa_squared)
    t_min = transmission_on_resonance(a, t)
    t_max = transmission_off_resonance(a, t)
    fsr = fsr_um(wavelength_um, n_group, length_um)
    width = fwhm_um(wavelength_um, n_group, length_um, a, t)
    # An extinction of exactly zero is the critically coupled case and is
    # reported as the decibel figure it implies rather than as an overflow.
    ext = float("inf") if t_min <= 0.0 else -10.0 * math.log10(t_min)
    over, under = t_giving_extinction(a, t_min)
    other = under if coupling_regime(a, t) == "over" else over
    return RingPoint(
        wavelength_um=wavelength_um,
        n_group=n_group,
        length_um=length_um,
        loss_dB_per_cm=loss_dB_per_cm,
        excess_loss_dB=excess_loss_dB,
        a=a,
        t=t,
        kappa_squared=kappa_squared,
        fsr_um=fsr,
        fwhm_um=width,
        fwhm_um_small_angle=fwhm_um_small_angle(
            wavelength_um, n_group, length_um, a, t),
        q_loaded=wavelength_um / width,
        q_intrinsic=q_intrinsic(wavelength_um, n_group, loss_dB_per_cm),
        finesse=fsr / width,
        transmission_min=t_min,
        transmission_max=t_max,
        extinction_dB=ext,
        regime=coupling_regime(a, t),
        t_critical=a,
        t_degenerate=other,
    )


def kappa_squared_for_critical_coupling(loss_dB_per_cm: float, length_um: float,
                                        excess_loss_dB: float = 0.0) -> float:
    """The power coupling that extinguishes the resonance at a stated loss.

    Critical coupling requires ``t = a``, so the coupling follows from the loss
    alone. A gap is not returned: converting a coupling into a gap requires the
    time-domain solve of the drawn coupler.
    """
    a = amplitude_per_round_trip(loss_dB_per_cm, length_um, excess_loss_dB)
    return float(1.0 - a * a)


def loss_dB_per_cm_for_critical_coupling(kappa_squared: float, length_um: float,
                                         excess_loss_dB: float = 0.0) -> float | None:
    """The propagation loss at which a drawn coupler is critically coupled.

    This is the inverse a design actually needs. The coupler is drawn once and
    the loss of the process is the quantity that is unknown, so the useful
    statement is the loss at which the drawn gap extinguishes rather than the
    gap that would extinguish at an assumed loss.

    ``None`` is returned where the loss taken once per turn already exceeds what
    the coupler removes, the loop then being overcoupled at every propagation
    loss including zero.
    """
    if not 0.0 < kappa_squared < 1.0:
        raise ValueError("the power coupling lies in (0, 1)")
    t = math.sqrt(1.0 - kappa_squared)
    total_dB = -20.0 * math.log10(t)
    remaining = total_dB - excess_loss_dB
    if remaining <= 0.0:
        return None
    return float(remaining / (length_um * 1.0e-4))


def loss_window_for_extinction(extinction_dB: float, kappa_squared: float,
                               length_um: float,
                               excess_loss_dB: float = 0.0) -> tuple[float | None, float | None]:
    """The propagation losses between which a drawn coupler meets an extinction.

    **An extinction requirement is a tolerance on the loss.** A coupler is drawn
    once and is critically coupled at one loss, so a requirement that the notch
    reach a stated depth admits a band of losses about that one and refuses
    everything outside it. The band is returned in decibels per centimetre, the
    lossiest ring first being the undercoupled edge.

    The width of the band is a property of the extinction alone. Writing
    `r = 10^(-E/20)`, the round-trip loss may lie between `(1-r)/(1+r)` and
    `(1+r)/(1-r)` times the critical loss, so a 10 dB requirement admits a factor
    of 3.71 in the loss and a 20 dB requirement admits 1.49. That ratio does not
    depend on the platform, the radius or the coupling, and on a stack whose loss
    is not measured it is what decides whether the requirement can be met at all.

    ``None`` is returned for an edge the geometry cannot reach: the low edge
    where the loss taken once per turn already exceeds it, and the high edge
    never, a lossier ring always being reachable.
    """
    if not 0.0 < kappa_squared < 1.0:
        raise ValueError("the power coupling lies in (0, 1)")
    if extinction_dB <= 0.0:
        raise ValueError("an extinction requirement is positive in decibels")
    t = math.sqrt(1.0 - kappa_squared)
    r = 10.0 ** (-extinction_dB / 20.0)
    # the two round-trip amplitudes giving this extinction, by the same symmetry
    # that gives the two couplings: the transfer function exchanges a and t
    a_lossy = (t - r) / (1.0 - r * t)
    a_clear = (t + r) / (1.0 + r * t)
    cm = length_um * 1.0e-4

    def to_loss(a: float) -> float | None:
        if a <= 0.0:
            return None
        power_dB = -20.0 * math.log10(a) - excess_loss_dB
        return power_dB / cm if power_dB > 0.0 else None

    return to_loss(a_clear), to_loss(a_lossy)
