# MEEP and MPB

The time-domain solver and the band-structure solver, reached natively on Linux
and macOS and through a virtualised Linux environment on Windows. These are the
most expensive stages in the chain by two orders of magnitude, so
[`../../generic/expensive-solves.md`](../../generic/expensive-solves.md) applies
in full before anything here.

## A band gap is hard to compute, and for two independent reasons

Measuring a grating's coupling constant from its photonic band structure fails
on a weak grating, and the two causes are separate.

**Discretisation.** A relative band gap of 1.5 × 10⁻⁵ sits below the mesh error.
Twelve pixels across a 300 nm feature staircase its edge, and that perturbs the
geometry by more than the gap can absorb. Halving the mesh halved the answer, so
the measurement carried no information.

**Eigenvalue separation.** The gap **is** the separation between two nearly
degenerate eigenvalues, and an iterative eigensolver converges at a rate set by
that separation. A small gap is slow to resolve by construction. One solve was
still running at iteration 1213 with the trace changing by 10⁻⁶ per cent.

**Widening the feature gap fixes the first and does nothing for the second.**
Moving to a stronger grating therefore does not rescue the method on its own.

## Measure where the signal is

Where the quantity is ill-conditioned at the design point, find a related point
where it is well conditioned, measure there, and carry the result across with the
transfer assumption written down.

Worked case: κ falls exponentially with the feature gap, so a gap 320 nm
narrower gives 5.8 times the coupling and 5.8 times the band gap while the mesh
error stays where it is. The convergence guard went from 99 % of the effect to
12.5 %, and the ratio of measured to closed-form κ came out at 0.6705 at
resolution 40.

**A converged measurement of a neighbouring case with a stated assumption is
worth more than an unconverged measurement of the exact case.** The assumption
here is that the ratio does not vary with the gap, and the evidence bears on it
in both directions: the unconverged measurement at the design point agrees to
2.7 %, while the theory argues the ratio should approach unity as the feature
moves away from the mode.

## Choosing between the two routes

The band-structure route involves no length, no propagation and no radiation
channel, which makes it the sounder instrument in principle.

Measuring the same quantity by propagation requires a length of order 1/κ, which
for a weak grating is millimetres and beyond a finite-difference domain. Forcing
the grating strong enough to measure over a short length introduces radiation,
which coupled-mode theory does not model, and the comparison is then confounded.
**Both failure modes were observed before the correct instrument was used.**

Against that, a time-domain reflectance measurement is better conditioned on both
counts above, its signal being a ratio of fluxes of order unity rather than a
difference of eigenvalues. It costs its own hours, and the estimate is to be made
before the run: one such was scoped at six hours against a true requirement
nearer thirty-five.

## A decay criterion can stop a solve before the pulse arrives

A run terminated by field decay at a monitor stops immediately on a long cell,
the field there being still zero when the first check falls due. The result is a
mode amplitude of exactly zero rather than an error.

**Impose a minimum run time of order twice the optical transit alongside any
decay criterion.**

## Crossing the environment boundary

**Killing the orchestrating process does not kill the solver.** Cancellation
issued on the host side removes the orchestrator while the solver continues
inside the virtualised environment. One such continued for three hours and forty
minutes on a geometry no longer part of any design, taking about 40 % of the
machine from the run that replaced it.

The condition went unreported for three reasons. The orchestrator was gone, so
the log had stopped being written. The run directory being written into belonged
to a cancelled run. The surviving process is a module invocation of the language
runtime, so it is found by searching the virtualised environment's process table
for that runtime rather than the host's table or the solver's own name.

**After cancelling, confirm the child is gone in the namespace it actually runs
in.**

**This solver writes its log only on completion**, so a live solve and a dead one
are identical from the filesystem. The process table is the only evidence.

## The convergence guard doubles the cost

A converged band structure at resolution 40 takes about three hours, and the
guard solves the structure a second time. Budget both before enabling the stage,
and read
[`../../../design-chain/PICCHAIN_REFERENCE.md`](../../../design-chain/PICCHAIN_REFERENCE.md)
under "Running the Chain Efficiently" for the measured cost of every stage.

## Evidence

`.claude/LESSONS.md` L010, T007, T018, T027, T037, T038, T039, T041.
