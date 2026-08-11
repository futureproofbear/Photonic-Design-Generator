"""Single-mode laser rate equations, in closed form.

The chain computes the *cavity* of an extended-DBR laser: the round-trip delay,
the threshold gain the gain chip must supply, and the Schawlow-Townes-Henry
linewidth. It does not compute anything that requires the carrier density to be
a dynamical variable. Output power, threshold current, relaxation oscillation,
relative intensity noise and the stability of the laser against its own optical
feedback all do.

The equations solved here are the standard single-mode pair

    dN/dt = eta_i I /(q V) - N/tau_c - v_g g(N,S) S
    dS/dt = Gamma v_g g(N,S) S - S/tau_p + Gamma beta N/tau_c

with a linear gain g = a (N - N_tr) compressed as g/(1 + eps S), together with
the phase equation that carries the linewidth enhancement factor alpha.

Two features of an *extended* cavity are carried explicitly.

The photon lifetime is that of the composite cavity and not of the gain chip.
It is taken from the round-trip delay and the round-trip power survival, so it
already contains the passive feed, the coupling losses and the DBR.

Gain acts only in the active fraction F of the round trip. Every rate that
multiplies the gain is therefore scaled by F, and the carrier equation is
referenced to the active volume alone.

Nothing here is fitted. Each expression is the textbook one, and the tests hold
it against a limit in which it can be evaluated by hand.
"""

from __future__ import annotations

import math

import numpy as np

C0 = 299792458.0
Q_E = 1.602176634e-19
H_PLANCK = 6.62607015e-34


# --------------------------------------------------------------------------
# the composite cavity
# --------------------------------------------------------------------------
def photon_lifetime_s(tau_rt_s: float, roundtrip_survival: float) -> float:
    """Photon lifetime of the composite cavity, in seconds.

    `roundtrip_survival` is the fraction of the power that remains after one
    full round trip with the gain switched off. The decay rate is the logarithm
    of that fraction spread over the round-trip delay, which makes the result
    independent of how the loss is apportioned between mirrors, coupling and
    propagation.
    """
    if not 0.0 < roundtrip_survival < 1.0:
        raise ValueError("round-trip survival must lie strictly between 0 and 1")
    if tau_rt_s <= 0:
        raise ValueError("round-trip delay must be positive")
    return tau_rt_s / (-math.log(roundtrip_survival))


def cold_cavity_Q(tau_p_s: float, nu_Hz: float) -> float:
    """Quality factor implied by the photon lifetime."""
    return 2.0 * math.pi * nu_Hz * tau_p_s


# --------------------------------------------------------------------------
# threshold
# --------------------------------------------------------------------------
def threshold_carrier_density_per_cm3(
    tau_p_s: float, v_g_cm_per_s: float, gamma_active: float,
    active_fraction: float, differential_gain_cm2: float,
    transparency_density_per_cm3: float,
) -> float:
    """Carrier density at which the modal gain equals the cavity loss.

    The threshold condition is that the round-trip gain rate balances the
    round-trip loss rate. Gain is present only in the active fraction F of the
    round trip, so the condition reads

        F * Gamma * v_g * a * (N_th - N_tr) = 1 / tau_p.
    """
    denom = active_fraction * gamma_active * v_g_cm_per_s * differential_gain_cm2
    if denom <= 0:
        raise ValueError("the modal differential gain must be positive")
    return transparency_density_per_cm3 + 1.0 / (denom * tau_p_s)


def threshold_current_A(
    n_th_per_cm3: float, active_volume_cm3: float, carrier_lifetime_s: float,
    injection_efficiency: float = 1.0,
) -> float:
    """Current at which the carrier density first reaches threshold.

    Below threshold the stimulated term is negligible, so the carrier density is
    set by injection against recombination alone.
    """
    if injection_efficiency <= 0:
        raise ValueError("injection efficiency must be positive")
    return Q_E * active_volume_cm3 * n_th_per_cm3 / (carrier_lifetime_s * injection_efficiency)


# --------------------------------------------------------------------------
# steady state above threshold
# --------------------------------------------------------------------------
def photon_density_per_cm3(
    current_A: float, threshold_current_A_: float, tau_p_s: float,
    active_volume_cm3: float, injection_efficiency: float = 1.0,
) -> float:
    """Steady-state photon density in the active region.

    Above threshold the carrier density is clamped, so every additional carrier
    injected is converted to a photon. The photon density is therefore the
    excess current divided by the charge, the volume and the photon decay rate.
    """
    if current_A <= threshold_current_A_:
        return 0.0
    return (injection_efficiency * (current_A - threshold_current_A_) * tau_p_s
            / (Q_E * active_volume_cm3))


def output_power_W(
    photon_density: float, active_volume_cm3: float, tau_p_s: float,
    nu_Hz: float, output_coupling_fraction: float,
) -> float:
    """Power emerging through the output coupler.

    The total optical energy stored is the photon density times the volume times
    the photon energy. It decays at 1/tau_p, and the stated fraction of that
    decay leaves through the output rather than being absorbed.
    """
    stored_J = photon_density * active_volume_cm3 * H_PLANCK * nu_Hz
    return stored_J / tau_p_s * output_coupling_fraction


def slope_efficiency_W_per_A(
    nu_Hz: float, output_coupling_fraction: float, injection_efficiency: float = 1.0,
) -> float:
    """Differential power per unit current above threshold.

    Every carrier above threshold makes one photon, and the stated fraction of
    those photons leaves through the output.
    """
    return injection_efficiency * output_coupling_fraction * H_PLANCK * nu_Hz / Q_E


def output_coupling_fraction(alpha_mirror_out_per_cm: float,
                             alpha_total_per_cm: float) -> float:
    """Fraction of the photon decay that leaves through the output mirror."""
    if alpha_total_per_cm <= 0:
        raise ValueError("total loss must be positive")
    return alpha_mirror_out_per_cm / alpha_total_per_cm


# --------------------------------------------------------------------------
# small-signal response
# --------------------------------------------------------------------------
def relaxation_oscillation_Hz(
    photon_density: float, tau_p_s: float, v_g_cm_per_s: float,
    gamma_active: float, active_fraction: float, differential_gain_cm2: float,
) -> float:
    """Relaxation oscillation frequency.

    The undamped exchange between the carrier and photon reservoirs, at

        omega_r^2 = F * Gamma * v_g * a * S_0 / tau_p.

    This is the frequency at which the intensity noise peaks and above which the
    laser cannot be modulated directly.
    """
    if photon_density <= 0:
        return 0.0
    w2 = (active_fraction * gamma_active * v_g_cm_per_s
          * differential_gain_cm2 * photon_density / tau_p_s)
    return math.sqrt(w2) / (2.0 * math.pi)


def damping_K_factor_s(tau_p_s: float, v_g_cm_per_s: float,
                       differential_gain_cm2: float,
                       gain_compression_cm3: float) -> float:
    """The K factor, in seconds, relating damping to the square of f_r.

        K = 4 pi^2 (tau_p + eps / (v_g a)).

    The second term is gain compression and is what bounds the modulation
    bandwidth once the photon lifetime has been made short.
    """
    return 4.0 * math.pi**2 * (tau_p_s + gain_compression_cm3
                               / (v_g_cm_per_s * differential_gain_cm2))


def damping_rate_per_s(f_r_Hz: float, K_s: float, carrier_lifetime_s: float) -> float:
    """Damping rate of the relaxation oscillation."""
    return K_s * f_r_Hz**2 + 1.0 / carrier_lifetime_s


def damping_ratio(f_r_Hz: float, gamma_per_s: float) -> float:
    """Ratio of the damping rate to the oscillation rate.

    Below unity the intensity response peaks at f_r; at or above unity the
    response is overdamped and no peak is present.
    """
    if f_r_Hz <= 0:
        return float("inf")
    return gamma_per_s / (2.0 * math.pi * f_r_Hz)


def modulation_bandwidth_Hz(f_r_Hz: float, gamma_per_s: float) -> float:
    """Small-signal 3 dB bandwidth of the intensity response.

    The two-pole transfer function reaches half power at

        f_3dB^2 = f_r^2 + sqrt(f_r^4 + (something)) ,

    which reduces to the closed form below. It is the standard result and
    approaches sqrt(1 + sqrt(2)) f_r = 1.55 f_r when damping is negligible.
    """
    if f_r_Hz <= 0:
        return 0.0
    wr = 2.0 * math.pi * f_r_Hz
    g = gamma_per_s
    a = wr**2 - g**2 / 2.0
    w3 = math.sqrt(a + math.sqrt(a**2 + wr**4))
    return w3 / (2.0 * math.pi)


# --------------------------------------------------------------------------
# relative intensity noise
# --------------------------------------------------------------------------
def rin_spectrum_per_Hz(
    f_Hz: np.ndarray, f_r_Hz: float, gamma_per_s: float,
    photon_density: float, tau_p_s: float, carrier_lifetime_s: float,
    beta_spontaneous: float, n_th_per_cm3: float,
) -> np.ndarray:
    """Relative intensity noise spectral density, per hertz.

    The spontaneous emission that seeds the field is filtered by the same two
    poles that produce the relaxation oscillation, so the noise peaks at f_r and
    falls as the fourth power of frequency above it.
    """
    if photon_density <= 0:
        return np.full_like(np.asarray(f_Hz, dtype=float), float("nan"))
    w = 2.0 * np.pi * np.asarray(f_Hz, dtype=float)
    wr = 2.0 * math.pi * f_r_Hz
    # spontaneous emission rate into the lasing mode
    r_sp = beta_spontaneous * n_th_per_cm3 / carrier_lifetime_s
    numer = 2.0 * r_sp / photon_density * (w**2 + 1.0 / carrier_lifetime_s**2)
    denom = (wr**2 - w**2) ** 2 + (gamma_per_s * w) ** 2
    return numer / denom


def rin_peak_dB_per_Hz(rin: np.ndarray) -> float:
    """Peak of a RIN spectrum, in decibels per hertz."""
    peak = float(np.nanmax(rin))
    return 10.0 * math.log10(peak) if peak > 0 else float("-inf")


# --------------------------------------------------------------------------
# optical feedback
# --------------------------------------------------------------------------
def feedback_rate_per_s(front_facet_R: float, external_R: float,
                        tau_in_s: float) -> float:
    """Coupling rate of the returned field into the gain chip, in 1/s.

    The residual reflectivity of the chip facet competes with the external
    mirror. The rate is

        kappa = (1 - R2) sqrt(R_ext / R2) / tau_in,

    which grows without bound as the anti-reflection coating is improved, this
    being the intended behaviour: a chip with no facet of its own is entirely
    governed by the external cavity.
    """
    if not 0.0 < front_facet_R < 1.0:
        raise ValueError("front facet reflectivity must lie strictly between 0 and 1")
    if tau_in_s <= 0:
        raise ValueError("internal round-trip delay must be positive")
    return (1.0 - front_facet_R) * math.sqrt(external_R / front_facet_R) / tau_in_s


def feedback_C(kappa_per_s: float, tau_ext_s: float, alpha: float) -> float:
    """The Lang-Kobayashi feedback parameter C.

        C = kappa tau_ext sqrt(1 + alpha^2).

    Below unity the compound cavity supports one solution and the laser is
    single mode whatever the feedback phase. Above unity it supports several,
    and which one the laser occupies depends on that phase.
    """
    return kappa_per_s * tau_ext_s * math.sqrt(1.0 + alpha**2)


def feedback_regime(C: float, external_R: float, front_facet_R: float) -> tuple[str, str]:
    """Classify the feedback into the five regimes, with the reason.

    The classification is that of Tkach and Chraplyvy. The ordering is not
    monotone in the feedback strength: the strongest regime is stable again,
    because the external mirror has by then displaced the chip facet entirely
    and the compound cavity is a single well-defined resonator. An external-cavity
    laser is designed to sit there, and it does so by suppressing the chip facet
    rather than by weakening the feedback.
    """
    ratio_dB = 10.0 * math.log10(external_R / front_facet_R) if front_facet_R > 0 else float("inf")
    if C < 1.0:
        return ("I", "the compound cavity supports one solution, so the feedback "
                     "narrows or broadens the line without changing the mode")
    if ratio_dB >= 20.0:
        return ("V", f"the external mirror exceeds the chip facet by {ratio_dB:.0f} dB, "
                     "so the compound cavity is governed by the external mirror alone "
                     "and is stable")
    if C < 4.6:
        return ("II", "several external-cavity solutions exist and the laser hops "
                      "between them as the feedback phase drifts")
    return ("IV", "coherence collapse: the external mirror is strong enough to "
                  "destabilise the chip yet too weak to define the cavity on its own")


def coherence_collapse_margin_dB(external_R: float, front_facet_R: float) -> float:
    """How far the external mirror stands above the chip facet, in decibels.

    This is the quantity that keeps an external-cavity laser out of coherence
    collapse. It degrades if the anti-reflection coating degrades, and it is
    therefore a reliability figure rather than only a design one.
    """
    if front_facet_R <= 0:
        return float("inf")
    return 10.0 * math.log10(external_R / front_facet_R)


def external_cavity_mode_spacing_Hz(tau_rt_s: float) -> float:
    """Spacing of the compound-cavity solutions."""
    return 1.0 / tau_rt_s
