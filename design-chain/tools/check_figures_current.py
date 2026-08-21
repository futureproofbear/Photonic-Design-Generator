"""Check that a design's published figures are the ones its run of record made.

Each run writes its figures under `runs/<id>/figures/`. The copies a report and a
slide deck point at live in `<design>/figures/`, and that copy is made by hand.
It therefore rots silently: the design moves on, the run is repeated, and the
document keeps displaying a picture of a device that no longer exists.

Found on 2026-08-17. Two designs had been re-run to a new operating point and
their published figures were three days old, so a review deck showed the
electro-optic field across an electrode gap that had since been narrowed, and a
tuning curve annotated with a drive voltage that had been retired twice. Every
number in the same documents had been corrected; the pictures had not, and a
picture carries no units to check.

    $PY tools/check_figures_current.py <design> --tag L21SYNC
    $PY tools/check_figures_current.py <design> --tag L21SYNC --sync

Without `--sync` it reports and exits 1 on any discrepancy. With `--sync` it
copies the run's figures over the published ones and exits 0.

Figures that no stage produces, such as a cross-design comparison drawn by a
separate tool, are listed as unmanaged rather than as errors. They are the ones
to watch, since nothing regenerates them.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import pathlib
import shutil
import sys


def digest(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(design: pathlib.Path, tag: str, sync: bool) -> int:
    runs = sorted(glob.glob(str(design / "runs" / f"*{tag}" / "metrics.json")))
    if not runs:
        print(f"{design.name}: no run tagged {tag}", file=sys.stderr)
        return 2
    run_figs = pathlib.Path(runs[-1]).parent / "figures"
    pub = design / "figures"
    if not run_figs.is_dir():
        print(f"{design.name}: the run made no figures at {run_figs}")
        return 1
    pub.mkdir(exist_ok=True)

    produced = {p.name: p for p in sorted(run_figs.glob("*.png"))}
    published = {p.name: p for p in sorted(pub.glob("*.png"))}

    missing = [n for n in produced if n not in published]
    stale = [n for n in produced
             if n in published and digest(produced[n]) != digest(published[n])]
    unmanaged = [n for n in published if n not in produced]

    if sync:
        for n in missing + stale:
            shutil.copy2(produced[n], pub / n)
        if missing or stale:
            print(f"{design.name}: copied {len(missing) + len(stale)} figure(s) "
                  f"from {run_figs.parent.name}")
        else:
            print(f"{design.name}: already current")
        if unmanaged:
            print(f"  unmanaged, produced by no stage: {', '.join(sorted(unmanaged))}")
        return 0

    problems = len(missing) + len(stale)
    if problems == 0:
        print(f"{design.name}: PASS  {len(produced)} figures match "
              f"{run_figs.parent.name}")
    else:
        if missing:
            print(f"{design.name}: {len(missing)} figure(s) the run made and the "
                  f"design does not publish: {', '.join(sorted(missing))}")
        if stale:
            print(f"{design.name}: {len(stale)} published figure(s) differ from "
                  f"the run of record, so a document showing them shows an "
                  f"earlier device: {', '.join(sorted(stale))}")
        print(f"  run --sync to bring them across")
    if unmanaged:
        print(f"  unmanaged, produced by no stage and refreshed by nothing: "
              f"{', '.join(sorted(unmanaged))}")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", nargs="+")
    ap.add_argument("--tag", required=True, help="run tag of the run of record")
    ap.add_argument("--sync", action="store_true",
                    help="copy the run's figures over the published ones")
    a = ap.parse_args()
    worst = 0
    for d in a.design:
        worst = max(worst, check(pathlib.Path(d).resolve(), a.tag, a.sync))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
