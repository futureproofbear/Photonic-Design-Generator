# The mask path of this chain, set against the Luxtelligence LT-PRO ltoi300 process

> **This report describes the run it names and the chain of 2026-09-03.**
> Three of the departures it records under section 3 have since been closed and
> one figure it quotes has moved, so a reader taking sections 1 to 4 as the
> current state of the chain would be misled. What changed is listed here and
> the sections themselves are left as written, because the change they rest on
> is not yet accepted.
>
> * **§3.3, the grating layer.** The report states that a grating post carries
>   no identity a layer map could redirect. `layout.grating_layer` now names the
>   layer the posts are drawn on, a preflight check refuses a name absent from
>   the layer map, and five tests hold it. Run
>   `20260903-112458-ltoi300_mask_grating_layer` emits 80.1 um2 on
>   `RIDGE_PERIODIC`, being 2/11, and verifies PASS.
> * **§3.4, the die footprint.** The report states 10060.0 by 5010.0 um against
>   a footprint the process does not offer. The seal-ring deduction was made
>   conditional and the current emission is 10100.0 by 5050.0, with a two-sided
>   check reporting `reticle.die_smaller_than_declared`.
> * **§3.7, the slab.** The report states that the slab is drawn as a band under
>   the guide alone and that `slab_from_ridges` has no call site. It is called
>   now, and the slab is derived from the ridges wherever
>   `platform.slab_offset_um` is declared.
> * **§4** lists all thirteen remediations as outstanding. Items 4, 5 and 8 are
>   the three above.
>
> **The run of record named below is superseded and deliberately so.** Run
> `20260904-081120-ltoi300_mask` is the same design on the current chain, and it
> moves `layout.geometry.by_layer.SLAB.area_um2` from 303762.809 to 14390.680.
> The stored golden reference still holds the earlier slab and disagrees with
> the current emission by 289420 um2, which `picchain golden` reports and which
> is an explicit act to accept. **Until that reference is adopted the run of
> record is the one this report names**, and rewriting the report against a run
> whose geometry has not been accepted would put a number in front of a reader
> that no reference stands behind.
>
> Section 6 is independent of all of this. It measures the vendor kit's own
> cells and touches neither the chain's emission nor the golden reference.

**Run of record:** `runs/20260903-102000-ltoi300_mask`, status `ok`,
`verify` PASS on 4 of 4 targets, 9 findings emitted and 9 acknowledged.

**Question.** Can this chain emit a mask that the LT-PRO process would accept,
and where does it fail?

**Answer.** A die was emitted and the foundry runset returned zero violations
on it. The die is nevertheless not submittable. The runset declares 46 rule
categories and 30 of them read only layers that carry no polygon on this mask,
so the clean verdict is a statement about the 16 rules that had geometry to
examine. Among the layers left empty are 3/11 and 2/11, which are the layers on
which the departures that matter would have been drawn. The emitted die carries
no edge coupler, no slab-etch negative and no repeating-feature layer.

At the time of the run all three were properties of the chain. **The third has
since become a property of the design file**: `layout.grating_layer` names the
layer the grating posts are drawn on, and a probe run emits them on 2/11. The
first two remain properties of the chain.

### Where the process requirements in this document come from

Every statement below attributed to "the manual" is taken from the working notes
held untracked at `design-chain/pdk/LXT_LT_PRO/MANUAL_NOTES.md`, read 2026-09-03.
That file is the record held in this repository of a document obtained from the
foundry under their terms and not redistributed, and it is excluded from version
control with the materials file and the rule decks beside it.

**A reader without the manual cannot reconstruct those statements**, which is the
consequence of the terms rather than an omission. The tracked entry in
[`references/README.md`](../../references/README.md) says what the manual governs
and where each derived value enters a design, and carries none of its figures.
The notes were held in that entry until 2026-09-05 and were moved on finding
that this repository's remote is public.

The rule deck is
`design-chain/pdk/LXT_KLayout_DRC_Runsets/LT_PRO_ltoi300.lydrc`, which declares
itself `LT-PRO ltoi300 DRC` at version 2.0. It is excluded from version control
under the foundry's terms and its content is described here rather than
reproduced.

The open process design kit is `design-chain/pdk/lxt_pdk_gf/ltoi300/`, which is
public and carries the MIT licence.

---

## 1. What was run, and against what

The design is [`design.yaml`](design.yaml). It draws a 0.7 um ridge on the
LTOI300 stack, being a 300 nm lithium tantalate film on a 7 um buried oxide,
etched 180 nm to leave a 120 nm slab, with a 70 degree sidewall, a 2 um
cladding, x-cut, operated at 1310 nm. A third-order Bragg mirror of 500 um is
drawn at a post width of 300 nm and a post gap of 630 nm, flanked by a pair of
first-metal electrodes on a 7 um gap. The die is 10.1 by 5.05 mm.

Seven stages were executed: `mode`, `grating`, `layout`, `reticle`, `drc`,
`mask` and `verify`. The rule deck was executed by the KLayout application
found at `%APPDATA%\KLayout\klayout_app.exe` against the assembled die.

The environment fingerprint of the run records chain revision `87a4d23` with
the working tree dirty and 15 files modified. Two of them are files this
document makes claims about. `design-chain/src/picchain/config.py` is modified,
and its diff touches `PhaseTrimmer` and `FDTDCfg` alone, so every assertion made
below about `LayoutCfg`, `ChipFrameCfg`, `ReticleCfg`, `MaskCfg` and `ProcessCfg`
holds at the revision recorded and in the tree as it stands. The other is
`examples/ltoi300_mask/` itself, which is untracked and holds this design and
these documents. `references/README.md` is modified as well, which is the point
made above about the source of the process requirements.

The runset is distributed for interactive use and names neither an input nor a
report file, so the chain prepended `source($input)` and gave the existing
`report(...)` call a second argument. The rules were passed through unaltered.
The bound script is held beside the run as `drc_deck.bound.drc`, and a
comparison against the runset's own text returns exactly those two additions.

### What the physical stages returned

| metric | value |
|---|---|
| `mode.n_guided_modes` | 1 |
| `mode.n_eff_bare` | 1.74824 |
| `mode.n_g` | 2.18928 |
| `mode.confinement_film` | 0.64470 |
| `mode.n_slab_floor` | 1.58645 |
| `mode.n_clad_max` | 1.44680 |
| `grating.period_um` | 1.123806 |
| `grating.bragg_wavelength_nm` | 1310.000 |
| `grating.kappa_L` | 0.15908 |
| `grating.peak_reflectivity` | 0.02483 |
| `grating.fwhm_GHz` | 122.447 |
| `grating.sidelobe_suppression_dB` | 13.196 |

**One of the four passing targets is satisfied by construction.** The design
declares `grating.target_wavelength_um` and no period, so the grating stage
solves the period that lands the Bragg condition on 1310 nm and then reports
that wavelength. The target `1310.0 nm ± 2 %` therefore receives its own input
back, and `verify` records the deviation as 6.9e-14 per cent, which is the noise
of the inversion and its return. The remaining
three targets are checks. The mirror strength and the stop band carry no target
here and are recorded above for the record.

### The emission

| quantity | value |
|---|---|
| device cell | `LTOI300_MASK`, 1048.41 um long, 894 polygons on the ridge layer |
| grating periods drawn | 445 of 445; `layout.mask_is_complete` is true |
| die cell | `LTOI300_MASK_DIE` |
| chip boundary 6/1 | 10100.0 by 5050.0 um, centred on the origin |
| usable area 6/0 | 10000.0 by 4950.0 um, inset by 50 um |
| grid snap | 3673 of 3685 vertices moved, 0.638 nm maximum displacement |
| period dither | 0.288 nm RMS, 0.500 nm maximum, over 445 periods |
| backend comparison | KLayout against gdsfactory, exclusive-or residual 0 um2 |
| geometry check | 0 issues; the minimum interior angle is 89.843 degrees on the ridge layer and 43.603 degrees on the orientation key |
| isolation | 0 overlapping polygons between `WG` and `METAL` |

Merged area on the die, measured from `ltoi300_mask.die.gds` with the KLayout
region engine: 10253.7 um2 on 2/10, 432778.6 um2 on 3/10, 6057.0 um2 on 4/0 and
129107.7 um2 on 20/0. The first and the last are also carried by
`mask.connectivity`; the middle two were measured for this document.

The layout regression reference was established in two further runs.
`runs/20260903-094529-golden` wrote `golden/ltoi300_mask.gds`, and
`runs/20260903-094542-golden` re-emitted the device and compared it against
that reference, returning an exclusive-or residual of 0 um2 across every layer.

---

## 2. What the rule deck reported

**Zero violations.** The report database `drc_deck.lyrdb` declares 46 rule
categories and holds no items. The deck ran in 0.117 seconds.

The declared in-process rules, which restate the layer table as a smoke test,
also returned zero across six rules.

### How much of the deck the verdict describes

Each of the deck's 46 outputs was set against the layers it reads. Thirty of
them read at least one layer that carries no polygon on this mask, so thirty
were evaluated against an empty region and were incapable of failing. Sixteen
had geometry to examine, and those sixteen are what the clean verdict
describes.

| exercised | count | what they check |
|---|---|---|
| yes | 16 | the chip boundary size, its centring and its 50 um enclosure of the usable area; ridge width and gap; slab width; label width, gap and separation from the ridge; first-metal width and gap; first metal to ridge separation; first metal overlapping the ridge; ridge, labels and first metal outside the usable area |
| no | 30 | every rule on 2/11, 3/11, 22/0, 23/0, 40/0 and 41/0, and the four rules keyed on the intersection of 3/11 with 3/10 |

### The layers the deck reads, and which of them carry geometry

| deck name | layer | drawn by | exercised |
|---|---|---|---|
| RIDGE | 2/10 | `WG` | yes |
| RIDGE_PERSTRCT | 2/11 | nothing | **no** |
| SLAB | 3/10 | `SLAB` | yes |
| SLAB_NEG | 3/11 | nothing | **no** |
| RIB_MARKERS | 4/0 | `LABEL` | yes |
| CHIP_INNER | 6/0 | `CHIP_INNER` | yes |
| CHIP_OUTER | 6/1 | `CHIP_OUTER` | yes |
| M1 | 20/0 | `METAL` and `PAD` | yes |
| M2 | 22/0 | nothing | **no** |
| HRL | 23/0 | nothing | **no** |
| VIA_M1_M2 | 40/0 | nothing | **no** |
| VIA_M2_HRL | 41/0 | nothing | **no** |

Four rules key on the intersection of 3/11 with 3/10, which the deck treats as
the signature of an edge coupler. Three are separations, holding the first
metal 20 um clear, the second metal 10 um clear and the high-resistivity layer
10 um clear. The fourth reports the first metal overlapping that intersection.
The intersection is empty on this mask, so all four were unexercised.

The deck declares 2/11 as an input and writes no rule against it. A grating
placed on 2/10 therefore produces no violation, and the misplacement is
invisible to the check.

### The verdict was tested for its ability to fail

A clean report is evidence in proportion to the ability of the check to return
a failure, so two deliberate breaches were introduced and the deck was re-run.

**Probe 1, `runs/20260903-093659-ltoi300_mask`.** The taper tip was set to
150 nm against the 250 nm minimum ridge width. The deck reported 4 items in the
category `RIB min. feature size violation (0.25um)`.

**Probe 2, `runs/20260903-094029-ltoi300_mask`.** The grating order was set to
1, which solves a period of 374.48 nm, and the mirror was shortened to 50 um so
that the probe ran quickly. A 300 nm post then leaves a longitudinal gap of
74.48 nm against the 300 nm minimum. The deck reported 266 items in the
category `RIB min. gap violation (0.3um)` over the 134 periods drawn, which is
133 interior gaps on each of two rows, and the declared in-process rule
reported the same 266.

The deck is therefore able to fail on this geometry, and the clean verdict of
the run of record carries evidence about the sixteen rules that were exercised.

Probe 2 also shows that the deck is to be run against the die. It was run
against the device cell, where 6/0 carries no polygon, and the deck reported a
further 272 items of `RIDGE outside CHIP_INNER` and 4 of `M1 outside
CHIP_INNER` for that reason alone.

---

## 3. Departures between the emission and the process

Ranked by whether the departure would cause a submission to be rejected or
would return a die that cannot be used. Each entry states whether it was
established by a run or by reading the code and the deck.

### 3.1 The die carries no edge coupler

**Severity: the returned die has no optical access. Established by measurement
of the emitted die and of the open PDK cell.**

The manual requires an edge coupler to protrude about 5 um beyond layer 6/1 and
to carry a uniform-width section about 10 um long whose midpoint sits on the
6/1 edge, so that singulation tolerance leaves the facet cross-section
unchanged.

The emitted die terminates its ridge 70.00 um inside the 6/1 boundary and
20.00 um inside the 6/0 boundary. The required position is 5 um outside 6/1, so
the shortfall is 75 um. After singulation the guide ends inside solid material
and the die has no facet.

The open PDK cell `edge_coupler_oband` was generated and measured, and it shows
what the process expects. It is a double-layer inverse taper. A lower taper is
drawn on 3/10 from 0.35 um at the facet, widening to 5.6 um over 160 um, and it
carries a uniform 0.35 um section 10 um long at the facet end. The ridge on
2/10 tapers from 0.25 um to 0.7 um over the final 80 um only. The whole
structure sits inside a 170 by 20 um box on 3/11, which removes the slab around
it.

The chain draws a single-layer ridge taper from a 0.40 um tip to 0.70 um over
150 um. It draws no lower taper, no slab-clear box and no uniform section, and
`layout` carries no field by which any of the three could be requested.

### 3.2 The slab-etch negative is absent, so the whole die is blanket slab

**Severity: the device is drawn on a continuous guiding sheet, and four deck
rules are unexercised. Established by a probe run.**

On this process the slab remains everywhere by default and the mask that
removes it is 3/11 minus 3/10. Nothing was drawn on 3/11, so the 120 nm slab is
continuous across the entire 10.1 by 5.05 mm die.

The chain's own mode solve establishes that such a sheet guides. It reports a
slab-mode index floor of 1.58645 against a cladding index of 1.44680, so the
unetched film supports a slab mode and the die offers a path from edge to edge
that bypasses every device on it.

The chain was tested for whether the layer can be reached at all.
[`probe_slab_negative.yaml`](probe_slab_negative.yaml) declares
`SLAB_NEG = FLOORPLAN not SLAB` on 3/11 through `layout.derived_layers`, which
is the only mechanism the chain offers. The derivation executes and writes the
layer. It produces 10584.1 um2 against the 49067221.4 um2 lying inside 6/0 and
outside the slab, which is 0.022 per cent of the area requiring clearance.

The cause is that `FLOORPLAN` is the only field extent the layout stage draws,
and it is sized 5 um outside the slab band it would have to be subtracted from.
The die-level extents 6/0 and 6/1 are drawn by the reticle stage, and
`apply_derived_layers` runs inside the layout stage, so no derivation can reach
them.

### 3.3 Every grating lands on 2/10

**Severity: the repeating structure is submitted on the layer for general
features, and no check reports it. Established by reading the layout stage and
by the deck's layer coverage.**

This gap was known and is confirmed. The open PDK layer map at
`design-chain/pdk/lxt_pdk_gf/ltoi300/tech.py` declares LT_RIDGE 2/10, LT_SLAB
3/10, SLAB_NEGATIVE 3/11, LABELS 4/0, M1 20/0, M2 22/0, HRL 23/0, VIA_M1_M2
40/0 and VIA_M2_HRL 41/0. Layer 2/11 is absent from it. The chain's
`layout.layer_map` is likewise silent on 2/11, and a search of the whole package
finds the number in one place alone, which is the deck's own input list.

The cause lies deeper than the layer map. In
`design-chain/src/picchain/stages/s05_layout.py`, `build_polygons` appends every
grating post to `out["WG"]` alongside the guide itself, so the posts carry no
identity a layer map could redirect. A derived layer cannot separate them
either, because no drawn layer marks the extent of the grating.

The deck writes no rule against 2/11, so the misplacement is silent. What is
lost is whatever process treatment the foundry applies to that layer.

### 3.4 A disabled seal ring still shrinks the die by twice its width

**Severity: the facet plane and every frame item are displaced by 20 um, and the
reported die size differs from the drawn one. Established by a control run.**

`reticle.seal_ring.enabled` was set false, the LT-PRO layer table declaring no
seal-ring layer. The emitted frame then measured 10060.0 by 5010.0 um against a
declared 10100.0 by 5050.0 um. A control run with the ring enabled,
`runs/20260903-094701-ltoi300_mask`, emitted exactly 10100.0 by 5050.0 um.

In `s14_reticle.py` the band deducted from the declared die is computed as the
margin plus the seal clearance plus `cfg.seal_ring.width_um` plus the dicing
lane, while the ring is drawn with a width of zero when it is disabled. The
20 um is therefore deducted and never used, twice per axis.

Two consequences follow. `reticle.align_facet_to_edge` places the facet on the
inner line of the emitted frame rather than on the drawn 6/0 boundary, so the
ridge stops 20 um short of it. The metric `reticle.die_width_um` reports
10060.0 um, which lies outside the set of footprints the process offers, while
the boundary actually drawn on 6/1 is the admissible 10100.0 um.

### 3.5 The reserved corners are expressed by no field

**Severity: compliance on this die is incidental. Established by measurement of
the emitted die and by reading the configuration model.**

The manual reserves the four 75 by 75 um corners for foundry structures, and the
deck writes no rule about them. `ReticleCfg.chip_frame` carries
`exclusion_zone_um`, `allowed_edges_um` and `edge_tolerance_um`, and nothing
that describes a corner.

The four corner squares were measured on the emitted die. Three layers reach
into them: the chip boundary 6/1 fills all four at 22500 um2, the usable area
6/0 enters at 2500 um2, and the dicing lane on 202/0 occupies 12100 um2. The
first two are the frame layers themselves and are drawn there by definition.

**Every fabrication level stands clear**, and the margin is smaller than the
edge clearances suggest. Measured as the Euclidean distance from the nearest
reserved-corner square, the slab on 3/10 is closest at 41.0 um, the ridge on
2/10 stands at 49.5 um, the first metal on 20/0 at 59.4 um and the labels on
4/0 at 4790.9 um. On the simpler measure of distance to a die edge those same
layers stand at 64.0, 70.0, 117.0 and 200.0 um.

That outcome follows from the 80 um dicing lane and the 40 um mark size. The
binding margin is the 41.0 um of the slab, which the reticle stage grows from
the ridges it finds. A smaller lane, a larger mark or a wider slab offset would
place a fabrication level in a reserved corner, and the chain would report it
nowhere.

The dicing lane itself is drawn 20.00 um from the die edge, which places it
inside both the 50 um exclusion zone and the reserved corners. It is harmless
only because 202/0 was chosen for it, and that layer lies outside the set this
process reads.

### 3.6 Bends are discretised more coarsely than recommended

**Severity: a scattering loss the chain does not model. Established by
measurement of the emitted device.**

The manual recommends about 500 nm per segment at 1550 nm, which scales to about
423 nm at the 1310 nm this design operates at. The open PDK ring cells draw 0.15
degrees per segment, being 524 nm at a 200 um radius.

The angled lead-in of the emitted device was measured off the written file. The
polygon carries 66 vertices. The arc turns 8 degrees at a 500 um radius and is
drawn in 24 chords of 2.911 um. That is 5.8 times the 500 nm the manual states
at 1550 nm, and 6.9 times the 423 nm that figure scales to at 1310 nm. The 24 is
a literal default of `_angled_lead_in` in `s05_layout.py` and `layout` offers no
field that reaches it.

The straight run of the same lead-in is sampled at 8 stations of 18.75 um,
because `_angled_lead_in` derives its own station count and never reads
`layout.taper_segments`. That field was set to 64 in this design and had no
effect on the drawn taper.

### 3.7 The slab is drawn as a blanket band rather than as a strip

**Severity: the drawn cross-section differs from the one the mode solve
describes. Established by measurement against the open PDK cell and against the
chain's own cross-section artifact.**

`platform.slab_offset_um` was declared as 6.0 um, which is the open PDK
convention. The mode stage reads it and solves a cross-section whose slab spans
-6.35 to +6.35 um, being the guide width plus twice the offset. The `edbr`
device ignores it. `build_polygons` appends one slab rectangle whose half-height
is set by the reach of the bond pads, giving 143.5 um, and the drawn band
therefore measures 287.0 um in height across the whole 1048 um device.

The comparison was made against the open PDK cell `straight_rwg700_oband` over
a window 10 um along the straight feed and 40 um across it, layer by layer.

| layer | this chain | open PDK | exclusive-or |
|---|---|---|---|
| 2/10 ridge | 7.000 um2 | 7.000 um2 | **0.000 um2** |
| 3/10 slab | 400.000 um2, filling the window | 127.000 um2 | 273.000 um2 |
| 3/11 slab negative | 0.000 um2 | 0.000 um2 | 0.000 um2 |

The ridge agrees exactly. The open PDK draws a slab strip of 12.7 um, which is
the figure the chain's own mode solve used. The band the layout stage draws is
287 um tall and fills the 40 um window entirely.

`build_mzm_polygons` in the same file honours `platform.slab_offset_um` by
building a strip along each guide, and the reticle stage honours it when adding
slab under the process monitors, so the omission is confined to the `edbr`
device.

The helper written for exactly this purpose, `slab_from_ridges` at
`s05_layout.py:332`, grows a strip of the declared offset around every drawn
ridge and opens it to clear the spikes that sizing leaves at an acute tip. A
search of the package finds its definition and no call site. Both the modulator
device and the reticle stage size their own strips inline instead.

### 3.8 A real violation is reported as a deliberate monitor breach

**Severity: a defect anywhere on the die can be reclassified as a process
monitor, silently. Established by a probe run.**

The reticle stage measures the monitor field from the written die by taking a
width check over the whole waveguide layer and drawing a box around whatever it
finds, on the reasoning that the critical-dimension vernier alone is drawn below
the minimum width. Any genuine sub-minimum feature elsewhere on the die
therefore enters that box.

This was observed in probe 1. With the taper tip at 150 nm, the measured monitor
field came back as `[-5015.01, 600.18, -3886.59, 1066.13]`, which is the device
and not the vernier. The in-process rule then reported 0 real violations and 2
in the monitor field, while the deck reported 4 items of `RIB min. feature size
violation`. The run of record measures no monitor field at all, the vernier
being drawn at 250 nm and above, and reports `declared_region_um` as null.

### 3.9 A two-metal stack cannot be drawn

**Severity: no modulator using both metals can be submitted. Established by
reading the layout stage and the deck; the consequence for the deck is reasoned
and is recorded as open in section 5.**

The process offers M1 at 20/0, M2 at 22/0, HRL at 23/0 and the contact layers
40/0 and 41/0, the last two at a minimum width of 10 um, a minimum separation of
7.5 um and an enclosure of 2.5 um within the metals they join. The chain draws
`METAL` and `PAD` and nothing else, and it carries no concept of a contact.

`METAL` and `PAD` were therefore mapped together to 20/0 in this design, and the
chain reported the aliasing from two independent sites. The alternative places
the pad on 22/0, where it abuts its electrode across a layer boundary with no
contact drawn on 40/0.

### 3.10 The label separation the deck enforces exceeds the one the manual states

**Severity: a design drawn to the manual figure would be reported by the deck.
Established by reading both; the consequence is recorded as open in section 5.**

The manual entry records that labels on 4/0 are to be kept 12 um from any
guiding structure. The deck enforces a 15.0 um separation between 4/0 and the
ridge. The two figures disagree by 3 um and the deck is the stricter.

The die label on this mask is drawn as polygons on 4/0 and stands 200.00 um from
the nearest die edge and well clear of any ridge, so the rule passed. The
chain's four electrode net labels are written as GDS text records instead. The
deck reads polygons, so those four are invisible to it, while 4/0 is a drawn
level of the process.

### 3.11 A first-order grating is not drawable on this process at 1310 nm

**Severity: a platform constraint, and the preflight did not run. Established by
a probe run and by reading the preflight.**

Probe 2 established the arithmetic on the mask. A first-order period at 1310 nm
is 374.48 nm and a 300 nm post leaves a 74.48 nm longitudinal gap against a
300 nm minimum. The design ran, drew 134 periods and was refused by the deck 266
times.

The preflight in `design-chain/src/picchain/preflight.py` carries
`the_grating_period_suits_the_order`, and that check returned before evaluating
anything. It begins by returning where `grating.period_um` is unset, and this
design sets `grating.target_wavelength_um` instead, so the resolved period is
solved by the grating stage and the preflight sees none. Remedy 11 of section 4
therefore addresses the early return as well as the test.

### 3.12 The mask stage compared its extraction against nothing

**Severity: a stage reported as run graded no expectation. Established by
reading the design file and the mask stage.**

`mask.target` is `die`, and the design declares an expectation at neither scale:
`expected_regions`, `expected_regions_die`, `expected_nets` and
`expected_nets_die` are all empty or null. The stage selected an empty set and
made no comparison. Its own report of a skipped comparison stayed silent as
well, that report firing only where an expectation exists at the other scale, so
a reader is told nothing at all. The stage extracted 2960 nets and 2948
connected regions on 2/10 and set them against nothing.

`mask.expectations_describe` is `device` in this design and is inert, the die
branch of the stage reading it nowhere.

The isolation check did run and returned zero overlapping polygons between `WG`
and `METAL`, which is a real result.

`mask.density_windows` is empty and no fill was placed, the manual entry
recording no density window, no fill pattern and no fill pitch. The manual
states that filler patterns and guard-rail dummy waveguides are added by the
foundry during mask preparation.

---

## 4. The changes that would close the gap

Ranked by the consequence of leaving each unchanged. Every file named lies under
`design-chain/src/picchain/`.

| # | change | file and field |
|---|---|---|
| 1 | Draw an edge coupler. Add a `layout.edge_coupler` block carrying the lower-taper layer, the tip width, the final width, the total taper length, the upper taper length and the input extension, and draw the lower taper and its clear box in `build_polygons`. | `config.py` `LayoutCfg`; `stages/s05_layout.py` `build_polygons` |
| 2 | Place the facet on the outer boundary. `align_facet_to_edge` computes the facet plane from the emitted frame and lands it on 6/0. Add `reticle.facet_reference` selecting the inner or the outer boundary, and add `reticle.facet_protrusion_um` so that the uniform section straddles 6/1 as the manual requires. | `config.py` `ReticleCfg`; `stages/s14_reticle.py` |
| 3 | Give the slab-etch negative a drawn extent. Either add `layout.slab_clear_layer` with one box per coupler, or move `apply_derived_layers` so that it can also run at die level where 6/0 exists. | `config.py` `LayoutCfg.derived_layers`; `stages/s05_layout.py` `apply_derived_layers`; `stages/s14_reticle.py` |
| 4 | Give the grating posts a layer of their own. Add `layout.grating_layer`, defaulting to `WG` so that existing masks are unchanged, and add a `BRAGG` entry to the default layer map. | `config.py` `LayoutCfg.layer_map` and a new `LayoutCfg.grating_layer`; `stages/s05_layout.py` `build_polygons` |
| 5 | Deduct the seal-ring width only where the ring is drawn. The `bands` expression reads `cfg.seal_ring.width_um`, and the value it is to read is the `sw` computed sixteen lines below it, so the two are to be reordered. | `stages/s14_reticle.py`, the `bands` expression and the `sw` assignment |
| 6 | Express the reserved corners. Add `reticle.chip_frame.reserved_corner_um`, defaulting to zero, and report every fabrication level found inside the four corner squares. | `config.py` `ChipFrameCfg`; `stages/s14_reticle.py` |
| 7 | Make the bend discretisation a declared quantity. Add `layout.bend_segment_um` and pass it to `_angled_lead_in` and `_cos_sbend`, which carry the literals 24 and 96, and let `_angled_lead_in` honour `layout.taper_segments` for its straight run. | `config.py` `LayoutCfg`; `stages/s05_layout.py` `_angled_lead_in` and `_cos_sbend` |
| 8 | Honour `platform.slab_offset_um` in the `edbr` device, as `build_mzm_polygons` does by building a strip of `width + 2 * offset` along each guide. The mode stage already solves the cross-section that field describes, so the two frames would then agree. The helper `slab_from_ridges` was written for this purpose and is called by nothing, so either it is wired in here or it is removed. | `stages/s05_layout.py` `build_polygons` and `slab_from_ridges` |
| 9 | Derive the monitor field from where the monitors were placed rather than from a width check over the whole die, or intersect that width check with the monitor rows. | `stages/s14_reticle.py`, the `monitor_field_box` block |
| 10 | Draw contacts. Add a `VIA` layer to the default map and a `layout.vias` block carrying the enclosure, so that a pad on a second metal reaches the electrode it drives. | `config.py` `LayoutCfg.layer_map`; `stages/s05_layout.py` |
| 11 | Refuse a grating whose drawn gap falls below the declared minimum. Add `process.min_gap_um` and `process.min_width_um`, extend the preflight check to compare the period minus the post length against them, and remove the early return that skips the check wherever the period is solved from a target wavelength. | `config.py` `ProcessCfg`; `preflight.py` `the_grating_period_suits_the_order` |
| 12 | Report the region and net comparison as skipped where no expectation describes the layout being checked, rather than selecting an empty set and comparing silently. | `stages/s12_mask.py`, the expectation selection |
| 13 | Emit net labels as polygons on the label layer as well as text, where that layer is a drawn level, so that the deck reads what the process prints. | `stages/s05_layout.py` `_write_klayout` |

---

## 5. What could not be settled

**Whether the deck would report a pad on the second metal as connected.**
Section 3.9 reasons that a pad on 22/0 abutting an electrode on 20/0 produces an
empty intersection, and that the deck's missing-contact rule is computed from
that intersection, so a pad joined to nothing would be reported as clean. The
deck line supports the reasoning. The case was put to no run, and one run with
`PAD` mapped to 22/0 would settle it.

**Whether a label at the manual's 12 um would be reported by the deck.**
Section 3.10 reasons that it would, the deck enforcing 15 um. The case was put
to no run. On this chain the question is narrower than it appears, because only
the reticle stage's die label is drawn as polygons and the net labels are text
the deck cannot read.

**Whether the process imposes a density window on submitted data.** The manual
entry records none, and the statement that the foundry adds the filler during
mask preparation is consistent both with a window the foundry satisfies and with
the absence of a window. The mask stage performed no density check for that
reason.

**Whether the deck would report an edge coupler drawn to the manual.** The
manual requires the coupler to protrude beyond 6/1, and the deck reports ridge
material outside 6/0 as a violation. A coupler drawn as the manual requires
therefore produces violations of that category, and whether the foundry waives
them at review remains open. No such structure exists on this mask, so the
question was put to no run.

**Whether 2/11 carries rules in a later revision of the deck.** The deck held
here is version 2.0 and it declares 2/11 as an input while writing no rule
against it.

**The manufacturing grid.** The sources read for this study state a grid figure
for this process nowhere. One nanometre was assumed. At that assumption the
third-order period of 1123.81 nm acquires a 0.288 nm RMS dither, and that dither
is carried by no model in the chain.

---

## 6. The kit's own cells, measured off the polygons they write

Chain rule 11 requires a geometric parameter to be measured back off the written
file. Three cells of this kit had been measured that way before today, each for
one question: `edge_coupler_oband` in section 3.1, `straight_rwg700_oband` in
section 3.7, and the modulator electrode in the companion modulator study. Every
other geometry the studies used was rebuilt from the parameters its builder
declares, and no cell had been measured against everything its builder declares.

[`scripts/as_drawn.py`](scripts/as_drawn.py) does that. Every cell is built and
written, and each declared quantity is set against a cut through the file at the
station where that quantity is defined. The tolerance is one nanometre, being
the database unit.

Sixty-nine quantities across seventeen cells were checked, and the presence of
the termination on twelve. All eighty-one readings agree.

| Cell class | What was checked | Result |
| --- | --- | ---: |
| The three straights | guide width and length, and the slab width on `straight_rwg700_oband` | exact |
| The four MMIs | port width, taper at the interface, section width, port separation, gap between the tapers, total length | exact |
| The four rings | ring width, bus width, coupler gap | exact |
| The two edge couplers | slab tip, ridge tip, both widths at the output, the transverse clearance window, the ridge run | exact |
| The four electro-optic phase shifters | signal and ground widths and the gap, on the rail and in the rail cut, and the guide within the gap on `terminated_eo_phase_shifter_oband` | exact |
| The twelve terminated and unterminated cells | whether the resistor layer reaches past the end of the signal metal | as declared |

Two things were found by measuring rather than by reading, and neither is a
defect in the kit.

**The modulator electrode is periodically interrupted and every travelling-wave
figure this repository holds was computed on a uniform one.** Cutting along the
run shows the O-band signal conductor stepping between 20 um and 10 um and its
gap between 5.5 um and 15.5 um, and the C-band one between 16 and 10 um and
between 5.5 and 11.5 um. The period is 58 um in both, the narrow-gap section
holding for 53 of every 58. The builder names the feature: `trail_cpw` draws "a CPW
transmission line with periodic T-rails on all electrodes", with a rail of 53 um,
a cut of 5 um, and a head and a tooth of 2.5 um each on the O-band cells and
1.5 um each on the C-band ones. The consequence is quantified in the
[Mach-Zehnder study](../ltoi300_mzm/README.md), which solves both drawn
cross-sections and homogenises them over the period: the half-wave voltage rises
by 6.7 per cent, the 3 dB bandwidth falls by 15 per cent, and the impedance rises
2.1 ohm toward 50.

**The edge coupler's lower taper does not follow the profile the study
reconstructed for it.** That is recorded in the edge-coupler study, which has
been re-run on the drawn polygons. The error was in the reconstruction and not in
the kit.

The measurement also settles what distinguishes a terminated cell from an
unterminated one, which had been taken on the cell names. It is one polygon on
the high-resistance layer beyond the far end of the signal metal, being 2911.9
square micrometres on the three O-band terminated cells and 2815.9 on the three
C-band ones. On an interferometer the same layer also carries the bias heater at
the input end, which accounts for 94213 of the 97125 square micrometres a
terminated O-band modulator carries, so the presence of the layer settles nothing
and its reach past the line settles it.

The kit declares the resistor 58.112 um long and 1.5 um wide under the name
`effective_length`, and 58.112 by 1.5 is 87 square micrometres against a drawn
polygon whose bounding box is 53.5 by 131.0. The declared pair therefore
describes the resistive path and the polygon describes the pad it sits in, and
which of the two carries the resistance is not stated. No sheet resistance is
declared for the layer either, so the value cannot be computed from the kit at
all and a terminated cell is taken as matched by declaration.

---

## 7. Files and runs

| file | what it is |
|---|---|
| [`design.yaml`](design.yaml) | the design of record |
| [`DESIGN_CONCEPT.md`](DESIGN_CONCEPT.md) | what the instrument is for, and the trace from each clause to its target |
| [`probe_grating_layer.yaml`](probe_grating_layer.yaml) | the probe that draws the grating posts on 2/11 |
| [`probe_slab_negative.yaml`](probe_slab_negative.yaml) | the probe of section 3.2, which derives 3/11 from the only field the chain draws |
| [`scripts/as_drawn.py`](scripts/as_drawn.py) | the measurement of section 6, every kit cell against every quantity its builder declares |
| [`REPORT.md`](REPORT.md) | this document |
| `golden/ltoi300_mask.gds` | the layout regression reference |

| run | what it is |
|---|---|
| `runs/20260903-102000-ltoi300_mask` | **the run of record**, seven stages, `verify` PASS, deck clean |
| `runs/20260904-081120-ltoi300_mask` | the same design on the chain of 2026-09-04, whose slab and die differ as the note at the head of this document sets out. It is not the run of record because the golden reference for its geometry has not been adopted |
| `runs/20260904-081218-golden` | the golden comparison that reports the 289420 um2 the slab moved by |
| `runs/as_drawn/` | the 25 cells of the kit as `scripts/as_drawn.py` writes them, which section 6 measures. Excluded from version control with every other run |
| `runs/20260903-111652-ltoi300_mask` | an intermediate full run |
| `runs/20260903-112458-ltoi300_mask_grating_layer` | the probe of `layout.grating_layer`, which emits 80.1 um2 of grating posts on 2/11 and verifies PASS |
| `runs/20260903-094453-ltoi300_mask` | the same design before a comment in it was corrected, superseded so that the design file on disk is the one the run of record was taken from; `design.resolved.json` is byte-identical between the two, and the geometry and the deck verdict are identical |
| `runs/20260903-093534-ltoi300_mask` | an earlier full run, superseded when the nine findings were acknowledged; the geometry and the deck verdict are identical |
| `runs/20260903-093659-ltoi300_mask` | probe 1, a 150 nm taper tip |
| `runs/20260903-093957-ltoi300_mask` | a first-order run of the layout stage alone, at the full 500 um mirror, abandoned in favour of probe 2 so that the deck could be run on a shorter grating |
| `runs/20260903-094029-ltoi300_mask` | probe 2, a first-order grating shortened to 50 um, checked against the deck |
| `runs/20260903-094106-ltoi300_mask_slabneg` | the derived slab-etch negative of section 3.2 |
| `runs/20260903-094529-golden` | the layout reference, written |
| `runs/20260903-094542-golden` | the layout reference, re-checked; exclusive-or residual 0 um2 |
| `runs/20260903-094701-ltoi300_mask` | the seal-ring control of section 3.4 |

The figures written under each run directory are the chain's standard plots of
the cross-section, the grating response and the emitted mask. This document
cites none of them and rests on the measurements tabulated above.
