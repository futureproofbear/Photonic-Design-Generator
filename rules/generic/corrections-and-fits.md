# Adopting, testing and withdrawing a correction factor

*Tier: generic. Confidence: high, two corrections adopted and withdrawn on one
design chain.*

A correction factor is a number introduced to close a gap between a model and a
measurement. It is admissible, and the discipline that admits one is the same
discipline that removes it.

The governing obligation is stated in `design-chain/CLAUDE.md` rule 8: where a
model and a measurement disagree, the disagreement is to be stated and
quantified, and a correction factor is not to be adjusted until agreement is
obtained. This file gives the procedure that obligation implies.

## Before a correction is adopted

**Establish that the disagreement is real and not an artefact of the
comparison.** Confirm the two routes are independent in the sense of
[independent-cross-checks.md](independent-cross-checks.md), and that the
convergence guard on each has passed. A smoothing length was calibrated twice to
close a disagreement that turned out to be a defaulted argument, and the second
calibration replaced the first on the same false basis. Supplying the missing
arguments reversed the sign of the disagreement, so every non-zero value of the
factor made the agreement worse.

**Establish that the correction is transferable to the design point.** A ratio
measured where the signal is large is transferred to a design point where the
signal is small on an assumption, and that assumption is to be written down with
the evidence bearing on it in both directions.

**State what the correction would do to every bounded quantity, and not only to
the one that motivated it.** A correction to a coupling constant reaches the
reflectivity, the stop-band width, the penetration depth, the round-trip delay,
the free spectral range and every quantity derived from those. Reporting its
effect on two of them and leaving the rest unstated invites the reader to assume
the rest are unaffected.

## Measure the corrected point rather than extrapolating to it

**Where a correction is a statement about a model, look for a parameter that
realises it without moving the geometry, and run it.** One run then reports the
whole metric tree at the corrected value, and every extrapolation drawn from a
neighbouring sweep is replaced by a measurement.

A coupling constant measured as overstated by 1.49 was applied in place through
the longitudinal profile smoothing, which scales the harmonic amplitude and
leaves the cross-section, the effective index, the group index, the
electro-optic overlap and the mirror tuning untouched. **The check that the lever
reached only the intended quantity was the Bragg wavelength**, unchanged to seven
figures; a lever that had moved the geometry would have moved it.

The run agreed with the extrapolation on the quantities that had been
extrapolated, disagreed with an earlier estimate of the reflectivity by 13 %, and
supplied two bounded quantities that the extrapolation had left unstated.

**A correction realised through a modelling parameter is recorded as such**, so
that the parameter is not later read as a measured property of the process.

## While a correction is carried

**Record it and do not apply it, wherever the design has margin to absorb the
uncertainty.** Recording states the disagreement and preserves the ability to
compare later measurements against an unadjusted model. Applying it commits the
design to a number that is itself uncertain.

**Where it is applied, apply it in one place and name that place.** A factor
distributed across several expressions cannot be withdrawn.

## When the measurement changes

**Withdrawal is to be as explicit as adoption, and its consequences are to be
reported before they are addressed.** A withdrawal moved a target from met to
unmet, and that failure was recorded in the design file and reported before any
change was made to recover it.

**The recovery is made in the geometry and not in the factor.** A 35 nm change
to the dimension the coupling actually depends on restored every target with
margin. Restoring them by choosing a different value of the factor would have
been the prohibited move, and it would have looked identical in the metric tree.

## The distinction that matters most

A model that has been fitted to a measurement can no longer be used to check
that measurement. Every fitted parameter is a degree of freedom spent, and a
design chain reporting zero fitted correction factors is making a stronger claim
than one reporting agreement. Where a chain carries any, the count belongs in
the verdict.

## Evidence

`.claude/LESSONS.md` L010 (coupled-mode theory over-predicts the coupling
constant, and by how much is measurable), L015 (replacing an assumption with a
sourced value is not a move toward agreement), T025 (two code paths, one
argument list), T026 (a correction adopted to explain a measurement must be
withdrawn when the measurement changes), T042 (a disagreement excused rather
than quantified), T043 (the correction that was itself a spurious correlation).
