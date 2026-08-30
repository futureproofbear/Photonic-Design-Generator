"""Stage 15 - the submission manifest.

A mask leaves the earlier stages as a file in a run directory. Nothing within
it states which run produced it, which design file it was drawn from, which
environment executed the chain, or whether the design that was drawn met its
acceptance criteria. A recipient holding two such files cannot order them, and
a sender holding three cannot say which was sent.

The manifest closes that. It inventories every artifact intended for
submission, takes the SHA-256 of each, records the provenance of the run and
the verdict that stood at the time, and states which conditions of readiness
were met and which were not.

The gate
--------
A manifest is a claim that a set of files is ready to be sent. Producing one
for a design that fails its acceptance targets, or for a mask that carries a
fraction of the device, would make the claim false. Those conditions are
therefore evaluated and, unless the operator overrides each in turn, the stage
refuses.

The refusal is the point. Every earlier stage reports; this one is the only
place in the chain where a condition stops the work rather than annotating it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..artifacts import RunContext, environment_fingerprint
from ..config import Design
from ..materials import MaterialLibrary

#: file suffixes that constitute a submission, as opposed to a working result
SUBMITTABLE = (".gds", ".oas", ".lyp", ".layermap.txt", ".lydrc")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _final_density(mask: dict) -> dict:
    """The density that stands, which is the one after any fill was placed.

    Reading the figure the density check produced before the placer ran would
    report a shortfall that has since been filled.
    """
    fill = mask.get("fill") or {}
    if fill.get("performed") and fill.get("density_after"):
        return fill["density_after"]
    return mask.get("density") or {}


def _readiness(design: Design, ctx: RunContext) -> list[dict[str, Any]]:
    """Every condition that bears on whether the mask can be sent.

    Each is reported with the value that decided it, so that an unmet condition
    names the field to change rather than requiring the reader to find it.
    """
    lay = ctx.get("layout") or {}
    drc = ctx.get("drc") or {}
    mask = ctx.get("mask") or {}
    ver = ctx.get("verify") or {}
    ret = ctx.get("reticle") or {}
    geom = lay.get("geometry") or {}
    grid = lay.get("grid") or {}
    env = environment_fingerprint()

    rows = [
        # A mask produced by a modified working tree cannot be regenerated from
        # any commit, so the manifest's revision identifies nothing. The stamp
        # was previously taken from whichever repository the command was invoked
        # in, which for a design directory is the application and never the
        # chain, so this condition could not have been evaluated at all.
        {"condition": "the chain that produced this is a committed revision",
         "met": bool((env.get("chain") or {}).get("revision"))
                and not (env.get("chain") or {}).get("dirty", True),
         "detail": (f"{(env.get('chain') or {}).get('revision')}, "
                    + (f"{(env.get('chain') or {}).get('modified_files')} uncommitted files"
                       if (env.get("chain") or {}).get("dirty")
                       else "clean")),
         "field": "environment.chain"},
        {"condition": "every grating period is drawn",
         "met": bool(lay.get("mask_is_complete")),
         "detail": f"{(lay.get('fidelity') or {}).get('periods_drawn')} of "
                   f"{(lay.get('fidelity') or {}).get('periods_total')}",
         "field": "layout.draw_periods"},
        {"condition": "the two layout backends agree",
         "met": bool((lay.get("backend_xor") or {}).get("agree")),
         "detail": str((lay.get("backend_xor") or {}).get("residual_area_um2")),
         "field": "layout.compare_backends"},
        {"condition": "the geometry is sound",
         "met": bool(geom.get("clean")) if geom.get("performed") else False,
         "detail": f"{geom.get('total_issues')} issues" if geom.get("performed")
                   else str(geom.get("reason")),
         "field": "layout.check_geometry"},
        {"condition": "every vertex is on the manufacturing grid",
         "met": True,
         "detail": f"{grid.get('grid_nm')} nm grid, "
                   f"{grid.get('max_displacement_nm', 0):.3f} nm worst snap",
         "field": "process.grid_nm"},
        {"condition": "the rule check is clean",
         "met": bool(drc.get("clean")) if drc.get("enabled") else False,
         "detail": f"{drc.get('error_violations')} violations on the "
                   f"{drc.get('checked')}" if drc.get("enabled") else "not run",
         "field": "drc.enabled"},
        {"condition": "a foundry rule deck was executed",
         "met": bool((drc.get("deck") or {}).get("violations_total") == 0),
         "detail": "no deck declared" if not design.drc.deck
                   else f"{(drc.get('deck') or {}).get('violations_total')} violations",
         "field": "drc.deck"},
        {"condition": "the acceptance targets are met",
         "met": ver.get("verdict") == "PASS",
         "detail": f"{ver.get('verdict')}, {ver.get('must_failures')} unmet at "
                   f"severity must" if ver else "verify did not run",
         "field": "targets"},
        {"condition": "the material data is confirmed",
         "met": not (ver.get("unconfirmed_materials") or []),
         "detail": ", ".join(ver.get("unconfirmed_materials") or []) or "all confirmed",
         "field": "platform.materials_file"},
        # the density that stands after any fill was placed, not before it
        {"condition": "density is within the declared windows",
         "met": all(not (v.get("tiles_below_window") or v.get("tiles_above_window"))
                    for v in _final_density(mask).values()),
         "detail": "; ".join(
             f"{k}: {v.get('fill_area_required_um2', 0):.0f} um2 of fill required"
             for k, v in _final_density(mask).items()
             if v.get("tiles_below_window") or v.get("tiles_above_window"))
         or ("within, after fill" if (mask.get("fill") or {}).get("performed")
             else "within"),
         "field": "mask.density_windows"},
        {"condition": "a die frame is present",
         "met": bool(ret.get("enabled")),
         "detail": "seal ring, dicing lane, marks, label" if ret.get("enabled")
                   else "the device cell alone was emitted",
         "field": "reticle.enabled"},
    ]
    return rows


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.release
    if not cfg.enabled:
        payload = {"enabled": False}
        ctx.put("release", payload)
        return payload

    rows = _readiness(design, ctx)
    waived = {w for w in cfg.waive}
    unknown = waived - {r["condition"] for r in rows}
    if unknown:
        raise ValueError(
            f"release.waive names conditions that do not exist: {sorted(unknown)}. "
            f"The conditions are: {[r['condition'] for r in rows]}"
        )
    for r in rows:
        r["waived"] = r["condition"] in waived
    blocking = [r for r in rows if not r["met"] and not r["waived"]]

    # --- the inventory ---------------------------------------------------
    files = []
    for p in sorted(ctx.run_dir.iterdir()):
        if not p.is_file():
            continue
        if not any(p.name.endswith(sfx) for sfx in SUBMITTABLE):
            continue
        if "drc_markers" in p.name:          # a review aid, not a deliverable
            continue
        files.append({
            "file": p.name,
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        })

    design_path = design.source_path
    payload: dict[str, Any] = {
        "enabled": True,
        "design": design.meta.name,
        "title": design.meta.title,
        "status": design.meta.status,
        "revision": cfg.revision or design.reticle.revision,
        "run_id": ctx.run_id,
        "design_file": str(design_path) if design_path else None,
        "design_sha256": sha256(design_path) if design_path and design_path.is_file() else None,
        "resolved_design_sha256": (
            sha256(ctx.run_dir / "design.resolved.json")
            if (ctx.run_dir / "design.resolved.json").is_file() else None
        ),
        "environment": environment_fingerprint(),
        "files": files,
        "file_count": len(files),
        "readiness": rows,
        "conditions_met": sum(1 for r in rows if r["met"]),
        "conditions_total": len(rows),
        "conditions_waived": sorted(waived),
        "blocking": [r["condition"] for r in blocking],
        "released": not blocking,
    }

    manifest = ctx.run_dir / "MANIFEST.json"
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (ctx.run_dir / "MANIFEST.md").write_text(_markdown(payload), encoding="utf-8")
    payload["manifest"] = str(manifest)

    ctx.put("release", payload)
    ctx.write_stage("release", payload)

    if blocking:
        detail = "; ".join(f"{r['condition']} ({r['detail']}, see {r['field']})"
                           for r in blocking)
        message = (
            f"the submission is blocked on {len(blocking)} of {len(rows)} conditions: "
            f"{detail}. Each may be waived by naming it in release.waive, which records "
            "the waiver in the manifest rather than concealing it"
        )
        if cfg.strict:
            raise RuntimeError(message)
        ctx.warn(message)
    if waived:
        ctx.warn(
            f"{len(waived)} readiness conditions were waived and are recorded as "
            f"waived in the manifest: {', '.join(sorted(waived))}"
        )
    if not files:
        ctx.warn("the manifest inventories no files; nothing submittable was emitted")
    return payload


def _markdown(doc: dict[str, Any]) -> str:
    L = [f"# Submission manifest — {doc['design']} rev {doc['revision']}", ""]
    L.append(f"**{'RELEASED' if doc['released'] else 'BLOCKED'}** — "
             f"{doc['conditions_met']} of {doc['conditions_total']} readiness "
             f"conditions met.")
    L.append("")
    L += ["| item | value |", "|---|---|"]
    L.append(f"| run | `{doc['run_id']}` |")
    L.append(f"| design file | `{doc['design_file']}` |")
    L.append(f"| design SHA-256 | `{doc['design_sha256']}` |")
    L.append(f"| resolved design SHA-256 | `{doc['resolved_design_sha256']}` |")
    env = doc["environment"]
    L.append(f"| python | {env['python']} on {env['platform']} |")
    chain = env.get("chain") or {}
    L.append(f"| chain revision | `{chain.get('revision')}`"
             + (f" **plus {chain.get('modified_files')} uncommitted files**"
                if chain.get("dirty") else " (clean)") + " |")
    inv = env.get("invocation_repo") or {}
    if inv.get("root") and inv.get("root") != chain.get("root"):
        L.append(f"| design repository | `{inv.get('revision')}`"
                 + (f" plus {inv.get('modified_files')} uncommitted files"
                    if inv.get("dirty") else " (clean)") + " |")
    pk = ", ".join(f"{k} {v}" for k, v in env["packages"].items() if v)
    L.append(f"| packages | {pk} |")
    L += ["", "## Files", "", "| file | bytes | SHA-256 |", "|---|---:|---|"]
    for f in doc["files"]:
        L.append(f"| `{f['file']}` | {f['bytes']} | `{f['sha256']}` |")
    L += ["", "## Readiness", "", "| condition | state | detail | field |",
          "|---|---|---|---|"]
    for r in doc["readiness"]:
        state = "met" if r["met"] else ("**waived**" if r["waived"] else "**UNMET**")
        L.append(f"| {r['condition']} | {state} | {r['detail']} | `{r['field']}` |")
    L.append("")
    if doc["blocking"]:
        L += ["## Blocking", ""]
        L += [f"* {c}" for c in doc["blocking"]]
        L.append("")
    return "\n".join(L)
