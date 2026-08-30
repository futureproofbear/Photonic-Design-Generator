"""The run's record of the code that produced it.

A provenance field that cannot identify the code behind a result is worse than
an absent one, because it is read as an audit trail. Three defects sat in one
function: the revision was taken from whichever repository the command was
invoked in rather than from the chain, a modified working tree was stamped as
though it were a clean commit, and a failed lookup returned a bare null
indistinguishable from a tree that has no revision.
"""

from __future__ import annotations

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
