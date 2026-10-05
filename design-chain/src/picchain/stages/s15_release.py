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
    labels = (mask.get("labels") or {}) if isinstance(mask, dict) else {}
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
        # Named for whatever the device's mask can be a fraction of. A grating is
        # drawn a period at a time and an interferometer is not, so on a device
        # with no grating this read "None of None" and passed: a condition that
        # cannot go red is worse than an absent one, being counted in the total.
        {"condition": ("every grating period is drawn" if lay.get("device") != "mach_zehnder"
                       else "the drawn electrode is the electrode that was solved"),
         "met": bool(lay.get("mask_is_complete")),
         "detail": (f"{(lay.get('fidelity') or {}).get('periods_drawn')} of "
                    f"{(lay.get('fidelity') or {}).get('periods_total')}"
                    if lay.get("device") != "mach_zehnder" else
                    f"{(lay.get('fidelity') or {}).get('electrode_length_drawn_um')} um drawn "
                    f"against {(lay.get('fidelity') or {}).get('electrode_length_simulated_um')} um solved"),
         "field": ("layout.draw_periods" if lay.get("device") != "mach_zehnder"
                   else "electrodes.length_um")},
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
         # judged outside the declared monitor field, where the monitors draw
         # below the rules on purpose; the in-process check is judged the same
         # way (2026-10-06). A deck result without the field classification is
         # judged on its total.
         "met": bool(_deck_outside(drc) == 0),
         "detail": "no deck declared" if not design.drc.deck
                   else (f"{(drc.get('deck') or {}).get('violations_total')} violations, "
                         f"{(drc.get('deck') or {}).get('violations_in_monitor_field_total', 0)} of them "
                         "in the declared monitor field"),
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
        # A window that was never declared was never checked, and `all()` over
        # nothing is true. A design declaring no density window reported this
        # condition met, with the detail "within", having measured nothing
        # against nothing. Silence from a check that did not run is recorded as
        # silence and may be waived with a reason like any other.
        {"condition": "density is within the declared windows",
         "met": bool(_final_density(mask)) and all(
             not (v.get("tiles_below_window") or v.get("tiles_above_window"))
             for v in _final_density(mask).values()),
         "detail": ("no density window is declared, so nothing was measured"
                    if not _final_density(mask) else
                    "; ".join(
                        f"{k}: {v.get('fill_area_required_um2', 0):.0f} um2 of fill required"
                        for k, v in _final_density(mask).items()
                        if v.get("tiles_below_window") or v.get("tiles_above_window"))
                    or ("within, after fill"
                        if (mask.get("fill") or {}).get("performed") else "within")),
         "field": "mask.density_windows"},
        {"condition": "a die frame is present",
         "met": bool(ret.get("enabled")),
         "detail": "seal ring, dicing lane, marks, label" if ret.get("enabled")
                   else "the device cell alone was emitted",
         "field": "reticle.enabled"},

        # The four below answer a pre-submission review rather than a solver.
        # Each costs the measurement or the submission rather than the wafer,
        # which is why neither a rule deck nor a connectivity check reports one.
        # `rules/generic/design-review.md` carries the list they come from.
        {"condition": "every text label is unique",
         "met": bool(labels.get("unique")),
         "detail": (f"{labels.get('count')} labels, {labels.get('distinct')} distinct"
                    + (f", duplicated: {', '.join(labels['duplicated'][:5])}"
                       if labels.get("duplicated") else "")
                    if labels.get("performed") and labels.get("count")
                    else "no text object was written, so uniqueness is vacuous"),
         "field": "mask.labels"},
        {"condition": "the mask carries a label for every device the layout names",
         "met": bool(_devices_labelled(lay, labels)[0]),
         "detail": _devices_labelled(lay, labels)[1],
         "field": "layout.labels"},
        {"condition": "the emitted files and the top cell carry the design's name",
         "met": _naming(design, ctx)[0],
         "detail": _naming(design, ctx)[1],
         "field": "meta.name"},
        {"condition": "no feature sits within the rule margin",
         "met": _margin_met(drc),
         "detail": _margin_detail(drc),
         "field": "drc.margin_fraction"},
    ]
    return rows


def _deck_outside(drc: dict) -> int | None:
    """The deck's violations outside the declared monitor field, or its total
    where the result carries no classification, or None where it did not run."""
    d = drc.get("deck") or {}
    if "violations_outside_monitor_field_total" in d:
        return int(d["violations_outside_monitor_field_total"])
    if "violations_total" in d:
        return int(d["violations_total"])
    return None


def _margin_met(drc: dict) -> bool:
    """Whether the mask carries no feature in the band above the rule.

    A margin that was never evaluated is reported as unmet. `drc.at_the_limit`
    is `None` where `drc.margin_fraction` is zero or the stage did not run, and
    reading that as a clean margin would be a condition passing because nothing
    was measured.
    """
    at_limit = drc.get("at_the_limit")
    return at_limit == 0 if at_limit is not None else False


def _margin_detail(drc: dict) -> str:
    at_limit = drc.get("at_the_limit")
    if at_limit is None:
        return "no margin was evaluated"
    pct = (drc.get("margin_fraction") or 0) * 100
    return (f"{at_limit} features clear every rule and fail it widened by "
            f"{pct:.0f} per cent")

def _devices_labelled(lay: dict, labels: dict) -> tuple[bool, str]:
    """Whether every device name the layout declares appears in a written label.

    The layout stage records the names it gave the devices it placed. A station
    that measures by label can reach only the devices whose names were written
    into the mask, so a name declared and never written is a device nobody
    measures.
    """
    declared = [str(n) for n in (lay.get("labels") or []) if str(n).strip()]
    if not declared:
        return False, ("the layout declares no device name, so nothing can be matched. "
                       "Name the devices in the block that places them, and draw the "
                       "names with reticle.split.label_each or "
                       "reticle.companions.label_each")
    if not labels.get("performed"):
        return False, "no label inventory was taken"
    written = chr(10).join(labels.get("texts") or [])
    missing = [n for n in declared if n not in written]
    if missing:
        return False, (f"{len(declared) - len(missing)} of {len(declared)} device names "
                       f"appear in a label; missing: {', '.join(missing[:5])}")
    return True, f"all {len(declared)} device names appear in a written label"


def _naming(design: Design, ctx: RunContext) -> tuple[bool, str]:
    """Whether the top cell and the emitted files carry the declared name.

    A submission is identified by its file and its cell, and the two drift apart
    silently. In one flow examined for this check the published verification
    named a file that no longer existed, the layout program having been changed
    to write a differently named top cell; every number in the report described
    a mask nobody had.
    """
    name = design.meta.name
    pattern = design.release.name_pattern
    problems = []

    # The comparison is case-insensitive. A die cell is conventionally the
    # design name uppercased with a suffix, and a case-sensitive test called
    # that a mismatch on the first design it ran against: `meta.name` of
    # `ltoi300_mzm_testchip` against a top cell `LTOI300_MZM_TESTCHIP_DIE`,
    # which carries the name exactly.
    lowered = name.lower()

    mask = ctx.get("mask") or {}
    top = mask.get("top_cell")
    if top and lowered not in str(top).lower():
        problems.append(f"top cell {top!r} does not carry {name!r}")

    emitted = [p.name for p in sorted(ctx.run_dir.iterdir())
               if p.is_file() and any(p.name.endswith(x) for x in SUBMITTABLE)
               and "drc_markers" not in p.name]
    stray = [f for f in emitted if lowered not in f.lower()]
    if stray:
        problems.append(f"{len(stray)} emitted file(s) do not carry the name: "
                        + ", ".join(stray[:3]))
    if pattern:
        import re
        bad = [f for f in emitted if not re.fullmatch(pattern, f)]
        if bad:
            problems.append(f"{len(bad)} file(s) do not match {pattern!r}: "
                            + ", ".join(bad[:3]))
    if not emitted:
        return False, "no submittable file was emitted"
    if problems:
        return False, "; ".join(problems)
    return True, (f"{len(emitted)} file(s) and the top cell carry {name!r}"
                  + (f", matching {pattern!r}" if pattern else ""))


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
