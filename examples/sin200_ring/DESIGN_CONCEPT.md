# A textbook microring on silicon nitride, and the round trip this chain has never assembled

*Written 2026-09-14, before any target was declared and before any stage was
written, in the order [`rules/generic/requirements-before-design.md`](../../rules/generic/requirements-before-design.md)
and directive 46 of the operating manual require.*

## What the device is, and what it is for

An all-pass microring resonator is drawn on a 200 nm stoichiometric silicon
nitride film in silica: one straight bus waveguide, one closed loop of radius R,
and one point coupler between them. Light entering the bus leaves by the same
bus. At a wavelength for which the loop's round-trip phase is an integer
multiple of two pi, the field circulating in the loop interferes with the field
continuing along the bus, and the transmitted power falls.

The device is posed for two reasons, and the second is the durable one.

**It is the first resonator this chain has been asked to assemble.** Every stage
models one component. The `cavity` stage combines components arithmetically for
one arrangement, being a gain chip behind a feed and a distributed mirror, and
the `circuit` stage states in its own opening that the arrangement it encodes
"cannot be applied to a resonator on a bus". The consequence is checkable: no
design in this repository declares a target on a loaded quality factor, on an
extinction, on a finesse or on a free spectral range, and the ring study at
[`examples/ltoi300_ring`](../ltoi300_ring/README.md) computes all four in a
script beside itself. Capability held in a script beside one example is
available to no other design, carries no acceptance target, and is graded by no
verification.

**It is the first design this chain has run on silicon nitride.** The material
is present, being the Luke 2015 fit in
[`design-chain/pdk/materials.yaml`](../../design-chain/pdk/materials.yaml), and
one study has solved strips on it to measure what a non-dispersive compact model
costs. No design file has declared the stack, so the first run of this design is
a test of the chain rather than of the device, in the sense of
[`rules/generic/first-exercise.md`](../../rules/generic/first-exercise.md).

**The device is a textbook one by choice.** Its closed forms are exact, they are
published, and each of them is checkable by an independent route. A first
exercise whose answer is unknown cannot separate a defect in the chain from a
property of the device.

## By what principle it works

The loop is described by one complex number per round trip and the coupler by
one real number.

    a       = exp(-alpha_p L / 2)        the amplitude surviving one round trip
    phi     = 2 pi n_eff L / lambda      the phase accumulated over it
    L       = 2 pi R                     the round trip
    t^2 + kappa^2 = 1                    the coupler, taken as lossless

Here `alpha_p` is the power attenuation per unit length and `t` is the amplitude
the coupler leaves in the bus. The transmitted power of the all-pass arrangement
follows from summing the circulating field over every round trip:

    T(phi) = (a^2 - 2 a t cos phi + t^2) / (1 - 2 a t cos phi + a^2 t^2)

Five statements follow from that expression, and the design is the exercise of
choosing where on them to sit.

**On resonance the transmission is set by the difference of two numbers.**
Putting `cos phi = 1`,

    T_min = (a - t)^2 / (1 - a t)^2

so the extinction is complete when `t = a`, which is the critical-coupling
condition. The condition is a statement about loss as much as about a gap.

**The resonance condition is degenerate, and one spectrum does not resolve it.**
The expression is symmetric under exchange of `a` and `t`, so a measured
extinction admits two solutions: an undercoupled one with `t > a` and an
overcoupled one with `t < a`. Separating them requires a second measurement, at
a second gap or across a deliberate change of loss.

**The order spacing is set by the group index and the circumference.**

    FSR = lambda^2 / (n_g L)

**The width of an order is set by the product `a t`.**

    FWHM   = (1 - a t) lambda^2 / (pi n_g L sqrt(a t))
    F      = FSR / FWHM = pi sqrt(a t) / (1 - a t)
    Q_load = lambda / FWHM

**The width of an order in the absence of the coupler reports the stack.**

    Q_int = 2 pi n_g / (lambda alpha_p)

That last quantity is what a ring is built to measure on a platform whose
propagation loss is unknown, and the propagation loss of this stack is unknown
here. The value carried by the chain is a typical figure and is marked as one.

## What this design does not settle, and why it is posed anyway

**No measurement of a silicon nitride device exists in this repository.** The
references folder holds three papers, two on lithium tantalate and one on a
lithium niobate laser. The
propagation loss of the stack is therefore an axis of the study and is not an
input to an answer, in the manner the sibling ring study adopted for lithium
tantalate. Every figure that depends on it is reported across a declared range,
and the single value in the design file carries an assumption marker.

**Bend radiation is computed by no stage of this chain.** The `bend` stage
solves the conformally transformed cross-section and returns the index shift and
the distance to the radiation caustic. It returns no loss in decibels per
centimetre. The clause "the round trip may be treated as a straight guide of
length 2 pi R" is therefore tested by a proxy, and the proxy is named as one in
the trace table below. The radius is chosen with margin against that ignorance
rather than against a computed figure.

The proxy is the distance to the caustic measured in lateral decay lengths of
the straight mode, and the choice of that form was settled by the first run. The
bend solve also integrates the power lying beyond the caustic, and that integral
is a property of the solved window: it is undefined wherever the caustic falls
outside the window, which is the case whenever the bend is comfortable. A target
on it would pass every wide bend because the instrument could not see the
quantity, and would begin to fail only once the caustic had already come inside
the window. The distance in decay lengths is defined in both cases and moves
smoothly between them.

**The coupler is measured in two dimensions.** The chain's point-coupler runner
reduces the cross-section to an effective index, and its own docstring states
that the reduction is valid where the film beside the ridge is a continuous
slab. A fully etched strip breaks that condition, the material beside the ridge
being the cladding. The consequence for this design is stated under "The first
run is a test of the chain" below, and it is the first thing the first run must
establish.

*Added 2026-09-15, after the runs: it was not established. The gap ladder the
first runs produced measures the reduced problem rather than the real
cross-section, so it discriminates in neither direction, and
[`REPORT.md`](REPORT.md) carries the question open under "What is not settled".
This paragraph is left as written so that the promise and its outcome stand
together.*

## What each clause of the principle requires, and what expresses it

| Clause of the principle | The quantity that expresses it | Where it comes from |
| --- | --- | --- |
| The loop closes on itself, so it resonates | `resonator.fsr_nm` | the group index from the mode solve and the drawn radius |
| One family of resonances appears, so a spectrum is readable | `mode.n_guided_modes` | the mode solve on the bus cross-section |
| Light survives the round trip, so an order is narrow | `resonator.q_intrinsic` | the declared propagation loss and the group index |
| The coupler transfers a defined fraction of the power | `resonator.kappa_squared` | the time-domain solve of the drawn point coupler, or a declared value where no solve has been run |
| The two together place the device in a coupling regime | `resonator.coupling_regime` and `resonator.extinction_dB` | the closed form above |
| An order is deep enough to be located | `resonator.extinction_dB` | the same |
| An order is wide enough to be resolved by the source | `resonator.fwhm_pm` | the same |
| The round trip may be treated as a straight guide | `resonator.bend_caustic_in_decay_lengths` | the conformal bend solve at the ring radius, divided by the lateral decay length of the straight mode. The radiation loss itself is computed by no stage, and this distance is a proxy for it |
| The chain's resonator arithmetic is the published arithmetic | the closed-form unit test of the stage | an independent evaluation of the same expressions |

## The trace from each clause to the target that tests it

This table is the one checked by
[`design-chain/tools/check_concept_trace.py`](../../design-chain/tools/check_concept_trace.py).
Every declared target appears here, and every traced clause carries a target.

| Clause | Metric | Severity | Why that severity |
| --- | --- | --- | --- |
| A spectrum carries one family of resonances | `mode.n_guided_modes` | must | A second guided mode produces a second comb, and the two are not separable in one transmission spectrum. |
| The loop resonates at a spacing the intended source can address | `resonator.fsr_nm` | must | The free spectral range is the wavelength squared over the group index and the circumference. The mask sets the circumference and the cross-section sets the group index, so the row is met by choosing a radius against a solved index. A value outside the window makes the device unmeasurable by the instrument it is posed for. |
| An order is deep enough to be located | `resonator.extinction_dB` | must | An extinction below ten decibels is lost in the ripple of a fibre-coupled measurement, and the device then reports nothing. |
| An order is wide enough to be resolved | `resonator.fwhm_pm` | should | The floor is a property of the source, and a narrower order remains a better device measured by a better instrument. |
| Light survives the round trip | `resonator.q_intrinsic` | info | The quantity is a restatement of the declared loss and of the group index. Grading it against a value assumed for the loss would be circular. |
| The coupler transfers the fraction of the power intended | `resonator.kappa_squared` | info | The value is measured by the time-domain solve and is recorded at an advisory severity, a measured quantity not being graded against the assumption it replaces. |
| The round trip may be treated as a straight guide | `resonator.bend_caustic_in_decay_lengths` | should | The quantity is a proxy for a loss the chain does not compute. A `must` on a proxy asserts a confidence the instrument does not support. |

Two clauses of the principle carry no row.

**The coupling regime is not graded.** `resonator.coupling_regime` is a label and
not a number, and the quantity it summarises is the extinction, which is graded.
The regime is reported and read.

**The closed form itself is not graded by a target.** It is established by the
unit test that accompanies the stage, which evaluates the same expressions by an
independent route and compares. A target in a design file cannot test the
arithmetic the design file is scored by.

## The first run is a test of the chain

Four options are selected here that no previous design has selected, and each
names code that has never executed on this branch.

| Option | The branch it selects | What is to be confirmed before the result is read |
| --- | --- | --- |
| `film_material: Si3N4` | the material library's isotropic path, where every previous design declared a uniaxial film and a crystal cut | that `cut` is inert for an isotropic material, and that the anisotropy bracket reports zero rather than a difference of one entry against itself |
| A full etch, `etch_depth_um` equal to `film_thickness_um` | the slab solver at zero slab thickness | that the slab index floor returns the cladding index, and that the two-dimensional coupler reduction takes the cladding as its background |
| `slab_offset_um` unset on a fully etched film | the blanket-slab default, which describes a film that is not there | that no stage draws or solves a slab |
| A resonator | a stage written for this design | that the stage's closed form agrees with an independent evaluation, which is the test that accompanies it |

The findings of that first run belong in the report of this design and in the
lessons ledger, as findings of the run and not as properties of the device.

## Provenance

The closed forms are those of Bogaerts, De Heyn, Van Vaerenbergh, De Vos,
Kumar Selvaraja, Claes, Dumon, Bienstman, Van Thourhout and Baets, "Silicon
microring resonators", Laser and Photonics Reviews 6, 47 (2012), which states
the all-pass and add-drop transfer functions, the critical-coupling condition
and the degeneracy between the undercoupled and overcoupled solutions. The
expressions are reproduced above from the definitions rather than copied, and
the stage's test evaluates them by a route that shares no step with the stage.

The silicon nitride dispersion is the Luke 2015 fit already held in the material
library. The silica dispersion is the Malitson 1965 fit held beside it.

The propagation loss is an assumption. No measurement of this stack is held in
this repository.
