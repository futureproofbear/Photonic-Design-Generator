"""The detached solver launch of the time-domain bridge.

Three long solves died on one machine with the session that started them.
With PICCHAIN_FDTD_DETACH set the solver is wrapped so that it outlives its
parent; this test states what the wrapper is, without launching anything.
"""
from __future__ import annotations

from pathlib import Path

from picchain.fdtd.bridge import Backend, detached_command, to_wsl_path


def test_the_wsl_wrapper_is_a_nohup_with_the_log_redirected_into_the_guest():
    b = Backend(kind="wsl", distro="Ubuntu", processes=4)
    cmd = b.command("/mnt/c/runner.py", "/mnt/c/job.json", "/mnt/c/out.json")
    log = Path(r"C:\runs\r1\meep_grating_run.log")
    d = detached_command(b, cmd, log)
    assert d[:4] == cmd[:4]                            # wsl.exe -d Ubuntu --, unchanged
    assert d[4:8] == ["setsid", "-f", "bash", "-lc"]  # a session of its own, forked
    assert d[-1].startswith(cmd[-1]) and to_wsl_path(log) in d[-1] and "2>&1" in d[-1] and "< /dev/null" in d[-1]


def test_a_native_backend_is_left_to_the_caller():
    b = Backend(kind="native", processes=2)
    cmd = b.command("runner.py", "job.json", "out.json")
    assert detached_command(b, cmd, Path("x.log")) == cmd
