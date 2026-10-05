# Silicon-on-insulator, 220 nm strip, single full etch, electron-beam written

*Written from one design activity on a multi-project electron-beam run: seven
interferometers and two calibration paths on a 605 by 410 um cell, with the mode
solves, the circuit simulations and the submission checks that accompanied them.
Every sensitivity below was computed once, on one cross-section.*

**None of the figures in this folder was produced by this framework's solvers.**
The mode solves were run on a commercial finite-difference eigenmode solver
through its Python interface, in the repository where that activity was
conducted. They are quoted here as a second party's results, they carry none of
this chain's cross-check discipline, and reproducing them inside the chain is
work that has not been done.

**The stack.** A 220 nm silicon layer on about 3.0 um of buried oxide, oxide
clad, etched once and completely so that the guide is a strip with no slab beside
it. The nominal single-mode strip is 500 nm wide at 1550 nm in the
quasi-transverse-electric polarisation. The sidewall is not vertical: an angle
near 82 degrees is declared and the core is modelled as a trapezoid.

Two things about this stack differ from the thin-film Pockels platforms the
sibling folder covers.

**The index contrast is large and the guide is fully etched.** There is no slab,
so the lateral guidance floor is the cladding and not an unetched film. The
consequences of that choice inside this framework are recorded under
[`../../generic/first-exercise.md`](../../generic/first-exercise.md) and in
ledger entry T092.

**The pattern is written rather than printed**, and the writer quantises.

## The writer's shot grid quantises every drawn dimension

The pattern generator places its exposures on a grid, and the kit's own
description is that all layout features snap to it. On this process the shot
pitch is 6 nm.

A 500 nm guide is not a multiple of 6 nm and is written as 498 or 504 nm, being
83 or 84 shots. A 480 nm guide is exactly eighty shots and is written as drawn.

Interpolating the width sensitivity below across that 6 nm step puts the group
index of the written guide between 4.173 and 4.184. **That bound is an
interpolation and not a pair of solves** at 498 and 504 nm, which were not run.

**Choose a dimension on the grid wherever a quantity depends on it.** That
removes the term rather than carrying it. The quantisation is invisible to a rule
deck, which passes a 500 nm feature against a 60 nm minimum without remarking
that the writer cannot produce it, and invisible to a mode solve, which solves
what it is given.

## Computed sensitivities of the nominal strip

All from one mode solver on the trapezoidal cross-section, 220 nm thick, at
1550 nm, except the last row, which is that solve repeated at 220 ∓ 3.7 nm.

| quantity | value |
|---|---|
| `n_eff`, 500 nm wide | 2.4416 |
| `n_g`, 500 nm wide | 4.1801 |
| `n_g`, 400 nm wide | 4.3687 |
| `n_g`, 600 nm wide | 4.0421 |
| `d n_g / d width` near 500 nm | about -0.0018 per nm |
| `d n_eff / d width` near 500 nm | about +0.0017 per nm |
| `n_g` at one standard deviation of film thickness either way, 3.7 nm | 4.1842 and 4.1772 |

**The group index falls with width and the effective index rises**, at nearly the
same rate in opposite directions on this stack. A design reading a difference of
group index between two widths has a usable lever: 480 against 500 nm gives
0.0352, which is **five times** the 0.0070 a one-sigma film excursion produces
either way.

## Two figures for the group index of this guide, and they differ by 0.0105

The table above gives 4.1801 from a mode solve of the trapezoid. The circuit
simulations of the same design return 4.1906, because they read the kit's own
waveguide compact model rather than a solve.

**That difference, 0.0105, is one and a half times the whole one-sigma film
excursion**, and it is larger than the shot-grid term and a third of the 480-to-
500 nm lever. Neither figure is a measurement. A design quoting a group index on
this stack is to say which of the two it is quoting and why, and a comparison
between a chain result and a published one is worth nothing until both are known
to come from the same side of this gap.

## The published monitor history is the right kind of source and the wrong one to quote directly

A multi-project run of this kind publishes process-control monitor data from past
runs, and that is the sourced window
[`../../generic/design-under-uncertainty.md`](../../generic/design-under-uncertainty.md)
asks for. One such report covers nineteen tape-outs from October 2021 to June
2025 and carries sixteen numeric entries for the group index of its monitor guide
at 1550 nm.

    thirteen of the sixteen fall inside a band 0.20 wide
    the other three fall about a unit below it, all from one year,
      and two of those carry a stated uncertainty of order half
      the quantity
    the extremes of the row therefore span about a quarter of its value

**The row carries its own simulated value, and it sits 0.034 above the figure
this cross-section solves to.** That difference is the whole lever a 20 nm change
of width gives this design. **The monitor is therefore not the guide this folder
describes**, and the row's spread bounds the process and that monitor together.

Three practices follow.

**Check the source's own modelled value against yours before adopting its
spread.** Where the two differ by more than the effect under study, the history
describes a different structure.

**Separate the cluster from the outliers and state what each is.** Thirteen
entries within 0.20 of each other is a process reproducing its own model. Three
entries far below, from one period and with large stated uncertainties, are
either a process excursion or a measurement problem, and the report does not say
which.

**State whether a quoted window is the spread within one run or across runs.**
The two differ by more than most design margins, and a design measured on one
chip is exposed to the first.

Component figures from the same report are of the same character, and **which
row a figure came from matters more than its value**: the report carries a
straight-guide propagation loss and a spiral-guide loss separately, and the
spiral range sits about a factor of two above the straight one over the same
runs. A routed guide with bends behaves like the second. A budget built on the
straight-guide row therefore understates a routed path by about that factor,
and a figure quoted without its row is not a figure.

## The fibre coupler moves further than its own usable band

The structure that admits light to this stack is a grating coupler, and it is the
narrowest-band element most designs on this process contain. Across the declared
thickness and width-bias excursions its peak moved by at least 97.9 nm, that
figure being a lower bound because the extreme corners place the peak outside the
1500 to 1600 nm window the study swept. A back-to-back pair leaves 74.1 nm within
10 decibels of its own peak, which is measured inside the swept window and is not
a bound. At nominal the pair costs 4.85 decibels and peaks at 1552.5 nm.

**Any specification on this stack is to be checked for observability across the
window as well as for compliance at nominal.**
[`../../generic/design-for-measurement.md`](../../generic/design-for-measurement.md)
carries the general form.

## What this folder does not contain

**No measurement of a fabricated device**, and no solve of this framework's own.

**No bend loss, no sidewall-roughness loss, and no thermal coefficient.** The
first two are the dominant propagation terms on a high-contrast strip and neither
is computed by this chain on any platform.

## Provenance

The stack description, the sidewall angle, the buried-oxide thickness, the
minimum isolated feature and the shot pitch are from the publicly published
process design kit of the run. The minimum space is from the rule deck that
accompanies it rather than from the manual. The monitor figures are characterised
from the monitoring report the run publishes to its participants: the shape of
one row's distribution and the relation between two rows, with no cell of its
table reproduced and the row's subject not named.

**The terms that report is published under were not checked.** The judgement
made here is that describing the shape of a distribution one has read is not
redistribution of the document, and that judgement is stated rather than
assumed, as it is for the other participant-published kit this framework
examines. A reader intending to publish this folder should confirm it.

The mode solves are the second-party results described at the head of this
file.
