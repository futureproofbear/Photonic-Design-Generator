"""A material file named by a design must be found from any working directory.

The path was handed to the loader as written, so it was resolved against the
working directory alone. A design carrying a foundry material file therefore ran
from the repository root and failed from its own folder with a bare
file-not-found, which reads as a missing file rather than as a path resolved
against the wrong place.

Four locations are now searched in order: beside the design file, against the
working directory, against the root of the chain installation, and against the
repository above it.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from picchain.config import Design

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _design(tmp_path: pathlib.Path, materials: str) -> pathlib.Path:
    p = tmp_path / "design.yaml"
    p.write_text(
        "meta:\n"
        "  name: path_probe\n"
        "  title: \"A design that names a material file\"\n"
        "platform:\n"
        f"  materials_file: {materials}\n"
        "grating:\n"
        "  enabled: false\n",
        encoding="utf-8",
    )
    return p


def test_found_beside_the_design(tmp_path, monkeypatch):
    (tmp_path / "materials.yaml").write_text("materials: {}\n", encoding="utf-8")
    d = Design.load(_design(tmp_path, "materials.yaml"))
    monkeypatch.chdir(ROOT)
    assert pathlib.Path(d.materials_path()) == tmp_path / "materials.yaml"


def test_found_against_the_working_directory(tmp_path, monkeypatch):
    lib = tmp_path / "elsewhere" / "materials.yaml"
    lib.parent.mkdir()
    lib.write_text("materials: {}\n", encoding="utf-8")
    d = Design.load(_design(tmp_path, "elsewhere/materials.yaml"))
    monkeypatch.chdir(tmp_path)
    assert pathlib.Path(d.materials_path()) == lib


def test_found_against_the_repository_root_from_any_directory(tmp_path, monkeypatch):
    """The vendored library, named as the repository sees it."""
    named = "design-chain/pdk/materials.yaml"
    assert (ROOT / named).exists()
    d = Design.load(_design(tmp_path, named))
    monkeypatch.chdir(tmp_path)
    assert pathlib.Path(d.materials_path()).exists()


def test_a_path_that_exists_nowhere_names_what_was_tried(tmp_path, monkeypatch):
    d = Design.load(_design(tmp_path, "no/such/materials.yaml"))
    monkeypatch.chdir(ROOT)
    with pytest.raises(FileNotFoundError) as excinfo:
        d.materials_path()
    message = str(excinfo.value)
    assert "no/such/materials.yaml" in message
    assert "Tried:" in message
    assert str(tmp_path) in message


def test_a_design_naming_no_file_returns_none(tmp_path):
    p = tmp_path / "plain.yaml"
    p.write_text("meta:\n  name: plain\n  title: \"No material file\"\n"
                 "grating:\n  enabled: false\n", encoding="utf-8")
    assert Design.load(p).materials_path() is None
