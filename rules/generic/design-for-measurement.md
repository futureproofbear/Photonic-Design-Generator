# A device that cannot be measured has produced no result, and measurability is designed in

*Tier: generic. Confidence: high on the coupler window and the extraction
procedure, each measured on one process; medium on the layout conventions, which
are the practice of one multi-project run and are stated here as a form rather
than as values.*

A design is judged against a specification, and the specification is read by an
instrument. Every stage of this framework asks whether the device meets its
target. **The question asked far less often is whether the target can be
observed**, and it fails in three ways that no simulation of the device reports.

## The extraction procedure is part of the model

A design characterised by an extraction carries two models: the physics that
produces the observable, and the procedure that reduces the observable to a
number. The second is usually implicit.

A group index taken from an interferometer is the clear case. The relation is
`n_g = lambda^2 / (dL . FSR)` and a mode solver returns `n_g` directly. The
laboratory does not. It sweeps a wavelength, records a transmission, locates the
minima, measures the spacing between consecutive minima, and divides. That
procedure carries a peak-finding threshold, a minimum separation between
accepted minima, a sub-sample interpolation, and a window over which the result
is averaged, and each is a choice.

**Run the simulated observable through the same procedure, on the instrument's
own sampling.** On one study the minima were found by prominence with a
separation taken from the expected free spectral range, each refined by a
parabolic fit to the three points either side, and the group index taken from
consecutive spacings and interpolated to the design wavelength. **The step is
part of the procedure and the instrument sets it**, 20.4 pm there; a run of the
same circuits at 5 pm is a circuit solve and not a reproduction of the
measurement. The difference is not cosmetic. The depth of a null in those
circuits moved by 13 decibels between a 1 pm grid and a 20.4 pm one, which
[`layout-verification.md`](layout-verification.md) records.

What comes out of the instrument's own grid is what the measurement will report.
A figure read from the mode solver is the quantity the device has, and the two
are different claims.

Where the two differ, the difference is the extraction's bias and it belongs in
the report. Where the procedure cannot run at all on the simulated observable,
the device cannot be characterised, and that is a design failure found before
fabrication rather than after.

## The instrument's reach is a design constraint with its own process window

The structure that admits light to a chip is usually resonant, and its band moves
with the process. Where it moves further than it is wide, a device that meets its
specification at nominal becomes unmeasurable at a corner.

Measured on a fibre grating coupler of a 220 nm silicon process, across the film
thickness and lithographic width bias that process declares, the peak moved by at
least 97.9 nm over a width excursion of 40 nm, while a back-to-back pair of the
same couplers leaves a usable window of 74.1 nm within 10 decibels of its own
peak. **The peak moves further across the process window than the window is
wide.**

The first figure is a lower bound and the second is not. At the extreme corners
the peak leaves the window the study swept, so it and every bandwidth measured
about it are truncated by the edge of the sweep rather than by the device.
**Sweep wider than the excursion before quoting either**, or mark the figure as
the bound it is.

Three practices follow.

**Place the device's feature near the centre of the coupler's band.** The margin
either side is what the process consumes.

**Add the measurability question to the corner study.** A corner sweep asks
whether the device still meets its target. It is also to ask whether the target
is still observable, and that is a question about the coupler and the instrument.

**Read the loss and the band of the pair, not of one coupler.** Light crosses the
structure twice, the band of the pair is narrower than the band of one, and a
budget built from a single-coupler figure understates both.

## The observable must fit inside the sweep, several times over

An extraction that measures a period needs several periods inside the
instrument's range, and a quantity derived from a spacing needs the spacing to be
resolvable. Both are design quantities and both are set by the same dimension the
specification is written against.

**Carry the fringe count in the table of variants.** On one design set the free
spectral range and the number of fringes inside a 50 nm sweep were tabulated
beside each variant, which makes a variant that cannot be read visible at the
point where it is chosen rather than at the point where it is measured. A
path-length difference chosen for a fine free spectral range is also a choice to
resolve a narrow fringe, and one too small to resolve returns nothing.

## A duplicate bounds what the model does not control

A variant answers a question the designer posed. **A second copy of an unchanged
device answers a question the designer did not pose**, which is how much of the
spread between two measurements belongs to the fabrication and the measurement
rather than to the parameter under study.

Place at least one device twice, unchanged. The difference between the two is
the floor beneath every other difference on the chip, and without it a variation
of the same size reads as an effect.

**Separate the two as far as the floor plan allows, and state which separation
was achieved.** On the design this is taken from, the duplicated pair sits in
adjacent slots of one column, which bounds the repeatability of the measurement
and of the immediate neighbourhood. It does not bound a gradient across the
field, and a pair at opposite corners would.

## The conventions that let a machine do the measurement

A chip measured by an automated station is measured by matching a machine-readable
label to a fibre position. The conventions are the run's, not the designer's, and
three classes recur.

**A label on each circuit, in the run's format**, naming at least the
polarisation, the wavelength, the designer and the device. It is the only link
between a trace in a data file and a device on a mask, and a device without one
is measured by nobody.

**A fixed geometry for the coupling structures**: one orientation for every
coupler, a fixed pitch between them set by the fibre array, and a stated rule for
which coupler is the input relative to its outputs. These are checkable
mechanically and they belong in the functional check described in
[`layout-verification.md`](layout-verification.md).

**A calibration path.** At least one structure that is two coupling structures
and nothing else, so that the response of the device can be divided by the
response of the path that reaches it. Without it, every insertion loss on the
chip is quoted against an unknown.

**State these as constraints with a source**, in the manner
[`requirements-before-design.md`](requirements-before-design.md) requires of any
inherited requirement, and record how the design meets each. A design-for-test
rule violated is a device that returns no data, which costs the whole run rather
than one target.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) L061 on the extraction
procedure as part of the model, L062 on the coupler's process window against its
own usable band, and L059 on the functional check that reads the design-for-test
rules. [`design-under-uncertainty.md`](design-under-uncertainty.md) carries the
corner machinery this adds a question to, and
[`measurement-validity.md`](measurement-validity.md) carries the general form of
the argument that a check is worth what it can detect.
