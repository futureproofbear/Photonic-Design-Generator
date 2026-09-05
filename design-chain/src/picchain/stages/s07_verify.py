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

    # Raised here rather than at the end of the stage, so that the accounting
    # below counts it. It is a finding about the DESIGN and not about the
    # accounting, and it was previously invisible to the very mechanism that
    # exists to leave no finding unowned.
    if unconfirmed:
        ctx.warn(
            "materials with unconfirmed data in this design: " + ", ".join(unconfirmed)
            + " - results are indicative until foundry PCM data replaces them",
            key="verify.materials_unconfirmed_data_design",
        )

    # --- findings, against what the design has acknowledged -----------------
    #
    # The acceptance verdict grades targets. A chain also raises findings that
    # carry no threshold, and until 2026-08-17 nothing read them: a run could
    # emit seventeen and still be reported a clean pass. They are counted here so
    # that the verdict carries its denominator, and so that a finding appearing
    # for the first time is visible in the same place the targets are.
    #
    # Enforcement is opt-in per design. Reporting first is deliberate: turning it
    # on before the standing findings are acknowledged would fail every released
    # design at once and teach the reader to bypass the gate.
    acked = {a.key: a.reason for a in design.warnings.acknowledged}
    # Only the two findings that are ABOUT this accounting are held out of it.
    # Counting them would be self-referential: reporting an unacknowledged
    # finding is itself a finding, which would never reach zero.
    #
    # The filter was previously by stage, which excluded every finding the verify
    # stage raises whatever it was about. The unconfirmed-material finding is a
    # statement about the design rather than about the count, and it was dropped
    # with the rest, so the standing caveat that a design's material data is not
    # the foundry's went unowned and unreported in the one place the denominator
    # is quoted.
    META = {"verify.findings_unacknowledged", "verify.acknowledgements_stale",
            "verify.acknowledgements_stage_not_run"}
    emitted = [w for w in ctx.warning_records if w["key"] not in META]
    seen = {w["key"] for w in emitted}
    unacknowledged = sorted(seen - set(acked))

    # An acknowledgement is stale where the finding it names was fixed or
    # reworded. It is NOT stale merely because the stage that raises it was left
    # out of the run.
    #
    # A key is `<stage>.<slug>`, so the stage that owns each acknowledgement is
    # read from the key and compared against the stages this run executed. A
    # design whose `stages:` line omits the layout stages reported six stale
    # entries on a run that had simply not drawn a mask, and a check that cries
    # wolf on a partial run is a check a reader learns to skip.
    ran = set(getattr(ctx, "stages_run", None) or ctx.metrics.keys())
    def _stage_of(key: str) -> str:
        return key.split(".", 1)[0] if "." in key else key
    not_run = sorted(k for k in set(acked) - seen if _stage_of(k) not in ran)
    stale = sorted(k for k in set(acked) - seen if _stage_of(k) in ran)
    enforce = bool(getattr(design.warnings, "enforce", False))

    payload = {
        "n_targets": len(rows),
        "n_pass": sum(1 for r in rows if r["status"] == "pass"),
        "n_fail": sum(1 for r in rows if r["status"] == "fail"),
        "n_missing": sum(1 for r in rows if r["status"] == "missing"),
        "must_failures": n_must_fail,
        "should_failures": n_should_fail,
        "unconfirmed_materials": unconfirmed,
        "blocked_on_materials": blocked,
        "findings_emitted": len(seen),
        "findings_acknowledged": len(seen & set(acked)),
        "findings_unacknowledged": unacknowledged,
        "findings_acknowledged_but_absent": stale,
        # acknowledgements whose stage this run did not execute, so nothing is
        # established about them either way
        "findings_acknowledged_stage_not_run": not_run,
        "findings_enforced": enforce,
        "verdict": ("PASS" if (n_must_fail == 0 and not blocked
                               and not (enforce and unacknowledged)) else "FAIL"),
        "rows": rows,
    }
    ctx.put("verify", payload)
    ctx.write_stage("verify", payload)
    if unacknowledged:
        ctx.warn(
            f"{len(unacknowledged)} finding(s) this run emitted are acknowledged by "
            f"no entry in the design file: " + ", ".join(unacknowledged)
            + ". A finding with no threshold has no owner unless the design names "
            "it, so each is either accepted with a reason under warnings."
            "acknowledged or is a defect to be fixed",
            key="verify.findings_unacknowledged",
        )
    if stale:
        ctx.warn(
            f"{len(stale)} acknowledgement(s) in the design file match no finding "
            f"this run emitted: " + ", ".join(stale)
            + ". Either the finding was fixed and the entry should go, or its "
            "wording changed and the key with it",
            key="verify.acknowledgements_stale",
        )
    if not_run:
        ctx.warn(
            f"{len(not_run)} acknowledgement(s) name a stage this run did not "
            f"execute, so they were neither confirmed nor cleared: "
            + ", ".join(not_run)
            + ". A run that omits stages establishes what those stages would "
            "have found, and a release is to be assembled from a run of the "
            "whole chain",
            key="verify.acknowledgements_stage_not_run",
        )
    return payload
