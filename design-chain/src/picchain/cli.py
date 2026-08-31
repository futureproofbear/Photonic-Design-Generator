"""Headless CLI for the PIC design chain.

    picchain run     <design.yaml> [--stages ...] [--tag ...] [--json]
    picchain verify  <design.yaml> [--run latest]
    picchain report  <design.yaml> [--run latest]
    picchain sweep   <design.yaml> --param a.b.c --values 1,2,3 --metric x.y
    picchain show    <design.yaml> [--metric dotted.path]
    picchain history <design.yaml> [--prune]
    picchain doctor

Exit codes (this is the contract an agent or CI iterates against):
    0  everything asked for succeeded; `verify` verdict PASS
    1  a stage raised
    2  `verify` verdict FAIL (a target of severity `must` is unmet, or the
       material provenance gate is blocking)
    3  bad invocation / design file
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional

import typer

from .artifacts import RunContext, dump_json, load_json, new_run_id
from .config import Design, get_dotted, set_dotted, walk_dotted
from .preflight import assert_ready
from .materials import MaterialLibrary
from .stages import DEPENDENCIES, STAGES

app = typer.Typer(add_completion=False, help="Headless PIC design chain")

EXIT_OK, EXIT_ERROR, EXIT_VERIFY_FAIL, EXIT_USAGE = 0, 1, 2, 3


def _library(d: Design) -> MaterialLibrary:
    """The material library this design names, derived from the design itself.

    Held apart from `_load` so that it can be rebuilt after an override. The
    library was previously constructed once from the design as it arrived on
    disk, and every override path then re-read the design and discarded the
    library that came with it. `--set platform.materials_file=...` therefore
    reached `design.resolved.json` and never reached a solver: the run recorded
    one material file and solved with another.

    The symptom was silence. A sweep of the radio-frequency permittivity across
    plus and minus fifteen per cent returned a capacitance identical in the last
    bit at every point, which reads as a quantity the design is insensitive to
    rather than as an override that was dropped.
    """
    return MaterialLibrary(d.platform.materials_file) if d.platform.materials_file else MaterialLibrary()


def _load(design_path: Path) -> tuple[Design, MaterialLibrary]:
    d = Design.load(design_path)
    return d, _library(d)


def _resolve_stages(requested: list[str]) -> list[str]:
    """The stages to run, closed over their dependencies and correctly ordered.

    The order is a topological sort of the dependency map, with the registration
    order of `STAGES` as the tie-break so that an unconstrained pair keeps its
    familiar sequence. It was previously the registration order alone, which is
    not the same thing: `fdtd` is registered before `grating` and depends on it,
    so a run naming both executed `fdtd` first and it raised. A declared order
    that contradicts the dependency map is a trap for whoever writes the list,
    and the map is the thing that knows.
    """
    order = list(STAGES)
    want: set[str] = set()

    def add(s: str):
        if s not in STAGES:
            raise typer.BadParameter(f"unknown stage {s!r}; choose from {', '.join(order)}")
        if s in want:
            return
        for dep in DEPENDENCIES[s]:
            add(dep)
        want.add(s)

    for s in requested:
        add(s)

    out: list[str] = []
    done: set[str] = set()
    while len(out) < len(want):
        ready = [s for s in order
                 if s in want and s not in done
                 and all(d in done for d in DEPENDENCIES[s])]
        if not ready:
            stuck = sorted(want - done)
            raise typer.BadParameter(
                f"the dependencies of {', '.join(stuck)} cannot be satisfied; "
                "the stage graph contains a cycle"
            )
        out.append(ready[0])
        done.add(ready[0])
    return out


def _latest_run(design_path: Path) -> Path:
    p = design_path.parent / "runs" / "latest.json"
    if not p.exists():
        raise typer.BadParameter(f"no runs yet under {design_path.parent / 'runs'}")
    return Path(load_json(p)["path"])


@app.command()
def run(
    design: Path = typer.Argument(..., exists=True, help="path to design.yaml"),
    stages: str = typer.Option("", "--stages", "-s", help="comma-separated subset; default = design.stages"),
    tag: str = typer.Option("", "--tag", help="suffix for the run id"),
    as_json: bool = typer.Option(False, "--json", help="print the metric tree to stdout"),
    figures: bool = typer.Option(True, "--figures/--no-figures"),
    report: bool = typer.Option(True, "--report/--no-report"),
    set_: list[str] = typer.Option([], "--set", help="override a design field, e.g. grating.length_um=9000"),
):
    """Run the chain for one design."""
    try:
        d, lib = _load(design)
    except Exception as exc:
        typer.echo(f"error: cannot load design: {exc}", err=True)
        raise typer.Exit(EXIT_USAGE)

    for ov in set_:
        if "=" not in ov:
            typer.echo(f"error: --set expects key=value, got {ov!r}", err=True)
            raise typer.Exit(EXIT_USAGE)
        key, val = ov.split("=", 1)
        _apply_override(d, key, val)
    lib = _library(d)          # an override may have named another material file

    chosen = _resolve_stages([s.strip() for s in stages.split(",") if s.strip()] or d.stages)
    ctx = RunContext(design_dir=design.parent, run_id=new_run_id(tag or d.meta.name)).ensure()
    dump_json(ctx.run_dir / "design.resolved.json", json.loads(d.model_dump_json()))
    # What this run set out to do, written before it does any of it. A run
    # invoked with `--stages fdtd` executes three stages while the design
    # declares seventeen, and without this the two cannot be told apart from the
    # outside: anything reading a part-finished run would infer the wrong stage
    # as the one underway.
    dump_json(ctx.run_dir / "run.plan.json", {"stages": chosen})

    # What each stage cost, recorded per stage rather than only for the run.
    #
    # A run-level total cannot say which stage to pace against, which to expect
    # to take hours, or whether a stage that has not returned is slow or stuck.
    # All three questions were asked of this chain and answered by guesswork: a
    # 20-minute solve was reported as a hang and killed, and a 3-hour one was
    # declared dead 13 minutes in. Neither would have survived a table of what
    # each stage costs.
    #
    # TWO clocks are recorded, and the distinction is not pedantic. Wall clock
    # counts the time the machine spent suspended: a corner sweep left overnight
    # reported one corner at 8.2 hours against 70 seconds for its neighbours, and
    # the difference was the machine asleep. That was read as a runaway solver
    # and a defect was reported against the period solve which did not exist.
    # Processor time does not advance across suspend, so the pair together
    # distinguish a slow stage from a suspended one, and neither alone does.
    # Where a stage delegates to an external solver in another process, that
    # solver's own reported time is the one to believe over either.
    # Preconditions on the design file, before any solver is started. A design
    # whose declared fields contradict each other is knowable in milliseconds and
    # running it first costs half an hour and returns numbers describing a
    # different device. See picchain/preflight.py for the case that produced this.
    assert_ready(d)

    status = "ok"
    timings: dict[str, float] = {}
    cpu: dict[str, float] = {}
    for s in chosen:
        typer.echo(f"[{s}] ...", err=True)
        t0, c0 = time.perf_counter(), time.process_time()
        try:
            ctx.current_stage = s
            ctx.stages_run.append(s)
            STAGES[s](d, ctx, lib)
        except Exception as exc:
            timings[s] = round(time.perf_counter() - t0, 3)
            cpu[s] = round(time.process_time() - c0, 3)
            status = f"failed:{s}"
            ctx.warn(f"stage {s} raised: {exc}")
            traceback.print_exc()
            break
        timings[s] = round(time.perf_counter() - t0, 3)
        cpu[s] = round(time.process_time() - c0, 3)
        sec = ctx.metrics.get(s)
        if isinstance(sec, dict):
            sec["elapsed_s"] = timings[s]
            sec["cpu_s"] = cpu[s]
        gap = timings[s] - cpu[s]
        note = f"  (cpu {cpu[s]:.1f}s)" if gap > max(60.0, 0.5 * timings[s]) else ""
        typer.echo(f"[{s}] {timings[s]:.1f}s{note}", err=True)
    ctx.metrics["stage_timings_s"] = timings
    ctx.metrics["stage_cpu_s"] = cpu

    metrics_path = ctx.finalise(status)

    figs: list[Path] = []
    if figures and status == "ok":
        try:
            from .report import make_figures
            figs, failed_figs = make_figures(ctx.run_dir)
            # A drawing that fails removes a figure from the run and leaves the
            # published copy at its previous version, which a reader cannot
            # detect. Six of nineteen were lost this way on 2026-08-18 under
            # memory pressure, and every one rendered correctly on a second
            # call. The finding is raised so the loss is on the record.
            if failed_figs:
                ctx.warn(
                    f"{len(failed_figs)} drawing(s) failed and this run's figure set is "
                    "incomplete: " + "; ".join(failed_figs)
                    + ". Re-render with `picchain report <design>` and confirm with "
                    "tools/check_figures_current.py before any document is shown",
                    key="report.figure_set_incomplete",
                )
            ctx.finalise(status)
        except Exception as exc:
            ctx.warn(f"figure rendering failed: {exc}")
            ctx.finalise(status)
    if report:
        try:
            from .report import render_markdown
            (ctx.run_dir / "report.md").write_text(render_markdown(metrics_path, figs), encoding="utf-8")
        except Exception as exc:
            typer.echo(f"warning: report rendering failed: {exc}", err=True)

    doc = load_json(metrics_path)
    if as_json:
        typer.echo(json.dumps(doc, indent=2))
    else:
        _print_summary(doc, ctx.run_dir)

    if status != "ok":
        raise typer.Exit(EXIT_ERROR)
    ver = doc["metrics"].get("verify")
    if ver and ver["verdict"] != "PASS":
        raise typer.Exit(EXIT_VERIFY_FAIL)


def _assign(node: Any, key: str, value: Any) -> None:
    if isinstance(node, dict):
        node[key] = value
    else:
        setattr(node, key, value)


def _apply_override(d: Design, dotted: str, raw: str) -> None:
    parts = dotted.split(".")
    node = walk_dotted(d, parts[:-1])
    cur = node.get(parts[-1]) if isinstance(node, dict) else getattr(node, parts[-1])
    try:
        val: Any = json.loads(raw)
    except Exception:
        val = raw
    # An optional field is cleared with `null`, and coercion against the type of
    # its present value would refuse that. `layout.draw_periods=null` is the
    # instruction that draws the whole grating, so this path is not an edge case.
    if val is None or cur is None:
        _assign(node, parts[-1], val)
        return
    if isinstance(cur, bool):          # bool is a subclass of int; test it first
        val = bool(val)
    elif isinstance(cur, float):
        val = float(val)
    elif isinstance(cur, int):
        val = int(val)
    _assign(node, parts[-1], val)


def _print_summary(doc: dict, run_dir: Path) -> None:
    m = doc["metrics"]
    typer.echo("")
    typer.echo(f"run {doc['run_id']}  status={doc['status']}  {doc['elapsed_s']}s")
    typer.echo(f"artifacts: {run_dir}")
    for sec, keys in [
        ("mode", ["n_eff_bare", "n_g", "dn_eff_posts", "single_mode"]),
        ("grating", ["period_nm", "kappa_per_cm", "kappa_L", "bragg_wavelength_nm",
                     "peak_reflectivity", "fwhm_GHz", "penetration_depth_mm"]),
        ("eo", ["eo_overlap_gamma", "tuning_MHz_per_V", "VpiL_V_cm", "lumped_RC_bandwidth_MHz"]),
        ("cavity", ["fsr_GHz", "pockels_lever", "laser_tuning_MHz_per_V",
                    "mode_hop_free_range_GHz", "chirp_nonlinearity_rms_percent",
                    "schawlow_townes_henry_linewidth_kHz", "smsr_dB"]),
        ("drc", ["rules_checked", "error_violations", "clean"]),
    ]:
        s = m.get(sec)
        if not s or s.get("enabled") is False:
            continue
        typer.echo(f"  {sec}:")
        for k in keys:
            if k in s:
                v = s[k]
                typer.echo(f"    {k:38s} {v:.6g}" if isinstance(v, (int, float)) and not isinstance(v, bool)
                           else f"    {k:38s} {v}")
    ver = m.get("verify")
    if ver:
        typer.echo(f"  verify: {ver['verdict']}  ({ver['n_pass']}/{ver['n_targets']} targets met; "
                   f"{ver['must_failures']} unmet at severity must, "
                   f"{ver['should_failures']} at severity should)")
        for r in ver["rows"]:
            if r["status"] != "pass":
                typer.echo(f"    [{r['status']:7s}] {r['metric']} {r['criterion']} "
                           f"actual={r['actual']}")
    for w in doc.get("warnings", []):
        typer.echo(f"  ! {w}")


@app.command()
def verify(
    design: Path = typer.Argument(..., exists=True),
    run_path: Optional[Path] = typer.Option(None, "--run", help="metrics.json; defaults to latest"),
):
    """Re-evaluate the acceptance targets against an existing run."""
    d, lib = _load(design)
    mp = run_path or _latest_run(design)
    doc = load_json(mp)
    ctx = RunContext(design_dir=design.parent, run_id=doc["run_id"])
    ctx.metrics = doc["metrics"]
    from .stages.s07_verify import run as verify_run
    res = verify_run(d, ctx, lib)
    typer.echo(json.dumps(res, indent=2))
    raise typer.Exit(EXIT_OK if res["verdict"] == "PASS" else EXIT_VERIFY_FAIL)


@app.command()
def report(
    design: Path = typer.Argument(..., exists=True),
    run_path: Optional[Path] = typer.Option(None, "--run"),
):
    """(Re)render report.md and the figure set for a run."""
    mp = run_path or _latest_run(design)
    from .report import make_figures, render_markdown
    figs, failed_figs = make_figures(mp.parent)
    for f in failed_figs:
        typer.echo(f"  ! drawing failed, the figure set is incomplete: {f}", err=True)
    out = mp.parent / "report.md"
    out.write_text(render_markdown(mp, figs), encoding="utf-8")
    typer.echo(str(out))
    from .dashboard import render as render_dashboard
    typer.echo(str(render_dashboard(mp.parent)))


def _open_in_browser(path: Path) -> None:
    """Show an HTML file rendered rather than as source.

    The default handler for `.html` is frequently an editor, and handing the
    file to it produces a page of markup where a page was wanted. A browser is
    therefore looked for first, and the registered handler is the fallback
    rather than the first choice.
    """
    import subprocess
    import webbrowser

    uri = path.resolve().as_uri()
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/firefox",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for exe in candidates:
        if Path(exe).is_file():
            try:
                subprocess.Popen([exe, uri],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    webbrowser.open(uri)


@app.command()
def dashboard(
    design: Path = typer.Argument(..., exists=True),
    run_path: Optional[Path] = typer.Option(None, "--run"),
    out: Optional[Path] = typer.Option(None, "--out", help="where to write it"),
    open_it: bool = typer.Option(False, "--open", help="open in the browser"),
):
    """Write a self-contained HTML view of where the design stands.

    One file, no external reference, so it opens from disk. It shows which
    stages produced a result and when each last did, which targets are met and
    by how much, and what the run raised that no target expresses.
    """
    mp = run_path or _latest_run(design)
    from .dashboard import render
    written = render(mp.parent, out)
    typer.echo(str(written))
    if open_it:
        _open_in_browser(written)


@app.command()
def show(
    design: Path = typer.Argument(..., exists=True),
    metric: str = typer.Option("", "--metric", help="dotted path; omit for the whole tree"),
    run_path: Optional[Path] = typer.Option(None, "--run"),
):
    """Print metrics from a run (machine-readable)."""
    mp = run_path or _latest_run(design)
    doc = load_json(mp)
    node: Any = doc["metrics"]
    if metric:
        for p in metric.split("."):
            node = node[p]
    typer.echo(json.dumps(node, indent=2))


@app.command()
def history(
    design: Path = typer.Argument(..., exists=True),
    prune: bool = typer.Option(False, "--prune",
        help="delete the regenerable artefacts of every run but the newest complete one"),
    out: Optional[Path] = typer.Option(None, "--out",
        help="directory for the summary; default is `history/` beside the design"),
):
    """Roll the run tree up into one summary, and optionally prune it.

    THE CHAIN WRITES A RUN DIRECTORY PER INVOCATION AND NOTHING ROLLS IT UP. On
    a design of any age the findings therefore exist only as a pile of
    timestamped directories, and the pile is mostly field data: on the tree that
    prompted this command, 912 MB of 931 was `.npz`, another 103 MB was repeated
    copies of the same mask, and everything carrying a conclusion came to about
    four megabytes spread over 67 `metrics.json` files.

    That shape has two costs. Nobody can see what a hundred runs established
    without opening a hundred files, and the tree cannot be pruned without
    losing the findings, so it is not pruned and it grows.

    This writes `RUNS.md` and `runs.json`, one row per run that produced a
    metric. `--prune` then deletes what regenerates: the field arrays, the
    figures and every mask but the newest complete run's. Each run keeps its
    `design.resolved.json`, so any of them can be rebuilt.
    """
    runs_dir = design.parent / "runs"
    if not runs_dir.is_dir():
        typer.echo(f"no run tree under {runs_dir}", err=True)
        raise typer.Exit(EXIT_USAGE)
    dest = out or (design.parent / "history")
    dest.mkdir(parents=True, exist_ok=True)

    def dig(doc: dict, *path: str) -> Any:
        node: Any = doc
        for k in path:
            if not isinstance(node, dict):
                return None
            node = node.get(k)
        return node

    FIELDS = [
        ("kappa", ("grating", "kappa_per_cm")),
        ("R", ("grating", "peak_reflectivity")),
        ("fwhm", ("grating", "fwhm_GHz")),
        ("fsr", ("cavity", "fsr_GHz")),
        ("lever", ("cavity", "pockels_lever")),
        ("sync", ("cavity", "mode_hop_free_range_synchronous_GHz")),
        ("smsr", ("cavity", "smsr_dB")),
        ("linewidth", ("cavity", "schawlow_townes_henry_linewidth_kHz")),
        ("tuning", ("eo", "tuning_MHz_per_V")),
        ("gamma", ("eo", "eo_overlap_gamma")),
        ("adiabaticity", ("taper", "min_adiabaticity")),
        ("facet_dB", ("facet", "total_loss_dB")),
        ("drc", ("drc", "error_violations")),
    ]
    rows: list[dict] = []
    for mp in sorted(runs_dir.glob("*/metrics.json")):
        try:
            doc = load_json(mp)
        except Exception:
            continue
        met = doc.get("metrics", {})
        vp = mp.parent / "verify.json"
        ver = {}
        if vp.exists():
            try:
                ver = load_json(vp)
            except Exception:
                ver = {}
        row = {"run": mp.parent.name, "verdict": ver.get("verdict")}
        row.update({name: dig(met, *path) for name, path in FIELDS})
        # The external solver is the expensive one and its disagreements are the
        # point, so it is carried separately rather than averaged into a column.
        row["fdtd_structure"] = dig(met, "fdtd", "structure")
        row["fdtd_kappa"] = dig(met, "fdtd", "kappa_per_cm")
        rows.append(row)

    dump_json(dest / "runs.json", rows)
    names = ["run", "verdict"] + [n for n, _ in FIELDS]
    fmt = lambda v: "" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
    lines = [
        "# Every run that produced a metric",
        "",
        "Written by `picchain history`. The run tree holds the field data, which is",
        "large and regenerable; this is what the runs established, so that pruning",
        "the tree costs nothing. `runs.json` carries the same rows as data.",
        "",
        "| " + " | ".join(names) + " |",
        "|" + "---|" * len(names),
    ]
    lines += ["| " + " | ".join(fmt(r[n]) for n in names) + " |" for r in rows]
    fd = [r for r in rows if r["fdtd_kappa"] is not None]
    if fd:
        lines += ["", "## Runs of the external solver", "",
                  "| run | structure | kappa /cm |", "|---|---|---|"]
        lines += [f"| {r['run']} | {r['fdtd_structure']} | {fmt(r['fdtd_kappa'])} |" for r in fd]
    (dest / "RUNS.md").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    typer.echo(f"{len(rows)} runs summarised into {dest}")

    if not prune:
        return
    complete = [mp.parent for mp in sorted(runs_dir.glob("*/metrics.json"))]
    keep = complete[-1].name if complete else ""
    freed = removed = 0
    for path in runs_dir.rglob("*"):
        if not path.is_file() or path.parent.name == keep:
            continue
        regenerable = path.suffix in {".npz", ".png"} or (
            path.suffix in {".gds", ".oas"} and "markers" not in path.name)
        if regenerable:
            freed += path.stat().st_size
            path.unlink()
            removed += 1
    typer.echo(f"pruned {removed} regenerable files, {freed / 1e6:.0f} MB; "
               f"field data retained for {keep or 'no complete run'}")


@app.command()
def sweep(
    design: Path = typer.Argument(..., exists=True),
    param: str = typer.Option(..., "--param", help="dotted design field to sweep"),
    values: str = typer.Option(..., "--values", help="comma-separated values"),
    metrics: str = typer.Option("", "--metric", help="comma-separated dotted metric paths to collect"),
    stages: str = typer.Option("", "--stages", "-s"),
    out: Optional[Path] = typer.Option(None, "--out", help="write results as JSON here"),
):
    """Sweep one design parameter and collect metrics. Nothing is cached: each
    point is a full, reproducible run under runs/."""
    d0, lib = _load(design)
    chosen = _resolve_stages([s.strip() for s in stages.split(",") if s.strip()] or d0.stages)
    want = [m.strip() for m in metrics.split(",") if m.strip()]
    vals = [v.strip() for v in values.split(",") if v.strip()]

    rows = []
    for i, v in enumerate(vals):
        d, _ = _load(design)
        _apply_override(d, param, v)
        lib_i = _library(d)    # the swept parameter may be the material file
        ctx = RunContext(design_dir=design.parent, run_id=new_run_id(f"sweep{i:03d}")).ensure()
        try:
            for s in chosen:
                ctx.current_stage = s
                ctx.stages_run.append(s)
                STAGES[s](d, ctx, lib_i)
            ctx.finalise("ok", update_latest=False)
            row = {"param": param, "value": v}
            row.update({m: ctx.get(m) for m in want} if want else {"metrics": ctx.metrics})
        except Exception as exc:
            ctx.finalise("failed", update_latest=False)
            row = {"param": param, "value": v, "error": str(exc)}
        rows.append(row)
        typer.echo(json.dumps(row), err=False)

    if out:
        dump_json(out, {"design": str(design), "param": param, "rows": rows})
        typer.echo(f"written {out}", err=True)


@app.command()
def corners(
    design: Path = typer.Argument(..., exists=True, help="path to design.yaml"),
    stages: str = typer.Option("", "--stages", "-s", help="subset; default = design.stages"),
    mode: str = typer.Option("", "--mode", help="onefactor or factorial; default = design.corners.mode"),
    tag: str = typer.Option("corners", "--tag"),
):
    """Re-run the chain at the edges of the process window.

    A single run describes the design as drawn. What is fabricated is a
    distribution, and the question a tape-out asks is not whether the nominal
    design passes but how much of the distribution does. Each parameter named in
    ``corners.parameters`` is displaced by the excursion given, and the spread of
    every target metric across those corners is reported alongside the verdict at
    each one.
    """
    import itertools

    try:
        d, lib = _load(design)
    except Exception as exc:
        typer.echo(f"error: cannot load design: {exc}", err=True)
        raise typer.Exit(EXIT_USAGE)

    cfg = d.corners
    if not cfg.parameters:
        typer.echo("error: design.corners.parameters is empty; nothing to vary", err=True)
        raise typer.Exit(EXIT_USAGE)

    from .stages.s07_verify import _evaluate as _evaluate_target
    design_targets = list(d.targets)
    metrics = cfg.metrics or [t.metric for t in d.targets]

    # A corner verdict judges only the metrics named here, so a `must` row left
    # out of the list passes every corner without being read. Two such rows were
    # added to a design and not to this list, and the sweep reported 9 of 9 while
    # the failing one was never evaluated; it returned 4 of 9 once they were
    # added. Any must-target absent from the list is added and the addition is
    # announced, because a silent pass is the failure this guards.
    # CORRECTED 2026-08-16. The first version of this added every absent `must`
    # target to the sweep. The corner stage list is derived from the metrics, so
    # that pulled `layout` and `drc` into a physics sweep, and every corner then
    # failed on rows a corner cannot move: a perturbation of film thickness does
    # not change whether the mask is complete. Twenty-four of twenty-four corners
    # failed for a structural reason.
    #
    # A `must` row is added only where the stage producing it is already being
    # run for the metrics that were declared. The rest are named and left out,
    # so the omission stays visible without corrupting the sweep.
    # Reachability is the RESOLVED stage closure, not the stages the declared
    # metrics name directly. `mode` runs as a dependency of `grating` even when
    # no declared metric mentions it, so `mode.n_guided_modes` is evaluable and
    # was being reported unreachable.
    _declared = sorted({m.split(".", 1)[0] for m in metrics if "." in m} & set(STAGES))
    declared_stages = set(_resolve_stages(_declared or list(d.stages)))
    must_absent = [t.metric for t in d.targets
                   if t.severity == "must" and t.metric not in metrics]
    addable = [m for m in must_absent if m.split(".", 1)[0] in declared_stages]
    unreachable = [m for m in must_absent if m not in addable]
    if addable:
        metrics = list(metrics) + addable
        typer.echo(
            "  ! these `must` targets were absent from corners.metrics and are produced by "
            "stages this sweep already runs; they have been added: " + ", ".join(addable),
            err=True)
    if unreachable:
        typer.echo(
            "  ! these `must` targets are not evaluated at any corner, their stages being "
            "outside this sweep: " + ", ".join(unreachable)
            + ". They are properties of the mask rather than of the process point, so the "
            "corner verdict says nothing about them", err=True)

    # A corner sweep runs the chain once per corner, so it inherits every cost
    # the stage list carries, multiplied. Defaulting it to the whole design is
    # therefore wrong in a way that a single run is not: with the external solver
    # in the list, nine corners of a three-hour stage is a day and a night spent
    # measuring the sensitivity of a grating to its post gap.
    #
    # The stages actually needed are those producing the declared corner metrics,
    # closed over their dependencies. That set is derived here rather than
    # demanded of whoever writes the design, and `--stages` overrides it where a
    # sweep genuinely wants more.
    asked = [s.strip() for s in stages.split(",") if s.strip()]
    if asked:
        chosen = _resolve_stages(asked)
    else:
        needed = sorted({m.split(".", 1)[0] for m in metrics if "." in m} & set(STAGES))
        chosen = _resolve_stages(needed or list(d.stages))
        skipped = [s for s in d.stages if s not in chosen]
        if skipped:
            typer.echo(
                f"corners runs {len(chosen)} stages producing the declared metrics: "
                f"{', '.join(chosen)}. Not run, no declared metric requiring them: "
                f"{', '.join(skipped)}. Pass --stages to override",
                err=True,
            )
    names = list(cfg.parameters)
    use_mode = mode or cfg.mode

    # A sweep run at a mode the design file does not declare is a sweep that
    # cannot be reproduced from the design file. One design's every
    # process-window claim rested on an 81-corner factorial while its file read
    # `onefactor`, so `picchain corners <design>` returned nine corners and the
    # report's own reproduction section gave no override. The divergence is
    # knowable at exactly this point and nowhere later, `corners.md` recording
    # the mode that ran and the design file recording the mode that was meant.
    if mode and mode != cfg.mode:
        typer.echo(
            f"  ! this sweep runs `{mode}` and the design declares `{cfg.mode}`. The result "
            f"cannot be reproduced from the design file alone. Set `corners.mode: {mode}` in "
            "the design, or record the override beside every figure this sweep produces",
            err=True,
        )

    # A corner excursion must be one a fabrication run can deliver on its own.
    # Bragg posts and the ridge they sit beside are drawn on one layer and
    # printed by one exposure and one etch, so a lithographic excursion moves
    # the gap between them and their own dimensions together, and on a grating
    # of order above one the two terms oppose through the duty cycle. Declaring
    # the gap alone reported a 63.6 % spread in kappa for an excursion that
    # produces a small fraction of it, and omitted the duty term entirely.
    #
    # `process.bias_um` is the field that expresses the excursion the process
    # actually delivers: a width grows by the full bias and a gap between two
    # features on the same layer shrinks by the same amount.
    _drawn = [n for n in names
              if n.startswith(("grating.post_", "waveguide.")) and n.endswith("_um")]
    if _drawn and not any(n.startswith("process.bias_um") for n in names):
        typer.echo(
            "  ! this window varies a drawn dimension without varying the process bias: "
            + ", ".join(_drawn)
            + ". Features on one layer move together under a lithographic excursion, so an "
            "excursion on one of them alone is not one the process delivers. Consider "
            "`process.bias_um.<layer>`, which moves every dimension on that layer coherently. "
            "See rules/generic/parameter-scans.md",
            err=True,
        )

    if use_mode == "factorial":
        combos = list(itertools.product(*[(-1, 0, 1)] * len(names)))
    elif use_mode == "onefactor":
        combos = [tuple([0] * len(names))]
        for i in range(len(names)):
            for s in (-1, 1):
                c = [0] * len(names)
                c[i] = s
                combos.append(tuple(c))
    else:
        typer.echo(f"error: unknown corner mode {use_mode!r}", err=True)
        raise typer.Exit(EXIT_USAGE)

    typer.echo(f"{len(combos)} corners over {len(names)} parameters, "
               f"{len(chosen)} stages each", err=True)

    rows: list[dict[str, Any]] = []
    for n, combo in enumerate(combos):
        dc = d.model_copy(deep=True)
        label_parts = []
        for name, sign in zip(names, combo):
            delta = cfg.parameters[name] * sign
            nominal = _read_dotted(dc, name)
            _apply_override(dc, name, str(nominal + delta))
            label_parts.append(f"{name}{'+' if sign > 0 else ''}{sign}")
        label = "nominal" if all(s == 0 for s in combo) else ",".join(
            p for p, s in zip(label_parts, combo) if s != 0)

        ctx = RunContext(design_dir=design.parent,
                         run_id=new_run_id(f"{tag}-{n:03d}")).ensure()
        # A corner resolves a DIFFERENT design from the one on disk, and it must
        # record which. Without this the hash cannot be taken and a reader cannot
        # tell a stage last run on the design from one last run on a deliberate
        # perturbation of it. The dashboard reported the two alike.
        dump_json(ctx.run_dir / "design.resolved.json", json.loads(dc.model_dump_json()))
        dump_json(ctx.run_dir / "run.plan.json",
                  {"stages": chosen, "corner": label, "combo": list(combo)})
        status = "ok"
        for s in chosen:
            try:
                ctx.current_stage = s
                ctx.stages_run.append(s)
                STAGES[s](dc, ctx, _library(dc))
            except Exception as exc:
                status = f"failed:{s}"
                ctx.warn(f"stage {s} raised: {exc}")
                break
        ctx.finalise(status)

        # A corner is judged on the metrics it declares, and not on the whole
        # verify verdict.
        #
        # The sweep runs only the stages producing those metrics, so the targets
        # naming anything else have no value to be compared against and would
        # report as missing. Reading the full verdict then failed every corner
        # for reasons that had nothing to do with the corner, and reading it
        # from a stage that was not run reported None, which is worse: it looks
        # like an answer.
        ver = ctx.get("verify") or {}
        by_metric = {tg.metric: tg for tg in design_targets}
        # Severity decides the verdict here exactly as it does in `verify`, and
        # it did not until 2026-08-12. Every unmet row was counted, so a target
        # carried at `info` failed the corner. `info` exists to be reported
        # without blocking, and a sweep that blocks on it reports a process
        # window narrower than the design has. The corner that exposed this was
        # judged on the mode-hop-free range from zero bias, which is set by
        # where the mode comb happens to sit and is placed by thermal tuning at
        # commissioning; it is carried at `info` for that reason.
        #
        # Each metric is judged once. The list was built by iterating the
        # declared metrics without deduplicating them, so a metric named twice
        # in `corners.metrics` appeared twice in the failure list.
        outside_must, outside_should, judged = [], [], 0
        for m in dict.fromkeys(metrics):
            tg = by_metric.get(m)
            if tg is None:
                continue
            judged += 1
            if _evaluate_target(tg, ctx.get(m))["status"] == "pass":
                continue
            if tg.severity == "must":
                outside_must.append(m)
            elif tg.severity == "should":
                outside_should.append(m)
        outside = outside_must + outside_should
        verdict = ver.get("verdict") or (
            None if not judged else ("PASS" if not outside_must else "FAIL"))
        row = {"corner": label, "combo": list(combo), "status": status,
               "run_id": ctx.run_id, "verdict": verdict,
               "metrics_judged": judged, "metrics_outside": outside,
               "must_failures": ver.get("must_failures") or outside_must,
               "should_failures": outside_should,
               "metrics": {m: ctx.get(m) for m in metrics}}
        rows.append(row)
        typer.echo(f"  [{n + 1}/{len(combos)}] {label:38s} {row['verdict']}", err=True)

    summary = {}
    for m in metrics:
        vals = [r["metrics"].get(m) for r in rows
                if isinstance(r["metrics"].get(m), (int, float))]
        # The nominal row by name, not by position. In onefactor mode the
        # nominal is generated first and rows[0] happened to be right; in
        # factorial mode rows[0] is a corner combination, so the column headed
        # "nominal" carried a corner's value and every spread percentage was
        # taken against it. On a niobate design the table printed a nominal
        # reflectivity of 0.9260 where the design gives 0.8549.
        nom_row = next((r for r in rows if r["corner"] == "nominal"), None)
        if nom_row is None and rows:
            nom_row = rows[0]
        nom = nom_row["metrics"].get(m) if nom_row else None
        if vals:
            summary[m] = {"nominal": nom, "min": min(vals), "max": max(vals),
                          "spread": max(vals) - min(vals),
                          "spread_pct_of_nominal":
                              (max(vals) - min(vals)) / nom * 100
                              if isinstance(nom, (int, float)) and nom else None}

    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    doc = {"design": str(design), "mode": use_mode, "parameters": cfg.parameters,
           "stages": chosen, "n_corners": len(rows),
           "n_pass": passed, "n_fail": len(rows) - passed,
           "summary": summary, "rows": rows}

    out_dir = design.parent / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_json(out_dir / "corners.json", doc)
    (out_dir / "corners.md").write_text(_corners_markdown(doc), encoding="utf-8")

    typer.echo("")
    typer.echo(f"{passed}/{len(rows)} corners pass")
    for m, s in summary.items():
        pct = f"{s['spread_pct_of_nominal']:.1f}%" if s["spread_pct_of_nominal"] else "-"
        typer.echo(f"  {m:46s} {s['min']:.6g} .. {s['max']:.6g}  ({pct})")
    typer.echo(f"written {out_dir / 'corners.md'}")
    raise typer.Exit(EXIT_OK if passed == len(rows) else EXIT_VERIFY_FAIL)


def _read_dotted(obj: Any, dotted: str) -> Any:
    return get_dotted(obj, dotted)


def _corners_markdown(doc: dict) -> str:
    L = [f"# Process corners - {Path(doc['design']).parent.name}", "",
         f"* mode: {doc['mode']}", f"* corners: {doc['n_corners']}",
         f"* passing: {doc['n_pass']} of {doc['n_corners']}", ""]
    L += ["Excursions applied:", ""]
    L += [f"* `{k}` +-{v}" for k, v in doc["parameters"].items()]
    L += ["", "## Spread of each target metric", "",
          "| metric | nominal | minimum | maximum | spread |", "|---|---:|---:|---:|---:|"]
    for m, s in doc["summary"].items():
        pct = f" ({s['spread_pct_of_nominal']:.1f} %)" if s["spread_pct_of_nominal"] else ""
        L.append(f"| `{m}` | {s['nominal']:.6g} | {s['min']:.6g} | {s['max']:.6g} | "
                 f"{s['spread']:.6g}{pct} |")
    L += ["", "## Verdict at each corner", "",
          "| corner | verdict | unmet at `must` | unmet at `should` |",
          "|---|---|---:|---:|"]
    for r in doc["rows"]:
        L.append(f"| {r['corner']} | {r['verdict']} | {r['must_failures']} "
                 f"| {r.get('should_failures', [])} |")
    L.append("")
    return chr(10).join(L)


@app.command()
def golden(
    design: Path = typer.Argument(..., exists=True, help="path to design.yaml"),
    accept: bool = typer.Option(False, "--accept",
                                help="write the current emission as the reference"),
    set_: list[str] = typer.Option([], "--set", help="override a design field"),
):
    """Compare the emitted mask against a stored reference, layer by layer.

    Every solver in this chain is anchored to a closed-form result. The layout
    stage has no such anchor: there is no analytic expression for a floor plan,
    so the only statement available about it is that it has not changed since
    it was last examined. That statement is worth having, and it is what a
    layout regression provides.

    The reference is held in ``golden/`` beside the design file and is version
    controlled. A difference is reported as the area of the exclusive-or per
    layer, which localises the change rather than merely detecting it. Accepting
    a new reference is an explicit act, so a change is reviewed once and then
    stops being reported.
    """
    from .stages import s05_layout

    try:
        d, lib = _load(design)
    except Exception as exc:
        typer.echo(f"error: cannot load design: {exc}", err=True)
        raise typer.Exit(EXIT_USAGE)
    for ov in set_:
        key, val = ov.split("=", 1)
        _apply_override(d, key, val)
    lib = _library(d)

    ctx = RunContext(design_dir=design.parent, run_id=new_run_id("golden")).ensure()
    for s in _resolve_stages(["layout"]):
        ctx.current_stage = s
        ctx.stages_run.append(s)
        STAGES[s](d, ctx, lib)
    emitted = Path((ctx.get("layout") or {})["gds"])

    ref_dir = design.parent / "golden"
    ref = ref_dir / f"{d.meta.name}.gds"

    if accept or not ref.exists():
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref.write_bytes(emitted.read_bytes())
        (ref_dir / "README.md").write_text(
            "# Layout reference\n\n"
            "The mask this design last emitted, held so that an unintended change to "
            "the layout stage or to a geometric parameter is detected. It carries no "
            "authority of its own: it records what was emitted, not what is correct. "
            "Regenerate with `picchain golden <design.yaml> --accept` after a change "
            "has been reviewed.\n",
            encoding="utf-8",
        )
        verb = "updated" if accept else "created"
        typer.echo(f"reference {verb}: {ref}")
        raise typer.Exit(EXIT_OK)

    result = s05_layout.compare_backends(ref, emitted, d.layout.layer_map)
    dump_json(ctx.run_dir / "golden.json", {"reference": str(ref), **result})
    if result["agree"]:
        typer.echo(f"layout unchanged against {ref}")
        raise typer.Exit(EXIT_OK)

    typer.echo(f"layout DIFFERS from {ref}", err=True)
    typer.echo(f"  residual area: {result['residual_area_um2']:.6g} um2", err=True)
    for layer, area in sorted(result["residual_by_layer_um2"].items(),
                              key=lambda kv: -kv[1]):
        typer.echo(f"    {layer:12s} {area:.6g} um2", err=True)
    typer.echo("  review the change, then `--accept` to adopt it", err=True)
    raise typer.Exit(EXIT_VERIFY_FAIL)


@app.command()
def doctor(
    design: Optional[Path] = typer.Argument(
        None, help="probe using this design's own fdtd settings rather than the defaults"),
    fdtd: bool = typer.Option(True, "--fdtd/--no-fdtd",
                              help="probe the external meep environment as well"),
):
    """Report which optional backends are available.

    Without a design, the external solver is probed at the DEFAULT distribution
    and environment names. A design that names its own reports unavailable here
    while running correctly, so pass the design to probe what it will actually
    use.
    """
    from .artifacts import environment_fingerprint
    env = environment_fingerprint()
    if fdtd:
        from .fdtd import bridge
        backend = None
        if design is not None:
            d = Design.load(design)
            backend = bridge.default_backend(processes=1)
            backend.distro = d.fdtd.wsl_distro
            backend.env = d.fdtd.environment
            env["fdtd_probed_from"] = str(design)
        env["fdtd"] = bridge.probe(backend)
    typer.echo(json.dumps(env, indent=2))

    # What is absent, and what to do about it.
    #
    # This command reported an inventory and nothing else until 2026-08-11. An
    # inventory tells somebody who already has the chain working that it works.
    # It tells a newcomer nothing, and the external solvers are the hard part of
    # adopting this: KLayout is a separate application, and meep and MPB live in
    # another environment entirely. Naming the remedy beside the gap is the
    # difference between a report and a setup guide.
    REMEDY = {
        "numpy": "pip install picchain            (required)",
        "scipy": "pip install picchain            (required)",
        "klayout": "pip install picchain            (required)",
        "matplotlib": "pip install picchain            (required, for figures)",
        "gdsfactory": "pip install 'picchain[layout]'  second mask writer, "
                      "compared against the first",
        "femwell": "pip install 'picchain[fem]'     independent mode solver, "
                   "stage `fem`",
        "gmsh": "pip install 'picchain[fem]'     mesher for the above",
        "sax": "pip install 'picchain[circuit]' circuit assembly, stage "
               "`circuit`",
    }
    missing = [k for k, v in env["packages"].items() if v is None]
    core = [k for k in ("numpy", "scipy", "klayout") if k in missing]

    lines: list[str] = []
    for name in missing:
        lines.append(f"  {name:12} {REMEDY.get(name, 'not a declared dependency')}")

    exe = None
    try:
        from .stages.s06_drc import find_klayout
        exe = find_klayout()
    except Exception:
        pass
    if not exe:
        lines.append("  KLayout app  the APPLICATION, distinct from the python module: "
                     "https://www.klayout.de/build.html")
        lines.append("               without it `drc.deck` cannot execute a foundry "
                     "runset, and the declared rules are a smoke test")
    if fdtd and not (env.get("fdtd") or {}).get("available"):
        lines.append("  meep / MPB   an external environment, stages `fdtd` "
                     "structure=taper|grating|bandstructure")
        lines.append("               on Windows this is WSL: set fdtd.wsl_distro and "
                     "fdtd.environment to match your install")
        lines.append("               a band structure costs about 3 hours; see "
                     "'Running the Chain Efficiently' in PICCHAIN_REFERENCE.md")

    if lines:
        typer.echo("", err=True)
        typer.echo("NOT AVAILABLE, and what each one costs you:", err=True)
        for ln in lines:
            typer.echo(ln, err=True)
        typer.echo("", err=True)
        typer.echo("The chain runs without every optional backend. Each stage that "
                   "needs one reports its absence rather than failing.", err=True)
    else:
        typer.echo("", err=True)
        typer.echo("every backend this chain can use is available", err=True)

    if core:
        raise typer.Exit(EXIT_ERROR)


@app.command()
def search(
    design: Path = typer.Argument(..., exists=True, help="path to design.yaml"),
    stages: str = typer.Option("", "--stages", "-s", help="subset; default = search.stages or design.stages"),
    tag: str = typer.Option("search", "--tag"),
    out: Optional[Path] = typer.Option(None, "--out", help="write the record as JSON here"),
):
    """Search the declared parameters for a design meeting its targets.

    Four phases, in order, each answering a question the next one needs.

    1. **State the problem.** Which targets are unmet, and by how much relative
       to their own bounds.
    2. **Sensitivity.** Every declared parameter is probed and the elasticity
       d(ln metric)/d(ln parameter) reported for every target metric. This says
       which knob moves which target, with sign and magnitude, at one run per
       parameter.
    3. **Reachability.** Every parameter is evaluated at both of its bounds. A
       requirement lying outside what a parameter can reach is reported as
       unreachable with the bound named, rather than approached until the budget
       is spent. A metric that is not monotone across its bracket is reported as
       unsearchable rather than bisected.
    4. **Solve and verify.** Where a bracket contains a satisfying point it is
       found by bisection on the dominant control. Every target is then evaluated
       at the candidate, so what worsened is reported beside what improved.

    Not a global optimiser. It states what the declared parameters reach and what
    they do not.
    """
    from . import search as S

    d0, lib = _load(design)
    cfg = d0.search
    if not cfg.parameters:
        typer.echo("no search.parameters declared; nothing to search", err=True)
        raise typer.Exit(3)

    requested = [x.strip() for x in stages.split(",") if x.strip()] or cfg.stages or d0.stages
    chosen = _resolve_stages(requested)
    reqs = [S.requirement_from_target(t) for t in d0.targets if t.severity in cfg.severities]
    budget = {"n": 0}

    def evaluate(overrides: dict) -> Optional[dict]:
        """One evaluation. None where a constraint is violated or a stage raised."""
        if budget["n"] >= cfg.max_evaluations:
            return None
        d, _ = _load(design)
        for k, v in overrides.items():
            set_dotted(d, k, v)
        bad = S.check_constraints(d, cfg.constraints)
        if bad:
            typer.echo(f"  skipped, constraint violated: {bad[0]}", err=True)
            return None
        budget["n"] += 1
        ctx = RunContext(design_dir=design.parent,
                         run_id=new_run_id(f"{tag}{budget['n']:03d}")).ensure()
        try:
            for st in chosen:
                ctx.current_stage = st
                ctx.stages_run.append(st)
                STAGES[st](d, ctx, _library(d))
            ctx.finalise("ok", update_latest=False)
            return ctx.metrics
        except Exception as exc:
            ctx.finalise("failed", update_latest=False)
            typer.echo(f"  evaluation raised: {exc}", err=True)
            return None

    def metric_of(tree, path):
        if tree is None:
            return None
        try:
            return float(_read_dotted(tree, path))
        except (TypeError, ValueError, KeyError, AttributeError):
            return None

    record = {"design": str(design), "stages": chosen}

    typer.echo("[1/4] the problem", err=True)
    base = evaluate({})
    if base is None:
        typer.echo("the nominal design does not evaluate; fix that first", err=True)
        raise typer.Exit(1)
    nominal = {r.metric: metric_of(base, r.metric) for r in reqs}

    # A target whose metric the chosen stages do not produce cannot be searched
    # for, and must not be counted as unmet: doing so would set the search to
    # chase a quantity it never computes, and would report failure at the end
    # for a reason that has nothing to do with the design. Such targets are
    # named and set aside.
    absent = [r for r in reqs if nominal[r.metric] is None]
    if absent:
        for r in absent:
            typer.echo(f"  excluded  {r.metric:42} not produced by stages {','.join(chosen)}", err=True)
        reqs = [r for r in reqs if nominal[r.metric] is not None]
    record["excluded"] = [{"metric": r.metric, "reason": "not produced by the chosen stages"}
                          for r in absent]

    unmet = [r for r in reqs if not r.satisfied_by(nominal[r.metric])]
    record["nominal"] = nominal
    record["unmet"] = [{"metric": r.metric, "severity": r.severity,
                        "requires": r.describe(), "actual": nominal[r.metric],
                        "shortfall": r.shortfall(nominal[r.metric])} for r in unmet]
    for r in unmet:
        typer.echo(f"  {r.severity:6} {r.metric:42} {nominal[r.metric]!s:>12}  requires {r.describe()}", err=True)
    if not unmet:
        typer.echo("  every target already met", err=True)
        if out:
            dump_json(out, record)
        raise typer.Exit(0)

    want = [r.metric for r in reqs]

    typer.echo("[2/4] sensitivity", err=True)
    sens = []
    for prm in cfg.parameters:
        v0 = float(get_dotted(d0, prm.path))
        v1 = min(max(v0 * (1.0 + prm.probe), prm.min), prm.max)
        tree = evaluate({prm.path: v1})
        sv = S.Sensitivity(parameter=prm.path, nominal=v0, probed=v1)
        for mname in want:
            a, b = nominal.get(mname), metric_of(tree, mname)
            sv.elasticity[mname] = (S.elasticity(v0, v1, a, b)
                                    if a is not None and b is not None else float("nan"))
        sens.append(sv)
        dom = sv.dominant([r.metric for r in unmet])
        msg = f"{dom[0]} at elasticity {dom[1]:+.2f}" if dom else "nothing it moves"
        typer.echo(f"  {prm.path:32} dominant: {msg}", err=True)
    record["sensitivity"] = [{"parameter": x.parameter, "nominal": x.nominal,
                              "probed": x.probed, "elasticity": x.elasticity} for x in sens]

    typer.echo("[3/4] reachability", err=True)
    reach = {}
    for prm in cfg.parameters:
        t_lo = evaluate({prm.path: prm.min})
        t_hi = evaluate({prm.path: prm.max})
        t_mid = evaluate({prm.path: 0.5 * (prm.min + prm.max)})
        reach[prm.path] = {}
        for r in unmet:
            lo_v, mid_v, hi_v = (metric_of(t_lo, r.metric), metric_of(t_mid, r.metric),
                                 metric_of(t_hi, r.metric))
            samples = [x for x in (lo_v, mid_v, hi_v) if x is not None]
            rc = S.Reach(parameter=prm.path, metric=r.metric, at_min=lo_v, at_max=hi_v,
                         monotone=S.bracket_is_monotone(samples))
            reach[prm.path][r.metric] = rc
            iv = rc.interval
            state = "reaches it" if rc.can_reach(r) else "CANNOT reach it"
            note = "" if rc.monotone else "  [not monotone: unsearchable by bisection]"
            span = f"{iv[0]:.4g} .. {iv[1]:.4g}  {state}{note}" if iv else "no value"
            typer.echo(f"  {prm.path:28} -> {r.metric:34} {span}", err=True)
    record["reachability"] = {
        pth: {mn: {"at_min": rc.at_min, "at_max": rc.at_max, "monotone": rc.monotone,
                   "can_reach": rc.can_reach(next(r for r in unmet if r.metric == mn))}
              for mn, rc in dd.items()}
        for pth, dd in reach.items()}

    typer.echo("[4/4] solve", err=True)

    # Which parameters are worth moving, and for which requirements. A parameter
    # is a candidate for a requirement only where its bracket both reaches the
    # requirement and is monotone; a metric that doubles back cannot be searched
    # and the fact is a finding about the metric.
    assigned: dict[str, list] = {}
    notes = []
    for r in unmet:
        cands = [p for p in cfg.parameters
                 if reach[p.path][r.metric].can_reach(r) and reach[p.path][r.metric].monotone]
        if not cands:
            spans = "; ".join(
                f"{p.path} spans {reach[p.path][r.metric].interval[0]:.4g} to "
                f"{reach[p.path][r.metric].interval[1]:.4g}"
                for p in cfg.parameters if reach[p.path][r.metric].interval)
            msg = (f"{r.metric} requires {r.describe()} and no declared parameter reaches it "
                   f"within its bounds, monotonically. {spans}")
            notes.append(msg)
            typer.echo(f"  UNREACHABLE  {msg}", err=True)
            continue

        def _el(path, metric):
            for x in sens:
                if x.parameter == path:
                    e = x.elasticity.get(metric)
                    return abs(e) if e is not None and e == e else 0.0
            return 0.0

        prm = max(cands, key=lambda p: _el(p.path, r.metric))
        assigned.setdefault(prm.path, []).append(r)

    # One control may carry several requirements, and their satisfying sets need
    # not overlap. Solving them one after another lets each overwrite the last:
    # bisecting the post gap for the reflectivity and then again for the
    # bandwidth produced a mirror of 6 per cent reflectivity, a guide carrying
    # two modes and a linewidth five times its bound, all three having been
    # acceptable before the solve began.
    #
    # Each control is therefore scanned across its range and every point is
    # scored against EVERY requirement, not against the ones assigned to it. The
    # scan finds the intersection where one exists and reports its absence where
    # it does not.
    applied = {}
    grid_n = max(5, min(11, cfg.max_evaluations // max(1, 2 * len(assigned)))) if assigned else 0
    for path, rs in assigned.items():
        prm = next(p for p in cfg.parameters if p.path == path)
        names = ", ".join(r.metric.split(".")[-1] for r in rs)
        typer.echo(f"  scanning {path} at {grid_n} points, carrying {len(rs)} requirement(s): {names}", err=True)
        best_val, best_score = None, None
        for x in S.scan_grid(prm.min, prm.max, grid_n):
            tree = evaluate(dict(applied, **{path: x}))
            if tree is None:
                continue
            vals = {r.metric: metric_of(tree, r.metric) for r in reqs}
            sc = S.score_point(vals, reqs)
            if best_score is None or S.better(sc, best_score):
                best_val, best_score = x, sc
        if best_val is None:
            notes.append(f"{path}: no point in its range evaluated successfully")
            typer.echo(f"  {path}: nothing evaluable in range", err=True)
            continue

        # A coarse scan places the answer between samples. Where the best point
        # still misses a requirement, the window either side of it is re-scanned
        # at the same count, which is one further refinement of the step and no
        # more. On the validation baseline the coarse step of 130 um left the
        # tuning range 25 MHz short of an 8 GHz requirement, which is the grid
        # rather than the design.
        if best_score[0] < len(reqs):
            step = (prm.max - prm.min) / max(1, grid_n - 1)
            lo = max(prm.min, best_val - step)
            hi = min(prm.max, best_val + step)
            if hi > lo:
                typer.echo(f"  refining {path} in {lo:.6g} .. {hi:.6g}", err=True)
                for x in S.scan_grid(lo, hi, grid_n):
                    tree = evaluate(dict(applied, **{path: x}))
                    if tree is None:
                        continue
                    vals = {r.metric: metric_of(tree, r.metric) for r in reqs}
                    sc = S.score_point(vals, reqs)
                    if S.better(sc, best_score):
                        best_val, best_score = x, sc

        applied[path] = best_val
        typer.echo(f"  {path} = {best_val:.6g} meets {best_score[0]} of {len(reqs)} requirements", err=True)

    record["candidate"] = applied
    record["notes"] = notes
    if applied:
        final = evaluate(applied)
        rows = []
        for r in reqs:
            a, b = nominal.get(r.metric), metric_of(final, r.metric)
            sa, sb = r.shortfall(a), r.shortfall(b)
            moved = "improved" if sb < sa else ("worsened" if sb > sa else "unchanged")
            rows.append({"metric": r.metric, "severity": r.severity, "requires": r.describe(),
                         "nominal": a, "candidate": b, "met": r.satisfied_by(b), "moved": moved})
        record["result"] = rows
        typer.echo("", err=True)
        typer.echo("candidate:", err=True)
        for k, v in applied.items():
            typer.echo(f"  {k} = {v:.6g}", err=True)
        typer.echo("", err=True)
        for row in rows:
            flag = "pass" if row["met"] else "FAIL"
            typer.echo(f"  {flag:4} {row['metric']:42} {row['nominal']!s:>11} -> "
                       f"{row['candidate']!s:>11}  ({row['moved']})", err=True)
        record["all_met"] = all(x["met"] for x in rows)
    typer.echo(f"{budget['n']} evaluations used of {cfg.max_evaluations}", err=True)

    if out:
        dump_json(out, record)
        typer.echo(f"written {out}", err=True)
    raise typer.Exit(0 if record.get("all_met") else 2)


@app.command()
def sensitivity(
    design: Path = typer.Argument(..., exists=True, help="path to design.yaml"),
    params: str = typer.Option("", "--params", help="comma-separated dotted fields; default = search.parameters plus corners.parameters"),
    metrics: str = typer.Option("", "--metric", help="comma-separated dotted metric paths; default = the target metrics"),
    probe: float = typer.Option(0.05, "--probe", help="fractional perturbation, applied either side"),
    stages: str = typer.Option("", "--stages", "-s"),
    tag: str = typer.Option("sens", "--tag"),
    out: Optional[Path] = typer.Option(None, "--out"),
):
    """How strongly each parameter moves each metric, as a dimensionless number.

    Two tables are produced and they answer different questions.

    **Elasticity**, being d(ln metric) over d(ln parameter), is a property of the
    physics and does not depend on how well the parameter happens to be
    controlled. It ranks the knobs: a parameter of elasticity 17 moves a metric by
    seventeen times its own fractional change.

    **Contribution**, the half-span a parameter produces over its declared
    excursion, is a property of the process. It ranks the risks: a parameter of
    large elasticity held to a tight tolerance may contribute less than a weak one
    held loosely. `corners.parameters` supplies those excursions.

    A design decision follows from the first table and a process specification
    from the second. Two runs per parameter, symmetric about the nominal, so the
    derivative is centred rather than one-sided.
    """
    from . import search as S

    d0, lib = _load(design)
    chosen = _resolve_stages([s.strip() for s in stages.split(",") if s.strip()]
                             or d0.search.stages or d0.stages)

    names = [p.strip() for p in params.split(",") if p.strip()]
    if not names:
        names = [p.path for p in d0.search.parameters]
        names += [k for k in d0.corners.parameters if k not in names]
    if not names:
        typer.echo("no parameters given and none declared; use --params", err=True)
        raise typer.Exit(3)

    want = [m.strip() for m in metrics.split(",") if m.strip()] or [t.metric for t in d0.targets]
    n = {"i": 0}

    def evaluate(over):
        d, _ = _load(design)
        for k, v in over.items():
            set_dotted(d, k, v)
        n["i"] += 1
        ctx = RunContext(design_dir=design.parent, run_id=new_run_id(f"{tag}{n['i']:03d}")).ensure()
        try:
            for st in chosen:
                ctx.current_stage = st
                ctx.stages_run.append(st)
                STAGES[st](d, ctx, _library(d))
            ctx.finalise("ok", update_latest=False)
            return ctx.metrics
        except Exception as exc:
            ctx.finalise("failed", update_latest=False)
            typer.echo(f"  evaluation raised: {exc}", err=True)
            return None

    def mval(tree, path):
        if tree is None:
            return None
        try:
            return float(_read_dotted(tree, path))
        except (TypeError, ValueError, KeyError, AttributeError):
            return None

    typer.echo(f"nominal, then {len(names)} parameters at +-{probe:.0%}", err=True)
    base = evaluate({})
    if base is None:
        typer.echo("the nominal design does not evaluate", err=True)
        raise typer.Exit(1)
    nominal = {m: mval(base, m) for m in want}
    present = [m for m in want if nominal[m] is not None]
    absent = [m for m in want if nominal[m] is None]
    for m in absent:
        typer.echo(f"  excluded {m}: not produced by stages {','.join(chosen)}", err=True)

    rows = {}
    for path in names:
        try:
            v0 = float(get_dotted(d0, path))
        except Exception:
            typer.echo(f"  skipped {path}: not a numeric design field", err=True)
            continue
        lo_t = evaluate({path: v0 * (1 - probe)})
        hi_t = evaluate({path: v0 * (1 + probe)})
        e = {}
        for m in present:
            a, b = mval(lo_t, m), mval(hi_t, m)
            e[m] = (S.elasticity(v0 * (1 - probe), v0 * (1 + probe), a, b)
                    if a is not None and b is not None else float("nan"))
        rows[path] = {"nominal": v0, "elasticity": e}
        typer.echo(f"  {path} = {v0:g}", err=True)

    def _table(title, cell):
        w = max((len(m) for m in present), default=10) + 2
        head = f"{'metric':<{w}}" + "".join(f"{p.split('.')[-1][:13]:>15}" for p in rows)
        lines = [title, "", head, "-" * len(head)]
        for m in present:
            lines.append(f"{m:<{w}}" + "".join(cell(p, m) for p in rows))
        return lines

    def _el_cell(p, m):
        v = rows[p]["elasticity"].get(m)
        return f"{'-':>15}" if v is None or v != v else f"{v:>+15.2f}"

    excursions = dict(d0.corners.parameters)

    def _cn_cell(p, m):
        v = rows[p]["elasticity"].get(m)
        dd = excursions.get(p)
        if v is None or v != v or dd is None or not rows[p]["nominal"]:
            return f"{'-':>15}"
        return f"{abs(v) * abs(dd) / abs(rows[p]['nominal']) * 100:>14.1f}%"

    typer.echo("", err=True)
    for line in _table("Elasticity: d(ln metric) over d(ln parameter)", _el_cell):
        typer.echo(line, err=True)
    if any(p in excursions for p in rows):
        typer.echo("", err=True)
        for line in _table("Contribution over the declared corner excursion, as a half-span",
                           _cn_cell):
            typer.echo(line, err=True)
        typer.echo("", err=True)
        typer.echo("A blank contribution means the parameter carries no excursion in "
                   "corners.parameters, so the process does not constrain it here.", err=True)

    record = {"design": str(design), "probe": probe, "stages": chosen,
              "nominal": nominal, "excursions": excursions,
              "parameters": rows, "excluded": absent}

    # A matrix of this size is read faster as a picture than as two tables, and
    # the two panels invite the comparison the tables cannot force: a cell dark
    # in both is not thereby a risk.
    fig_dir = design.parent / "runs" / "sensitivity"
    fig_dir.mkdir(parents=True, exist_ok=True)
    try:
        from .report import sensitivity_heatmap
        drawn = sensitivity_heatmap(record, fig_dir / "sensitivity.png")
        if drawn:
            record["figure"] = str(drawn)
            typer.echo(f"drawn {drawn}", err=True)
    except Exception as exc:               # a drawing must never fail an analysis
        typer.echo(f"heatmap not drawn: {exc}", err=True)

    if out:
        dump_json(out, record)
        typer.echo(f"written {out}", err=True)
    typer.echo(f"{n['i']} evaluations", err=True)


def main() -> None:
    try:
        app()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
