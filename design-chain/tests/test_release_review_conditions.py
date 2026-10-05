"""The four release conditions that answer a pre-submission review.

They are the rows of `rules/generic/design-review.md` that can be computed from a
written mask: labels unique, a label per named device, the file and cell naming,
and the margin between a drawn feature and the rule it clears.

Each answers something that costs the measurement or the submission rather than
the wafer, so neither a rule deck nor a connectivity check reports it. Two of the
four have a failure mode of their own, and both are pinned below.

**A check with nothing to compare must not pass.** A mask carrying no text
satisfies "every label is unique" vacuously, and a condition that passes because
there was nothing to compare is the failure `rules/tool/klayout/README.md` names.

**A name is compared without regard to case.** A die cell is conventionally the
design name uppercased with a suffix. The first version of the naming check was
case-sensitive and reported `LTOI300_MZM_TESTCHIP_DIE` as not carrying
`ltoi300_mzm_testchip`, which it carries exactly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picchain.stages import s12_mask, s15_release

MASK_SOURCE = Path(s12_mask.__file__).read_text(encoding="utf-8")
RELEASE_SOURCE = Path(s15_release.__file__).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# the label inventory
# --------------------------------------------------------------------------

class _Text:
    def __init__(self, string, x=0, y=0):
        self.string, self.x, self.y = string, x, y

    def transformed(self, _):
        return self


class _Shape:
    def __init__(self, text):
        self.text = _Text(text)

    def is_text(self):
        return True


class _Iter:
    def __init__(self, shapes):
        self._s = list(shapes)

    def at_end(self):
        return not self._s

    def shape(self):
        return self._s[0]

    def trans(self):
        return None

    def next(self):
        self._s.pop(0)


class _Info:
    layer, datatype = 10, 0


class _Layout:
    dbu = 0.001

    def __init__(self, texts):
        self._texts = texts

    def layer_indexes(self):
        return [0]

    def get_info(self, _):
        return _Info()


class _Top:
    def __init__(self, texts):
        self._texts = texts

    def begin_shapes_rec(self, _):
        return _Iter(_Shape(t) for t in self._texts)


def inventory(texts):
    return s12_mask._label_inventory(_Layout(texts), _Top(texts))


def test_distinct_labels_are_unique():
    inv = inventory(["DEV1", "DEV2", "CAL1"])
    assert inv["count"] == 3 and inv["distinct"] == 3
    assert inv["unique"] is True
    assert inv["duplicated"] == []


def test_a_repeated_label_is_reported_with_its_text():
    inv = inventory(["DEV1", "DEV2", "DEV1"])
    assert inv["unique"] is False
    assert inv["duplicated"] == ["DEV1"]
    assert inv["count"] == 3 and inv["distinct"] == 2


def test_a_mask_with_no_text_is_not_unique():
    """The vacuous case, which is the one worth a test."""
    inv = inventory([])
    assert inv["count"] == 0
    assert inv["unique"] is False, (
        "a mask carrying no label satisfies uniqueness vacuously; reporting that "
        "as met is a condition passing because it had nothing to compare")
    assert "vacuous" in inv["note"]


# --------------------------------------------------------------------------
# a label for every named device
# --------------------------------------------------------------------------

def test_every_named_device_found_in_a_label():
    ok, detail = s15_release._devices_labelled(
        {"labels": ["DEV1", "DEV2"]},
        {"performed": True, "texts": ["CHIP REV A", "DEV1 g=5.5", "DEV2 g=8.0"]})
    assert ok is True
    assert "all 2" in detail


def test_a_named_device_with_no_label_is_reported_by_name():
    ok, detail = s15_release._devices_labelled(
        {"labels": ["DEV1", "DEV2", "DEV3"]},
        {"performed": True, "texts": ["DEV1", "DEV2"]})
    assert ok is False
    assert "DEV3" in detail


def test_a_layout_naming_no_device_cannot_be_matched_and_says_what_to_declare():
    ok, detail = s15_release._devices_labelled({}, {"performed": True, "texts": ["X"]})
    assert ok is False
    assert "label_each" in detail, "the detail is to name the field that would satisfy it"


# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------

def test_the_naming_check_is_case_insensitive():
    """The bug this was written for: a die cell is the name uppercased."""
    assert "lowered = name.lower()" in RELEASE_SOURCE
    assert "lowered not in str(top).lower()" in RELEASE_SOURCE
    assert "lowered not in f.lower()" in RELEASE_SOURCE


def test_the_naming_check_reads_a_declared_pattern():
    from picchain.config import ReleaseCfg
    assert ReleaseCfg().name_pattern is None
    assert "re.fullmatch(pattern, f)" in RELEASE_SOURCE


# --------------------------------------------------------------------------
# the rule margin
# --------------------------------------------------------------------------

def test_the_margin_is_declared_and_defaults_to_a_tenth():
    from picchain.config import DRCCfg
    assert DRCCfg().margin_fraction == pytest.approx(0.10)


def test_the_margin_count_subtracts_what_already_fails_the_rule():
    """`at_the_limit` is the band, not the total at the widened threshold."""
    source = Path(__import__("picchain.stages.s06_drc", fromlist=["x"]).__file__)
    text = source.read_text(encoding="utf-8")
    assert "at_the_limit" in text
    assert "max(0, at_margin - real)" in text, (
        "a feature already violating the rule must not be counted again as one "
        "sitting at the limit")


def test_all_four_conditions_are_registered_in_the_gate():
    for condition in ("every text label is unique",
                      "the mask carries a label for every device the layout names",
                      "the emitted files and the top cell carry the design's name",
                      "no feature sits within the rule margin"):
        assert condition in RELEASE_SOURCE, condition


@pytest.mark.parametrize("drc,met", [
    ({"at_the_limit": 0, "margin_fraction": 0.10}, True),
    ({"at_the_limit": 1, "margin_fraction": 0.10}, False),
    ({"at_the_limit": 10, "margin_fraction": 0.10}, False),
    ({"at_the_limit": None}, False),
    ({}, False),
])
def test_a_margin_never_evaluated_does_not_read_as_a_clean_margin(drc, met):
    assert s15_release._margin_met(drc) is met


def test_the_detail_says_when_nothing_was_evaluated():
    assert s15_release._margin_detail({}) == "no margin was evaluated"
    assert "10 per cent" in s15_release._margin_detail(
        {"at_the_limit": 3, "margin_fraction": 0.10})
