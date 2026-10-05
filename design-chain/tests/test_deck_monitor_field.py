"""A foundry deck's markers inside the declared monitor field are set aside.

A critical-dimension vernier draws rungs below the minimum width on purpose,
and a runset that reads them as violations is right about the rungs and says
nothing about the device. The in-process check had set its own markers in the
monitor field aside since 2026-08-31; the deck's count was judged whole, and a
die whose only deck violations were the vernier's twenty rungs was blocked at
release (2026-10-06).
"""

from __future__ import annotations

from pathlib import Path

from picchain.stages import s06_drc, s15_release

LYRDB = """<?xml version="1.0" encoding="utf-8"?>
<report-database>
 <categories>
  <category><name>RIB min. feature size violation (0.25um)</name></category>
 </categories>
 <items>
  <item><category>'RIB min. feature size violation (0.25um)'</category><cell>DIE</cell>
   <values><value>edge-pair: (-4835,-1259.185;-4835,-1199.185)|(-4834.77,-1199.185;-4834.77,-1259.185)</value></values></item>
  <item><category>'RIB min. feature size violation (0.25um)'</category><cell>DIE</cell>
   <values><value>polygon: (100,20;100,21;101,21;101,20)</value></values></item>
 </items>
</report-database>
"""


def test_markers_are_read_with_their_first_vertex(tmp_path: Path):
    p = tmp_path / "r.lyrdb"
    p.write_text(LYRDB, encoding="utf-8")
    marks = s06_drc.parse_report_markers(p)
    assert len(marks) == 2
    assert marks[0][1:] == (-4835.0, -1259.185)
    assert marks[1][1:] == (100.0, 20.0)
    assert s06_drc.parse_report(p) == {"RIB min. feature size violation (0.25um)": 2}


def test_the_release_judges_the_count_outside_the_field():
    drc = {"deck": {"violations_total": 20, "violations_outside_monitor_field_total": 0}}
    assert s15_release._deck_outside(drc) == 0
    drc = {"deck": {"violations_total": 20}}
    assert s15_release._deck_outside(drc) == 20
    assert s15_release._deck_outside({"deck": {}}) is None


def test_the_runner_classifies_by_the_field_box():
    src = Path(s06_drc.__file__).read_text(encoding="utf-8")
    assert "monitor_field_box_um" in src
    assert '"violations_outside_monitor_field_total"' in src
    assert 'key="drc.deck_violations_in_monitor_field_only"' in src
