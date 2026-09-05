"""The FDTD stage measures a multimode splitter, and its monitors stay apart.

The splitter is drawn by the layout stage and was evaluated by nothing. Its
excess loss enters both arms of an interferometer and its imbalance bounds the
extinction the device can reach whatever the phase control does.

The monitor width is the property held most carefully here. Set to the port
separation, each monitor plane reaches the neighbouring guide's centre line, the
eigenmode decomposition then solves the modes of a two-guide cross-section, and
band one is a supermode rather than the isolated port. The transmission then
falls as the mesh refines, because the supermode is resolved better, and reads
as a device that loses power.

The solver is not exercised here, meep living in another environment. What is
exercised is the job the stage builds, the arithmetic it performs on the result,
and the findings it raises.
"""

from __future__ import annotations

import pytest

from picchain.config import Design, FDTDCfg
from picchain.stages import s09_fdtd


class _Ctx:
    def __init__(self):
        self.metrics: dict = {}
        self.stages: dict = {}
        self.warnings: list[tuple[str, str]] = []
        self.run_dir = None

    def put(self, k, v):
        self.metrics[k] = v

    def get(self, k):
        return self.metrics.get(k)

    def write_stage(self, k, v):
        self.stages[k] = v

    def warn(self, message, key=None, **_):
        self.warnings.append((key, message))


class _Backend:
    kind = "wsl"


def _design(width=0.7, sep=3.9, ports=2, **fdtd) -> Design:
    return Design.model_validate({
        "meta": {"name": "mmi_probe", "title": "A multimode splitter"},
        "waveguide": {"top_width_um": width, "wavelength_um": 1.31},
        "grating": {"enabled": False},
        "mzm": {"mmi_width_um": 5.65, "mmi_length_um": 97.5,
                "port_width_um": 1.75, "port_separation_um": sep},
        "fdtd": {"enabled": True, "structure": "mmi", "mmi_ports_in": ports, **fdtd},
    })


def _result(ports=(0.49, 0.49), reflection=1e-5, guard_shift=-0.01):
    n = 5
    out = {
        "ok": True,
        "resolution": 50,
        "wavelength_um": [1.35, 1.33, 1.31, 1.29, 1.27],
        "port_transmission": [[p] * n for p in ports],
        "reflection": [reflection] * n,
        "accounted": [sum(ports) + reflection] * n,
        "imbalance_dB": [0.0] * n,
        "transmission_at_design": sum(ports),
        "excess_loss_dB_at_design": 0.0,
        "imbalance_dB_at_design": 0.0,
        "reflection_at_design": reflection,
        "accounted_at_design": sum(ports) + reflection,
    }
    if guard_shift is not None:
        out["guard"] = {"resolution": 25,
                        "transmission_at_design": sum(ports) * (1 - guard_shift),
                        "shift_fraction": guard_shift}
    return out


def _run(monkeypatch, design, result):
    seen: dict = {}

    def fake(job, work_dir, backend=None, timeout_s=0):
        seen.update(job)
        return result

    monkeypatch.setattr(s09_fdtd.bridge, "run_mmi", fake)
    ctx = _Ctx()
    payload = s09_fdtd._run_mmi(design, ctx, design.fdtd, backend=_Backend(),
                               status={"version": "1.34.0"},
                               n_core=1.8459, n_clad=1.5864)
    return payload, ctx, seen


def test_the_structure_is_accepted():
    assert FDTDCfg(structure="mmi").structure == "mmi"


@pytest.mark.parametrize("width,sep", [(0.7, 3.9), (0.9, 3.65), (0.7, 2.45), (0.9, 2.55)])
def test_the_monitor_never_reaches_the_neighbouring_port(monkeypatch, width, sep):
    """Half the separation is where the next guide's centre line sits."""
    _, _, job = _run(monkeypatch, _design(width=width, sep=sep), _result())
    assert job["port_width_monitor_um"] < sep, "the monitor spans the whole separation"
    assert job["port_width_monitor_um"] / 2 < sep / 2
    # and it is still wide enough to hold the mode it is decomposing
    assert job["port_width_monitor_um"] > 2.0 * width


def test_the_job_carries_the_geometry_the_layout_declares(monkeypatch):
    d = _design()
    _, _, job = _run(monkeypatch, d, _result())
    assert job["mmi_width_um"] == d.mzm.mmi_width_um
    assert job["mmi_length_um"] == d.mzm.mmi_length_um
    assert job["port_width_um"] == d.mzm.port_width_um
    assert job["port_separation_um"] == d.mzm.port_separation_um
    assert job["n_background"] == pytest.approx(1.5864)


def test_power_above_unity_is_reported(monkeypatch):
    _, ctx, _ = _run(monkeypatch, _design(), _result(ports=(0.52, 0.52)))
    assert "fdtd.mmi_gain" in [k for k, _ in ctx.warnings]


def test_a_shortfall_is_reported_as_radiation(monkeypatch):
    _, ctx, _ = _run(monkeypatch, _design(), _result(ports=(0.40, 0.40)))
    assert "fdtd.mmi_radiates" in [k for k, _ in ctx.warnings]


def test_an_imbalance_is_reported(monkeypatch):
    r = _result(ports=(0.55, 0.40))
    r["imbalance_dB_at_design"] = 1.38
    _, ctx, _ = _run(monkeypatch, _design(), r)
    assert "fdtd.mmi_imbalanced" in [k for k, _ in ctx.warnings]


def test_an_unconverged_mesh_is_reported(monkeypatch):
    _, ctx, _ = _run(monkeypatch, _design(), _result(guard_shift=-0.13))
    assert "fdtd.mmi_unconverged" in [k for k, _ in ctx.warnings]


def test_a_converged_guard_resolves(monkeypatch):
    payload, _, _ = _run(monkeypatch, _design(), _result(guard_shift=-0.01))
    assert payload["convergence"]["resolved"] is True
