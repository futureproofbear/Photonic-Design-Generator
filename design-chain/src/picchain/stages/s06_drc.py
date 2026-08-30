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


class DeckPlatformMismatch(RuntimeError):
    """The rule deck belongs to a different process stack than the design.

    Distinct from the failures that make a deck merely unrunnable, such as a
    missing KLayout or an unreadable file. Those are conditions of the machine
    and are reported as warnings, leaving the release gate to refuse on the
    condition that no deck was executed. This one is a property of the design:
    the deck would run perfectly and report on the wrong process.
    """


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

    # The monitor field, where a breach is deliberate.
    #
    # A critical-dimension vernier has to straddle the minimum width to find
    # where printing fails, so its narrowest rungs break the rule on purpose.
    # Checked against the device cell those shapes are out of scope and the
    # report is silent about them, which is how a die carrying twenty-one
    # deliberate breaches was reported as clean. Checked against the die they are
    # real, and a reader cannot tell them from a defect. They are counted
    # separately instead, and the box is read from the reticle stage so that it
    # follows the monitors rather than being written out by hand.
    declared_box = None
    if getattr(cfg, "declared_region_from_reticle", True):
        box_um = (ctx.get("reticle") or {}).get("monitor_field_box_um")
        if box_um and len(box_um) == 4:
            declared_box = db.Region(db.Box(
                db.DPoint(box_um[0], box_um[1]).to_itype(ly.dbu),
                db.DPoint(box_um[2], box_um[3]).to_itype(ly.dbu)))

    def _split(polys: "db.Region") -> tuple[int, int]:
        """Violations inside the monitor field, and the rest."""
        if declared_box is None or polys.is_empty():
            return 0, int(polys.count())
        inside = polys.interacting(declared_box)
        return int(inside.count()), int((polys - inside).count())

    results = []
    total_err = 0
    total_declared = 0
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
                dec, real = _split(bad)
                results.append({
                    "name": rule.name, "kind": rule.kind, "layer": rule.layer,
                    "value_um": rule.value_um, "severity": rule.severity,
                    "violations": real, "declared_in_monitor_field": dec,
                    "status": "fail" if real else "pass",
                })
                total_declared += dec
                if real and rule.severity == "error":
                    total_err += real
                top.shapes(marker_idx).insert(bad)
                continue
            else:
                results.append({"name": rule.name, "status": "skipped",
                                "reason": f"unknown kind {rule.kind}"})
                continue
        except Exception as exc:  # pragma: no cover
            results.append({"name": rule.name, "status": "error", "reason": str(exc)})
            continue

        polys = edges.polygons(1)
        dec, real = _split(polys)
        results.append({
            "name": rule.name, "kind": rule.kind, "layer": rule.layer,
            "other_layer": rule.other_layer, "value_um": rule.value_um,
            "severity": rule.severity, "violations": real,
            "declared_in_monitor_field": dec,
            "status": "fail" if real else "pass",
        })
        total_declared += dec
        if real and rule.severity == "error":
            total_err += real
        top.shapes(marker_idx).insert(polys)

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
        "declared_in_monitor_field": total_declared,
        "declared_region_um": (list((ctx.get("reticle") or {}).get(
            "monitor_field_box_um") or []) if declared_box is not None else None),
        "clean": total_err == 0,
        "results": results,
    }
    ctx.put("drc", payload)
    ctx.write_stage("drc", payload)
    if cfg.deck:
        try:
            deck_result = run_deck(design, ctx, gds_path)
        except DeckPlatformMismatch:
            # not an environment problem, and not a weaker check: it is a check
            # of another process. It stops the stage.
            raise
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
    # The per-user Windows installer's actual target, confirmed against a real
    # install: unversioned, and under Roaming rather than Local.
    r"%APPDATA%\KLayout\klayout_app.exe",
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


def deck_identity(deck_text: str) -> str | None:
    """The stack a runset declares, read from its own text.

    Both KLayout runsets seen so far name themselves twice, in the macro
    description and in the `report(...)` call, as `LN-CORE lnoi400 DRC` and
    `LT-PRO ltoi300 DRC`. Either is enough to tell one stack from the other.
    """
    import re

    for pat in (r"<description>\s*([^<]+?)\s*</description>",
                r"report\(\s*[\"']([^\"']+)[\"']"):
        m = re.search(pat, deck_text)
        if m:
            return m.group(1).strip()
    return None


def check_deck_matches_platform(design, deck_text: str) -> None:
    """Refuse a rule deck that belongs to another process stack.

    `platform.stack` carries the foundry's identifier for the stack this design
    is drawn on. Where it is set, it must appear in the deck's own declared
    identity. This raises rather than warning: a deck for the wrong stack does
    not produce a weaker check, it produces a check of a different process whose
    clean result means nothing about this one.
    """
    want = getattr(design.platform, "stack", None)
    if not want:
        return
    ident = deck_identity(deck_text)
    if ident is None:
        raise DeckPlatformMismatch(
            f"the design declares platform.stack '{want}' and the rule deck names no stack of "
            "its own, so the two cannot be matched. Confirm the deck is for this process, then "
            "clear platform.stack to proceed without the check"
        )
    if want.lower() not in ident.lower():
        raise DeckPlatformMismatch(
            f"the rule deck declares itself '{ident}' and this design declares platform.stack "
            f"'{want}'. A deck for another stack reads different layer numbers, so a clean "
            "report from it establishes nothing about this design. Point drc.deck at the deck "
            "for this process, and correct layout.layer_map to its layer numbers at the same "
            "time: the two must be changed together"
        )


def deck_layers(deck_text: str) -> dict[str, tuple[int, int]]:
    """The layers a runset names, as {name: (layer, datatype)}.

    A deck reads its geometry through `NAME = input(layer, datatype)`. Those
    numbers are the contract between the deck and the mask, and they are the
    part most easily got wrong: two stacks from the same foundry differ in
    datatype, and a deck pointed at a layer the mask does not use finds nothing
    and reports clean.
    """
    import re

    out: dict[str, tuple[int, int]] = {}
    for m in re.finditer(r"^([A-Z_0-9]+)\s*=\s*input\(\s*(\d+)\s*,\s*(\d+)\s*\)",
                         deck_text, re.M):
        out[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return out


def deck_layer_coverage(deck_text: str, gds_path) -> dict:
    """Which layers the deck reads, and whether the mask carries any of them.

    A rule evaluated against an empty layer cannot fail, so a clean report on a
    deck whose layers are absent from the mask says nothing at all. This was not
    hypothetical: a tantalate design was drawn on the niobate stack's layer
    numbers and checked with the niobate deck, and the correct deck would have
    found its metal layer empty and passed every metal rule silently.
    """
    import gdstk

    lib = gdstk.read_gds(str(gds_path))
    present: set[tuple[int, int]] = set()
    for cell in lib.cells:
        for poly in cell.get_polygons(depth=None):
            present.add((poly.layer, poly.datatype))

    named = deck_layers(deck_text)
    empty = {n: ld for n, ld in named.items() if ld not in present}
    return {
        "layers_named_by_deck": {n: list(ld) for n, ld in named.items()},
        "layers_named_and_empty": {n: list(ld) for n, ld in empty.items()},
        "layers_exercised": len(named) - len(empty),
        "layers_named": len(named),
    }


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

    # Before anything is executed: a deck belonging to another stack is refused
    # outright. Running it first and judging afterwards would spend the solve
    # and produce a clean report that means nothing.
    check_deck_matches_platform(design, deck.read_text(encoding="utf-8", errors="replace"))

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

    # A clean report is worth only as much as the geometry the deck could see.
    # Every layer the runset names is checked against the mask, and any that
    # carries no polygon is reported: its rules were evaluated against nothing.
    deck_text = deck.read_text(encoding="utf-8", errors="replace")
    cov = deck_layer_coverage(deck_text, gds_abs)
    cov["deck_declares"] = deck_identity(deck_text)
    cov["platform_stack"] = getattr(design.platform, "stack", None)

    # Which of the design's own layers land on each layer the deck reads. A
    # layer map written against one stack carries auxiliary layers chosen
    # because that stack ignored them, and another stack does not. The seal
    # ring, the dicing lane and the facet marks sat on 20/0, 22/0 and 23/0,
    # unread by the niobate deck and read as M1, M2 and HRL by the tantalate
    # one, which reported the dicing lane as circuit metal fourteen times.
    lmap = getattr(design.layout, "layer_map", None) or {}
    by_ld: dict[tuple[int, int], list[str]] = {}
    for name, ld in lmap.items():
        try:
            by_ld.setdefault((int(ld[0]), int(ld[1])), []).append(str(name))
        except (TypeError, ValueError, IndexError):
            continue
    sources = {dn: sorted(by_ld.get(tuple(ld), []))
               for dn, ld in cov["layers_named_by_deck"].items()}
    cov["deck_layer_sources"] = {k: v for k, v in sources.items() if v}
    shared = {k: v for k, v in sources.items() if len(v) > 1}
    if shared:
        detail = "; ".join(f"{k} <- {', '.join(v)}" for k, v in sorted(shared.items()))
        ctx.warn(
            "more than one design layer lands on a layer this deck reads, so the rules for it "
            f"are evaluated over their union: {detail}. Confirm each is intended to be checked "
            "as that layer"
        )
    if cov["layers_named_and_empty"]:
        names = ", ".join(f"{n} ({d[0]}/{d[1]})"
                          for n, d in sorted(cov["layers_named_and_empty"].items()))
        ctx.warn(
            f"the rule deck names {cov['layers_named']} layers and {len(cov['layers_named_and_empty'])} "
            f"of them carry no geometry on this mask: {names}. Every rule on those layers was "
            "evaluated against nothing and cannot have failed. Confirm the deck matches this "
            "process and that layout.layer_map uses its layer numbers"
        )

    return {
        "deck": str(deck),
        "deck_io_bound": bound,
        "klayout": exe,
        "report": str(report),
        "violations_by_category": counts,
        "violations_total": int(sum(counts.values())),
        "clean": bool(sum(counts.values()) == 0),
        **cov,
    }
