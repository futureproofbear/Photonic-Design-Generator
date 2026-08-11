"""Stage 7 - verification against declared acceptance targets.

Every design file carries a ``targets:`` list.  Each target names a dotted path
into the metric tree and a criterion (value+tolerance, min, or max).  This stage
evaluates them all and produces a signed-off table.  The CLI exit code is
non-zero when any ``must`` target fails, which is what lets an agent (or CI)
iterate on a design without a human reading a plot.
"""

from __future__ import annotations

import math
from typing import Any

from ..artifacts import RunContext
from ..config import Design, Target
from ..materials import MaterialLibrary


def _evaluate(t: Target, actual: float | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "metric": t.metric, "unit": t.unit, "severity": t.severity,
        "source": t.source, "actual": actual,
    }
    if actual is None or (isinstance(actual, float) and math.isnan(actual)):
        row.update(criterion=_criterion_text(t), status="missing")
        return row
    ok = True
    if t.value is not None:
        tol = None
        if t.rel_tol is not None:
            tol = abs(t.value) * t.rel_tol
        if t.abs_tol is not None:
            tol = t.abs_tol if tol is None else max(tol, t.abs_tol)
        if tol is None:
            tol = abs(t.value) * 0.05
        ok &= abs(actual - t.value) <= tol
        row["deviation"] = actual - t.value
        row["deviation_pct"] = (actual - t.value) / t.value * 100 if t.value else None
    if t.min is not None:
        ok &= actual >= t.min
    if t.max is not None:
        ok &= actual <= t.max
    row.update(criterion=_criterion_text(t), status="pass" if ok else "fail")
    return row


def _criterion_text(t: Target) -> str:
    parts = []
    if t.value is not None:
        tol = f" +-{t.rel_tol*100:.0f}%" if t.rel_tol is not None else (
            f" +-{t.abs_tol}" if t.abs_tol is not None else " +-5%")
        parts.append(f"= {t.value}{tol}")
    if t.min is not None:
        parts.append(f">= {t.min}")
    if t.max is not None:
        parts.append(f"<= {t.max}")
    return " and ".join(parts) or "(none)"


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    rows = [_evaluate(t, ctx.get(t.metric)) for t in design.targets]

    n_must_fail = sum(1 for r in rows if r["severity"] == "must" and r["status"] in ("fail", "missing"))
    n_should_fail = sum(1 for r in rows if r["severity"] == "should" and r["status"] in ("fail", "missing"))

    # material-provenance gate
    used = [design.platform.film_material, design.platform.clad_material,
            design.platform.box_material, design.platform.substrate_material,
            design.electrodes.material]
    unconfirmed = lib.unconfirmed(used)
    blocked = bool(unconfirmed) and not design.allow_unconfirmed_materials

    payload = {
        "n_targets": len(rows),
        "n_pass": sum(1 for r in rows if r["status"] == "pass"),
        "n_fail": sum(1 for r in rows if r["status"] == "fail"),
        "n_missing": sum(1 for r in rows if r["status"] == "missing"),
        "must_failures": n_must_fail,
        "should_failures": n_should_fail,
        "unconfirmed_materials": unconfirmed,
        "blocked_on_materials": blocked,
        "verdict": "PASS" if (n_must_fail == 0 and not blocked) else "FAIL",
        "rows": rows,
    }
    ctx.put("verify", payload)
    ctx.write_stage("verify", payload)
    if unconfirmed:
        ctx.warn(
            "materials with unconfirmed data in this design: " + ", ".join(unconfirmed)
            + " - results are indicative until foundry PCM data replaces them"
        )
    return payload
