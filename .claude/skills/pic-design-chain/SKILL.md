---
name: pic-design-chain
description: Operate the picchain PIC design chain - run a design, read the metric tree, iterate against acceptance targets, add a stage, or diagnose a failed run. Use whenever a design.yaml is being created or modified, whenever picchain output is being interpreted, or whenever a photonic component must be taken from cross-section to DRC-clean mask.
---

# Operating the PIC Design Chain

The authoritative reference is `design-chain/PICCHAIN_REFERENCE.md`, which is
published. `design-chain/CLAUDE.md` carries the agent directives that sit on top
of it. Read both before acting.
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
11. **A clean DRC means the rules supplied were met, on the geometry the deck
   could actually read.** The declared `rules` are a smoke test; `drc.deck` runs
   a foundry runset through the KLayout application. Three things are to be
   established before a clean report is believed, and the first two are cheap.

   **That the deck is this process.** A runset encodes a stack. Two runsets from
   one foundry differ in their layer datatypes and in nothing a reader notices.
   A tantalate design was released with zero violations from the niobate deck,
   ten of ten release conditions and a signed manifest.

       layer     LN-CORE     LT-PRO
       RIDGE     2 / 0       2 / 10
       SLAB      3 / 0       3 / 10
       M1        21 / 0      20 / 0

   **That every layer the deck names carries geometry.** Read
   `drc.deck.layers_named_and_empty`. A rule on an empty layer cannot fail, so a
   clean report over absent layers says nothing. Correcting the deck without
   correcting `layout.layer_map` is worse than either error alone: the metal
   moves from 21/0 to 20/0 between these two stacks, so the right deck on the
   old map finds no metal and passes every metal rule in silence.

   **That it detects a violation deliberately introduced.** Where a check can be
   made to fail on demand, make it fail once.

   `drc.checked` and `mask.checked` state whether the device cell or the
   assembled die carried the verdict.
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
16. **The tuning range is three inequalities, and the swept figure is none of
   them.** Write the requirement against the algebra below, and never against
   `cavity.mode_hop_free_range_GHz`.

   The cavity is a gain chip, a passive feed and a distributed mirror:

       tau_u  = tau_soa + tau_feed          the delay the voltage does not reach
       tau_rt = tau_u + tau_dbr             tau_dbr = 2 n_g L_pen / c
       r      = tau_dbr / tau_rt            the Pockels lever
       FSR    = 1 / tau_rt
       S      = mirror tuning, MHz/V        eta = r * S = laser tuning, MHz/V

   The mirror moves at `S` and the laser follows at `eta`, so **the mode slips
   relative to the mirror at `(1-r)*S`.** Everything follows from that slip:

       drift       = (1-r) * S * V_max      mode excursion relative to the mirror
       hops        = drift / FSR            mode boundaries the sweep crosses
       guaranteed  = eta * V_max / (ceil(hops) + 1)
       placed      = eta * V_max
       containment = drift / FWHM

   **The three conditions a design must meet**, for a required excursion `dF`:

       guaranteed  >= dF        the worst cavity phase still delivers it
       containment <= 1         the mode stays inside the mirror it follows
       hops        <  1         at most one hop, so a placed comb clears the sweep

   **Where the hop falls is cavity phase, and no process controls it.** The
   phase is the round-trip path modulo one wavelength. On a 17 mm tantalate
   cavity, moving the feed by 200 nm moved the hop from 51.6 V to 9.6 V with the
   stop band unchanged at 7.492 GHz. The swept figure is one sample of that
   phase. A corner sweep of it reports phase scatter: the same design read 125.5
   % spread on the swept figure and 9 of 9 corners on the guaranteed one.

   `guaranteed` is what the device delivers before commissioning. `placed` is
   what it delivers after the comb is set thermally, and the ratio between them
   is `ceil(hops)+1`. Both are worth quoting; only `guaranteed` belongs in a
   `must` row.

   **Which knob moves which condition.** The lever and the stop band oppose each
   other, so a change is to be evaluated on all three:

   | change | r | FWHM | guaranteed | containment |
   |---|---|---|---|---|
   | weaken kappa (open the gap) | up | down | mixed | **worse** |
   | shorten the grating at fixed kappa | down | up | down | better |
   | lengthen the feed | down | unchanged | down | worse |
   | raise the drive `V_max` | — | — | up | **worse** |

   Weakening the grating lowers the drift through `(1-r)` and narrows the stop
   band, and the narrowing wins. Measured on a third-order tantalate mirror at
   55 V, containment went 0.916, 0.996 and 1.022 at post gaps of 0.900, 0.970
   and 1.010 um. **Raising the drive buys tuning range and spends containment
   linearly, so the two are set together.**

   The closed form `r/(1-r)*FSR/2` is the average over phase of the swept
   figure. It is `placed/2` when `hops < 1`, carries the same phase assumption
   averaged away, and states nothing about containment. Retain it at `info`.

17. **A one-factor corner pass is not a process-window pass, and no linear
   shortcut substitutes for the factorial.** Run `--mode factorial` when a
   `must` row is to be established across the window.

   The tempting arithmetic is to linearise. With parameters `p_i` and declared
   excursions `dp_i`, each contributing `d_i = (dM/dp_i)*dp_i`:

       onefactor worst = max_i |d_i|
       linear estimate = sum_i |d_i|          <- NOT a bound
       RSS             = sqrt(sum_i d_i^2)

   **Both linear figures were measured against a real factorial and both
   failed.** On a tantalate laser, for the placed tuning excursion:

   | | GHz | verdict against 8 GHz |
   |---|---:|---|
   | nominal | 11.32 | pass |
   | one-factor worst of 8 | 10.10 | pass |
   | linear estimate `sum |d_i|` | 9.20 | pass |
   | **true factorial worst of 81** | **6.45** | **fail** |

   The linear estimate was 30 % optimistic and would have passed a design that
   the window fails. The interactions were adverse, and superposition cannot see
   them.

   **The single adverse run is not a substitute either.** Taking each
   parameter's unfavourable sign from the one-factor sweep and setting all of
   them at once looks like a one-run answer. On a niobate laser whose four
   parameters were each individually unfavourable by 0.10 to 1.25 GHz, the
   combination returned 15.03 GHz against a nominal of 14.74. **The combination
   was better than nominal**, the individual effects having cancelled rather
   than added.

   So the sign of the interaction is not predictable from one-factor data in
   either direction. **A window is established by the factorial or it is not
   established.** Where the factorial is too costly, say so and quote the
   one-factor result as what it is.

   Cost, measured: 3^4 = 81 combinations at four stages each. On a design whose
   mode solve takes 140 s that is about four hours; on one taking 20 s, forty
   minutes. Reduce the stage list before reducing the corner count.

18. **`corners.metrics` is a filter, and a target absent from it is never
   judged.** The corner verdict iterates the metrics named in
   `corners.metrics` and looks each up among the targets. A `must` row that is
   not named there passes every corner silently, because it is never evaluated.

   This produced a false result. Two new `must` rows were added to a design and
   not added to `corners.metrics`, and the sweep reported 9 of 9 while the
   failing row was simply unread. Adding them returned 4 of 9. **After adding or
   re-severing any target, add it to `corners.metrics` in the same edit**, and
   confirm the corner report lists a spread row for every `must`.

18a. **A corner parameter is a quantity the process varies, and not the drawn
   dimension that quantity happens to reach.** Features on one layer are
   printed by one exposure and one etch, so a lithographic excursion moves their
   widths and the gaps between them together. Declaring one of those dimensions
   alone describes a displacement the process cannot deliver.

   `process.bias_um.<layer>` is the field that expresses the real excursion: a
   width grows by the full bias and a same-layer gap shrinks by the same amount.
   **Take the excursion with `precompensate` off**, so that it represents the
   residual the process leaves rather than the displacement the mask was drawn
   to absorb; at zero bias all three geometry frames still coincide.

   Measured on one third-order side-coupled grating, each parameter displaced by
   +-20 nm with everything else nominal:

       post gap alone      kappa 1.0477 .. 0.8480 /cm    span -21.2 %
       process bias        kappa 0.9092 .. 0.9558 /cm    span  +4.9 %

   **The gap-only excursion overstated the sensitivity by a factor of four and
   reversed its sign.** Correcting it changed three results on one design: it
   exposed a `must` row that had never failed, the guided-mode count reaching two
   at positive bias with a deep etch, which no gap excursion could reach because
   it moves no dimension of the guide; it withdrew nine `should` failures on the
   linewidth; and it narrowed a quoted kappa spread from 63.6 % to 46.4 %.

   **A metric flat across a window is insensitive, or is unreachable by that
   window.** Name the declared excursion that moves it before reporting it as
   stable.

18b. **Declare `corners.mode` in the design file.** A sweep run at a mode the
   file does not declare cannot be reproduced from the file. One design's every
   process-window claim rested on an 81-corner factorial while its file read
   `onefactor`, so re-running from the design returned nine corners and the
   reproduction section gave no override. The chain now warns where the two
   differ.

18c. **Where every corner failure sits at one level of one parameter, the
   finding is about the window and not the design.** Establish the tolerance the
   design actually requires: walk that parameter at the adverse combination
   until each bound is crossed, and compare the result against what the process
   states. On one design all ten failures sat at the positive etch excursion, and
   walking it showed the tuning crossing its floor at about +6 nm and the
   guided-mode count at about +5 nm, against a declared window of +-10 nm that
   cited no source. **An unsourced window that alone determines a verdict is the
   finding.**

19. **Exclude from corner judgement any metric whose spread is dominated by a
   quantity the process does not control.** A corner sweep moves geometry, and
   geometry moves cavity phase, so a phase-dependent metric returns scatter that
   reads as sensitivity. The swept mode-hop-free range spread 125.5 % across a
   window on which the phase-independent quantities spread 14 %. Judge the
   design on the latter and carry the former at `info`.

   The test for whether a metric is phase-dominated costs two runs: perturb an
   optical path by a fraction of a wavelength, leaving every other quantity
   fixed, and see whether the metric moves. A 200 nm change of feed length moved
   the hop voltage from 51.6 V to 9.6 V and left the stop band at 7.492 GHz.

20. **Reach for `search` before hand-iterating, and read its phase 3 first.**
   The reachability pass evaluates every declared parameter at both bounds
   before any solving, so a requirement no parameter can reach is reported in a
   few runs rather than discovered after an afternoon of bisection. Phase 2 is
   the elasticity matrix, which answers "which knob moves which target" in one
   run per parameter, and is worth reading even when the design already passes.

21. **Sensitivity is two tables, and risk needs a third thing.** Elasticity
   ranks the knobs and is physics; contribution over the declared excursion ranks
   the process; neither is risk until both are set against the margin the target
   leaves. A metric of elasticity −14 sitting three decades below its bound is
   not a risk, and a metric of elasticity 1 sitting on its bound is.
22. **An elasticity on a non-monotone metric is meaningless.** It will differ by
   an order of magnitude with the width of the probe. Check the reachability
   monotonicity flag before quoting any derivative of the tuning range.
23. **Read the per-corner failures, not only the spread.** A corner summary
   aggregates. The useful question is which target failed at which excursion,
   and on the validation baseline that is what revealed the single-mode
   condition failing at three of eight.

24. **Keep the run register.** The design report must carry a table of what was
   run, when, with which parameters, how many evaluations it cost, and what it
   established. Superseded studies stay in it, marked superseded; discarded ones
   say why they were discarded. A conclusion without its register is an
   assertion.

25. **Replace the layer numbers before running a foundry deck, and check the
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

26. **A runset checks a chip, not a device cell.** Footprint, centring and
   exclusion-ring rules are evaluated against an outer boundary and a usable-area
   rectangle, and neither exists until the die assembly draws it. A deck run
   against a device cell reports nothing on those rules. **Silence there is not a
   pass**, and it is to be recorded as not exercised. Where a device-level floor
   plan is mapped onto the usable-area layer to obtain a device-level check, that
   mapping becomes wrong at die level, a die spreading content far outside any
   single device's bounding box.

27. **A runset written for the graphical application names no input and no report
   file.** It expects a layout already open and a marker browser. Executed
   headless it stops at its first layer read with no source. Supply the input and
   the report file, alter nothing else, and record what was supplied. The rules
   evaluated must remain the foundry's own.

28. **Die footprints are quantised, and a size between them is refused.** A
   process offers a fixed set of die dimensions. Record that set in the design
   and check against it, rather than discovering it at submission. **Confirm that
   the die emitted is the die declared**: on one baseline the usable area was
   computed by deducting the margin, the seal width and the dicing lane but not
   the seal-ring clearance, which the ring then added back, so a declared
   footprint was written 120 um larger in each dimension. Nothing reported it,
   there being no boundary drawn against which a footprint could be checked.

29. **The monitors are drawn against a rule, and it must be the process's rule.**
   A critical-dimension monitor draws the narrowest feature it is told to draw.
   Where the design's own minimum is looser than the process minimum, the rung
   intended to measure the process is itself unmanufacturable. Check the monitor
   dimensions against the foundry deck and not against the declared rules.

30. **A documentation layer drawn on a process layer is drawn geometry.** Marks,
   composites and viewing aids are convenient and are not levels. Where such a
   layer maps to one the process reads, it becomes real: on one baseline a
   composite overlay mark reproduced the etch-level figure a few micrometres from
   a marker layer the process requires to stand fifteen micrometres clear of it.
   Suppress the aid, or place it on a number no rule reads.

31. **A drawing keyed to layer numbers misreports silently when the map
   changes.** A plan-view renderer holding its own table of numbers went on
   painting the waveguide in the slab's colour and omitting the metal entirely
   after a remap, and said so in neither its legend nor its caption. Drive every
   drawing from the run's own layer map.

32. **Run every stage. An absent stage is not a passing stage.** A verdict
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

33. **Cost is a reason to run less often, not a reason to check less.** The
   expensive stages are expensive because they are independent of the cheap ones,
   which is precisely what makes them worth running. A cross-check skipped for
   its runtime is a cross-check that was never performed.

34. **Pick the tier before running.** Stage costs on one baseline span three
   orders of magnitude, and a single external solve is 98 % of a full run.
   Iterate on the four stages that produce the metric being changed; run the
   whole flow short of the external solver at a decision point; run everything
   once per frozen configuration. Choosing the tier is a design decision and is
   to be made rather than defaulted.

35. **A sweep multiplies what it is given.** A stage list correct for one run is
   wrong for nine. Derive a sweep's stages from the metrics it declares, and
   report what was skipped. A comprehensive stage list turned a nine-corner
   sweep into a thirty-one hour job, and nothing reported it because per-stage
   cost was not recorded.

36. **Never repeat an identical external solve.** Content-hash the job with
   floats rounded well below the noise and above physical significance, reuse a
   matching prior result, and record which run it came from. Two evaluations of
   the same geometry differ in the last bits, so a raw hash never matches.

37. **Ask what a run could possibly show before starting it.** A parameter that
   does not enter a solver's inputs cannot change its output. Establishing that
   is arithmetic and takes a second; the run it displaces may take hours. A run
   that cannot change a conclusion is delay and not evidence.

38. **Slow is not stuck, and unfinished is not failed.** Establish the expected
   cost and the elapsed time before concluding anything about a job's health.
   Record wall clock and processor time separately, since the first counts
   machine suspend and the second does not, and prefer an external solver's own
   reported time to either. Every misdiagnosis of this chain's health has come
   from treating absence of a finish as evidence of failure.

39. **Audit the documents against the artifacts; do not reread them.** Invoke
   the `doc-auditor` sub-agent after any change to a design, a stage or a test,
   and before any document is shown or published. Trace every number to a run,
   take every count from the source rather than from another document, resolve
   every cross-reference, open every figure, and measure the structure. Rereading
   finds prose errors; only checking against the artifact finds a document that
   has quietly ceased to be true.

40. **A stage that ran and is reported nowhere is the omission that hides
   itself.** Nothing in a document reveals what it fails to mention. List every
   stage that produced a result, including those that found nothing, so that an
   absent finding is distinguishable from an unasked question.

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

41. **A corner sweep moves the level of a parameter and never its gradient,
   and for a long device the gradient is the failure.** The chain holds film
   thickness, etch depth and sidewall angle as scalars: a cross-section times a
   length. A sweep of such a parameter shifts every derived quantity uniformly
   and leaves the device internally consistent, so it cannot represent the
   failure where the parameter varies along the device.

   Measured on a 17 mm third-order mirror: the Bragg condition follows n_eff at
   1.38e-3 per nm of film, so the whole 6.4 GHz stop band is a twentieth of a
   nanometre of thickness, and pi of Bragg phase over the 4.89 mm penetration
   depth is **0.117 nm of film non-uniformity, 0.039 % of a 300 nm film**.
   Films are specified at one to two per cent. Eighty-one factorial corners on
   film thickness reported comfort throughout, because a uniform shift keeps
   the grating perfectly coherent and merely moves its wavelength.

   The instruments for it: `mesh.film_sensitivity: true` adds one mode solve
   and yields `dn_eff_d_film_per_um`; the `grating` stage turns it into
   `film_uniformity_for_pi_phase_nm` over the penetration depth, compares it
   against `platform.film_nonuniformity_nm`, and states when coherence is
   assumed rather than established. The budget scales inversely with the
   penetration depth, which is how mirror length is priced honestly.

   **A stepped-parameter ladder cannot measure this** - every copy sits on the
   same film. The monitor is a stepped-LENGTH grating set at the design's own
   gap (`reticle.monitors.coherence_ladder`): coupled-mode theory says its
   reflectivity follows tanh^2(kappa L), and a mirror losing phase departs
   from that curve and broadens instead of narrowing.

42. **Name the loss channels the model discards, and state the margin
   against them.** Coupled-mode theory keeps the backward Bragg order. On a
   grating of order m, every order below m radiates into the cladding and the
   substrate, and that loss is in no reported figure. Where no solver for a
   channel is available, the honest output is a budget, not silence: the
   `grating` stage reports `radiation_orders_unmodelled` and points at the room
   under the threshold-gain ceiling as the loss the design survives. A gap
   framed as "kappa is uncertain" hides a channel with no model at all;
   uncertainty on a computed number and absence of a model are different
   findings.

43. **An intracavity phase section is sized from the passive delay, and it
   must cancel the slip it creates.** The mirror and the mode comb are set by
   different things, so tuning the mirror makes the mode slip across the comb at
   `(1-r)*S` until it hands over. A phase electrode over passive guide moves the
   comb without moving the mirror, so the two go together and the hop is removed
   rather than placed.

   The phase it must supply is

       phi_needed = 2*pi * drift / FSR = 2*pi * tau_u * S * V_mirror

   because `(1-r)*tau_rt = tau_u` exactly. **The grating cancels.** Measured
   across four post gaps spanning reflectivity 0.93 to 0.80 and stop bands 10.05
   to 6.84 GHz, `phi_needed` held at 2.455 rad throughout. A section is
   therefore sized once, from the passive delay and the mirror drive, and any
   mirror may be chosen behind it. **Size it before choosing the grating.**

   **It is itself passive delay, so it enters `tau_u` and raises its own
   requirement.** Omitting that declares an insufficient section sufficient: a
   1500 um section was accepted against 2.455 rad when its own 20.6 ps of delay
   took the requirement to 4.025 rad. Solving self-consistently,

       L = tau_0 * S * V_m / (2*dn_per_V*V_p/lambda - 2*n_g*S*V_m/c)

   which diverges as the denominator closes. At a phase drive equal to the
   mirror's, that gave 3583 um and did not fit the die.

   **Give the phase electrode its own drive, above the mirror's.** It raises
   what the section supplies without raising what it must supply, and it is the
   only lever that breaks the circularity. 900 um at 55 V against a 25 V mirror
   drive left 15 % margin where 25 V needed four times the length.

   **Its gap is not the mirror's.** A phase section carries no Bragg posts, so
   the electrodes are bounded only by the metal-to-ridge rule: 4.0 um against a
   mirror's 6.62 um on one platform, and the field goes as 1/gap, so the section
   shortens in proportion. That ratio is what makes it fit.

   **Check what it displaces.** Passive delay added here does the job a long
   feed was doing, so a feed lengthened for linewidth becomes redundant and is
   costing Pockels lever for nothing. Returning it recovered the lever from
   0.547 to 0.631 and left the linewidth better than before.

44. **A metric written for one architecture will condemn the architecture that
   replaces it.** The quantity that graded the old design describes a mechanism
   the new design removed, so the new design scores badly on it while being
   better at the thing both were built for.

   The case: an extended-DBR laser tuned by its mirror alone follows the mirror
   at `r*S`, the comb slipping at `(1-r)*S` until it hops. Adding an
   intracavity phase section driven in step supplies that slip, so the comb is
   carried with the mirror and the laser follows at the full `S` with no hop at
   all. Differentiating the resonance condition gives it directly:

       df/dV = r*S - (dphi_ps/dV) / (2*pi*tau_rt)

   which reaches `S` exactly when `dphi_ps/dV = -2*pi*tau_u*S`, and that is the
   slip the section is already sized to cancel. **The sizing rule and the
   one-for-one tracking are the same statement**, so a correctly sized section
   tunes at the mirror rate by construction.

   The phase section is also passive delay, so it lowers `r` and lowers the
   mirror-only excursion. Graded on that excursion the phase-section design lost
   on every count: 8.41 GHz against 11.22, and 17 of 81 corners failing where
   the design without a section failed none. Graded on what it delivers it wins
   outright: 12.11 GHz continuous and no hop, against 5.61 GHz guaranteed and
   one hop to hand over.

   **Before grading a new architecture, ask which mechanism each target
   assumes.** Where a target encodes a mechanism the design has replaced, say
   so, move the requirement to the row that measures the new mechanism, and keep
   the old row at a lower severity so the degraded mode stays on the record.
   Here `placed` remains as `should`, being what the device delivers if the
   phase drive is lost.

45. **Where a correction and a model can be made to meet, make them meet, and
   report the residual.** The synchronous rate was available two ways: from the
   algebra above, and by adding the section's phase to the round trip and
   re-tracking the lasing mode numerically. They agree at 484.20 against
   484.19 MHz/V. That agreement is worth more than either number, because the
   two routes share no step: one differentiates a resonance condition in closed
   form, the other finds roots of a non-monotonic phase on a grid. **Compute the
   claimed quantity by the machinery that produces every neighbouring quantity,
   not by a formula quoted beside it.** A closed form printed next to a
   numerical model is a claim about the model and not a result from it.

46. **Write the concept of operation before the targets, and validate against
   it.** A design states what the device does, by what principle, and which
   physical quantity expresses each clause of that principle. The acceptance
   targets are then derived from those clauses rather than assembled from
   whatever the previous design measured.

   **The failure this prevents is silent.** A target encodes a mechanism as well
   as a number, so a design that replaces the mechanism keeps passing a test that
   has stopped asking the right question. There is no symptom: the run completes,
   the metric is computed, the corner sweep reports a number. Only a reader
   holding the concept can see it.

   The case: a laser built to hold its mode comb in step with its mirror
   inherited the targets of a laser built to position the mode hop outside the
   sweep. The `must` row measured a comb left to slip, which is the mechanism the
   new element removes. The device therefore scored worse than the one it
   replaced on the quantity it exists to improve, 8.41 GHz against 11.22, with 17
   of 81 corners failing. Re-derived from its own concept it gives 12.11 GHz
   continuous against 5.61 guaranteed, and every corner clears.

   **Bind the two documents mechanically.** A trace table in the concept, one row
   per clause naming the metric that tests it, checked against the declared
   targets by a tool. Prose cross-references between two documents drift, and the
   drift is invisible precisely because each document remains internally
   consistent.

   Three questions to ask of a target set, in this order. **Which clause of the
   concept does this row test?** A row that answers nothing is either unnecessary
   or the concept is incomplete. **Which clause has no row?** That is an
   untested promise. **Which row assumes a mechanism this design does not use?**
   That is the inherited target, and it will invert the verdict.

   Where the old row still describes a real degraded mode, keep it at a lower
   severity rather than deleting it. On the laser above, the mirror-only
   excursion is what the device delivers if the phase drive is lost, so it stays
   as a `should` and the degradation is on the record.

47. **A figure is an artifact of a run, and must be checked against the run like
   a number.** A design's published `figures/` directory is a copy of what the
   run wrote, and a copy rots. Two designs were re-run to a new operating point;
   every number in their documents was corrected and every figure was left three
   days stale, so a review deck showed the electro-optic field across an
   electrode gap that had since been narrowed and a tuning curve labelled with a
   retired drive voltage.

   **Rereading cannot find this.** A number carries units and traces to a run. A
   figure carries neither, so a stale one looks exactly like a current one, and
   it is the artifact a reviewer trusts most. Opening the figure shows what it
   depicts, not which revision it depicts.

   **Compare by hash and list what nothing regenerates.** Each published figure
   is set against the one the run of record wrote. Separately, name the figures
   no stage produces, since those are refreshed by nothing at all, and record the
   command that regenerates each of them beside them. Two figures in this case
   had been captured by hand from a layout viewer and could not be reproduced.

   **Draw from the model's arrays, not from its reported numbers.** A tuning
   curve redrawn from the stage's stored mode track is a measurement; the same
   curve drawn from a reported slope is a restatement of a number. Where a figure
   needs a quantity the stage does not store, add it to the stage's arrays rather
   than reconstructing it in the plotting tool.

48. **Ask a process table for identity and elapsed time, never for load.** An
   external parallel solver was checked with a processor-sorted `ps`, listed
   nothing, and was nearly reported dead. Eight ranks were in a synchronisation
   barrier at that instant and the job had hours of its timeout remaining.

   A parallel job is idle at every barrier, so an instantaneous view of processor
   use samples a duty cycle and not a state. Match the command line and read the
   elapsed time; both answer the question and neither depends on the sampling
   moment. Where the solver runs in another environment, query inside that
   environment, since the ranks may be invisible to the host process list
   entirely.

49. **Check the design before you spend the compute, and treat every clamp as a
   precondition that was written as a rescue.** A contradiction among declared
   fields is knowable from the file in milliseconds. Running it first costs the
   full chain and returns numbers that describe a different device.

   The case: a circuit stage subtracted twice a taper length against one taper in
   its netlist. On a long feed the error was invisible; on a short one the length
   went negative, a `max(..., 1.0)` returned 1 um, and the stage assembled a
   cavity with no feed. **Its own cross-check then passed**, the expectation
   being computed from the same clamped value, while the sibling design with the
   smaller defect disagreed by 11 % and looked worse.

   **Audit the fallbacks.** Search for `max(`, `min(`, `or <default>` and every
   silent repair applied to a value that came from the design file. For each, ask
   what input makes it fire and whether that input should reach a solver at all.
   A clamp exists because someone knew the value could be impossible.

   **Split the checks by what establishes them.** A relation among declared
   fields belongs in a precondition. A relation needing a computed quantity
   belongs in the stage that computes it, raising there — reconstructing the
   arithmetic in a precondition is a second implementation and it will diverge.
   On this chain the lead-in path is 203.2 um against a 150 um taper, so the
   precondition that used the taper passed a design that was violating the
   condition.

   **Never assert a precondition from an assumption about the design.** The first
   version of this gate failed a correct device by supposing a phase section sat
   inside the feed, when the layout draws it after. A gate that fails correct work
   teaches the reader to bypass it, and a gate that passes incorrect work is worse
   than absent because it is believed. Read the code that establishes the relation
   and name it in the check.

50. **The acceptance verdict is not a summary of the run.** It grades targets,
   and a chain also emits findings that carry no threshold. On this one, ninety
   warning sites across seventeen stages were read by nothing at all, so a design
   could emit seventeen findings and be reported a clean pass.

   Three kinds of statement exist about a design and each needs its own gate: a
   quantity with a bound is a target; a finding with no bound must be
   **acknowledged by name in the design file, with the reason**; a channel not
   modelled at all is a declared limitation gated indirectly by a budget.

   **Report the denominator, never a bare verdict.** "75 of 81 corners, 17
   findings of which 0 acknowledged, 3 stages unreported" is a true summary.
   "PASS" was not, and a green wall of individually-true checks is how a false
   summary gets assembled.
