# A design is settled in stages, and each stage exists to refute the one before

*Tier: generic. Confidence: high. The staging below was performed on one design.
Stage 0 admitted the architecture in microseconds; stage 1 found a defect in its
own objective; stage 2 found the closed form wrong in two places and the
uncertainty intervals wrong on two axes of three; and the verification of stage
2 established that its instrument could not resolve the question at all.*

The models available to a photonic design differ in cost by ten orders of
magnitude. Algebra is microseconds, a closed form is milliseconds, a mode solve
is seconds, a time-domain solve is hours. **A search cannot contain the
expensive model and the expensive model cannot explore the space**, so the work
is staged, and the staging is not an administrative convenience.

Three things force it and they compound.

**Cost.** One search performed about 10⁶ closed-form evaluations in a second.
The same grid with a mode solve inside it is months.

**Variables change meaning with fidelity.** A coupling constant is a number in
closed form. In reality it is *produced* by a post gap and a post size, and only
a mode solve maps one onto the other.

**Some constraints have no closed form at all.** Side-mode suppression as a
number, sidelobe levels, chirp linearity and metal absorption in decibels per
centimetre cannot enter an early stage on any terms.

## The stages

| stage | model | free variables | what it decides | cost |
|---|---|---|---|---|
| **0 · reachability** | algebra | none | whether the architecture admits the requirement at all | µs |
| **1 · lumped search** | closed form | what the mask controls | the design point and its worst-case margin | seconds |
| **2 · geometry inversion** | mode, electrostatic and finite-element solves | the geometry that produces stage 1's lumped quantities | the mask dimensions, **and it measures the parameters stage 1 assumed** | minutes |
| **2b · model verification** | an independent method on one lumped quantity | none | whether stage 1's model of that quantity is correct | minutes to hours |
| **3 · cavity verification** | transfer matrix and rate equations | drive ratio, bias, operating point | what no closed form reaches: hop count under sweep, side-mode suppression, linewidth | minutes |
| **4 · layout** | polygons, rule deck, corners | apodisation, taper, routing | manufacturability and yield | hours |

## Stage 0 refutes before it costs anything

Every architecture carries an inequality that admits or forbids the requirement
before a dimension is chosen. Evaluate it first. Where it fails, the finding is
the architecture or the purchased part, and it is reported without running
anything.

An extended cavity is the clear case: the untuned delay must satisfy
`tau_u < 1/(2 dnu)`, so a gain chip longer than a stated length makes the
excursion unreachable by any mirror of any strength. **That is a statement about
the chip and not about the grating**, and it is available from a datasheet.

## Stage 1 optimises, and its objective is the thing most likely to be wrong

The search is cheap, so the temptation is to trust it. What fails is not the
search but the set it is given, and the failure presents as a confident answer.

The method belongs to [`design-under-uncertainty.md`](design-under-uncertainty.md).
What belongs here is the ordering consequence: **stage 1 is re-run whenever
anything below it moves**, because it costs a second and everything else costs
hours. It is not a phase that has been passed.

## Stage 2 measures, and a measurement replaces an assumption

The stage exists for three purposes and only the first is what a reader expects
of a simulation.

**Inversion.** A lumped quantity becomes geometry. On one design the coupling
constant was inverted into a post gap by five mode solves, which established a
decay of −5.23 µm⁻¹, constant to two decimals. The gap borrowed from a
comparable device on another platform was wrong by a factor of 5.5, and the two
platforms agreed on the decay while disagreeing entirely on the value.

**Measurement.** The parameters stage 1 carried as unknowns become solver
outputs, and the interval they occupied is replaced by one that was measured.

**Adjudication.** A quantity asserted at two values in two documents is settled
by computing it on the design's own geometry, which removes the question rather
than deciding between the claims.

Two disciplines attach. **A measured quantity is recorded at an advisory
severity rather than graded against the value that was assumed for it**, since
grading a measurement against its own assumption is circular. And **a lumped
quantity that stage 1 treated as free may not be free in geometry**: on one
design weakening the grating opened the post gap, which moved the posts outward,
which forced the electrode to retreat to hold a metal-to-ridge rule, which
lowered the tuning rate as one over the gap. Stage 1 had chosen the electrode
gap from a fixed list and could not see the coupling, never having drawn a post.

## Stage 2 is also where the closed form is caught being wrong

Run the closed form and the solver at **identical geometry** and compare every
quantity. Agreement is worth having and disagreement is worth more.

On one design that comparison found two defects in a closed form that had been
carried through four revisions. A mirror was treated as loss-free, which
overstated its reflectivity by 6.4 per cent and overstated the margin against
the reflectivity bound from +7.7 per cent to +33.6. And the electrode geometry
was decoupled from the coupling constant, as above. Corrected, the two agreed to
under 0.4 per cent on seven quantities.

**The consequence of a model error is often in the margin rather than in the
value**, and the margin is what the design is steered by. A six per cent error
in a quantity moved its margin by a factor of four, because the bound sat close
to the value.

## Stage 2b verifies the model, and may report that it cannot

A lumped quantity produced by a closed form is not measured merely because its
inputs were. Where an independent method exists, run it.

**An instrument has a resolution and the quantity may sit beneath it.** On one
design a band-structure solve was run to check a coupling constant, and the
comparison was refused: between two mesh densities the method moved the quantity
by 0.613 cm⁻¹ against a disagreement of 0.339 cm⁻¹, so **the instrument's error
was 1.8 times the signal**. The band gap being measured was a split in the fifth
decimal between two nearly degenerate bands, and the difficulty scales inversely
with the coupling strength the design had deliberately made small.

That outcome is a finding and is to be recorded as one. **A comparison that
cannot resolve the question establishes nothing, and a number taken from it is
worse than no number**, since it will be quoted. Report the mesh shift beside
the disagreement so that a later reader can see which exceeded which.

## It is a loop, and the return path is what pays

    0 -> 1 -> 2 -> re-run 1 with the measured box -> 2b -> 3 -> 4
              ^                                  |
              +----------------------------------+

Stage 1 assumes an interval box. Stage 2 computes several of the parameters that
box is made of. On one design that return path took the worst-case margin from
+8.89 per cent to +1.13 per cent, the measured intervals being wider than the
assumed ones on two axes of three. **The design had not changed and the number
had been wrong for a week.**

A stage that finds nothing has still established that the stage before it was
right, which is what makes the ordering worth keeping.

## What is derived is never a free variable

Penetration depth, free spectral range, delay ratios and active fraction follow
from other choices. Treating them as independent over-specifies the problem and
returns designs that are internally inconsistent.

A quantity that *follows* from geometry but must be *supplied* by something
external is a third case, and it enters as a constraint on that external thing
rather than as a design variable. A drive ratio is the example: it is fixed by
the cavity, and the driver has to deliver it.

## Do not run a stage on a geometry that is about to move

Where an open question would change the geometry, the stages that consume that
geometry wait. On one design the verification of stage 2b was outstanding, and
its answer would have moved a post gap, an electrode gap and a tuning rate
together. Computing side-mode suppression and linewidth from that geometry first
would have produced figures for a cavity that no longer existed.

## Evidence

`.claude/LESSONS.md` L030 (a lumped variable that is not free in geometry), L031
(an instrument whose error exceeded the signal), L026 and L027 (the interval box
and its verification), and
[`design-under-uncertainty.md`](design-under-uncertainty.md),
[`expensive-solves.md`](expensive-solves.md) and
[`independent-cross-checks.md`](independent-cross-checks.md), whose subjects are
the cost, the ordering and the independence this staging depends on.
