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
COUPLER_RUNNER = Path(__file__).with_name("meep_coupler.py")
MMI_RUNNER = Path(__file__).with_name("meep_mmi.py")


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


#: machine-local overrides. The distribution and the environment are properties
#: of the machine and not of the design, so they are read from here as well as
#: from the design file. A design carrying one machine's distribution name is
#: not portable, and it was the design file or nothing until 2026-09-03.
ENV_DISTRO = "PICCHAIN_FDTD_DISTRO"
ENV_ENVIRONMENT = "PICCHAIN_FDTD_ENV"

#: environments tried after the declared one, where the declared one does not
#: carry meep. These are the names in ordinary use for a meep install; the list
#: is a convenience and the discovery below does not depend on it
COMMON_ENVS = ("mpp", "mp", "meep", "pmp")

_RESOLVED: dict[tuple, tuple] = {}


def _run_probe(backend: "Backend") -> dict:
    """One launch, reporting the meep version and whether mpirun is present."""
    snippet = ("import meep, shutil; "
               "print('MEEP_VERSION=' + meep.__version__); "
               "print('MPIRUN=' + str(shutil.which('mpirun')))")
    quoted = f'"{snippet}"' if backend.kind == "wsl" else snippet
    cmd = backend.command("-c", quoted, parallel=False)
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc)}
    stdout, stderr = _decode(out.stdout), _decode(out.stderr)
    version = mpirun = None
    for line in stdout.splitlines():
        if line.startswith("MEEP_VERSION="):
            version = line.split("=", 1)[1].strip()
        elif line.startswith("MPIRUN="):
            val = line.split("=", 1)[1].strip()
            mpirun = None if val in ("None", "") else val
    if version:
        return {"available": True, "version": version, "mpirun": mpirun}
    return {"available": False, "reason": (stderr or stdout).strip()[-400:]}


def _wsl_distros() -> list[str]:
    """The distribution names wsl.exe reports, in its own order."""
    try:
        out = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in _decode(out.stdout).splitlines() if ln.strip()]


def _env_names(backend: "Backend") -> list[str]:
    """Environment names the launcher reports inside one distribution.

    The name column of ``micromamba env list`` carries a relative path where an
    environment lives outside the root prefix, so the basename of the path
    column is taken instead.
    """
    cmd = backend.command("--version", parallel=False)
    cmd[-2:] = ["env", "list"] if backend.kind == "native" else cmd[-2:]
    inner = f"{backend.micromamba} env list"
    cmd = ([os.path.expanduser(backend.micromamba), "env", "list"]
           if backend.kind == "native"
           else ["wsl.exe", "-d", backend.distro, "--", "bash", "-lc", inner])
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    names: list[str] = []
    for ln in _decode(out.stdout).splitlines():
        parts = ln.split()
        if not parts or parts[0].startswith(("Name", "-", "─")):
            continue
        base = parts[-1].rstrip("/").rsplit("/", 1)[-1]
        if base.replace("_", "").replace("-", "").isalnum() and base not in names:
            names.append(base)
    return names[:8]


def resolve(backend: "Backend" | None = None) -> tuple["Backend", dict]:
    """The backend that actually reaches meep on this machine, and how.

    The declared pair is tried first, then the machine-local overrides, then
    every distribution the wrapper reports against every environment its
    launcher reports. A wrong name in a design file is therefore a slower start
    rather than a stage that cannot run, and what was found is reported so that
    the design or the environment can be corrected knowingly.

    A parallel job needs mpirun as well as meep, and an environment can carry
    one without the other. Where the resolved environment has meep and no
    mpirun, the job is run serially and the report says so, which is a slow
    solve rather than a failed one.
    """
    b = backend or default_backend()
    b = Backend(kind=b.kind,
                distro=os.environ.get(ENV_DISTRO, b.distro),
                micromamba=b.micromamba,
                env=os.environ.get(ENV_ENVIRONMENT, b.env),
                ca_bundle=b.ca_bundle,
                processes=b.processes)
    key = (b.kind, b.distro, b.env, b.processes)
    if key in _RESOLVED:
        return _RESOLVED[key]

    tried: list[dict] = []

    def attempt(cand: "Backend", how: str):
        res = _run_probe(cand)
        tried.append({"distro": cand.distro if cand.kind == "wsl" else None,
                      "environment": cand.env, "how": how,
                      "available": res["available"],
                      "reason": res.get("reason")})
        return res

    candidates: list[tuple[Backend, str]] = [(b, "declared")]
    if b.kind == "wsl":
        distros = _wsl_distros()
        for d in distros:
            if d != b.distro:
                candidates.append((Backend(kind=b.kind, distro=d,
                                           micromamba=b.micromamba, env=b.env,
                                           ca_bundle=b.ca_bundle,
                                           processes=b.processes), "discovered distro"))
    #: the first candidate carrying meep, kept in case none carries mpirun too
    fallback: tuple | None = None

    def accept(cand: "Backend", res: dict, how: str) -> tuple | None:
        """Take a candidate, or hold it while a parallel one is looked for."""
        nonlocal fallback
        if not res["available"]:
            return None
        if b.processes > 1 and not res.get("mpirun"):
            if fallback is None:
                fallback = (cand, {**res, "how": how, "tried": tried})
            return None
        return (cand, {**res, "how": how, "tried": tried})

    for cand, how in list(candidates):
        got = accept(cand, attempt(cand, how), how)
        if got:
            _RESOLVED[key] = got
            return got

    # the distributions exist and the environment name does not: search it
    base = candidates[0][0] if not candidates[1:] else candidates[1][0]
    for cand_distro in ({c.distro for c, _ in candidates} if b.kind == "wsl" else {None}):
        probe_b = Backend(kind=b.kind, distro=cand_distro or b.distro,
                          micromamba=b.micromamba, env=b.env,
                          ca_bundle=b.ca_bundle, processes=b.processes)
        names = list(COMMON_ENVS) + _env_names(probe_b)
        seen: set[str] = set()
        for name in names:
            if name in seen or name == b.env:
                continue
            seen.add(name)
            cand = Backend(kind=b.kind, distro=probe_b.distro,
                           micromamba=b.micromamba, env=name,
                           ca_bundle=b.ca_bundle, processes=b.processes)
            got = accept(cand, attempt(cand, "discovered environment"),
                         "discovered environment")
            if got:
                _RESOLVED[key] = got
                return got

    if fallback is not None:
        # meep without mpirun: a serial solve rather than none, and the caller
        # is told which it got
        _RESOLVED[key] = fallback
        return fallback

    found = (b, {"available": False, "how": "declared",
                 "reason": tried[0]["reason"] if tried else "no candidate was tried",
                 "tried": tried})
    _RESOLVED[key] = found
    return found


def probe(backend: Backend | None = None) -> dict:
    """Report whether the solver can be reached, and where it was found.

    The backend passed in is UPDATED to the distribution and environment that
    actually carry meep, so a caller holding it runs where the probe succeeded.
    The declared pair is tried first and what was tried is reported either way.

    The report names the environment that was probed as well as the outcome.
    Without it a wrong distribution name returns WSL_E_DISTRO_NOT_FOUND, which
    reads as WSL being absent from the machine and sends the reader to install
    what is already installed.
    """
    backend = backend or default_backend()
    declared = {"kind": backend.kind, "environment": backend.env,
                "launcher": backend.micromamba}
    if backend.kind == "wsl":
        declared["distro"] = backend.distro
    if backend.kind == "wsl" and shutil.which("wsl.exe") is None:
        return {"available": False, "probed": declared,
                "reason": "wsl.exe is not on PATH"}

    found, status = resolve(backend)
    res: dict = {"available": status["available"], "declared": declared,
                 "probed": {"kind": found.kind, "environment": found.env,
                            "launcher": found.micromamba,
                            **({"distro": found.distro} if found.kind == "wsl" else {})},
                 "found_by": status.get("how"),
                 "candidates_tried": len(status.get("tried", []))}

    if not status["available"]:
        reason = status.get("reason") or ""
        res["reason"] = reason
        res["tried"] = status.get("tried", [])
        if "WSL_E_DISTRO_NOT_FOUND" in reason or "no distribution" in reason.lower():
            res["hint"] = (
                f"WSL is reachable and carries no distribution named "
                f"{backend.distro!r}, and no distribution it does carry holds meep "
                f"in an environment this probe found. Run `wsl.exe -l -v` for the "
                f"names present, then set `fdtd.wsl_distro` and `fdtd.environment`, "
                f"or set {ENV_DISTRO} and {ENV_ENVIRONMENT} in the environment so "
                f"the machine is described where the design is not.")
        elif "micromamba" in reason and "No such file" in reason:
            res["hint"] = (
                f"The distribution is reachable and the launcher is absent at "
                f"{backend.micromamba}. Install micromamba there, or point "
                f"MAMBA_ROOT_PREFIX at an existing environment root.")
        return res

    # the caller runs where meep was found, not where the design guessed
    backend.distro, backend.env = found.distro, found.env
    res["version"] = status.get("version", "unknown")

    # a parallel job needs mpirun as well, and an environment can carry one
    # without the other. Degrading to one process is a slow solve; failing here
    # would be no solve at all
    if backend.processes > 1 and not status.get("mpirun"):
        res["parallel"] = False
        res["reason_serial"] = (
            f"environment {found.env!r} carries meep and no mpirun, so the solve "
            f"runs on one process rather than {backend.processes}")
        backend.processes = 1
    else:
        res["parallel"] = backend.processes > 1
    return res


def run_taper(job: dict, work_dir: Path, backend: Backend | None = None,
              timeout_s: int = 7200) -> dict:
    """Write the job, invoke the taper runner, and read the result back."""
    return _run(RUNNER, "taper", job, work_dir, backend, timeout_s)


def run_grating(job: dict, work_dir: Path, backend: Backend | None = None,
                timeout_s: int = 7200) -> dict:
    """The same, for the finite-grating reflection check."""
    return _run(GRATING_RUNNER, "grating", job, work_dir, backend, timeout_s)


def run_coupler(job: dict, work_dir: Path, backend: Backend | None = None,
                timeout_s: int = 7200) -> dict:
    """The same, for the power coupling of a ring-to-bus point coupler."""
    return _run(COUPLER_RUNNER, "coupler", job, work_dir, backend, timeout_s)


def run_mmi(job: dict, work_dir: Path, backend: Backend | None = None,
            timeout_s: int = 7200) -> dict:
    """The same, for the transmission and the balance of an MMI splitter."""
    return _run(MMI_RUNNER, "mmi", job, work_dir, backend, timeout_s)


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


def runner_digest(runner: Path) -> str:
    """A content digest of the runner script, for the reuse key.

    The runner is as much an input to the result as the job is. On 2026-09-05 a
    third simulation and four new output fields were added to the taper runner,
    and the next run returned a cached result carrying none of them, the job
    being unchanged and the key being computed over the job alone. The solve is
    deterministic in its inputs, and the code is one of them.
    """
    import hashlib

    try:
        return hashlib.sha256(runner.read_bytes()).hexdigest()[:16]
    except OSError:
        # a runner that cannot be read is a fault the solve itself will report;
        # keying on its absence merely disables reuse, which is the safe side
        return "unreadable"


def job_key(job: dict, sig: int = 10, runner: Path | None = None) -> str:
    """A content key for an external solver job, insensitive to last-bit noise.

    Two runs computing the same geometry through the same code produce job files
    that differ in the fifteenth significant figure, the evaluation order not
    being identical. Hashing the raw file therefore never matches, which is how a
    three-hour band structure came to be re-solved for a structure that had not
    changed: the period differed by 5e-16 and the group index by 2e-14.

    Floats are rounded to `sig` significant figures before hashing. Ten is far
    beyond any physical significance here and far short of the noise.

    Where `runner` is given, its content digest enters the key, so that editing
    the solver invalidates every result it produced.
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

    payload = {"job": canon(job)}
    if runner is not None:
        payload["runner"] = runner_digest(runner)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
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
    # The runner script is one of those inputs and enters the key, so editing the
    # solver invalidates every result it produced.
    # Set the environment variable PICCHAIN_NO_REUSE to force a fresh solve.
    import os

    key = job_key(job, runner=runner)
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
