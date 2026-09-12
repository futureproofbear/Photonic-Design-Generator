# The coupled-mode coupling constant of a third-order post grating, measured

*2026-09-06. Run of record `20260906-084337-ltoi300_grating_fdtd`, from
[`design_grating_fdtd.yaml`](design_grating_fdtd.yaml). The consequences for the
extended-DBR baseline are computed in
[`../edbr_tfln_baseline/`](../edbr_tfln_baseline/) and are summarised here.*

## Summary

A time-domain solve of the drawn 500 um mirror returns a coupling constant of
**1.299 /cm against the coupled-mode value of 2.459 /cm** on the identical
two-dimensional structure, a ratio of 0.528. The mesh moves that number by 5.6
per cent between resolutions 20 and 30 while the disagreement is 47 per cent, so
the disagreement is eight times its own discretisation error and survives it.

**The coupled-mode route overstates the coupling of this grating by about a
factor of two.** The consequence for the drawn mirror is that its peak
reflectivity is 0.42 per cent rather than 2.5, and that a mirror of this design
would need roughly two and a half times its length for the reflectivity the
analytic route predicts.

## What was measured

| quantity | time domain | coupled mode, two dimensions | ratio |
|---|---|---|---|
| kappa | 1.299 /cm | 2.459 /cm | 0.528 |
| kappa times length | 0.0650 | 0.1591 | |
| peak reflectivity | 0.00421 | 0.0248 | |
| Bragg wavelength | 1321.7 nm | 1318.2 nm | 1.0026 |

The grating is the one the mask draws: order 3, 445 periods of 1.1238 um over
500 um, posts 0.3 um wide on a 0.63 um gap, on the 300 nm film with a 180 nm
etch, at 1310 nm.

**The Bragg wavelength agrees to 0.26 per cent and the coupling does not, which
is the expected signature.** The period sets the wavelength and the strength of
the perturbation sets the coupling, so a model that places the stopband
correctly and misjudges its depth is wrong about the perturbation and not about
the geometry.

### Why the result is readable

The convergence guard is what makes this quotable, and it was added to this
runner on 2026-09-05 having never existed. The comparison it enables:

| | this grating | the E-DBR grating, for contrast |
|---|---|---|
| mesh shift | 5.6 % between resolutions 20 and 30 | 86 % between 10 and 20 |
| departure from coupled mode | 47 % | 26 % |
| verdict | the departure survives the mesh | the mesh is the larger term |

The same stage reaches opposite verdicts on the two, and for the right reason.
On the E-DBR grating no conclusion is available and the stage withholds the
physical reading. The difference between the two structures is the strength of
the perturbation: this one has an effective-index modulation of 1.068e-3 and
that one 3.744e-4, and the weaker one is not resolved at a mesh this host can
afford.

### What the run does not establish

The reflectivity of 0.0042 sits on an unaccounted background of 1.6 per cent,
reflection and transmission summing to 0.984 at the peak. That bounds the
confidence in the 47 per cent and is the first thing to improve.

Both routes are two-dimensional reductions by effective index. The measurement
says the two disagree on the same reduced structure; it does not say that either
matches the drawn device.

No apodisation, no fabrication tolerance and no three-dimensional solve enters
any figure here.

## What it implies, and the knob the chain already carried

`grating.profile_sigma_um` suppresses the m-th Fourier harmonic of the
longitudinal index profile by `exp(-(2 pi m sigma / period)^2 / 2)`. Its own
comment in `config.py` states that the suppression is quadratic in the order,
that an assumption benign at first order is not benign at third, and that **the
value is a measurement obtained by setting the coupled-mode kappa against a
band-structure or time-domain solve**. This grating is third order, and this is
that measurement.

Inverting the measured ratio gives **sigma = 67 nm**.

A second and unrelated route lands close to it. The extended-DBR baseline
reproduces a published device whose peak reflectivity is stated as about 75 per
cent, and the chain computes 97.5 per cent from the same geometry. The sigma
that reconciles those two is **84 nm**.

Two estimates from wholly independent evidence, one a time-domain solve on
lithium tantalate and the other a published reflectivity on lithium niobate,
agree within a quarter of each other.

## The consequence for the extended-DBR

**The design of record is `design_candidate.yaml`, not `design.yaml`.** The
first version of this section propagated sigma through the latter and reported
that the correction moved two acceptance rows from unmet to met. That is true of
`design.yaml` and it is the wrong file: it is a superseded baseline whose
reflectivity of 0.975 already fails its own target of 0.75, and the candidate
exists because that was fixed. The candidate opens the post gap from 0.63 to
0.855 um and lengthens the mirror from 7.25 to 11 mm, landing a coupling of
1.476 /cm and a reflectivity of 0.832, which passes.

On the design of record the correction runs the other way.

| quantity | sigma 0, as designed | sigma 67 nm, the measured value | acceptance |
|---|---|---|---|
| kappa /cm | 1.476 | 0.918 | |
| kappa times length | 1.624 | 1.010 | |
| peak reflectivity | 0.832 **met** | 0.564 **unmet** | = 0.75 ±20 %, so 0.60 to 0.90 |
| stopband FWHM /GHz | 9.475 | 7.267 | 5 to 14, met either way |
| mode-hop-free range /GHz | 13.23 | 13.78 | ≥ 8, met either way |
| side-mode suppression /dB | 50.65 | 48.56 | ≥ 40, met either way |
| penetration depth /mm | 3.134 | 4.170 | |
| chirp nonlinearity /% | 1.032 | 0.467 | |

Every figure in the sigma 67 column is measured, from run
`20260906-112749-edbr_cand_sigma67`. An earlier version of this table carried
values interpolated between the sigma 0 and sigma 84 runs, which were wrong by
up to five per cent and, on the reflectivity, by more than the width of the
target's tolerance band.

**Correcting the coupling breaks the mirror the design of record relies on.**
Reflectivity falls from 0.832 to 0.564, below the 0.60 floor of its target. The
candidate is tuned against the analytic coupling, so if that coupling is
overstated by the factor measured here, the candidate is under-coupled and its
mirror is too short by roughly sixty per cent.

Nothing else the candidate is graded on moves out of specification. The
mode-hop-free range, which is the requirement the published device is built
around, is met throughout and improves slightly, the penetration depth carrying
the tuning lever with it. **The correction costs reflectivity and buys tuning**,
which is the same trade seen on the superseded baseline running in the opposite
direction because the two sit on opposite sides of the target.

### The two paper-derived constraints disagree

The published device is quoted at about 75 per cent reflectivity and at a
stopband of 6.5 GHz simulated and 8 GHz measured. Those two do not select the
same sigma on the candidate geometry.

| constraint | sigma it implies |
|---|---|
| reflectivity 0.75 on the candidate | 45 nm |
| the LTOI time-domain measurement | 67 nm |
| stopband 6.5 GHz on the candidate | above 67 nm |

The reflectivity wants less suppression and the stopband wants more. A single
value of sigma does not reconcile both on this geometry, which is evidence that
sigma is absorbing more than one effect, or that the published pair is not
self-consistent with the geometry as this chain draws it, or that the transfer
across platforms does not hold. **The three lie within a factor of two of each
other and none is settled**, and an earlier version of this section claimed the
first two agreed within a quarter, which was an artifact of anchoring on the
superseded baseline.

## The transfer assumption is removed: the E-DBR grating was measured directly

Run `20260906-101437-edbr_tfln_grating_fdtd`, 450 periods of the candidate's own
grating at resolution 30 with the guard at 20.

| | LTOI, this study | E-DBR candidate, measured directly |
|---|---|---|
| kappa, time domain | 1.299 /cm | 0.861 /cm |
| kappa, coupled mode in the plane | 2.459 /cm | 1.323 /cm |
| ratio | 0.528 | 0.651 |
| mesh shift | 5.6 % between 20 and 30 | 5.5 % between 20 and 30 |
| **sigma implied** | **67.3 nm** | **64.0 nm** |

**Two time-domain measurements, on two films, at two periods, with two post
gaps, give sigma within five per cent of each other.** Nothing was transferred
between them. The earlier version of this report carried the cross-platform
transfer as its principal assumption; it is now a corroboration instead.

The same grating at resolution 20 with the guard at 10 had moved 86 per cent and
was unresolved. Raising the primary mesh to 30 and lengthening the section from
300 to 450 periods resolved it. **The earlier run was not evidence that the
structure could not be measured; it was evidence that it had not been.**

The signal is poorer here than on LTOI. The reflectivity of 0.00254 sits on an
unaccounted background of 3.3 per cent, against 0.42 per cent on 1.6 for LTOI,
so the ratio of background to signal is thirteen to one rather than four. The
35 per cent departure is seven times its own mesh shift and stands, and it is
the less well conditioned of the two measurements.

## The smoothing is tested against an alternative, and survives

The drawn duty of 0.2669 sits close to the null of the third-order Fourier
amplitude at one third, where that amplitude is small and varies steeply. An
effective post 37 nm longer than drawn, 19 nm per edge, reproduces the measured
ratio exactly. **Two parameterisations therefore fitted the same measurement**,
and they are not the same physics: a smoothing is independent of duty, while an
effective lengthening is not.

They diverge away from the null, so the test is to move the duty. Run
`20260911-094049-ltoi300_grating_duty015` repeats the measurement with the posts
shortened to 0.169 um, a duty of 0.1504, and everything else identical.

| duty | smoothing predicts | lengthening predicts | measured |
|---|---|---|---|
| 0.2669, as drawn | 0.528 | 0.528 | 0.5283 |
| **0.1504** | **0.528** | **0.999** | **0.5067** |

The measurement lands four per cent from the smoothing prediction and a factor
of two from the alternative. **The lengthening reading is eliminated**, and with
it the concern that the original result was an artefact of measuring beside a
null.

The test is also the better measurement of the two, in every respect that the
original was weak:

| | duty 0.2669 | duty 0.1504 |
|---|---|---|
| peak reflectivity | 0.00421 | 0.01097 |
| unaccounted background at the peak | 1.6 % | 0.74 % |
| mesh shift, resolutions 20 to 30 | 5.6 % | **0.24 %** |

The analytic amplitude is 1.68 times larger away from the null, so the signal
rises while the background falls, and the convergence guard reads 0.24 per cent
against a 49 per cent departure. The disagreement is two hundred times its own
discretisation error.

### Three measurements of sigma

| | duty | ratio | sigma |
|---|---|---|---|
| LTOI as drawn | 0.267 | 0.528 | 67.4 nm |
| E-DBR, measured directly | 0.230 | 0.651 | 63.5 nm |
| LTOI at the shifted duty | 0.150 | 0.507 | 69.5 nm |

Two films, two wavelengths, and a duty varied by nearly a factor of two, giving
sigma within nine per cent. **A parameter that holds across the variable chosen
to break it is doing work rather than absorbing a local sensitivity.**

What none of the three tests is the effective-index reduction itself. All are
plane against plane, so they establish that the two routes disagree on the same
reduced structure and say nothing about whether either matches the drawn device.

## What it costs the design, and what fixes it

At the sigma measured on its own grating the candidate's coupling falls from
1.476 to 0.961 /cm and its mirror reflectivity from 0.832 to 0.593, which fails
the floor of its target by one per cent of the value. Everything else it is
graded on continues to pass.

The remedy is not length, though length works. **The directed search finds a
better one**: closing the post gap from 0.855 to 0.750 um restores the mirror at
no area cost and meets all twelve targets, where lengthening meets ten. The post
gap moves the reflectivity with an elasticity of -5.79 and is the only one of
the design's four declared free parameters that moves it at all; the other three
cannot reach the requirement from either bound. The candidate is confirmed by an
independent full-chain run, `20260910-005501-edbr_postgap075`, mask and rule
check included.

| | post gap /um | mirror /mm | kappa /cm | reflectivity | targets met |
|---|---|---|---|---|---|
| as drawn | 0.855 | 11.0 | 0.961 | 0.593 | 9 of 12 |
| lengthened by hand | 0.855 | 13.5 | 0.961 | 0.711 | 10 of 12 |
| **the search's candidate** | **0.750** | **11.0** | **1.719** | **0.890** | **12 of 12** |

The hand analysis varied the parameter it thought of first, and length is not
among the four the design declares free. Lengthening the mirror remains a valid
answer and is recorded below for the trade it represents:

| mirror | kappa times length | peak reflectivity | acceptance | stopband /GHz |
|---|---|---|---|---|
| 11.0 mm, as drawn | 1.057 | 0.593 | **unmet** | 7.42 |
| 12.0 mm | 1.153 | 0.645 | met | 7.10 |
| **13.5 mm** | 1.297 | **0.711** | met | **6.72** |
| 15.0 mm | 1.441 | 0.766 | met | 6.43 |

**Lengthening the mirror from 11 to about 13.5 mm restores the reflectivity and
improves the agreement with the published device at the same time.** At that
length the stopband is 6.72 GHz against the 6.5 GHz the paper simulates, where
the design as drawn gives 9.48. The two constraints that pulled in opposite
directions at fixed length are satisfied together once length is the free
variable, which is the resolution of the tension the earlier version of this
report recorded and could not settle.

The cost is 23 per cent more mirror. The mode-hop-free range, the side-mode
suppression and the chirp linearity all improve slightly across that range, so
nothing is traded away for it.

## The design value

**kappa = 0.96 /cm for the E-DBR candidate**, from a direct time-domain
measurement of its own grating, against the 1.476 the coupled-mode route gives.
Equivalently, `grating.profile_sigma_um: 0.064`.

**kappa = 1.30 /cm for the LTOI mirror as drawn**, against the coupled-mode
2.459 in the plane, or `profile_sigma_um: 0.067`.

Both rest on two-dimensional reductions on both sides of the comparison, so they
say the two routes disagree on the same reduced structure and do not say that
either matches the drawn device. No three-dimensional solve, no apodisation and
no fabrication tolerance enters either figure.
