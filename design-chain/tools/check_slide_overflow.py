#!/usr/bin/env python
"""Check that no slide in a Marp deck overflows its frame.

A slide that overflows is not a formatting complaint. **Marp clips the overflow
and renders no warning**, so the bottom of the slide is silently absent from the
PDF and from the screen. The author sees the whole slide in the editor and the
reader never learns that anything is missing. A conclusion placed at the foot of
a slide is the part most likely to be lost.

This tool estimates the rendered height of each slide from the deck's own CSS
and reports the ones that will not fit.

**The estimate is an estimate.** No renderer is invoked, so this reports a
prediction and not a measurement. It is calibrated to be pessimistic, so a slide
it passes is very likely to fit and a slide it flags is worth looking at. Where
Marp is available, render the deck and read it; this exists because a render is
frequently not available and a deck is edited anyway.

    $PY tools/check_slide_overflow.py <deck.md>
    $PY tools/check_slide_overflow.py <deck.md> --verbose

Exit codes: 0 every slide fits, 1 at least one is predicted to overflow,
2 the file is missing or unreadable.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

# Marp's 16:9 canvas, and the default theme's padding.
CANVAS_H = 720.0
PADDING = 70.0 * 2

# Cost of one line, in pixels, at the font size the deck declares for each
# element. Line height is taken as 1.5, which is the default theme's.
LINE = 1.5


def _css(text: str) -> dict[str, float]:
    """Font sizes the deck's own style block declares, in pixels."""
    out = {"section": 22.0, "table": 18.0, "code": 17.0, "h1": 44.0}
    for sel, size in re.findall(r"(section|table|code|section\.lead h1)\s*\{[^}]*?"
                                r"font-size:\s*([\d.]+)px", text):
        out["h1" if "lead" in sel else sel] = float(size)
    return out


def _blocks(slide: str):
    """Yield (kind, text) for each line, collapsing fenced code.

    An HTML comment renders nothing and is skipped. Counting one put a build
    note on the wrong side of the budget, and the remedy that suggested was to
    move the note to satisfy the tool.
    """
    fence = False
    comment = False
    for raw in slide.split("\n"):
        if comment:
            if "-->" in raw:
                comment = False
            continue
        if raw.strip().startswith("<!--"):
            comment = "-->" not in raw
            continue
        line = raw.rstrip()
        if line.strip().startswith("```"):
            fence = not fence
            yield "code", line
            continue
        if fence or line.startswith("    "):
            yield "code", line
            continue
        if line.strip().startswith("|"):
            yield "table", line
            continue
        if "![" in line:
            yield "image", line
            continue
        if line.strip().startswith("#"):
            yield "heading", line
            continue
        if not line.strip():
            yield "blank", line
            continue
        yield "text", line


def _wrapped(text: str, font_px: float, width_px: float = 1140.0) -> int:
    """How many rendered lines a source line occupies once wrapped.

    A proportional face averages near 0.5 em per character on running prose.
    """
    chars = len(re.sub(r"[*`_\[\]]|\(\.\..*?\)", "", text))
    per_line = max(1.0, width_px / (font_px * 0.5))
    return max(1, int(chars / per_line) + (1 if chars % per_line else 0))


def _aspect(rel: str, base: pathlib.Path, default: float = 0.42) -> float:
    """Height over width of a PNG, read from its header.

    The IHDR chunk carries the dimensions in bytes 16 to 24, so no image
    library is needed and a missing file simply falls back.
    """
    try:
        p = (base / rel).resolve()
        with open(p, "rb") as fh:
            head = fh.read(24)
        if head[1:4] != b"PNG":
            return default
        w = int.from_bytes(head[16:20], "big")
        h = int.from_bytes(head[20:24], "big")
        return (h / w) if w else default
    except Exception:
        return default


def height(slide: str, css: dict[str, float],
           base: pathlib.Path = pathlib.Path(".")) -> tuple[float, dict[str, float]]:
    """Estimated rendered height of one slide, in pixels."""
    parts = {"heading": 0.0, "text": 0.0, "table": 0.0,
             "code": 0.0, "image": 0.0, "blank": 0.0}
    lead = "_class: lead" in slide
    # A two-column slide stacks roughly half its body in each column, so summing
    # the whole body over-counted it and flagged slides that fit comfortably.
    # The deck declares the grid in its own style block.
    cols = 2.0 if 'class="cols"' in slide else 1.0
    for kind, line in _blocks(slide):
        if kind == "heading":
            n = line.count("#", 0, 4)
            size = css["h1"] if (n == 1 and lead) else css["section"] * (1.6 if n == 1 else 1.3)
            parts["heading"] += size * LINE + 12.0          # heading margin
        elif kind == "text":
            parts["text"] += _wrapped(line, css["section"], 1140.0 / cols) * css["section"] * LINE / cols
        elif kind == "table":
            parts["table"] += (css["table"] * LINE + 6.0) / cols   # row plus its border
        elif kind == "code":
            parts["code"] += css["code"] * LINE / cols
        elif kind == "image":
            m = re.search(r"w:(\d+)", line)
            w = float(m.group(1)) if m else 800.0
            # The aspect ratio is read from the file rather than assumed. It is
            # the dominant term on an image slide, and assuming it put several
            # slides on the wrong side of the budget.
            src = re.search(r"\]\(([^)]+)\)", line)
            parts["image"] += w * _aspect(src.group(1) if src else "", base)
        else:
            parts["blank"] += 8.0                           # collapsed paragraph spacing
    return sum(parts.values()), parts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=pathlib.Path, nargs="+")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--budget", type=float, default=CANVAS_H - PADDING,
                    help="usable height in px (default: the 16:9 canvas less padding)")
    a = ap.parse_args()

    worst = 0
    for deck in a.deck:
        if not deck.exists():
            print(f"{deck}: no such file", file=sys.stderr)
            return 2
        text = deck.read_text(encoding="utf-8")
        # A prose document separated by horizontal rules is not a deck, and
        # measuring one against a slide frame reports a wall of false findings.
        # A check pointed at the wrong kind of input is to refuse rather than
        # answer.
        if not re.search(r"^marp:\s*true\s*$", text[:1000], re.M):
            print(f"{deck.name}: not a Marp deck, its front matter does not declare "
                  f"`marp: true`; nothing to check", file=sys.stderr)
            continue
        css = _css(text)
        body = text.split("---", 2)[2] if text.startswith("---") else text
        slides = re.split(r"\n---\s*\n", body)

        over = []
        for i, sl in enumerate(slides, 1):
            h, parts = height(sl, css, deck.parent)
            head = next((l.strip().lstrip("# ") for l in sl.split("\n")
                         if l.strip().startswith("#")), "(no heading)")
            if h > a.budget:
                over.append((i, h, head, parts))
            elif a.verbose:
                print(f"  ok   slide {i:3d}  {h:6.0f} px  {head[:60]}")

        if over:
            print(f"{deck.name}: {len(over)} of {len(slides)} slides are predicted to "
                  f"overflow a {a.budget:.0f} px frame")
            for i, h, head, parts in over:
                worst_part = max(parts, key=parts.get)
                print(f"  slide {i:3d}  {h:6.0f} px  ({h - a.budget:+.0f})  "
                      f"most of it {worst_part}  {head[:52]}")
            worst = 1
        else:
            print(f"{deck.name}: PASS  all {len(slides)} slides fit a "
                  f"{a.budget:.0f} px frame, by estimate")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
