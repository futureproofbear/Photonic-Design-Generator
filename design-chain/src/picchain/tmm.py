"""Coupled-mode theory and transfer-matrix engine for Bragg gratings.

Two layers:

1. ``fourier_kappa`` - turn a *physical* longitudinal index profile (duty cycle,
   index contrast, grating order) into the coupling constant kappa_m of the
   m-th Fourier harmonic.  This is the step arXiv:2408.01743 describes as
   "spatial Fourier analysis to isolate the m=3 coefficient".

2. ``grating_response`` - piecewise TMM over the grating, supporting
   apodisation, chirp, loss and a lumped phase section, returning the complex
   field reflectivity r(f) from which reflectivity, bandwidth, group delay and
   the penetration depth that sets the laser cavity all follow.

Sign/normalisation convention
-----------------------------
n(z) = n_bar + dn * s(z),  s(z) in {0, 1} with duty cycle d
     = n_bar + d*dn + sum_m a_m cos(2 pi m z / Lambda)
     a_m = 2 dn sin(pi m d) / (pi m)
kappa_m = pi a_m / lambda_B      (standard index-grating CMT)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

C0 = 299792458.0  # m/s


# --------------------------------------------------------------------------
# CMT coupling from geometry
# --------------------------------------------------------------------------
def profile_smoothing(order: int, period_um: float, sigma_um: float) -> float:
    """Factor by which a longitudinal smoothing suppresses the m-th harmonic.

    The rectangular profile assumed below is an idealisation. Two things round
    it. The lithography rounds the corners of a post, and the guided mode
    cannot resolve a step over a distance short compared with its own transverse
    extent, so it responds to a longitudinally averaged perturbation. Both are
    modelled here as a convolution with a Gaussian of RMS length `sigma_um`,
    which multiplies the m-th Fourier coefficient by

        exp(-(2*pi*m*sigma/Lambda)^2 / 2).

    The suppression is quadratic in the order, so the assumption that is benign
    at m = 1 is not benign at m = 3. On the TFLN validation baseline a sigma of
    84 nm, which is a FWHM of 198 nm against a post 300 nm long, costs the first
    harmonic 8 % and the third harmonic 54 %.

    The default is zero, which is the identity, so nothing changes where no
    smoothing is declared. The parameter exists so that the assumption is stated
    rather than hidden, and so that a band-structure or time-domain measurement
    of kappa can be expressed as a length rather than as a correction factor.
    """
    if sigma_um <= 0:
        return 1.0
    if period_um <= 0:
        raise ValueError("period must be positive")
    return math.exp(-0.5 * (2.0 * math.pi * order * sigma_um / period_um) ** 2)


def fourier_amplitude(dn: float, duty: float, order: int,
                      period_um: float = 0.0, sigma_um: float = 0.0) -> float:
    """Amplitude a_m of the m-th cosine harmonic of the longitudinal profile.

    The profile is rectangular unless `sigma_um` declares a smoothing length,
    in which case the coefficient carries the factor from `profile_smoothing`.
    """
    if order < 1:
        raise ValueError("grating order must be >= 1")
    rect = 2.0 * dn * math.sin(math.pi * order * duty) / (math.pi * order)
    if sigma_um <= 0:
        return rect
    return rect * profile_smoothing(order, period_um, sigma_um)


def mean_index(n_base: float, dn: float, duty: float) -> float:
    """Period-averaged effective index (this is what sets the Bragg wavelength)."""
    return n_base + dn * duty


def bragg_wavelength_um(n_bar: float, period_um: float, order: int) -> float:
    return 2.0 * n_bar * period_um / order


def period_for_bragg_um(n_bar: float, lambda_um: float, order: int) -> float:
    return order * lambda_um / (2.0 * n_bar)


def fourier_kappa(dn: float, duty: float, order: int, lambda_B_um: float,
                  period_um: float = 0.0, sigma_um: float = 0.0) -> float:
    """Coupling constant kappa in 1/um."""
    return math.pi * fourier_amplitude(dn, duty, order, period_um, sigma_um) / lambda_B_um


# --------------------------------------------------------------------------
# uniform-grating closed form (fast path + analytic cross-check)
# --------------------------------------------------------------------------
def uniform_reflectivity(kappa: float, L: float, delta: np.ndarray, alpha: float = 0.0) -> np.ndarray:
    """Complex field reflectivity of a uniform grating.

    kappa, delta, alpha in 1/um; L in um.  delta is the detuning from the Bragg
    condition, delta = 2 pi n_g (f - f_B) / c.

    ``alpha`` is a **loss**, so it enters the complex detuning with a negative
    imaginary part.  The opposite sign describes a medium with gain, under which
    the reflectivity rises above unity, and the error is invisible at moderate
    coupling: at kappa*L = 2.1 it displaces R by under 0.1 %, and only past
    kappa*L = 3 does it break the physical bound.
    """
    d = delta - 1j * alpha
    s = np.sqrt(kappa**2 - d**2 + 0j)
    sl = s * L
    num = -kappa * np.sinh(sl)
    den = s * np.cosh(sl) + 1j * d * np.sinh(sl)
    return num / den


def peak_reflectivity(kappa: float, L: float) -> float:
    return float(np.tanh(kappa * L) ** 2)


def transform_limit_fwhm_Hz(L_um: float, n_g: float) -> float:
    """Narrowest reflection FWHM a *uniform* grating of length L can have.

    As kappa -> 0 the response tends to a sinc^2 whose FWHM is
    0.886 c / (2 n_g L); any stronger coupling only broadens it.  A quoted
    bandwidth below this floor is not achievable at the quoted length, so this
    is a cheap consistency guard on both designs and published numbers.
    """
    return 0.886 * C0 / (2 * n_g * L_um * 1e-6)


def penetration_depth(kappa: float, L: float) -> float:
    """Effective mirror penetration depth L_pen = tanh(kappa L)/(2 kappa), in um.

    The round-trip group delay contributed by the grating is 2 n_g L_pen / c.
    For the hybrid E-DBR laser this is the single most important number after
    the reflectivity: it sets the cavity FSR, the fraction of the round-trip
    phase that the Pockels electrodes actually control, and hence the
    mode-hop-free tuning range.
    """
    if kappa <= 0:
        return 0.0
    return float(np.tanh(kappa * L) / (2 * kappa))


# --------------------------------------------------------------------------
# general piecewise TMM (apodisation / chirp / phase sections)
# --------------------------------------------------------------------------
@dataclass
class GratingSection:
    length_um: float
    kappa_per_um: float
    #: local detuning offset (1/um), e.g. from a chirped period or a local dn_bar
    delta_offset: float = 0.0
    alpha_per_um: float = 0.0


def _section_matrix(sec: GratingSection, delta: complex) -> np.ndarray:
    d = delta + sec.delta_offset - 1j * sec.alpha_per_um   # alpha is a loss
    k = sec.kappa_per_um
    s = np.sqrt(k**2 - d**2 + 0j)
    L = sec.length_um
    sl = s * L
    ch, sh = np.cosh(sl), np.sinh(sl)
    if abs(s) < 1e-30:
        ch, sh = 1.0 + 0j, L + 0j
        s = 1.0 + 0j
    # F-matrix in the (forward, backward) amplitude basis.
    #
    # The sign of the diagonal detuning term fixes which of two conjugate
    # conventions this matrix follows, and it must be the one
    # ``uniform_reflectivity`` follows or the two disagree about which sign of
    # Im(d) is a loss. For a **real** detuning the two conventions give the same
    # reflected magnitude, so a test comparing |r|^2 at real detuning passes
    # under either and cannot detect the difference. The disagreement appears
    # only once the detuning is complex, which is to say only once a loss is
    # present, and it appears there as gain.
    return np.array(
        [
            [ch - 1j * d / s * sh, 1j * k / s * sh],
            [-1j * k / s * sh, ch + 1j * d / s * sh],
        ],
        dtype=complex,
    )


def tmm_reflectivity(sections: list[GratingSection], delta: np.ndarray) -> np.ndarray:
    """Complex field reflectivity of a cascade of sections."""
    out = np.empty(len(delta), dtype=complex)
    for n, dl in enumerate(delta):
        M = np.eye(2, dtype=complex)
        for sec in sections:
            M = _section_matrix(sec, dl) @ M
        out[n] = -M[1, 0] / M[1, 1]
    return out


def apodised_sections(
    L_um: float,
    kappa_peak: float,
    n_sections: int = 201,
    profile: str = "uniform",
    alpha_per_um: float = 0.0,
    apod_fraction: float = 1.0,
) -> list[GratingSection]:
    """Build a section list for a given apodisation profile.

    ``profile`` in {uniform, gaussian, raised_cosine, tanh}.  ``apod_fraction``
    is the fraction of the grating length over which the taper is applied
    (1.0 = taper over the whole grating).
    """
    z = (np.arange(n_sections) + 0.5) / n_sections  # 0..1
    if profile == "uniform":
        w = np.ones_like(z)
    elif profile == "gaussian":
        w = np.exp(-4.0 * np.log(2) * ((z - 0.5) / (0.5 * apod_fraction)) ** 2)
    elif profile == "raised_cosine":
        w = 0.5 * (1 - np.cos(2 * np.pi * np.clip(z, 0, 1)))
    elif profile == "tanh":
        e = apod_fraction / 2
        w = np.tanh(np.clip(z, 0, 1) / max(e, 1e-6)) * np.tanh((1 - np.clip(z, 0, 1)) / max(e, 1e-6))
        w /= w.max()
    else:
        raise ValueError(f"unknown apodisation profile {profile!r}")
    dz = L_um / n_sections
    return [GratingSection(dz, kappa_peak * float(wi), 0.0, alpha_per_um) for wi in w]


# --------------------------------------------------------------------------
# spectrum analysis
# --------------------------------------------------------------------------
@dataclass
class GratingSpectrum:
    freq_Hz: np.ndarray
    r: np.ndarray  # complex field reflectivity
    f_B_Hz: float
    n_g: float

    @property
    def R(self) -> np.ndarray:
        return np.abs(self.r) ** 2

    @property
    def peak_R(self) -> float:
        return float(self.R.max())

    @property
    def peak_freq_Hz(self) -> float:
        return float(self.freq_Hz[int(np.argmax(self.R))])

    def fwhm_Hz(self) -> float:
        R = self.R
        half = R.max() / 2
        i0 = int(np.argmax(R))
        lo = hi = None
        for i in range(i0, 0, -1):
            if R[i] < half:
                lo = np.interp(half, [R[i], R[i + 1]], [self.freq_Hz[i], self.freq_Hz[i + 1]])
                break
        for i in range(i0, len(R) - 1):
            if R[i] < half:
                hi = np.interp(half, [R[i], R[i - 1]], [self.freq_Hz[i], self.freq_Hz[i - 1]])
                break
        if lo is None or hi is None:
            return float("nan")
        return float(abs(hi - lo))

    def sidelobe_suppression_dB(self) -> float:
        """Peak-to-highest-sidelobe ratio, in dB."""
        R = self.R
        i0 = int(np.argmax(R))
        # walk out of the main lobe to the first minima either side
        i = i0
        while i > 0 and R[i - 1] < R[i]:
            i -= 1
        left = R[:i].max() if i > 0 else 0.0
        j = i0
        while j < len(R) - 1 and R[j + 1] < R[j]:
            j += 1
        right = R[j:].max() if j < len(R) else 0.0
        side = max(left, right)
        if side <= 0:
            return float("inf")
        return float(10 * np.log10(R.max() / side))

    def group_delay_s(self) -> np.ndarray:
        """tau_g = -d(arg r)/d(omega)."""
        phase = np.unwrap(np.angle(self.r))
        omega = 2 * np.pi * self.freq_Hz
        return -np.gradient(phase, omega)

    def group_delay_at_peak_s(self) -> float:
        return float(self.group_delay_s()[int(np.argmax(self.R))])


def delta_from_frequency(freq_Hz: np.ndarray, f_B_Hz: float, n_g: float) -> np.ndarray:
    """Detuning in 1/um from optical-frequency offset (group-index linearisation)."""
    return 2 * np.pi * n_g * (freq_Hz - f_B_Hz) / (C0 * 1e6)


def compute_spectrum(
    *,
    kappa_per_um: float,
    L_um: float,
    n_bar: float,
    n_g: float,
    period_um: float,
    order: int,
    span_GHz: float = 120.0,
    points: int = 4001,
    alpha_dB_per_cm: float = 0.0,
    apodisation: str = "uniform",
    apod_fraction: float = 1.0,
    n_sections: int = 201,
) -> GratingSpectrum:
    lam_B = bragg_wavelength_um(n_bar, period_um, order)
    f_B = C0 / (lam_B * 1e-6)
    f = f_B + np.linspace(-span_GHz / 2, span_GHz / 2, points) * 1e9
    delta = delta_from_frequency(f, f_B, n_g)
    # dB/cm -> field amplitude 1/um
    alpha = alpha_dB_per_cm / (8.686 * 1e4) if alpha_dB_per_cm else 0.0

    if apodisation == "uniform":
        r = uniform_reflectivity(kappa_per_um, L_um, delta, alpha)
    else:
        secs = apodised_sections(L_um, kappa_per_um, n_sections, apodisation, alpha, apod_fraction)
        r = tmm_reflectivity(secs, delta)
    return GratingSpectrum(freq_Hz=f, r=r, f_B_Hz=f_B, n_g=n_g)
