# What makes two routes to one quantity independent

*Tier: generic. Confidence: high, measured on two unrelated solvers and
demonstrated by three separate failures of independence.*

A quantity computed twice is worth more than a quantity computed once, and only
where the two computations share nothing that could be wrong in the same way.
Independence is a property to be established, and it is ordinarily asserted
instead.

## The four ways independence is lost

**A shared convention.** Two expressions carrying one sign error agree exactly.
A netlist cascade and a closed-form round trip agreed to a residual of zero for
as long as both treated a length of passive guide as subtracting delay from the
mirror rather than adding it. The agreement established that one expression had
been evaluated twice. The anchor that settled it was physical, being that a
length of passive guide lengthens a round trip.

**A shared argument list, partly supplied.** Two code paths computing one
quantity for comparison were driven from one function, and one path called it
with four of its six arguments. The trailing two defaulted to zero, so one side
applied the declared smoothing and the other applied none. The resulting
disagreement was attributed to physics, a correction factor was calibrated to
close it, and the correction was carried for three days. Supplying the missing
arguments reversed the sign of the disagreement.

**A shared clamp.** A stage whose input went negative returned a fallback value,
and its own cross-check was computed from the same fallback. The check agreed to
0.3 % on the broken design and disagreed by 11 % on the sound one.

**A shared mesh, where the shared mesh is the point.** This case is favourable
and is included because the distinction matters. Where a small index difference
is obtained by solving a perturbed and an unperturbed cross-section, the two
solves are performed on one mesh precisely so that the systematic discretisation
error cancels. The difference so obtained is of materially higher standing than
either absolute value entering it. The cancellation has been measured: two
solvers differing by 2.6 × 10⁻⁴ on the absolute index agreed to 1.8 % on the
index difference.

## The three tests

**Name what the two routes share.** Write down the code path, the convention, the
mesh and the input list of each. Where the list has an entry in common that
could be wrong, the comparison bounds nothing about that entry.

**Anchor on a physical statement, and not on a second calculation.** A sign, a
direction and an ordering are settled by asking what the device does. Lengthening
a passive section lengthens a round trip. Closing a gap strengthens an
evanescent perturbation. Where two calculations disagree on a sign, the physical
statement is what decides which of them is wrong.

**Read a cross-check only after its convergence guard has passed.** Two solvers
differing by less than the mesh error of either have established nothing. The
guard is to solve one side at two resolutions and to compare the shift between
them against the separation being measured. A band-structure route ran unguarded
and reported a verdict; the band gap was 5 × 10⁻⁵ of the band frequency and the
answer moved by 39 % between two resolutions, against a claimed disagreement of
63 %. A cross-check without a guard is not a weaker cross-check.

## Where the two routes disagree

**The disagreement is the finding.** It is not to be narrated, attributed or
averaged. State it, quantify it, and establish how much of it is the model
before the remainder is attributed to fabrication.

**Where the two are anti-correlated in some parameter, identify the binding one
before that parameter is chosen.** A swept mode-hop-free range and its closed
form move in opposite directions with the coupling constant. Two weeks of tuning
aimed at the closed form moved a design away from the range it was meant to buy.
Optimising the slack route is worse than not optimising at all.

**A dimensional check is arithmetic and costs a second.** A capacitance was in
error by 10⁶ because a conversion was applied where the chosen units already
cancelled. Any expression mixing micrometre geometry with SI constants warrants
one.

## Evidence

`.claude/LESSONS.md` L012 (the shared-mesh cancellation, measured), L013 (the
quantity a semi-vectorial solver cannot report about itself), T006 (unit
cancellation), T009 (a solver's natural boundary condition), T018 (a cross-check
without a convergence guard), T025 (two code paths, one argument list), T042
(two numbers for one quantity), T052 (a clamp that made a check agree with
itself), and `design-chain/CLAUDE.md` rule 15.
