"""Check that every stage a run executed is mentioned by the design's documents.

A stage that ran and is reported nowhere is the omission that hides itself:
nothing in a document reveals what it fails to mention, so the absence is
invisible to any amount of rereading. The reader sees a coherent account and has
no way to know that a solver ran, produced a result, and was never mentioned.

Found on 2026-08-17. Two designs had each executed `bend`, `fem` and `layout`,
consuming four minutes of solver time between them, and neither report named any
of the three. The `fem` omission was the costly one: the operating manual
requires `fem.polarisation_purity` to be read before the semi-vectorial
assumption is relied upon, and it sat at 0.9967 with the finite-element and
finite-difference solvers disagreeing by 4.8 % on the grating perturbation, in a
file nobody opened.

    $PY tools/check_stages_reported.py <design> --tag L21FINAL2
    $PY tools/check_stages_reported.py <design> --tag L21FINAL2 --docs ../docs/deck.md

Exit 0 when every executed stage is named, 1 otherwise.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import sys

#: A stage may be discussed under the name of the thing it computes rather than
#: under its own. These are the accepted alternatives, and each must be specific
#: enough that a passing match means the subject was genuinely covered.
ALIASES: dict[str, tuple[str, ...]] = {
    "eo": ("electro-optic", "electrode"),
    "fem": ("femwell", "finite element", "finite-element", "polarisation purity"),
    "drc": ("rule deck", "design rule"),
    "mask": ("connectivity", "netlist", "fill"),
    "layout": ("mask is complete", "drawn geometry", "polygon"),
    "bend": ("bend radius", "bend loss", "waveguide bend"),
    "reticle": ("die", "seal ring"),
    "circuit": ("assembled circuit", "scattering", "sax", "etalon"),
    "verify": ("acceptance", "verdict", "targets"),
    "release": ("release", "readiness"),
    "dynamics": ("threshold current", "rate equation", "slope efficiency"),
    "taper": ("taper",),
    "facet": ("facet", "coupling loss"),
    "grating": ("grating", "bragg"),
    "mode": ("mode solve", "n_eff", "guided mode"),
    "cavity": ("cavity", "pockels lever"),
    "fdtd": ("fdtd", "time-domain", "meep"),
}


def executed(design: pathlib.Path, tag: str) -> tuple[pathlib.Path, list[str]]:
    runs = sorted(glob.glob(str(design / "runs" / f"*{tag}" / "metrics.json")))
    if not runs:
        raise SystemExit(f"no run tagged {tag} under {design}")
    rd = pathlib.Path(runs[-1]).parent
    m = json.loads((rd / "metrics.json").read_text())["metrics"]
    out = []
    for name, node in m.items():
        if not isinstance(node, dict) or "elapsed_s" not in node:
            continue
        if node.get("enabled") is False:
            continue          # a stage that declined to run is not an omission
        out.append(name)
    return rd, sorted(out)


def prose(text: str) -> str:
    """The document with its code stripped.

    A metric name is not coverage of the stage that produced it. Matching the
    raw text passed `layout` on the string `layout.mask_is_complete` appearing in
    a trace table, which is a reference and not a discussion, and that false pass
    is worse than no check at all: a gate that accepts uncovered work is trusted
    and wrong. Fenced blocks and inline spans are therefore removed before any
    match is attempted.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    # a bare dotted metric outside backticks is a reference too
    text = re.sub(r"\b[a-z_0-9]+\.[a-z_0-9]+\b", " ", text)
    return text


def mentioned(stage: str, text: str) -> bool:
    if re.search(rf"\b{re.escape(stage)}\b", text):
        return True
    return any(a in text for a in ALIASES.get(stage, ()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--docs", action="append", default=[],
                    help="further documents that may cover a stage; repeatable")
    a = ap.parse_args()

    d = pathlib.Path(a.design).resolve()
    rd, stages = executed(d, a.tag)

    docs = [d / "DESIGN_REPORT.md", d / "DESIGN_CONCEPT.md"]
    docs += [pathlib.Path(x).resolve() for x in a.docs]
    text = prose("\n".join(p.read_text(encoding="utf-8").lower()
                           for p in docs if p.exists()))
    if not text:
        print(f"{d.name}: no documents found to check against", file=sys.stderr)
        return 2

    missing = [s for s in stages if not mentioned(s, text)]
    present = len(stages) - len(missing)
    if not missing:
        print(f"{d.name}: PASS  all {len(stages)} executed stages are covered "
              f"({rd.name})")
        return 0

    print(f"{d.name}: {len(missing)} of {len(stages)} executed stages are named "
          f"in no document ({rd.name}):")
    for s in missing:
        print(f"    {s}")
    print("  A stage that ran and is reported nowhere cannot be found by "
          "rereading, because nothing in a document reveals what it omits.")
    print(f"  {present} covered. Documents read: "
          f"{', '.join(p.name for p in docs if p.exists())}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
