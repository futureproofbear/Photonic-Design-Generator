"""A self-contained HTML view of where one design stands.

The report states conclusions in prose. This states the position: which stages
produced a result, which targets are met and by how much, and what the run
raised that no target expresses.

Its one editorial decision is to draw the distinction a verdict cannot. A run
reports PASS when every target it was asked about is met, and a target can only
be asked about a metric some stage produced. A design whose taper, bend and
facet stages were never enabled therefore passes without any of them having been
examined. The page shows stage coverage beside the verdict for that reason, and
names the stages that produced nothing.

The page is written as one file with no external reference of any kind, so it
opens from disk and survives being moved or sent.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# What each stage answers, and what it leaves behind. Held here rather than
# taken from the stage docstrings: a docstring addresses somebody reading the
# source, and this addresses somebody reading the design.
# --------------------------------------------------------------------------
STAGE_PURPOSE: dict[str, tuple[str, str]] = {
    "mode": ("Does the guide hold one mode, and at what index",
             "n_eff, n_g, mode count, the index step the posts make"),
    "taper": ("Does the taper convert without exciting a second mode",
              "adiabaticity margin, staircase residue"),
    "fem": ("Does an independent solver agree on the cross-section",
            "n_eff disagreement, polarisation purity, mesh guard"),
    "fdtd": ("Does a method carrying radiation agree on kappa",
             "band-gap kappa, ratio to coupled-mode, convergence guard"),
    "bend": ("How tight may the guide turn before it leaks",
             "bend mode, outward shift, radiation caustic"),
    "facet": ("How much light crosses the chip boundary",
              "overlap, Fresnel, angle, alignment tolerance"),
    "grating": ("What mirror does the geometry make",
                "period, kappa, Bragg wavelength, R, bandwidth, penetration"),
    "eo": ("How hard is it to tune that mirror",
           "overlap, MHz/V, Vpi.L, capacitance, bandwidth"),
    "cavity": ("What laser results, and how far will it tune",
               "FSR, Pockels lever, mode-hop-free range, linewidth, SMSR"),
    "dynamics": ("What current does it need, and is it stable",
                 "threshold, power, relaxation oscillation, RIN, feedback regime"),
    "circuit": ("What does the gain chip actually see",
                "assembled reflection, facet etalon ripple"),
    "layout": ("Is the device drawn, and drawn as declared",
               "GDS and OASIS, grid snap, drawn against printed, completeness"),
    "reticle": ("Is there a die a fabricator would accept",
                "frame, seal ring, dicing lane, marks, monitors, chip frame"),
    "drc": ("Does the mask break any rule",
            "per-rule counts, and the foundry runset separately"),
    "mask": ("Is the mask connected as intended, and dense enough",
             "regions, extracted netlist, shorts, density, fill"),
    "verify": ("Does the design meet what was asked of it",
               "one row per target, with severity and margin"),
    "release": ("May this be sent",
                "manifest with checksums, ten conditions of readiness"),
}

TIER_TITLE = {
    0: "the cross-section",
    1: "what the geometry makes",
    2: "the device that results",
    3: "the mask, and what it is checked against",
    4: "assembled and released",
}

# --------------------------------------------------------------------------
# Warnings, sorted by what a reader must do about them.
#
# This is a heuristic over the warning text and the page says so. It exists
# because eleven undifferentiated lines are read as eleven equal lines, and they
# are not: one of them said the laser would hop inside its own chirp ramp and sat
# between a note about sidelobes and a note about monitor gaps. Anything matching
# nothing is `recorded`, so a warning is never promoted by accident, only ever
# demoted.
# --------------------------------------------------------------------------
# Patterns are kept narrow and each is anchored to a condition that genuinely
# demands action. `is not the bandwidth` was included once and promoted a note
# about the lumped electrode estimate, which is a stated model limitation and
# not a defect, so it is gone. A pattern that promotes a limitation defeats the
# grouping: three items in the blocking column, one of which is background, and
# the column stops being read.
_BLOCKING = re.compile(
    r"will hop|coherence collapse|was skipped|refus|"
    r"against the \d+ expected|below the required|< required",
    re.I,
)
_OUTSTANDING = re.compile(
    r"no fill is placed|fill is required|is required\b|"
    r"not carried by any model|could not be drawn|"
    r"before submission|has not been|remains? unexercised",
    re.I,
)


def classify_warning(text: str) -> str:
    """`blocking`, `outstanding` or `recorded`, in that order of precedence."""
    if _BLOCKING.search(text or ""):
        return "blocking"
    if _OUTSTANDING.search(text or ""):
        return "outstanding"
    return "recorded"


GROUP_BLURB = {
    "blocking": ("A requirement is unmet, or a check did not complete. Neither "
                 "appears in the verdict, no target expressing either."),
    "outstanding": ("Work the mask needs before it could be submitted. Each is "
                    "sized here; none is done."),
    "recorded": ("Known and accepted. Each states a limit of the model rather "
                 "than a defect in the design."),
}


# --------------------------------------------------------------------------
# how far inside its bound a value sits: 1 comfortable, 0 on the limit
# --------------------------------------------------------------------------
def headroom(criterion: str, actual: Any) -> float | None:
    """Distance from the value to the bound, as a fraction of that bound.

    Returns None where the criterion is not one of the four forms the verify
    stage emits, so an unparsed criterion shows as no bar rather than as a full
    one. A shape this does not recognise must never read as comfortable.
    """
    try:
        a = float(actual)
    except (TypeError, ValueError):
        return None
    if a != a:
        return None
    c = (criterion or "").strip()

    m = re.match(r"^= *([-\d.eE+]+) *\+- *([\d.]+)% *$", c)
    if m:
        centre, pct = float(m.group(1)), float(m.group(2))
        tol = abs(centre) * pct / 100.0
        return None if tol == 0 else max(0.0, 1.0 - abs(a - centre) / tol)

    m = re.match(r"^>= *([-\d.eE+]+) *and *<= *([-\d.eE+]+) *$", c)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        half = (hi - lo) / 2.0
        return None if half <= 0 else max(0.0, 1.0 - abs(a - (lo + hi) / 2.0) / half)

    m = re.match(r"^<= *([-\d.eE+]+) *$", c)
    if m:
        lim = float(m.group(1))
        if lim == 0:
            return 1.0 if a <= 0 else 0.0
        return max(0.0, min(1.0, (lim - a) / abs(lim)))

    m = re.match(r"^>= *([-\d.eE+]+) *$", c)
    if m:
        lim = float(m.group(1))
        if lim == 0:
            return 1.0 if a >= 0 else 0.0
        return max(0.0, min(1.0, (a - lim) / abs(lim)))
    return None


def _tier(name: str, deps: dict[str, list[str]], seen: frozenset = frozenset()) -> int:
    if name in seen:
        return 0
    reqs = deps.get(name) or []
    if not reqs:
        return 0
    return 1 + max(_tier(r, deps, seen | {name}) for r in reqs)


# --------------------------------------------------------------------------
# when each stage last produced a result, and whether the design has moved on
#
# A subset run leaves the other stages untouched, so a metric tree assembled
# from `--stages mode,grating` says nothing about the bend stage rather than
# saying the bend stage failed. The history below answers the question a reader
# actually has, which is when the bend was last looked at and whether the design
# has changed since. The comparison is over the whole resolved design, so a
# change anywhere marks every earlier result as predating it. That is
# deliberately conservative: it can call a result stale that is in fact still
# valid, and it cannot call a stale result current.
# --------------------------------------------------------------------------
def _run_when(run_id: str) -> str:
    m = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})", run_id or "")
    if not m:
        return ""
    y, mo, d, h, mi = m.groups()
    return f"{y}-{mo}-{d} {h}:{mi}"


def _design_hash(run_dir: Path) -> str:
    import hashlib

    p = run_dir / "design.resolved.json"
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def stage_history(runs_dir: Path, stage_names, current_hash: str) -> dict:
    """The most recent run that produced each stage, newest first.

    Run identifiers begin with a sortable timestamp, so the directories are
    walked in reverse order and the scan stops as soon as every stage has been
    accounted for. A design with hundreds of runs is therefore read in a handful
    of files rather than in all of them.
    """
    remaining = set(stage_names)
    found: dict[str, dict] = {}
    if not runs_dir.is_dir():
        return found
    for d in sorted((x for x in runs_dir.iterdir() if x.is_dir()), reverse=True):
        if not remaining:
            break
        mp = d / "metrics.json"
        if not mp.exists():
            continue
        try:
            doc = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        produced = set((doc.get("metrics") or {}).keys()) & remaining
        if not produced:
            continue
        h = _design_hash(d)
        for name in produced:
            plan = d / "run.plan.json"
            corner = None
            if plan.exists():
                try:
                    corner = json.loads(plan.read_text(encoding="utf-8")).get("corner")
                except (OSError, ValueError):
                    corner = None
            found[name] = {
                "run_id": doc.get("run_id") or d.name,
                "when": _run_when(doc.get("run_id") or d.name),
                "same_design": bool(h and current_hash and h == current_hash),
                "design_known": bool(h and current_hash),
                "corner": corner,
            }
        remaining -= produced
    return found


def in_flight(runs_dir: Path) -> dict:
    """The stage a run currently underway is working on, if any.

    A run writes one JSON per stage as it completes it, and writes `metrics.json`
    only at the end. A directory holding the first and not the second is a run
    that has not finished, and the earliest stage of its resolved order with no
    file of its own is the one it is inside.

    Elapsed time is reported rather than a verdict on liveness. The stage this
    matters for is the external solver, which writes nothing for hours between
    its job file and its result, so a freshness test on file times would call a
    healthy three-hour solve dead within minutes. That mistake has already been
    made twice here by hand. What the reader needs is how long it has been going
    and what it usually costs, which is what is given.
    """
    import datetime as _dt

    out: dict = {}
    if not runs_dir.is_dir():
        return out
    for d in sorted((x for x in runs_dir.iterdir() if x.is_dir()), reverse=True)[:40]:
        if (d / "metrics.json").exists():
            continue
        plan = d / "run.plan.json"
        resolved = d / "design.resolved.json"
        try:
            if plan.exists():
                order = json.loads(plan.read_text(encoding="utf-8")).get("stages") or []
            elif resolved.exists():
                # A run predating the plan file, or one whose subset is unknown.
                # The declared list is the best available and may be a superset,
                # so the stage underway is taken as the first one missing AFTER
                # the last one present rather than the first missing outright:
                # a subset run leaves earlier stages absent by intent, not by
                # having stopped at them.
                from .cli import _resolve_stages
                declared = json.loads(resolved.read_text(encoding="utf-8")).get("stages") or []
                order = _resolve_stages(list(declared))
            else:
                continue
        except Exception:
            continue
        present = [i for i, s in enumerate(order) if (d / f"{s}.json").exists()]
        start = (max(present) + 1) if present else 0
        pending = [s for s in order[start:] if not (d / f"{s}.json").exists()]
        if not pending:
            continue
        started = _run_when(d.name)
        mins = None
        m = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})", d.name)
        if m:
            y, mo, dd, hh, mi, ss = (int(x) for x in m.groups())
            try:
                t0 = _dt.datetime(y, mo, dd, hh, mi, ss)
                mins = max(0.0, (_dt.datetime.now() - t0).total_seconds() / 60.0)
            except ValueError:
                mins = None
        out.setdefault(pending[0], {
            "run_id": d.name, "started": started, "elapsed_min": mins,
            "done_before_it": [s for s in order if (d / f"{s}.json").exists()],
        })
    return out


def typical_cost(runs_dir: Path, stage: str) -> float | None:
    """The longest this stage has taken in any recorded run, in seconds.

    The longest and not the mean: the question a reader has is whether the run
    now underway has exceeded anything previously seen, and a mean answers a
    different one.
    """
    worst = None
    if not runs_dir.is_dir():
        return None
    for d in sorted((x for x in runs_dir.iterdir() if x.is_dir()), reverse=True)[:80]:
        p = d / "metrics.json"
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        v = ((doc.get("metrics") or {}).get("stage_timings_s") or {}).get(stage)
        if isinstance(v, (int, float)):
            worst = v if worst is None else max(worst, v)
    return worst


def collect(run_dir: Path) -> dict:
    """Everything the page shows, read from one run directory."""
    from .stages import DEPENDENCIES, STAGES

    doc = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    metrics = doc.get("metrics", {}) or {}

    current_hash = _design_hash(run_dir)
    history = stage_history(run_dir.parent, STAGES, current_hash)
    running = in_flight(run_dir.parent)

    stages = []
    for name in STAGES:
        sec = metrics.get(name)
        purpose, evidence = STAGE_PURPOSE.get(name, ("", ""))
        if sec is None:
            state, note = "not_run", "not executed in this run"
        elif isinstance(sec, dict) and sec.get("enabled") is False:
            state = "off"
            note = str(sec.get("reason") or "switched off in the design")
        else:
            state, note = "ran", ""
        stages.append({
            "name": name,
            "requires": DEPENDENCIES.get(name, []),
            "tier": _tier(name, DEPENDENCIES),
            "purpose": purpose,
            "evidence": evidence,
            "state": state,
            "note": note,
            "last": history.get(name),
            "running": running.get(name) if state != "ran" else None,
            "typical_s": typical_cost(run_dir.parent, name),
        })

    # A stage still in flight elsewhere is marked as such, and one whose run has
    # exceeded several times its own longest recorded duration is marked
    # interrupted instead. Both replace the state rather than annotating it: a
    # card carrying a green "ran" chip beside a line saying the run was
    # interrupted asserts two incompatible things and was doing so.
    for s in stages:
        r = s.get("running")
        if not r or s["state"] == "ran":
            continue
        typ, mins = s.get("typical_s"), r.get("elapsed_min")
        s["state"] = ("interrupted"
                      if (typ and mins and mins > 3.0 * (typ / 60.0))
                      else "running")

    v = metrics.get("verify", {}) or {}
    drc = metrics.get("drc", {}) or {}
    deck = (drc.get("deck") or {}) if isinstance(drc.get("deck"), dict) else {}
    frame = ((metrics.get("reticle") or {}).get("chip_frame") or {})

    warnings = [{"text": w, "group": classify_warning(w)}
                for w in (doc.get("warnings") or [])]

    return {
        "run_id": doc.get("run_id"),
        "status": doc.get("status"),
        "elapsed_s": doc.get("elapsed_s"),
        "design": (metrics.get("meta") or {}).get("name") or run_dir.parent.parent.name,
        "stages": stages,
        "targets": v.get("rows") or [],
        "verify": {k: v.get(k) for k in
                   ("verdict", "n_targets", "n_pass", "n_fail", "n_missing")},
        "drc": {
            "rules_checked": drc.get("rules_checked"),
            "own_violations": drc.get("error_violations"),
            "target": drc.get("checked"),
            "deck_total": deck.get("violations_total"),
            "deck_bound": deck.get("deck_io_bound") or [],
        },
        "frame": frame,
        "warnings": warnings,
    }


def selfcheck(state: dict) -> list[str]:
    """Contradictions in the page, found before a reader finds them.

    This exists because six defects in this page were reported by its reader
    rather than by its author, across successive publishes: a green "ran" chip
    beside a line saying the run was interrupted, a chip reading "running now"
    over body text saying the opposite, a stage marked switched off on a
    justification that had gone stale, and a warning classifier promoting a
    stated model limitation into the blocking column. Every one was visible in
    the output.

    A check that runs on every render beats one that depends on remembering.
    """
    bad: list[str] = []
    known = set(_LABEL)
    for s in state["stages"]:
        if s["state"] not in known:
            bad.append(f"{s['name']}: unknown state {s['state']!r}")
        if s["state"] == "ran" and s.get("running"):
            bad.append(f"{s['name']}: reported as having run and as in flight at once")
        if s["state"] in ("running", "interrupted") and not s.get("running"):
            bad.append(f"{s['name']}: state {s['state']} with nothing in flight to describe")
        if s.get("last") and not s["last"].get("run_id"):
            bad.append(f"{s['name']}: a last run with no identifier")

    v = state["verify"]
    n_p, n_t = v.get("n_pass"), v.get("n_targets")
    if n_p is not None and n_t is not None:
        if n_p > n_t:
            bad.append(f"verify: {n_p} passing of {n_t} declared")
        if v.get("verdict") == "PASS" and n_p != n_t:
            bad.append(f"verify: verdict PASS with {n_t - n_p} target(s) not met")
    if len(state["stages"]) != len(set(s["name"] for s in state["stages"])):
        bad.append("the stage list contains a duplicate")
    return bad


def newer_run(runs_dir: Path, run_id: str) -> str | None:
    """A completed run of this design later than the one being shown, if any.

    A page describing an older run is not wrong, but a reader has no way to know
    it unless the page says so, and a stale page is read as a current one.
    """
    if not runs_dir.is_dir():
        return None
    later = [d.name for d in runs_dir.iterdir()
             if d.is_dir() and d.name > (run_id or "") and (d / "metrics.json").exists()]
    return max(later) if later else None


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
_MONO = ('ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,'
         '"Liberation Mono",monospace')

_LIGHT = (
    "--ground:#F4F6F5;--panel:#FFFFFF;--sunk:#EDF1EF;--ink:#141A20;--ink-2:#4B5761;"
    "--hair:#C8D1CD;--accent:#26707E;--pass:#3B7A57;--pass-bg:#E2F0E8;"
    "--warn:#8A5A1F;--warn-bg:#F7EDDC;--absent:#7C8A93;--absent-bg:#E7ECEA;"
    "--stop:#9C3B2E;--stop-bg:#F7E4E0;--bar:#D6DEDA;"
)
_DARK = (
    "--ground:#0D1116;--panel:#151B21;--sunk:#101519;--ink:#E3EAE7;--ink-2:#8FA0AA;"
    "--hair:#2A343C;--accent:#5FB0BD;--pass:#6FB490;--pass-bg:#16281F;"
    "--warn:#D8A44B;--warn-bg:#2B2114;--absent:#6B7A84;--absent-bg:#1A2126;"
    "--stop:#D07767;--stop-bg:#2C1815;--bar:#243039;"
)

_TONE = {"ran": "pass", "off": "absent", "not_run": "absent",
         "running": "live", "interrupted": "warn"}
_LABEL = {"ran": "ran", "off": "switched off", "not_run": "not executed",
          "running": "running now", "interrupted": "interrupted"}
_GROUP_TONE = {"blocking": "stop", "outstanding": "warn", "recorded": "absent"}


def _esc(v: Any) -> str:
    return html.escape(str(v), quote=True)


def _num(v: Any) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(v)
    if f != f:
        return "nan"
    if f == 0:
        return "0"
    if abs(f) >= 1e5 or abs(f) < 1e-3:
        return f"{f:.3e}"
    return f"{f:.4g}"


def _css() -> str:
    return f"""
:root{{{_LIGHT}}}
@media (prefers-color-scheme:dark){{:root{{{_DARK}}}}}
:root[data-theme="dark"]{{{_DARK}}}
:root[data-theme="light"]{{{_LIGHT}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);
 font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 font-size:15px;line-height:1.55}}
.wrap{{max-width:1240px;margin:0 auto;padding:36px 22px 76px}}
header.top{{border-bottom:1px solid var(--hair);padding-bottom:20px;margin-bottom:26px}}
.eyebrow{{font-family:{_MONO};font-size:11px;letter-spacing:.16em;text-transform:uppercase;
 color:var(--ink-2);margin:0 0 9px}}
h1{{font-family:{_MONO};font-size:clamp(23px,3.2vw,32px);font-weight:600;margin:0 0 10px;
 letter-spacing:-.01em;text-wrap:balance}}
.sub{{color:var(--ink-2);max-width:72ch;margin:0}}
h2{{font-family:{_MONO};font-size:12.5px;letter-spacing:.13em;text-transform:uppercase;
 font-weight:600;color:var(--ink-2);margin:42px 0 14px;padding-bottom:8px;
 border-bottom:1px solid var(--hair)}}
p{{max-width:72ch}}
.meters{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}}
.meter{{background:var(--panel);border:1px solid var(--hair);border-radius:3px;
 padding:15px 16px;border-left:3px solid var(--accent)}}
.meter.pass{{border-left-color:var(--pass)}}
.meter.warn{{border-left-color:var(--warn)}}
.meter.stop{{border-left-color:var(--stop)}}
.meter.absent{{border-left-color:var(--absent)}}
.meter .k{{font-family:{_MONO};font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;
 color:var(--ink-2);margin:0 0 7px}}
.meter .val{{font-family:{_MONO};font-size:25px;font-weight:600;line-height:1.1;
 font-variant-numeric:tabular-nums}}
.meter .cap{{font-size:12.5px;color:var(--ink-2);margin:6px 0 0;max-width:none}}
.tier{{display:grid;grid-template-columns:150px 1fr;gap:16px;margin-bottom:18px}}
.tier-label{{font-family:{_MONO};font-size:11.5px;color:var(--ink-2);display:flex;gap:9px;
 align-items:baseline;padding-top:13px;line-height:1.35}}
.tier-n{{display:inline-flex;align-items:center;justify-content:center;flex:none;width:21px;
 height:21px;border-radius:50%;border:1px solid var(--hair);background:var(--sunk);
 color:var(--ink);font-size:11px}}
.stages{{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:12px}}
.stage{{background:var(--panel);border:1px solid var(--hair);border-radius:3px;
 padding:13px 14px;border-top:2px solid var(--absent)}}
.stage.pass{{border-top-color:var(--pass)}}
.stage.live{{border-top-color:var(--accent)}}
.stage.warn{{border-top-color:var(--warn)}}
.chip.live{{background:var(--panel);color:var(--accent);border:1px solid var(--accent)}}
.live.stalled{{color:var(--warn)}}
.live{{font-family:{_MONO};font-size:11px;margin:9px 0 0;max-width:none;line-height:1.5;
 color:var(--accent)}}
.stage.absent{{opacity:.72;background:var(--sunk)}}
.stage header{{display:flex;justify-content:space-between;align-items:center;gap:8px;
 margin-bottom:8px}}
.stage h3{{font-family:{_MONO};font-size:14px;margin:0;font-weight:600}}
.purpose{{font-size:13px;margin:0 0 6px;max-width:none}}
.evidence{{font-size:12px;color:var(--ink-2);margin:0;max-width:none;font-family:{_MONO};
 line-height:1.45}}
.note{{font-size:12px;color:var(--warn);margin:7px 0 0;max-width:none}}
.last{{font-family:{_MONO};font-size:11px;margin:9px 0 0;max-width:none;
 line-height:1.5;color:var(--ink-2)}}
.last .mark{{padding:1px 5px;border-radius:2px;margin-left:5px}}
.last.fresh .mark{{background:var(--pass-bg);color:var(--pass)}}
.last.stale .mark{{background:var(--warn-bg);color:var(--warn)}}
.last .rid{{opacity:.65}}
.last.none{{opacity:.7;font-style:italic}}
.reqs{{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}}
.req{{font-family:{_MONO};font-size:10.5px;padding:1px 6px;border-radius:2px;
 background:var(--sunk);border:1px solid var(--hair);color:var(--ink-2)}}
.req.none{{opacity:.6;font-style:italic}}
.chip{{font-family:{_MONO};font-size:10.5px;letter-spacing:.04em;padding:2px 7px;
 border-radius:2px;white-space:nowrap;flex:none;display:inline-block}}
.chip.pass{{background:var(--pass-bg);color:var(--pass);border:1px solid var(--pass)}}
.chip.warn{{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn)}}
.chip.absent{{background:var(--absent-bg);color:var(--absent);border:1px solid var(--absent)}}
.chip.stop{{background:var(--stop-bg);color:var(--stop);border:1px solid var(--stop)}}
.tablewrap{{overflow-x:auto;background:var(--panel);border:1px solid var(--hair);
 border-radius:3px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:760px}}
th,td{{text-align:left;padding:9px 14px;border-bottom:1px solid var(--hair)}}
tbody tr:last-child td{{border-bottom:none}}
th{{font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-2);
 font-weight:600;background:var(--sunk)}}
td.m{{font-family:{_MONO};font-size:12.5px}}
td.c{{font-family:{_MONO};font-size:12px;color:var(--ink-2);white-space:nowrap}}
td.n{{font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.hr{{width:190px}}
.bar{{display:inline-block;vertical-align:middle;width:112px;height:7px;background:var(--bar);
 border-radius:1px;overflow:hidden}}
.bar i{{display:block;height:100%}}
.bar i.pass{{background:var(--pass)}}
.bar i.warn{{background:var(--warn)}}
.bar i.stop{{background:var(--stop)}}
.bar.none{{opacity:.35}}
.hrv{{font-family:{_MONO};font-size:11.5px;color:var(--ink-2);margin-left:9px;
 font-variant-numeric:tabular-nums}}
.groups{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
.group{{background:var(--panel);border:1px solid var(--hair);border-radius:3px;
 padding:15px 16px;border-top:2px solid var(--absent)}}
.group.stop{{border-top-color:var(--stop)}}
.group.warn{{border-top-color:var(--warn)}}
.group h3{{font-family:{_MONO};font-size:13px;margin:0 0 7px;display:flex;gap:9px;
 align-items:center;font-weight:600}}
.blurb{{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;max-width:none}}
.group ul{{margin:0;padding-left:17px;font-size:12.5px;line-height:1.5}}
.group li{{margin-bottom:8px}}
.legend{{display:flex;flex-wrap:wrap;gap:16px;font-size:12.5px;color:var(--ink-2);
 margin:0 0 16px;align-items:center}}
.legend span{{display:flex;align-items:center;gap:7px}}
.stale-banner{{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn);
 border-radius:3px;padding:9px 13px;margin:0 0 14px;font-size:13px;max-width:none}}
.stale-banner code{{font-size:.92em}}
footer{{margin-top:44px;padding-top:14px;border-top:1px solid var(--hair);
 font-size:12px;color:var(--ink-2);font-family:{_MONO}}}
"""


def _running_line(s: dict) -> str:
    """What a stage now underway has been doing, and for how long.

    No claim is made about whether it is healthy. The elapsed time is given
    beside the longest this stage has previously taken, which is the comparison
    that answers the question actually being asked.
    """
    r = s.get("running")
    if not r:
        return ""
    mins = r.get("elapsed_min")
    el = f"{mins/60:.1f} h" if mins and mins >= 90 else (
        f"{mins:.0f} min" if mins is not None else "unknown")
    typ = s.get("typical_s")
    against = ""
    if typ:
        tt = f"{typ/3600:.1f} h" if typ >= 5400 else f"{typ/60:.0f} min"
        against = f" &middot; longest previously {tt}"
    # A stage that writes nothing for hours cannot be judged by file times, which
    # is why no freshness test is applied. It CAN be judged against its own
    # history: a run past several times the longest that stage has ever taken has
    # almost certainly been interrupted, and saying so is more useful than
    # calling it live indefinitely. A killed run reported 22.1 hours of "running
    # now" against a longest-ever of 2.7 h, with both figures on the same card.
    typ_m = (typ / 60.0) if typ else None
    stalled = bool(typ_m and mins and mins > 3.0 * typ_m)
    word = "no result after" if stalled else "running for"
    tail = (" &mdash; this run has almost certainly been interrupted"
            if stalled else "")
    return (f'<p class="live{" stalled" if stalled else ""}">{word} {el}{against}'
            f'{tail}<br><span class="rid">{_esc(r.get("run_id"))}</span></p>')


def _last_line(s: dict) -> str:
    """When this stage last produced a result anywhere under `runs/`.

    A stage absent from the current run is not necessarily a stage nobody has
    ever run, and the two are worth telling apart. Where an earlier run produced
    it, that run is named along with whether the design has changed since.
    """
    last = s.get("last")
    if not last:
        return ('<p class="last none">never run under this design</p>')
    when = last.get("when") or last.get("run_id")
    if not last.get("design_known"):
        mark, tone = "design not comparable", "stale"
    elif last.get("same_design"):
        mark, tone = "this design", "fresh"
    else:
        mark, tone = "design has changed since", "stale"
    corner = last.get("corner")
    if corner:
        mark, tone = f"a corner, not the design: {corner}", "stale"
    return (f'<p class="last {tone}">last run {_esc(when)} '
            f'<span class="mark">{_esc(mark)}</span><br>'
            f'<span class="rid">{_esc(last.get("run_id"))}</span></p>')


def _stage_card(s: dict) -> str:
    tone = _TONE[s["state"]]
    reqs = "".join(f'<span class="req">{_esc(r)}</span>' for r in s["requires"])
    note = f'<p class="note">{_esc(s["note"])}</p>' if s["note"] else ""
    return f"""
      <article class="stage {tone}">
        <header><h3>{_esc(s['name'])}</h3>
          <span class="chip {tone}">{_LABEL[s['state']]}</span></header>
        <p class="purpose">{_esc(s['purpose'])}</p>
        <p class="evidence">{_esc(s['evidence'])}</p>
        {note}
        {_running_line(s)}
        {_last_line(s)}
        <div class="reqs">{reqs or '<span class="req none">no inputs</span>'}</div>
      </article>"""


def _target_row(t: dict) -> str:
    h = headroom(t.get("criterion"), t.get("actual"))
    tone = "pass" if t.get("status") == "pass" else "stop"
    if h is not None and h < 0.10 and tone == "pass":
        tone = "warn"
    if h is None:
        bar, hv = '<div class="bar none"></div>', "&mdash;"
    else:
        pct = int(round(h * 100))
        bar = (f'<div class="bar"><i class="{tone}" '
               f'style="width:{max(2, pct)}%"></i></div>')
        hv = f"{pct}%"
    sev = t.get("severity") or ""
    return f"""
      <tr>
        <td class="m">{_esc(t.get('metric'))}</td>
        <td class="c">{_esc(t.get('criterion'))}</td>
        <td class="n">{_num(t.get('actual'))}</td>
        <td><span class="chip {'stop' if sev == 'must' else 'absent'}">{_esc(sev)}</span></td>
        <td class="hr">{bar}<span class="hrv">{hv}</span></td>
      </tr>"""


def render_html(state: dict) -> str:
    """The page, as one string with no external reference."""
    stages = state["stages"]
    ran = sum(1 for s in stages if s["state"] == "ran")
    total = len(stages)
    missing = [s["name"] for s in stages if s["state"] != "ran"]
    v = state["verify"]
    drc = state["drc"]
    frame = state["frame"]

    tiers = []
    for t in sorted({s["tier"] for s in stages}):
        cards = "".join(_stage_card(s) for s in stages if s["tier"] == t)
        tiers.append(f"""
    <section class="tier">
      <div class="tier-label"><span class="tier-n">{t}</span>
        <span>{_esc(TIER_TITLE.get(t, ''))}</span></div>
      <div class="stages">{cards}</div>
    </section>""")

    rows = "".join(_target_row(t) for t in state["targets"])
    if not rows:
        rows = ('<tr><td colspan="5">No target was evaluated. The verify stage '
                'did not run, or the design declares none.</td></tr>')

    groups = []
    for key in ("blocking", "outstanding", "recorded"):
        items = [w["text"] for w in state["warnings"] if w["group"] == key]
        if not items:
            continue
        li = "".join(f"<li>{_esc(x)}</li>" for x in items)
        groups.append(f"""
      <div class="group {_GROUP_TONE[key]}">
        <h3><span class="chip {_GROUP_TONE[key]}">{len(items)}</span> {key.title()}</h3>
        <p class="blurb">{_esc(GROUP_BLURB[key])}</p>
        <ul>{li}</ul>
      </div>""")
    groups_html = "".join(groups) or (
        '<div class="group"><h3>Nothing raised</h3>'
        '<p class="blurb">The run produced no warnings.</p></div>')

    # the verdict meter takes its tone from the verdict and not from the count
    verdict = (v.get("verdict") or "-").upper()
    v_tone = "pass" if verdict == "PASS" else "stop"
    cover_tone = "pass" if ran == total else "warn"

    own = drc.get("own_violations")
    deck_n = drc.get("deck_total")
    if own is None:
        rule_val, rule_tone = "not run", "absent"
        rule_cap = "The rule check did not run."
    elif deck_n is None:
        rule_val = f"{own}"
        rule_tone = "pass" if own == 0 else "stop"
        rule_cap = (f"{drc.get('rules_checked')} declared rules against the "
                    f"{drc.get('target') or 'device'}. No foundry runset was "
                    "executed, so this is a smoke test.")
    else:
        rule_val = f"{own} + {deck_n}"
        rule_tone = "pass" if (own == 0 and deck_n == 0) else "stop"
        rule_cap = (f"{drc.get('rules_checked')} declared rules and a foundry "
                    f"runset, both against the {drc.get('target') or 'device'}.")

    if frame.get("outer_um"):
        ow, oh = frame["outer_um"]
        offered = frame.get("footprint_is_offered")
        f_tone = "pass" if offered else "stop"
        f_val = f"{ow:.0f} &times; {oh:.0f}"
        f_cap = ("micrometres, one the process offers, boundary centred on the "
                 "origin." if offered else
                 "micrometres. This is NOT among the footprints the process "
                 "offers.")
    else:
        f_tone, f_val = "absent", "not drawn"
        f_cap = ("No chip frame was drawn, so the footprint, centring and "
                 "exclusion rules had nothing to compare and reported nothing.")

    nr = state.get("newer_run")
    stale_banner = (
        f'<p class="stale-banner">This page describes run '
        f'<code>{_esc(state["run_id"])}</code>. A later completed run exists, '
        f'<code>{_esc(nr)}</code>, and this page does not describe it.</p>'
        if nr else "")

    missing_line = (
        f" The stages that produced nothing are "
        f"{', '.join(f'<code>{_esc(m)}</code>' for m in missing)}."
        if missing else "")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(state['design'])} - design flow</title>
<style>{_css()}</style></head><body>
<div class="wrap">
<header class="top">
  {stale_banner}
  <p class="eyebrow">{_esc(state['design'])} &middot; run {_esc(state['run_id'])}
     &middot; {_num(state['elapsed_s'])} s &middot;
     {_esc(drc.get('target') or 'device')} level</p>
  <h1>Where the design stands</h1>
  <p class="sub">Every state on this page is read from the artifacts of one run.
  A stage that was never executed is shown as never executed and not as passing,
  which is the distinction the page exists to draw: a verdict covers what was
  asked, and a question is only asked about a metric some stage produced.
  <strong>{ran} of {total} stages produced a result.</strong>{missing_line}</p>
</header>

<div class="meters">
  <div class="meter {v_tone}">
    <p class="k">acceptance targets</p>
    <div class="val">{v.get('n_pass', 0)} / {v.get('n_targets', 0)}</div>
    <p class="cap">verdict {_esc(verdict)}. {v.get('n_fail', 0)} unmet,
       {v.get('n_missing', 0)} not produced by the stages that ran.</p>
  </div>
  <div class="meter {rule_tone}">
    <p class="k">rule checks</p>
    <div class="val">{rule_val}</div>
    <p class="cap">{rule_cap}</p>
  </div>
  <div class="meter {f_tone}">
    <p class="k">die footprint</p>
    <div class="val">{f_val}</div>
    <p class="cap">{f_cap}</p>
  </div>
  <div class="meter {cover_tone}">
    <p class="k">stage coverage</p>
    <div class="val">{ran} / {total}</div>
    <p class="cap">No result exists for a stage that did not run. Enabling one
       may change the verdict.</p>
  </div>
</div>

<h2>The flow</h2>
<div class="legend">
  <span><i class="chip pass">ran</i> produced a result in this run</span>
  <span><i class="chip absent">not executed</i> no result exists</span>
  <span>Each stage is placed one level below the deepest input it needs.</span>
</div>
{''.join(tiers)}

<h2>What was asked, and by how much it is met</h2>
<p>The bar is headroom: the distance from the value to the bound that constrains
it, as a fraction of that bound. A full bar is comfortable, an empty one sits on
the limit, and an absent one means the criterion was not of a form this page
parses. Headroom is not margin against the process, which is a different question
and is answered by <code>picchain corners</code>.</p>
<div class="tablewrap"><table>
  <thead><tr><th>Metric</th><th>Criterion</th><th style="text-align:right">Actual</th>
    <th>Severity</th><th>Headroom</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>

<h2>What the run raised</h2>
<p>Conditions the run reported that no target expresses. They are grouped by what
must be done about them rather than by the stage that raised them. The grouping
is a heuristic over the text and the wording is the run's own; anything the
heuristic does not recognise is left as recorded, so a warning is only ever
demoted by it and never promoted.</p>
<div class="groups">{groups_html}</div>

<footer>Written by <code>picchain dashboard</code> from
{_esc(state['run_id'])}. Re-run the command to refresh it.</footer>
</div></body></html>
"""


def render(run_dir: Path, out_path: Path | None = None,
           strict: bool = True) -> Path:
    """Write the dashboard for a run and return where it was written.

    The page is checked against its own state before it is written. With
    `strict` a contradiction raises rather than being published, on the reasoning
    that a page nobody can trust is worse than no page.
    """
    run_dir = Path(run_dir)
    state = collect(run_dir)
    state["newer_run"] = newer_run(run_dir.parent, state.get("run_id") or "")
    problems = selfcheck(state)
    if problems and strict:
        raise RuntimeError(
            "the dashboard contradicts itself and was not written:"
            + chr(10) + "  " + (chr(10) + "  ").join(problems))
    state["selfcheck"] = problems
    out = Path(out_path) if out_path else run_dir / "dashboard.html"
    out.write_text(render_html(state), encoding="utf-8")
    return out
