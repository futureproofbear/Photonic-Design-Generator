# A machine-extracted copy of a reference is not the reference

*Tier: generic. Confidence: high, the mechanism is documented and a worked case
is given.*

Machine extraction of a supplier datasheet, a foundry document or a published
paper is ordinarily the only practical way to read it. The extraction is lossy
in ways that are silent, and it produces output that reads as authoritative.
Every quantity a design takes from a document arrives through that extraction,
so the extraction is part of the measurement chain and is to be treated as one.

This rule is stated because a photonic design draws a large fraction of its
inputs from documents rather than from solvers. Material indices, electro-optic
coefficients, gain-chip facet reflectivities, mode-field diameters, chip
lengths, and every foundry design rule enter this way.

## The failure modes

**A multi-column table extracts with its row labels displaced against its
values.** Text extractors group glyphs by baseline. Where a table's label column
and its numeric cells sit on slightly different baselines, which is common when
a header row shares a baseline with the first data row, every value lands
against a neighbouring label. The extractor reports success. The output is a
well-formed table of true numbers against wrong labels.

**The displacement is uniform, and it is therefore detectable.** Check two rows
against a source known independently. A trailing row carrying values and no
label is a strong indication that the whole column is displaced by one. Once one
row is shown to be displaced, treat every row of that table as corrupted rather
than only the row that was caught.

**A derived export drops characters as readily as a page misplaces them.** A
layer list, a pin list or a parameter list exported from a tool may truncate
every name to its stem, so that a suffix distinguishing two entries is lost.
Recovery then depends on inferring the file's own ordering convention, which
remains a guess until it is checked against a second source.

**A page carries no geometry.** Every dimension and every label on a
cross-section drawing may be extracted correctly while the relationship between
them is unrecoverable. Which of two layers sits above the other, which side of a
ridge an electrode is on, and whether a stated thickness is of the film or of
the residual slab are questions the text layer does not answer. Settle them from
a human reading of the drawing, or from a figure, and do not assert them from an
extraction.

**A figure is not extracted at all.** A value read off a plotted curve is a
measurement made by the reader, with the reader's own error, and it is to be
recorded as such rather than quoted to the precision of the axis label.

## The practice

**Before a machine-extracted number is used as an input, cross-check it against
a ground truth the tool produces.** Where the extraction and the tool disagree,
the tool is right. The ground truths available here are the PDK layer database,
the foundry rule deck, the material library and any solver that computes the
same quantity from first principles.

| extracted claim | the tool that settles it |
|---|---|
| a layer number or datatype | the deck's own layer declarations, and whether the design draws geometry there |
| a design-rule value | the rule deck, executed |
| a refractive index at a wavelength | a dispersion relation evaluated at that wavelength |
| a stated mode-field diameter | a mode solve on the declared cross-section |
| a stated V<sub>π</sub>·L | the electrode solve, with the overlap stated |

**Record the provenance beside the value.** A quantity taken from a document
carries the document, the table or section, and the date it was read. A quantity
taken from a figure says so. `# ASSUMPTION:` marks a quantity that was not taken
from any of them.

**Where a document quotes a figure of merit, establish which convention it
uses.** A V<sub>π</sub>·L computed at unit electro-optic overlap differs from the
physical value by 1/Γ, and Γ falls between 0.3 and 0.5 for coplanar electrodes
on a high-permittivity film. A published figure that appears optimistic by a
factor of two to three is frequently the un-derated one. The same applies to an
index quoted as phase where the consumer needs group, and to a loss quoted per
facet where the consumer needs per round trip.

## Evidence

`.claude/LESSONS.md` L006 (overlap-free figures of merit against physical ones),
L015 (replacing an assumption with a sourced value is not a move toward
agreement), T034 (a component requirement is a bound before it is a search),
T035 (adopting a real part changes the mask and not only the model).

The displaced-table mechanism is documented outside this repository as well, and
the worked case there reversed which of two device variants a part carried, on
an extraction that read as a clean table throughout.
