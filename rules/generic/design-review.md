# A design is reviewed before it is sent, by its author and then by somebody else

*Tier: generic. Confidence: high on the list, which is the standard practice of a
multi-project run and is reproduced here in substance; medium on the mapping to
this framework's instruments, which was established once by walking each row
against the code.*

Every other file under `rules/` states how to establish one thing. This one
states what is to be established before a mask is sent, in the order a reviewer
reads it, and names the instrument that answers each row.

**It exists because the rest of the framework is organised by subject and a
review is not.** A reviewer does not ask "what do the platform rules say"; they
ask "is this ready", and the answer is assembled from four tiers, eleven release
conditions and a ledger. A list that cannot be read in one pass is not a review.

## The review is performed twice, and the second time by somebody else

**The author verifies.** Every row below, against the run of record.

**A peer assesses, against the same rows.** This is a separate act and it is not
a formality. The framework's own evidence for why is in the ledger: over one
session a reader found a stage reported switched off on a justification that had
gone stale, figures regenerated from one design and placed in sections describing
another, a run register eight days behind the conclusions resting on it, three
stages that ran and were reported nowhere, and a reference manual claiming
sixteen stages against seventeen. **Every one was visible in the document**, and
the author had read it each time.

A peer who has not held the design in their head reads what is written rather
than what was meant, which is the whole of the mechanism.

## The rows, and what answers each

A row is answered by an instrument, by a declared assumption, or by nothing. The
third is a finding and is recorded as one.

### Design concept

| # | Row | Answered by |
|---|---|---|
| 1 | Enough test structures, with parameter variation that spans the question | the variants table and the fringe count of [`design-for-measurement.md`](design-for-measurement.md); the ladder discipline of [`parameter-scans.md`](parameter-scans.md). **Nothing checks the count or the span** |
| 2 | De-embedding structures, so that a measurement divides by its own path | "A calibration path" in [`design-for-measurement.md`](design-for-measurement.md). **Nothing checks that one was drawn** |

### Manufacturability

| # | Row | Answered by |
|---|---|---|
| 3 | Every feature clears the minimum width and space | the `drc` stage and the foundry deck; release conditions "the rule check is clean" and "a foundry rule deck was executed". [`../tool/klayout/README.md`](../tool/klayout/README.md) states what makes a clean deck mean anything |
| 4 | No feature *sits on* the minimum | `drc.margin_fraction`, which re-runs each dimensional rule widened by a fraction and reports `drc.at_the_limit`; release condition "no feature sits within the rule margin" |
| 5 | The design works across the known process variations | the `corners` stage run factorially, [`design-under-uncertainty.md`](design-under-uncertainty.md), and the monitor-history discipline in the platform tier |

### Mask layout

| # | Row | Answered by |
|---|---|---|
| 6 | Every waveguide is connected, none misaligned | **partly.** `mask` merges touching polygons into nets and compares them against a declared schematic. It matches no component port, so a guide landing off-port still merges and passes. [`layout-verification.md`](layout-verification.md) states the gap and names the functional check that closes it |
| 7 | Every path is a waveguide of adequate radius, with no sharp corner | `layout.check_geometry` refuses interior angles below `min_angle_deg`, and the `bend` stage solves the radii. **No routing-integrity check exists**, the chain building geometry directly rather than routing it |
| 8 | Enough separation between guides that they do not couple | **nothing.** The coupling machinery exists in the `fdtd` coupler structure and in [`../platform/`](../platform/), and no stage applies it to a routed pair. Declared, not stubbed |
| 9 | Every structure on the correct layer | the layer map, `test_grating_layer.py`, and the renumbering discipline of [`../tool/klayout/README.md`](../tool/klayout/README.md) |
| 10 | The layout fits inside the allocated floor plan | the `reticle` footprint check and the rule that places all geometry inside the frame |
| 11 | The layout is space-efficient | **nothing.** No area-utilisation figure is computed. Declared, not stubbed |

### Design for test

| # | Row | Answered by |
|---|---|---|
| 12 | Fibre couplers drawn correctly: pitch, orientation | the conventions in [`design-for-measurement.md`](design-for-measurement.md). **Nothing checks them**, and a kit-supplied functional checker is what does where one ships |
| 13 | Every device carries a label an automated station can read | release condition "the mask carries a label for every device the layout names", which matches the names the layout declared against the texts written into the file |
| 14 | Every label is unique | release condition "every text label is unique", from the label inventory `mask` reads back off the written file |

### Submission

| # | Row | Answered by |
|---|---|---|
| 15 | File and cell names correct | release condition "the emitted files and the top cell carry the design's name", with `release.name_pattern` imposing a submission convention on top |

## Three disciplines the list depends on

**A row answered by nothing is a finding, not a blank.** Rows 8 and 11 are
answered by nothing here and say so. The framework's standing position is that a
quantity nobody computed is an assumption, and an assumption nobody wrote down
is a defect.

**A check with nothing to compare is not a pass.** The label conditions report an
empty inventory as unmet rather than as unique, because a design carrying no
label satisfies "every label is unique" vacuously. The same reasoning governs
every condition whose subject may be absent.

**The review is performed on the artifact that ships.** Every row is answered
against a run, and a run names the resolved input that produced it. A review
performed on a file that has since been rewritten establishes nothing, which
[`layout-verification.md`](layout-verification.md) records happening.

## What the four computable rows found on the first mask they ran against

A design that had previously released clean, re-run with the four conditions in
place, reported three unmet. **One was the check and two were the mask**, and
separating those was the first task.

**The check.** The naming condition compared the declared name against the top
cell case sensitively and reported that a die cell named by uppercasing the
design name did not carry it. It carries it exactly. The comparison is now
case-insensitive.

**The mask, twice.** The layout declares no device name, so no label can be
matched to a device and a station measuring by label could identify none of
them; the die carries one text and that text names an electrode gap. And ten
ridge-to-ridge spaces sit between 0.300 and 0.330 um, legal against a 0.300 um
rule and illegal after a tenth of an excursion. **The deck reported all ten
legal**, which is what a rule check does: it reports violations and not margins.

The fourth condition passed, and the reason it is believable is that the same
inventory reports an empty mask as unmet rather than as unique.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) L053 on a cell sitting
exactly on the rule it is checked against, L059 on the three checks that clear a
mask, L062 on the coupler's own process window, T097 on a review whose numbers
outlived the file that produced them, and L055 on the difference between a waiver
and a silence. The release conditions are implemented in
[`../../design-chain/src/picchain/stages/s15_release.py`](../../design-chain/src/picchain/stages/s15_release.py),
the label inventory in `s12_mask.py` and the rule margin in `s06_drc.py`.

The list itself is the pre-submission review checklist of a multi-project
electron-beam run, which separates the author's own verification from a peer
assessment against the same criteria.
