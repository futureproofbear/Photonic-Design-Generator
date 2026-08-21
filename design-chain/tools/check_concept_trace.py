"""Check that a design's acceptance targets trace to its concept of operation.

A target carries a mechanism as well as a number. Where a design replaces the
mechanism, the target stops testing the requirement and starts testing the
absence of the change, and it does so silently: the run still passes, the number
is still computed, and only a reader who knows the concept can see that the
wrong question is being asked.

That failure occurred on a laser built to hold its mode comb in step with its
mirror. Its targets were inherited from a design whose concept is the opposite
one of positioning the mode hop outside the sweep, so the requirement sat on a
metric measuring a comb left to slip. The new design scored worse than the one it
replaced on the very quantity it exists to improve, and 17 of 81 process corners
appeared to fail. Measured against its own concept it is better by a factor of
two. **The verdict inverted on which concept the target encoded.**

This tool makes the link checkable. Each design carries a `DESIGN_CONCEPT.md`
holding a trace table of

    | clause | target metric | severity |

and this compares that table against the targets actually declared in
`design.yaml`. It reports:

  * targets declared and absent from the concept - the design is graded on
    something the concept does not ask for, which is where an inherited target
    hides;
  * clauses traced to a metric no target declares - the concept promises
    something the validation does not test;
  * severity disagreements between the two.

Usage:

    $PY tools/check_concept_trace.py ../projects/<scope>/designs/<name>
    $PY tools/check_concept_trace.py ../examples/*/           # several at once

Exit codes: 0 all traced, 1 a discrepancy, 2 a file is missing or unreadable.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

try:
    import yaml
except ImportError:                                     # pragma: no cover
    print("pyyaml is required", file=sys.stderr)
    raise SystemExit(2)

CONCEPT = "DESIGN_CONCEPT.md"
# metric names carry unit suffixes in mixed case: fwhm_GHz, tuning_MHz_per_V,
# linewidth_kHz, smsr_dB, VpiL_ideal_V_cm
#
# A metric path may be deeper than two segments. `RunContext.get` walks the
# metric tree to any depth, and a stage grouping a sub-system into its own
# payload produces names such as `cavity.phase_section.margin`. This pattern
# admitted exactly two segments until 2026-08-18, so a target on a nested
# quantity could not be traced: the checker reported the target as absent from
# the concept while the concept named it, and the recommended remedy would have
# been to flatten a metric name to satisfy the tool. The failure was visible
# because it named the metric it could not find, which is the tolerable form of
# this defect; a checker silently skipping the row would have passed.
ROW = re.compile(r"^\|\s*(?P<clause>[^|]+?)\s*\|\s*`(?P<metric>\w+(?:\.\w+)+)`"
                 r"\s*\|\s*(?P<severity>must|should|info)\s*\|", re.M)


def concept_rows(path: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Metric -> (clause, severity), from the trace table of the concept."""
    text = path.read_text(encoding="utf-8")
    out: dict[str, tuple[str, str]] = {}
    for m in ROW.finditer(text):
        out[m.group("metric")] = (m.group("clause"), m.group("severity"))
    return out


def declared_targets(path: pathlib.Path) -> dict[str, str]:
    """Metric -> severity, from the design file."""
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, str] = {}
    for t in d.get("targets", []) or []:
        metric = t.get("metric")
        if metric:
            out[metric] = t.get("severity", "must")
    return out


def check(design: pathlib.Path) -> int:
    cpath, ypath = design / CONCEPT, design / "design.yaml"
    if not ypath.exists():
        print(f"{design.name}: no design.yaml", file=sys.stderr)
        return 2
    if not cpath.exists():
        print(f"{design.name}: FAIL  no {CONCEPT}. Every design states what it "
              f"does and by what principle, and the targets are derived from it")
        return 1

    traced = concept_rows(cpath)
    declared = declared_targets(ypath)
    if not traced:
        print(f"{design.name}: FAIL  {CONCEPT} holds no trace table. Expected "
              f"rows of the form | clause | `stage.metric` | severity |")
        return 1

    problems = 0

    untraced = sorted(set(declared) - set(traced))
    if untraced:
        problems += len(untraced)
        print(f"{design.name}: {len(untraced)} target(s) declared and absent from "
              f"the concept. The design is graded on something the concept does "
              f"not ask for:")
        for m in untraced:
            print(f"    {m}  ({declared[m]})")

    untested = sorted(set(traced) - set(declared))
    if untested:
        problems += len(untested)
        print(f"{design.name}: {len(untested)} clause(s) trace to a metric no "
              f"target declares. The concept promises what the validation does "
              f"not test:")
        for m in untested:
            print(f"    {m}  ({traced[m][0]})")

    for m in sorted(set(traced) & set(declared)):
        want, got = traced[m][1], declared[m]
        if want != got:
            problems += 1
            print(f"{design.name}: severity disagrees for {m}: concept says "
                  f"{want}, design.yaml says {got}")

    if problems == 0:
        n_must = sum(1 for s in declared.values() if s == "must")
        print(f"{design.name}: PASS  {len(declared)} targets all trace to "
              f"{CONCEPT} ({n_must} at must)")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", nargs="+", help="design directory or directories")
    a = ap.parse_args()
    worst = 0
    for d in a.design:
        worst = max(worst, check(pathlib.Path(d).resolve()))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
