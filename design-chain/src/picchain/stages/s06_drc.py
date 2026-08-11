"""Stage 6 - DRC on the emitted GDS, using klayout's Region engine.

Rules are declared in the design file, not hard-coded, because every foundry
prints a different minimum feature.  The rules that matter for an E-DBR are:

* METAL/WG separation - the electrodes must not eat the evanescent tail
  (stage 3 reports the actual optical overlap with the metal, this rule is the
  cheap geometric guard);
* WG min space - the post-to-ridge gap is the single most aggressive dimension
  on the mask and is what decides whether kappa is manufacturable;
* WG min width - the post size and the taper tip;
* min area - sub-resolution posts that will simply not print.

Violations are written as a GDS marker layer so they can be viewed in KLayout.
"""

from __future__ import annotations

from typing import Any

from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary
from ._target import resolve_target

MARKER_LAYER = (1000, 0)


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.drc
    if not cfg.enabled or (not cfg.rules and not cfg.deck):
        ctx.put("drc", {"enabled": False, "reason": "no rules and no deck declared"})
        return {"enabled": False}

    gds_path, checked = resolve_target(design, ctx, "drc")

    import klayout.db as db

    ly = db.Layout()
    ly.read(str(gds_path))
    top = ly.top_cell()
    lmap = design.layout.layer_map

    def region(name: str) -> "db.Region":
        li, ld = lmap[name]
        idx = ly.layer(li, ld)
        return db.Region(top.begin_shapes_rec(idx)).merged()

    regions = {n: region(n) for n in lmap}
    marker_idx = ly.layer(*MARKER_LAYER)

    results = []
    total_err = 0
    for rule in cfg.rules:
        a = regions.get(rule.layer)
        if a is None:
            results.append({"name": rule.name, "status": "skipped",
                            "reason": f"layer {rule.layer} not in layer_map"})
            continue
        d = int(round(rule.value_um / 0.001))
        ang = float(rule.ignore_angle_deg)
        try:
            if rule.kind == "min_width":
                edges = a.width_check(d, False, db.Metrics.Euclidian, ang, None, None)
            elif rule.kind == "min_space":
                edges = a.space_check(d, False, db.Metrics.Euclidian, ang, None, None)
            elif rule.kind in ("min_separation", "min_enclosure"):
                b = regions.get(rule.other_layer or "")
                if b is None:
                    results.append({"name": rule.name, "status": "skipped",
                                    "reason": f"other_layer {rule.other_layer} missing"})
                    continue
                edges = (a.separation_check(b, d, False, db.Metrics.Euclidian, ang, None, None)
                         if rule.kind == "min_separation"
                         else a.enclosing_check(b, d, False, db.Metrics.Euclidian, ang, None, None))
            elif rule.kind == "min_area":
                bad = db.Region()
                for poly in a.each():
                    if poly.area() * (ly.dbu**2) < rule.value_um:
                        bad.insert(poly)
                results.append({
                    "name": rule.name, "kind": rule.kind, "layer": rule.layer,
                    "value_um": rule.value_um, "severity": rule.severity,
                    "violations": int(bad.count()),
                    "status": "fail" if bad.count() else "pass",
                })
                if bad.count() and rule.severity == "error":
                    total_err += int(bad.count())
                top.shapes(marker_idx).insert(bad)
                continue
            else:
                results.append({"name": rule.name, "status": "skipped",
                                "reason": f"unknown kind {rule.kind}"})
                continue
        except Exception as exc:  # pragma: no cover
            results.append({"name": rule.name, "status": "error", "reason": str(exc)})
            continue

        n = int(edges.count())
        results.append({
            "name": rule.name, "kind": rule.kind, "layer": rule.layer,
            "other_layer": rule.other_layer, "value_um": rule.value_um,
            "severity": rule.severity, "violations": n,
            "status": "fail" if n else "pass",
        })
        if n and rule.severity == "error":
            total_err += n
        top.shapes(marker_idx).insert(edges.polygons(1))

    marked = ctx.run_dir / f"{design.meta.name}.drc_markers.gds"
    ly.write(str(marked))

    payload = {
        "enabled": True,
        "gds": str(gds_path),
        # which layout carries the verdict: the device cell, or the die that
        # would actually be submitted
        "checked": checked,
        "markers_gds": str(marked),
        "rules_checked": len(cfg.rules),
        "error_violations": total_err,
        "clean": total_err == 0,
        "results": results,
    }
    ctx.put("drc", payload)
    ctx.write_stage("drc", payload)
    if cfg.deck:
        try:
            deck_result = run_deck(design, ctx, gds_path)
        except Exception as exc:
            deck_result = {"deck": cfg.deck, "error": str(exc)}
            ctx.warn(f"the foundry rule deck could not be executed: {exc}")
        payload["deck"] = deck_result
        ctx.put("drc", payload)
        ctx.write_stage("drc", payload)
        if deck_result.get("violations_total"):
            ctx.warn(
                f"the foundry deck reports {deck_result['violations_total']} violations "
                f"across {len(deck_result['violations_by_category'])} categories; the "
                "in-process rules are a smoke test and do not replace it"
            )

    if total_err:
        ctx.warn(f"DRC: {total_err} error-severity violations - see {marked.name}")
    return payload


# --------------------------------------------------------------------------
# foundry runset
# --------------------------------------------------------------------------
DEFAULT_KLAYOUT = [
    r"%LOCALAPPDATA%\KLayout\klayout-0.30.10-win64\klayout_app.exe",
    r"C:\Program Files\KLayout\klayout_app.exe",
    "/usr/bin/klayout",
    "/usr/local/bin/klayout",
]


def find_klayout(explicit: str | None = None) -> str | None:
    """The KLayout *application*, which is what executes a runset."""
    import os
    import shutil

    candidates = [explicit] if explicit else DEFAULT_KLAYOUT
    for c in candidates:
        if not c:
            continue
        p = os.path.expandvars(c)
        if os.path.isfile(p):
            return p
    return shutil.which("klayout") or shutil.which("klayout_app")


def parse_report(path) -> dict[str, int]:
    """Violations per category from a KLayout report database (.lyrdb)."""
    import xml.etree.ElementTree as ET

    counts: dict[str, int] = {}
    root = ET.parse(str(path)).getroot()
    for item in root.iter("item"):
        cat = (item.findtext("category") or "").strip().strip("'\"")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def bind_deck_io(text: str) -> tuple[str, list[str]]:
    """Bind a runset written for the graphical application to a batch run.

    A runset distributed for interactive use names no input and no report file:
    the layout is whatever the application has open, and the markers are shown
    in the browser. Executed with ``-b`` there is neither, and the runset stops
    at its first ``input()`` with no source.

    Two lines are therefore supplied, and nothing else is altered. ``source`` is
    prepended where the runset declares none, and a single-argument ``report``
    is given the file to write. The rules themselves are passed through
    verbatim, so the check performed is the foundry's own. What was added is
    returned alongside the text so that the run records it.
    """
    import re

    added: list[str] = []
    out = text

    m = re.search(r"^\s*report\s*\((\s*[\"'][^\"']*[\"']\s*)\)", out, re.M)
    if m:
        out = out[:m.end() - 1] + ", $report" + out[m.end() - 1:]
        added.append("report(..., $report)")

    if not re.search(r"^\s*source\s*\(", out, re.M):
        out = "source($input)\n" + out
        added.append("source($input)")

    return out, added


def deck_script(deck, run_dir) -> tuple[object, list[str]]:
    """The runset as an executable script, with its I/O bound.

    A ``.lydrc`` is an XML macro whose rules live in a ``text`` element. It is
    unwrapped here rather than handed to the interpreter, so that the binding
    above can be applied to the same source in either format.
    """
    import xml.etree.ElementTree as ET
    from pathlib import Path

    if deck.suffix.lower() == ".lydrc":
        body = ET.parse(str(deck)).getroot().findtext("text") or ""
    else:
        body = deck.read_text(encoding="utf-8")

    bound, added = bind_deck_io(body)
    if not added:
        return deck, []

    prepared = Path(run_dir) / "drc_deck.bound.drc"
    prepared.write_text(bound, encoding="utf-8")
    return prepared, added


def run_deck(design, ctx, gds_path) -> dict:
    """Execute a foundry runset against the emitted mask."""
    import subprocess
    from pathlib import Path

    cfg = design.drc
    deck = Path(cfg.deck)
    if not deck.is_absolute():
        base = design.source_path.parent if design.source_path else Path.cwd()
        deck = (base / deck).resolve()
    if not deck.is_file():
        raise RuntimeError(f"the rule deck {deck} was not found")

    exe = find_klayout(cfg.klayout_exe)
    if not exe:
        raise RuntimeError(
            "the KLayout application was not found, and the Python module cannot "
            "execute a runset. Set drc.klayout_exe, or install the portable build"
        )

    # KLayout resolves relative paths against its own working directory, and the
    # run directory is held relative to the design; both are made absolute here
    report = (ctx.run_dir / "drc_deck.lyrdb").resolve()
    gds_abs = Path(gds_path).resolve()
    script, bound = deck_script(deck, ctx.run_dir)
    if bound:
        ctx.warn(
            "the rule deck named no input and no report file, so it was written "
            "for the graphical application. It has been bound to this run by "
            f"supplying {' and '.join(bound)}. The rules are unaltered"
        )
    cmd = [exe, "-b", "-r", str(script),
           "-rd", f"input={gds_abs}", "-rd", f"report={report}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=cfg.deck_timeout_s)
    (ctx.run_dir / "drc_deck.log").write_text(
        (proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""), encoding="utf-8")

    if not report.exists():
        tail = (proc.stderr or proc.stdout or "").strip()[-600:]
        raise RuntimeError(f"the runset produced no report database\n{tail}")

    counts = parse_report(report)
    return {
        "deck": str(deck),
        "deck_io_bound": bound,
        "klayout": exe,
        "report": str(report),
        "violations_by_category": counts,
        "violations_total": int(sum(counts.values())),
        "clean": bool(sum(counts.values()) == 0),
    }
