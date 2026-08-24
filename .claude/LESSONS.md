# Lessons Ledger

Accumulated design knowledge, held in sanitised form. This file and the skills
in `.claude/skills/` constitute the mechanism by which the generator is intended
to improve across successive design scopes.

**This file sits outside `projects/` and is therefore covered by
`tools/check_ip_boundary.py`. Every entry must survive that check.**

---

## The Sanitisation Rule

A lesson is admissible only where it remains true and useful with the originating
scope entirely removed.

**Admissible:** physics, numerical method, solver behaviour, sensitivity
relationships, failure modes, invariants that ought to be checked, defects found
in the toolchain, and the correspondence between a control and the quantity it
moves.

**Not admissible:** the client, the programme, the application, the operating
band, deliverable or work-package codes, the specific parameter set of any
delivered design, target values drawn from a client requirement, foundry data
received under non-disclosure, and schedule or commercial information.

Where a lesson can only be stated by reference to a specific design, it is not
yet a lesson. Generalise it or leave it in the project.

### Test to Apply Before Writing an Entry

1. Would the entry read identically had it been derived from a different scope?
2. Does it name a client, a programme, an application, or a deliverable code?
3. Does it quote a numerical target that originated in a client requirement
   rather than in physics?
4. Does it reproduce a parameter set that identifies a delivered design?

An entry is admissible where the answers are yes, no, no, no.

### Procedure

At the close of a design activity:

1. Invoke the `lesson-harvester` sub-agent against the project run artifacts.
2. Review each proposed entry against the four questions above.
3. Append accepted entries below, or fold them into the relevant skill in
   `.claude/skills/` where they are procedural rather than observational.
4. **Place the operative instruction in a tier.** Where an entry carries an
   instruction general enough to be read before every design activity, it also
   earns a rule in [`../rules/`](../rules/). Take the narrowest tier that
   remains true: `generic/` for what holds on any platform with any tool,
   `platform/<stack>/` for what holds on one film stack, `tool/<tool>/` for what
   holds of one solver or engine. Amend an existing rule rather than adding a
   near-duplicate. [`../rules/README.md`](../rules/README.md) states the
   discipline in full.
5. Execute `python tools/check_ip_boundary.py`.
6. Where a skill has been changed, add or amend the corresponding closed-form
   test in `design-chain/tests/` so that the lesson is enforced and not merely
   recorded.

### The Ledger and the Rules Are Different Objects

**This file is the evidence and it is held in full.** Each entry carries the
case that produced it, the measurement that supports it, and the confidence it
was recorded at. Entries are never deleted.

**A rule is the operative instruction distilled from one or more entries**, kept
short enough to be resident while work is done. A rule that cannot cite the
entries behind it is an opinion, and an entry whose instruction is already
covered by a rule stays here alone.

Entries are numbered and dated. They are not deleted; a superseded entry is
marked as such, since the record of a corrected belief is itself informative.

---

## Entries

### L001 — The tuning lever of an externally tuned cavity is a layout ratio
*Recorded 2026-08. Class: physics. Confidence: high, derived analytically and confirmed numerically.*

In a hybrid laser whose wavelength-selective mirror is tuned electro-optically,
only the fraction of the round-trip delay residing **inside the tuned element**
follows the tuning. Defining

> r = τ_mirror / (τ_mirror + τ_gain + τ_feed)

the laser tunes at r × the mirror tuning rate, and a mode hop occurs once the
mirror has slipped half a cavity free spectral range relative to the mode comb,
giving a continuous excursion of r/(1−r) × FSR/2.

Consequence: continuous tuning range is fixed at layout time by the ratio of the
distributed mirror's group delay to everything else in the cavity. It is not a
property of the mirror alone. Raising r requires a short gain chip, a short
passive feed, and a long weakly-coupled grating.

Counter-pressure to record alongside it: lengthening the grating lowers the
cavity FSR, which brings the nearest side mode closer to the mirror peak and
costs side-mode suppression. Continuous tuning range and side-mode suppression
are opposed through the grating length. Apodisation is the second control.

Enforced by: `cavity.pockels_lever` is reported by the `cavity` stage.

### L002 — Evanescently coupled grating perturbations are exponentially sensitive to gap
*Recorded 2026-08. Class: manufacturability. Confidence: high, measured by parameter sweep.*

Where a grating is formed by elements placed **beside** a waveguide rather than
patterned into it, the index perturbation decays exponentially with the
separation, at the transverse decay constant of the guided mode. A measured
value on a shallow-etched thin-film cross-section was
d(ln Δn_eff)/d(gap) ≈ −5.55 µm⁻¹, a decay length of approximately 180 nm. It was
measured as −5.4 µm⁻¹ on the same cross-section drawn with vertical walls, so the
sidewall angle moves the sensitivity as well as the value.

Consequence: **a ±20 nm lithographic error is a ±12 % error in κ**, and κ sets
reflectivity, mirror bandwidth, penetration depth and hence the tuning range.
Any such design must either be centred where ∂(performance)/∂κ is flat, or carry
a trim mechanism. Monitor structures with stepped gaps should be placed on the
first reticle so that the process is measured and not merely assumed.

Corollary: where a model and a measurement disagree on κ, the gap is the first
quantity to suspect, though it will not always be the whole answer. A factor of
2.15 was traced to approximately 130 nm of separation on one comparison, which is
at the upper end of the combined error of stepper critical-dimension control,
etch bias, and the definition of a nominal gap on a sloped wall. Where the
implied displacement exceeds what the process plausibly delivers, the model is
carrying part of the discrepancy and the split is to be established by a second
instrument.

### L003 — Sloped sidewalls increase side-coupled grating strength
*Recorded 2026-08. Class: physics. Confidence: medium, one parameter sweep on one cross-section.*

Sloping the sidewalls of a ridge and its adjacent grating elements was found to
**increase** Δn_eff, because a trapezoidal element presents a wider base
positioned closer to the ridge. The intuition that a sloped wall weakens the
perturbation, by removing material, is incorrect for side-coupled geometries.

Measured on one shallow-etched thin-film cross-section, against the same
structure drawn with vertical walls:

| wall angle from horizontal | Δn_eff, relative | λ_B shift |
|---:|---:|---:|
| 90° | 1.00 | — |
| 85° | 1.12 | +1.7 nm |
| 80° | 1.26 | +3.3 nm |
| 77° | 1.35 | +4.3 nm |
| 70° | 1.61 | +6.6 nm |
| 60° | 2.13 | +10.1 nm |

A wall angle typical of an ion-beam etch on this platform, near 77°, is a third
of the way to doubling the coupling constant.

The same change raises n_eff and therefore displaces the Bragg wavelength by
approximately 10 nm across that range. Sidewall angle is consequently a
first-order parameter for both κ and λ_B, and is not to be treated as a
second-order process detail.

### L004 — A uniform grating has a bandwidth floor that no coupling strength can beat
*Recorded 2026-08. Class: invariant. Confidence: high, analytic.*

The reflection FWHM of a uniform grating of length L and group index n_g cannot
fall below the κ→0 sinc limit

> Δf_min ≈ 0.886 · c / (2 · n_g · L)

Any stronger coupling only broadens the response. A quoted bandwidth below this
floor is not achievable at the quoted length, whatever the coupling.

This is a cheap and general consistency check, applicable to published figures as
readily as to one's own. It has already identified a mutually inconsistent
reflectivity-and-bandwidth pair in the literature.

Enforced by: `grating.transform_limit_fwhm_GHz` is reported and a warning is
raised by the `grating` stage.

### L005 — The Bragg wavelength shift under an index perturbation scales with the group index
*Recorded 2026-08. Class: physics. Confidence: high, analytic.*

The Bragg condition λ_B = 2 n_eff Λ / m suggests Δλ/λ = Δn/n_eff. That is
incorrect, because n_eff is itself dispersive. Perturbing both sides properly
gives

> Δλ_B/λ_B = Δn / n_g

For a shallow-etched thin-film ridge, n_g/n_eff ≈ 1.25, so use of the phase index
over-predicts the tuning efficiency by approximately 25 %. This is among the
easiest ways to mis-size an electro-optically tuned distributed reflector.

### L006 — Quoted overlap-free figures of merit must be distinguished from physical ones
*Recorded 2026-08. Class: interpretation. Confidence: high.*

A Vπ·L figure computed at unit electro-optic overlap differs from the physical
value by 1/Γ, and Γ is frequently in the range 0.3 to 0.5 for coplanar
electrodes on a high-permittivity film, because the film draws the field and the
optical mode is only partly within it.

When a published Vπ·L appears optimistic by a factor of two to three, the
probable explanation is that the un-derated figure has been quoted. Both should
be reported. The chain reports `eo.VpiL_ideal_V_cm` alongside `eo.VpiL_V_cm` for
this reason.

### L007 — Intrinsic linewidth is not the coherence figure that matters for delay-line interferometry
*Recorded 2026-08. Class: system. Confidence: high.*

Where a single source drives both arms of a delayed self-heterodyne measurement,
the phase noise is delay-correlated and cancels to first order, with a residual
proportional to 4 sin²(π f τ). Noise below approximately 1/(2πτ) is strongly
suppressed. The intrinsic Lorentzian linewidth is therefore the correct figure of
merit, and the much larger integrated linewidth is not.

The qualification that matters: any narrow spectral feature falling near the
correlation knee survives the cancellation. Mechanical resonances of an
overhanging die commonly land in the tens of kilohertz, which is precisely that
region for delays of a few microseconds. The mechanical mount is consequently a
coherence design item and not a packaging afterthought.

---

### L024 — The scope of a platform limit belongs in the record beside its value
*Recorded 2026-08. Class: procedural. Confidence: high, both readings were
worked through and they produce different architectures.*

A material limit is ordinarily reported against the structure where it was
noticed. A power ceiling observed in a resonator gets written down as a ceiling
"in the cavity". That phrase carries an ambiguity the number does not: it may be
a property of resonant buildup, where circulating intensity greatly exceeds what
is launched, or a property of any waveguide in that material.

**The two readings are not a matter of degree. They select different
architectures.** Under the resonant reading the constraint binds one element and
the rest of the circuit distributes power freely. Under the material reading
every passive splitter, every modulator and every feed is bound by the same
number, and a circuit that routes more than the ceiling anywhere cannot be built
on that material alone. In the case that produced this entry the second reading
forced a partition across two materials, changed a splitter ratio, introduced
interface transitions that no component list carried, and propagated into the
linewidth budget through the output-power term.

An architecture had been drafted against the first reading, and a resolution
accepted, before the question was asked. The resolution was void.

**Record the scope when the value is recorded.** A one-line qualifier — this
element, this material, this wavelength, this intensity, this average power —
costs nothing at the time and decides what the number governs. Where the scope
is unknown, record that it is unknown and treat the constraint as blocking
rather than as satisfied: the permissive reading is the one that silently
produces an unbuildable design.

**Ask for the mechanism as well.** Damage, absorption-driven heating and a
foundry handling statement scale differently and carry different margin. A
number without a mechanism cannot be extrapolated to another wavelength, duty
cycle or geometry, and it cannot be argued with.

---

### L025 — A specification tighter than its own justifying analysis is slack
*Recorded 2026-08. Class: procedural. Confidence: high, the mechanism is plain
and one worked case is given.*

A component specification and the system analysis that justifies it are written
at different times, often by different hands, and they drift apart in one
direction: the specification tightens. A system analysis performed with a
conservative placeholder is not revisited when the component target is later set
at a firmer value, so the requirement ends up demanding performance the analysis
never asked for.

In the case that produced this entry a linewidth requirement stood three times
tighter than the per-source figure the system budget had assumed when computing
the very quantity that requirement exists to protect. Relaxing the requirement
to the assumed figure cost nothing measurable at system level, and it released a
design freedom that a coupled requirement needed.

**The test is mechanical and is worth running over every requirement set.** For
each component specification, find the value the system analysis actually
substituted. Where the analysis used a looser number and still closed, the
difference is free performance available to be spent elsewhere. Where the
analysis used a tighter number than the specification, the specification does
not protect the system and the conflict is real.

The same comparison catches the opposite error, which is more dangerous because
it is less visible: a figure quoted in a design table that the analysis never
used, or used under a different convention. A quantity carried at unit overlap,
in a different band, or before a derating is not the quantity the component must
meet.

**A specification is not evidence about a system until it is shown to be the
number that system's analysis consumed.**

---

## Toolchain Defects Found and Corrected

Recorded because each represents a class of error that recurs.

### T001 — Truncated buried oxide over a high-index handle admits substrate modes
A mode-solver window that truncates the buried oxide and then includes the
silicon handle will return substrate modes at the handle index. Where the real
oxide is thick enough to isolate the mode, the handle is to be excluded from the
optical problem and retained only for the electrostatic problem.

### T002 — Blanket layers drawn to the window edge corrupt the boundary column
Sub-pixel material averaging at a window boundary will report a half-filled cell
where a blanket layer terminates exactly at the edge. The consequence was a
lateral-guidance floor computed too low, and slab continuum states miscounted as
guided modes. Blanket layers are to be drawn beyond the window.

### T003 — Guided-mode counting must be referenced to the slab, not the cladding
For a rib waveguide, a mode is laterally guided only while n_eff exceeds the
effective index of the **unpatterned slab**. Counting against the cladding index
classifies every discretised slab continuum state as a guided mode.

### T004 — Electrostatic windows must be sized for the fringing field, not the mode
The field that sets electrode capacitance extends far further than the optical
mode. A window sized for the mode under-read the capacitance by approximately a
factor of four. Two meshes are appropriate: a fine narrow one for the optics, a
coarse wide one for the electrostatics, with interpolation between them.

### T005 — A test fixture that places a material interface on a node is not a solver defect
A finite-difference validation in which the interface coincides with a node
widens the core by one cell and biases n_eff upward. Where a solver appears to
disagree with an analytic result at the third decimal place, the fixture is to be
examined before the solver. Production code should sub-pixel average; validation
fixtures should stagger the interface between nodes.

### T006 — Unit cancellation is to be verified, not assumed
A capacitance was in error by 10⁶ because a conversion was applied where the
chosen units already cancelled. Any expression mixing micrometre geometry with SI
constants warrants an explicit dimensional check.

### L008 — A discretisation residue is not a loss, and must not be named as one
*Recorded 2026-08. Class: numerical method. Confidence: high, demonstrated by a convergence study.*

A staircase treatment of a slowly varying structure, in which the local modes of
successive slices are projected onto one another, loses a little power at every
step. That deficit is not radiation. It falls as the reciprocal of the slice
count and tends to zero for a structure that is genuinely adiabatic, so a figure
derived from it describes the mesh rather than the device.

The test that distinguishes them costs one extra run: halve the slice count and
compare. A physical loss is unmoved; a residue changes. Where the two are
reported under one name, a taper whose real loss is below 0.02 dB can be
presented as losing 0.18 dB.

Consequence: any quantity that scales with the discretisation is to be reported
under a name that says so, and separately from the quantity that converges.

### L009 — An adiabaticity criterion is a screen, not a loss estimate
*Recorded 2026-08. Class: physics. Confidence: high, one criterion checked against a time-domain solve.*

The usual criterion compares the rate at which a guide changes against the beat
length with the state into which power would be lost. It takes no account of the
overlap with that state. A symmetric taper couples only weakly to the symmetric
radiation continuum, so a margin of order unity does not imply that power is
lost there.

On one structure a margin of 2.7, which by the usual rule of thumb calls for a
redesign, corresponded to lateral radiation below 0.015 dB when solved in the
time domain. The margin located the section worth examining and was wrong about
the consequence.

Consequence: a margin below the threshold is a reason to run a solver that
carries the continuum, and not a reason to lengthen the taper.

### L010 — Coupled-mode theory over-predicts the coupling constant, and by how much is measurable
*Recorded 2026-08. Class: physics. Confidence: medium; two instruments agree in direction, not yet in magnitude.*

A coupling constant obtained by Fourier analysis of an index profile assumes the
perturbation is weak. Checked against the photonic band gap of the same
structure, which involves no length, no propagation and no radiation channel, the
constructed value was high by roughly a quarter to a half.

The band-structure route is the appropriate instrument. Measuring the same
quantity by propagation requires a length of order 1/κ, which for a weak grating
is millimetres and beyond a finite-difference domain; forcing the grating strong
enough to measure over a short length introduces radiation, which coupled-mode
theory does not model, and the comparison is then confounded. Both failure modes
were observed before the correct instrument was used.

Consequence: where a computed κ disagrees with a measurement by a factor of
order one, part of the discrepancy is likely to be the model. The split is to be
established before the remainder is attributed to fabrication.

### L011 — The nominal point is not the design; the window is
*Recorded 2026-08. Class: procedural. Confidence: high, quantified on a validation baseline.*

Re-running a chain at the edges of a plausible process window costs a few
minutes and frequently reorders the concerns. On one device, across ±20 nm on
the most sensitive lithographic dimension and ±10 nm on two film thicknesses,
the Bragg wavelength moved by 0.9 % while the continuous tuning range moved by a
factor of five.

Consequence: for any metric whose spread across the window exceeds its own
value, the nominal figure carries little information. Such a metric is to be
centred where its sensitivity is small, or provided with a trim.

### L012 — A shared mesh cancels systematic error, and the cancellation is measurable
*Recorded 2026-08. Class: numerical method. Confidence: high, two unrelated solvers on one cross-section.*

Where a small index difference is obtained by solving a perturbed and an
unperturbed cross-section, the two solves are conventionally performed on one
mesh so that the systematic discretisation error largely cancels. The
cancellation is usually asserted rather than demonstrated.

It has now been measured. A finite-difference semi-vectorial solver on a
staircased structured mesh and a full-vectorial finite-element solver on a
conforming triangulation were applied to the same shallow-etched thin-film
cross-section. The absolute effective indices differed by 2.6 × 10⁻⁴ in
fraction. The index *difference* produced by a side-coupled perturbation, of
order 8 × 10⁻⁴ in absolute terms, agreed to within 1.8 %.

Consequence: a difference computed on a shared mesh is of a materially higher
standing than either absolute value entering it, and by a margin that can be
quoted. Where a coupling constant built from such a difference disagrees with an
independent measurement, the difference is not the first place to look.

The comparison is admissible only where it is resolved. Halving the mesh density
of the finite-element solve moved its answer by one sixth of the separation
between the two solvers. Had the two been comparable, nothing would have been
established in either direction.

### L013 — A semi-vectorial solver cannot report the quantity that bounds its own error
*Recorded 2026-08. Class: numerical method. Confidence: high, analytic and confirmed numerically.*

A semi-vectorial formulation carries one transverse field component and assumes
the other to be absent. The share of the transverse energy actually carried by
the minor component is therefore invisible to it, and that share is exactly the
weight attaching to everything the formulation omits.

A full-vectorial solve on the same cross-section returns it directly. On a
shallow-etched thin-film ridge the polarisation purity was 0.9965, so the
assumption was supported there. The figure is a property of the cross-section
and not of the solver, and it is to be re-measured on any section that is more
strongly hybridised.

The same figure converts an unusable bound into a usable one. A scalar-permittivity
solver run at each principal index of a birefringent film brackets the
anisotropic answer, but the bracket is as wide as the birefringence and of no
practical use on its own. Weighted by the polarisation purity, it becomes an
estimate of the right order, the dominant component already seeing the correct
axis.

### L014 — A lithographic bias moves a high-order grating in two opposing ways
*Recorded 2026-08. Class: manufacturability. Confidence: high, arithmetic confirmed against a chain run.*

The intuition that a process printing wide produces a stronger grating is
correct for a first-order structure and can be wrong for a high-order one. Two
effects follow from the same displacement and they oppose each other.

A positive bias closes the gap between the guide and a side-coupled element, so
the index contrast rises. The same bias also widens the element along the
propagation direction, so the duty cycle rises. The coupling constant depends on
the duty cycle through the Fourier amplitude of the m-th harmonic,

> a_m ∝ Δn · sin(m π D) / m

which is maximised at D = 1/(2m) and falls on either side of it. A third-order
grating operated above that duty cycle therefore loses harmonic amplitude as the
bias closes the gap.

Measured on one shallow-etched cross-section, a 40 nm bias raised Δn_eff by 24 %
and reduced sin(3πD) by 26 %, for a net change in κ of −8 %. The two terms
cancelled to within a tenth of either.

Consequence: the sensitivity of κ to a lithographic bias cannot be taken from
the gap alone on a grating of order above one. Both terms are to be evaluated,
and the sign of the net effect is to be established rather than assumed. A
design sitting near D = 1/(2m) is additionally insensitive to the duty term at
first order, which is a centring choice available at no cost.

### T007 — A decay criterion can stop a time-domain solve before the pulse arrives
A run terminated by field decay at a monitor will stop immediately on a long
cell, the field there being still zero when the first check falls due. The
result is a mode amplitude of exactly zero rather than an error. A minimum run
time of order twice the optical transit is to be imposed alongside any decay
criterion.

### T008 — A conformal bend transformation manufactures a bound state near the caustic
The transformation grades the cladding index without bound, so beyond the
radiation caustic the cladding out-guides the core. A discretised solve then
returns a state bound to the window edge, with an effective index above the core
index and a centroid displaced several times the guide width. Three separate
guards were needed: the ceiling must be the index of the mode being tracked and
not the material index; the cladding index must be that of the vertical stack
beside the guide, not the maximum permittivity of the edge column; and where the
caustic falls inside the window the case is to be refused rather than answered,
the mode being genuinely leaky there.

### T009 — The natural boundary condition of a curl-curl mode solver is a magnetic wall
A finite-element mode solver in the curl-curl formulation imposes no essential
condition by default, and the resulting natural condition forces the tangential
*magnetic* field to zero at the window edge. This is a magnetic wall. A layer
reaching that edge is incompatible with it, and the solve returns an index low
by a hundred times the error of a comparable finite-difference solve on the same
problem.

The condition is to be set explicitly to the electric wall, which forces the
tangential electric field to zero and matches what a finite-difference solver
with a Dirichlet window imposes on its dominant component.

The defect is recorded because of how it presents. It returns a plausible number
rather than a failure, and where such a solver is being used as a cross-check the
discrepancy is attributed to the method under test rather than to the
instrument. A cross-check is to be anchored to a closed-form result before it is
pointed at anything.

### T010 — A process-wide cell library silently disables a second layout backend
A layout framework holding its cells in a process-wide library refuses a
repeated cell name. Any chain emitting a layout more than once within a single
process therefore loses that backend after the first call, and a comparison
against it is skipped rather than failed. The condition was invisible: the
metric recorded the backend as unavailable, which is also what an uninstalled
backend records.

A corner study is precisely the case that emits repeatedly. The cross-check ran
on the first corner and on none of the others.

The library is to be cleared before each emission. More generally, a check that
reports "not performed" is to be distinguished in the metric tree from one that
reports "performed and agreed", and any stage that can silently skip a
cross-check is to state which of the two occurred.

### T011 — An overlay mark drawn identically on two levels is a short
The obvious construction for a registration mark is one figure repeated on each
lithographic level at the same position. It fails twice. The two levels then
overlap over their whole area, which any layer-to-layer separation rule reports
as a short, and the overlay cannot be read at all, there being no gap whose
asymmetry carries it.

The figures must nest: an outer annulus on the first level, a smaller figure
inside it on the second, separated by more than the layer-to-layer rule. The
registration error is then the difference between opposite gaps.

Corollary of wider application: every structure added to a mask for measurement
rather than for function is subject to the same rule deck as the device. A
monitor field that violates the deck is removed before submission, which is the
least useful outcome available. Where a monitor cannot be drawn at the dimension
requested, the dimension is to be raised to the rule and the compromise
reported, so that it is known which part of the design space the monitor does
not reach.

### T012 — A loss term entered with the sign of a gain, and the existing test could not see it
The propagation loss of a grating enters the coupled-mode solution as the
imaginary part of the detuning. Its sign was inverted, so reflectivity **rose**
with loss instead of falling, and passed unity once the coupling was strong
enough. Two evaluation paths were present, a closed form and a piecewise
transfer-matrix cascade, and they carried opposite conventions for that sign.

Three properties of the defect are general.

**It hid in a regime that had not been reached.** At the integrated coupling the
design carried, the error displaced the reflectivity by 0.03 and no acceptance
target resolved it. It broke the physical bound only when an unrelated
correction to an input raised the coupling by a third. Improving one input moved
the model into a regime where a second error became visible.

**The test that should have caught it could not.** A test comparing the two
evaluation paths was present and passing. It compared them at *real* detuning,
and for a real detuning the two conjugate conventions give the same reflected
magnitude. The test passed under either and distinguished nothing. A comparison
between two implementations is only as strong as the region of the input space
over which it is drawn, and the region that matters is the one where the two
formulations differ.

**The invariant was not being checked.** A passive structure cannot return more
power than it receives. Such a bound costs nothing to evaluate, holds for every
design, and is violated only by an incorrect model. It is now enforced twice: as
a test swept across coupling strength and loss, and as a runtime condition that
raises rather than warns, a value above unity indicating that the model is wrong
rather than that the design is poor.

Consequence, stated as a rule: for any quantity bounded by physics, the bound is
to be asserted in the code and not only in the reader's expectation. A
monotonicity is to be asserted alongside it, since a bound alone is satisfied by
a term of the right sign and the wrong magnitude.

### L015 — Replacing an assumption with a sourced value is not a move toward agreement
A design file carried a vertical sidewall, annotated as an assumption because
the reference did not state one. The etch used on that platform cannot produce a
vertical wall, so the value was not a conservative placeholder; it was
unattainable. An open foundry kit for the same film thickness, etch depth and
oxide declared the real figure.

Adopting it raised the coupling constant by 35 % and moved the disagreement with
the published device from a factor of 1.6 to a factor of 2.15. The single-
parameter explanation that had reconciled four published figures now reconciles
three.

The result of the correction was therefore a larger discrepancy and a weaker
explanation, and it was still worth making. What the model says is now known;
before, what was known was what the model said about a geometry that cannot be
fabricated.

Two corollaries follow.

An assumption is to be judged against what the process can deliver, not against
whether it is neutral. A placeholder at the boundary of the attainable range is
the least defensible choice available, and it will usually be the one that looks
tidiest.

The direction in which a corrected input moves the agreement carries
information. Where it moves against agreement, an explanation that was carrying
the whole discrepancy has been weakened, and the residual is to be re-attributed
rather than re-scaled.

### T013 — A parameter that feeds a calculation is not on the mask until a polygon carries it
A facet angle was declared in a design file, read by the coupling calculation,
and reached no polygon. The emitted guide had square ends for as long as the
chain existed. Every check passed, because every check examined either the
number or the mask, and no check compared them.

The angle exists to steer the facet reflection out of the guide. A number that
is used to derate a coupling figure and is absent from the geometry suppresses
nothing, so the derating was applied to a device that would not have behaved
that way.

Consequence: for any parameter with a geometric meaning, the test is to measure
the quantity back off the written layout rather than to assert the parameter.
The failure is invisible to a review of the design file, to a review of the
metrics, and to a rule deck.

### T014 — Snapping vertices does not put the merged geometry on the grid
Every vertex of a drawn polygon was snapped to the manufacturing grid, and the
merged layer was still off it. Two shapes on one layer that overlap are resolved
into a single outline when the layer is merged, and the boolean introduces
vertices at their intersections. Those vertices are computed rather than drawn,
so they land where the crossing falls.

The order is therefore to merge first and snap afterwards, which is the order
mask preparation uses. The condition is invisible until a grid check is run
against the merged layer, and a grid check against the drawn shapes passes.

### L016 — An angled feature and a minimum-width rule interact through the corner
Every convex corner brings two edges arbitrarily close together, so a width or a
spacing check reports the corner itself unless a threshold on the interior angle
is supplied. Engines default that threshold to 90 degrees, which is exactly the
value at which an orthogonal layout sits.

Drawing any feature at an angle moves a corner below the threshold. An 8 degree
facet on a guide produces an 82 degree corner at the tip, which is
manufacturable, and which a minimum-width rule reports as a violation at the
default setting.

Consequence: the corner threshold is a property of the rule and belongs in the
rule declaration, not in the engine default. It is to be set below the sharpest
corner the design intends and above the sharpest corner the process refuses.
Where a mask acquires violations after a feature is drawn at an angle, the
corner threshold is the first thing to examine and the geometry is the second.

### L017 — A reticle carrying one copy of an uncertain design gambles the run
Process control structures measure the process. They do not deliver a working
device. Where a metric is more sensitive to a lithographic dimension than to any
design choice, a reticle carrying one copy of the device stakes the whole
fabrication run on the model being right about that dimension.

The remedy is a ladder: copies of the device stepped across the range the model
and the process together leave open. On a device whose coupling constant is
uncertain by a factor of two and whose continuous tuning range varies fivefold
across the process window, the ladder is what returns a working part from the
first run, and the monitors are what explain why.

A coupled constraint is to be expected and checked for. Stepping one dimension
frequently moves a second feature into a clearance rule; opening the gap of a
side-coupled grating moves its elements toward the electrodes. Where a copy must
be adjusted in a second parameter to remain legal, that copy is no longer the
design with one parameter moved, and the adjustment is to be reported with it.

### T015 — A boolean result carries holes, and a hull-only representation fills them in
An inverse layer produced as *field minus feature* was found to overlap the very
feature it was derived to exclude. The operation was correct; the representation
was not. A boolean result is a polygon with holes, and a pipeline carrying
polygons as sequences of hull vertices has no way to express one, so every hole
closed silently and the inverse came out solid.

The condition passes a rule deck, the resulting shape being legal, and it passes
an area check on the derived layer alone. It is detected only by intersecting
the derived layer with its operand, which should be empty by construction.

Where a geometry pipeline cannot represent holes, they are to be cut open before
the conversion, which is the operation a mask writer performs in any case. More
generally, a derived layer is to be checked against the identity that derived
it, and not merely inspected.

### L018 — A single-pass budget and a cascade differ by the resonance between the ends
The reflection presented to a gain chip by a mirror behind a coupler is not the
mirror reflectivity times the coupler transmission squared. The coupler has a
residual reflection, and the two reflectors form an etalon.

Measured on one device, an anti-reflection coating of 10⁻⁴ in power, which is
0.01 in amplitude, modulated the effective mirror by 2.7 % across its stop band.
The single-pass product was 4.6 % from the assembled result at the peak.

Two consequences follow. A loss budget is not an anchor against which a
scattering-matrix assembly can be checked, since the two describe different
things; the closed-form two-mirror expression is the anchor, and agreement to
numerical precision is then the expectation. And a cavity model applying its
mirror at a single plane carries no such ripple, so the threshold and the
side-mode margin it reports are evaluated against a mirror smoother than the one
the laser sees.

A ripple is to be measured against the same circuit with the offending
reflection removed. Measured against the reflectivity itself it reports the
mirror's own lineshape, which varies by a factor of two across a half-maximum
band by definition.

### L019 — The release step is the only one that should refuse
Every stage of a design chain reports. A quantity is computed, a condition is
annotated, and the run continues, which is correct: an intermediate result that
halted the work would prevent the reader from seeing the rest.

That property becomes a defect at the point of submission. A set of files sent
to a fabricator is a claim that they are ready, and a chain in which every check
is advisory produces that claim by default. One step is therefore to evaluate
the conditions of readiness and to raise rather than warn.

Two properties make such a gate usable rather than an obstruction. Each
condition names the field that decides it, so an unmet condition states what to
change. And each may be waived by name, with the waiver recorded beside the
condition rather than removing the row, so that what was accepted remains
visible to whoever reads the manifest afterwards.

### L020 — A default chosen for cost is to be re-measured when the cost changes
A mask emitter drew a fraction of a periodic structure by default, the count
having been chosen when the stage was written on the grounds that emitting all
of it was slow. The justification was carried forward in a docstring and never
re-tested.

Measured later, emitting the whole structure cost 1.5 s against the 35 s the
same run already spent solving a mode. The saving had never been material, and
the cost of taking it was that every geometric figure the run reported described
a device that was not the one being simulated. A warning was emitted on every
execution to say so, which is the worst of both: the condition was known, stated
and permanent.

Two general points follow.

A performance default is an assertion about relative cost, and relative cost
moves as the surrounding work grows. Such a default is to be re-measured when
the stage around it changes materially, and the measurement is to be recorded
beside the value so that the next reader is not left with the assertion alone.

A warning that fires on every run is not a warning. It is a permanent condition
being reported through a channel meant for exceptions, and it trains the reader
to skip the channel. Where a condition is permanent, either the default that
causes it is wrong or the condition is not worth a warning.

### T016 — A hand-drawn figure sits outside the geometry checks the chain applies to itself
A schematic in a design report carried a four-vertex polygon whose vertices were
in the wrong cyclic order. The edges crossed, so the shape was a bowtie, and its
enclosed area was 40 % of the trapezoid intended. It rendered as a plausible
wedge and was reviewed several times without the defect being seen.

The chain checks the emitted mask for exactly this condition and reports it as a
strange polygon. The figure was drawn by hand into a document, so it never
entered that path.

Two points generalise.

A self-intersecting quadrilateral is the failure mode of specifying a shape by
its vertices rather than by its dimensions. It is avoided by declaring the shape
in terms a reader can check, being an end width and a length, and constructing
the vertices from them.

Any geometry the project produces outside its own toolchain is to be held to the
same checks the toolchain applies. Where the check is a few lines, it is cheaper
to duplicate it than to rely on inspection, because the failure renders as
something believable.

### T017 — An editable-SVG figure carries two descriptions, and they diverge
A diagram format that stores both a rendered picture and an editable model in
one file has two sources of truth. Writing them independently produced a
detailed rendering beside a coarse model of the same diagram, 96 elements
against 9.

Two consequences, and the second is the dangerous one. The editor shows
something that is not what the document displays. And saving from the editor
regenerates the picture from the model, so opening the file to look at it and
pressing save silently replaces the detailed figure with the coarse one.

Both descriptions are to be generated from a single declaration of the diagram.
Where the two renderers cannot express the same primitive, the divergence is to
be confined to one named element and stated, rather than left to be discovered.

### T018 — A cross-check without a convergence guard is not a cross-check
A coupling constant obtained from a photonic band gap was set against the
coupled-mode value on the same structure and reported a disagreement of 1.63,
attributed in a warning to the coupled-mode construction. The comparison was
then repeated on a second mesh. The refinement moved the band-gap value by more
than the disagreement being claimed, so the verdict distinguished nothing.

The cause is structural rather than numerical. A band gap is the difference
between two eigenvalues that are nearly degenerate by construction, so its
relative size can be four or five orders below the eigenvalues themselves. The
discretisation error is carried by each eigenvalue separately and does not
cancel in their difference. A mesh adequate for the band frequency to three
figures is therefore not adequate for the gap to one.

Three points generalise.

Any quantity obtained as the difference of two large and nearly equal results
requires its own convergence statement. The convergence of the results entering
it does not transfer.

A warning that attributes a disagreement to a named cause is a finding, and it
is subject to the same guard as a reported metric. The attribution here was
plausible, was consistent with an independent analytic argument, and was
nonetheless unsupported.

An operating manual can document a guard the code does not implement. The rule
requiring the guard had been written and was being followed in reading the
output; the guard itself did not exist. A rule is to be enforced by the code
that produces the quantity, and not by the discipline of the reader.

### T019 — Inverting a function by interpolation asserts that it is monotonic
A resonance condition was solved by interpolating the inverse of a phase
function: given the phase on a frequency grid, the frequency at which the phase
took an integer multiple of 2*pi was obtained by interpolating frequency against
phase. The routine used requires its abscissa to increase, and returns a value
without complaint when it does not.

The phase was not monotonic. A distributed reflector's phase steps by pi at each
null of its reflectivity, so the group delay there is large and negative. Five
per cent of the samples decreased. The returned roots were wrong, and the
quantity built from them moved discontinuously by amounts that would have been
noticed had anyone plotted it.

Three points generalise.

Inverting a function by interpolation is an assertion that the function is
monotonic, and the assertion is silent. Where the function is a phase, a group
delay or any quantity whose derivative can change sign, roots are to be found by
bracketing a sign change, which is correct either way and costs no more.

A tracked quantity is to be checked for continuity as a matter of course. The
defect presented as a discontinuity in a curve that no equation permitted to be
discontinuous, and that check is two lines.

The defect was invisible at the nominal design point and severe away from it.
The measured window on the baseline happened to contain no jump, so every run
ever performed on that design was correct. The error appeared only when the
design was moved toward the configuration that met its requirement, which is
the configuration a study is undertaken to find.

### T020 — A sensitivity is two matrices, and neither of them is risk
A derivative of a metric with respect to a parameter answers which knob moves
what. It does not answer what threatens the design, and the two were conflated
until both were tabulated side by side.

The elasticity, being the logarithmic derivative, is a property of the physics.
It is independent of how well any parameter happens to be controlled, and it
ranks the knobs. The contribution, being the excursion each parameter actually
carries multiplied by that elasticity, is a property of the process, and it ranks
the process steps. On the study that prompted this, one quantity carried the
largest elasticity in the matrix and the largest contribution, and was no risk of
any kind: it stood three orders of magnitude below the bound its target set.

Three points generalise.

Risk is the contribution compared against the margin the requirement leaves, so
it needs the target as well as both matrices. A quantity of small sensitivity
sitting on its bound is at risk and a quantity of large sensitivity sitting far
from its bound is not.

An elasticity presumes the metric is monotone in the parameter over the range
probed. Where it is not, the number scales with the width of the perturbation and
describes nothing: one metric returned values differing by a factor of nineteen
between a wide excursion and a narrow one, and the correct report was that no
derivative exists for it.

A one-factor study cannot see an interaction, and a geometric clearance rule is
where interactions live. Widening one dimension moved a feature into a second
whose clearance then forced a third dimension to change, and that third change
undid the improvement the first was made for. Neither the sensitivity matrix nor
the corner study could reveal it, both perturbing one factor at a time, and it
appeared only when the rule check was placed inside the search loop.


### T021 — Placeholder layer numbers do not fail against a foundry deck, they collide

A rule deck reads layers by number. A design carrying placeholder numbers was run
against a process runset for the first time. The numbers did not simply miss:
the design's slab sat on the number the process reads as its ridge, its alignment
marks on the number read as metal, and its waveguides on a number the deck reads
not at all.

The deck therefore checked a slab rectangle against the ridge rules, checked the
alignment marks against the metal rules, and never examined a waveguide, a
grating feature or an electrode. Had it been run without the mapping being
inspected, it would have returned a small non-zero count that reads exactly like
a check that was performed.

**A false pass is worse than no check.** After any remap, confirm that every
layer the deck names is one something is actually drawn on. Enforced by the
device-level and die-level deck runs recorded in the run register.

### T022 — A rule that has nothing to compare reports nothing, and that is not a pass

The same runset carries a die footprint rule, a centring rule and an
exclusion-ring rule. All three are evaluated against an outer boundary rectangle
and a usable-area rectangle. The chain drew a seal ring and a dicing lane and
neither of those two, so all three rules were silent on every die it had ever
emitted.

Silence was being read as compliance. Drawing the pair moved the die from three
unexercised rules to three exercised and passing ones, and in doing so exposed a
second defect: the emitted die was 120 um larger in each dimension than the die
declared, the usable area having been computed without deducting the seal-ring
clearance that the ring then added back. On a process offering three fixed
footprints that is a refusal at submission.

**Report an unexercised rule as unexercised.** A check that produced no finding
because it had no input is to be distinguished, in every report, from a check
that produced no finding because nothing was wrong. Enforced by
`test_the_chip_frame_is_drawn_centred_and_to_the_declared_size` and
`test_the_emitted_die_is_the_size_that_was_declared`.

### T023 — A range that never reached its limit is a statement about the driver

A continuous tuning range was reported as 8.20 GHz against a requirement of 8.0
and treated as a cavity result for several iterations. Effort went into the
penetration depth and the mirror strength, which are what bound a mode-hop-free
range.

The sweep had encountered no mode hop at all. It had run out of drive voltage.
The cavity's own bound was 12.15 GHz, and the 8.20 was simply the declared 20 V
multiplied by the tuning rate. Every conclusion drawn from that number was
addressing a mechanism that was not active, and the remedy was a higher-voltage
driver rather than any change to the grating.

**Report what bounded a swept quantity, not only its value.** Where a sweep is
clamped, the clamp is the finding. A range that meets its target without
encountering the limit it is named after is to be labelled by the limit that
actually applied.

### T024 — A drawing keyed to numbers the design may change misreports in silence

A plan-view renderer held its own table of layer numbers. When the design was
remapped to a process numbering, the renderer went on believing the old
assignment: it painted the waveguide in the slab's colour and omitted the metal
entirely. It raised nothing, and neither its legend nor its caption disclosed
anything.

A figure that fails is a nuisance. A figure that quietly draws the wrong thing is
evidence, and it will be believed.

**Drive every drawing from the run's own resolved configuration.** Where a
drawing must name something the design declares, it reads that name from the run
rather than holding a copy.


### T025 — A cross-check computed by two different code paths must be made like for like

A coupled-mode coupling constant was compared against a band-structure
measurement of the same structure. The band-structure stage carried its own
two-dimensional reduction, and that reduction called the Fourier coefficient with
four of its six arguments. The trailing two, the period and the longitudinal
profile smoothing, therefore defaulted to zero.

So one side of the comparison applied the smoothing the design declared and the
other applied none, and nothing in either output said so. The disagreement that
resulted was attributed to the physics. A smoothing length was calibrated to
close it, adopted, documented at length, and carried for three days. A second
calibration replaced the first on the same false basis.

When the missing arguments were supplied the disagreement reversed sign. The
band gap lies **above** the coupled-mode value, not below, so every non-zero
smoothing makes the agreement worse rather than better. Both calibrations were
withdrawn, and the coupling they had been suppressing turned out to be 16 %
higher than the design had been carrying, which put peak reflectivity outside its
bound.

**Where two code paths compute the same quantity for comparison, they are to be
driven from one function with one argument list.** A default that silently
changes the meaning of one side is indistinguishable from a physical effect, and
it will be explained as one. The tell was available throughout: the same
quantity appeared under two names in one metric tree and no test asserted that
they agreed when they should.

Enforced by passing the period and sigma explicitly in the reduction, and by
the arithmetic check that at sigma = 0 the two paths return the same number.

### T026 — A correction factor adopted to explain a measurement must be withdrawn when the measurement changes

The smoothing above was defended on the grounds that an instrument had measured
it and that adopting it made no target pass. Both statements were true when
written. Neither survived the instrument being corrected.

The discipline that admits a correction factor is the same discipline that
removes it. **Withdrawing one is to be as explicit as adopting one, and its
consequences are to be reported before they are addressed.** Here withdrawal
moved a target from met to unmet, and that failure was recorded in the design
file and reported before any change was made to recover it.

The recovery is then to be made in the geometry and not in the factor. A 35 nm
change to the dimension the coupling actually depends on restored every target
with margin. Restoring them by choosing a different smoothing would have been
the prohibited move, and it would have looked identical in the metric tree.

### T027 — Wall clock counts the time a machine spends asleep

A corner sweep left running overnight reported one corner at 8.2 hours against
70 seconds for each of its neighbours. The elapsed figure was wall clock and the
machine had suspended. A runaway iteration was diagnosed, a defect was reported
against a period solver that did not have one, and the supporting evidence was a
converged wavelength read as a symptom of over-iteration.

**Record processor time beside wall clock and report the gap.** The two together
distinguish a slow stage from a suspended one and neither alone does. Where a
stage delegates to an external process, that process's own reported elapsed time
is the one to believe over either.

### T028 — Absence of a finish is not evidence of failure

Four jobs were misjudged in one session, and every misjudgement had the same
shape. A test module taking twenty minutes was called a hang and killed. A
three-hour run was declared dead thirteen minutes in, on a process listing
truncated by `head`. An eleven-minute sweep was killed twice by a nine-minute
timeout, and the second kill was then explained as a hang in a stage that had
never been reached.

In each case a job that was working was recorded as broken, and in two of them
work was done to fix a defect that did not exist.

**Establish the expected cost and the elapsed time before concluding anything
about a job's health.** A chain that does not record what each stage costs cannot
support that judgement, and one that records only wall clock supports it wrongly.
The check that a timeout exceeds the measured duration of the thing it guards is
arithmetic and takes a second.

### T029 — Ask what a run can possibly show before starting it

A three-hour band structure was queued to confirm a calibration. The parameter
being confirmed does not enter that solver's inputs at all, so the run could not
have returned a different answer whatever the calibration was. The confirmation
that mattered was arithmetic on numbers already in hand.

Separately, the job it was about to re-solve differed from a completed one only
in the fifteenth significant figure, through floating-point evaluation order.

**A run that cannot change a conclusion is delay and not evidence.** Two habits
follow: state what each outcome of a proposed run would imply before starting it,
and content-hash an expensive deterministic job so that an unchanged one is
reused rather than repeated.


### T030 — A long document written as work proceeds records the investigation, not the answer

Two reports here grew by accretion, and the measurement is unambiguous. In
`DESIGN_REPORT.md` one section holds **1152 of 1937 lines, 59 % of the
document**. In `TOOLCHAIN_VALIDATION.md` one section holds **512 of 1134,
45 %**, and inside it a single finding runs to seven sub-sections that are the
steps of an investigation in the order they happened: the alternative
explanation, the hypothesis tested, a correction to the reading above, the check
re-run, the leading candidate, the converged measurement, the remaining suspect
eliminated.

Each addition was correct when written. The result is that a reader meets three
withdrawn explanations before the surviving one, and meets a superseded figure
seven hundred lines before its replacement.

**Order a report by what the reader needs, not by what happened.** The answer
first, the evidence that supports it second, and the history of how it was
reached in an annex where it remains available and stops obstructing. A section
exceeding roughly a fifth of a document is a section that has become the
document, and the test is mechanical enough to apply without judgement.

The history is not to be deleted. A withdrawn explanation records why an obvious
line of attack fails, which is worth as much as the answer and is not recoverable
from it.

### T031 — A document carrying two designs must say which one every number and every figure describes

`DESIGN_REPORT.md` covers a baseline that fails and a candidate that passes. The
distinction is stated once, near the top, and then governs nineteen hundred
lines: most numbers are the baseline's, two sections are the candidate's, and
seven figures are the baseline's while three are the candidate's.

That is not sustainable and it failed in practice. Figures were regenerated from
a candidate run and copied into sections describing the baseline, so every
figure contradicted the text beside it, and the error was found by the reader
rather than the author. It was found because a tuning sweep drawn without a mode
hop sat beside a table stating the voltage at which the mode hops.

**State the design on every figure caption and at the head of every section that
departs from the default.** A convention held in one sentence at the top is a
convention that will be broken, and the breakage is invisible to whoever
introduced it.

The same episode surfaced four numbers that had never been consistent with the
lever printed beside them. **Where a table's entries are related by an
arithmetic identity, that identity is worth checking against the table itself**;
here the ratio of two delays did not equal the ratio stated in the next row, and
nothing had ever compared them.

### T032 — A generated view is to be read before it is shown

The dashboard was published six times and a reader found a defect on each: a
stage reported switched off on a justification that had gone stale, no detection
of a stage then running, corner runs reporting an incomparable design because
they wrote no resolved design, a chip reading "running now" beside body text
saying interrupted, a green "ran" chip beside an interrupted line, and a warning
classifier promoting a stated model limitation into the blocking column.

Every one was visible in the output. None survived being looked at.

**Check a generated view against the artifacts that produced it before
presenting it**: states against what the run produced, counts against the stage
list, dates against the run identifiers, groupings against the text they
classify.

**Prefer a check inside the generator to a habit of checking.** A page that
refuses to emit itself when it contradicts itself is a check that runs every
time; remembering to look is a check that runs when convenient. The two that
survive a self-check are the two that need a reader: a justification that has
gone stale, and a classification that is defensible but wrong.

**Where a view can go stale, have it say so on its own face.** It names the run
it describes and reports whether a later one exists, because every stale page
looked exactly like a current one.


### T033 — A document is checked against the thing it describes, or it is not checked

Across one session, every documentation defect was found by the reader. The
author had reread the documents and found none of them.

The list is worth keeping because the failures are of one kind. A stage reported
switched off on a justification that had gone stale. Six defects on a generated
dashboard across successive publishes. Figures regenerated from one design and
placed in sections describing another, so that every figure contradicted its
caption. A table whose two delays did not form the ratio printed in the next
row. A run register eight days behind the conclusions resting on it. Three
stages that ran, found things, and appeared nowhere. A reference manual claiming
sixteen stages and 249 tests against seventeen and 257.

**None of these is a prose error, and rereading finds prose errors.** Each is a
claim that ceased to be true when something else changed, and the only way to
catch that is to compare the claim against the thing it describes.

Three checks are mechanical and would have caught most of it: take every count
from the source rather than from another document; after changing a value,
search the whole document for the old one; open every figure before citing it.

The rest needs an auditor with the artifacts in hand, which is why
`.claude/agents/doc-auditor.md` exists and why the chain's operating manual
requires it after any change to a design, a stage or a test.

**The hardest omission to see is the one that leaves no trace.** A stage that
ran, found something and was never written up is invisible in the document by
construction. The remedy is to enumerate what ran and report every item,
including those that found nothing, so that an absent finding can be told from
an unasked question.


### T034 — A component requirement is a bound before it is a search

Four suppliers were surveyed for a C-band gain chip. One offered no such part.
One served a different spectral window entirely. One offered a part whose every
published figure was better than the incumbent's, and it was rejected on a
quantity the datasheet does not print.

The mode-hop-free requirement inverts to a bound on the un-tuned round-trip
delay:

    tau_u < 1 / (2 delta_nu)

which is 50 ps at 10 GHz. A gain chip contributes `2 n_g L / c` to that budget.
The bound therefore converts directly into a procurement criterion, being a
maximum chip length of about 1900 um at a group index of 3.6 with a 300 um feed.
The rejected part was 2500 um and no grating design recovers it, the denominator
of the inversion having gone negative.

**The bound was available before the search began and was not derived until
after three suppliers had been read.** Had it been derived first, the survey
would have been one arithmetic step per candidate.

Two consequences are general. A requirement that inverts to a closed form should
be inverted before any catalogue is opened, and the resulting bound recorded
alongside the requirement. A catalogue search that ranks candidates on the
figures a datasheet advertises will rank on the wrong quantity, the binding
constraint being the one the supplier had no reason to print.

### T035 — Adopting a real part changes the mask, not only the model

Substituting a gain chip moved five design quantities. Two were expected, being
the facet reflectivities. Three were not.

The part is specified over a wavelength range that excludes the design's
operating point, which moved the operating point, which moved the effective
index, which moved the grating period, which moved the number of periods drawn,
which moved the mask's expected region and net counts.

The part emits at 19.5 deg to its facet normal, its ridge being curved to meet
the facet off-normal. The waveguide on the partner die must be angled so that
the two beams are collinear after refraction across the joint. The angle
inherited from the reference device would have presented the beam 1.56 deg off
inside the semiconductor. **That angle is a drawn polygon.**

The part quotes beam divergences and not mode-field diameters, so the coupling
calculation's partner mode had to be derived by Gaussian far-field inversion,
and it is elliptical where the previous part was declared circular.

**A datasheet is read for what it constrains downstream, not only for the fields
that share a name with a model input.** The three quantities above appear in no
configuration field of the same name, and each reached the mask.

### T036 — A parameter scan is invalid unless every dependent field moves with it

A remedy was found for a missed linewidth target, quantified across a five-point
scan, written up with its table, and then discovered to have the wrong sign.

The chain carries the laser output power in two places. The `dynamics` stage
solves the rate equations and computes it. The `cavity` stage computes the
linewidth from a DECLARED value in the design file. The two are separate fields
reconciled by hand at each revision, and the separation is deliberate: the
stages are independent and neither reads the other.

The scan varied the facet coupling loss. Every row was evaluated against the
same declared power while the computed power fell by 34 % across the scan. The
reported linewidth improved monotonically. Reconciling each row against its own
computed power reversed the result: the linewidth WORSENS monotonically, the
threshold gain falling by 11 % while the power falls by 34 %.

**The two effects oppose and the scan concealed it.** Better coupling raises the
effective mirror, which lowers the threshold gain and lowers the output coupling
in the same step. Nothing in the metric tree flags this. Both numbers are
correct; only their combination is meaningless.

Three rules follow.

Before scanning a parameter, enumerate every field that is a manual copy of a
computed quantity, and check whether the scanned parameter reaches it. Where it
does, the scan must re-declare that field at each point or the comparison is
between different designs.

Where two stages hold the same physical quantity, the divergence is to be
printed at every run rather than checked at revisions. A field that must be
reconciled by hand will be stale for most of its life.

**A result that arrives in the convenient direction earns more scrutiny, not
less.** This one was written into a design report before it was checked.

### T037 — Killing a process does not kill what it launched across a boundary

A long solve was cancelled because its geometry had been superseded. The
cancellation removed the orchestrating process on the Windows side. **The solver
itself continued**, because it runs inside WSL as a subprocess and the kill did
not cross that boundary.

It ran for a further three hours and forty minutes on a geometry no longer part
of any design, taking about 40 % of the machine from the run that replaced it.
Nothing reported this. The orchestrator was gone, so no log was being written;
the run directory it was writing into belonged to a cancelled run that nobody
was watching; and the surviving process appears under neither the Windows
process table nor a search for the solver's own name, being a `python`
invocation of a module.

Three practices follow.

After cancelling any stage that shells out, confirm the child is gone on the
side it actually runs on, not on the side the cancellation was issued from.

**A quiet working directory is not evidence of a hung solve, and it is not
evidence of a stopped one either.** This chain's external solver writes its log
only on completion, so a live solve and a dead one look identical from the
filesystem. The process table is the only evidence, and it must be consulted in
the right namespace.

When a solve runs longer than its historical cost, check for contention before
concluding the problem is the solve. Two solvers sharing fourteen cores is
indistinguishable from one solver on a harder problem, from the outside.

### T038 — Two launches of one job, and a log that could not reveal it

A band-structure solve was launched, the launch appeared to fail, and it was
launched again. Both ran. They shared the machine for thirteen hours, each at
half throughput, against a solve that takes four hours alone.

The first launch had worked. What failed was the command that read its log two
seconds later, before the file existed, and that failure was read as the launch
having failed rather than as the check having been premature.

**Both invocations redirected to the same log path.** The second truncated the
first on open and the two then interleaved, so the file could not show that two
runs existed. The only evidence was two run directories twenty-two seconds
apart, and the process table.

Three practices follow, and the first two are already lesson T037.

Confirm a launch by the artifact it creates, which is a run directory, and never
by a log file read immediately afterwards. A process that has started has not
yet written anything.

Where a job may be long, give each invocation its own log path. A shared path
cannot record a duplicate; it conceals one.

**Before relaunching anything, look for what is already running.** The cost of
the check is one command. The cost of skipping it was thirteen hours, and it has
now been paid twice in one session.

### T039 — A band gap is a hard thing to compute, and for two separate reasons

Measuring a grating's coupling constant from its photonic band structure failed
on this design after twelve hours. The two causes are independent and both are
worth knowing before the method is chosen again.

**Discretisation.** The gap is 1.5e-5 of the band frequency at the design's post
gap. The mesh places twelve pixels across a 0.30 um post, and staircasing that
edge perturbs the geometry by more than the gap can absorb. Halving the mesh
halved the answer, so the measurement carried no information.

**Eigenvalue separation.** The gap IS the separation between two nearly
degenerate eigenvalues. An iterative eigensolver converges at a rate set by that
separation, so a small gap is slow to resolve by construction. The solve was
still running at iteration 1213 with the trace changing by 1e-4 per cent.

Widening the post gap fixes the first and does nothing for the second, which is
why moving to a stronger grating did not rescue the method.

**Where the quantity of interest is itself a small difference between two large
computed numbers, the cost of resolving it rises faster than the signal.** A
time-domain reflectance measurement is better conditioned on both counts, its
signal being a ratio of fluxes of order unity rather than a difference of
eigenvalues. It costs its own hours, and the estimate must be made before the
run rather than after: this one was scoped at 6 h against a true need nearer 35.

### T040 — Where a grating feature sits decides whether the coupling is usable

An extended-DBR laser was constrained by its electrodes. The metal must stay
2 um clear of anything on the waveguide layer, and the Bragg posts sit 1.8 um
off the guide axis, so the electrodes were held 7.7 um apart and the tuning with
them. Moving the grating feature INTO the ridge, as a periodic widening rather
than as islands beside it, frees the metal to 5.3 um and raises the tuning by
51 %.

It was built and measured. The tuning rose as predicted, to 610 MHz/V. **The
coupling constant rose 105-fold**, from 0.76 to 79.8 /cm, because the
perturbation moved from the tail of the mode into its centre. The penetration
depth is 1/2kappa at strong coupling, so it collapsed from 5.6 mm to 63 um,
taking the Pockels lever with it. Linewidth went from 4.5 to 52.5 kHz and
side-mode suppression from 46 to 7 dB.

Weakening it back is not available. kappa scales with the corrugation depth, so
0.76 /cm needs 1.4 nm of corrugation. Sitting near the Fourier zero of the third
harmonic instead needs the duty cycle held to 0.09 %, which is 1.2 nm on the
feature. Both are below lithographic control.

**The slab-coupled post grating is not an arbitrary choice.** Placing the
feature outside the mode is what makes the coupling weak enough to give a long
penetration depth, and weak coupling is what an extended-DBR laser is for. The
same placement is what forces the electrodes apart. **The geometry that frees
the electrodes forbids the coupling the architecture requires**, and no
parameter reconciles them.

Two general points follow. A perturbation moved from the evanescent tail to the
mode centre changes strength by two orders of magnitude, not by a factor;
proximity to the field is the dominant term. And where an architecture appears
to be constrained by a rule, check whether the constraint and the function share
a cause before designing around the rule.

### T041 — Measure where the signal is, not where the design is

Two attempts to measure a grating's coupling constant failed at the design
point: a band-structure solve that did not converge, and a time-domain solve
that exhausted six hours. The band gap there is 1.5e-5 of the band frequency,
below the mesh error and slow to resolve as two nearly degenerate eigenvalues.

The measurement succeeded at a different geometry. kappa falls exponentially
with the post gap, so a gap 320 nm narrower gives 5.8 times the coupling and
5.8 times the band gap, while the mesh error stays where it is. The convergence
guard went from 99 % of the effect to 12.5 %, and the ratio of measured to
closed-form kappa came out at 0.6705.

**The quantity of interest was not measured at the design point, and the
transfer carries an assumption**, namely that the ratio does not vary with the
gap. That assumption is stated rather than buried, and it is testable: the
unconverged measurement at the design point agrees to 2.7 %, while the theory
argues the ratio should approach unity as the feature moves away from the mode.

The general practice: where a measurement is ill-conditioned at the point of
interest, look for a related point where the same quantity is well conditioned,
measure there, and carry the result across with the transfer assumption written
down. **A converged measurement of a neighbouring case with a stated assumption
is worth more than an unconverged measurement of the exact case.**

### T042 — Two numbers for one quantity, and the comfortable one was believed

The chain reports the mode-hop-free range twice: measured from the swept cavity,
and from the closed form `r/(1-r)*FSR/2`. On a released tantalate design they
read 6.34 GHz and 13.78 GHz. **The factor of 2.2 was attributed to thermal comb
placement and written into the design report as a commissioning matter.** It was
not the whole story, and the correction that replaced it was wrong in its turn.
Both are recorded below, because the second error is the more instructive.

The consequence was not merely a mis-explained number. The two figures are
anti-correlated through kappa, so **two weeks of tuning aimed at the closed form
moved the design away from the tuning range it was meant to buy.** Reverting one
parameter to a value already on the mask raises the achieved range from 6.34 to
10.32 GHz and the tuning slope from 196 to 313 MHz/V.

Three failures compounded, and each is general.

**A disagreement was excused rather than quantified.** Rule 8 of the operating
manual requires a model and a measurement that disagree to be stated and
quantified. That rule was applied to kappa, where the disagreement was 1.49 and
was measured, converged and recorded without being tuned away. It was not
applied here, where the disagreement was 2.2. The rule was followed where a
measurement was already in hand and set aside where following it meant starting
one. **A rule obeyed only when it is convenient is a preference.**

**A plausible cause was accepted without being tested.** Comb placement does
move the zero-bias figure, that is real, and skill entry 15 documents it. It
explained the observation, so the search stopped. The test that would have
settled it costs three runs of five stages, which is what finally settled it.
**An explanation that fits is not an explanation that was checked, and the cost
of checking is the thing to weigh, not the plausibility.**

**A recorded lesson was wrong and was followed anyway.** Skill entry 16 said
kappa moves the reflectivity, the bandwidth and the tuning range "together". It
moves the achieved range opposite to the other two. The entry was written from a
design where the ceiling happened to bind, generalised from that single case,
and never re-tested. **A lesson generalised from one design carries the
conditions of that design, and the conditions are the part worth writing down.**

The guard now in place: `cavity.mode_hop_free_range_stopband_bound` compares the
two figures and warns when the achieved range falls below three quarters of the
closed form, naming the stop band as the binding constraint and stating the
direction to move. Two tests in `test_laser.py` hold the anti-correlation and
the presence of the warning.

**The transferable rule. Where a chain reports the same quantity by two routes,
the disagreement is the finding.** It is not to be narrated, attributed or
averaged. Where the two are known to be anti-correlated in some parameter, the
binding one is to be identified before that parameter is chosen, because
optimising the slack one is worse than not optimising at all.

### T043 — The correction that was itself a spurious correlation

T042 replaced a commissioning explanation with a physical one: that the achieved
mode-hop-free range is bounded by the mirror stop band at about 1.25 times its
FWHM. The ratio held at 1.13 to 1.34 across five post gaps, which looked like a
law.

**It was a coincidence of the parameter being scanned.** Both the stop band and
the achieved range vary smoothly with the post gap, so scanning that one knob
produced a tight ratio with no causal content. Scanning a different knob broke
it immediately: at three feed lengths the same ratio read 1.32, 1.95 and 1.83.

The decisive test cost two runs. **Perturb an optical path by a fraction of a
wavelength, holding every optical property fixed, and see whether the metric
moves.** Moving the feed by 200 nm moved the hop from 51.6 V to 9.6 V and left
the stop band at 7.492 GHz. The swept range carries the cavity phase, which is
the round-trip path modulo one wavelength, and no process holds a 17 mm cavity
to 200 nm. The original commissioning explanation was nearer the truth than the
physics that displaced it.

**A correlation observed along one axis is not a law.** T042 warns against
generalising a lesson from one design; this is the same error one level down,
generalising from one parameter of one design. The guard is to vary a second,
unrelated parameter before writing the relationship down.

**What replaced it.** Four phase-independent quantities, each derived rather
than fitted, from the mode's slip relative to its own mirror at `(1-r)*S`:

    drift       = (1-r) * S * V_max
    hops        = drift / FSR
    placed      = eta * V_max
    guaranteed  = placed / (ceil(hops) + 1)
    containment = drift / FWHM

A requirement is written against `placed` and `containment`. The swept figure is
retained at `info`. On the design in question the swept figure spread 125.5 %
across a process window on which these spread 14 %.

**A second defect concealed the first.** The corner verdict evaluates only the
metrics named in `corners.metrics`, so a `must` row absent from that list passes
every corner unread. Two new `must` rows were added to the targets and not to
that list, and the sweep reported 9 of 9 while the failing row was never
evaluated. It returned 4 of 9 once they were added. **A pass on a list that does
not contain the row is not a pass**, and the two lists are now edited together.

### T044 — A check that ran is not a check that could have failed

A lithium tantalate design was drawn on the lithium niobate stack's layer
numbers and checked against the niobate rule deck. It returned zero violations,
ten of ten release conditions and a released manifest. **Every foundry-deck
result it carried was obtained against the wrong process.**

The two runsets come from the same foundry and are near-identical in rule
values. They differ in the numbers that decide what gets read:

    layer     LN-CORE     LT-PRO
    RIDGE     2 / 0       2 / 10
    SLAB      3 / 0       3 / 10
    M1        21 / 0      20 / 0

**The metal move is the one that would have passed silently.** Pointing the
correct deck at the existing mask would have found layer 21/0 unread and every
metal width and spacing rule evaluated against an empty layer, reporting clean.
Correcting the deck without correcting the layer map produces a worse result
than either error alone, because it looks right.

This was not an isolated slip. Every error of the session had one shape.

| the green result | what was never established |
|---|---|
| deck: 0 violations | that the deck was this process, and its layers carried geometry |
| corners: 9 of 9 | that the `must` rows were in the evaluated metric list |
| linewidth computed | that the power it used was the power the design produces |
| a ratio held across a scan | that it held across a second, unrelated parameter |

**In each case the instrument was confirmed to have run and never confirmed to
be capable of returning a failure.** The operating manual already carried the
rule, at "before trusting either, confirm it detects a violation deliberately
introduced". Reading it was not enough.

**The practice.** Before a passing result is accepted, name the failure it would
have caught and establish that it could have caught it. Three mechanical forms:

* **Coverage.** For every check that reads geometry or metrics through a named
  list, report what the list resolved to and what it did not reach. `drc.deck`
  now reports the layers a runset names and which of them carry no polygon, and
  warns that rules on an empty layer cannot have failed. `corners` now adds any
  `must` target missing from `corners.metrics` and announces the addition.
* **Provenance.** A file that encodes a process, a deck or a layer map, is to be
  checked against the platform the design declares. Two files from one foundry
  differing only in datatype will not announce the mismatch.
* **Falsification.** Where a check can be made to fail on demand, make it fail
  once and confirm it says so.

**The general rule: a passing check is evidence only in proportion to its
demonstrated ability to fail.** A green result whose failure mode was never
established is not weak evidence; it is no evidence.

### T045 — The stage list is not the physics, and the absent model is the risk

An external reviewer, reasoning from the device rather than from the metric
tree, raised in one pass three risks that many hours of tool-driven work had
not: out-of-plane radiation from a third-order grating, phase coherence over a
17 mm mirror, and a stale coupling figure. One was inverted, but two were real
and one was dominant.

**The dominant one was invisible to every instrument the chain had.** The Bragg
condition follows the effective index, the index follows the film thickness at
1.38e-3 per nm, and the whole 6.4 GHz stop band corresponds to a twentieth of a
nanometre of film. The mirror tolerates 0.117 nm of non-uniformity before the
Bragg phase slips by pi over its 4.89 mm penetration depth; thin films are
specified at one to two per cent of 300 nm, which is 25 to 50 times that.

**The corner sweep could not see it and reported comfort instead.** It moves the
film thickness uniformly, which shifts the Bragg wavelength and leaves the
grating perfectly coherent. A gradient along the mirror is a different failure,
and a parameter the chain models as a scalar cannot fail by varying. Eighty-one
corners on film thickness were run and the comfortable answer was accepted at
the framing the tool supplied.

**Why it was missed, precisely.** The working method audited what the chain
reports: every number traced, every check tested for its ability to fail
(T044). It never asked what the chain omits. Radiation was framed as "kappa is
uncertain" because kappa is what the chain computes, when the true statement
was "a loss channel exists with no model at all". Attention followed the metric
tree, and absence has no metric.

**The countermeasure is a written omissions audit, from the device.** At review,
walk the physical object end to end - film, etch, grating, electrodes, facet,
assembly - and for each element ask what mechanism could degrade it and which
stage models that mechanism. Where the answer is "none", the finding is not a
smaller number but a missing instrument, and it is to be stated as such: as a
budget where a bound exists (radiation against the threshold-gain margin), as a
new measurement where one does not (a stepped-length grating ladder, which
departs from tanh^2(kappa L) when phase is lost and which a stepped-gap ladder
can never reveal, every copy sitting on the same film).

**A scalar parameter models a quantity as uniform, and that is itself an
assumption.** Film thickness, etch depth and sidewall angle all vary along a
device the chain treats as a cross-section times a length. For any device long
compared to the scale of process variation, ask what the gradient does, not
only what the level does.

### T046 — A guard added in haste failed twice, in opposite directions

A `must` target absent from `corners.metrics` passes every corner unevaluated,
because the corner verdict iterates that list. The guard added for it appended
every absent `must` row to the sweep.

**The corner stage list is derived from the metrics.** Adding `drc.error_violations`
and `layout.mask_is_complete` therefore pulled `layout` and `drc` into a physics
sweep, and every corner then failed on rows a corner cannot move: a perturbation
of film thickness does not change whether the mask is complete. Twenty-four of
twenty-four corners failed for a structural reason.

The correction restricted the addition to targets whose stage the sweep already
runs. That was still wrong, more quietly: reachability was tested against the
stages the declared metrics *name*, when `mode` runs as a dependency of
`grating` whether or not any metric names it. `mode.n_guided_modes` was
reported unreachable while being perfectly evaluable. Reachability is the
resolved stage closure, not the declared set.

**One guard, three versions, two wrong.** The first was wrong by adding too
much and failed loudly. The second was wrong by adding too little and failed
silently, which is the same failure the guard was written to prevent.

**What to take from it.** A guard that changes what a sweep evaluates also
changes what it costs and what it runs, and those consequences are not visible
in the guard. Before adding a metric to a sweep, ask what stages that metric
drags in and whether the sweep's parameters can move it at all. A metric a
corner cannot move does not belong in a corner sweep, whatever its severity:
the honest treatment is to name it as unevaluated and say why, which is what
the third version does.

**The general rule: a check is scoped to the perturbation it is checking.**
Requirements that a sweep's parameters cannot reach are reported as out of
scope for that sweep, not forced into it and not silently dropped.

### T047 — A compensator that is inside the thing it compensates

An intracavity phase section removes the mode hop by driving the cavity comb in
step with the mirror. The phase it must supply is the mirror-to-comb slip, and
because `(1-r)*tau_rt = tau_u` exactly, that reduces to

    phi_needed = 2*pi * tau_u * S * V_mirror

**The grating cancels.** Measured across four post gaps, reflectivity 0.93 to
0.80 and stop band 10.05 to 6.84 GHz, phi_needed held at 2.455 rad throughout.
That is a genuinely useful invariant: the compensator is sized once and any
mirror goes behind it, so it is designed first and the grating follows.

**And then it defeats itself.** The section is passive cavity length, so its own
delay enters `tau_u`, which is exactly what sets the phase it must supply. A
1500 um section was accepted against 2.455 rad; with its own 20.6 ps counted the
requirement is 4.025 rad and the same section is short. Solving self-
consistently, the length diverges as the denominator closes, and at a phase
drive equal to the mirror's it ran to 3583 um and did not fit the die.

**The escape was an axis the compensator did not share with its own load.** Its
drive is separate from the mirror's, so raising it lifts what the section
supplies without lifting what it must supply. 900 um at 55 V against a 25 V
mirror left 15 % margin where 25 V needed four times the length.

**The general shape.** Where a compensator sits inside the loop it corrects, its
own contribution belongs in the requirement before the sizing is believed. Ask
what the compensator adds to the quantity that drives its requirement, and solve
for the fixed point rather than the first pass. Then look for a parameter that
enters its capability but not its load; without one the sizing may not converge
at all.

**A second effect, easy to miss.** A compensator often displaces something. This
section is passive delay, and a feed had been lengthened for exactly that
property to buy linewidth. The feed was then costing tuning for a benefit
already supplied, and returning it recovered the Pockels lever from 0.547 to
0.631 with the linewidth better than before. **After adding a component, re-ask
what every earlier compromise was bought for.**

### T048 — The metric graded the mechanism the design had removed

An intracavity phase section was added so the mode comb could be driven in step
with the mirror. The device was then graded on `mode_hop_free_range_placed_GHz`,
which is the excursion of a cavity whose comb is left to slip. The section is
passive delay, so it lowers the Pockels lever and lowers that excursion. On that
row the new architecture read 8.41 GHz against 11.22 for the design without a
section, and 17 of 81 corners failed where the other failed none.

**The row was measuring the mechanism the section exists to remove.** With both
electrodes driven the laser follows the mirror one for one and no hop occurs:
12.11 GHz continuous, against 5.61 GHz guaranteed and one hop to hand over on
the design it replaces. The conclusion reversed completely on changing which row
carried the requirement.

**A model defect kept it hidden.** The synchronous figure was computed as
`eta*V_max` using the mirror-only `eta`, understating it by exactly the lever and
returning 8.41 GHz, the same number as the mirror-only row. Two rows agreeing
exactly is a signal, and it was read as corroboration rather than as the
duplicate it was. The figure now comes from a second mode-tracking sweep with the
section's phase applied to the round trip.

**What was checked before believing the correction.** The corrected rate is
484.20 MHz/V against the mirror's 484.19 MHz/V, and the two are reached by routes
that share no step: differentiating the resonance condition in closed form, and
finding roots of a non-monotonic phase on a grid. The design without a phase
section was re-run and every cavity metric held to 4e-10, so the refactor moved
nothing it should not have.

**The general shape.** A target encodes a mechanism as well as a number. Where a
design replaces the mechanism, the target stops testing the requirement and
starts testing the absence of the change. Ask of every `must` row which mechanism
it assumes, before concluding that a new architecture is worse. Then keep the old
row at a lower severity, because it usually describes a real degraded mode: here
`placed` is what the device delivers if the phase drive is lost.

**Related:** T043, where a metric was trusted because five runs agreed and the
agreement was a coincidence of one parameter. Both are failures to ask what a
number is a number *of*.

**THE COUNTERMEASURE, ADDED 2026-08-17.** Recording the lesson was not enough,
because the defect is invisible to rereading: each document stayed internally
consistent and only the relation between them was wrong. Every design now carries
a `DESIGN_CONCEPT.md` stating what the device does, by what principle, and which
quantity expresses each clause of that principle. It ends in a trace table
binding each clause to the target that tests it, and
`design-chain/tools/check_concept_trace.py` compares that table against the
declared targets, reporting a target the concept does not ask for, a clause no
target tests, and a severity disagreement. It is exercised by two tests, one over
the designs in the tree and one on a constructed design carrying exactly the
inherited-target defect. The obligation is in rule 16 of the operating manual and
in the reference manual under "The Concept of Operation".

**The order matters and is the point.** The concept is written first, the targets
are derived from it, and the validation is then evidence about this device rather
than about the one before it.

### T049 — The published figure is not the run's figure, and a picture cannot be proof-read

Two designs were re-run to a new operating point. Every number in their reports
and in the review deck was traced to the new runs and corrected. **The figures
were not**, because a design's `figures/` directory is a hand-made copy of
`runs/<id>/figures/` and nothing refreshes it.

The deck therefore showed fourteen pictures of an earlier device, among them the
electro-optic field across an electrode gap that had since been narrowed by 15 %,
and a tuning curve captioned with a drive voltage retired twice over. Two further
figures had been captured by hand from the layout viewer and showed a device
ladder reset later the same day; nothing in the repository could regenerate them.

**Why rereading does not catch it.** A number carries units and can be checked
against a run. A figure carries neither units nor a run identifier, so a stale
one is indistinguishable from a current one at a glance, and it is the artifact a
reviewer trusts most. The existing habit "open a figure before citing it" is
necessary and insufficient: opening the figure shows what it depicts, not which
design it depicts.

**The countermeasure is a hash comparison, not a habit.**
`design-chain/tools/check_figures_current.py` compares each published figure with
the one the run of record wrote, reports the differences, and copies them across
with `--sync`. It separately lists figures no stage produces, which are the ones
nothing refreshes and therefore the ones to watch. Each design now carries a
`figures/README.md` giving the command that regenerates every unmanaged figure,
so unmanaged does not mean unreproducible.

**A figure drawn beside a numerical model should read the model's own arrays.**
The tuning curve was redrawn from `cavity.npz` rather than from the reported
slope, and the cavity stage was extended to store the second mode track so the
figure shows a measurement instead of a line inferred from a number.

### T050 — One snapshot of a process table is not a measurement of a job

An external solver was checked with `ps` sorted by processor use. It listed
nothing, and the conclusion drawn was that the job had died. It had not: eight
MPI ranks were sitting in a barrier at that instant, and the job was twenty-six
minutes into a solve that had hours of its timeout left.

**A parallel job is idle at every synchronisation point**, so an instantaneous
view of processor use samples a duty cycle rather than a state. The report was
nearly published as a failure.

**Ask the process table for identity and elapsed time, not for load.** Matching
the command line and reading `etime` answers whether the job exists and how long
it has run, and neither depends on catching it between barriers. Where the
solver is reached through another environment, query inside that environment: on
this platform the ranks are invisible to the host process list and appear only
under WSL.

This is the concrete case behind the standing rule that slow is not stuck and
unfinished is not failed. Every misdiagnosis of this chain's health so far has
come from treating an absence of evidence as evidence of failure.

### T051 — Ninety warnings, and nothing read them

The chain raises warnings from ninety call sites across seventeen stages. Until
2026-08-17 **no code read the list**: not `verify`, not `release`, no tool. A run
could emit seventeen findings, several material, and still be reported a clean
pass, because the acceptance verdict grades targets and the warnings sit in a
file nobody opens.

The inventory, once taken, held 33 findings across two designs and 0
acknowledged. Among them: a mask whose connectivity tripwire had been firing on
four counts against a released design; a layout that had silently redrawn the
cavity on four devices of a die; and a circuit stage assembling a device that was
not the design.

**The acceptance verdict is not a summary of the run.** It is a summary of the
targets, and the gap between those two is exactly where a finding with no
threshold lives. A design has three kinds of statement about it, and only the
first was gated: a quantity with a bound, a finding with no bound, and a channel
not modelled at all.

**Silence must fail, not pass.** A warning with a stable key can be acknowledged
in the design file with the reason it is accepted, and a run can then fail on any
finding not acknowledged. The property that matters is not the acknowledgement of
the known findings; it is that **a newly appearing warning breaks the run**,
which is what catches the thing nobody anticipated.

### T052 — A clamp turns a modelling failure into a passing check

A circuit stage computed the straight guide as the feed minus twice the taper
length, against one taper instance in its own netlist. On a long feed the error
was invisible. On a 210 um feed carrying a 150 um taper it went negative, a
`max(..., 1.0)` returned 1 um, and the stage assembled a cavity with no feed at
all. Every figure it produced described a different device.

**Its own cross-check then passed.** The group delay agreed with the expectation
to 0.3 %, because the expectation was computed from the same clamped value. The
sibling design, whose arithmetic did not go negative, disagreed by 11 % and was
the one that looked wrong. **The design with the worse defect produced the better
number.**

**A clamp is a confession.** It exists because the author knew the value could be
impossible and chose to continue anyway. Every clamp on a declared quantity is
therefore a precondition that was written as a rescue, and it should raise before
the run rather than repair silently during it.

The general check: search for `max(`, `min(`, `or default`, and every silent
fallback on a value that came from the design file. Ask what input makes the
fallback fire, and whether that input should have reached a solver at all.

### T053 — A precondition asserted from a guess is worse than none

The first version of the preflight module asserted that an intracavity phase
section had to fit inside the feed, and failed a design that was correct. The
layout draws the section *after* the feed as its own length, and the cavity
carries its delay in a separate term. The check had been written from an
assumption about the geometry rather than from the code that draws it.

A second check in the same module used the taper length where the binding
quantity was the lead-in path, which is longer: 203.2 um against 150. It passed a
design that was in fact violating the condition.

**A gate that fails correct work trains the reader to bypass the gate**, and a
gate that passes incorrect work is worse than absent because it is trusted. Both
were caught by reading the code that establishes the relation instead of
believing the tool that had just been written.

Two rules follow. **A precondition names the code path that establishes it**, so
the relation can be checked against the thing it constrains. **A check that needs
a computed quantity belongs in the stage that computes it**, not in a
precondition that reconstructs the arithmetic, since a reconstruction is a second
implementation and will diverge.

### T054 — A checker whose pattern is narrower than the thing it checks

The metric tree is walked to any depth, so a stage that groups a sub-system into
its own payload produces a name of three segments rather than two. The
concept-trace checker matched exactly two, and a target written against such a
quantity was reported as declared and absent from the concept while the concept
named it on the line above.

The remedy the tool implied was to flatten the metric name until the checker
could read it, which repairs the design to suit the instrument. The two new
targets it rejected were the two carrying the architecture, so the alternative
was to leave the mechanism ungraded.

**A checker's accepting grammar is to be as wide as the thing it reads.** The
test is to take one existing artifact, extend it in a way the producing code
already permits, and confirm the checker still reads it.

This one failed in the tolerable direction, naming the metric it could not find,
so the defect was visible within one run. The same narrowness applied by a
checker that skipped an unmatched row would have returned a clean pass on an
untraced target, which is the defect the checker exists to catch.

Enforced by `test_the_concept_checker_reads_a_nested_metric_path`, which traces
a three-segment path and then confirms the checker still fails on an untraced
one at the same depth.

### T055 — A material constant that is declared, gated and never enabled

Measured thin-film indices replaced bulk congruent values in the material
library, the provenance was rewritten to record the measurement, a design
document reported the replacement, and a release gate reported the material data
as confirmed. Every solve continued to evaluate the bulk fit.

The values sit behind a per-design flag that defaults to off, and no design in
the repository had ever set it. The library is therefore correct, the flag is
correct, the gate is correct, and the number reaching the solver is the one the
work was done to replace.

Three properties made it invisible. The library entry reads as adopted, because
adoption and consumption are separate acts and only the first is visible in the
file. The provenance string describes the measurement rather than its use. The
release condition tests whether a material is tagged as needing confirmation,
which is a statement about the tag and not about the value that was read.

Measured on one shallow-etched thin-film cross-section, enabling the flag moved
the bare effective index by +1.18 %, the electro-optic overlap by +2.46 %, the
mirror tuning by +4.56 %, and the grating index perturbation by **−19.3 %**. The
last is the quantity that sets the coupling constant, so the mirror, the
penetration depth, the tuning lever and the linewidth all move together, and the
Bragg wavelength moves by 1.18 % and requires the period to be re-solved.

**The practice. A constant is adopted when a run consumes it, and the run is the
evidence.** After changing a material value, re-run one stage that depends on it
and confirm the reported quantity moved. Where the reported quantity is unmoved,
the value is declared and unused.

**A gate that reads a tag has not read a value.** A provenance check establishes
that somebody recorded a source. It establishes nothing about which number the
solver evaluated, and the two are to be reported separately.

A related expectation was also wrong and is recorded because the reasoning was
plausible. The override returns one value at every wavelength, so the film
contributes no dispersion when enabled, and the group index was expected to
collapse toward the effective index. It rose by 0.75 %. The waveguide and
cladding dispersion carry the group index on this cross-section, and the film's
material dispersion is a small part of it. **An expected consequence is to be
measured before it is reported**, including where it is being reported as a
reason not to act.

### L021 — A process window states which excursions the sweep can represent, and the rest read as insensitive

A factorial corner sweep declared four excursions, one of them a lateral
dimension of a grating feature, annotated as lithographic critical-dimension
control. The features and the guide beside them are drawn on one layer and
printed by one exposure and one etch, so a lithographic excursion moves the gap
between them and their own dimensions together. Displacing the gap alone is a
translation the process cannot deliver.

Replacing it with the process bias, which grows a width by the full bias and
shrinks a same-layer gap by the same amount, changed three things at once on one
design.

**It exposed a `must` row that had never failed.** The guided-mode count reached
two against a ceiling of one, at positive bias combined with a deep etch, in five
of eighty-one corners. The previous window moved no dimension of the guide, so
that row returned one at every corner and read as insensitive. It was the
second-tightest requirement in the design.

**It withdrew a `should` failure.** The linewidth had been reported as exceeding
its bound at nine corners. On the corrected window it is met at every corner.
Those nine were produced by an excursion the process does not deliver.

**It narrowed a spread that had been quoted as a risk.** The coupling constant
had been reported as spanning 63.6 % across the whole window and spans 46.4 %.
Isolated to the lateral parameter alone, with the film, the etch and the
sidewall held at nominal, the two excursions measure:

    post gap alone      kappa 1.0477 .. 0.8480 /cm    span -21.2 %
    process bias alone  kappa 0.9092 .. 0.9558 /cm    span  +4.9 %

**The gap-only excursion overstates the sensitivity by a factor of about four
and reverses its sign.** The response to bias is asymmetric, kappa rising 1.4 %
at +20 nm and falling 3.5 % at -20 nm, the duty term growing faster than the gap
term across the span.

**An estimate made before the sweep predicted the net at under one per cent, and
the measured figure is 4.9 %.** The cancellation is real and its magnitude is not
obtainable from the two terms evaluated at a single point, their curvatures
differing. **A predicted consequence is not a finding until the sweep has been
run**, and it is not to be reported as one.

**The transferable rule. A corner parameter is a quantity the process varies, and
not the geometric field that quantity happens to reach.** Where a chain offers a
parameter representing the process displacement itself, that parameter is the
correct corner input, because it moves every dependent dimension coherently and
in the right direction.

Two corollaries. **A metric that is flat across a window may be insensitive or
may be unreachable by that window**, and the two are distinguished by asking
which declared excursion moves it. **A pre-compensated bias is a no-op on the
printed geometry** by construction, so an excursion on it is taken with
pre-compensation off and represents the residual the process leaves.

Recorded in `rules/generic/parameter-scans.md`. The chain warns where a window
varies a drawn dimension without varying the process bias.

### L022 — A model correction can be applied in place, and then it is measured rather than argued

A coupled-mode coupling constant was measured against a band structure and found
to be overstated by a factor of 1.49. The consequence for the design was
described by extrapolating a corner sweep, because the correction is a statement
about the model and the geometry that produced it had not changed.

It can be applied in place. The longitudinal profile smoothing scales the
harmonic amplitude and touches nothing else, so setting it to the sigma that
realises the measured ratio reduces kappa by exactly that factor while the
cross-section, the effective index, the group index, the electro-optic overlap
and the mirror tuning stay where they are. One run then reports the whole metric
tree at the corrected value.

**The check that the lever reached only the intended quantity is the Bragg
wavelength**, which came out unchanged to seven figures. A lever that moved the
geometry would have moved it.

The measurement agreed with the extrapolation on the two quantities that had
been extrapolated and disagreed on one that had been estimated earlier: the
reflectivity fell to 0.543 against an estimate of 0.626. It also supplied two
figures that had been left unstated, the threshold gain and the side-mode
suppression, and confirmed three invariances that had been argued analytically.

**The smoothing is a lever and not a claim about the etch**, and the distinction
is to be written beside the number. A correction realised through a modelling
parameter is recorded as such, so that it is not later read as a measured
property of the process. See T026.

**The general practice. Where a correction is a statement about a model, look
for a parameter that realises it without moving the geometry, and run it.** A
metric tree at the corrected point costs one run and replaces every
extrapolation drawn from it.

### T056 — A guard added to catch a silent defect, and its first run raised

A finding was added to a stage so that a declared and unconsumed material
constant could not pass unnoticed again. The guard read the platform through a
local name bound in a different function, so the stage raised on its first
execution and the run terminated at the first of sixteen stages.

Two properties made it cheap rather than expensive, and both are worth keeping.

**The stage raised rather than returning a wrong number**, so the run reported
`status=failed:mode` and produced no manifest. A guard that had instead
evaluated to false under the same error would have shipped a run in which the
finding could never fire, which is the condition the guard exists to detect.

**The failure was in the guard and not in the physics**, so nothing downstream
had to be re-examined. A guard is to be written where it can see only what it
needs, and exercised once before it is relied upon.

**A guard is to be made to fire before it is trusted.** The corrected guard was
executed directly against the design that motivated it, and its finding key was
compared against the acknowledgement written for it. Those are two separate
checks: that the condition is detected, and that the name it is detected under
is the name the design file acknowledges.

A second defect, in the invocation rather than the chain, concealed the first
for one cycle. The run was launched as a pipeline into `tee`, and the exit code
captured was the pipe's last element rather than the chain's, so a failed run
reported success. **Where a command's exit code is the branch condition, it is
read from the command and not from a pipeline built around it**, through
`PIPESTATUS` or `set -o pipefail`.

### L023 — A bound is declared once and may govern more than one structure

A design carried two electrode pairs at different gaps. The metal-overlap bound
existed because metal loss is not recoverable, and the acceptance row evaluated
it at the mirror electrode, where it passed by three orders of magnitude. The
second pair sits at a gap 40 % narrower and exceeds the same bound by a factor of
6.7. The metric tree showed one number and gave no indication which structure it
described.

Measured on one shallow-etched thin-film cross-section, the mode overlap with
metal rises from 6.9e-8 at a 6.62 um gap to 6.7e-5 at 4.00 um, against a bound of
1e-5. The decay is exponential at d(ln overlap)/d(gap) = -2.61 /um, so the gap
that restores a given bound is a short calculation, and a section whose length
scales with its gap lengthens in proportion.

**The practice. For each bound, enumerate the instances of the thing it
constrains, and confirm the metric was evaluated at each.** Two electrode pairs,
two waveguide widths, two grating sections, two facets. Where a chain reports one
value, establish which instance it describes before the row is read as met.

A second finding came from the same run and it corrects a conventional
expectation. **The electro-optic overlap does not necessarily fall as the
electrode gap closes.** On a high-permittivity film the radio-frequency field is
drawn into the film, so a tighter gap concentrates it where the mode already is:
Gamma rose from 0.2473 at 6.62 um to 0.2619 at 4.00 um. A chain that rescales the
index change per volt from one electrode to another by the inverse gap ratio is
asserting a common Gamma, and that assertion was conservative here by 5.9 %. It
is not conservative by construction, and the electrode solve at the second
geometry costs one run.

Recorded in `.claude/skills/eo-electrode-design/SKILL.md`.

### T057 — A guard written for the wrong one of three outcomes

A drawing routine reports its outcome three ways: it returns a path, it raises,
or it returns None. Six of nineteen drawings were lost from a run of record, and
a guard was added to record the failures. It covered the raising case.

**The outcome that had actually occurred was the third one.** The next run lost
the same six drawings, wrote no failure record and raised no finding, because
every one of them had returned None. The guard was correct, tested against the
mechanism it was written for, and blind to the mechanism in front of it.

The tell was available and was not read. The first run had produced no
`figures.failed.json` while six figures were missing, which says directly that
nothing raised. That was visible before the second run was started.

**The practice. Enumerate a routine's outcomes before guarding one of them.** For
a function returning an optional value the outcomes are at least three, and the
quiet one is the likeliest to be the live defect precisely because it produces no
symptom to reason from.

**A silent no-result is distinguished from a legitimate one by the input, not by
the routine.** A renderer returning None is correct where the stage feeding it
did not run, and is a failure where that stage's payload is present. The guard
now looks for the payload rather than trusting the return.

Falsified in both directions before it was relied upon: a renderer forced to
return None with its stage payload present is reported and writes the record; the
same renderer with the payload removed is not reported.

The root cause of the loss itself is unresolved. Every one of the six renders
correctly when called again on the same run directory, which points to a resource
condition during the run rather than to the drawing code. **The loss is now
reported, which is the property that was missing.**

### T058 — A slide that overflows is clipped, and nothing says so

A review deck was edited across several sessions. Twenty-three of its
sixty-nine slides held more content than a 16:9 frame at the declared type size,
and the renderer clips silently: the author sees the whole slide in the editor
and the reader receives one whose foot is missing. On a technical slide the foot
is the conclusion.

Three quantities dominate the height and each is checkable before rendering.
**A figure's height is its declared width times its aspect ratio**, and the
aspect is to be read from the file: two figures in this deck differed by a factor
of two in aspect, so one declared width gave 380 px and another 615 px, and only
the second overflowed. A table row costs its font size times the line height plus
its border. Prose wraps, so a source line is not a rendered line.

`tools/check_slide_overflow.py` now estimates every slide against the frame. It
took the deck from twenty-three overflowing to none, by sizing eighteen figures
to the space their slides had left and splitting thirteen slides.

**The check is an estimate and says so.** No renderer is invoked. Its first
version also summed a two-column slide as one column and flagged slides that fit;
**a checker that refuses correct work trains the reader to bypass it**, so the
column case was added rather than the slides being edited to suit the tool.

Recorded as a rule at `rules/generic/slides-and-figures.md`.

### T059 — Two structures on one layer draw in one colour, and a plan view stops distinguishing them

A device carried two electrode pairs at different gaps driving different
sections. The process patterns metal in one lithographic step, so both pairs and
all four bond pads sit on one layer number, and the plan view the chain draws is
coloured by layer. A reader could see that metal existed and could not see which
metal was which, nor which pair drove which section.

The design documents inherited the same blindness. The electrode and bond-pad
slides of a review deck described one pair, having been written for the
single-pair predecessor, and the second pair appeared in no drawing at all.

**A figure coloured by layer shows the process and not the design.** Where two
structures share a layer and differ in function, the drawing is to identify them
by what they are, and the identification is to come from the emitted layout
rather than from the design file, so that it describes the mask.

They are separable without a second layer. On this device the classification is
shape: a bond pad is compact and an electrode is long and thin, so an aspect
threshold divides them and the grouping follows from which pads sit inside which
electrode run. `tools/electrode_plan.py` does that, states each run's length,
gap and pad position, and reports the classification so a reader can check it.

The general practice: **for any layer carrying more than one kind of structure,
ask whether a reader of the drawing can tell them apart.** Where the answer is
no, the drawing needs a second basis for identification, and geometry usually
supplies one.

### T060 — A fixed view is a view of the design it was written for

The chain renders five mask shots at windows chosen in code: the lead-in, the
taper tip, ten grating periods, the electrodes and a bond pad. The electrode
window is centred on half the device length and sized from `electrodes.gap_um`.

That was correct for a device carrying one electrode pair at mid-span. A device
carrying a second pair near the facet has no view of it, and the fixed windows
cannot be pointed anywhere else. A review deck then described the architecture in
prose and showed a picture of the predecessor.

**A renderer with a hard-coded window renders the design it was written for.**
Where a design gains a second instance of a structure, the fixed views do not
gain one with it, and the omission is invisible: the figures that exist all look
correct.

`tools/mask_view.py` renders any window of any run with a chosen subset of
layers. Layer selection is what makes a crowded region legible, a metal run over
a slab over a fill pattern drawing as one block until the others are turned off.
It refuses a layer name the design does not declare, rather than dropping it,
because a view that quietly omits the layer somebody asked for is a view of the
wrong thing.

The practice: **after adding a structure to a design, ask which existing figure
shows it.** Where the answer is none, the figure set has not kept up with the
device, and no amount of reading the existing figures reveals that.

### T061 — A deck's numbers drift silently, and the drift is only found by comparing

A review deck carried eleven numbers that matched no run of record. Five were
found by reading, after a reviewer asked about one of them. The rest were found
only by comparing every stated quantity against the metric trees of both designs
the deck covers.

The stale set: a free spectral range of 10.6 GHz against 10.06, a device length
of 17.4 mm against 17.75, an electrode gap of 7.7 um against 6.54, a feed length
of 210 um against 600 in one appendix row and against 220 in a paragraph, a
device length of 17359.2 um against 17746.0, a linewidth bound of 5.6 kHz
against 5.0, and a post count given as "~12 000" against 11 997.

**Each was internally plausible and none was findable by rereading.** Two were
transpositions, one digit apart from the truth.

`tools/check_doc_numbers.py` compares a document against the runs. Three
refinements were needed before it stopped reporting correct text: a bound
carrying a comparison operator is not a claim; a corner extreme is a real figure
a document may quote; and a section deliberately frozen at an earlier
configuration declares itself with a `<!-- frozen: ... -->` span rather than the
tool guessing.

**A checker that reports correct work as wrong is one the reader learns to
skip.** All three were fixed in the tool. The tool was then falsified by
injecting a wrong free spectral range and confirming it was caught.

The residual on the two design reports is fifteen and twenty lines, and they were
inspected rather than assumed: they are prose narrating a corrected defect by
quoting the superseded value, and part numbers whose digits match a numeric
pattern. **A residual that has been read is a different thing from a residual
that has been tolerated**, and the distinction belongs in the report of the check.

### T062 — Run directories grow without bound, and the numbers in them are a rounding error

Seven designs held 1401 run directories totalling 17.3 GB. The numeric
provenance of all of them, being every `metrics.json`, `verify.json`,
`design.resolved.json`, stage payload, manifest, corner report and figure, came
to under 100 MB. **The other 99 % is solved field arrays and emitted layouts,
and both are regenerable from the design file and the run's own
`design.resolved.json`.**

The policy applied, and it is the one to repeat: keep the run of record in full,
strip `.npz` and `.gds` from every other run, keep every `.json`, `.md`, `.png`,
`.drc` and `.lyrdb` everywhere. The repository went from 19 GB to 2.6 GB with
every number, verdict and manifest still in place.

**Identify the run of record by checksum, not by date.** A manifest whose design
SHA matches the current `design.yaml` names it exactly. Two of seven designs had
such a match; the rest had drifted, and for those the newest run was kept
together with the newest released run, because the newest may be a partial check
run and stripping the only complete artifact set to keep a two-stage probe is
the failure to avoid.

**A deletion is itself an artifact and is recorded.** Each `runs/` now carries a
`REMOVED.md` stating what went, on what basis, what it costs, and the command
that regenerates it. Two costs follow and both are acceptable on a superseded
run: its figures cannot be re-rendered, and its manifest cannot be
checksum-verified, the files it lists having gone.

Loose `run_*.log` and `corners_*.log` at a design root were moved to `logs/`,
keeping the run of record's own log and the newest corner log beside the design.
A toolchain root carrying a run log is a run executed from the wrong working
directory, and that one was moved out.

### T063 — A deck about two designs is a deck about neither

A review deck was written for one design and a second design was appended to it
as a section when that design superseded the first. The result read as a document
about the predecessor with a variant bolted on, and the variant was the device
going to fabrication.

Three defects followed from the structure and each was invisible while the
structure stood.

**The narrative explained the wrong device twice.** The concept section derived
the behaviour of a cavity whose mode comb is left to slip, and the mechanism that
removes that behaviour appeared thirty slides later. A reader met the problem,
its consequences, its process window and its mask before being told the design
does not have it.

**Two process-window sections coexisted** and reported different verdicts, one
per design, without either saying so at the point of reading.

**Comparison figures hid the subject.** Several figures were two-panel views of
the two designs, so the device under review occupied half of each frame and the
other half described something the deck was not about.

The correction is structural rather than editorial. The superseded design was
removed entirely, the comparison figures were regenerated single-panel, the
mechanism was moved into the concept section where the problem is posed, and the
two window sections were merged into one. The deck went from 90 slides to 71,
and a fifteen-slide recipe for rebuilding the design in another toolchain was
split into its own document, being a different job for a different reader.

**Narrowing the truth set is what found the residue.** While the number check
admitted both designs' runs, three counterpart figures passed as correct: a free
spectral range, a feed length and a worst-corner containment. Checking against
the one design the deck is now about failed all three immediately. **A checker is
only as strict as the set of answers it will accept**, and a document covering
two subjects licenses every number of both.

### T064 — A precondition that asserts a fit must ask whether both things exist

A study widened a waveguide with the electrodes switched off, and the preflight
refused it because the electrode gap no longer cleared the ridge. There were no
electrodes. Two of the module's preconditions read a stage's fields without
checking whether that stage is enabled, while their immediate neighbours did
check, so the omission was an inconsistency rather than a policy.

**The distinction that resolves it.** A precondition asserting that a declared
value is possible at all, such as a reflectivity inside the unit interval, holds
whether or not the stage runs; the value is wrong on its face. A precondition
asserting that one structure fits another holds only where both structures
exist. The first kind is left unguarded and the second now checks.

Recorded because the failure mode is the one T053 names. **A gate that refuses
correct work trains the reader to bypass the gate**, and the bypass available
here was to switch the check off or to abandon the study.

Enforced by `test_a_geometric_precondition_respects_a_disabled_stage`, which
confirms the widened guide passes with the electrodes off and still fails with
them on. A guard relaxed without the second half of that test would have removed
the check rather than corrected it.

### L026 — The collapse of a worst-case search to box corners is verified, not assumed
*Recorded 2026-08. Class: method. Confidence: high, verified against 200 000
interior samples in two boxes on one design.*

Choosing a design point against the worst outcome over an interval of unknown
parameters is a semi-infinite problem, one constraint per point of a continuous
set. It becomes finite where every constraint is monotone in every uncertain
parameter, because a monotone function over a box attains its extremum at a
vertex, and four unknowns then cost sixteen evaluations rather than a search.

Monotonicity is a property of the particular constraint set and is ordinarily
asserted. In the case that produced this entry it was checked: the worst margin
over the sixteen corners was compared against 200 000 uniformly sampled interior
points, in a wide box and in a narrow one, and the corner bound was the lower of
each pair. The check cost seconds.

Where an interior point beats the corners the inner problem is not monotone, the
corner set is not a bound, and every margin computed from it is optimistic by an
unknown amount. The verification is what distinguishes a bound from a hope, and
it is cheap enough that omitting it is never justified by cost.

### L027 — An interval labelled as measured before anything was measured
*Recorded 2026-08. Class: procedural. Confidence: high, one design, measured.*

A worst-case design point is only as good as the interval box it was chosen
against, and the box is written before the measurement it anticipates. Naming
that interval after the measurement is the error, because the label then travels
into every margin computed from it and into every document that quotes one.

In the case that produced this entry a box was declared in two variants, one
described as the unmeasured case and one as the measured case, and the design was
reported feasible against the second. The parameters were later measured by a
mode solve and an electrostatic solve. Two of the three axes came back **wider**
than the assumed interval, the electro-optic overlap by a factor of 2.7 and the
coupling constant by 3.7, and only the group index came back narrower. The
worst-case margin with realisation error included fell from +8.89 per cent to
+1.13 per cent on that correction alone.

The design had not changed. What changed was the accuracy of the box. Label an
assumed interval as assumed in the file where it is declared, and re-run the
search whenever the box moves, which costs seconds where the solve that narrowed
it cost hours.

### L028 — An inherited target that the reference device never demonstrated
*Recorded 2026-08. Class: procedural. Confidence: high, one design, and the
framework reproduction of the reference device records the failure.*

A requirement elicited from a scope document may have entered that document from
a cited device rather than from the system it is meant to serve. Where the
architecture then differs from that device, the figure is inherited twice over
and is anchored to nothing.

In the case that produced this entry a mode-hop-free tuning range of at least
8 GHz was elicited, and the operational requirement derived from the system
bandwidth was 3.0 GHz, a factor of 2.7 lower. The 8 GHz had come from a reference
device with a different cavity architecture, and the framework reproduction of
that device returns 3.85 GHz against the row and records a fail: **it had not
been demonstrated even there.** The scope document blanket justification, that
its targets sat below demonstrated performance, did not reach a row that was
never demonstrated.

Re-derive from the level above rather than adjusting the inherited figure, and
check whether the source of an inherited number ever met it. Where a goal above
the derived requirement is retained by decision, hold both rows and mark which is
which, since a goal recorded as a requirement sizes the design against a number
nobody asked for. Here that decision cost fifteen volts of drive, which is a
legitimate price and an illegitimate accident.

### L029 — An architecture statement contradicted by the datasheet of its own part
*Recorded 2026-08. Class: procedural. Confidence: high, one design.*

An architecture is ordinarily recorded as a diagram and as prose, and neither
can be contradicted by evidence. A numbered statement in the requirement set
carrying a source can be, and the difference is not cosmetic.

In the case that produced this entry an architecture row asserted a
high-reflectivity back facet on a purchased gain chip. The datasheet for the
part actually selected gives approximately ten per cent, which is a partial
reflector. The lasing condition, the threshold gain and the output extraction
all follow from the actual value. The error survived elicitation and one review,
and was found only when the part number was checked against the row that
described it.

Write the architecture as rows with sources, and check each row against the
datasheet of the part it describes at the point the part is selected. A part
substitution invalidates every row that described the part it replaced, and the
rows are not adjacent to the substitution in any document.

### L030 — A lumped variable that the mask makes conditional on another
*Recorded 2026-08. Class: method. Confidence: high, one design, measured.*

An early-stage search treats lumped quantities as independent because in closed
form they are. Geometry may couple them, and the coupling is invisible to a
stage that never draws a polygon.

In the case that produced this entry a search chose a coupling constant and an
electrode gap from independent lists. Realising the coupling constant required a
post gap, and weakening the grating opened that gap, which moved the posts
outward, which forced the electrode to retreat to hold a metal-to-ridge
separation rule, which lowered the tuning rate as one over the gap. The tuning
rate fell from the assumed 587 MHz/V to 494, and its margin from +30.5 per cent
to +9.8, on a row that was already the binding one.

The remedy is to carry the dependency into the early stage as a function rather
than to discover it later: the electrode floor became a function of the coupling
constant, fitted from the same mode solves that performed the inversion. A
search over a variable the mask cannot vary independently is exploring
geometries that cannot be built.

### L031 — An instrument whose discretisation error exceeded the quantity measured
*Recorded 2026-08. Class: method. Confidence: high, one design, quantified by
the convergence guard.*

An independent method is run to check a model, and the check may be beneath the
resolution of that method. Where the quantity is a small difference of two large
numbers, that outcome is likely rather than exotic.

In the case that produced this entry a band-structure solve was run to check a
coupling constant obtained from coupled-mode theory. The band gap is the
difference of two nearly degenerate bands, and at a coupling constant of
1.5 cm⁻¹ that gap is a split in the fifth decimal of normalised frequency.
Between two mesh densities the method moved the coupling constant by 0.613 cm⁻¹
against a disagreement with the model of 0.339 cm⁻¹, so the error of the
instrument stood at 1.8 times the signal. The band pair carrying the gap was
itself identified differently at the two meshes.

Two consequences. **The difficulty scales inversely with the quantity the design
deliberately made small**, so a result obtained on a strongly coupled reference
structure does not establish that the same check is available on a weakly
coupled one. And a comparison that cannot resolve the question establishes
nothing: report the mesh shift beside the disagreement, so that a later reader
sees which exceeded which, and record the outcome as a finding about the
instrument rather than quoting a number from it.
