# templates

Reusable fragments that have proven out on a real design and are general enough
to be started from: acceptance-target blocks with their reasoning, monitor
structure declarations, report skeletons, and rule-deck binding stubs.

**Content is added here once it has been used on at least two designs, and never
authored speculatively ahead of need.** A fragment written in advance of a
second use encodes one design's assumptions under a general name, which is the
failure recorded at `.claude/LESSONS.md` T042: a lesson generalised from one
design carries the conditions of that design, and the conditions are the part
worth writing down.

This directory exists so that the path is stable before it has content.

**It is empty at present.**

## What this is not

[`projects/_template/`](../projects/_template/) is the skeleton of a new design
scope, copied once to start a project. It is a different thing and it is
maintained separately.

[`examples/`](../examples/) holds complete validation designs drawn from public
literature. Those are designs to be run, and not fragments to be copied.

## Admission criterion

A fragment is admissible where all four hold.

1. It has been used on two or more designs.
2. It carries no client, programme, application or deliverable identity, so that
   it survives `tools/check_ip_boundary.py`.
3. It states its own assumptions in comments, so that a design copying it
   inherits the reasoning and not only the values.
4. It names the design activity it came from by class rather than by name, so
   that a reader can judge whether the conditions apply.
