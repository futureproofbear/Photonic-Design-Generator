#!/usr/bin/env python
"""Check the quantities a document states against the runs that produced them.

A document accumulates numbers across revisions and the stale ones look exactly
like the current ones. Reading does not find them; comparing does.

This scans a document for lines stating a known quantity, extracts the numbers on
those lines, and reports any line where no number matches the run of record. A
document covering more than one design is given more than one design, and a
value matching any of them passes, because a comparison table legitimately holds
both.

**Corner extremes count as matches.** A deck quoting the worst corner of a sweep
is quoting a real figure, and comparing only against the nominal reported it as
wrong. Where `runs/corners.json` exists its minimum and maximum are admitted for
every metric it carries.

    $PY tools/check_doc_numbers.py <doc.md> --design <dir>=<TAG> [--design ...]

Exit codes: 0 every stated quantity traces, 1 at least one does not,
2 a document or a run is missing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# A quantity is recognised by what the prose calls it. The pattern must be
# specific enough that the number on the line is that quantity: a pattern
# matching a bare word appearing in ordinary prose reports the sentence's other
# numbers as wrong, which is noise and trains the reader to ignore the tool.
CHECKS: list[tuple[str, str]] = [
    # The phase-section gap is a different quantity from the mirror gap and is
    # matched first, so that a line naming it is not judged against the mirror.
    (r"phase[- ]section gap|phase electrode gap", "cavity.phase_section.gap_um"),
    (r"(?<!phase )electrode gap|electrodes?\s+\S+\s+apart|gold strips.*apart",
     "eo.electrode_gap_um"),
    (r"side-mode suppression|\bSMSR\b", "cavity.smsr_dB"),
    (r"free spectral range", "cavity.fsr_GHz"),
    (r"penetration depth", "grating.penetration_depth_mm"),
    (r"peak reflectivity", "grating.peak_reflectivity"),
    (r"device length", "layout.device_length_um"),
    (r"threshold current", "dynamics.threshold_current_mA"),
    (r"threshold gain", "cavity.modal_threshold_gain_per_cm"),
    (r"containment,? worst|worst.*containment", "cavity.stopband_containment_ratio"),
    (r"grating length|Bragg grating.*\bmm\b", "grating.length_um"),
    (r"feed length", "cavity.feed_length_um"),
    (r"Bragg wavelength", "grating.bragg_wavelength_nm"),
    # A document says "round-trip delay" of three different things: the cavity's
    # own, the mirror's, and the one the assembled circuit reports. All three are
    # admitted, because a line naming one and judged against another reads as a
    # document error when the tool is the thing that is wrong.
    (r"round.?trip delay", "cavity.tau_roundtrip_ps"),
    (r"round.?trip delay", "grating.mirror_round_trip_delay_ps"),
    (r"assembled round.?trip delay", "circuit.group_delay_at_peak_ps"),
]

NUM = re.compile(r"(?<![\w.])(\d{1,7}(?:[  ]\d{3})*(?:\.\d+)?)(?![\w])")

# A number carrying a comparison operator states a bound, not a measurement.
# `modal threshold gain <= 40 /cm` is the requirement; the run returns 29.5, and
# reporting that line as a mismatch is noise. A tool that reports correct work
# as wrong is one the reader learns to skip, so bounds are removed before the
# remaining numbers on the line are judged.
BOUND = re.compile(r"(?:>=|<=|\+/-|[<>≤≥±])\s*\d{1,7}(?:[  ]\d{3})*(?:\.\d+)?")


def _claims(line: str) -> list[float]:
    """Numbers on the line that assert a value, with bounds removed."""
    stripped = BOUND.sub(" ", line)
    return [float(x.replace(" ", "").replace(" ", ""))
            for x in NUM.findall(stripped)]


def _dig(tree: dict, path: str):
    node = tree
    for k in path.split("."):
        node = node.get(k) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


def _truths(design: pathlib.Path, tag: str) -> dict[str, set[float]]:
    runs = sorted(design.glob(f"runs/*-{tag}"))
    if not runs:
        raise FileNotFoundError(f"no run tagged {tag} under {design}")
    run = runs[-1]
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))["metrics"]
    resolved = json.loads((run / "design.resolved.json").read_text(encoding="utf-8"))
    out: dict[str, set[float]] = {}
    for _, path in CHECKS:
        vals = set()
        for tree in (metrics, resolved):
            v = _dig(tree, path)
            if isinstance(v, (int, float)):
                vals.add(float(v))
        # a length in micrometres is as often quoted in millimetres
        vals |= {v / 1000.0 for v in list(vals) if abs(v) > 100}
        if vals:
            out[path] = vals
    # corner extremes are real figures a document may quote
    cj = design / "runs" / "corners.json"
    if cj.exists():
        try:
            summ = json.loads(cj.read_text(encoding="utf-8")).get("summary", {})
            for m, st in summ.items():
                for key in ("min", "max"):
                    if isinstance(st.get(key), (int, float)):
                        out.setdefault(m, set()).add(float(st[key]))
        except Exception:
            pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc", type=pathlib.Path)
    ap.add_argument("--design", action="append", required=True,
                    metavar="DIR=TAG", help="repeat for a document covering several")
    ap.add_argument("--tol", type=float, default=0.02,
                    help="fractional tolerance, default 2 %% for rounding")
    a = ap.parse_args()

    if not a.doc.exists():
        print(f"{a.doc}: no such file", file=sys.stderr)
        return 2

    truths: dict[str, set[float]] = {}
    for spec in a.design:
        d, _, tag = spec.partition("=")
        try:
            for k, v in _truths(pathlib.Path(d), tag).items():
                truths.setdefault(k, set()).update(v)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 2

    text = a.doc.read_text(encoding="utf-8")
    findings = []
    # A document may hold a section deliberately frozen at an earlier
    # configuration, such as a platform comparison held at the point where only
    # the platform differed. Its numbers are correct and describe a different
    # device, so the document declares the span rather than the tool guessing:
    #
    #     <!-- frozen: the platform comparison, held at the transition -->
    #     ... numbers that describe that configuration ...
    #     <!-- /frozen -->
    #
    # This is the mechanism T031 asks for, that a document carrying two designs
    # says which one every number describes, made checkable.
    frozen = False
    for n, line in enumerate(text.split("\n"), 1):
        low = line.strip().lower()
        if low.startswith("<!-- frozen"):
            frozen = True
            continue
        if low.startswith("<!-- /frozen"):
            frozen = False
            continue
        if frozen or line.strip().startswith("<!--"):
            continue
        for pat, path in CHECKS:
            if path not in truths or not re.search(pat, line, re.I):
                continue
            vals = _claims(line)
            if not vals:
                continue
            # every check whose pattern matches this line contributes its truths
            good = set()
            for pat2, path2 in CHECKS:
                if path2 in truths and re.search(pat2, line, re.I):
                    good |= truths[path2]
            if any(any(abs(v - t) <= max(abs(t) * a.tol, 1e-6) for t in good)
                   for v in vals):
                continue
            findings.append((n, path, line.strip()[:100], sorted(good)[:6]))
            break   # one quantity per line; the most specific pattern claimed it

    if not findings:
        print(f"{a.doc.name}: PASS  every stated quantity traces to a run")
        return 0
    print(f"{a.doc.name}: {len(findings)} line(s) state a quantity matching no run")
    for n, path, line, good in findings:
        print(f"  line {n:5d}  {path}")
        print(f"     doc: {line}")
        print(f"     run: {', '.join(f'{v:g}' for v in good)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
