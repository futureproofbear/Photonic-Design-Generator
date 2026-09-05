"""Run-artifact management.

Every stage writes:
  runs/<run_id>/<stage>.json    machine-readable metrics + provenance
  runs/<run_id>/<stage>.npz     bulk arrays (fields, spectra)
  runs/<run_id>/figures/*.png   optional plots

and the orchestrator writes runs/<run_id>/metrics.json (the merged metric tree)
plus runs/latest -> the newest run.  Everything an agent needs is in
metrics.json; the npz files are for humans and for re-plotting.
"""

from __future__ import annotations

import json
import platform
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


def _json_default(o: Any):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, complex):
        return {"re": o.real, "im": o.imag}
    raise TypeError(f"not JSON serialisable: {type(o)}")


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=_json_default, allow_nan=True)


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _repo_state(where: "pathlib.Path") -> dict[str, Any]:
    """The revision of the git tree containing `where`, and whether it is clean.

    Returns the reason rather than a bare null where git cannot answer, so that
    an absent revision is distinguishable from a failed lookup.
    """
    def _git(*args: str) -> "str | None":
        try:
            r = subprocess.run(["git", "-C", str(where), *args],
                               capture_output=True, text=True, timeout=5)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    root = _git("rev-parse", "--show-toplevel")
    if root is None:
        return {"revision": None, "reason": "not a git tree, or git is unavailable"}
    status = _git("status", "--porcelain")
    return {
        "root": root,
        "revision": _git("rev-parse", "--short", "HEAD"),
        # a run from a modified tree is not reproducible from its revision
        "dirty": bool(status),
        "modified_files": len([l for l in status.splitlines() if l.strip()]) if status else 0,
    }


def environment_fingerprint() -> dict[str, Any]:
    def _v(mod: str) -> str | None:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "unknown")
        except Exception:
            return None

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        # The revision of the CODE THAT RAN, taken from the package's own
        # location, plus whether that tree was modified.
        #
        # This previously invoked `git rev-parse` with no working directory, so
        # it stamped whichever repository the command was invoked from. Run from
        # a design directory inside an application repository, every run recorded
        # the application's revision and never the solver's, and two runs
        # produced by different chain code were indistinguishable. It carried no
        # dirty flag either, so a run made from a modified working tree was
        # stamped as though it came from a clean commit.
        #
        # A provenance field that cannot identify the code that produced the
        # result is worse than an absent one, being read as an audit trail.
        "chain": _repo_state(pathlib.Path(__file__).resolve().parent),
        # kept, and now labelled for what it is
        "invocation_repo": _repo_state(pathlib.Path.cwd()),
        "packages": {m: _v(m) for m in
                     ["numpy", "scipy", "klayout", "gdsfactory", "femwell", "gmsh", "sax",
                      "matplotlib"]},
    }



#: Words carrying no distinguishing weight in a finding's opening phrase.
_KEY_SKIP = {"the", "a", "an", "of", "is", "to", "and", "on", "in", "this",
             "that", "it", "at", "for", "its", "with", "no", "not", "so", "by",
             "are", "was"}


def derive_key(stage: str, msg: str) -> str:
    """A stable key for a finding, from its stage and its opening words."""
    import re as _re
    words = [w for w in _re.findall(r"[a-z0-9]+", msg.lower())
             if w not in _KEY_SKIP][:4]
    return f"{stage}." + "_".join(words or ["warning"])

@dataclass
class RunContext:
    design_dir: Path
    run_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    #: the same findings with their stage and a stable key, so that a design
    #: can acknowledge one by name and a new one can be told from a known one
    warning_records: list[dict] = field(default_factory=list)
    #: set by the runner before each stage, so a warning knows its origin
    current_stage: str = ""
    #: every stage the runner has entered, in order. Read by the verify stage to
    #: tell an acknowledgement whose finding was fixed from one whose stage was
    #: simply left out of the run; the metric tree cannot answer that, a stage
    #: being free to run and write nothing.
    stages_run: list[str] = field(default_factory=list)
    t0: float = field(default_factory=time.time)

    @property
    def run_dir(self) -> Path:
        return self.design_dir / "runs" / self.run_id

    @property
    def fig_dir(self) -> Path:
        return self.run_dir / "figures"

    def ensure(self) -> "RunContext":
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        return self

    # -- metric tree ------------------------------------------------------
    def put(self, dotted: str, value: Any) -> None:
        node = self.metrics
        parts = dotted.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.metrics
        for p in dotted.split("."):
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node

    def masked_for(self, overrides, subdir: str | None = None) -> "RunContext":
        """A copy of this context with the solved value hidden for each override.

        A stage that solves a quantity writes it into the metric tree, and later
        stages prefer the tree over the design file. That is right for the
        primary device and wrong for a variant, whose tree would hold the
        primary's answer. Hiding the overridden leaves makes every reader fall
        back to the design file, where the override was written.

        WHERE A VARIANT IS TO BE SOLVED AND NOT ONLY DRAWN, GIVE IT A `subdir`.
        Stages write their arrays and payloads into `run_dir`, and a variant
        solved in the primary's run directory writes over the primary's files.
        On one design every run carrying a companion laser left `grating.npz`,
        `cavity.npz` and `cavity.json` on disk belonging to the companion while
        the metric tree described the primary, and a sweep that re-solved the
        primary in a loop read the companion's grating back on its second pass
        and returned a beat that did not move with the mirror. With a subdir the
        variant's run directory is its own, the primary's artifacts are copied
        into it so that stages needing an earlier stage's arrays still find
        them, and the primary's directory is untouched.
        """
        import copy as _copy
        import shutil
        v = _copy.copy(self)
        v.metrics = _copy.deepcopy(self.metrics)
        for dotted in (overrides or {}):
            parts = str(dotted).split(".")
            node = v.metrics
            for part in parts[:-1]:
                node = node.get(part) if isinstance(node, dict) else None
                if node is None:
                    break
            if isinstance(node, dict):
                node.pop(parts[-1], None)
        if subdir:
            src = self.run_dir
            v.run_id = f"{self.run_id}/{subdir}"
            v.ensure()
            if src.exists():
                for f in src.iterdir():
                    if f.is_file() and f.suffix in (".npz", ".json"):
                        shutil.copy2(f, v.run_dir / f.name)
        return v

    def warn(self, msg: str, key: str | None = None) -> None:
        """Record a finding.

        A warning is the chain saying *here is something you should know*, and
        until 2026-08-17 nothing read the list: ninety call sites across
        seventeen stages, and a run could emit seventeen findings and still be
        reported a clean pass, because the acceptance verdict grades targets and
        a finding carrying no threshold had no owner.

        Each finding therefore carries a stage and a key. `key` may be given
        explicitly where the wording is likely to change; otherwise it is derived
        from the opening words, which is stable enough to acknowledge against and
        changes if the finding is reworded, at which point it deserves a second
        look anyway.
        """
        self.warnings.append(msg)
        self.warning_records.append({
            "stage": self.current_stage or "unattributed",
            "key": key or derive_key(self.current_stage or "unattributed", msg),
            "message": msg,
        })

    # -- io ---------------------------------------------------------------
    def write_stage(self, stage: str, payload: dict[str, Any], arrays: dict[str, np.ndarray] | None = None) -> None:
        self.ensure()
        dump_json(self.run_dir / f"{stage}.json", payload)
        if arrays:
            np.savez_compressed(self.run_dir / f"{stage}.npz", **arrays)

    def finalise(self, status: str, update_latest: bool = True) -> Path:
        self.ensure()
        out = {
            "run_id": self.run_id,
            "status": status,
            "elapsed_s": round(time.time() - self.t0, 2),
            "environment": environment_fingerprint(),
            "warnings": self.warnings,
            "warning_records": self.warning_records,
            "metrics": self.metrics,
        }
        p = self.run_dir / "metrics.json"
        dump_json(p, out)
        if update_latest:
            # sweep points are probes, not the design's current state, so they
            # deliberately do not move the `latest` pointer
            dump_json(self.design_dir / "runs" / "latest.json",
                      {"run_id": self.run_id, "path": str(p)})
        return p


def new_run_id(tag: str = "") -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{tag}" if tag else stamp
