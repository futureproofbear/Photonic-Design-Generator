# The overlap test chip, and what taking it through the chain found

**Run of record:** `runs/20260905-131525-ltoi300_mzm_testchip`, nine stages,
`verify` PASS on 4 of 6 targets with both `must` rows met, the declared rules
clean, and the `release` gate blocking on 3 of 11 conditions.

Conducted 2026-09-05. The concept is in
[`DESIGN_CONCEPT.md`](DESIGN_CONCEPT.md) and was written before the targets.

## Why this design was drawn

Not to make a modulator. This chain and the Luxtelligence kit disagree by 31 per
cent about the half-wave voltage of the kit's own C-band modulator arm, the
disagreement sits entirely in the electro-optic overlap, and one device cannot
separate the overlap from the material constant it multiplies. A ladder over
electrode gap can, and the concept sets out why.

**Two figures for that disagreement appear in this repository and both are
right.** The chain returns 7.3482 V·cm on the rail cross-section it solves,
which is 31.2 per cent above the kit's 5.6. Homogenised over the drawn T-rail
electrode it returns 7.7384, which is 38.2 per cent above. This document quotes
31.2 throughout, because that is what the run of record reports; the concept
quotes 38.2, because that is what the mask carries. The 5.31 per cent between
them is the T-rail correction, which the run does not perform.

The device is that ladder: five Mach-Zehnder modulators on one die, differing in
electrode gap alone, at 3.5, 5.5, 8.0, 11.0 and 15.0 um. The 5.5 um rung is the
gap the kit draws and is the one rung the kit states a figure for.

## What the run reports

| | Value |
| --- | ---: |
| Electro-optic overlap | 0.38800 |
| Vπ·L, one arm | 7.34825 V·cm |
| Vπ·L, device push-pull | 3.67412 V·cm |
| Vπ over the 5 mm drawn | 7.348 V |
| Characteristic impedance | 44.24 Ω |
| Worst far-end penalty | −1.85 dB at 9.93 GHz |
| Best far-end advantage | +5.37 dB at 0.1 GHz |
| Declared rules | 4 checked, 0 violations outside the monitor field |
| Foundry deck | 11 violations, unresolved |

**The declared rules are clean only outside the process-monitor field.**
`RIDGE_min_width` found ten features narrower than the 250 nm minimum and
excused all ten as lying inside the declared monitor field, which is what a
critical-dimension vernier is for: it draws below the minimum deliberately so
the wafer shows where the process gives out. The numerator is zero and the
exclusion is ten, and both belong in the sentence.

**The two `should` rows carrying the disagreement fail, and that is the
experiment.** The chain returns 7.348 V·cm against the kit's 5.600, which is
31.2 per cent high. The concept states why those rows are `should` and not
`must`: a `must` on either would be the chain asserting the answer the chip is
built to find.

**The process window does not explain it, and two windows were swept.** The
first, at `runs/20260905-101119-corners-000` to `-102745-corners-006`, moved the
electrode gap by ±200 nm and the arm width by ±50 nm. The second, which is the
one the design now declares and which `runs/corners.md` records, moves the two
layer biases and the film thickness. All fourteen corners pass.

| Sweep | Widest metric spread | On |
| --- | ---: | --- |
| Drawn dimensions: gap ±200 nm, arm ±50 nm | **8.5 %** in `eo.VpiL_V_cm`, 7.035 to 7.663 | the gap |
| Layer biases and film: WG ±50 nm, METAL ±200 nm, film ±10 nm | 7.0 %, 7.092 to 7.605 | the film |

**The disagreement is 31.2 per cent as the run reports it, and 20.6 per cent
once the electrostatic mesh is extrapolated, which is 2.4 times the wider of the
two windows.** It cannot be a process effect, and that is the result that makes the
chip worth fabricating. An earlier revision of this document called the 7.0 per
cent figure "the entire process window" and did not mention the first sweep,
which was wrong on both counts: the drawn-dimension sweep is wider, and it
exists.

| Metric | Corner spread, the layer-bias sweep |
| --- | ---: |
| `eo.eo_overlap_gamma` | 0.3749 .. 0.4020 (7.0 %) |
| `eo.VpiL_V_cm` | 7.092 .. 7.605 (7.0 %) |
| Characteristic impedance | 44.17 .. 44.56 Ω (0.9 %) |

**Fourteen corners passing is a pass on four of six targets over four of nine
stages, and neither denominator was stated until now.** `corners.metrics` names
five quantities and the sweep runs only the stages producing them, so `layout`,
`reticle`, `drc`, `mask`, `verify` and `release` were not exercised at any
corner. The two `must` rows were judged; so were the two carrying the
disagreement. The row on the far-end penalty was not, because
`corners.metrics` still named `electro_optic_3dB_GHz` — the very quantity this
document argues is the wrong figure of merit — and did not name the penalty that
replaced it. The design has been corrected and the sweep not re-run, so the
figures above are those of the sweep as it was declared.

## What taking it through the chain found

This is the first Mach-Zehnder the chain has drawn. `layout.device:
mach_zehnder` had never been run, in 97 layout runs all of which drew the
extended-DBR laser, and the reticle split ladder had never been drawn at all.
Exercising both found four defects, each now corrected. **Two are held by
tests and two are not.** The splitter precondition carries five tests and the
corner nominal carries three. Nothing in the suite calls the reticle stage with
`layout.device: mach_zehnder`, so neither the builder dispatch nor the
suppression of the gap widening is pinned by a test, and the existing ladder
test exercises the extended-DBR path only. Both are asserted by the run and by
the split description it emits, which is evidence and is not a regression
guard.

**The split ladder drew the wrong device.** `_split_cells` called the E-DBR
polygon builder unconditionally, so a ladder beside a Mach-Zehnder would have
drawn extended-DBR lasers as its rungs. It now dispatches on `layout.device` as
the layout stage does.

**The split silently overwrote its own ladder parameter.** Logic belonging to a
grating flanked by electrodes widened `electrodes.gap_um` to clear the posts
from the metal. On a device with `grating.enabled` false it computed that
clearance from the schema's default post geometry, arriving at 6.36 um, and
would have replaced every rung below it. **That is the 3.5 um rung alone.** The
5.5 um nominal is drawn by the layout stage and never passes through the split,
which iterates the four declared values, so the rung the external comparison
rests on was never at risk and an earlier revision of this document said it was.
The correction is now applied only where the device draws posts, and the run
confirms it: `electrode_gap_widened_to_um` is null on all four rungs.

**The splitter could not carry its own arm.** The access ports leave the
multimode section 2.55 um apart, and each widens to the 2.5 um modulation arm
before the S-bend has separated them, so the two guides pass within **50 nm** of
each other against a 300 nm rule, that being 2.55 minus 2.50 exactly. The
declared in-process rules reported 148 violations at both ends of all five
devices; the foundry deck, which is a separate check, reported 11 in the same
run. The builder's own comment states the invariant that
the port taper then breaks. The relation is among three declared fields, so
under chain rule 17 it is now a precondition, which refuses the design in
milliseconds and names the three remedies. Opening the separation to 2.80 um,
the least the rule admits, took the count to zero.

**The corner stage's own advice crashed it.** Where a window varies a drawn
dimension the stage objects that a lithographic excursion moves every feature on
a layer together, and recommends `process.bias_um.<layer>` instead. Following
that recommendation on a design declaring `bias_um: {}` raised `KeyError: 'WG'`
before the first corner ran, a layer carrying no bias having no key rather than
a key of zero. The absence of a bias is now read as a bias of zero, and only for
the bias dictionaries, whose empty state is meaningful.

## Two findings that were the design's fault and not the chain's

**The design said terminated and the mask drew no terminator.** The foundry deck
reported `M2_HRL_no_contact` five times: it expects the line to contact a
resistor on the high-resistance layer, the kit's terminated cell carries one of
2815.9 um², and this chain draws no such layer. Declaring `far_end_load_ohm:
null` therefore described a device the mask does not carry. The design now
declares the far end open, which is what is drawn.

**And then the bandwidth target failed on the wrong quantity.** Declaring the
line open dropped the self-referred 3 dB point to 4.4 GHz and the `should` row
on it failed. That is the trap this repository identified on 2026-09-04: the
self-referred response of an open line is divided by a zero-frequency value the
open end has doubled, so it measures the loss of a doubling rather than the
onset of a loss. The target now reads `far_end_worst_penalty_dB`, which compares
the two lines driven from one source, and bounds the chip at −1.85 dB at a null
near 9.93 GHz, outside the 0.1 to 5 GHz it declares.

## The splitter assumption, settled

**The splitter is no longer the kit's cell, and that turned out to help.** This
was recorded as an open assumption and has since been settled by
[`scripts/splitter_check.py`](scripts/splitter_check.py), which solves the
section in its full cross-section once and re-cascades it at each length.

| Port separation | Transmission at the drawn 13.5 um | Excess | Best length |
| --- | ---: | ---: | ---: |
| 2.55 um, the kit's | 0.9292 | 0.319 dB | 13.75 um |
| 2.80 um, this design's | **0.9805** | **0.086 dB** | 14.00 um |

**Opening the ports to clear the spacing rule gains 0.233 dB rather than costing
anything.** The imaging length is fixed by the beat length of the multimode
section and therefore by its width, which did not change; what the separation
moves is where the images land, and 2.80 um lands them better than 2.55 does on
a section carrying 2.5 um arms. Keeping the kit's 13.5 um rather than the 14.00
the sweep prefers costs a further 0.012 dB, which is not worth redrawing for.

**Neither figure has passed a convergence guard.** The two solves are at one
grid and one mode count, and chain rule 15 requires the guard before the
comparison is read. The 0.233 dB is large against any plausible mesh error and
the 0.012 dB is not: at 2.55 um the sweep's preferred 13.75 um returns 0.9292,
identical to four decimals to the drawn length, so the preferred length in that
row is inside the numerical noise and is reported as a position rather than a
result.

## What the release gate says

It raises, and it blocks the submission on 3 of its 11 conditions. Nothing is
waived, deliberately: the gate was run to find out what it says about a chip
whose purpose is measurement, and a waiver written before the verdict is read
would decide the answer in advance.

| Condition | Why it blocks |
| --- | --- |
| The chain that produced this is a committed revision | 43 files are uncommitted |
| A foundry rule deck was executed | 11 violations remain |
| Density is within the declared windows | no window is declared, so nothing was measured |

**All 11 deck violations stand, and an earlier revision of this document wrongly
said five of them were resolved.** They are 5 of `M2_HRL_no_contact` and 6 of
`M2 outside CHIP_INNER`, and the count has not moved across any of the six full
runs of this design. Declaring `far_end_load_ohm: 1.0e9` changed the electrical
model and drew no polygon, so the deck still finds no resistor for the line to
contact; that was the point of declaring it, and it does not clear the deck.

Eight of the deck's twelve layers carry no polygon on this mask because
`layout.layer_map` does not use the process numbers, which the companion
[mask study](../ltoi300_mask/REPORT.md) records. **Renumbering the layer map is
the remedy for both categories and it is not done here**, so the deck's verdict
covers four layers of twelve and the release gate blocks on it.

## The S-bends, which turn out not to matter

The device draws two S-bends per arm: the splitter to the electrode gap, moving
9.35 um over 220, and the electrode to the probe pad, moving 17.17 um over the
same. A cosine S-bend of lateral offset d over length L carries a minimum radius
of 2L²/(dπ²), so those are 1050 um and 570 um. Radiation from either goes into
the interferometer as loss, and any asymmetry between the arms goes in as
imbalance. Neither had been checked.

| Radius | `n_eff` | Δ from straight | Outward shift | Caustic |
| ---: | ---: | ---: | ---: | --- |
| 1050 um, the splitter bend | 1.771378 | 2.1e-5 | 0.021 um | at 139.5 um, outside the window |
| 570 um, the pad bend | 1.771429 | 7.2e-5 | 0.038 um | at 75.8 um |
| 350 um | 1.771548 | 1.9e-4 | 0.062 um | at 46.5 um |
| 200 um | 1.771943 | 5.9e-4 | 0.107 um | at 26.6 um |
| 100 um | 1.773673 | 2.3e-3 | 0.209 um | at 13.4 um |

**Both drawn bends are far from the radiation limit and the item closes as a
negative.** The caustic does not enter the solve window at any radius down to
100 um, an order of magnitude tighter than either bend draws, and at the drawn
radii the mode centroid moves 21 and 38 nanometres. The straight mode index is
1.771356 against a slab floor of 1.550957, so the guide is strongly bound and
this is the expected result rather than a surprising one.

**Imbalance from the bends is zero by symmetry** and this measurement does not
establish that: the two arms are mirror images, so whatever the bends cost is
common to both, and the imbalance a fabricated device carries comes from width
and etch asymmetry that no figure here represents.

## The mesh carries a third of the disagreement

The electro-optic stage raises a finding on every run of this design: halving the
cell moves the overlap by 3.0 per cent against a 2.0 per cent tolerance. The
design acknowledges it and the concept calls it the reason the chip exists. It
was never quantified here, and it should have been, because a third of the
headline number is in it.

Five cells, the convergence check switched off so that each is one solve:

| Cell | Overlap | Vπ·L, one arm | Capacitance |
| ---: | ---: | ---: | ---: |
| 50.0 nm | 0.371775 | 7.66895 | 1.66717 |
| 35.0 nm | 0.381668 | 7.47016 | 1.68885 |
| **25.0 nm**, as published | **0.388001** | **7.34825** | 1.69750 |
| 17.5 nm | 0.394466 | 7.22781 | 1.69723 |
| 12.5 nm | 0.399539 | 7.13604 | 1.69442 |

**The capacitance is converged and the overlap is not.** Over the last three
cells the capacitance moves 0.18 per cent, so every line parameter that follows
from it — the microwave index, the impedance, the bandwidth, the far-end penalty
— is sound. The overlap rises monotonically and has not stopped.

Fitting `Gamma(h) = Gamma_inf − C h^p` over all five points gives p = 0.570 and
Gamma_inf = 0.4222, with a residual under 5e-4. The sub-linear exponent is the
signature the design file names: the ridge sidewall is sloped and the
permittivity steps across it by a factor of eleven, so the staircased boundary
converges as roughly the square root of the cell.

| Vπ·L, one arm | Value | Against the kit's 5.600 |
| --- | ---: | ---: |
| As published, at a 25 nm cell | 7.3483 | +31.2 % |
| At a 12.5 nm cell | 7.1360 | +27.4 % |
| **Extrapolated to a converged mesh** | **6.7530** | **+20.6 %** |

**A third of the disagreement was the mesh.** That is a correction to this
document, which quoted 31.2 per cent throughout and attributed all of it to the
overlap model.

**The chip is still justified and its margin is thinner.** The remaining 20.6 per
cent is 2.4 times the wider of the two corner windows, so the process is still
eliminated, but the factor is 2.4 and not the 4.5 an earlier revision claimed.
The extrapolation is itself an extrapolation, resting on a two-parameter fit to
five points of a quantity that has not converged, so it is a correction to be
measured rather than a figure to design against — which is what the chip is for.

**The mesh was not changed.** Running at 12.5 nm costs four times the solve for a
figure that is still 27 per cent from the kit, and the extrapolation is carried
beside the run's own number rather than replacing it.

## Every finding the run emitted, and where each went

Nine findings, all nine acknowledged in the design file, four discussed above.
The denominator is stated because a green wall of individually-true checks is how
a false summary gets assembled.

| Finding | Where it is dealt with |
| --- | --- |
| `eo.electrostatic_solve_converged_halving` | above, and it is the reason the chip exists |
| `modulator.3_db_bandwidth_4` | above, the self-referred figure on an open line |
| `drc.rule_deck_names_12` | above, the layer-number mismatch |
| `drc.foundry_deck_reports_11` | above, unresolved |
| **`mode.cross_section_supports_3`** | **here, and nowhere else until now** |
| `reticle.die_carries_seal_ring` | acknowledged: the foundry adds it at mask preparation |
| `reticle.fill_placed_mask_stage` | acknowledged: the foundry places the fill |
| `drc.rule_deck_named_input` | acknowledged: the chain binds the deck without altering a rule |
| `release` raising | the gate, below |

**The arm carries three guided modes and that bears on the measurement.** The
concept treats the depth of the optical null as its one declared limitation and
budgets it from splitter imbalance alone, at 48 dB. A three-mode arm admits a
second channel that budget does not carry: light converted into a higher order
at the splitter, the S-bend or the taper returns at the combiner with an
uncontrolled phase and fills the null. The chip measures the position of the
null rather than its depth, so a filled null costs precision rather than the
measurement, but the figure is not 48 dB and this study does not say what it is.

## What was not done

**No measurement.** That is the point of the chip and it needs a wafer.

**The electrostatic solve is not converged** and is acknowledged as such: halving
the cell moves the overlap by 3.0 per cent against a 2.0 per cent tolerance. The
chip exists to replace that extrapolation with a measurement, so the residual is
the reason for the design rather than a defect in it.

## What the corner sweep did not exercise

Seven corners pass and two of the three parameters moved nothing. The design
declares `process.precompensate: true`, which draws the mask inward by the bias
so that the printed feature lands on the nominal dimension, and a printed
geometry constructed to be bias-independent does not move when the bias is
swept. The sensitivity table shows it directly: the elasticity of every metric
with respect to `process.bias_um.WG` and `process.bias_um.METAL` is blank, and
the whole 7.0 per cent window is film thickness alone, whose half-span
contribution of 3.433 per cent doubles to 6.87 against a measured 6.98, the
residual being the nonlinearity.

**So the corner sweep as declared is a one-parameter sweep wearing three
parameters' clothing.** Exercising a lithographic excursion on this design needs
either `precompensate: false`, or a declared residual the compensation does not
remove. Neither is done here.

**The evidence for that is the corner sweep and not the sensitivity table.** An
earlier revision cited the blank elasticity columns, and those columns are blank
whatever the metrics did: the elasticity is undefined where the nominal is zero
and the tool returns it as such. `runs/corners.json` is the artifact that
establishes the claim, its WG and METAL corners returning the nominal to every
digit. A blank from a comparison that could not be made is not a measurement,
which is the failure this repository has recorded before.

| Metric | Elasticity in film thickness | Contribution over the window |
| --- | ---: | ---: |
| `modulator.Vpi_V` | −1.03 | 3.4 % |
| `eo.eo_overlap_gamma` | +1.03 | 3.4 % |
| `eo.VpiL_V_cm` | −1.03 | 3.4 % |
| `eo.travelling_wave.characteristic_impedance_ohm` | −0.16 | 0.5 % |

The half-wave voltage goes as the reciprocal of the film thickness to within
three per cent of exactly, which is the behaviour a Pockels overlap on a fixed
etch should show and is a check on the stage rather than a result.

## Files and runs

| File | What it is |
| --- | --- |
| [`DESIGN_CONCEPT.md`](DESIGN_CONCEPT.md) | what the chip is for and the trace from each clause to its target |
| [`design.yaml`](design.yaml) | the design of record |
| [`scripts/splitter_check.py`](scripts/splitter_check.py) | the splitter at both port separations, by cross-section cascade |
| `golden/ltoi300_mzm_testchip.gds` | the layout regression reference, adopted 2026-09-05 |
| `runs/corners.md` | the seven corners |
| `runs/sensitivity/sensitivity.png` | the elasticity and contribution tables |

| Run | What it is |
| --- | --- |
| `runs/20260905-131525-ltoi300_mzm_testchip` | **the run of record**, nine stages including `release`, and the first to declare the 210 um far-end stub |
| `runs/20260905-105354-…` | the same before the stub was declared, so its far-end penalty is that of a line the mask does not draw |
| `runs/20260905-100806-…` | before the release gate was enabled |
| `runs/20260905-095845-…`, `-100329-…` | the far-end load and the band, changed in turn |
| `runs/20260905-095425-…` | after the splitter port separation was opened; the first with the declared rules clean |
| `runs/20260905-094326-…` | the first run, 148 declared-rule violations from the splitter |
| `runs/20260905-101119-corners-000` … `-102745-corners-006` | the first corner sweep, on the drawn dimensions |
| `runs/20260905-103202-corners-000` … `-104906-corners-006` | the second, on the layer biases, which `runs/corners.md` records |
| `runs/20260905-121318-sens001` … `-124738-sens007` | the sensitivity evaluations |
| `runs/20260905-105255-golden`, `-105304-golden` | the reference adopted and re-checked, residual 0.0 um² |

**The sensitivity figures exist as a figure and not as a file.** The sweep was
run without `--out`, so no `sensitivity.json` was written and the elasticity and
contribution tables can be read only from the PNG. That is a defect in how it was
run rather than in the sweep, and re-running it with `--out` would fix it.
