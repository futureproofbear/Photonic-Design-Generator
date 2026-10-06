"""The parasitic reflectors folded into the cavity's round-trip phase.

Two defects were found by review on 2026-10-06. The corrections were multiplied
by the sign that maps the mirror's computed phase into the round-trip
convention, although they were already built in it, so on a mirror of negative
sign they entered conjugated. The joint reflector's external path omitted the
phase the intracavity section applies. These tests hold the algebra to an
explicit sum of reflections and the sense of the pull to the weak-feedback
result.
"""
import math

import numpy as np

from picchain.stages.s04_cavity import (_extra_at, apply_reflector_correction,
                                        joint_correction, resonance_roots)


def _series(r_e, e_f, r_f, terms=400):
    """The reflection seen from the gain section, summed bounce by bounce. The
    reflector returns e_f r_f directly; light crossing it with amplitude
    transmission t each way meets the external cavity, and each further pass
    is reflected back by the reflector with the Stokes sign, -e_f r_f."""
    t2 = 1.0 - r_f ** 2
    total = e_f * r_f
    for n in range(terms):
        total += t2 * r_e * (-e_f * r_f * r_e) ** n
    return total


def test_joint_correction_equals_the_sum_of_reflections():
    rng = np.random.default_rng(3)
    for _ in range(20):
        r_e = 0.8 * rng.uniform(0.2, 1.0) * np.exp(1j * rng.uniform(0, 2 * np.pi))
        e_f = np.exp(1j * rng.uniform(0, 2 * np.pi))
        r_f = rng.uniform(1e-3, 0.3)
        assert abs(joint_correction(r_e, e_f, r_f) * r_e - _series(r_e, e_f, r_f)) < 1e-10


def test_joint_correction_is_unity_without_a_reflector():
    r_e = 0.7 * np.exp(0.4j)
    assert abs(joint_correction(r_e, 1.0, 0.0) - 1.0) < 1e-15


def test_weak_feedback_pull_has_the_lang_kobayashi_sense():
    """A weak reflection kappa e^{i 2 pi f tau_x} on a cavity of round trip
    tau_rt pulls the mode by

        2 pi tau_rt df = -kappa sqrt(1 + alpha^2) sin(2 pi f tau_x + atan alpha),

    the steady state of the Lang-Kobayashi equations to first order in kappa.
    The mode is found from the corrected phase and compared with that."""
    tau_rt, tau_x, kappa = 87e-12, 30e-12, 2e-3
    f = np.linspace(-40e9, 40e9, 400001)
    base = 2 * np.pi * f * tau_rt
    for alpha in (0.0, 3.0):
        c = 1.0 + kappa * np.exp(1j * 2 * np.pi * f * tau_x)
        P = apply_reflector_correction(base, c, alpha)
        for k in (-2, 0, 1, 3):
            f0 = k / tau_rt
            (f_m,) = [r for r in resonance_roots(f, P, k) if abs(r - f0) < 0.25 / tau_rt]
            expect = (-kappa * math.sqrt(1 + alpha ** 2)
                      * math.sin(2 * math.pi * f0 * tau_x + math.atan(alpha)) / (2 * math.pi * tau_rt))
            assert abs((f_m - f0) - expect) < 0.02 * kappa / (2 * math.pi * tau_rt), (alpha, k)


def test_a_conjugated_correction_pulls_the_wrong_way():
    """The defect the review found, kept as a check that the test can fail."""
    tau_rt, tau_x, kappa = 87e-12, 30e-12, 2e-3
    f = np.linspace(-20e9, 20e9, 200001)
    base = 2 * np.pi * f * tau_rt
    c = 1.0 + kappa * np.exp(1j * 2 * np.pi * f * tau_x)
    P_bad = base - (np.angle(c) + 0.0 * np.log(np.abs(c)))
    f0 = 1 / tau_rt
    (f_m,) = [r for r in resonance_roots(f, P_bad, 1) if abs(r - f0) < 0.25 / tau_rt]
    expect = -kappa * math.sin(2 * math.pi * f0 * tau_x) / (2 * math.pi * tau_rt)
    assert (f_m - f0) * expect < 0


def test_intracavity_phase_is_read_at_the_mode():
    f_grid = np.linspace(0.0, 1.0, 11)
    assert _extra_at(0.3, 0.55, f_grid) == 0.3
    assert abs(_extra_at(2.0 * f_grid, 0.55, f_grid) - 1.1) < 1e-12
