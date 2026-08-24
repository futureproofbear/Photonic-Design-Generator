# A design point is chosen against the worst corner, and the corner set is earned

*Tier: generic. Confidence: high. The collapse to corners was verified against
200 000 interior samples on one design; the omission of realisation error was
measured to place an electrode ninety nanometres from a cliff; and the
uncertainty intervals themselves were later measured and found wider than
assumed on two axes of three.*

A design has parameters nobody has measured yet. Choosing the point that
performs best at their nominal values selects a design that is optimal for a
platform that may not exist. What is wanted is the point whose **worst outcome
over the whole interval** is best, and the difference between the two is
routinely the difference between a design that survives fabrication and one that
does not.

Write it as a maximisation of the smallest normalised margin:

    maximise over x    min over theta in Theta    m_i(x, theta)

where `x` is what the mask controls, `Theta` is the interval box of what is not
known, and each `m_i` is one acceptance row normalised so that zero is its
bound. Normalisation is what allows a tuning efficiency in MHz/V and a
dimensionless overlap to be compared at all.

## Normalise every row, and state the sign convention once

    m = (value - bound) / bound          for a lower bound
    m = (bound - value) / bound          for an upper bound
    m = min(value - lo, hi - value) / half_width     for an interval

Zero is the bound, positive is inside it. The design is then described by one
number, and the row that produces it is the binding constraint, which is the
quantity worth reporting beside it. **A margin without the name of the row that
set it cannot be acted on**, since it does not say what to change.

## The inner problem collapses to corners only where the constraints are monotone

The formulation is semi-infinite: one constraint per point of a continuous set.
It becomes finite when every constraint is monotone in every uncertain
parameter, because a monotone function over a box attains its extremum at a
vertex. Four unknowns then cost 2⁴ = 16 evaluations rather than a search.

**Verify the collapse rather than assuming it.** On one design the worst margin
over the 16 corners was compared against 200 000 uniformly sampled interior
points, in both a wide and a narrow box, and the corner bound was the lower of
each pair. That check costs seconds and is the difference between a bound and a
hope. Where an interior point beats the corners, the inner problem is not
monotone and the corner set is not a bound.

## The uncertainty set contains the tolerances on the drawn dimensions

Protecting against unknown parameters does not protect against **realisation
error**, and the two are different things. A parameter is unknown and will turn
out to have one value; a drawn dimension is known and will be printed
imperfectly every time.

The failure has a signature. Where every trade is monotone and opposed, the
optimum is pushed to the boundary of the feasible set, and a boundary has no
manufacturing tolerance by construction. On one design the optimiser placed a
phase-electrode gap **ninety nanometres above a metal-absorption cliff**, and
perturbing that gap by ±0.20 µm swung the margin from −31.75 % to +0.89 %.
Nothing was wrong with the optimiser. The set it was given omitted the
tolerances.

**Fold the drawn tolerances into the same inner minimisation**, so that a
candidate is evaluated at every combination of parameter corner and realisation
excursion. The point that emerges is duller and it can be built.

## An interval that has not been measured is not a measurement

An uncertainty box is a claim about the world and it is ordinarily written
before anyone has looked. Naming it after the measurement it anticipates is the
error, because the label then travels into every downstream margin.

On one design a box labelled as the measured case was later measured, and two
of its three axes were **wider** than assumed: the electro-optic overlap by a
factor of 2.7 and the coupling constant by 3.7. The worst-case margin with
realisation error included fell from +8.89 % to +1.13 % on that correction
alone. **The design had not changed. What changed was the honesty of the box.**

Two consequences follow. Label an assumed interval as assumed, in the file where
it is declared. And re-run the search whenever the box moves, which costs
seconds where the solve that narrowed it cost hours.

## The modelling spread belongs in the box beside the process spread

A parameter carries two independent uncertainties and only one of them is
process. On the same design the process window moved the coupling constant by
29.9 %, and two independent solvers disagreed by a further 4.9 % on the index
difference the coupling constant is proportional to, while agreeing on the
effective index itself to 0.09 %. **The method spread alone exceeded the entire
interval that had been assumed for the parameter.**

A box built from the process window alone therefore understates what is not
known. Where a quantity is produced by a model rather than measured directly,
the disagreement between two implementations of that model is part of its
interval.

## Separate a limit set by the physics from a limit set by the supply

Sweep the drive, or whatever external resource bounds the design, and report the
binding row at each value. Two signatures distinguish the cases. Where the worst
margin stops improving, the design is bounded by the optics and further supply
buys nothing. Where every added increment still improves it, the design is
bounded by the supply, and that is a statement about the electronics rather than
about the cavity.

The distinction decides which part is redesigned, and the two are indis-
tinguishable from a single figure.

## One-at-a-time sensitivity ranks causes and bounds nothing

A tornado varying each unknown alone about the nominal point is worth producing
and is worth reading carefully, because it has two blind spots that present as
findings.

**A parameter outside the currently binding row reports zero swing.** It is not
insensitive; it does not enter the constraint that happens to be tightest at
this point, and it will enter as soon as the binding row changes.

**It cannot see the two-parameter interaction that sets the worst corner**,
which is the quantity the box evaluation returns. Where the leader and the
runner-up sit within a factor of about two, no single parameter dominates and
the ranking is not a licence to measure one and assume the rest.

Generate the accompanying prose from the numbers. A narrative asserting which
parameter dominates was carried through three revisions on one design and was
false in the last two, the binding row having moved beneath it.

## What is to be reported

| quantity | why |
|---|---|
| the worst-case margin **and the row that set it** | a margin alone does not say what to change |
| the interval box, and whether each axis is assumed or measured | the margin means nothing without it |
| the corner-against-interior check | it is what makes the corner set a bound |
| whether realisation error is included | a point without it may sit on a cliff |
| the binding row at each value of the external supply | it separates an optical limit from a supply limit |
| the margin at nominal, beside the worst case | the gap between them is the exposure |

## Evidence

`.claude/LESSONS.md` L026 (the corner collapse, verified against interior
samples), L027 (an interval labelled as measured before it was measured), L021
(a process window states which excursions the sweep can represent), and
[`parameter-scans.md`](parameter-scans.md), whose subject is the validity of the
excursions this method consumes.
