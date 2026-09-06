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

## What is assumed in the transfer

The measurement is on lithium tantalate and the extended-DBR is lithium niobate.
Carrying sigma across assumes the mechanism is common. The proposed mechanism,
an overstatement of the third-order Fourier amplitude for a perturbation carried
by posts beside the guide rather than by a corrugation of it, is a property of
the geometry and the order rather than of the film, and the two gratings share
both. It remains an assumption and is recorded as one.

**No direct measurement of the lithium-niobate grating exists.** Its own
time-domain solve moved 86 per cent with mesh and is unresolved, and no
band-structure payload exists in the run tree on either platform. A solve of it
at the settings that resolved this one is the measurement that would remove the
assumption, and it is running.

Until it returns, the defensible statement is narrower than a value. **The
analytic coupling is overstated on the one grating where it has been checked,
by about a factor of two, and the design of record is tuned against the analytic
coupling.** Whether the candidate's mirror is adequate therefore rests on a
transfer that has not been tested, and the reflectivity row is the one that
turns on it.

The candidate's coupling as designed is 1.476 /cm. The measured correction would
put it at 0.92 and its reflectivity below target. Sizing the mirror so that it
meets the target under both values, which needs about 17 mm rather than 11,
costs area and buys immunity to the question, and is the decision this
measurement puts in front of the design.
