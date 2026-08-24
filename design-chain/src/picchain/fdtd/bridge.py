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
from collections import deque
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


def _decode(raw) -> str:
    """wsl.exe writes its own errors as UTF-16LE while the guest writes UTF-8.

    A guest message therefore arrives readable and a wrapper message arrives
    with a NUL between every character, which renders as `T\x00h\x00e\x00...`
    and is unreadable in a report. The two are distinguished by the NULs.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-16-le" if b"\x00" in raw[:40] else "utf-8", "replace")
        except Exception:
            raw = raw.decode("utf-8", "replace")
    return raw.replace("\x00", "") if isinstance(raw, str) else ""


def probe(backend: Backend | None = None) -> dict:
    """Report whether the solver can be reached, and its version.

    The report names the environment that was PROBED as well as the outcome.
    Without it a wrong distribution name returns WSL_E_DISTRO_NOT_FOUND, which
    reads as WSL being absent from the machine and sends the reader to install
    what is already installed.
    """
    backend = backend or default_backend()
    where = {"kind": backend.kind, "environment": backend.env,
             "launcher": backend.micromamba}
    if backend.kind == "wsl":
        where["distro"] = backend.distro
    if backend.kind == "wsl" and shutil.which("wsl.exe") is None:
        return {"available": False, "probed": where,
                "reason": "wsl.exe is not on PATH"}

    # the version is printed with a marker, meep itself writing an elapsed-time
    # line to stdout on exit that would otherwise be mistaken for the answer
    snippet = "import meep; print('MEEP_VERSION=' + meep.__version__)"
    quoted = f'"{snippet}"' if backend.kind == "wsl" else snippet
    cmd = backend.command("-c", quoted, parallel=False)
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "probed": where, "reason": str(exc)}
    stdout, stderr = _decode(out.stdout), _decode(out.stderr)
    for line in stdout.splitlines():
        if line.startswith("MEEP_VERSION="):
            return {"available": True, "probed": where,
                    "version": line.split("=", 1)[1].strip()}
    reason = (stderr or stdout).strip()[-400:]
    hint = None
    if "WSL_E_DISTRO_NOT_FOUND" in reason or "no distribution" in reason.lower():
        hint = (f"WSL is reachable but carries no distribution named "
                f"{backend.distro!r}. Run `wsl.exe -l -v` for the names actually "
                f"present and set `fdtd.wsl_distro` to one of them. This is a "
                f"name mismatch and not a missing installation.")
    elif "micromamba" in reason and "No such file" in reason:
        hint = (f"The distribution is reachable and the launcher is absent at "
                f"{backend.micromamba}. Install micromamba there, or point "
                f"MAMBA_ROOT_PREFIX at an existing environment root.")
    res = {"available": False, "probed": where, "reason": reason}
    if hint:
        res["hint"] = hint
    return res


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

    # STREAMED, not buffered, from 2026-08-17. This was
    # `subprocess.run(capture_output=True)`, which holds the solver's output in
    # memory and writes it only after the process exits, so a solve running for
    # an hour was silent for that hour. meep prints exactly what an operator
    # needs while it waits: the timestep reached, the simulated time, and the
    # field decay the stopping condition is watching.
    #
    # The cost of that silence was paid twice. A live taper solve was checked
    # against the host process list, showed nothing because eight ranks were in a
    # synchronisation barrier, and was nearly reported dead; its remaining time
    # then had to be estimated from the cell size and the Courant timestep rather
    # than read. Worse, a job killed at the timeout left a log written from a
    # buffer that was never flushed, so the one case where the output matters
    # most was the case where it was least complete.
    log = (work_dir / f"meep_{name}_run.log")
    tail: deque[str] = deque(maxlen=40)
    with open(log, "w", encoding="utf-8", buffering=1) as fh:
        fh.write(f"$ {' '.join(str(c) for c in cmd)}\n\n")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                fh.write(line)
                tail.append(line.rstrip())
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            fh.write(f"\n--- killed at the {timeout_s} s ceiling ---\n")
            raise RuntimeError(
                f"meep exceeded its {timeout_s} s ceiling; the log holds every line "
                f"it produced up to the kill, see {log.name}\n" + "\n".join(tail)
            ) from None
        finally:
            if proc.stdout is not None:
                proc.stdout.close()

    if not out_path.exists():
        raise RuntimeError(f"meep produced no result; see {log.name}\n"
                           + "\n".join(tail))
    return json.loads(out_path.read_text(encoding="utf-8"))
