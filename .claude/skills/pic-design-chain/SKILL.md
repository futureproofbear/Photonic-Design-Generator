---
name: pic-design-chain
description: Operate the picchain PIC design chain - run a design, read the metric tree, iterate against acceptance targets, add a stage, or diagnose a failed run. Use whenever a design.yaml is being created or modified, whenever picchain output is being interpreted, or whenever a photonic component must be taken from cross-section to DRC-clean mask.
---

# Operating the PIC Design Chain

The authoritative reference is `design-chain/CLAUDE.md`. Read it before acting.
This skill records the working method that sits on top of it.

## The Loop

```
run → read metrics.verify.rows → change ONE field → run → …
```

Exit codes are the branch condition: 0 targets met, 1 a stage raised, 2
verification failed, 3 malformed invocation.

## Method

1. **Read the targets before the results.** The `targets:` block states what the
   design is for. A run that passes irrelevant targets has established nothing.
2. **Change one field per iteration.** The full extended-DBR chain runs in about
   a minute. Bisection is cheaper than reasoning about coupled changes.
3. **Probe with `--set` before editing.** `--set a.b.c=value` leaves the design
   file untouched and does not move the `latest` pointer.
4. **Use `sweep` for any question of the form "how sensitive is X to Y".** One
   JSON row per point. Sensitivity is nearly always more informative than a
   single value, and two such commands have historically produced the most
   useful findings of an entire study.
5. **Read `metrics.warnings` on every run.** Failure modes that do not present as
   a failed target are reported there.
6. **Answer the process question with `corners`, not with a nominal run.** The
   command re-runs the chain at the edges of the window declared in
   `corners.parameters` and reports the spread of every target metric. Where a
   metric's spread exceeds its own value, the nominal figure carries little
   information.
7. **Know which stages are switched off.** Eight stages run by default. `taper`,
   `fem`, `fdtd` and `bend` are enabled per design because each costs minutes
   rather than seconds: an eigenmode expansion of the taper, four finite-element
   solves, an external time-domain or band-structure solve, and a mode solve per
   bend radius.
8. **Prefer the band structure to propagation for a coupling constant, and
   guard it.** `fdtd.structure: bandstructure` gives κ from the photonic band
   gap of one period, with no length and no radiation channel. Measuring the
   same quantity by propagation needs a length of order 1/κ, and a grating made
   strong enough to shorten that radiates, which coupled-mode theory does not
   model. The gap is the difference of two nearly degenerate bands, so it
   converges slowly: on a third-order grating it was 5 × 10⁻⁵ of the band
   frequency and the mesh moved κ by 39 % between resolution 20 and 40. Read
   `fdtd.convergence.resolved` before the ratio.
9. **Read a cross-check only after its convergence guard has passed.** Two
   instruments that differ by less than the mesh error of either have
   established nothing, in either direction. `fem.convergence.resolved` states
   whether the comparison distinguishes anything, and a warning is raised where
   it does not.
10. **Distinguish an absolute index from an index difference.** A difference
   computed from two solves on one mesh is of a materially higher standing than
   either value entering it, the systematic discretisation error largely
   cancelling. On a shallow-etched thin-film section the two mode solvers
   differed by 2.6 × 10⁻⁴ in fraction on n_eff and by 1.8 % on Δn_eff, the
   latter being a quantity three orders of magnitude smaller. Where a coupling
   constant disagrees with a measurement, the mode solver's Δn_eff is not the
   first place to look.
11. **A clean DRC means the rules supplied were met, on the layout that was
   checked.** The declared `rules` are a smoke test; `drc.deck` runs a foundry
   runset through the KLayout application. Before trusting either, confirm it
   detects a violation deliberately introduced. `drc.checked` and `mask.checked`
   state whether the device cell or the assembled die carried the verdict.
12. **Confirm the mask is the device before reading anything geometric.**
   `layout.draw_periods` draws the whole device by default. Where a count is
   set, the emitted file is a fraction of the device and the rule check, the
   polygon counts and the electrode length all describe the fraction.
   `layout.mask_is_complete` states which case obtains, and
   `layout.require_complete` refuses the partial one.
13. **State the process bias rather than absorbing it into a dimension.**
   `process.bias_um` is the difference between the printed feature width and the
   drawn one. A gap loses what a width gains, both facing edges advancing into
   it. With `process.precompensate` the mask is drawn inward so the wafer lands
   on the nominal dimension; the physics is solved on the printed geometry
   either way. On a grating of order above one the sensitivity is not monotone:
   a positive bias raises Δn_eff and lowers the harmonic amplitude sin(mπD), and
   the two can nearly cancel.
14. **Draw the monitors on the first reticle.** Where a metric moves further
   across the process window than across the design space, the first fabrication
   run is to measure the process rather than only to build the device. The
   `reticle` stage draws four families: κ against gap, loss by cut-back, printed
   critical dimension against drawn, and electro-optic overlap against electrode
   gap. Read `gaps_raised_to_the_rule` afterwards, since a monitor held to the
   deck may not reach the dimension the design uses.

15. **Read the mode-hop-free range between hops, not from zero bias.** The
   zero-bias figure is a property of the cavity phase at zero volts, which a DC
   offset moves at will. Two designs differing by a fraction of a wavelength in
   optical path reported 0.37 and 6.86 GHz. `bias_offset_needed` states when the
   two differ, and `range_limited_by` states whether the excursion ended at a
   hop or at the end of the drive. Those are different findings: the first is a
   property of the cavity and the second of the electronics.
16. **The mirror strength is a control on the tuning range.** Weakening the
   grating deepens the penetration, which lengthens the grating delay and raises
   the Pockels lever, so κ moves the reflectivity, the bandwidth and the tuning
   range together. It is bounded, the penetration never exceeding half the
   grating length. On a third-order TFLN mirror the asymptote was 7.47 GHz
   against an 8 GHz requirement, so weakening alone did not reach it and the
   passive path had to shorten as well.

17. **Reach for `search` before hand-iterating, and read its phase 3 first.**
   The reachability pass evaluates every declared parameter at both bounds
   before any solving, so a requirement no parameter can reach is reported in a
   few runs rather than discovered after an afternoon of bisection. Phase 2 is
   the elasticity matrix, which answers "which knob moves which target" in one
   run per parameter, and is worth reading even when the design already passes.

18. **Sensitivity is two tables, and risk needs a third thing.** Elasticity
   ranks the knobs and is physics; contribution over the declared excursion ranks
   the process; neither is risk until both are set against the margin the target
   leaves. A metric of elasticity −14 sitting three decades below its bound is
   not a risk, and a metric of elasticity 1 sitting on its bound is.
19. **An elasticity on a non-monotone metric is meaningless.** It will differ by
   an order of magnitude with the width of the probe. Check the reachability
   monotonicity flag before quoting any derivative of the tuning range.
20. **Read the per-corner failures, not only the spread.** A corner summary
   aggregates. The useful question is which target failed at which excursion,
   and on the validation baseline that is what revealed the single-mode
   condition failing at three of eight.

21. **Keep the run register.** The design report must carry a table of what was
   run, when, with which parameters, how many evaluations it cost, and what it
   established. Superseded studies stay in it, marked superseded; discarded ones
   say why they were discarded. A conclusion without its register is an
   assertion.

22. **Replace the layer numbers before running a foundry deck, and check the
   replacement.** A deck reads layers by number. Placeholder numbers do not
   merely fail to match; they collide. On one baseline the chain's slab sat on
   the number the process reads as its ridge, its alignment marks on the number
   the process reads as metal, and its waveguides on a number the deck reads not
   at all. The deck then reported violations on the slab rectangle, checked the
   marks as though they were metal, and never examined a waveguide, a grating
   feature or an electrode. **That result is a false pass and is worse than
   running no deck**, since a small non-zero count reads as a check that was
   performed. After remapping, confirm that each layer the deck names is a layer
   something is actually drawn on.

23. **A runset checks a chip, not a device cell.** Footprint, centring and
   exclusion-ring rules are evaluated against an outer boundary and a usable-area
   rectangle, and neither exists until the die assembly draws it. A deck run
   against a device cell reports nothing on those rules. **Silence there is not a
   pass**, and it is to be recorded as not exercised. Where a device-level floor
   plan is mapped onto the usable-area layer to obtain a device-level check, that
   mapping becomes wrong at die level, a die spreading content far outside any
   single device's bounding box.

24. **A runset written for the graphical application names no input and no report
   file.** It expects a layout already open and a marker browser. Executed
   headless it stops at its first layer read with no source. Supply the input and
   the report file, alter nothing else, and record what was supplied. The rules
   evaluated must remain the foundry's own.

25. **Die footprints are quantised, and a size between them is refused.** A
   process offers a fixed set of die dimensions. Record that set in the design
   and check against it, rather than discovering it at submission. **Confirm that
   the die emitted is the die declared**: on one baseline the usable area was
   computed by deducting the margin, the seal width and the dicing lane but not
   the seal-ring clearance, which the ring then added back, so a declared
   footprint was written 120 um larger in each dimension. Nothing reported it,
   there being no boundary drawn against which a footprint could be checked.

26. **The monitors are drawn against a rule, and it must be the process's rule.**
   A critical-dimension monitor draws the narrowest feature it is told to draw.
   Where the design's own minimum is looser than the process minimum, the rung
   intended to measure the process is itself unmanufacturable. Check the monitor
   dimensions against the foundry deck and not against the declared rules.

27. **A documentation layer drawn on a process layer is drawn geometry.** Marks,
   composites and viewing aids are convenient and are not levels. Where such a
   layer maps to one the process reads, it becomes real: on one baseline a
   composite overlay mark reproduced the etch-level figure a few micrometres from
   a marker layer the process requires to stand fifteen micrometres clear of it.
   Suppress the aid, or place it on a number no rule reads.

28. **A drawing keyed to layer numbers misreports silently when the map
   changes.** A plan-view renderer holding its own table of numbers went on
   painting the waveguide in the slab's colour and omitting the metal entirely
   after a remap, and said so in neither its legend nor its caption. Drive every
   drawing from the run's own layer map.

29. **Run every stage. An absent stage is not a passing stage.** A verdict
   reports on the targets it was given, a target may only name a metric some
   stage produced, and a stage that never ran produces nothing. A design missing
   its taper, mode-solver cross-check, band-structure, bend and facet stages
   returns a full pass with none of its five cross-checks performed, and the
   verdict discloses none of that. On one baseline that condition persisted for
   the whole of development, the five absentees having each been run once as a
   probe against a configuration since superseded. **Declare every stage the
   chain offers.** Where one must be omitted, omit it explicitly and state the
   reason, so that the omission is a decision rather than an oversight wearing
   the appearance of a result. Report the stage coverage wherever the verdict is
   reported.

30. **Cost is a reason to run less often, not a reason to check less.** The
   expensive stages are expensive because they are independent of the cheap ones,
   which is precisely what makes them worth running. A cross-check skipped for
   its runtime is a cross-check that was never performed.

31. **Pick the tier before running.** Stage costs on one baseline span three
   orders of magnitude, and a single external solve is 98 % of a full run.
   Iterate on the four stages that produce the metric being changed; run the
   whole flow short of the external solver at a decision point; run everything
   once per frozen configuration. Choosing the tier is a design decision and is
   to be made rather than defaulted.

32. **A sweep multiplies what it is given.** A stage list correct for one run is
   wrong for nine. Derive a sweep's stages from the metrics it declares, and
   report what was skipped. A comprehensive stage list turned a nine-corner
   sweep into a thirty-one hour job, and nothing reported it because per-stage
   cost was not recorded.

33. **Never repeat an identical external solve.** Content-hash the job with
   floats rounded well below the noise and above physical significance, reuse a
   matching prior result, and record which run it came from. Two evaluations of
   the same geometry differ in the last bits, so a raw hash never matches.

34. **Ask what a run could possibly show before starting it.** A parameter that
   does not enter a solver's inputs cannot change its output. Establishing that
   is arithmetic and takes a second; the run it displaces may take hours. A run
   that cannot change a conclusion is delay and not evidence.

35. **Slow is not stuck, and unfinished is not failed.** Establish the expected
   cost and the elapsed time before concluding anything about a job's health.
   Record wall clock and processor time separately, since the first counts
   machine suspend and the second does not, and prefer an external solver's own
   reported time to either. Every misdiagnosis of this chain's health has come
   from treating absence of a finish as evidence of failure.

## Prohibitions

* A target is never edited to make a run pass. Where a target is wrong, that is a
  finding to be stated and sourced.
* Nothing under `runs/` is hand-edited. It is generated and stamped with the
  resolved inputs.
* A material provenance tag is never cleared without a source.
* Project-proprietary data never enters `design-chain/pdk/`. It belongs in the
  project `pdk/`, referenced through `platform.materials_file`.

## Diagnosing a Failed Run

| symptom | first thing to check |
|---|---|
| n_eff implausibly high | is a high-index substrate inside the optical window |
| many guided modes reported | is the mode count referenced to the slab index, not the cladding |
| a stage raises on geometry | window bounds against feature extents; blanket layers must exceed the window |
| a quantity off by a round power of ten | dimensional analysis of the expression; unit factors that already cancel |
| bandwidth below the transform limit | n_g, and the span of the spectrum grid |
| DRC violations proportional to a periodic count | a per-period feature against a clearance rule; inspect the marker GDS |
| two solvers disagree on a cross-section | the boundary condition of each, before the physics. A curl-curl formulation defaults to a magnetic wall, which is incompatible with a layer reaching the window edge |
| a cross-check reports a disagreement | `fem.convergence.resolved` or `fdtd.convergence.resolved`, and whether either solve is converged at all. An unconverged comparison is to be reported as unresolved, not as a finding |
| a band gap disagrees with coupled-mode theory | the mesh, before the physics. A gap that is 10⁻⁵ of the band frequency is two nearly degenerate eigenvalues, and the discretisation error on each can exceed their difference |
| a check reports "not performed" | whether the backend is absent or was silently lost. A process-wide cell library refuses a repeated name, so a second emission in one process can disable a backend and skip a comparison rather than fail it |
| a geometric figure looks wrong by a large factor | `layout.mask_is_complete` first. Where a period count has been set, every count and length scales with the fraction drawn |
| the die fails a rule the device passes | the frame and the monitors, which are subject to the same deck. An overlay mark drawn identically on two levels is a short; the levels must nest |

## Adding a Stage

Write `src/picchain/stages/sNN_<name>.py` exposing `run(design, ctx, lib) -> dict`;
read upstream results through `ctx.get(...)` and upstream arrays from
`ctx.run_dir`; write through `ctx.put(...)` and `ctx.write_stage(...)`; register
in `stages/__init__.py`; and add a **closed-form** test. A test that pins the
previous numerical output pins the previous defect with equal fidelity.
