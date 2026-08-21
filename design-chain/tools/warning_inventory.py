"""Inventory every warning a run emitted, attributed to its stage.

The chain raises warnings from ninety call sites across seventeen stages, and
until 2026-08-17 **nothing read them**. Not `verify`, not `release`, no tool. A
run could emit seventeen findings, several of them material, and still be
reported as a clean pass, because the acceptance verdict grades targets and the
warnings sit in a list nobody opens.

Warnings are where the chain says *here is something you should know*, so they
are the one channel that must not be silent by default. This tool is the first
half of closing that: it produces the inventory. The second half is an
acknowledgement gate, where a design names each finding it accepts and a run
fails on any finding it has not.

Attribution without re-running
------------------------------
A stored warning is free prose with no stage recorded beside it, so this parses
the stage sources, collects the literal fragments inside every `ctx.warn(...)`
call, and matches each emitted warning against them. Runs made before the
structured record existed are therefore attributable, which matters because the
inventory is wanted for designs already released.

Where a run carries structured records, those are preferred and the matching is
skipped.

    $PY tools/warning_inventory.py <design>=<tag> [<design>=<tag> ...]
    $PY tools/warning_inventory.py <design>=<tag> --by-key
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "picchain" / "stages"
MIN_LITERAL = 18


def stage_literals() -> dict[str, list[str]]:
    """Distinctive prose fragments inside each stage's ctx.warn(...) calls."""
    out: dict[str, list[str]] = {}
    for f in sorted(SRC.glob("s*.py")):
        stage = re.sub(r"^s\d+_", "", f.stem)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        lits: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr == "warn"):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    for piece in re.split(r"\s{2,}", sub.value):
                        piece = piece.strip()
                        if len(piece) >= MIN_LITERAL:
                            lits.append(piece)
        if lits:
            out[stage] = sorted(set(lits), key=len, reverse=True)
    return out


def attribute(msg: str, lits: dict[str, list[str]]) -> str:
    best, best_len = "unattributed", 0
    for stage, fragments in lits.items():
        for fr in fragments:
            if fr in msg and len(fr) > best_len:
                best, best_len = stage, len(fr)
    return best


def key_for(stage: str, msg: str) -> str:
    """A stable-ish key from the opening words, for grouping and acknowledging."""
    words = re.findall(r"[a-z0-9]+", msg.lower())
    skip = {"the", "a", "an", "of", "is", "to", "and", "on", "in", "this", "that",
            "it", "at", "for", "its", "with", "no", "not", "so", "by", "are", "was"}
    keep = [w for w in words if w not in skip][:4]
    return f"{stage}." + "_".join(keep or ["warning"])


def acknowledged(design: pathlib.Path) -> set[str]:
    import yaml
    y = yaml.safe_load((design / "design.yaml").read_text(encoding="utf-8")) or {}
    node = (y.get("warnings") or {})
    ack = node.get("acknowledged") or []
    out = set()
    for a in ack:
        out.add(a if isinstance(a, str) else str(a.get("key", "")))
    return out


def load(design: pathlib.Path, tag: str):
    runs = sorted(glob.glob(str(design / "runs" / f"*{tag}" / "metrics.json")))
    if not runs:
        raise SystemExit(f"no run tagged {tag} under {design}")
    rd = pathlib.Path(runs[-1]).parent
    doc = json.loads((rd / "metrics.json").read_text())
    return rd, doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", nargs="+", metavar="DIR=TAG")
    ap.add_argument("--by-key", action="store_true",
                    help="group across designs by key instead of listing per design")
    a = ap.parse_args()

    lits = stage_literals()
    per_design: dict[str, list[tuple[str, str, str, bool]]] = {}

    for spec in a.design:
        d_path, _, tag = spec.partition("=")
        if not tag:
            raise SystemExit(f"expected DIR=TAG, got {spec!r}")
        design = pathlib.Path(d_path).resolve()
        rd, doc = load(design, tag)
        ack = acknowledged(design)
        rows = []
        for w in doc.get("warnings") or []:
            if isinstance(w, dict):
                stage, msg = w.get("stage", "unattributed"), w.get("message", "")
                key = w.get("key") or key_for(stage, msg)
            else:
                msg = str(w)
                stage = attribute(msg, lits)
                key = key_for(stage, msg)
            rows.append((stage, key, msg, key in ack))
        per_design[design.name] = rows
        print(f"=== {design.name}  ({rd.name}) ===")
        print(f"  {len(rows)} warning(s), {sum(1 for r in rows if r[3])} acknowledged, "
              f"{sum(1 for r in rows if not r[3])} NOT acknowledged")
        for stage, key, msg, ok in sorted(rows):
            mark = "ack " if ok else "  ! "
            print(f"  {mark}{key}")
            print(f"        {msg[:150]}{'...' if len(msg) > 150 else ''}")
        un = [r for r in rows if r[0] == "unattributed"]
        if un:
            print(f"  {len(un)} could not be attributed to a stage")
        print()

    if a.by_key and len(per_design) > 1:
        print("=== across designs, by key ===")
        allk: dict[str, set[str]] = {}
        for name, rows in per_design.items():
            for _, key, _, _ in rows:
                allk.setdefault(key, set()).add(name)
        for key in sorted(allk):
            where = sorted(allk[key])
            tag = "both" if len(where) == len(per_design) else ", ".join(where)
            print(f"  {key:<58} {tag}")

    total_un = sum(1 for rows in per_design.values() for r in rows if not r[3])
    print(f"\n{total_un} finding(s) across {len(per_design)} design(s) are not "
          f"acknowledged by any design file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
