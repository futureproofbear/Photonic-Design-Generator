# A textbook microring on silicon nitride, and what its first run found

A study of an all-pass microring resonator on a 200 nm stoichiometric silicon
nitride film in silica, conducted on 2026-09-14 and 2026-09-15. The concept of operation is in
[`DESIGN_CONCEPT.md`](DESIGN_CONCEPT.md) and was written before any target was
declared and before any code was written.

## The verdict

**The run of record is `runs/20260915-000630-sin200_ring`**, and every figure in
this document comes from it except where another run is named. It ran the whole
of the design's stage list, including the time-domain coupler solve, and met 7 of
7 targets with 0 unmet at `must` and 0 at `should`.

That verdict rests on six findings the run emitted, each acknowledged with its
reason in `design.yaml` under `warnings.acknowledged`: the two mode solvers
disagreeing on the absolute index, three bend radii the conformal solve refuses,
the coupler solve's unaccounted power, the two-dimensional reduction on a film
that carries no slab, the extinction following an assumed loss, and the
extinction requirement being a tolerance on that loss. The verify stage records
`findings_enforced: false`, so a finding does not gate the verdict and the
acknowledgement is what puts each on the record.

**The device is posed to exercise the chain and not to be fabricated.** It is the
first design in the repository to declare silicon nitride, the first to declare
an etch depth equal to its film thickness, and the first to assemble a resonator
of any kind. The first run of such a design is a test of the chain, in the sense
of [`rules/generic/first-exercise.md`](../../rules/generic/first-exercise.md).

**Six defects in the chain were found and corrected, and one error in the targets
written for this design.** Five of the six sat in code that no previous design
had reached, and are numbered 1 to 4 and 6 under "Six findings of the first run".
The sixth is under "The coupler, by time-domain solve": it had run on every
coupler ever solved and reported nothing, its threshold being set against the
wrong quantity. The entry numbered 5 is an error in a target written here rather
than a defect in the chain, and it is listed with the others because it is the
same mistake in a different place.

## What was built

The chain carried no resonator. Every stage models one component; the `cavity`
stage combines components for a gain chip behind a feed and a distributed mirror,
and the `circuit` stage states in its own opening that the arrangement it encodes
"cannot be applied to a resonator on a bus". The consequence was checkable
before this study: no design in the repository declared a target on a loaded
quality factor, on an extinction, on a finesse or on a free spectral range, while
the lithium tantalate ring study computed all four in a script beside itself.

Two pieces were added.

[`src/picchain/resonator.py`](../../design-chain/src/picchain/resonator.py)
holds the closed forms of one loop and one lossless point coupler, and
[`src/picchain/stages/s19_resonator.py`](../../design-chain/src/picchain/stages/s19_resonator.py)
is the stage that supplies the two numbers and reports what follows.
[`tests/test_resonator.py`](../../design-chain/tests/test_resonator.py) reaches
every quantity by a second construction: the two were written independently, and
the test rebuilds the transfer function by summing the circulating field round
trip by round trip, finds the resonance width by bisection on that sum, finds the
order spacing by locating two consecutive resonances of a dispersive phase, and
checks the loaded width against the intrinsic and coupling widths taken in
series.

## The design point

| | |
| --- | ---: |
| Film | 200 nm Si3N4, fully etched |
| Guide width | 1.30 um |
| Cladding and buried oxide | SiO2 |
| Wavelength | 1.550 um |
| Ring radius | 100 um |
| Round trip | 628.3 um |
| Coupler gap | 1.50 um |
| Power coupling | 3.653423e-3, solved |
| Propagation loss | **0.2 dB/cm, an assumption** |

The width was chosen from a probe of the mode count, described under "Two probes
that are not chain runs" below. The radius was chosen to place the free spectral
range inside the window a tunable source addresses and to keep the bend
comfortable.

**The coupling is solved on every run.** The `fdtd` stage is in this design's
stage list, so the run of record records
`resonator.kappa_squared_source: "fdtd point-coupler solve"` and takes
3.653423e-3 from it. The solve is reused from the cache where the job and the
runner both match, which is why the run of record costs 61 seconds rather than
eight minutes. `design.yaml` carries the same figure truncated to four as
`resonator.kappa_squared`, and that fallback is what the resonator stage reads on
a host where meep cannot be reached; a run that used it says so in the same
field. The truncation costs 0.004 dB of extinction.

## What the chain returned

| Quantity | Value |
| --- | ---: |
| `n_eff` | 1.527377 |
| `n_g` | 1.801436 |
| Guided modes | 1 |
| Guidance floor | 1.444024, being the cladding |
| Film confinement | 0.3167 |
| Free spectral range | 2.1226 nm, 264.9 GHz |
| Resonance width | 2.2139 pm |
| Loaded Q | 7.001e5 |
| Intrinsic Q | 1.586e6 |
| Finesse | 958.7 |
| Extinction | 18.638 dB, overcoupled |
| Radiation caustic at 100 um | 5.64 um, being 11.4 lateral decay lengths |

The group index here is the stage's own dispersive derivative. The separate
figure of 1.801431 quoted under "Two quantities were bounded" comes from a
central difference across three runs, which is a different construction of the
same quantity.

## The loss is an axis and not an input

No measurement of a silicon nitride device is held in this repository. The
propagation loss is therefore swept, and the device is reported across the range
a nitride process spans.

| Loss, dB/cm | Extinction, dB | Loaded Q | Intrinsic Q | Regime | Width, pm |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.05 | 3.48 | 1.047e6 | 6.343e6 | over | 1.48 |
| 0.10 | 7.26 | 8.984e5 | 3.171e6 | over | 1.73 |
| 0.20 | **18.64** | 7.001e5 | 1.586e6 | over | 2.21 |
| 0.50 | 9.68 | 4.212e5 | 6.343e5 | under | 3.68 |
| 1.00 | 4.49 | 2.531e5 | 3.171e5 | under | 6.12 |

**The extinction peaks at the critical loss and falls on both sides of it, and
the `must` row on it is met at one of the five values.** A coupling drawn once is
critically coupled at one propagation loss and at no other, and this coupling is
critical at 0.253 dB/cm.

### An extinction requirement is a tolerance on the loss

The useful statement is the band of losses over which the requirement is met
rather than the extinction at one assumed loss. For this coupler the 10 dB row is
met between **0.131 and 0.487 dB/cm**, a factor of 3.71 about the critical 0.253.

The width of that band follows from the required extinction alone. Writing
`r = 10^(-E/20)`, the round-trip loss may lie between `(1-r)/(1+r)` and
`(1+r)/(1-r)` times the critical loss:

| Required extinction | Admissible loss, relative to critical | Width |
| ---: | :--- | ---: |
| 3 dB | 0.171 to 5.848 | 34.2x |
| 10 dB | 0.520 to 1.925 | 3.71x |
| 15 dB | 0.698 to 1.433 | 2.05x |
| 20 dB | 0.818 to 1.222 | 1.49x |
| 30 dB | 0.939 to 1.065 | 1.13x |

That table depends on the required extinction and on nothing else: the platform,
the radius and the coupler all cancel. **On a stack whose propagation loss nobody
has measured, an extinction requirement is a statement about how well the loss
must be known**, and a 20 dB requirement here would demand it to a fifth. The
chain computes the band from the design's own declared target, so the two cannot
drift apart, and reports it as a finding on every run.
`loss_window_for_extinction` is verified against bisection of the transfer
function at five extinctions and against three rings differing in radius and
coupling.

## The coupler, by time-domain solve

Four gaps were solved in two dimensions at resolution 40, each against a
normalisation run of the bus alone and each with a convergence guard at
resolution 20.

| Gap, um | Run | `kappa^2` | Unitarity | Residual / `kappa^2` | Mesh shift | Critical loss, dB/cm |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0.50 | `-223705` | 2.333816e-1 | 0.938123 | 26.5 % | -2.2 % | 18.37 |
| 1.00 | `-224225` | 3.018435e-2 | 0.992015 | 26.5 % | -3.8 % | 2.118 |
| **1.50** | `-225048` | **3.653423e-3** | 0.999218 | **21.4 %** | **-8.6 %** | **0.253** |
| 2.00 | `-225835` | 3.871091e-4 | 0.999865 | 34.8 % | -1.3 % | 0.027 |

**A 0.5 um gap is two orders too strong for a 100 um ring**, and its solve
accounts for only 93.8 per cent of its input, the two guides being close enough
at that separation to stop behaving as a point coupler. The gap was raised until
the coupling reached the order the loop loss requires, and 1.50 um is the drawn
value.

**The unitarity guard was absolute, and an absolute guard is silent wherever the
coupling is weak.** It raises above one per cent of the input, and a point
coupler removes a small fraction of the input by construction, so the shortfall
falls with the coupling. Across these four gaps the residual fell by a factor of
460 in absolute terms and held between a fifth and 35 per cent of the coupling
throughout, and the guard reported it on the one gap whose coupling was two
orders too strong to be used. A residual holding at a fixed fraction of the
measurand across three orders is a systematic rather than numerical noise; the
likeliest cause is the crossed power reaching the ring monitor displaced and
tilted, the ring curving away from the plane its mode is projected onto.

The stage now reports `fdtd.unitarity_residual_over_kappa2` and raises a finding
above five per cent. The four runs above predate that change and carry neither
the field nor the finding. The run of record carries both, recording 0.213984 at
the drawn gap, and `design.yaml` acknowledges it.

**The consequence for this design is bounded and it survives.** If the missing
power did cross, the coupling is understated by about a fifth and the critical
loss moves from 0.253 to 0.307 dB/cm, which is inside the 0.131 to 0.487
band over which the 10 dB row is met. The mesh shift of 8.6 per cent at the drawn
gap moves the extinction between 16.1 and 22.8 dB, also inside it.

## Six findings of the first run

**1. A uniform column crashed the one-dimensional slab solve.** The column beside
a fully etched ridge is cladding above and buried oxide below, which is one
material. The slab solve places its spectral shift at the largest index in the
column, and on a uniform column that shift is an eigenvalue exactly, so the
factorisation of the shifted matrix is singular. The message returned was
`RuntimeError: Factor is exactly singular` from three frames inside ARPACK,
naming neither the film nor the etch. The solve now returns an empty list for a
column carrying no index above the medium bounding it.

**2. The guidance floor fell back to zero, which admits everything.** The mode
stage read `n_slab[0] if n_slab else 0.0`, and the floor is the index a mode must
exceed to count as laterally bound. A floor of zero admits every eigenvalue the
solver returns, and the solver returns two more than the design asks for, so this
strip would have been reported as carrying six guided modes against a design
declaring four, and the `must` row on single-mode operation would have failed on
a device that meets it. The run of record's `n_eff_spectrum` holds the six:
1.527377, four states at the cladding index, and one below it. The floor is now
the cladding where there is no slab, and `mode.guidance_floor_is` records which
of the two was used. **This is the worse of the two defects**, the crash at least
being visible.

**3. The slab solve admitted the continuum.** Its filter kept every state with a
real propagation constant, so its second mode on a guiding column was the index
of the oxide bounding it. Only the first entry is read anywhere, so the defect had
no consequence and would have acquired one the moment a caller asked for two.

**4. The effective-index reduction refused rather than taking the cladding.** The
time-domain stage raised "the effective-index reduction found no slab mode",
which describes neither of its two columns. Where the film is fully etched the
background of the reduction is the cladding, and that index is available without
solving anything.

**5. A target measured the instrument's reach rather than the device.** The
clause "the round trip may be treated as a straight guide" was first written
against the power lying beyond the radiation caustic, which the bend solve
integrates. That integral is a property of the solved window: it is undefined
wherever the caustic falls outside the window, which is the case whenever the
bend is comfortable. Here the caustic sits at 5.64 um against a window edge at
4.58 um. A ceiling on it would have passed because the instrument could not see
the quantity, and would have begun to fail only once the caustic had come inside.
The graded quantity is now the distance to the caustic in lateral decay lengths
of the straight mode, which is defined in both cases.

**6. The new stage ran before the solve it reads from.** The planner sorts
topologically and breaks ties by registration order. The resonator stage takes
its power coupling from the `fdtd` stage where that stage solved a coupler, and
`fdtd` is deliberately not a dependency, an external time-domain solve being too
expensive to force on a closed-form stage. Registered beside `bend`, the stage
came first: the run wrote a resonator payload built from the declared coupling
and then wrote the measured one beside it, reporting the source as declared. The
plan was `mode, resonator, grating, fdtd`, and it is preserved in
`runs/20260914-223705-sin200_ring/run.plan.json`. Two things were corrected. The
stage is registered after the ones it reads, and `grating` is now registered
before `fdtd`, which depends on it, so that the declared order agrees with the
dependency map and the tie-break means what it says.

## The four branches the concept asked about

[`DESIGN_CONCEPT.md`](DESIGN_CONCEPT.md) names four options no previous design
had selected and states what was to be confirmed of each before the result is
read. Each was answered, and one was answered differently from the way it was
posed. The four statements below do not map one to one onto the concept's four
rows: the second and third between them cover the concept's second and third
rows, which are the full etch and the slab.

**`film_material: Si3N4` selects the isotropic path, and `cut` is inert on it.**
This is the row answered differently from the way it was posed: the concept asked
that the anisotropy bracket report zero, and it reported that it does not apply.

`Material.eps_optical_device` returns one index for all three axes before it
reads the field, so the declared cut selects nothing. The finite-element stage's
anisotropy bracket reports `applicable: false` with the reason "every material in
the optical cross-section is isotropic". **It declined to apply rather than
returning zero**, and the absence of a complaint from it is not a pass; the
quantity it would have measured does not exist on this stack.

**A full etch leaves no slab, and no stage draws or solves one.** The run of
record's `cross_section.json` holds two shapes, the buried oxide and the ridge,
so nothing is drawn; and the column beside the ridge returns no slab mode, which
is what the corrected slab solve reports and what finding 1 above describes. The
guidance floor is therefore the cladding, which finding 2 describes.

**The two-dimensional reduction takes the cladding as its background.** Every
`fdtd.json` records `n_slab_effective_index: 1.444024`, which is the cladding
index, against `n_core_effective_index: 1.584124` for the 200 nm column through
the ridge.

**The resonator closed form agrees with an independent evaluation**, which is the
test that accompanies the module.

## Two quantities were bounded rather than assumed

**The two mode solvers disagree by 0.115 per cent on the absolute index**,
against the 0.100 per cent the chain treats as material. That is the largest
disagreement the chain has recorded, and it exceeds the next largest by a factor
of 1.33. Every cross-section this chain has solved with both solvers:

| Film | Film confinement | Transversality | Fractional disagreement in `n_eff` |
| --- | ---: | ---: | ---: |
| LiTaO3 | 0.7300 | 0.9863 | -6.1e-5 |
| LiTaO3 | 0.6522 | 0.9814 | -8.0e-5 |
| LiTaO3 | 0.8884 | 0.9750 | -9.3e-5 |
| LiNbO3 | 0.7169 | 0.9519 | -2.1e-4 |
| LiNbO3 | 0.7013 | 0.9460 | -2.8e-4 |
| LiTaO3 | 0.6447 | 0.9360 | -6.8e-4 |
| LiTaO3 | 0.5775 | 0.9405 | -8.7e-4 |
| **Si3N4, this design** | **0.3167** | 0.9544 | **-1.2e-3** |

**No mechanism is established by that table, and two candidates are refused by
it.** Transversality does not order the list: four cross-sections are less
transverse than this one and every one of them agrees better, two of them by
four to six times. Film confinement does not order it either: the highest
confinement in the table, 0.8884, sits third rather than first, and 0.7169
disagrees more than 0.6522. What can be said is that this cross-section is the
least confined by a wide margin, holding 31.7 per cent of its mode in the film
against 57.8 per cent for the next lowest, and that it carries the largest
disagreement. That is an observation about the extremes and not a relation
fitted across the set.

The finite-element solve is itself converged, its own mesh guard moving the
index by 4e-6, so the disagreement is between the two methods rather than
inside either. The column above is the fractional disagreement that
`fem.n_eff_bare_rel_delta` reports; in index units this design's is 1.76e-3.

No target reads the absolute index. The group index does, through the free
spectral range, and the finite-element cross-check returns no dispersion, so that
quantity had no independent bound at all. Three runs of each solver over 1.545 to
1.555 um closed it:

| | finite difference | finite element | disagreement |
| --- | ---: | ---: | ---: |
| `n_eff` at 1.550 um | 1.527377 | 1.525614 | **-0.115 %** |
| `n_g`, by central difference | 1.801431 | 1.801137 | **-0.016 %** |
| Free spectral range | 2.12259 nm | 2.12294 nm | 0.016 % |

**The derivative is bounded seven times better than the value it is taken from**,
the systematic part of the disagreement being nearly common to the three
wavelengths and cancelling in the difference. The three runs are
`-223114`, `-223157` and `-223241`.

## Two probes that are not chain runs

Two figures quoted above come from scripts written against the chain's solvers
rather than from any run in `runs/`. Each is named here so that no reader looks
for an artifact that does not exist.

**The single-mode width.** The mode solver was called directly at five widths on
this cross-section, returning one guided mode to 1.50 um and two at 1.80 um. Only
1.30 um is solved by any run.

**The oxide truncation.** The optical cross-section models the buried oxide to
1.8 um and puts a hard wall below it, and that depth was chosen for a strongly
confining ridge. Calling the geometry builder at 1.8 um and at 3.0 um moves the
effective index by 4.6e-5, which is a fortieth of the disagreement between the
two solvers, so the default is adequate on this stack. **The depth is not a
design field.** `s01_mode.py` passes 1.8 um whenever no electrode is present,
whatever `platform.box_thickness_um` says, so this probe cannot be repeated
through `design.yaml`, and the 3.0 um the design declares does not reach the
optical solve.

## What is not settled

**The decay constant of the two-dimensional reduction, against the real
cross-section.** The coupler configuration states in its own comment that the
reduction holds where the unetched film is continuous across the gap, which a
fully etched strip breaks. An earlier revision of this report treated that doubt
as cleared, and **the claim is withdrawn**. The reasoning was that the decay
implied by the gap ladder, being 2.045, 2.112 and 2.245 per micrometre over the
three intervals, sits near the 2.017 of the full cross-section solve. It does not
follow. **The ladder measures the reduced problem and not the real one.** The
coupler propagates a lateral profile of core 1.584124 on a background of
1.444024, and the decay of that problem's own guided mode is about 2.18 per
micrometre, which is what a re-solve of the reduced profile returns. The three
ladder intervals all exceed 2.017, they rise monotonically, and a regression over
all four gaps gives 2.132. They discriminate between 2.017 and 2.18 in neither
direction.

Two things stand in the way of settling it. The extraction assumes the prefactor
of `kappa^2 ~ exp(-2 gamma g)` holds still as the gap opens, and the length over
which the ring stays close to the bus does move with the gap, so the ladder gives
an indicative decay rather than a measured one. And the reduced problem's own
prediction depends on which polarisation the lateral step is solved in, which the
one-dimensional re-solve and the propagation need not treat alike. The question
is open. If there is an error its direction is that the reduction decays faster
than the real cross-section and therefore understates the coupling.

**About a fifth of the coupled power is unaccounted for, one-sidedly.** The
residual holds between a fifth and 35 per cent of the coupling across four gaps
while falling by a factor of 460 in absolute terms, which is a systematic. If
that power did cross, the coupling is understated by about that much. The design
point survives it, as set out above. Settling it needs the ring monitor placed
and oriented on the ring's own axis, or a three-dimensional coupler, and the
chain builds three dimensions for the taper alone.

**Bend radiation is computed by no stage.** The caustic at the ring radius sits
11.4 lateral decay lengths from the guide, which places the field at it below
`e^-22` in power, and that is a proxy rather than a loss. The conformal solve
stops returning a bound mode between 100 um and 60 um on this stack, so a tighter
ring would need a leaky-mode or time-domain method.

**The propagation loss is assumed.** It is the one quantity that decides the
extinction, and no measurement of a silicon nitride device is held in this
repository. The design answers that by reporting the band of losses over which
its requirement is met rather than a figure at one of them.

**The device has been validated against arithmetic and against a second solver,
and against no fabricated ring.** The closed forms are checked against
independent constructions of them, and the cross-section against a full-vectorial
solver. A measurement would settle the propagation loss, the coupling and the
bend loss together, and it is the one instrument absent here.

## The run register

19 run directories sit under `runs/`. 12 carry a resonator payload, of which
11 are superseded, and the design file that produced each is stamped into
its own `design.resolved.json`.

| When | Run | What was run | Cost | What it established |
| --- | --- | --- | ---: | --- |
| 2026-09-14 | `-222445`, `-222941`, `-223508` | `mode, fem, bend, resonator, verify`, coupling declared at 0.005 | 49 s each | the cross-section and the bend; five defects in the chain and one in the targets. **Superseded**, the coupling being a placeholder |
| 2026-09-14 | `-223114`, `-223157`, `-223241` | `mode, fem` at 1.545, 1.550 and 1.555 um | 37 s each | the group index bounded to 0.016 per cent, seven times better than the index |
| 2026-09-14 | `-223705` | `fdtd` at a 0.50 um gap, under the stage order that placed the resonator first | 225 s | the coupling two orders too strong; unitarity 0.938. **Its resonator payload is withdrawn**, having been written before the solve it should have read |
| 2026-09-14 | `-224225`, `-225048`, `-225835` | `mode, grating, fdtd` at 1.00, 1.50 and 2.00 um | 492, 455, 476 s | the gap ladder; the drawn gap; the relative-residual defect |
| 2026-09-14 | `-225934`, `-230407`, `-230608`, `-233639`, `-233824` | the chain at the transcribed coupling, each superseded by the next as a finding or an acknowledgement was added | 97, 100, 86, 70, 76 s | **Superseded** |
| 2026-09-14 | `-233128` | `mode, grating, fdtd` at the drawn gap, against the corrected stage | 28 s | that `unitarity_residual_over_kappa2` reads 0.214 and raises its finding |
| 2026-09-14 | `-234014`, `-234159` | the whole stage list, the `fdtd` stage having entered it | 85, 79 s | **Superseded**, the first by the acknowledgement of the last finding and the second by the corrected provenance rows of the generated report |
| 2026-09-15 | `-000630` | `mode, fem, grating, fdtd, bend, resonator, verify` | 61 s | **the run of record.** 7 of 7 targets met, 0 unmet at `must`, 6 findings emitted and 6 acknowledged, the coupling taken from the solve. Its resonator payload is identical to `-234159` in every scalar field |

Two figures rest on no run and are named under "Two probes that are not chain
runs": the single-mode width and the oxide truncation.

## Reproduction

```bash
picchain run examples/sin200_ring/design.yaml
python design-chain/tools/check_concept_trace.py examples/sin200_ring
```

The run solves the coupler, so it costs about eight minutes on a cold solver
cache and about eighty seconds against a warm one, the bridge reusing a prior
solve whose job and runner both match. On a host that cannot reach meep the
`fdtd` stage reports a stated reason, the resonator stage falls back to
`resonator.kappa_squared` in the design file, and
`resonator.kappa_squared_source` records which of the two was used.

The four-gap ladder is reproduced by overriding one field at a time:

```bash
for g in 0.5 1.0 1.5 2.0; do
  picchain run examples/sin200_ring/design.yaml --stages mode,grating,fdtd --set fdtd.coupler_gap_um=$g
done
```
