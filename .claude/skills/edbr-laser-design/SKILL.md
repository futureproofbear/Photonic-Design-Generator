---
name: edbr-laser-design
description: Design or diagnose a hybrid extended-DBR laser, being a gain chip butt-coupled to a passive circuit terminated in a distributed reflector. Covers the tuning lever, mode-hop-free range, side-mode suppression, threshold and linewidth, and the trades between them. Use whenever continuous tuning range, chirp linearity, SMSR or linewidth of an external-cavity or extended-DBR laser is at issue.
---

# Extended-DBR Laser Design

## The Governing Ratio

An extended-DBR laser comprises a gain chip, a passive feed, and a distributed
mirror. Where the mirror is tuned, by whatever mechanism, **only the round-trip
delay residing inside the tuned element follows the tuning**:

> r = tau_mirror / (tau_mirror + tau_gain + tau_feed)

* laser tuning rate = r x mirror tuning rate
* continuous (mode-hop-free) excursion = r/(1-r) x FSR/2
* cavity FSR = 1 / (tau_mirror + tau_gain + tau_feed)

The group delay of the mirror is set by its penetration depth,
L_pen = tanh(kL)/(2k), so a **weaker and longer** grating raises r. The ratio is
fixed at layout time and cannot be recovered by driving harder.

Reported as `cavity.pockels_lever`.

### The ratio is over the tuned region, which need not be the mirror

Written as above, r presumes that the element being tuned is the grating. The
quantity that governs is more general: **the fraction of round-trip delay
residing in whatever region's index actually changes**. Three arrangements follow
from that and they do not behave alike.

**The index is changed within the grating.** The Bragg condition
lambda_B = 2 n_bar Lambda / m moves with n_bar, so the reflection envelope and the
phase move together, and r is the mirror fraction as written. Electro-optic
tuning of an electrode straddling the grating is this case.

**The index is changed in a separate phase section.** The envelope does not move
at all. Only the comb translates, and r is the delay fraction of the phase
section rather than of the mirror. The mode is walked under a stationary
envelope, so the excursion is bounded by the envelope width rather than by the
mode spacing.

**The index is changed over a region that only partly overlaps the grating.** A
heater has a thermal footprint that is rarely coincident with the grating it is
placed over. The delay that follows the drive is the delay within the heated
region, and taking r as the whole mirror fraction overstates the tuning.

A second-order term attaches to thermal tuning specifically. Heating changes the
period through expansion as well as the index through dn/dT, and both shift
lambda_B. **The thermo-optic term dominates**, typically by one to two orders:
dn/dT of order 1e-4 per kelvin against a linear expansion coefficient of order
1e-6 to 1e-5 per kelvin on the usual platforms. The expansion term is a
correction to the tuning coefficient and is not a separate tracking mechanism.
Where the two are of comparable size, the platform is unusual and the assumption
is to be checked rather than carried.

## What Limits the Excursion Is Not Always the Mode Spacing

A continuous tuning range has **three** possible limits, and a figure quoted
without naming which one applies cannot be acted on.

| limit | set by | how it is raised |
|---|---|---|
| a mode hop | r and the FSR, as above | layout: shorten the untuned length, lengthen or weaken the mirror |
| the drive | the available voltage times the laser tuning rate | a higher-voltage driver, or a smaller electrode gap |
| the mirror band | the reflection peak ceasing to support the mode | a wider mirror, meaning a shorter or weaker grating |
| carrier loss | free-carrier absorption, where the tuning is by current injection | move to electro-optic or thermo-optic tuning, or separate the injected region from the optical mode |

The drive limit is the one most often mistaken for the others, because a swept
range that never reaches a hop looks exactly like a range that has no hop. On one
baseline the reported range was 8.20 GHz against a requirement of 8.0, and the
cavity's own mode-hop bound was **12.15 GHz**: the sweep had simply run out of
volts at the declared 20 V, the laser tuning at 408 MHz/V. Every conclusion drawn
about penetration depth and mirror strength from that number was addressing the
wrong mechanism, and the remedy was a 25 V driver rather than any change to the
grating.

**The carrier-loss limit applies only where the tuning is by injection**, and it
is easily overlooked because it does not present as a hop. Injecting carriers to
change the index also raises the absorption: the index change and the loss are
two consequences of the same carrier population, and their ratio is the figure of
merit for the tuning section. As the drive is increased the cavity loss rises,
the threshold rises with it, the output power falls, and the sweep terminates in
a roll-over rather than at a mode boundary. **The linewidth broadens across the
same sweep**, the power entering it inversely. A tuning range quoted for such a
device is therefore to be quoted with the loss, the power and the linewidth at
its far end, and not at its centre. Electro-optic and thermo-optic tuning carry
no such term, which is a substantial part of the reason for preferring them.

Report the range together with what bounded it, the number of hops actually
encountered in the sweep, and whether the sweep was clamped. **A range that met
its target with no hop in the sweep is a statement about the driver, not about
the cavity.**

The same care applies to the requirement. Where a chirp span is specified, the
quantity to compare against it is the drive voltage that span demands, and that
must be checked against the driver before the cavity is blamed.

## Sizing the Cavity Before Anything Is Simulated

Every quantity above is available in closed form, so a layout can be sized, and
more usefully **refuted**, before a solver is opened. The forward relations are:

    L_eff  = n_g L_g + n_f L_f + n_m L_pen
    L_pen  = tanh(k L) / (2 k)
    FSR    = c / (2 L_eff)              equivalently 1 / tau_total
    r      = tau_mirror / tau_total
    dnu    = r/(1-r) x FSR/2

Delays are the convenient currency, tau_i = 2 n_i L_i / c, since r and the FSR
are both delay ratios and the indices then cancel.

### The inversion, which is what sizing needs

Write tau_u for the untuned delay, being the gain chip and the feed together, and
tau_m for the delay in the tuned region. Then

    dnu = tau_m / (2 tau_u (tau_u + tau_m))

and solving for the mirror delay a demanded excursion requires:

> **tau_m = 2 dnu tau_u^2 / (1 - 2 dnu tau_u)**

**A hard feasibility bound falls out of the denominator.** The expression is
positive only where

> **tau_u < 1 / (2 dnu)**

so **no mirror, of any strength or length, delivers dnu once the untuned delay
exceeds 1/(2 dnu)**. That single inequality is the first thing to evaluate on any
new device, and it is evaluated on the gain chip datasheet and the feed length
alone. A 10 GHz excursion admits 50 ps of untuned delay and no more, which is
about 2.1 mm of III-V at n_g = 3.6 together with whatever feed is drawn. Where
the chosen gain chip breaks it, the requirement is unreachable and the finding is
the chip rather than the grating.

Two ceilings bound tau_m from above once feasibility is established.

**The penetration depth cannot exceed half the grating.** L_pen = tanh(kL)/(2k)
tends to L/2 as kL falls and to 1/(2k) as kL rises, so L_pen <= L/2 always.
Weakening the grating therefore asymptotes rather than scaling, and the asymptote
is set by the length that fits the die.

**The die is quantised.** A process offers a fixed set of footprints, so the
grating length has a ceiling that is not continuous. Evaluating tau_m <= n_m L/c
against the largest offered die converts a tuning requirement into a die
selection, and does so before any mask exists.

### Worked, against this chain

For a 1000 um gain chip at n_g = 3.6 and a 200 um feed, tau_u is 26.97 ps.

| demanded excursion | tau_mirror required | remark |
|---|---|---|
| 8 GHz | 20.47 ps | comfortable |
| 10 GHz | 31.59 ps | comfortable |
| 12.15 GHz | 51.30 ps | equals the delay an 11 mm grating at kappa 1.276/cm delivers |

The last row is the round trip: the inversion returns the mirror delay the
forward calculation consumed, so the two agree to the digit. The feasibility
bound at 10 GHz is 50 ps against an actual 26.97 ps, so the arrangement is
reachable with room.

### The closed form is a lower bound, and knowing when tells you a great deal

dnu = r/(1-r) x FSR/2 presumes that a competing longitudinal mode exists **inside
the mirror band** for the laser to hop to. Where the FSR exceeds the mirror
bandwidth, no such mode is supported, the hop the expression describes has
nowhere to go, and the real excursion is larger.

On one baseline the closed form gave 12.15 GHz while a swept search found no hop
at all up to 16.8 GHz, at which point the sweep itself ended. The FSR was
12.78 GHz against a mirror full width of 8.65 GHz, so the neighbour lay outside
the band and the side-mode suppression stood at 53 dB.

**Compare the FSR against the mirror bandwidth before trusting the number.**
Where FSR is below the mirror width, several modes sit under the peak, the
expression is the operative limit, and the trade against side-mode suppression in
the next section is live. Where FSR exceeds the mirror width, the expression is a
lower bound, and the excursion ends instead at the band edge or at the point
where the gain no longer supports the mode.

### Using this to direct a search

A parametric search is expensive and a closed form is not, so the algebra above
belongs in the reachability phase and not after it.

1. Evaluate tau_u < 1/(2 dnu). Failing it, report the requirement unreachable and
   name the gain chip, without running anything.
2. Compute the tau_m demanded, and from it L_pen = c tau_m / (2 n_m).
3. Check L_pen <= L/2 for the largest grating the die admits. Failing it, the
   finding is the die size.
4. Solve tanh(kL)/(2k) = L_pen for the pair (k, L), which fixes the post gap and
   the grating length that the search would otherwise hunt for.
5. Only then simulate, and use the simulation to check what the algebra omits:
   the side-mode suppression, the mirror bandwidth, the sidelobes and the chirp
   linearity.

Steps 1 to 4 cost no runs and bound the space the search explores. They also
supply the monotonic bracket a bisection needs, which the search cannot establish
for itself on a metric that is not monotone.

## The Central Trade

Raising r requires the grating to be lengthened. Lengthening the grating lowers
the cavity FSR, which brings the nearest side mode closer to the mirror peak, at
a cost in side-mode suppression.

> continuous tuning range up  =>  side-mode suppression down

Two controls are available: the grating length and the apodisation profile.
Apodisation suppresses the sidelobes that pull the mode without shortening the
grating, and is therefore the control to reach for first. Where both targets
remain unmet, the trade is genuine and is to be presented as such rather than
optimised away.

## Design Order

1. Fix the cross-section. A single lateral mode is required, assessed against
   the **slab** index and not the cladding index.
1b. **Match the modes across the butt joint before anything else is sized.** A
   single lateral mode in each section is the easy part, and it is not the part
   that fails. The gain chip is ordinarily a deeply etched high-confinement
   III-V guide and the passive circuit is a shallow-etched dielectric one, so
   the two mode fields differ in both transverse dimensions. A mismatch is
   charged three times over: as insertion loss, which raises the threshold and
   broadens the linewidth through the power; as a reduction in the effective
   mirror the gain chip sees, which is what the lever acts on; and as a
   parasitic Fabry-Perot between the chip facet and the reflector, which
   superimposes its own comb on the compound cavity and can override the
   mode-hop-free range computed from the intended one. Compute the overlap
   integral, the Fresnel term and the alignment tolerance separately, since they
   are separate quantities and only the first is geometry.
2. Fix the period from the period-averaged index for the target Bragg
   wavelength.
3. Choose k from the required reflectivity, then L from kL. Check the resulting
   bandwidth against the transform limit.
4. Compute r. Where the continuous tuning range is short, shorten the gain chip
   and the feed before weakening the grating further.
5. Apodise. Check the sidelobe level and the resulting chirp linearity.
6. Size the electrodes. Check the optical overlap with the metal and the drive
   bandwidth against the harmonics of the intended waveform.
7. Layout, DRC, verify.

## The Intracavity Phase Section

A second electrode over passive guide moves the **comb** without moving the
**mirror**, so the two are driven in step and the hand-over never occurs. **The
hop is removed as a mechanism rather than positioned outside the sweep**, which
removes the thermal commissioning step and the reliance on a thermal setting
holding over the life of the part.

### The grating cancels out of the sizing

The phase the section must supply is the mirror-to-comb slip expressed as
round-trip phase, and because `(1 - r) * tau_rt = tau_u` exactly,

    phi_needed = 2*pi * drift / FSR = 2*pi * tau_u * S * V_mirror

**No grating quantity appears.** Measured across four post gaps spanning
reflectivity 0.93 to 0.76 and stop band 10.05 to 6.38 GHz, `phi_needed` did not
move. The section is therefore sized once, from the passive delay and the mirror
drive alone, and any mirror goes behind it. **Design the section first and choose
the grating afterwards.**

### It must cancel the slip it creates, so solve for the fixed point

The section is passive cavity length, so its own delay enters `tau_u`, which is
what sets the phase it must supply. Sizing it against the phase required without
it understates the length. Solve self-consistently:

    L = tau_0 * S * V_m / (2*dn_per_V*V_p/lambda - 2*n_g*S*V_m/c)

The length diverges as the denominator closes. **The escape is an axis the
compensator does not share with its own load**: a phase drive separate from the
mirror's raises what the section supplies without raising what it must supply.
At a phase drive equal to the mirror's, one design ran to 3583 um and did not fit
the die; at twice the mirror drive it fitted in 900 um.

**Where a compensator sits inside the loop it corrects, its own contribution
belongs in the requirement before the sizing is believed.**

### The sizing rule and the performance claim are one statement

Differentiating the resonance condition with the section's phase included,

    df/dV = r*S - (dphi_ps/dV) / (2*pi*tau_rt)

reaches `S` exactly when `dphi_ps/dV = -2*pi*tau_u*S`, which is `phi_needed` per
volt. **A section sized to cancel the slip tunes the laser at the mirror rate by
construction.** Agreement between the closed form and a mode-tracking sweep is
therefore the check that the section works, and not an independent result.

### Grade the mechanism, not only the performance

The continuous excursion with the section driven is the performance. Two
conditions carry it and both deserve their own acceptance row:

* **the phase margin** `phi_avail / phi_needed`, whose physical bound is unity;
* **the hand-over count** with the section driven, whose bound is zero.

A design graded on the excursion alone detects an insufficient section only
through a missing value, which reads as an absent measurement rather than as a
named condition. **The margin is also nearly process-independent**: both
`phi_avail` and `phi_needed` scale with the mirror tuning `S`, so `S` cancels and
the ratio reduces to a function of `tau_u` and the group index. A corner sweep
confirms it and does not bound it. **What bounds it is the as-built passive
length and the phase-electrode gap.**

### What the section displaces

A compensator often makes an earlier compromise redundant. Passive delay bought
by lengthening a feed, to lower the active fraction and with it the linewidth, is
supplied by the section instead. **After adding a component, re-ask what every
earlier compromise was bought for.** Returning one such feed recovered the
Pockels lever from 0.547 to 0.630 with the linewidth better than before.

### Why the tuning is not moved entirely into the section

Driving the section alone slides the comb under a stationary stop band, so the
lasing mode walks off the reflection peak while a neighbour approaches it. The
hand-over occurs at about half a free spectral range whatever phase is
available. **The mirror must move to carry the frequency and the section must
move with it to prevent the hop.** Neither electrode is redundant.

## Diagnostics

| observation | probable cause |
|---|---|
| the laser tunes at approximately half the mirror rate | r is near 0.5; the cavity is dominated by untuned length |
| the mode hops mid-sweep | the continuous excursion is below the required span; raise r |
| the range is short but no hop occurred in the sweep | the drive limit, not the cavity. Compare the range against the drive voltage times the tuning rate before touching the grating |
| the swept excursion moves by tens of per cent when a passive length changes by microns | the cavity phase, which is the round-trip path modulo one wavelength and which no process holds over a centimetre cavity. Write the requirement against the phase-independent quantities and hold the swept figure at `info` |
| the fitted tuning slope and the lever route r*S differ by more than about 15 % | the fitted slope is taken over whichever hop-free segment the sweep exposed, so it carries that segment's dispersion and its position. Name which route each downstream figure used |
| every corner failure sits at one level of one process parameter | the finding is about the window and not the design. Establish the tolerance the design actually requires by walking that parameter until each bound is crossed, and compare it against what the process states |
| a metric is flat across the whole process window | it is insensitive, or no declared excursion reaches it. Name the excursion that moves it before reporting it as stable |
| the range moves when the grating length is changed, with no hop either side | the tuning rate moved, not the mode-hop boundary. The lever enters the rate, and the rate times the drive limit is what was measured |
| SMSR is marginal | the FSR is small relative to the mirror bandwidth; shorten the grating or narrow the mirror |
| chirp nonlinearity is high | the grating is unapodised and its sidelobes are pulling the mode |
| the linewidth is high | check the mirror reflectivity, the output power, and the active fraction tau_gain/tau_roundtrip; the extended-cavity reduction enters squared |
| the linewidth broadens and the power falls together toward the end of the sweep | free-carrier absorption, where the tuning is by injection. The loss rises with the same carriers that shift the index |
| the linewidth differs by an order of magnitude either side of the reflection peak | detuned loading acting through the gain chip's alpha_H. Establish which flank narrows before choosing the operating point |
| the coupling loss is far above the overlap calculation | the mode fields are mismatched across the butt joint, or the joint is misaligned. Separate the overlap from the Fresnel term and from the alignment before adjusting either |
| frequency jitter between roughly 10 Hz and 10 kHz | mechanical rather than optical. Relative motion of the gain chip and the passive circuit at nanometre scale is converted into cavity phase. It is a packaging finding and no grating change addresses it |

## Linewidth, and the Side of the Peak the Mode Sits On

The Schawlow-Townes-Henry expression carries the linewidth enhancement factor as
(1 + alpha_H^2), and alpha_H is ordinarily between 2 and 6 for a semiconductor
gain medium. That factor alone accounts for an order of magnitude, so the gain
chip and not the mirror is the usual origin of a disappointing linewidth.

A second effect operates and is not in that expression. Where the mirror
reflectivity varies with frequency, the mode does not sit at an extremum of the
loss but on a flank of it, and the resulting frequency-dependent loss acts on the
same alpha_H that broadens the line. This is **detuned loading**. A frequency
excursion is then opposed or reinforced by the change in mirror loss it produces,
and the linewidth is narrowed or broadened accordingly.

Three consequences follow.

**The sign matters and is not universal.** Narrowing occurs on one flank and
broadening on the other, and which is which follows from the sign of alpha_H
together with the sign of the mirror loss slope. It is to be established for the
device in hand rather than assumed from another one.

**The magnitude is not a correction.** An order of magnitude either way is
ordinary, so a linewidth quoted without stating where in the reflection band the
mode sits is quoted without its dominant term.

**It couples to the tuning.** Tuning the mirror moves the mode across the flank,
so the linewidth varies over the sweep. A single figure quoted at the centre
describes neither end.

Neither this chain nor the expression above models detuned loading. The reported
linewidth is the flat-mirror result, and it is to be read as an ordering.

## Model Boundaries

The mode-hop-free range is measured between hops and not from zero bias. The
figure obtained without a DC offset is a property of the cavity phase, which is
arbitrary at layout time: on one baseline the same cavity gave 0.37 GHz and
6.86 GHz for lengths differing by a fraction of a wavelength. Where the two
differ, a bias offset is required and is to be stated.

The coupling interface is assumed rigid and ideal. Sub-wavelength residual
reflections at the butt joint, below about -40 dB, are excluded, and in practice
they form parasitic sub-cavities whose comb can override the predicted
mode-hop-free range. Relative mechanical motion across that joint is excluded
altogether, and an extended cavity with a physical assembly interface converts
ambient vibration into frequency noise directly.

Free-carrier absorption is not modelled. Where a tuning section is driven by
current injection, the loss rising with the index change is a first-order effect
on the threshold, the power and the linewidth, and none of the three is predicted
here.

The cavity model is single-mode and steady-state. Rate-equation dynamics,
relative intensity noise and the self-injection-locking regime are excluded. The
SMSR figure scales with the assumed spontaneous-emission factor and is to be read
as an ordering rather than as an absolute value.

Linewidth is evaluated by Schawlow-Townes-Henry with the extended-cavity
(tau_a/tau_rt)^2 factor. Agreement within a factor of approximately 1.5 against
measurement is the realistic expectation, the gain-chip parameters being rarely
known independently.
