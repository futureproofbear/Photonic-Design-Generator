# gdsfactory

Used here as a second, independent layout backend. The mask is emitted twice and
the two are compared layer by layer, so that a defect in one writer is visible.

## A process-wide cell library silently disables the backend

The framework holds its cells in a library scoped to the process, and that
library refuses a repeated cell name. **Any chain emitting a layout more than
once within a single process therefore loses this backend after the first
call**, and the comparison against it is skipped rather than failed.

The condition was invisible. The metric recorded the backend as unavailable,
which is also what an uninstalled backend records.

**A corner study is precisely the case that emits repeatedly.** The cross-check
ran on the first corner alone, and the remaining corners recorded it as
unavailable.

Two practices follow.

**Clear the library before each emission.**

**Distinguish "not performed" from "performed and agreed" in the metric tree.**
Any stage able to skip a cross-check silently is to state which of the two
occurred. The chain reports `layout.backend_gdsfactory_available` beside
`layout.backend_xor.performed` and `layout.backend_xor.agree` for this reason.

## What the comparison establishes and what it does not

The comparison is a layer-by-layer geometric difference reported as a residual
area, so it localises a disagreement. It establishes that two writers produced
the same polygons from one description.

**It does not establish that the description is correct.** Both writers consume
the same resolved design, so a wrong dimension, a wrong layer number or an absent
feature is emitted identically by both and the residual is zero. The instruments
that bound those are the rule deck, the golden reference and measuring a declared
quantity back off the written file.

## Evidence

`.claude/LESSONS.md` T010, T013.
