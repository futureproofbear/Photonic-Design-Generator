"""Invocation of a solver that lives outside this interpreter.

meep has no Windows build, so on this platform it is executed inside a WSL 2
distribution through a small bridge: the job is written as JSON, the runner is
invoked under the meep environment, and the result is read back as JSON. The
chain therefore keeps one interpreter, one metric tree and one exit-code
contract, and the location of the solver becomes a configuration detail.

Where the chain is itself executed under Linux, the same runner is invoked
directly and no wrapper is involved.

Nothing here imports meep. Availability is probed rather than assumed, and a
design that requests the stage on a machine without it receives a stated reason
rather than a traceback.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

RUNNER = Path(__file__).with_name("meep_taper.py")
GRATING_RUNNER = Path(__file__).with_name("meep_grating.py")
BAND_RUNNER = Path(__file__).with_name("mpb_grating.py")


@dataclass
class Backend:
    """How the meep environment is reached from here."""
    kind: str                 # "native" or "wsl"
    distro: str = "Ubuntu"
    micromamba: str = "~/.local/bin/micromamba"
    env: str = "mp"
    ca_bundle: str = "~/.certs/ca-bundle.pem"
    processes: int = 1

    def command(self, *python_args: str, parallel: bool = True) -> list[str]:
        """Command line that runs ``python <args>`` inside the meep environment."""
        inner = [self.micromamba, "run", "-n", self.env]
        if parallel and self.processes > 1:
            inner += ["mpirun", "-np", str(self.processes)]
        inner += ["python", *python_args]
        if self.kind == "native":
            inner[0] = os.path.expanduser(inner[0])
            return inner
        return ["wsl.exe", "-d", self.distro, "--", "bash", "-lc", " ".join(inner)]


def to_wsl_path(p: Path | str) -> str:
    """``C:\\Users\\x`` -> ``/mnt/c/Users/x``; a POSIX path is returned as given."""
    s = str(p).replace("\\", "/")
    if len(s) > 1 and s[1] == ":":
        return f"/mnt/{s[0].lower()}{s[2:]}"
    return s


def default_backend(processes: int = 1) -> Backend:
    kind = "wsl" if platform.system() == "Windows" else "native"
    return Backend(kind=kind, processes=processes)


def probe(backend: Backend | None = None) -> dict:
    """Report whether the solver can be reached, and its version."""
    backend = backend or default_backend()
    if backend.kind == "wsl" and shutil.which("wsl.exe") is None:
        return {"available": False, "reason": "wsl.exe is not on PATH"}

    # the version is printed with a marker, meep itself writing an elapsed-time
    # line to stdout on exit that would otherwise be mistaken for the answer
    snippet = "import meep; print('MEEP_VERSION=' + meep.__version__)"
    quoted = f'"{snippet}"' if backend.kind == "wsl" else snippet
    cmd = backend.command("-c", quoted, parallel=False)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc)}
    for line in (out.stdout or "").splitlines():
        if line.startswith("MEEP_VERSION="):
            return {"available": True, "version": line.split("=", 1)[1].strip()}
    return {"available": False, "reason": (out.stderr or out.stdout).strip()[-400:]}


def run_taper(job: dict, work_dir: Path, backend: Backend | None = None,
              timeout_s: int = 7200) -> dict:
    """Write the job, invoke the taper runner, and read the result back."""
    return _run(RUNNER, "taper", job, work_dir, backend, timeout_s)


def run_grating(job: dict, work_dir: Path, backend: Backend | None = None,
                timeout_s: int = 7200) -> dict:
    """The same, for the finite-grating reflection check."""
    return _run(GRATING_RUNNER, "grating", job, work_dir, backend, timeout_s)


def run_bandstructure(job: dict, work_dir: Path, backend: Backend | None = None,
                     timeout_s: int = 3600, name: str = "bands") -> dict:
    """Kappa from the photonic band gap, by MPB.

    `name` selects the job and result filenames, so a convergence guard solving
    the same structure on a second mesh does not overwrite the primary result.
    """
    b = backend or default_backend()
    single = Backend(kind=b.kind, distro=b.distro, micromamba=b.micromamba,
                     env=b.env, ca_bundle=b.ca_bundle, processes=1)
    return _run(BAND_RUNNER, name, job, work_dir, single, timeout_s)


def job_key(job: dict, sig: int = 10) -> str:
    """A content key for an external solver job, insensitive to last-bit noise.

    Two runs computing the same geometry through the same code produce job files
    that differ in the fifteenth significant figure, the evaluation order not
    being identical. Hashing the raw file therefore never matches, which is how a
    three-hour band structure came to be re-solved for a structure that had not
    changed: the period differed by 5e-16 and the group index by 2e-14.

    Floats are rounded to `sig` significant figures before hashing. Ten is far
    beyond any physical significance here and far short of the noise.
    """
    import hashlib

    def canon(v):
        if isinstance(v, float):
            if v != v or v in (float("inf"), -float("inf")):
                return str(v)
            if v == 0:
                return "0"
            return f"{v:.{sig}e}"
        if isinstance(v, dict):
            return {k: canon(v[k]) for k in sorted(v)}
        if isinstance(v, (list, tuple)):
            return [canon(x) for x in v]
        return v

    blob = json.dumps(canon(job), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _find_prior(name: str, key: str, work_dir: Path) -> tuple[dict, str] | None:
    """A completed result for this identical job under a sibling run, if any.

    Searched newest first and returned with the run it came from, so that a reuse
    is attributable rather than anonymous. Nothing is reused unless both the job
    and its result are present and the job key matches exactly.
    """
    runs = work_dir.parent
    if not runs.is_dir():
        return None
    for d in sorted((x for x in runs.iterdir() if x.is_dir()), reverse=True):
        if d == work_dir:
            continue
        jp, rp = d / f"meep_{name}_job.json", d / f"meep_{name}_result.json"
        if not (jp.exists() and rp.exists()):
            continue
        try:
            if job_key(json.loads(jp.read_text(encoding="utf-8"))) != key:
                continue
            return json.loads(rp.read_text(encoding="utf-8")), d.name
        except (OSError, ValueError):
            continue
    return None


def _run(runner: Path, name: str, job: dict, work_dir: Path,
         backend: Backend | None = None, timeout_s: int = 7200) -> dict:
    backend = backend or default_backend()
    work_dir.mkdir(parents=True, exist_ok=True)
    job_path = work_dir / f"meep_{name}_job.json"
    out_path = work_dir / f"meep_{name}_result.json"
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    if out_path.exists():
        out_path.unlink()

    # An identical job already solved is not solved again. The external solver is
    # the only part of this chain measured in hours, and it is deterministic in
    # its inputs, so re-solving an unchanged structure buys nothing whatever.
    # Set the environment variable PICCHAIN_NO_REUSE to force a fresh solve.
    import os

    key = job_key(job)
    if not os.environ.get("PICCHAIN_NO_REUSE"):
        prior = _find_prior(name, key, work_dir)
        if prior is not None:
            result, source = prior
            result = dict(result)
            result["reused_from_run"] = source
            result["job_key"] = key
            out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            (work_dir / f"meep_{name}_run.log").write_text(
                "reused the result of run " + source
                + ", the job being identical; job key " + key + chr(10),
                encoding="utf-8")
            return result

    if backend.kind == "wsl":
        cmd = backend.command(to_wsl_path(runner), to_wsl_path(job_path), to_wsl_path(out_path))
    else:
        cmd = backend.command(str(runner), str(job_path), str(out_path))

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    log = (work_dir / f"meep_{name}_run.log")
    log.write_text((proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""),
                   encoding="utf-8")
    if not out_path.exists():
        tail = (proc.stderr or proc.stdout or "").strip()[-800:]
        raise RuntimeError(f"meep produced no result; see {log.name}\n{tail}")
    return json.loads(out_path.read_text(encoding="utf-8"))
