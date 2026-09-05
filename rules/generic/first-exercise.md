# The first run of a configuration is a test of the configuration

*Tier: generic. Confidence: high, four defects in one activity, every one of them
a silent substitution rather than a failure.*

A design chain accumulates options faster than it accumulates runs that select
them. A stage that has executed a hundred times has executed one branch of every
conditional it carries. **The first design to select a different branch is
exercising code that has never run**, and the defects that surface are of a
characteristic kind.

## What the failures look like

**Dispatch defaults to the only case that has ever been drawn.** A builder called
one device's constructor unconditionally, so a study of a second device would
have emitted copies of the first.

**A conditional written for the previous case runs unconditionally.** Logic that
adjusts one dimension to clear a feature ran on a device carrying no such
feature, took its inputs from schema defaults, and overwrote the very parameter
the study was varying.

**The absent case has no default.** A recommendation to declare a per-layer
quantity raised a key error on a design declaring an empty mapping, a layer
carrying no value having no key rather than a key of zero.

**An invariant lives in a comment.** A builder's own comment stated the relation
its geometry must satisfy, and the code beneath it broke the relation. The
condition was found by a rule deck and not by anything in the chain.

**A gate refuses the investigation of what it is gating.** A readiness gate that
raises correctly on a blocked submission also stopped the sensitivity sweep that
would have resolved the blockage, because the sweep ran every stage rather than
the stages its metrics need.

**None of these raised where it mattered.** Four substituted a value and
continued, and the others raised only because an empty case reached a subscript.
A silent substitution is the expected presentation of this class, because the
code being entered was written to handle the case it knew about.

## The practice

**Name the option, and enumerate the code that branches on it, before the run.**
A search for the option's name across the stages costs a minute and returns the
list of places where the new branch is untested.

**Read the first run of a new configuration as a test of the chain and not of the
design.** Budget for it. Report the defects found as findings of that run.

**Every invariant a builder states in prose is convertible into a precondition
where its terms are declared fields.** Convert it. A precondition names the code
path that establishes the relation, refuses in milliseconds, and names the fields
that remedy it.

**A conditional is guarded on the presence of what it needs**, and not on the
absence of an alternative. Where the guard fails, the stage refuses rather than
reaching for a default.

**A study's independent variable is immune to automatic adjustment.** Where an
adjustment may move it, the adjustment reports what it did on every copy, and a
copy whose swept value was replaced is no longer a member of the study.

**A tool's own recommendation is a code path the tool supports.** Advice that
cannot be followed on the design it was given is worse than silence, because it
is followed.

**A gate is scoped to the act it gates.** A sweep, a probe and an investigation
are not submissions, and a readiness gate that blocks them teaches the bypass.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) T053 on a precondition
asserted from a guess, T064 on a precondition that must ask whether both things
exist, T068 on a ladder that drew a different device and overwrote its own swept
parameter, T069 on an invariant stated in a comment, T070 on a stage that
recommended a field and then crashed on it, and L017 on a copy adjusted in a
second parameter.
