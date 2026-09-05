---
name: eo-electrode-design
description: Design and evaluate electro-optic electrodes on a Pockels platform (thin-film lithium niobate or tantalate, X-cut or Z-cut), covering the overlap factor Gamma, tuning efficiency in MHz/V, Vpi.L both ideal and derated, capacitance, lumped and travelling-wave bandwidth, velocity and impedance matching, metal absorption, and the drive voltage a specification actually demands. Use whenever an electrode gap, width, thickness or placement is being chosen, whenever a tuning efficiency or Vpi figure is to be predicted, interpreted or reconciled with a published one, whenever a modulator must reach beyond about one gigahertz, or whenever a tuning range falls short and it must be established whether the shortfall is optical or electrical.
---

# Electro-Optic Electrode Design

## The Overlap Factor Constitutes the Problem

The parallel-plate estimate

> dn = 0.5 n^3 r V / G

is an upper bound. The physical result is Gamma times that value, where

> Gamma = (G/V) . Int_active( E_rf |E_opt|^2 ) / Int_all( |E_opt|^2 )

Two separate effects are folded into Gamma, and both are to be understood before
a figure is trusted:

1. **Optical confinement within the electro-optically active material.**
   Frequently 0.6 to 0.8 for a thin-film ridge, part of the mode residing in the
   cladding.
2. **Non-uniformity of the RF field.** On a high-permittivity film the field is
   drawn into the material and is depressed where the ridge sits. Ratios of 0.5
   to 0.7 relative to V/G at the waveguide are usual.

The product is commonly Gamma = 0.3 to 0.5. A design predicated on Gamma = 1 will
under-deliver by that factor.

## Interpretation of Published Figures

Where a published Vpi.L appears superior to the achievable value by a factor of
two to three, the probable explanation is that the **un-derated** figure has been
quoted, computed at Gamma = 1. Both are to be reported, and the distinction
stated.

## The Crystal Cut Selects the Field Direction, and the Electrode Follows

The Pockels tensor is not isotropic, so the electrode geometry is decided by the
cut before any dimension is chosen. Using the largest coefficient, r33 on lithium
niobate and tantalate, requires the RF field to lie along the crystal c-axis.

**X-cut.** The c-axis lies in the plane of the film, across the guide. A pair of
coplanar electrodes either side of the ridge produces an in-plane field along it,
so r33 is reached with a planar process and no electrode above the guide. The
mode sees metal only through its lateral tails, which is why the gap can be
closed further here than the vertical arrangement allows.

**Z-cut.** The c-axis is normal to the film. The field must therefore be
vertical, which requires an electrode above the guide with a ground below or
immediately beside it. Optical absorption is the binding constraint, the metal
sitting where the mode is strongest rather than in its tail, and a buffer layer
is usual. That buffer enters Gamma, since it drops part of the applied voltage
outside the electro-optic material.

**A cut mismatched to the electrode does not fail; it under-delivers.** A lateral
pair on Z-cut material addresses r13, which is roughly a third of r33, and the
design will read as a factor-of-three disappointment rather than as an error.
State the cut, the field direction and the coefficient together, always.

### Push-pull applies to an interferometer, not to a phase shifter

Where both arms of a Mach-Zehnder lie between the same electrode pair, one arm
sees the field in one direction and the other in the opposite direction. The
differential phase is then twice the single-arm phase, and **Vpi halves**. This
is a factor of two and it is worth having.

It is a property of the interferometer and not of the electrode. A single phase
shifter, and a tuned reflector such as a DBR, has no second arm and takes no such
factor. A Vpi.L quoted for a push-pull modulator is therefore not comparable with
one quoted for a phase shifter, and the two are routinely confused. State which
is meant.

## Two Meshes Are Required

The optical mode occupies a few micrometres. The fringing field that sets the
electrode capacitance extends across tens of micrometres. Meshing the
electrostatic problem at optical resolution is wasteful, and sizing the
electrostatic window for the mode under-reads the capacitance substantially.

A fine narrow mesh is to be used for the optics, a coarse wide mesh for the
electrostatics, and the RF field interpolated onto the optical mesh. The RF field
is smooth on the scale of the mode, so no accuracy is lost.

## The Gap Trade

Narrowing the electrode gap raises dn as 1/G, and three consequences follow.
**Only the second and third are penalties on a high-permittivity film**, and the
first is measured rather than assumed:

* **Gamma is not necessarily lowered.** The conventional expectation is that a
  narrower gap makes the field less uniform across the mode and lowers the
  overlap. Measured on a 300 nm X-cut tantalate ridge, Gamma **rose** from 0.2473
  at a 6.62 um gap to 0.2619 at 4.00 um, a gain of 5.9 %. The film draws the
  field, so closing the gap concentrates it where the mode already is. **Measure
  Gamma at the gap in question rather than scaling a value from another gap.**
* optical absorption in the metal rises steeply once the evanescent tail reaches
  the electrode;
* capacitance rises, by which the drive bandwidth is lowered.

### Scaling dn by the gap ratio alone is an assumption, and it is testable

A chain that takes the index change per volt of one electrode and rescales it to
a second electrode by the inverse gap ratio is asserting that Gamma is common to
both. **Run the electrode solve at the second geometry instead.** On the
measurement above the 1/G scaling understated the second electrode by 5.9 %,
which was conservative in that instance and is not conservative by construction.

### A second electrode inherits the bound as well as the physics

Where a design carries two electrode pairs at different gaps, **the metal-overlap
bound applies to both and is ordinarily evaluated at one**. On the same
cross-section the mode overlap with metal rose from 6.9e-8 at the 6.62 um mirror
gap to 6.7e-5 at the 4.00 um phase-section gap, against a design bound of 1e-5.
The narrow electrode breaches by nearly an order of magnitude and no acceptance
row saw it, the metric being reported for the mirror alone.

**The overlap falls exponentially with the gap**, measured here at
d(ln overlap)/d(gap) = -2.6 /um, so the gap that restores a given bound is a
short calculation and the section length scales with it in proportion.

The optical power beyond the electrode inner edge is to be reported on every
design. It is a geometric proxy and it is a guard rather than a measurement: a
real-permittivity mode solve carries no absorption at all, so the loss it reports
for a guide touching metal is zero.

**Where a figure in dB/cm is required, solve with a complex permittivity.** A
metal admits a complex index, and a solver that accepts one returns a complex
effective index whose imaginary part is the attenuation directly:

    alpha (Np/m) = 2 (2 pi / lambda) Im(n_eff)
    alpha (dB/cm) = alpha (Np/m) x 8.686 / 100

Most finite-element and time-domain solvers support this; a semi-vectorial
finite-difference solver written for real indices usually does not. Report both:
the proxy as a fast guard on every run, and the complex solve at the point where
a loss budget is actually committed to. Where the two disagree in ordering, the
complex solve is the one to believe.

## The Driver Is a Design Constraint, Not an Afterthought

An efficiency in MHz/V is only half of a tuning specification. The other half is
the voltage available, and their product is the excursion the device will
actually deliver.

Two figures are therefore to be reported together with any tuning efficiency:
the drive the intended span demands, and the drive the electronics can supply.
Where a sweep is bounded by the latter, the resulting range is a property of the
driver and must be labelled as such. A range that meets its target without ever
reaching the physical limit it is named after invites every subsequent iteration
to address the wrong mechanism.

The gap is the control that connects the two. Closing it raises MHz/V and lowers
the voltage a given span demands, at the cost in overlap and metal absorption
described above. Where a span cannot be reached, establish first whether the
shortfall is in the efficiency or in the supply, since only the first is a
photonic problem.

## Bandwidth

A lumped RC estimate is adequate for drive frequencies of a few hundred
kilohertz. It is not adequate above approximately one gigahertz. The lumped
estimate over-reads at the lower end, the fringing field being truncated by the
electrostatic window.

**The crossover is a length and not a frequency.** Once the electrode is a
significant fraction of the RF wavelength it is a transmission line, and a
lumped figure computed for it is not a bandwidth but an artefact. On one baseline
an 11 mm electrode gave 2.5 GHz lumped against 27.7 GHz from the travelling-wave
model, a factor of eleven, and the lumped figure was the one that would have been
quoted had the two not been reported side by side.

### The three travelling-wave conditions

A travelling-wave electrode is bounded by three separate things, and a design
meeting two of them is bounded by the third.

**Velocity match.** The optical and microwave waves must stay in step, so
n_RF is to equal n_opt, where n_RF = sqrt(C / C_air) with C the line capacitance
per unit length and C_air the same line with the dielectrics removed. The walk-off
bandwidth of a length L falls as

    |m(f)| = |sinc(dtheta/2)|,  dtheta = 2 pi f L (n_RF - n_opt) / c

so the first null is at dtheta = 2 pi. A mismatch of 0.5 in index over 10 mm puts
that null near 6 GHz irrespective of loss.

**Characteristic impedance.** Z0 = 1/(c sqrt(C C_air)) is to sit near the source
and termination, usually 50 ohm. A mismatch reflects rather than attenuates, so
it appears as ripple against frequency rather than as a roll-off, and it is
easily mistaken for a resonance.

**Conductor loss.** The current occupies one skin depth, so the series resistance
rises as the square root of frequency and the electrode attenuates as exp(-alpha L).
Two consequences follow. **The metal thickness matters**: once it exceeds a few
skin depths further thickness buys nothing, and below one skin depth the
resistance is set by the thickness rather than by the skin effect, so a thin
evaporated film is markedly worse than the bulk figure. And **length trades
against loss**: a longer electrode lowers Vpi and lowers the bandwidth, the two
being the same knob.

Design against all three together. Lengthening for a lower Vpi costs bandwidth
through both walk-off and attenuation; narrowing the gap for a lower Vpi raises
capacitance, which moves n_RF and Z0 at once.

For a swept or ramped drive, the bandwidth is to be sized against the harmonics
rather than the fundamental. Approximately ten times the ramp repetition rate is
a workable rule for acceptable corner fidelity.

### The far-end condition, which is the fourth travelling-wave condition

A matched line carries one forward wave. A line left open, which is what a bond
pad with nothing behind it presents, returns a wave. The returned wave travels
against the optical carrier, so the two walk off at the **sum** of the indices
rather than at their difference, and it therefore contributes at low frequency
and vanishes at high. With `g = alpha + j omega n_RF / c`,

    m ~ (1 - exp(-u_f))/u_f  +  G exp(-2 g L) (exp(u_b) - 1)/u_b
    u_f = (alpha + j (omega/c)(n_RF - n_opt)) L
    u_b = (alpha + j (omega/c)(n_RF + n_opt)) L
    G   = (Z_L - Z0) / (Z_L + Z0)

`G` is zero at a matched load, plus one at an open end and minus one at a short.
Any unmodulated line between the end of the modulation section and the load
rotates the returned wave without contributing modulation, so it moves the null
and leaves the zero-frequency limit alone.

**The reference decides what the number means, and it inverts the conclusion.**
An open end doubles the response at zero frequency, so dividing by that value
reports the decay of the doubling rather than the onset of a loss. On one 5 mm
electrode the self-referred 3 dB point read 4.4 GHz while the device was within
half a decibel of a matched line above 49 GHz. **Quote the penalty against a
matched line driven by the same incident wave**, being the worst and the best the
far-end condition does across the band, each with the frequency it occurs at.

**The far-end condition is a claim about a polygon.** A termination is realised
by a resistive feature the mask must draw. Where the layout draws none, the
declared load is an assumption and the correct declaration is the open end that
exists. A foundry deck will say so, five times, before anything else does.

### A periodically loaded electrode is two cross-sections, and one is no bound on the pair

An electrode may be interrupted along its length, holding a narrow gap for most
of a period and opening to several times that gap for the remainder. A chain
solving one cross-section per run returns the figure of the narrow section alone.

**Weighting the reciprocal gap over the period is an estimate and not a bound.**
It holds the overlap fixed and the overlap moves: on one such electrode the
overlap fell by 23 per cent in the open section, and the ratio of the two
half-wave voltages is the gap ratio multiplied by that further factor. The
weighting predicted 5.9 per cent and the homogenised figure is 6.7.

**Solve both drawn cross-sections and homogenise over the period.** Capacitance
averages arithmetically, the sections being in parallel across the line;
inductance averages arithmetically, the sections being in series along it; the
half-wave voltage combines as a reciprocal average; and the series resistance is
recovered from each section before being averaged, since each section's
attenuation carries its own impedance.

The homogenisation returns three quantities the weighting is silent about. The
microwave index rises away from the optical group index, so the walk-off worsens
and on the case measured the bandwidth fell 15 per cent. The characteristic
impedance rises, by about two ohm toward the source.

## What Must Be Reported

An electrode design is not delivered until the following are stated together.
Each exists because quoting the design without it has misled somebody.

| quantity | why it must appear |
|---|---|
| the cut, the field direction and the coefficient | a lateral pair on the wrong cut addresses r13 and under-delivers threefold |
| Gamma, and the two effects composing it | a design predicated on Gamma = 1 under-delivers by that factor |
| **Vpi.L ideal AND Vpi.L derated, side by side** | the ideal figure is what published work usually quotes; the derated one is what the device does |
| whether Vpi is push-pull or single-arm | a factor of two, and the two are routinely compared as though alike |
| tuning efficiency in MHz/V | the quantity a system engineer actually consumes |
| the drive the specification demands, against the drive available | a range bounded by the supply is not a property of the optics |
| optical power beyond the electrode inner edge | the guard on metal absorption in a real-index solve |
| metal attenuation in dB/cm, from a complex solve | required wherever a loss budget is committed to |
| capacitance, and the lumped bandwidth | adequate only below roughly one gigahertz |
| n_RF, n_opt, Z0 and conductor loss | required above it, and the lumped figure is to be labelled inadequate there |

**The ideal and the derated Vpi.L are to appear in the same table, never in
separate places.** A reader given only one will assume it is the other.

Where a figure cannot be produced, say so and say why. An absent row is a
question nobody asked, and reads exactly like a favourable answer.

## Platform Note

A high RF permittivity is not automatically favourable. It redistributes the
electrode field and thereby alters Gamma, and it displaces the microwave index
from the optical index, which is significant for travelling-wave designs. Where a
platform is changed, Gamma and Vpi.L are to be recomputed. They do not scale with
the electro-optic coefficient alone.
| the far-end load, and whether the mask draws it | a declared termination with no resistive polygon describes a device that does not exist |
| the penalty against a matched line over the declared band | the self-referred 3 dB point of an unterminated line measures the loss of a doubling |
| whether the electrode is uniform along its length | one cross-section of a periodically loaded electrode understates Vpi and overstates the bandwidth |
