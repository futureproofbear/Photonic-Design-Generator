"""The FDTD stage measures a point coupler, and the measurement is closed-form checked.

The power coupling of a ring-to-bus coupler was measurable only by a script
written beside a study, so the result carried no run identity, no metric tree
and no acceptance target. It is now a structure of stage 9.

The solver itself is not exercised here, meep living in another environment.
What is exercised is the wiring: the job the stage builds, the metrics it
publishes, the arithmetic it performs on the result, and the findings it raises.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from picchain.config import Design, FDTDCfg
from picchain.stages import s09_fdtd


class _Ctx:
    """The parts of a run context this stage touches."""

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


def _design(**fdtd) -> Design:
    d = Design.model_validate({
        "meta": {"name": "coupler_probe", "title": "A point coupler"},
        "waveguide": {"top_width_um": 0.7, "wavelength_um": 1.31},
        "grating": {"enabled": False},
        "fdtd": {"enabled": True, "structure": "coupler", **fdtd},
    })
    return d


def _result(kappa2: float, unitarity: float = 1.0, guard_shift: float | None = -0.02):
    n = 5
    k = [kappa2] * n
    out = {
        "ok": True,
        "resolution": 50,
        "wavelength_um": [1.35, 1.33, 1.31, 1.29, 1.27],
        "kappa2": k,
        "t2": [unitarity - kappa2] * n,
        "unitarity": [unitarity] * n,
        "kappa2_at_design": kappa2,
        "t2_at_design": unitarity - kappa2,
        "unitarity_at_design": unitarity,
    }
    if guard_shift is not None:
        out["guard"] = {
            "resolution": 25,
            "kappa2_at_design": kappa2 * (1.0 - guard_shift),
            "shift_fraction": guard_shift,
        }
    return out


def _run(monkeypatch, design, result):
    seen: dict = {}

    def fake(job, work_dir, backend=None, timeout_s=0):
        seen.update(job)
        return result

    monkeypatch.setattr(s09_fdtd.bridge, "run_coupler", fake)
    ctx = _Ctx()
    payload = s09_fdtd._run_coupler(
        design, ctx, design.fdtd, backend=_Backend(), status={"version": "1.34.0"},
        n_core=1.8459, n_clad=1.5864)
    return payload, ctx, seen


class _Backend:
    kind = "wsl"


def test_the_structure_is_accepted():
    assert FDTDCfg(structure="coupler").structure == "coupler"


def test_the_job_carries_the_declared_geometry(monkeypatch):
    d = _design(coupler_gap_um=1.05, coupler_ring_radius_um=200.0,
                coupler_bandwidth_frac=0.04)
    _, _, job = _run(monkeypatch, d, _result(0.009))
    assert job["gap_um"] == 1.05
    assert job["ring_radius_um"] == 200.0
    assert job["width_um"] == 0.7
    assert job["n_core"] == pytest.approx(1.8459)
    # the background is the slab beside the ridge, never the cladding
    assert job["n_background"] == pytest.approx(1.5864)
    assert job["lambda_min_um"] == pytest.approx(1.31 * 0.96)
    assert job["lambda_max_um"] == pytest.approx(1.31 * 1.04)


def test_the_critical_loss_is_the_loss_that_matches_the_coupling(monkeypatch):
    """Closed form: at critical coupling the round trip loses exactly kappa^2."""
    kappa2, radius = 0.009045, 200.0
    d = _design(coupler_gap_um=1.05, coupler_ring_radius_um=radius)
    payload, _, _ = _run(monkeypatch, d, _result(kappa2))

    alpha_dB_cm = payload["critical_coupling_loss_dB_cm"]
    circumference_cm = 2.0 * math.pi * radius * 1e-4
    round_trip = 10 ** (-alpha_dB_cm * circumference_cm / 10.0)
    assert 1.0 - round_trip == pytest.approx(kappa2, rel=1e-9)


def test_a_shortfall_in_the_two_ports_is_reported(monkeypatch):
    d = _design()
    _, ctx, _ = _run(monkeypatch, d, _result(0.009, unitarity=0.95))
    assert any(k == "fdtd.coupler_unitarity" for k, _ in ctx.warnings)


def test_an_unconverged_mesh_is_reported(monkeypatch):
    d = _design()
    _, ctx, _ = _run(monkeypatch, d, _result(0.009, guard_shift=-0.4))
    keys = [k for k, _ in ctx.warnings]
    assert "fdtd.coupler_unconverged" in keys


def test_a_solve_without_a_guard_is_reported(monkeypatch):
    d = _design()
    payload, ctx, _ = _run(monkeypatch, d, _result(0.009, guard_shift=None))
    assert payload["convergence"]["guarded"] is False
    assert "fdtd.coupler_unguarded" in [k for k, _ in ctx.warnings]


def test_a_converged_guard_resolves(monkeypatch):
    d = _design()
    payload, _, _ = _run(monkeypatch, d, _result(0.009, guard_shift=-0.026))
    assert payload["convergence"]["resolved"] is True
    assert payload["convergence"]["coarse_resolution"] == 25


def test_the_plane_reduction_declares_its_limit(monkeypatch):
    d = _design(dimensions=2)
    _, ctx, _ = _run(monkeypatch, d, _result(0.009))
    assert "fdtd.coupler_two_dimensional" in [k for k, _ in ctx.warnings]


def test_the_ring_may_be_wider_than_the_bus(monkeypatch):
    """A multimode ring is drawn wider, and the job must carry both widths.

    The kit pairs a 0.7 um bus with a 1.5 um ring on its multimode cells. Where
    the job carries one width the runner draws two identical guides, the coupler
    is synchronous, and the coupling reported belongs to a device the mask does
    not contain.
    """
    d = _design(coupler_gap_um=0.75, coupler_ring_width_um=1.5,
                coupler_cross_bands=3)
    _, _, job = _run(monkeypatch, d, _result(0.02))
    assert job["ring_width_um"] == 1.5
    assert job["width_um"] == 0.7
    assert job["cross_bands"] == 3


def test_a_ring_width_left_unset_leaves_the_two_guides_equal(monkeypatch):
    d = _design(coupler_gap_um=1.05)
    _, _, job = _run(monkeypatch, d, _result(0.009))
    assert job["ring_width_um"] is None, "unset means the runner takes the bus width"
    assert job["cross_bands"] == 1


def test_the_payload_states_the_ring_width_it_solved(monkeypatch):
    d = _design(coupler_gap_um=0.75, coupler_ring_width_um=1.5)
    payload, _, _ = _run(monkeypatch, d, _result(0.02))
    assert payload["ring_width_um"] == 1.5
