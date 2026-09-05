"""The run's record of the code that produced it.

A provenance field that cannot identify the code behind a result is worse than
an absent one, because it is read as an audit trail. Three defects sat in one
function: the revision was taken from whichever repository the command was
invoked in rather than from the chain, a modified working tree was stamped as
though it were a clean commit, and a failed lookup returned a bare null
indistinguishable from a tree that has no revision.
"""

from __future__ import annotations

import inspect
import pathlib
import subprocess

import pytest

from picchain.artifacts import _repo_state, environment_fingerprint


def test_the_revision_recorded_is_the_chain_and_not_the_caller():
    """The stamp must follow the package, not the working directory.

    This is the defect it exists to prevent: run from a design directory inside
    an application repository, every run recorded the application's revision and
    never the solver's, so two runs produced by different chain code were
    indistinguishable.
    """
    import picchain
    env = environment_fingerprint()
    chain_root = pathlib.Path(env["chain"]["root"]).resolve()
    package = pathlib.Path(picchain.__file__).resolve()
    assert chain_root in package.parents


def test_a_modified_tree_is_reported_as_modified(tmp_path):
    """A run from a dirty tree is not reproducible from its revision, and says so."""
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], capture_output=True, check=True)

    try:
        git("init", "-q")
    except Exception:
        pytest.skip("git is unavailable")
    git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("one")
    git("add", "-A"); git("commit", "-qm", "first")

    clean = _repo_state(tmp_path)
    assert clean["dirty"] is False
    assert clean["modified_files"] == 0
    assert clean["revision"]

    (tmp_path / "a.txt").write_text("two")
    dirty = _repo_state(tmp_path)
    assert dirty["dirty"] is True
    assert dirty["modified_files"] == 1
    # the revision is unchanged, which is exactly why the flag is needed
    assert dirty["revision"] == clean["revision"]


def test_a_tree_with_no_revision_gives_a_reason_rather_than_a_bare_null(tmp_path):
    """An absent revision must be distinguishable from a failed lookup."""
    state = _repo_state(tmp_path)
    assert state["revision"] is None
    assert state["reason"]


def test_the_release_manifest_demands_a_committed_chain():
    """A mask that cannot be regenerated from a commit is not ready to send."""
    import inspect

    from picchain.stages import s15_release
    src = inspect.getsource(s15_release)
    assert "the chain that produced this is a committed revision" in src
    # and the condition must read the chain's own state, not the caller's
    assert 'env.get("chain")' in src
    assert "environment.chain" in src


def test_every_provenance_row_has_the_shape_the_renderer_reads():
    """A malformed row breaks the report and nothing else.

    The `modulator` row was added with three-element metric tuples where the
    renderer unpacks two, so every run of that design emitted
    "report rendering failed: too many values to unpack" and produced no
    report.md. The verdict, the metrics and the mask were all unaffected, which
    is why it went unnoticed.
    """
    from picchain.report import PROVENANCE

    for entry in PROVENANCE:
        assert len(entry) == 4, f"provenance row is not a 4-tuple: {entry[0]}"
        stage, question, tool, metrics = entry
        assert isinstance(stage, str) and isinstance(question, str)
        for m in metrics:
            assert len(m) == 2, f"metric tuple in {stage!r} is not a pair: {m}"


def test_an_acknowledgement_whose_stage_did_not_run_is_not_called_stale():
    """A partial run establishes what its absent stages would have found.

    The staleness check compares the acknowledgements in the design file against
    the findings the run emitted, and every acknowledgement belonging to a stage
    that was skipped falls out of that comparison. One design whose `stages:`
    line omitted the layout stages reported six stale entries on a run that had
    simply not drawn a mask. A check that reports a false positive on an ordinary
    partial run is a check a reader learns to skip, so the two cases are now
    reported separately and under different keys.
    """
    from picchain.stages import s07_verify

    src = inspect.getsource(s07_verify)
    assert "findings_acknowledged_stage_not_run" in src
    assert "verify.acknowledgements_stage_not_run" in src
    # the split must be made on the stage the key names, against the stages the
    # runner recorded, and not against the metric tree: a stage may run and
    # write no metrics
    assert "stages_run" in src
    assert "_stage_of" in src


def test_the_runner_records_every_stage_it_enters():
    """`stages_run` is the only record of what a run actually executed.

    The metric tree is not that record. A stage is free to run and write
    nothing, and its absence from the tree would then read as a stage that never
    ran, which is the misreading the staleness check was making.
    """
    from picchain import artifacts, cli

    ctx = artifacts.RunContext(design_dir=pathlib.Path("."), run_id="x")
    assert ctx.stages_run == []

    src = inspect.getsource(cli)
    n_set = src.count("ctx.current_stage = s\n") + src.count("ctx.current_stage = st\n")
    n_rec = src.count("ctx.stages_run.append(")
    assert n_rec >= n_set, "every site that sets the current stage must record it"


def test_a_variant_solved_in_a_subdir_leaves_the_primary_artifacts_untouched(tmp_path):
    """A variant's stages write into their own directory and read copies of the primary's.

    Solved in the primary's run directory, a companion laser's grating and cavity
    stages wrote over the primary's arrays; the metric tree described one device
    and the files on disk another. With a subdir the primary's files are copied
    in and the variant writes beside them, not over them.
    """
    import numpy as np
    from picchain import artifacts

    ctx = artifacts.RunContext(design_dir=tmp_path, run_id="r").ensure()
    np.savez(ctx.run_dir / "grating.npz", period=np.array([1.42474]))
    (ctx.run_dir / "grating.json").write_text('{"period_um": 1.42474}')
    v = ctx.masked_for({"grating.period_um": 1.4248532}, subdir="companions/CW")
    assert v.run_dir != ctx.run_dir
    assert v.run_dir.is_dir()
    # the primary's artifacts were copied in, so a stage needing them still finds them
    assert (v.run_dir / "grating.npz").exists() and (v.run_dir / "grating.json").exists()
    # a write in the variant's directory does not reach the primary's
    np.savez(v.run_dir / "grating.npz", period=np.array([1.4248532]))
    assert float(np.load(ctx.run_dir / "grating.npz")["period"][0]) == 1.42474
    assert float(np.load(v.run_dir / "grating.npz")["period"][0]) == 1.4248532
