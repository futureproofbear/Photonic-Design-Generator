# Scoping, launching and reading a solve that costs hours

*Tier: generic. Confidence: high, six distinct misjudgements recorded in one
session, four of them on jobs that were working.*

Most stages of a design chain cost seconds. A time-domain solve, a band
structure and a converged corner sweep cost hours, and every judgement made
about them was wrong at least once for a reason that generalises.

## Before the run

**State what each outcome would imply, before starting.** A three-hour band
structure was queued to confirm a calibration whose parameter does not enter that
solver's inputs at all. The run could not have returned a different answer
whatever the calibration was. A run that cannot change a conclusion is delay and
not evidence.

**Estimate the cost, and estimate it against the quantity being resolved.** A
time-domain measurement was scoped at six hours against a true requirement
nearer thirty-five. Where the quantity of interest is a small difference between
two large computed numbers, the cost of resolving it rises faster than the
signal.

**Move the measurement to where the signal is, rather than raising the
resolution at the design point.** A relative band gap of 1.5 × 10⁻⁵ sits below
the mesh error and is slow to resolve by construction, an iterative eigensolver
converging at a rate set by the separation it is measuring. Displacing one
geometric parameter until the gap is several times wider leaves the mesh error
where it was and makes the measurement tractable. The transfer back to the
design point is then an assumption, and it is to be stated as one.

**Content-hash a deterministic job so an unchanged one is reused.** Two jobs
differing only in the fifteenth significant figure, through floating-point
evaluation order, are one job.

## Launching

**Confirm a launch by the artifact it creates, and never by a log file read
immediately afterwards.** A process that has started has not yet written
anything. A launch was declared failed because its log was read two seconds
later, and it was relaunched; both ran, sharing the machine for thirteen hours at
half throughput against a four-hour solve.

**Give each invocation its own log path.** A shared path cannot record a
duplicate. It conceals one, the second invocation truncating the first on open
and the two then interleaving.

**Before relaunching anything, look for what is already running.** The check
costs one command.

## While it runs

**Record processor time beside wall clock and report the gap.** Wall clock counts
the time a machine spends asleep. A corner reported at 8.2 hours against 70
seconds for each of its neighbours had suspended, and a runaway iteration was
diagnosed in a solver that did not have one.

**Establish the expected cost and the elapsed time before concluding anything
about a job's health.** A twenty-minute test module was called a hang and killed.
A three-hour run was declared dead thirteen minutes in. An eleven-minute sweep
was killed twice by a nine-minute timeout, and the second kill was explained as a
hang in a stage that had never been reached. Checking that a timeout exceeds the
measured duration of the thing it guards is arithmetic.

**A quiet working directory is evidence of nothing.** Where an external solver
writes its log only on completion, a live solve and a dead one are identical from
the filesystem. The process table is the only evidence.

**Where a solve runs longer than its historical cost, check for contention before
concluding the problem is the solve.** Two solvers sharing a machine is
indistinguishable from one solver on a harder problem, from the outside.

## Cancelling

**Killing a process does not kill what it launched across a boundary.**
Cancellation removed an orchestrating process on the host side while the solver
continued inside the virtualised Linux environment, for a further three hours and
forty minutes, on a geometry no longer part of any design.

The condition went unreported for three reasons. The orchestrator was gone, so
the log had stopped being written. The run directory being written into belonged
to a cancelled run. The surviving process is a module invocation of the language
runtime, so it is found by searching the virtualised environment's process table
for that runtime rather than the host's table or the solver's own name.

**After cancelling any stage that shells out, confirm the child is gone on the
side it actually runs on.**

**Capture the decisive pass-or-fail signals before any risky teardown**, so that
the run still yields usable data where the teardown itself hangs.

## Reading the result

**Read the convergence guard before the result.** See
[independent-cross-checks.md](independent-cross-checks.md).

**A decay criterion can stop a solve before the signal arrives.** A run
terminated by field decay at a monitor stops immediately on a long cell, the
field there being still zero when the first check falls due, and returns an
amplitude of exactly zero rather than an error. Impose a minimum run time of
order twice the transit alongside any decay criterion.

## Evidence

`.claude/LESSONS.md` T007, T027, T028, T029, T037, T038, T039, T041, T050.
