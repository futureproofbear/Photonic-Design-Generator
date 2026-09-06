# A passing check is evidence in proportion to its demonstrated ability to fail

*Tier: generic. Confidence: high, established across four independent cases in
one working session.*

A check that cannot distinguish a correct result from a check that did nothing
is not evidence. Before a passing result is accepted, name the failure it would
have caught, and establish that it could have caught it.

## The shapes this takes

**The instrument read an empty input.** A rule deck names twelve layers and the
mask carries geometry on six. Every rule on the other six was evaluated against
nothing and returned clean. The count of violations is a true number and it
describes nothing.

**The instrument was the wrong instrument.** Two rule decks from one foundry
differ in the layer numbers that decide what is read, and in little a reader
notices. A design drawn on one stack's numbers and checked against the other
returned zero violations, ten of ten release conditions and a released manifest.

**The list the check reads did not contain the row.** A corner verdict evaluates
only the metrics named in its own list. Two `must` rows were added to the
targets and not to that list, and the sweep reported nine of nine while the
failing row was never evaluated.

**The bound was never approached.** A swept quantity met its target without
encountering the limit the target is named after. The sweep had exhausted its
drive voltage rather than reaching a mode hop, so the reported figure was the
drive limit multiplied by a rate, and every conclusion drawn from it addressed a
mechanism that was not active.

**A clamp repaired an impossible value and the check then agreed with itself.** A
length went negative, a fallback returned one micrometre, and the stage's own
cross-check agreed to 0.3 % because the expectation was computed from the same
clamped value. The sibling design, whose arithmetic did not go negative,
disagreed by 11 % and looked the worse of the two.

**Two routes agreed because they were one route.** Two expressions carrying the
same sign error agreed to a residual of exactly zero, and the agreement
established that one expression had been evaluated twice. See
[independent-cross-checks.md](independent-cross-checks.md).

## The three mechanical forms

**Coverage.** For every check reading geometry or metrics through a named list,
report what the list resolved to and what it did not reach. A check is to state
its denominator.

**Provenance.** A file encoding a process, a deck or a layer map is to be checked
against the platform the design declares. Two files from one source differing
only in a datatype will not announce the mismatch.

**Falsification.** Where a check can be made to fail on demand, make it fail once
and confirm it says so. A deliberately introduced violation is the cheapest
proof a rule check is live.

**Resolution.** A guard's tolerance is compared to the quantity it grades. A
tolerance wider than the measurand admits every result the guard exists to
reject, and it passes most loudly on the runs that need it. One normalisation
guard admitted two per cent while the loss being reported was a few tenths of
one, so the reference guide's own attenuation was free to exceed the structure's
without remark. Where the two are within a small factor, the run is reported as
unresolved by that cell rather than graded.

**Bounds.** A quantity carrying a physical bound is compared to it on every run,
and the comparison is written into the stage. Transmission through a passive
structure is at most unity. One solve returned 1.00378 and the stage printed it,
because every bound the code knew about was a threshold somebody had declared
and this one belongs to physics.

**Budgets, and the identities that impersonate them.** Where the outputs of a
run are the parts of a conserved quantity, sum them, and first establish that
the sum could come out otherwise. Three rows were once reported as an energy
budget closing to one part in a million when the third was defined as one less
the other two, so the total was one for any values whatever. A sum that cannot
fail discriminates nothing, and it conceals inconsistent denominators among its
terms, because it comes out right regardless. The information in such a
decomposition is in the separate bound on each row.

Where the outputs are genuinely independent measurements of the parts of a
conserved quantity, sum them. Transmitted flux and reflection are both in the payload and their sum
against unity is one addition. It closed in the plane and failed in three
dimensions by 1.6 per cent, which localised a defect to one path without a
further solve, and no run in the history of that stage had ever formed it. A
budget is the cheapest check available and it is the one most often left out,
the parts being reported individually and never added.

**A ceiling on a proposed cause is computed before the cause is accepted.**
Where a reference loses a fraction f, it lifts a quotient by at most f/(1−f). An
excess above that ceiling is not the reference. One attribution stood for the
length of a report on evidence that already contradicted it at one of its two
points, the arithmetic never having been done.

**Enumerate a routine's outcomes before guarding one of them.** A function
returning an optional value has at least three: a result, an exception, and a
quiet absence. A guard written for the exception path was added to a drawing
routine that had lost six figures from a run, and the next run lost the same six
without a word, every one having returned the absence instead. **The quiet
outcome is the likeliest to be the live defect**, precisely because it produces
no symptom to reason from. The tell was already on the record: no failure file
had been written while figures were missing, which says directly that nothing
raised.

**A quiet absence is distinguished from a legitimate one by the input, not by the
routine.** Ask what the routine needed and whether it was there.

**Falsification is two checks and not one.** That the condition is detected, and
that the name it is reported under is the name the acknowledgement, the target
or the test refers to. A guard whose finding key differs from the key its design
file acknowledges fires correctly and is filed as a new finding, which either
fails an enforcing run or joins a list that is not read.

**Read the exit code from the command, and not from a pipeline built around it.**
A chain launched into `tee` reported success while the run had terminated at its
first stage, the captured status belonging to the pipe's last element. Use
`PIPESTATUS` or `set -o pipefail` wherever an exit code is the branch
condition.

## Which artifact is the design

**A directory holding more than one design file states which is the design, in
the first line of every other one.** A superseded baseline is retained because
reports cite it, and nothing about the file itself distinguishes it from the one
that supersedes it. A correction was propagated through such a baseline and
reported as moving two acceptance rows from unmet to met; on the design of
record it moves one the other way, the two sitting on opposite sides of the
target.

**A figure in a report that disagrees with the file you are running is an
orientation signal before it is a discrepancy.** One report quoted a coupling
constant of 1.28 and 1.48 per centimetre throughout while the file being run
returned 3.90. That factor of three was visible for an hour and was read as a
property of the physics rather than as evidence that the wrong file was open.

**Name the design beside the figure, always**, and say which of the files in the
directory it came from. A conclusion about a direction of change carries no
information without it.

## The questions to ask before quoting a number

* **Could this have come out differently?** Where the answer is no under any
  input the design admits, the measurement is vacuous.
* **What would a broken setup produce?** Where that is indistinguishable from the
  result in hand, nothing has been measured.
* **Does the tool state what it actually did**, rather than what it was asked to
  do? Prefer the line reporting the resolved value, the file that was loaded and
  the constraint that was applied.
* **Is the value physically plausible?** Zero resources, exactly identical
  results, perfect agreement and zero spread each warrant suspicion.

## A quantity that should not change is itself a check

Where a transformation is meant to be exact, the affected figure is to come out
unchanged. Reporting the same number to full precision on both sides is strong
evidence the transformation was applied correctly. A changed number indicates a
mistake, and an improved number usually indicates that the baseline was wrong.

## The corollary for reporting

**Report the denominator and never a bare verdict.** A wall of individually true
green checks is how a false summary is assembled. An unexercised rule is to be
reported as unexercised in every document, and distinguished from a rule that
found nothing because nothing was wrong.

**A gate that can be disarmed reports whether it was armed.** Where a design
carries a flag permitting a condition to be bypassed, the readiness row for that
condition states the flag alongside the verdict. A reader cannot otherwise
distinguish a condition that was satisfied from one that could not have failed.

## And a failing check is evidence in proportion to its ability to pass

A verdict of non-compliance is inherently plausible, most of all where the
subject is somebody else's product, and it is examined least at the moment it is
believed most. One checker keyed a scattering entry on a port number where the
identity of a channel is a port and a mode together, so the entries of every
multimode model collapsed and the last read won. It reported that every mode
converter in a supplied library passed under two per cent of its power.
Corrected, they are physical. What caught it was that the number was absurd
rather than merely bad, which is a defence available only for gross errors.

**Before a violation is reported, establish that the instrument returns a pass on
an input known to be sound.** The construction is symmetric with falsification: a
synthesised artifact that must pass, beside one that must fail.

**A checker's key and its accepting grammar are to be as wide as the thing it
reads.** Take one existing artifact, extend it in a way the producing code
already permits, and confirm the checker still reads it.

**A checker with no input reports a pass.** `check_ip_boundary.py` exits zero
where no term list is declared, and a report of a clean boundary drawn from it is
silence from a rule with nothing to compare. State the denominator: what was
compared, and against what.

## Evidence

`.claude/LESSONS.md` T021, T022, T023, T042, T044, T052, T053, T055 (a material
constant declared, gated and never enabled), T056 (a guard added to catch a
silent defect, and its first run raised), and the `corners` and `drc.deck`
coverage reporting those entries produced.
