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
4. Execute `python tools/check_ip_boundary.py`.
5. Where a skill has been changed, add or amend the corresponding closed-form
   test in `design-chain/tests/` so that the lesson is enforced and not merely
   recorded.

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

