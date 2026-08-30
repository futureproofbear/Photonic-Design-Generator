"""A material file named by an override must reach the solver, not only the record.

The library was constructed once from the design as it arrived on disk, and every
override path re-read the design and discarded the library that came with it. A
`--set platform.materials_file=...` therefore reached `design.resolved.json` and
never reached a solver.

**The symptom was silence.** A dropped override returns the nominal answer, which
looks like a result rather than an absence: a sweep of the radio-frequency
permittivity across plus and minus fifteen per cent returned a capacitance
identical in the last bit at every point.
"""

from __future__ import annotations

import inspect
import pathlib

import pytest

from picchain import cli
from picchain.config import Design
from picchain.materials import MaterialLibrary

BASELINE = (pathlib.Path(__file__).resolve().parents[2]
            / "examples" / "edbr_tfln_baseline" / "design.yaml")

#: every command that mutates a design after loading it, and therefore must
#: rebuild the library before handing it to a stage
OVERRIDING_COMMANDS = ["run", "sweep", "corners", "golden", "search", "sensitivity"]


def test_the_library_follows_the_design_it_is_given(tmp_path):
    """`_library` is a pure function of the design, so an override changes it."""
    d = Design.load(BASELINE)
    default = cli._library(d)

    other = tmp_path / "other_materials.yaml"
    other.write_text(
        "materials:\n"
        "  SiO2:\n"
        "    kind: isotropic\n"
        "    index_const: 1.444\n"
        "    eps_rf: 3.9\n"
        "    provenance: test\n",
        encoding="utf-8",
    )
    d.platform.materials_file = str(other)
    overridden = cli._library(d)
    assert overridden is not default
    assert isinstance(overridden, MaterialLibrary)


def test_every_overriding_command_rebuilds_the_library():
    """The regression guard.

    A seventh override site added without a rebuild would reintroduce the defect
    silently, so the check is on the source of each command rather than on one
    execution path.
    """
    missing = []
    for name in OVERRIDING_COMMANDS:
        fn = getattr(cli, name, None)
        assert fn is not None, f"cli.{name} no longer exists; update this list"
        src = inspect.getsource(fn)
        applies = "_apply_override" in src or "set_dotted" in src
        assert applies, f"cli.{name} no longer applies overrides; update this list"
        if "_library(" not in src:
            missing.append(name)
    assert not missing, (
        "these commands mutate the design and hand a stale material library to a "
        f"stage: {missing}. Rebuild it with _library(d) after the overrides")


def test_the_library_is_derived_after_the_overrides_and_not_before():
    """The actual invariant, stated as ordering.

    A textual ban on passing `lib` to a stage would fail correct work: `run`
    rebinds `lib` from `_library(d)` after its override loop and is right to
    pass it. What matters is that the library used was derived AFTER the design
    was mutated, so the check is on the position of the rebuild.
    """
    for name in OVERRIDING_COMMANDS:
        src = inspect.getsource(getattr(cli, name))
        first_override = min(
            (src.index(tok) for tok in ("_apply_override", "set_dotted") if tok in src),
            default=None)
        assert first_override is not None, f"cli.{name} applies no override"
        rebuilds = [i for i in range(len(src)) if src.startswith("_library(", i)]
        assert rebuilds, f"cli.{name} never derives a library"
        assert max(rebuilds) > first_override, (
            f"cli.{name} derives its material library before applying overrides, so a "
            "design that names another material file is recorded with it and solved "
            "without it")
