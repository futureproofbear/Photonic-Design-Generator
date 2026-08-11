# Projects

One folder is allocated per design scope. Each folder is self-contained and
proprietary to that scope.

```
projects/
  _template/            copy this to start a new scope
  <scope-name>/         a design scope
```

## Contents of a Project Folder

```
<scope-name>/
  IP_BOUNDARY.md             the restrictions applying to this folder
  proprietary_terms.txt      the terms the boundary check enforces for this scope
  README.md                  scope overview, status, and the design register
  docs/                      analysis produced for this scope
  designs/                   one folder per PIC, plus a shared _platform/ file
  references/                documents received from or produced for the client
  pdk/                       foundry data received under non-disclosure
```

## Starting a New Scope

```bash
cp -r projects/_template projects/<scope-name>
cd projects/<scope-name>
# 1. edit proprietary_terms.txt    -- the client and programme identifiers
# 2. edit README.md                -- the scope overview
# 3. place client documents in     references/
# 4. place foundry data in         pdk/   and point designs at it through
#                                  platform.materials_file
# 5. create the first design under designs/
python ../../tools/check_ip_boundary.py
```

Step 1 is to be completed before any analysis is written. The boundary check
cannot protect terms that have not been declared.

## The IP Rule

**Project information does not leave the project folder.** This applies to the
generic documentation, the shared toolchain, the public examples, the skills and
sub-agents under `.claude/`, and commit messages.

Capability may flow inward without restriction. The shared toolchain, the public
examples and the methodology documentation are all intended for use within a
project.

Where a technique developed within a project proves generally useful, it is to be
re-expressed without project-identifying content and contributed to the generic
tree as a separate change. The sanitisation procedure is defined in
[`../.claude/LESSONS.md`](../.claude/LESSONS.md).

## Declaring Terms

`proprietary_terms.txt` holds the strings that identify the scope. Guidance:

* Include the client name, the programme name, the application, the operating
  band where it is identifying, deliverable and work-package codes, distinctive
  part numbers named in client documents, and client document filenames.
* Exclude generic physics and platform vocabulary. A material name, a solver
  name or a device class is not proprietary and a term that broad renders the
  check unusable.
* The combination is often what identifies a scope even where the individual
  words do not. Where that is the case, declare the phrase rather than the
  words.

The file is itself proprietary and is not to be relocated.

## Running the Check

```bash
python tools/check_ip_boundary.py          # from the repository root
python tools/check_ip_boundary.py --list   # confirm the term lists are loaded
```

Exit code 0 indicates that no declared term appears outside its own project
folder. Exit code 1 reports the file, line and term of each occurrence.
