# Contributing

## Before anything else: the IP boundary

**Everything outside `projects/` is generic and publishable. Everything inside a
project folder is proprietary to that scope and must never leave it.**

`projects/` is excluded by `.gitignore` and that exclusion is not to be relaxed.
Where a technique developed inside a project has general value, re-express it
without project-identifying content and contribute it separately to
`design-chain/`, `docs/` or `.claude/skills/`.

```bash
python tools/check_ip_boundary.py     # must pass before every push
```

The check reads each `projects/<scope>/proprietary_terms.txt` and searches the
generic tree for those terms. It is mechanical, and it is the reason the
separation survives contact with a deadline.

## Running the tests

```bash
cd design-chain
python -m pytest tests/ -q            # 257 tests, about 4 minutes
```

Some need optional backends. `test_femmode.py` needs `femwell` and takes about
90 s on its own; `test_foundry.py` and `test_reticle.py` need `klayout`, which
is a required dependency. Nothing needs meep.

`python -m picchain.cli doctor` reports what is absent and what to install.

## What a good change looks like

**A solver is validated against a closed form, not against its own last
output.** A regression test that pins the previous number pins the previous
defect with equal fidelity. Every test in `tests/` states in its docstring the
property being asserted, and where it was written in response to a defect, what
that defect was.

**A finding is recorded where it will be met again.** Three places, and they are
not interchangeable:

| where | what belongs there |
|---|---|
| `tests/` | the property, so the defect cannot return unnoticed |
| `.claude/LESSONS.md` | the reasoning, so the next person does not re-derive it |
| the design file | why this number is this number, beside the number |

**An assumption is labelled.** Any quantity not drawn from literature, a
datasheet or a foundry document carries `# ASSUMPTION:` in the design file. The
chain reports unconfirmed material data on every run for the same reason.

**A correction factor is measured, never fitted to make a target pass.** This
is the rule most easily broken with good intentions. `.claude/LESSONS.md` T025
and T026 record an occasion when it was broken here, what it concealed for three
days, and what withdrawing it cost.

## Style

Prose in documentation and in comments is formal and impersonal. Comments say
*why*, not *what*; the code already says what. Where a comment records a defect,
it names the defect rather than describing the fix.

Numbers carry units in the identifier: `length_um`, `tuning_MHz_per_V`. This is
not decoration. A unit that lives only in a comment is a unit that will be lost.

## Reporting a problem

A useful report names the design file, the run identifier, and the metric that
is wrong together with what it should be. Run directories carry
`design.resolved.json` and `run.plan.json`, which together say exactly what was
executed, so attaching those two settles most questions immediately.
