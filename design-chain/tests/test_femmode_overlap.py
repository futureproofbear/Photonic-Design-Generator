"""The finite-element overlap reduces to the confinement on a uniform field.

`Gamma = (G/V) * Int_active(E_rf |E_t|^2) / Int_all(|E_t|^2)`, so a uniform
field of one volt per micrometre reduces it to `(G/V) * confinement`. That is
the one value of the integral obtainable without a second solver, and it checks
the assembly, the subdomain selection and the normalisation together.
"""

from pathlib import Path

from picchain.solvers import femmode

SOURCE = Path(femmode.__file__).read_text(encoding="utf-8")


def test_the_overlap_is_assembled_on_the_native_triangulation():
    assert "def eo_overlap(" in SOURCE
    # assembled over the active subdomain against the whole basis
    assert "sub = basis.with_elements(elements)" in SOURCE
    assert "weighted.assemble(sub" in SOURCE
    assert "energy.assemble(basis" in SOURCE


def test_the_radio_frequency_field_is_evaluated_at_the_quadrature_points():
    """The two routes must share that field, or the comparison confounds the
    optical field with the electrostatic one."""
    i = SOURCE.index("def eo_overlap(")
    block = SOURCE[i:i + 2600]
    assert "rf_field(np.asarray(w.x[0]), np.asarray(w.x[1]))" in block


def test_an_absent_mode_or_subdomain_returns_nan_rather_than_a_number():
    """A missing subdomain once returned zero from a per-point sampler that
    swallowed its own exception, which is a wrong answer rather than no answer."""
    i = SOURCE.index("def eo_overlap(")
    block = SOURCE[i:i + 2600]
    assert 'return float("nan")' in block
    assert "self._mode is None" in block


def test_the_docstring_states_what_differs_between_the_two_routes():
    """Point evaluation is unavailable on the vector basis, so the quadrature
    differs as well as the field, and a reader must not take the comparison as
    isolating the field alone."""
    i = SOURCE.index("def eo_overlap(")
    block = SOURCE[i:i + 2600]
    assert "probes" in block
    assert "quadrature" in block
