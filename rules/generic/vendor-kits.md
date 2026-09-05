# A supplied kit is audited before a design is built on it

*Tier: generic. Confidence: high, three kits audited, and a defect found in each
by a different one of the checks below.*

A process kit supplies models, layers and cells that no stage of a design chain
re-derives. What the kit asserts is what the design is built on, so the kit is an
input to the measurement chain and is treated as one. Every check below is cheap,
and each has returned a finding.

## The models

**Evaluate passivity and reciprocity over every tabulated model.** The power
leaving a passive device cannot exceed the power entering it, and a structure of
reciprocal materials presents a symmetric scattering matrix. Both bounds cost one
pass over the library.

**Class any violation by a property read off the file.** Port widths are drawn as
pin geometry and can be measured. A violation confined to models whose ports
differ in width, and within those to the direction entering the wide port,
indicates a mode power normalised inconsistently between the two ports rather
than anything physical. Classing by cell name is a corroboration and not the
evidence.

**Establish whether such an error is systematic before attempting to correct
it.** Where the magnitude tracks neither the geometric ratio nor the wavelength,
and clusters instead at two values with the same nominal device appearing in
both, the cause is per-simulation and no user-applied rule corrects it. The
affected models are replaced rather than scaled.

**Read the model's own declarations of what it is.** A model extracted in two
dimensions with the material index frozen at band centre is adequate for a
transmission and wrong for anything derived from a group index. Freezing the
material index costs the group index between one and a half and five per cent,
worst at short wavelength, so a free spectral range computed from such a model is
too large by that amount.

**A non-passive model says the model is wrong and does not say what the device
does.** Replacing it requires geometry, and a black-box cell carries none.

## The layers

**Reconcile the kit's three descriptions of every layer**: the name its layer map
gives a number, the thickness and material its layer stack gives that name, and
the polygons its cells draw. Build every cell, write it, and read back the layers
that carry polygons. On one library eight of the eighteen drawn layers were named
by neither the map nor the stack, among them the layer on which every device of
the kit's second guiding material sits. A three-dimensional solve of such a cell
sees an empty stack where the waveguide should be, and a rule written against a
layer name matches nothing.

**A cell name is not a description of its polygons.** A cell whose name promised
a shallow etch drew every polygon on the full-thickness layer.

**A layer may exist as a name and nothing else**, declared in the map, absent
from the stack, and drawn by no cell.

## The numbers the kit ships

**A table supplied with a kit carries no convergence record.** One such table of
effective indices sat above a converged independent solve at every one of
thirty-two comparisons, by up to 935 times the mesh error of the check. An offset
of one sign says the two problems are not posed identically, and its size
tracking confinement points to the resolution the table was computed at.

## Provenance and installation

**A repository head and a published release are different artifacts.** They carry
different version numbers and different declared dependencies, and an installer
takes the second. Record which was read beside the figure, and state which
findings were measured on which. A correction made by reading the other artifact
will overwrite accurate entries and will read exactly like a repair.

**One environment per kit.** A kit pins the version of the layout engine it
requires, and installing it beside another takes that engine out from under the
design chain.

## What may be written down

**A kit's licence governs what a study may reproduce, and the licences differ.**
One kit under a permissive licence may be quoted freely, including its layer
numbers and cell dimensions. Another forbidding redistribution in whole or in
part may be reported only as counts, verdicts and correlations, with no matrix,
no geometry and no file reproduced. **Read the licence before the study is
written**, because the framing cannot be retrofitted once the figures are in the
prose.

**A document obtained under supplier terms is not a reference that can be
quoted.** Where the terms forbid redistribution, the working notes are held
outside version control and the tracked entry says what the document governs and
where each derived value enters a design, carrying none of its figures. A reader
without the document cannot then reconstruct those statements, which is a
consequence of the terms and not an omission.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) L036 on passivity and
reciprocity, L037 on a non-dispersive model, L038 on a kit's three descriptions
of a layer, L039 on a repository head against a published release, T067 on a
checker keyed on a port where the identity is a port and a mode, and T071 on the
contrast limit and a shipped table without a convergence record. The instrument
is
[`design-chain/tools/check_pdk_models.py`](../../design-chain/tools/check_pdk_models.py).
