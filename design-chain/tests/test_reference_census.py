"""The reference manual's account of the suite is checked against the suite.

Three statements in `PICCHAIN_REFERENCE.md` count the tests: a total near the
head, a total and a module count at the head of the test annex, and a table of
one row per module. All three are copies, and they have drifted twice.

The first drift was found by a reader: the manual claimed 418 tests over 24
modules against 664 over 32, and one module's count was wrong by one. The table
was rebuilt by hand and **drifted again inside a day**, because work elsewhere
added five modules and a hand-written table cannot notice that.

This test does not compare the numbers. It compares the set of module names,
which is the drift that matters and the one a reader cannot detect: a module
absent from the table is a body of tests the manual says nothing about, and a row
naming a module that no longer exists sends a reader to a file that is not there.
The counts are maintained by `tools/census_tests.py`, which reads them from a
collection run.

A module added here therefore fails this test until it is given a row and a
description, which is the intended cost.
"""

from __future__ import annotations

import pathlib
import re

TESTS = pathlib.Path(__file__).resolve().parent
MANUAL = TESTS.parent / "PICCHAIN_REFERENCE.md"
ROW = re.compile(r"^\| \[`(test_[\w.]+\.py)`\]\([^)]*\) \| (\d+) \| (.*) \|$", re.M)


def manual_rows() -> dict[str, tuple[int, str]]:
    text = MANUAL.read_text(encoding="utf-8")
    return {m.group(1): (int(m.group(2)), m.group(3)) for m in ROW.finditer(text)}


def modules_on_disk() -> set[str]:
    return {p.name for p in TESTS.glob("test_*.py")}


def test_every_test_module_has_a_row_in_the_manual():
    missing = sorted(modules_on_disk() - set(manual_rows()))
    assert not missing, (
        f"these test modules are described nowhere in the reference manual: {missing}. "
        "Run `python tools/census_tests.py` and write a description for each")


def test_no_row_names_a_module_that_does_not_exist():
    extra = sorted(set(manual_rows()) - modules_on_disk())
    assert not extra, (
        f"the reference manual lists test modules that are not on disk: {extra}. "
        "Run `python tools/census_tests.py`")


def test_every_row_carries_a_description():
    blank = sorted(n for n, (_, d) in manual_rows().items()
                   if not d.strip() or "no description written" in d)
    assert not blank, f"these rows carry no description: {blank}"


def test_the_stated_module_count_matches_the_table():
    """The prose and the table are two copies, and this is the cheap half."""
    text = MANUAL.read_text(encoding="utf-8")
    m = re.search(r"(\d+) tests are distributed over (\d+) modules", text)
    assert m, "the test annex no longer states a total and a module count"
    assert int(m.group(2)) == len(manual_rows()), (
        f"the annex states {m.group(2)} modules and the table has {len(manual_rows())} rows")
    assert int(m.group(1)) == sum(n for n, _ in manual_rows().values()), (
        f"the annex states {m.group(1)} tests and the table sums to "
        f"{sum(n for n, _ in manual_rows().values())}")
