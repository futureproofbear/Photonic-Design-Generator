# Projects

**A project is a separate repository. It is not a subfolder of this one.**

This tree previously held one folder per design scope directly inside the
framework, at `projects/<scope-name>/`. That arrangement is retired. A design
scope now lives in its own repository, which reaches this framework as a
**git submodule**, mounted at `.framework/`.

`_template/` remains as a source of file skeletons to copy from — see below —
but nothing new is created directly under `projects/`.

## Why the arrangement changed

Nesting a project inside the framework made the two hard to keep apart in
practice: a commit touching both was one commit, a clone of the framework
carried every project along with it unless deliberately excluded, and the
boundary depended on `.gitignore` doing the separating rather than the
repositories being separate to begin with. Two independent repositories make
the separation structural instead of procedural.

**The submodule, and not a plain symlink to a sibling checkout, is the
correct mechanism**, for a reason that matters beyond convenience: a
submodule pins a project to one recorded framework commit. A design's
numbers stay traceable to the framework state that produced them, months
later, on a different machine, or after the framework has moved on. A
symlink to a sibling checkout was tried and reverted — it removes that pin
silently, so a framework change made for one project can alter every other
project's behaviour with nothing in any project's own history saying so. It
is viable only as a short-lived expedient while the framework repository is
unreachable by other means, and this repository is public, so that
expedient is not needed.

## Starting a New Project

```bash
mkdir my-project && cd my-project
git init
git submodule add https://github.com/futureproofbear/Photonic-Design-Generator.git .framework

# The skills and sub-agents become discoverable at the conventional
# Claude Code paths without duplicating their content. Real symlinks are
# tracked by git as a small blob naming their target, not as a copy of what
# they point to, so this adds two lines to the repository, not a duplicate
# tree.
mkdir .claude
cmd /c mklink /D .claude\skills .framework\.claude\skills     # Windows
cmd /c mklink /D .claude\agents .framework\.claude\agents     # Windows
ln -s ../.framework/.claude/skills .claude/skills             # Linux/macOS
ln -s ../.framework/.claude/agents .claude/agents             # Linux/macOS
```

Windows note: creating a symbolic link requires either an elevated shell or
Developer Mode enabled (Settings > Privacy & Security > For developers).
Without one of those, `mklink` and PowerShell's `New-Item -ItemType
SymbolicLink` both fail with a privilege error; the submodule step above is
unaffected either way.

Then, at the new repository's own root:

1. Write `CLAUDE.md`, stating the hardware target, the active design, and
   importing the register standard: `@.framework/rules/generic/prose-and-register.md`.
2. Write `proprietary_terms.txt` (copy the skeleton from
   [`_template/proprietary_terms.txt`](_template/proprietary_terms.txt)) — the
   client and programme identifiers, declared before any analysis is written.
3. Create `designs/<design-name>/`, with `requirements/` before `design.yaml`
   exists, so that what the design is required to do is reviewed before it is
   baselined. **Invoke the `requirements-reviewer` sub-agent on that set before
   baselining it.** It recomputes every derived value, registers the
   contradictions within the source document, tests each requirement against
   the platform constraints and the selected parts, and checks whether a
   requirement inherited from a reference device still measures what limits
   this architecture. Those errors are committed before a design file exists
   and they survive every later check, because the run is faithful to a
   requirement set that was already wrong.
4. Run the chain from inside the submodule, pointing back at the design:

   ```bash
   cd .framework/design-chain
   python -m picchain.cli run ../../designs/<design-name>/design.yaml
   ```

`_template/` also carries [`IP_BOUNDARY.md`](_template/IP_BOUNDARY.md) and a
platform skeleton at `designs/_platform/platform.yaml`; both are written for
the old nested arrangement and their relative paths need adjusting to the new
repository's own layout when copied. The wording of the restrictions
themselves does not change.

## The IP Rule, Unchanged in Substance

**Project information does not leave the project repository.** This applies
to the framework's generic documentation, the shared toolchain, the public
examples, the skills and sub-agents under `.claude/`, and commit messages
inside `.framework/`.

Capability flows inward without restriction: the shared toolchain, the public
examples and the methodology documentation are all intended for use from a
project. Nothing about that direction has changed; only the mechanism that
enforces the other direction has.

## How a Learning Gets Back to the Framework

**The submodule is a real, independent checkout with its own `.git`.**
Editing a file under `.framework/` from inside a project is editing that
checkout; committing and pushing from inside it updates the framework's own
history on the framework's own remote, exactly as if the edit had been made
from a clone of the framework directly. The project's own commit is separate,
and records only the pointer to the framework commit the project now
depends on — which is the traceability point the submodule exists to give.

The discipline that makes the edit itself safe is unchanged from
[`../.claude/LESSONS.md`](../.claude/LESSONS.md): a lesson is admissible only
where it remains true and useful with the originating project entirely
removed. In practice, from inside a project:

1. Invoke the `lesson-harvester` sub-agent against the project's own run
   artifacts, which are never inside `.framework/` and are never read by it.
2. Review each proposed entry against the four-question test in
   `.claude/LESSONS.md` — would it read identically from a different project,
   does it name anything project-identifying, does it quote a client-sourced
   number, does it reproduce a delivered design's parameters.
3. Make the accepted edit under `.framework/` — the ledger entry, the rule, or
   the skill, whichever applies.
4. `cd .framework && python tools/check_ip_boundary.py --app-root ..`, run
   from inside the framework checkout with the project repository named
   explicitly as the application root. Detection also runs automatically
   here without `--app-root`, since a submodule checkout carries the linked
   `.git` file the check looks for.
5. Commit and push from inside `.framework/` — an ordinary commit to the
   framework's own history, on the framework's own remote.
6. Back in the project repository, `git add .framework && git commit`, to
   record the new pointer. This step is what a symlink arrangement cannot
   give: a reviewable diff showing exactly when the project picked up new
   framework capability, and what commit it now depends on.

A lesson recorded but not enforced by a test will be relearned; step 3 is
expected to include a closed-form test under `.framework/design-chain/tests/`
wherever the skill it touches has one.

## Declaring Terms

`proprietary_terms.txt`, at the project repository's own root, holds the
strings that identify it. Guidance:

* Include the client name, the programme name, the application, the operating
  band where it is identifying, deliverable and work-package codes, distinctive
  part numbers named in client documents, and client document filenames.
* Exclude generic physics and platform vocabulary. A material name, a solver
  name or a device class is not proprietary and a term that broad renders the
  check unusable.
* The combination is often what identifies a scope even where the individual
  words do not. Where that is the case, declare the phrase rather than the
  words.

The file is itself proprietary and is not to be committed into `.framework/`.

## Running the Check

From inside the framework checkout:

```bash
python tools/check_ip_boundary.py            # auto-detects the submodule arrangement
python tools/check_ip_boundary.py --list     # confirm the term list is loaded
python tools/check_ip_boundary.py --app-root /path/to/my-project   # override, where auto-detection does not apply
```

Detection runs automatically wherever the framework is reached through a
linked `.git` file — the marker a git submodule checkout carries — or
through a directory literally named `.framework`. `--app-root` exists for
the case neither holds.

Exit code 0 indicates that no declared term appears inside `.framework/`.
Exit code 1 reports the file, line and term of each occurrence.
