#!/usr/bin/env python3
"""IP boundary check.

Project-specific information is required to remain within
``projects/<project>/``. This script enforces that requirement mechanically so
that the boundary is not dependent on recollection.

How the term lists are handled
------------------------------
The terms that identify a project are themselves proprietary to it, so they
cannot be held in a shared list at the repository root. Each project therefore carries its
own ``proprietary_terms.txt``. Every such file is read, and the union of the
terms is searched for across the *generic* tree only. A term never appears
outside its own project by construction.

Scope of the scan
-----------------
Scanned:      everything outside ``projects/``
Not scanned:  ``projects/`` itself, ``.git``, ``.venv``, ``__pycache__``,
              ``runs/``, and binary files

Usage
-----
    python tools/check_ip_boundary.py            # scan, report, set exit code
    python tools/check_ip_boundary.py --list     # show the loaded term count only
    python tools/check_ip_boundary.py --root .   # explicit repository root

Exit codes
----------
    0   no project term found outside its project folder
    1   a leak was detected; the offending file, line and term are reported
    2   invocation error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "__pycache__", "runs", "node_modules",
             ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist"}
SKIP_SUFFIXES = {".pdf", ".gds", ".oas", ".npz", ".png", ".jpg", ".jpeg", ".gif",
                 ".zip", ".gz", ".whl", ".pyc", ".exe", ".dll", ".so", ".dylib"}
TERMS_FILENAME = "proprietary_terms.txt"


def load_terms(projects_dir: Path) -> dict[str, list[str]]:
    """Return {project_name: [term, ...]} for every project that declares terms."""
    out: dict[str, list[str]] = {}
    if not projects_dir.is_dir():
        return out
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        f = proj / TERMS_FILENAME
        if not f.is_file():
            continue
        terms = []
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                terms.append(line)
        if terms:
            out[proj.name] = terms
    return out


def iter_scannable(root: Path, projects_dir: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if projects_dir in path.parents or path == projects_dir:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def scan(root: Path) -> list[tuple[Path, int, str, str, str]]:
    projects_dir = root / "projects"
    terms_by_project = load_terms(projects_dir)
    if not terms_by_project:
        return []

    patterns = []
    for project, terms in terms_by_project.items():
        for t in terms:
            # word-boundary match where the term is alphanumeric at its edges,
            # so that a short acronym does not fire inside a longer word, while
            # a hyphenated term still matches as written
            lb = r"\b" if t[:1].isalnum() else ""
            rb = r"\b" if t[-1:].isalnum() else ""
            patterns.append((project, t, re.compile(lb + re.escape(t) + rb, re.IGNORECASE)))

    hits = []
    for path in iter_scannable(root, projects_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for project, term, pat in patterns:
                if pat.search(line):
                    hits.append((path, n, project, term, line.strip()[:120]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="repository root (default: parent of this script)")
    ap.add_argument("--list", action="store_true", help="report the loaded term count and exit")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not (root / "design-chain").is_dir():
        print(f"error: {root} does not look like the repository root", file=sys.stderr)
        return 2

    projects_dir = root / "projects"
    terms_by_project = load_terms(projects_dir)

    if args.list:
        if not terms_by_project:
            print("no project term lists found")
        for project, terms in terms_by_project.items():
            print(f"{project}: {len(terms)} terms declared")
        return 0

    if not terms_by_project:
        print("no project term lists found; nothing to enforce")
        return 0

    hits = scan(root)
    n_terms = sum(len(t) for t in terms_by_project.values())
    scanned = sum(1 for _ in iter_scannable(root, projects_dir))

    if not hits:
        print(f"PASS  {scanned} files scanned against {n_terms} terms "
              f"from {len(terms_by_project)} project(s); no leak detected")
        return 0

    print(f"FAIL  {len(hits)} occurrence(s) of project-proprietary terms found "
          f"outside projects/\n")
    for path, n, project, term, line in hits:
        rel = path.relative_to(root)
        print(f"  {rel}:{n}")
        print(f"      project : {project}")
        print(f"      term    : {term}")
        print(f"      line    : {line}")
        print()
    print("Remedy: move the content into the project folder, or reword the "
          "generic file so that the project is not identifiable.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
