"""Rewrite the test census of the reference manual from a collection run.

Three statements in `PICCHAIN_REFERENCE.md` count the suite: a total near the
head, a total and a module count at the head of the test annex, and a table of
one row per module. They have drifted twice. The first time the manual claimed
418 tests over 24 modules against 664 over 32. The table was then rebuilt by hand
and drifted again within a session, because other work added five modules and the
hand-written table had no way to notice.

A count copied into prose is a copy, and the rule this framework states for every
other copy applies to it: take the count from the thing it describes.

    python tools/census_tests.py            # rewrite the manual in place
    python tools/census_tests.py --check    # report drift, change nothing

`--check` exits 1 where the manual disagrees with collection, which is what the
accompanying test asserts.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
MANUAL = ROOT / "PICCHAIN_REFERENCE.md"

ROW = re.compile(r"^\| \[`(test_[\w.]+\.py)`\]\([^)]*\) \| (\d+) \| (.*) \|$", re.M)

#: a module added since the table was last written needs a description, and
#: inventing one from the file name produces a row that says nothing. The
#: fallback states plainly that nobody has written one.
UNDESCRIBED = "**no description written**; add one in tools/census_tests.py"


def collect() -> dict[str, int]:
    """Tests per module, from pytest's own collection rather than from a parse."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only",
         "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True).stdout
    counts = {}
    for m in re.finditer(r"^(tests[/\\][\w.]+\.py): (\d+)$", out, re.M):
        counts[pathlib.PurePath(m.group(1).replace("\\", "/")).name] = int(m.group(2))
    if not counts:
        raise SystemExit("collection returned no modules; is pytest installed?")
    return counts


def existing_rows(text: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in ROW.finditer(text)}


def rewrite(text: str, counts: dict[str, int]) -> str:
    descriptions = existing_rows(text)
    rows = [
        f"| [`{name}`](tests/{name}) | {n} | {descriptions.get(name, UNDESCRIBED)} |"
        for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    lines = text.split("\n")
    first = next(i for i, l in enumerate(lines) if l.startswith("| [`test_"))
    last = max(i for i, l in enumerate(lines) if l.startswith("| [`test_"))
    lines[first:last + 1] = rows
    text = "\n".join(lines)

    total, modules = sum(counts.values()), len(counts)
    # The counts were spelled out in words before this tool existed and are
    # written as numerals by it, so both forms are matched. A pattern that
    # matched only the form it had just written would rewrite the manual once
    # and silently stop, which is how this tool first failed.
    count_word = r"(?:\d+|[A-Za-z][\w\- ]*?)"
    text = re.sub(rf"^{count_word} tests are provided\.",
                  f"{total} tests are provided.", text, flags=re.M)
    text = re.sub(rf"^{count_word} tests are distributed over {count_word} modules\.",
                  f"{total} tests are distributed over {modules} modules.",
                  text, flags=re.M)
    text = re.sub(r"# \d+ tests", f"# {total} tests", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report drift and change nothing")
    args = ap.parse_args()

    counts = collect()
    text = MANUAL.read_text(encoding="utf-8")
    new = rewrite(text, counts)

    if args.check:
        if new == text:
            print(f"census current: {sum(counts.values())} tests over {len(counts)} modules")
            return 0
        listed = set(existing_rows(text))
        print(f"census STALE: collection gives {sum(counts.values())} tests over "
              f"{len(counts)} modules")
        for name in sorted(set(counts) - listed):
            print(f"  module in the suite and absent from the manual: {name}")
        for name in sorted(listed - set(counts)):
            print(f"  module in the manual and absent from the suite: {name}")
        return 1

    MANUAL.write_text(new, encoding="utf-8")
    print(f"census rewritten: {sum(counts.values())} tests over {len(counts)} modules")
    undescribed = [n for n in counts if n not in existing_rows(text)]
    for name in sorted(undescribed):
        print(f"  new module, description needed: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
