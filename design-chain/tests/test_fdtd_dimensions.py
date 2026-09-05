"""A structure is refused the dimensionality its runner does not build.

`fdtd.dimensions` was recorded in the payload of every structure and passed to
the runner of one. A multimode-splitter run declaring three dimensions emitted a
payload stamped ``dimensions: 3`` carrying a two-dimensional result, and the job
dictionary omitted the field, so the cache returned the two-dimensional solve.
"""

import re
from pathlib import Path

import pytest

from picchain.stages import s09_fdtd

SOURCE = Path(s09_fdtd.__file__).read_text(encoding="utf-8")


class _Cfg:
    def __init__(self, structure, dimensions):
        self.structure, self.dimensions = structure, dimensions


@pytest.mark.parametrize("structure", ["mmi", "coupler", "grating", "bandstructure"])
def test_three_dimensions_is_refused_where_no_runner_builds_it(structure):
    with pytest.raises(ValueError, match="two-dimensional cell only"):
        s09_fdtd._refuse_a_dimension_the_runner_does_not_build(_Cfg(structure, 3))


def test_the_taper_builds_three_dimensions_and_is_admitted():
    s09_fdtd._refuse_a_dimension_the_runner_does_not_build(_Cfg("taper", 3))


@pytest.mark.parametrize(
    "structure", ["mmi", "coupler", "grating", "bandstructure", "taper"]
)
def test_two_dimensions_is_admitted_everywhere(structure):
    s09_fdtd._refuse_a_dimension_the_runner_does_not_build(_Cfg(structure, 2))


def test_the_message_names_the_field_and_the_remedy():
    with pytest.raises(ValueError) as excinfo:
        s09_fdtd._refuse_a_dimension_the_runner_does_not_build(_Cfg("mmi", 3))
    text = str(excinfo.value)
    assert "fdtd.dimensions" in text
    assert "fdtd.structure" in text
    assert "taper" in text


def _job_dict_of(function_name):
    """Return the source of the job dictionary built inside one runner."""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"^def (\w+)\(", SOURCE, re.M)]
    bounds = {}
    for i, (pos, name) in enumerate(starts):
        bounds[name] = (pos, starts[i + 1][0] if i + 1 < len(starts) else len(SOURCE))
    a, b = bounds[function_name]
    match = re.search(r"\n    job = \{(.*?)\n    \}", SOURCE[a:b], re.S)
    assert match, f"{function_name} builds no job dictionary"
    return match.group(1)


@pytest.mark.parametrize(
    "function_name", ["run", "_run_mmi", "_run_coupler", "_run_grating", "_run_bands"]
)
def test_every_job_carries_its_dimensionality(function_name):
    """The cache key is computed over the job, so a job that omits the
    dimensionality lets a two-dimensional solve satisfy a three-dimensional
    request. One such reuse returned a transmission agreeing to six decimals
    with the run it was meant to differ from."""
    assert '"dimensions": cfg.dimensions,' in _job_dict_of(function_name)


class _Ctx:
    """Collects what the stage reports."""

    def __init__(self):
        self.warnings = []

    def warn(self, text):
        self.warnings.append(text)


def test_a_passive_structure_above_unity_is_reported():
    """The first three-dimensional taper solve returned 1.00378 and the stage
    said nothing. The excess is the size of the quantity the run measures."""
    ctx = _Ctx()
    s09_fdtd._warn_if_power_exceeds_unity(
        ctx, {"transmission_fundamental": 1.0037759184851751}
    )
    assert len(ctx.warnings) == 1
    assert "exceeds unity" in ctx.warnings[0]
    assert "0.378 per cent" in ctx.warnings[0]


def test_a_transmission_at_or_below_unity_is_not_reported():
    ctx = _Ctx()
    s09_fdtd._warn_if_power_exceeds_unity(
        ctx, {"transmission_fundamental": 0.9888506780574378, "other": 1.0}
    )
    assert ctx.warnings == []


def test_flux_ratio_noise_is_not_reported_as_a_passivity_violation():
    """A flux ratio formed from two DFT monitors carries noise of order one part
    in a million. The plane reduction's self-normalised budget reads 1.0000019
    on a solve whose physics is sound."""
    ctx = _Ctx()
    s09_fdtd._warn_if_power_exceeds_unity(ctx, {"self_normalised_taper": 1.0000019145871135})
    assert ctx.warnings == []


def test_a_real_violation_is_still_reported_above_the_tolerance():
    ctx = _Ctx()
    s09_fdtd._warn_if_power_exceeds_unity(ctx, {"self_normalised_taper": 1.0077})
    assert len(ctx.warnings) == 1


def test_a_missing_quantity_is_skipped():
    ctx = _Ctx()
    s09_fdtd._warn_if_power_exceeds_unity(ctx, {"transmission_fundamental": None})
    assert ctx.warnings == []


def test_a_reference_no_finer_than_the_measurand_is_reported():
    """The normalisation guide lost 0.245 per cent over its own length while the
    structure was graded at a few tenths of a per cent. The standing tolerance
    was two per cent, which is five times the measurand."""
    ctx = _Ctx()
    s09_fdtd._warn_if_the_reference_is_not_finer_than_the_measurand(
        ctx, normalisation_check=0.997551031545434, transmission=0.9989
    )
    assert len(ctx.warnings) == 1
    assert "unresolved by this cell" in ctx.warnings[0]


def test_a_reference_far_finer_than_the_measurand_is_accepted():
    ctx = _Ctx()
    s09_fdtd._warn_if_the_reference_is_not_finer_than_the_measurand(
        ctx, normalisation_check=0.99990, transmission=0.9889
    )
    assert ctx.warnings == []


def test_a_clean_reference_is_accepted():
    ctx = _Ctx()
    s09_fdtd._warn_if_the_reference_is_not_finer_than_the_measurand(
        ctx, normalisation_check=1.0, transmission=0.9889
    )
    assert ctx.warnings == []


def test_the_three_dimensional_ambient_is_the_cladding_and_not_the_slab_index():
    """`n_clad` is the effective index of the unetched film beside the ridge and
    belongs to the plane reduction. The first three-dimensional taper solve used
    it as the ambient of a cell that already built the slab explicitly, so a real
    ridge and a real slab sat in a medium of 1.5509 that exists nowhere in the
    device. The cladding of that stack is 1.4440."""
    source = Path(
        s09_fdtd.__file__
    ).parent.parent.joinpath("fdtd", "meep_taper.py").read_text(encoding="utf-8")
    assert 'job["n_clad"] if dims == 2 else job["n_ambient"]' in source
    assert '"n_ambient": float(np.sqrt(max(' in SOURCE


def test_the_taper_job_carries_the_ambient_index():
    assert '"n_ambient"' in _job_dict_of("run")


def test_the_taper_payload_records_its_structure():
    """The mmi and coupler payloads carry `structure`; the taper payload did not,
    so an enumeration of the emitted payloads by the option each selected could
    not be reproduced from the taper runs."""
    assert '"structure": cfg.structure,' in SOURCE


def test_a_result_records_which_runner_produced_it(tmp_path):
    """The runner is an input to the result as much as the job is.

    Folding its digest into the job key does not work: a lookup recomputes the
    stored job's key with the runner it holds now, so the digest appears on both
    sides and cancels. It is written into the result and compared there. An
    earlier attempt put it in the key on one side only, which made every key
    mismatch and stopped reuse altogether for an evening.
    """
    from picchain.fdtd import bridge

    job = {"a": 1.0, "b": [2.0, 3.0]}
    assert bridge.job_key(job) == bridge.job_key(job)
    assert bridge.job_key(job) != bridge.job_key({"a": 2.0})

    one, two = tmp_path / "one.py", tmp_path / "two.py"
    one.write_text("print('a')", encoding="utf-8")
    two.write_text("print('b')", encoding="utf-8")
    assert bridge.runner_digest(one) != bridge.runner_digest(two)
    assert bridge.runner_digest(one) == bridge.runner_digest(one)


def test_an_unreadable_runner_disables_reuse_rather_than_matching(tmp_path):
    from picchain.fdtd import bridge

    assert bridge.runner_digest(tmp_path / "absent.py") == "unreadable"


def test_the_guide_runs_through_the_absorber():
    """The ridge stopped at the inner face of the absorber, so the mode met an
    abrupt end of the guide exactly where the absorber began. That facet
    reflects by different amounts for guides of different width, and a taper
    normalised against a straight guide of another width inherited the
    difference: two runs of one taper differed by 1.15 per cent in net flux at
    the input monitor, where the source and the input section were identical."""
    import json
    import types

    src = Path(s09_fdtd.__file__).parent.parent / "fdtd" / "meep_taper.py"
    text = src.read_text(encoding="utf-8")
    assert 'x0 = -(L_in + L_t / 2.0) - dpml' in text
    assert 'x1 = L_t / 2.0 + L_out + dpml' in text

    # exercise the vertex arithmetic without importing meep
    ns = {}
    fake = types.SimpleNamespace(
        Vector3=lambda x=0.0, y=0.0, z=0.0: types.SimpleNamespace(x=x, y=y, z=z),
        inf=1.0e20,
    )
    exec(  # noqa: S102 - the module under test is not importable off the solver host
        "import numpy as np\n"
        + text.split("def taper_halfwidths")[1].join(["def taper_halfwidths", ""])
        .split("def build_geometry")[0],
        {"np": __import__("numpy"), "mp": fake},
        ns,
    )
    job = {
        "tip_width_um": 0.9, "full_width_um": 1.95, "length_um": 5.0,
        "in_length_um": 6.0, "out_length_um": 6.0, "pml_um": 1.5,
    }
    sx = job["in_length_um"] + job["length_um"] + job["out_length_um"] + 2 * job["pml_um"]
    x0 = -(job["in_length_um"] + job["length_um"] / 2.0) - job["pml_um"]
    x1 = job["length_um"] / 2.0 + job["out_length_um"] + job["pml_um"]
    assert x0 == -sx / 2, "the guide must reach the input face of the cell"
    assert x1 == sx / 2, "the guide must reach the output face of the cell"
    assert json.dumps({"x0": x0, "x1": x1})


def test_the_raw_fluxes_are_retained():
    """A budget that cannot be reconstructed cannot be checked by a reader."""
    src = Path(s09_fdtd.__file__).parent.parent / "fdtd" / "meep_taper.py"
    text = src.read_text(encoding="utf-8")
    assert '"raw": {' in text
    for field in ("transmitted_flux", "reference_flux",
                  "forward_amplitude_sq", "backward_amplitude_sq"):
        assert field in text


def test_every_runner_carries_its_guide_through_the_absorber():
    """The taper's ridge stopped at the inner face of the absorber and the
    grating's guide did the same; the splitter's leads stopped 0.5 um inside it
    while its normalisation guide ran past the cell edge. A guide terminating
    where the absorber begins presents a facet to the mode, and it presents a
    different one at each width."""
    root = Path(s09_fdtd.__file__).parent.parent / "fdtd"
    taper = (root / "meep_taper.py").read_text(encoding="utf-8")
    grating = (root / "meep_grating.py").read_text(encoding="utf-8")
    mmi = (root / "meep_mmi.py").read_text(encoding="utf-8")
    coupler = (root / "meep_coupler.py").read_text(encoding="utf-8")

    assert "- dpml" in taper and "+ dpml" in taper
    assert 'through = total + 2.0 * job["pml_um"]' in grating
    assert 'run_out = job["pml_um"] + 1.0' in mmi
    # the coupler was already correct: its bus is two absorber widths longer
    # than the cell and its ring stations run past both ends
    assert "2 * X + 2 * dpml + 2.0" in coupler


def test_the_two_escape_channels_are_measured_separately():
    """The residual that failed to reach the output plane contains the lateral
    channel, the vertical channel, the reflection and the reference guide's own
    loss. A study attributed a difference between two dimensionalities to the
    vertical channel on the strength of that residual alone. Four flux planes
    just inside the absorber separate the two axes for the cost of four discrete
    Fourier transforms and no further simulation."""
    src = Path(s09_fdtd.__file__).parent.parent / "fdtd" / "meep_taper.py"
    text = src.read_text(encoding="utf-8")
    for field in ("escaped_lateral", "escaped_vertical", "escaped_total",
                  "escape_accounts_for"):
        assert field in text, field
    # the minus face is subtracted, a plane's flux being signed along its normal
    assert 'mp.get_fluxes(sides["lateral_minus"])[0])' in text
    # the vertical pair exists only where there is a third axis
    assert 'if dims == 3 else 0.0' in text


def test_the_taper_runner_carries_a_convergence_guard():
    """The splitter and coupler runners solved a second time on a coarser mesh
    and reported the shift; the taper and grating runners did not, and the study
    went to the pair that did not. The plane loss moves 68 per cent between
    resolution 10 and 20."""
    src = Path(s09_fdtd.__file__).parent.parent / "fdtd" / "meep_taper.py"
    text = src.read_text(encoding="utf-8")
    assert 'guard = int(job.get("convergence_resolution") or 0)' in text
    assert '"loss_shift_fraction"' in text
    assert '"convergence_resolution"' in _job_dict_of("run")


class _Cfg2:
    def __init__(self, resolution=20, ceiling=16.0):
        self.resolution, self.max_cells_millions = resolution, ceiling


def _taper_job(resolution, dimensions=3):
    return {
        "resolution": resolution, "dimensions": dimensions,
        "in_length_um": 6.0, "length_um": 5.0, "out_length_um": 6.0,
        "pml_um": 1.5, "width_um": 10.0, "height_um": 6.0,
    }


def test_a_grid_beyond_the_ceiling_is_refused():
    """This host bugchecked while a 32.4 million cell grid was allocating, at
    resolution 30. The arithmetic is one multiplication and it was never done."""
    with pytest.raises(ValueError, match="32.4 million cells"):
        s09_fdtd._refuse_a_grid_this_host_cannot_be_trusted_with(
            _Cfg2(30), _taper_job(30))


def test_the_grid_this_host_has_completed_is_allowed():
    s09_fdtd._refuse_a_grid_this_host_cannot_be_trusted_with(
        _Cfg2(20), _taper_job(20))


def test_the_plane_is_not_constrained_by_a_three_dimensional_ceiling():
    """The plane reduction at resolution 80 is 1.28 million cells."""
    s09_fdtd._refuse_a_grid_this_host_cannot_be_trusted_with(
        _Cfg2(80), _taper_job(80, dimensions=2))


def test_the_ceiling_can_be_raised_deliberately():
    s09_fdtd._refuse_a_grid_this_host_cannot_be_trusted_with(
        _Cfg2(30, ceiling=40.0), _taper_job(30))


def test_the_message_names_the_field_and_the_arithmetic():
    with pytest.raises(ValueError) as e:
        s09_fdtd._refuse_a_grid_this_host_cannot_be_trusted_with(
            _Cfg2(30), _taper_job(30))
    text = str(e.value)
    assert "fdtd.max_cells_millions" in text
    assert "fdtd.resolution" in text
    assert "9.6 million" in text


def test_a_grating_disagreement_smaller_than_its_mesh_shift_is_refused():
    """The runner's first execution returned a kappa 0.74 times the coupled-mode
    value and the stage attributed the departure to the weak-perturbation
    assumption, which is a statement about physics. The same payload showed that
    number moving 86 per cent between resolution 10 and 20."""
    ctx = _Ctx()
    s09_fdtd._grade_the_grating_disagreement_against_its_own_mesh(
        ctx, {"guard": {"resolution": 10, "shift_fraction": 0.8619}, "resolution": 20},
        0.7386)
    assert len(ctx.warnings) == 1
    assert "uninformative at this mesh" in ctx.warnings[0]
    assert "not to be read as physics" in ctx.warnings[0]


def test_a_grating_disagreement_larger_than_its_mesh_shift_is_reported_plainly():
    ctx = _Ctx()
    s09_fdtd._grade_the_grating_disagreement_against_its_own_mesh(
        ctx, {"guard": {"resolution": 20, "shift_fraction": 0.02}, "resolution": 40},
        0.70)
    assert len(ctx.warnings) == 1
    assert "uninformative" not in ctx.warnings[0]
    assert "against a 30% departure" in ctx.warnings[0]


def test_a_grating_solve_without_a_guard_says_so():
    ctx = _Ctx()
    s09_fdtd._grade_the_grating_disagreement_against_its_own_mesh(
        ctx, {"resolution": 20}, 0.74)
    assert "no convergence guard" in ctx.warnings[0]


def test_the_cache_lookup_and_store_keys_are_built_alike(tmp_path):
    """`_run` keyed on the job and the runner while `_find_prior` keyed on the
    job alone, so the two could never match and every solve re-ran. One grating
    job with byte-identical job files and equal keys re-solved for ten minutes.
    """
    import json as _json
    from picchain.fdtd import bridge

    runner = tmp_path / "runner.py"
    runner.write_text("print('x')", encoding="utf-8")
    runs = tmp_path / "runs"
    prior, current = runs / "a", runs / "b"
    for d in (prior, current):
        d.mkdir(parents=True)
    job = {"a": 1.0}
    (prior / "meep_taper_job.json").write_text(_json.dumps(job), encoding="utf-8")
    (prior / "meep_taper_result.json").write_text(
        _json.dumps({"ok": True, "runner_digest": bridge.runner_digest(runner)}),
        encoding="utf-8")

    key = bridge.job_key(job)
    found = bridge._find_prior("taper", key, current, runner=runner)
    assert found is not None, "an identical job under a sibling run must be reused"
    assert found[1] == "a"


def test_a_result_from_a_different_runner_is_not_reused(tmp_path):
    """A solve made by an earlier version of the solver is not the solve the
    present one would make. Six output fields and a third simulation were added
    to one runner, and the next run returned a cached result carrying none."""
    import json as _json
    from picchain.fdtd import bridge

    runner, other = tmp_path / "runner.py", tmp_path / "other.py"
    runner.write_text("print('x')", encoding="utf-8")
    other.write_text("print('y')", encoding="utf-8")
    runs = tmp_path / "runs"
    prior, current = runs / "a", runs / "b"
    for d in (prior, current):
        d.mkdir(parents=True)
    job = {"a": 1.0}
    (prior / "meep_taper_job.json").write_text(_json.dumps(job), encoding="utf-8")
    (prior / "meep_taper_result.json").write_text(
        _json.dumps({"ok": True, "runner_digest": bridge.runner_digest(runner)}),
        encoding="utf-8")

    key = bridge.job_key(job)
    assert bridge._find_prior("taper", key, current, runner=runner) is not None
    assert bridge._find_prior("taper", key, current, runner=other) is None


def test_a_result_predating_the_digest_is_not_reused(tmp_path):
    """Results written before 2026-09-06 carry no `runner_digest`, and the
    runner that made them is unknown. Reuse fails safe."""
    import json as _json
    from picchain.fdtd import bridge

    runner = tmp_path / "runner.py"
    runner.write_text("print('x')", encoding="utf-8")
    runs = tmp_path / "runs"
    prior, current = runs / "a", runs / "b"
    for d in (prior, current):
        d.mkdir(parents=True)
    job = {"a": 1.0}
    (prior / "meep_taper_job.json").write_text(_json.dumps(job), encoding="utf-8")
    (prior / "meep_taper_result.json").write_text('{"ok": true}', encoding="utf-8")
    assert bridge._find_prior("taper", bridge.job_key(job), current,
                              runner=runner) is None
