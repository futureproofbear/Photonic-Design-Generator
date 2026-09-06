# The access taper of the mmi1x2 splitter, in two dimensions and in three

*2026-09-05. Runs of record `20260905-204348-ltoi300_access_taper_2d` and
`20260905-184841-ltoi300_access_taper_3d`. Designs
[`design_access_taper_2d.yaml`](design_access_taper_2d.yaml) and
[`design_access_taper_3d.yaml`](design_access_taper_3d.yaml), both at
`meta.status: scaffold` and both carrying no acceptance target.*

## Summary

The three-dimensional FDTD path returns a physical result, and this is the first
sound solve the repository has taken through it. Five earlier attempts are
withdrawn.

**The plane reduction gives a smaller loss for this taper than three dimensions
do, by a third, and that comparison is not resolved at the resolution it was
made at.** Three dimensions give 0.0304 dB against the plane's 0.0228 dB. A
convergence guard added to this runner on 2026-09-05, after the comparison was
first published, shows the plane loss moving by 68 per cent between resolution
10 and 20 and understating its converged value by about a sixth at resolution
20. That error is 0.10 percentage points against a reported difference of 0.17,
so the discretisation is the larger term. See "Whether the difference is
resolved" below.

What the difference consists of is also not measured. The vertical radiation
channel is one contributor and the inaccuracy of the effective-index reduction
is another, and the two were not separated.

**The taper measured is 5.0 um long. The `mmi1x2_cband` cell draws 25 um.** No
length was swept, so nothing here transfers to the shipped cell.

Reaching this required four defects to be found and fixed. One moved the plane
figure by a factor of two and had been present in three of the four FDTD runners
since they were written.

## The cross-section

The `mode` stage runs on both members and reports, for the 1.950 um output port,
an effective index of 1.7616, a group index of 2.1393, a film confinement of
0.6457 and three guided modes, with an effective-index spectrum of 1.7616,
1.6772 and 1.5637 above a slab floor of 1.5509.

That port is multimode, which is the premise of the study. The measurand is
therefore a transmission **into the fundamental mode of a multimode port**, and
power leaving the fundamental has somewhere to go that is neither radiation nor
loss to the splitter downstream.

## What was measured

Both members are solved at resolution 20, in a cell 20 um long and 10 um wide,
with a 1.5 um perfectly matched layer. The three-dimensional member is 6 um deep
and the plane member has no depth. They differ in `fdtd.dimensions` and the
fields derived from it.

| quantity | plane | three dimensions |
|---|---|---|
| transmission into the fundamental | 0.994753 | 0.993036 |
| total flux crossing the output plane | 1.000124 | 0.999051 |
| reflection into the fundamental | 0.0000542 | 0.000148 |
| self-normalised transmission | 1.000129 | 0.998866 |
| loss of the launch-width guide over its own length | 0.0000020 | 0.000207 |
| loss of the output-width guide over the same span | −0.0000032 | 0.000101 |
| loss into the fundamental | 0.0228 dB | 0.0304 dB |
| solver elapsed | 3.94 s | 1516.94 s |

### The plane member returns power above unity, and this bounds everything it reports

Three of its quantities exceed one: the total transmitted flux by 1.24e-4, the
self-normalised transmission by 1.29e-4, and the output-width guide's loss is
negative by 3.2e-6. The stage raised both of the first two, at a tolerance of
1e-4, with the instruction that no figure of the run be quoted.

The figures are quoted here, and the reason is stated rather than assumed. The
quantity the run exists to measure is a loss of 5.25e-3, forty times the
residual, so the measurement is resolved despite it.

**The residual falls with mesh, and its cause is not yet separated.** The
resolution ladder below reads +129, -313, -483, -580 and -626 parts per million
at resolutions 20, 30, 40, 60 and 80. It crosses unity between resolution 20 and
30 and falls monotonically thereafter, so the bound is violated only on the
coarsest mesh of the ladder and refining removes it.

That behaviour is consistent with discretisation and an earlier version of this
section attributed it to discretisation on that evidence alone. A second
candidate has since appeared and predicts the same behaviour. The input flux
plane sits 0.4 um downstream of the source, where the launch near field is still
forming, and the splitter runner uses 0.5 um for the same measurement. A plane
reading low there inflates every quotient normalised on it, and the error would
also fall as the mesh samples the near field better. **The ladder therefore does
not separate the two**, and the attribution stands only as far as "it refines
away" until the plane is moved and the run repeated. The two findings are
acknowledged in the design on those terms.

The three-dimensional member violates no bound.

### Where the power goes

The incident power splits three ways, by the definitions the runner uses.

| | plane | three dimensions |
|---|---|---|
| into the fundamental of the output guide | 0.994753 | 0.993036 |
| crossing the output plane outside the fundamental | +0.005371 | +0.006016 |
| not crossing the output plane at all | −0.000124 | +0.000949 |

**These three sum to one identically and not as a measurement.** The third is
defined as one less the second and the first, so the sum is one for any values
whatever, and an earlier draft of this report presented that identity as an
energy budget closing to one part in a million. It is no such thing. The rows
are a decomposition, and the check they carry is that each is bounded, which the
plane member fails as above.

The two denominators also differ. The first two rows are normalised on the
reference run's fundamental-mode power at the output plane, and the third on its
total flux there. Those differ by 5.9e-5 in the plane and 5.7e-5 in three
dimensions, which is comparable to the plane's whole third row.

**Row 2 is not established to be guided power.** Only band 1 is extracted from
the monitor, so nothing in any run separates conversion into the second and
third guided modes from radiation still travelling forward inside the monitor
aperture. The runner names the field `radiated_or_converted` and its own
docstring calls it power that has left the guided mode. Three guided modes exist
at that port, so conversion is available; that it dominates is an assumption.

### The difference between the two dimensionalities

The loss into the fundamental differs by 0.001717 in power, being 0.0075 dB.
That difference decomposes as 62 per cent in row 3 and 38 per cent in row 2.

Row 3 is everything that failed to reach the output monitor. It contains the
reflection, 1.48e-4 in three dimensions; the straight launch guide's own
unexplained loss over the same span, 2.07e-4; lateral radiation escaping through
the side boundary; and radiation out of the plane. **The monitor spans 7.0 um
laterally and 3.0 um vertically and accepts radiation to about 41 degrees in the
lateral axis and 21 degrees in the vertical, so it does not separate the two
axes**, and neither does anything else in the run.

What can be said is bounded. Radiation leaving the cell in three dimensions is
at most row 3 less the reflection, being 8.0e-4, and at least that less the
straight-guide floor, being 5.9e-4. In the plane the same quantity is negative,
which is the residual of the previous section rather than a physical value. The
out-of-plane channel is therefore worth something of order 0.003 dB on this
structure, against a headline difference of 0.0075 dB, and the balance sits in
row 2 and in the accuracy of the effective-index reduction.

**The effective-index reduction is the second contributor and was not
controlled.** The plane member replaces the ridge and the slab by indices of
1.7907 and 1.5509 while the three-dimensional member builds the layer stack, so
any inaccuracy in that reduction appears in this difference alongside the
physics. Separating the two requires a cell-height sweep, a monitor-aperture
sweep, or an extraction of the higher-order coefficients. None was run.

### Whether the difference is resolved

The taper runner carried no convergence guard until 2026-09-05, while the
splitter and coupler runners did. The comparison above was published without
discretisation evidence of any kind.

The guard, and a ladder run in the plane where it is cheap, give this.

| resolution | plane loss | change on the previous rung |
|---|---|---|
| 10 | 0.166 % | - |
| 20 | 0.525 % | +216 % |
| 30 | 0.582 % | +10.8 % |
| 40 | 0.609 % | +4.6 % |
| 60 | 0.617 % | +1.5 % |
| 80 | 0.626 % | +1.4 % |

The plane member is solved at resolution 20 and its converged loss is at least
0.626 per cent, so resolution 20 understates it by about 0.10 percentage points.
The difference between the two dimensionalities is 0.17 percentage points. **The
discretisation error on one member is sixty per cent of the quantity the two
members are being compared on.**

The self-normalised transmission converges better over the same ladder, reading
1.000129, 0.999687, 0.999517, 0.999420 and 0.999374 at resolutions 20 to 80, so
the residual above unity discussed earlier is itself a discretisation artifact
and falls away with mesh.

A difference between two solves often converges faster than either solve, and
that is never to be assumed. Testing it requires both members at a second
resolution, and in three dimensions the cost is the fourth power of the ratio.

### The self-normalised transmission, which needs no second run

Each simulation carries a flux monitor downstream of its source and another at
its output, so the quotient of the two grades that run by itself, and for a
passive structure it is at most one whatever any other simulation did.

That quantity settled the diagnosis. Three quantities had been used to grade the
taper and each divided one simulation by another, so a result above unity could
be attributed to the reference indefinitely, and was, across two drafts. The
self-normalised figure read 0.9988 where the between-run quotient read 1.0077,
which put the fault in the normalisation rather than the physics, with no
further solve.

### The reference asymmetry, measured rather than argued

The normalisation guide is held at the launch width while the structure widens
away from it. That asymmetry was proposed as the cause of an above-unity
transmission and was never bounded. A third simulation, of a straight guide at
the output width over the same span, measures it: 0.0005 per cent in the plane
and 0.011 per cent in three dimensions. The mechanism is real, it is negligible,
and it was never capable of explaining the 0.8 per cent it was invoked for.

## A check against the splitter that contains it

Light traverses the input taper and then one output taper, the two output
branches of a 1x2 splitter being parallel, and `transmission_at_design` sums both
ports, so two tapers act in series. The splitter job and the standalone taper job
carry the same width, port width, taper length, station count, profile, indices
and resolution.

| | value |
|---|---|
| two tapers in series, from the standalone run | 0.989534 |
| shortened splitter measured, `20260905-191516` | 0.977346 |
| difference | −1.219 % |

**That difference is not the multimode section's loss, and an earlier draft said
it was.** Squaring the fundamental-mode transmission books row 2 as lost at each
taper. If any of row 2 is guided power, it enters the multimode section rather
than vanishing, and the difference attributable to the section falls towards
1.219 − 2 × 0.537 = 0.15 per cent. The section's loss therefore lies somewhere
between about 0.1 and 1.2 per cent, and the two ends correspond to the two
readings of row 2 that this study did not separate. The splitter's own
convergence guard moves its transmission by 0.93 per cent between resolution 10
and 20, which covers most of that interval.

Three conventions separate the two measurements. The taper divides out the
reference guide's propagation loss, both of its planes being at the output, while
the splitter takes its incident power near the source and retains that loss over
about 21 um; at the launch guide's present 2.0e-6 over 12.6 um that correction is
0.0003 per cent and immaterial, where before the fourth defect below it was 0.18
per cent. The splitter grades each port with a 2.04 um monitor while the taper
grades with one spanning the cell. The splitter fixes the wavevector direction
and the taper does not. Both runs also draw their two effective indices from the
same routine, so an error in the reduction is common to both and invisible here.

## The four defects

All were in code that had never executed in the configuration that reaches them,
and all are fixed. They are recorded in
[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) as T073, T076, T078 and
T080. T075 in that range records a fifth condition, that a stage printed a
transmission above unity without remark; the guard added for it is what raises
the plane member's residual above, so that entry describes a live condition and
not a closed one.

**A declared dimensionality that one runner read and four recorded.** The
splitter, coupler and grating runners build every shape with an infinite extent
in the third axis. A splitter asked for three dimensions produced a payload
stamped `dimensions: 3` carrying a two-dimensional result, in 13.9 s, the field
being absent from every job dictionary so that the reuse key matched an earlier
two-dimensional solve. The stage now refuses a dimensionality its runner does not
build, before the solver environment is probed.

**A cell filled with an index belonging to the other model.** `n_clad` is the
effective index of the unetched film beside the ridge, which is the surround of
the plane reduction. The three-dimensional branch builds the slab explicitly, so
its surround is the cladding, and using `n_clad` there placed the slab twice and
filled the cell with 1.5509 where this stack's cladding is 1.4440. The job now
carries `n_ambient`.

**A reuse key over the job and not the runner.** A third simulation and six
output fields were added to the taper runner, and the next run returned a cached
result carrying none of them, in seconds, the job being unchanged. The runner's
content digest now enters the key.

**A guide that stopped where the boundary started.** This is the one that
mattered. The ridge was built only to the inner face of the perfectly matched
layer rather than out to the edge of the cell, so the mode met an abrupt end of
the guide exactly where the layer began. That is a dielectric step across the
whole mode and it reflects.

The error cancels within a run and survives every quotient between two runs,
because the reference is a straight guide at the launch width while the structure
ends at the output width, and a facet reflects by an amount that depends on the
confinement of the mode meeting it. What located it was the net flux at the
*input* monitor: two runs sharing a source and an identical input section
differed there by 1.15 per cent, which no mechanism downstream can produce. That
figure is not held directly in any artifact, the raw fluxes having been added to
the payload afterwards, and it is recovered from the three published ratios of
run `20260905-181023` as `transmission_total_flux` times
`self_normalised_narrow_guide` divided by `self_normalised_taper`.

Correcting it changed the plane reduction as follows.

| | before | after |
|---|---|---|
| reflection into the fundamental | 0.00353 | 0.0000542 |
| loss of the launch guide over its own length | 0.109 % | 0.0002 % |
| transmission into the fundamental | 0.98844 | 0.99475 |
| loss into the fundamental | 0.0505 dB | 0.0228 dB |

`meep_grating.py` carried the same defect at full severity and is corrected.
`meep_mmi.py` carried a milder form, its leads stopping 0.5 um inside the layer
while its normalisation guide ran past the cell edge; re-solving after the
correction moved the shortened splitter's transmission in the seventh decimal
place, so that defect was real and its effect immaterial. `meep_coupler.py` was
already correct, its bus and ring both running 1.0 um beyond the cell.

The three corrected runners do not now agree with each other. The taper's guide
ends flush with the cell boundary while the coupler and the splitter overshoot it
by 1.0 um. Meep discards geometry outside the cell, so the two constructions
should be equivalent, and no control run tested that on the structure this study
turns on.

The conditions are held by
[`../../design-chain/tests/test_fdtd_dimensions.py`](../../design-chain/tests/test_fdtd_dimensions.py).
Ten runs are withdrawn, and the notices are reproduced in
[`WITHDRAWN_RUNS.md`](WITHDRAWN_RUNS.md), the run tree being excluded from
version control.

## A claim this report previously made, withdrawn

Two earlier drafts concluded that the plane reduction *overstates* this taper's
loss, one of them by a factor of seven. Both rested on runs since withdrawn and
on a mechanism argued rather than measured. The corrected pair reverses the
direction: the plane gives the smaller loss.

## What this study does not establish

The composition of the 0.0075 dB difference. The vertical radiation channel, the
lateral channel, and the accuracy of the effective-index reduction all
contribute and none was separated.

The composition of row 2. Only band 1 was extracted, so conversion into the two
higher guided modes was never distinguished from forward radiation.

Whether the difference is resolved. It is not, at resolution 20; the ladder
above gives the evidence. Whether it survives at a higher resolution is being
tested and is not answered here.

The cause of the three-dimensional launch guide's 2.07e-4 loss over its own
length, which floors every three-dimensional figure quoted.

A figure for the taper the cell draws, which is 25 um. Lengthening a taper is
expected to reduce its loss and no length was swept.

A loss figure for the multimode section closer than the 0.1 to 1.2 per cent
interval above.

The `verify` stage returned PASS on both runs of record, and each grades zero
acceptance rows, so the verdict carries no information.

## Cost

The `fdtd` stage took 16.6 s in the plane and 1529.8 s in three dimensions, a
ratio of 92, and that is the figure to plan against. The solver's own elapsed
figures are 3.94 s and 1516.9 s, a ratio of 385, the difference being a bridge
and job round trip of 12.7 and 12.9 s.

Each job now performs three simulations rather than two. The cost did not rise
in proportion and did not rise at all: the previous three-simulation
three-dimensional run, `20260905-181023`, took 2066.8 s against the present
1529.8 s. The geometry correction changed the field decay and therefore the
stopping time, so the run is 26 per cent cheaper than its predecessor despite
carrying the same three simulations. An earlier draft attributed the cost to the
third simulation alone.
