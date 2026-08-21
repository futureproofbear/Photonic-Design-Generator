# KLayout, and foundry runsets executed through it

The rule-check engine and the geometry representation it operates on. Every
failure below returns a clean or plausible report rather than an error.

## The deck reads layers by number, so a wrong map collides rather than misses

A design carrying placeholder layer numbers was run against a process runset for
the first time. The numbers did not simply fail to match. The design's slab sat
on the number the process reads as its ridge, its alignment marks on the number
read as metal, and its waveguides on a number the deck reads not at all.

The deck therefore checked a slab rectangle against the ridge rules, checked the
alignment marks against the metal rules, and never examined a waveguide, a
grating feature or an electrode. It returned a small non-zero count, which reads
exactly like a check that was performed.

**After any remap, confirm that every layer the deck names is one that something
is actually drawn on.** The chain reports `drc.deck.layers_named_by_deck` and
`drc.deck.layers_named_and_empty` for this purpose.

## Two runsets from one foundry differ where it matters and nowhere a reader looks

Decks for two stacks from the same foundry are near-identical in rule values and
differ in the numbers deciding what gets read. One observed set:

    layer     stack A     stack B
    RIDGE     2 / 0       2 / 10
    SLAB      3 / 0       3 / 10
    M1        21 / 0      20 / 0

**The metal move is the one that passes silently.** Pointing the correct deck at
a mask drawn on the other stack's numbers leaves the metal layer unread, and
every metal width and spacing rule is evaluated against an empty layer and
reports clean. Correcting the deck without correcting the layer map produces a
worse result than either error alone, because it looks right.

**Check `drc.deck.deck_declares` and `drc.deck.platform_stack` against the
platform the design states**, by stack name and by film thickness, before any
deck result is quoted.

## A rule with nothing to compare reports nothing, and that is not a pass

A runset carrying a die footprint rule, a centring rule and an exclusion-ring
rule evaluates all three against an outer boundary rectangle and a usable-area
rectangle. A mask that draws a seal ring and a dicing lane in place of those two
rectangles leaves all three rules silent on every die it emits.

**Report an unexercised rule as unexercised, in every document.** Drawing the
missing pair moved one die from three unexercised rules to three exercised and
passing ones, and exposed a second defect in doing so: the emitted die was 120 µm
larger in each dimension than the die declared. On a process offering fixed
footprints that is a refusal at submission.

## Two design layers on one deck layer are checked as their union

Where more than one design layer maps to a layer the deck reads, the rules for it
are evaluated over the union of both. This is frequently intended, a metal layer
and its pad layer being one lithographic level. It is to be confirmed rather than
assumed, and the chain names the sources in `drc.deck.deck_layer_sources`.

## A deck written for the graphical application names no input and no report

A runset authored for interactive use takes its input from the open layout view
and writes its report to the view. Executing it in batch requires the input and
the report path to be bound, by supplying `source($input)` and
`report(..., $report)`. The rules themselves are unaltered by that binding, and
the chain records that it was applied.

## Run the deck against the die and not against the device cell

A frame drawn and never checked is a frame assumed. Seal ring, dicing lane,
overlay marks, label and process-control monitors are subject to the same deck as
the device. A monitor field violating the deck is removed before submission,
which is the least useful outcome available.

## An angled mask needs a corner threshold

Every convex corner brings two edges arbitrarily close together, so a width or a
spacing check reports the corner itself unless a threshold on the interior angle
is supplied. Engines default that threshold to 90°, which is exactly the value
at which an orthogonal layout sits. A mask carrying an 8° facet presents 82°
corners and reports them all.

**Set the threshold below the sharpest corner the design intends**, through
`DRCRule.ignore_angle_deg`, and state what that value admits.

## Merge before snapping, not after

Every vertex of a drawn polygon may be snapped to the manufacturing grid and the
merged layer still be off it. Two overlapping shapes on one layer resolve into a
single outline when merged, and the boolean introduces vertices at their
intersections. Those vertices are computed rather than drawn, so they land where
the crossing falls.

**Merge first and snap afterwards**, which is the order mask preparation uses.
A grid check against the drawn shapes passes while the merged layer fails.

## A boolean result carries holes, and a hull-only representation fills them in

An inverse layer produced as *field minus feature* was found to overlap the very
feature it was derived to exclude. The operation was correct and the
representation was not: a boolean result is a polygon with holes, and a pipeline
carrying polygons as sequences of hull vertices cannot express one, so every hole
closed silently and the inverse came out solid.

The condition passes a rule deck, the shape being legal, and passes an area check
on the derived layer alone. **It is detected only by intersecting the derived
layer with its operand, which is empty by construction.** Where a geometry
pipeline cannot represent holes, cut them open before the conversion, which is
what a mask writer does in any case.

**A derived layer is checked against the identity that derived it, and not
merely inspected.**

## An overlay mark repeated identically on two levels is a short

The obvious construction for a registration mark is one figure repeated on each
level at the same position. It fails twice. The two levels overlap over their
whole area, which any layer-to-layer separation rule reports as a short, and the
overlay cannot be read at all, there being no gap whose asymmetry carries it.

The figures must nest: an outer annulus on the first level, a smaller figure
inside it on the second, separated by more than the layer-to-layer rule. The
registration error is then the difference between opposite gaps.

## Evidence

`.claude/LESSONS.md` T011, T014, T015, T021, T022, T024, T044, L016, and
`design-chain/CLAUDE.md` rules 6, 9 and 12.
