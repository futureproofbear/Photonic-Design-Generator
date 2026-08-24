# A requirement set is elicited, contradicted, decided and re-derived before it is baselined

*Tier: generic. Confidence: high. Every part below was exercised on one design,
and four of the eight caught an error that would otherwise have reached a mask:
a system-layer figure that did not recompute, a requirement inherited from a
device that never demonstrated it, a part substitution that invalidated a cited
noise figure, and an architecture statement contradicted by its own datasheet.*

A design chain consumes targets and returns metrics. Where the targets are wrong
the chain will meet them exactly, and the run will pass. **The acceptance set is
therefore the last place an error can be caught cheaply and the first place it
should be looked for.**

Eight activities constitute the layer. They are listed in the order they are
first performed, and several of them recur.

## 1. Elicitation separates values from derivations

Hold the requirement set as values and provenance only, one file per level, and
put every derivation somewhere else. A file that carries both will restate a
derivation beside each of the four requirements that depend on it, and the four
will drift.

    system.yaml            one file per level: values, units, provenance
    subsystem_<name>.yaml  the same, at the level below
    parts.yaml             vendor figures for what is bought, per constraint
    ANALYSIS.md            every derivation, every recomputation
    DECISIONS.md           every departure from the source, dated
    README.md              what is where, and what stands

Each fact is held once. A YAML row carries the value, the unit, the verification
method and a `source` naming the document and page. **Where a row's value was
computed rather than read, it names the row it descends from.**

## 2. The source's own arithmetic is recomputed before anything is inherited

A scope document states a system layer and derives quantities from it. Recompute
every one of them. On one design all nine derived quantities of the top-level
table reproduced correctly, and establishing that took an hour and made every
subsequent disagreement attributable to the allocation rather than to the
arithmetic.

The failures cluster at the boundary between levels rather than within one, so
the recomputation is what tells you where to look.

## 3. Contradictions are registered, numbered and given a severity

A source of any size contradicts itself. Register each contradiction with an
identifier, both figures, the severity, and the condition that would close it.
Severity is what distinguishes a blocking incompatibility from a notation
collision, and a register without it reads as an equally weighted list of
complaints.

**A conflict is closed by evidence and not by a preference.** On one design a
conflict between two figures for one quantity was closed by reading the source's
own explanation of why it quoted both, having been carried for a week as a
contradiction. Another was closed by a solver computing the quantity on the
design's own geometry, which removed the question rather than adjudicating it.

**A conflict register is a live document.** Entries are added by review long
after elicitation, and one closed entry was later reopened and inverted by a
foundry rule deck.

## 4. Every departure from the source is a dated decision that supersedes explicitly

Where a value is changed, a decision records what it was, what it became, the
rationale, and what follows. Where a later decision overturns an earlier one,
the earlier is struck through and retained rather than deleted, and the record
says which superseded it.

**The retained record is what prevents a superseded figure being requoted.** On
one design two intermediate figures were withdrawn and their withdrawal noted in
the decision that replaced them, and both were nevertheless found still standing
in a document a week later. The strike-through is the mechanism that makes the
staleness visible.

State in each decision **what follows from it**, itemised. A decision to change
an operating band moved a grating period, a drive requirement, a material index
evaluation, and the validity of every cited amplifier noise figure. Three of
those four were consequences nobody would have enumerated without being asked to.

## 5. What is unresolved is a numbered question naming what it blocks

An unknown carried in prose is invisible. Hold open questions in one table with
an identifier, the question, and **what the answer decides**. The last column is
what makes the list actionable, since it converts a curiosity into a dependency.

Close a question with a decision that cites it, and strike the row rather than
removing it. On one design a question about which of two quantities a
requirement referred to was closed from evidence already held in the repository,
having been carried as open for the whole elicitation.

## 6. An inherited target is re-derived whenever the architecture changes

This is the trap that costs the most and presents as success. A design gains an
element that removes a limiting mechanism, inherits the targets written for the
architecture without it, and then **scores worse on the quantity the new element
exists to improve**, because nothing in the acceptance set rewards it.

On one design an intracavity phase section was added to remove a mode-hop limit.
The acceptance set contained no row the phase section could improve, so the
optimiser spent the delay ratio the section depends on and the design required a
second driver at 30 V to reach what the architecture without it reaches on one.
Adding a single row restored it.

**Re-derivation means deriving the number again from the level above, not
adjusting the old one.** The re-derived figure came from the system-level
bandwidth by way of the relation that generates it, and it differed from the
inherited figure by a factor of 2.7. The inherited figure had come from a
reference device, and the reproduction of that device records a failure against
it: **it had never been demonstrated even there.**

Where a goal is retained above the derived requirement, hold both rows and mark
which is which. A goal and a requirement priced differently is a decision worth
seeing; a goal recorded as a requirement is a design sized against a number
nobody asked for.

## 7. The architecture is stated as rows that can be contradicted

Write the architecture as numbered statements in the requirement set, not only as
a diagram. A statement carries a source and can be checked; a diagram cannot be
contradicted by a datasheet.

On one design an architecture row asserted a high-reflectivity facet on a
purchased part whose datasheet gives approximately ten per cent. The lasing
condition, the threshold and the output extraction all follow from the actual
value. The error survived elicitation and a review, and was found only when the
part number was checked against the row.

Where a diagram is produced, generate it from a single source so that its
rendered form and its editable form cannot disagree.

## 8. The set is reviewed against the platform and the parts before baselining

A review that reads only the requirement set can confirm internal consistency
and nothing else. The review that pays is the one that tests each row against
what the platform delivers and what the selected parts do, because that is where
an elicited figure meets a constraint the source never saw.

Reviewing before baselining is the point. A requirement set held as draft can be
corrected; one that has been baselined and flowed into a design file is
corrected in four places.

## What baselining requires

| condition | why |
|---|---|
| every derived value recomputed | an arithmetic error propagates silently |
| every conflict closed or its severity accepted | an open blocking conflict is a design that cannot be built |
| every inherited target re-derived against the current architecture | the trap of part 6 |
| every open question closed, or its consequence stated and accepted | an unknown that blocks nothing may be carried |
| the architecture rows checked against the datasheets they describe | part 7 |

## Evidence

`.claude/LESSONS.md` L028 (an inherited target that was never demonstrated),
L029 (an architecture row contradicted by its own datasheet), L024 (the scope of
a platform limit belongs beside its value), L025 (a specification tighter than
its own justifying analysis), and `design-chain/CLAUDE.md` rule 16, which states
the re-derivation obligation of part 6 and supplies no mechanism for it.
