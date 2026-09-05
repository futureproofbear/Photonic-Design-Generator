"""The eigenmode expansion of a multimode splitter, held against closed forms.

Two properties are checked without reference to any device. A uniform guide
carrying no junction and no width change must transmit unity and reflect
nothing, whatever length is declared, because the phase of a uniform section is
exact in this method. And the transmission of a structure may not exceed what
was launched into it.

The third check is the one this instrument was built for. The self-imaging
length of a multimode section is fixed by the spacing of its modal propagation
constants and by nothing else, so it scales as the square of the section width
at fixed index and wavelength. A method that reproduces that scaling is
propagating the modes it claims to.
"""

from __future__ import annotations

import numpy as np
import pytest

from picchain import mmi_eme

N_CORE, N_BG = 1.845898, 1.586427
LAM = 1.31

BASE = dict(taper_length_um=25.0, lead_um=3.0, window_points=2001,
            taper_slices=8, num_modes=16, guided_only=False,
            n_core=N_CORE, n_background=N_BG, wavelength_um=LAM)


@pytest.mark.parametrize("length", [5.0, 40.0, 200.0])
def test_a_uniform_guide_transmits_unity_at_any_length(length):
    """The exact statement this method makes about a uniform section.

    A time-domain solve of the same guide accumulates phase error with length
    and loses a little more at each. Here the length enters as one exponential,
    so two hundred micrometres costs what five does.
    """
    job = dict(BASE, width_um=0.7, port_width_um=0.7, mmi_width_um=0.7,
               mmi_length_um=length, port_separation_um=0.0, ports_in=1,
               taper_length_um=0.0, taper_slices=1, window_um=16.0, num_modes=6)
    r = mmi_eme.solve(job)
    assert r["port_transmission"][0] == pytest.approx(1.0, abs=2e-3)
    assert r["reflection"] < 1e-9


def test_nothing_transmits_more_than_was_launched():
    job = dict(BASE, width_um=0.7, port_width_um=1.7, mmi_width_um=4.5,
               mmi_length_um=15.8, port_separation_um=2.45, ports_in=1,
               window_um=14.0)
    r = mmi_eme.solve(job)
    assert r["transmission"] <= 1.0 + 1e-2
    assert r["accounted"] <= 1.0 + 1e-2


def test_the_imaging_length_scales_as_the_square_of_the_width():
    """The relation that fixes an MMI, measured off the method rather than assumed.

    The beat length between the two lowest modes of a slab of width W is
    proportional to W^2, so the length maximising transmission scales the same
    way. Two widths are swept and the ratio of their optima is compared with the
    ratio of the squares.
    """
    def best_length(width, lengths):
        best = (0.0, None)
        for L in lengths:
            job = dict(BASE, width_um=0.7, port_width_um=1.7, mmi_width_um=width,
                       mmi_length_um=float(L), port_separation_um=2.45, ports_in=1,
                       window_um=3.0 * width + 6.0, taper_slices=6, num_modes=12)
            T = mmi_eme.solve(job)["transmission"]
            if T > best[0]:
                best = (T, float(L))
        return best[1]

    l_small = best_length(3.5, np.arange(8.0, 14.1, 0.5))
    l_large = best_length(4.5, np.arange(13.0, 21.1, 0.5))
    assert l_small is not None and l_large is not None
    ratio = l_large / l_small
    expected = (4.5 / 3.5) ** 2
    assert ratio == pytest.approx(expected, rel=0.12), (
        f"optima {l_small} and {l_large} give {ratio:.3f} against {expected:.3f}")


def test_a_lateral_profile_is_the_geometry_it_was_asked_for():
    x = np.linspace(-6, 6, 1201)
    n = mmi_eme.lateral_profile(x, [-1.5, 1.5], 0.9, N_CORE, N_BG)
    inside = np.abs(np.abs(x) - 1.5) <= 0.45 - 1e-9
    assert np.allclose(n[inside], N_CORE)
    assert np.allclose(n[np.abs(x) > 2.5], N_BG)
    # the two guides occupy their own widths and no more
    assert float(np.sum(np.gradient(x)[n == N_CORE])) == pytest.approx(1.8, abs=0.02)
