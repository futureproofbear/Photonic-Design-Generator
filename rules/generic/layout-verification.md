# A mask is cleared by three checks, and the artifact checked is the artifact that ships

*Tier: generic. Confidence: high. The three-check separation and the extracted
netlist are drawn from one multi-project electron-beam submission; the staleness
failure at the foot was found in the same flow and is of a class this framework
has recorded twice before on its own documents.*

A rule deck measures geometry against dimensional rules. It is routinely spoken
of as "the" check on a mask, and it answers one question of three. The other two
fail in ways a deck cannot see, and a mask that passes the deck may be
unconnected, or may carry a cell with no geometry in it at all.

## The three checks, and what each sees that the others do not

**Dimensional.** Minimum width, minimum space, enclosure, density, everything
inside the floor plan. This is the deck, and
[`../tool/klayout/README.md`](../tool/klayout/README.md) covers how to run one
so that it reads the geometry it was written for.

**Functional.** Components walked, each pin matched against the waveguide
meeting it, overlapping cells found, and the run's design-for-test rules
applied: the orientation of every fibre coupler, the pitch of the fibre array,
the format of the machine-readable label on each circuit. **None of that is
dimensional.** A device routed to nothing passes every rule in the deck.

**The recipient's own submission script.** This is the only one of the three
that is updated when the recipient changes what it accepts, and it reads what the
other two cannot. On one submission it reported 21 black-box cells to be
replaced and none left unreplaced. **That clearance, and every count in this
section, describes a generation of that mask which no longer exists**, which is
the subject of the last section of this file. They are quoted for the separation
they illustrate and not as the clearance of a mask now on disk.

**A black box is a hole in the mask that both of the other checks pass.** It is
a cell with a correct outline and no internal geometry, placed so that a designer
may route to a part whose layout the vendor supplies at submission. Its outline
meets every dimensional rule, its pins meet every connectivity rule, and the
fabricated chip has nothing there. **Count the black boxes, and count how many
remain unreplaced.**

**Run the submitter's own script and not only a port of its rules.** A port
establishes that the geometry meets the rules the porter knew about. The script
establishes that the submission is one the recipient will accept.

## Simulate the netlist the mask produces

A circuit model assembled by hand asserts a connectivity and a set of lengths,
and the mask is drawn by a separate program. The two agree until they do not, and
nothing in either reports the disagreement.

**Extract the netlist from the drawn layout and solve that**, with its
components, its connectivity, and its drawn waveguide lengths and widths. On one
set of nine circuits the extraction returned arm lengths to a thousandth of a
micrometre, and a path-length difference the router had altered would have
appeared as a shifted free spectral range instead of appearing nowhere.

This is the layout-versus-schematic comparison performed by simulation rather
than by graph matching, and it is stronger than either on its own: it catches a
mis-wiring and a changed length in the same pass, and it reports them in the
units the specification is written in.

**Two solvers on one extracted netlist separate the trustworthy quantity from the
fragile one, and the mechanism is not the one first proposed.** On that study two
solvers reading the same compact models agreed on the free spectral range and on
the group index to four figures, 5.733 nm against 5.733 and 4.1906 against
4.1904, and differed on the extinction ratio by 7.2 decibels, 55.2 against 48.0.

The first explanation written here was that the extinction divides by a small
difference between two arms, so every approximation in the splitter model reaches
it multiplied. **That explanation is withdrawn**, and the evidence against it was
in the same files.

**The two runs sample the wavelength axis differently**, at 5 pm and at 20.4 pm,
and a third run of the same circuits at 1 pm completes a monotone series: 61.1,
55.2 and 48.0 decibels as the step coarsens. A deep null is a narrow feature, and
the depth a run reports is set by how close its nearest sample falls to the exact
minimum rather than by the physics of the null.

**The discriminating case contradicts the splitter explanation outright.** The
one circuit whose splitter model differs most between the two solvers is the one
the two agree on, to 0.8 decibels, because its null is shallow for a physical
reason both solvers share and no grid can dig below a floor that is really there.
Every circuit the two differ on by 6 decibels or more has a deep null.

**The rule is therefore about the quantity and not about the component.** A figure
that is the extremum of a narrow feature is a property of the sampling as much as
of the device, and two runs on different grids are not comparable on it at all. A
figure that is a property of a period, such as a free spectral range or anything
derived from one, is insensitive to the grid and may be compared. **Before
quoting a disagreement between two solvers as physics, check that they sampled
the axis alike.**

## The drawn quantity is read back and compared against the intent

A layout program that computes a dimension can compute it wrongly. Have it write
out what it actually drew, in the units the design states, and compare.

On the same submission the layout program emitted the drawn arm length of every
interferometer, and the circuit simulation read those lengths rather than the
design values. The comparison is one line and it closes the loop between what was
intended and what exists.

**Where a specification is a difference between two paths, make everything but
the difference identical.** Equal bend counts in both arms of an interferometer
leave the path-length difference entirely in straight waveguide, where it is
exact and where the drawn value can be checked against the intent by subtraction.
A difference taken between two paths of unlike construction carries every
modelling error of the bends into the quantity the device exists to measure.

## The artifact checked is the artifact that ships

Every check above is performed on a file, and the value of the result decays with
the age of that file.

A flow assembled from separate programs, each reading a file the previous one
wrote, has no record of which generation produced which output. On one such flow
the layout program and its mask carried one time, the circuit results carried a
time nearly two hours earlier, the verification log earlier still, **and the mask
file both of those outputs name by path no longer existed.** One device had
changed between the two generations. Nothing raised, and every file read as a
complete and consistent record.

Three requirements follow.

**Write every output of a run into one directory stamped with the resolved
input.** A result that cannot name the input that produced it is an assertion.

**Have every consumer print the path and identity of the artifact it read**, and
check that name against the current one. The verification log did print its
input, which is the only reason the drift could be found.

**Extend the staleness check from the figures to every derived artifact**: the
tables, the comma-separated results, the verification logs and the mask itself. A
reader trusts a verification log more than a figure, and it is refreshed by
nothing.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) L059 on the three checks
and the black-box class, L060 on the extracted netlist and the two solvers, and
T097 on the flow whose published numbers outlived the file that produced them.
Within this framework the same staleness class is recorded at T049, where a
published figure was not the run's figure and no picture carries a run
identifier, and at T031, where one document carried two designs and did not say
which one each number described. The figure-currency obligation and the tool that
discharges it are stated in
[`../../design-chain/CLAUDE.md`](../../design-chain/CLAUDE.md).
