# The MMI splitters of the LTOI300 kit, and the models shipped with them

The four multimode splitters of the Luxtelligence LTOI300 kit, being
`mmi1x2_oband`, `mmi1x2_cband`, `mmi2x2_oband` and `mmi2x2_cband` in
[`design-chain/pdk/lxt_pdk_gf/ltoi300/cells.py`](../../design-chain/pdk/lxt_pdk_gf/ltoi300/cells.py),
set against a second instrument. The geometry of each is read from its builder
and nothing here is chosen.

Conducted 2026-09-03.

## The question

A kit states the behaviour of its cells so that a circuit may be assembled
without solving each one. Those statements govern every design built on them and
nothing in a kit checks them. Two questions follow: whether the shipped models
are physically admissible, and whether they agree with an independent solve of
the same drawn geometry.

## The models, tested against physics

`design-chain/tools/check_pdk_models.py` reads the compact models of every
installed kit and tests three properties that hold whatever the device is: the
power leaving may not exceed the power entering, a magnitude is not negative,
and a reciprocal structure satisfies S_ij = S_ji. It prints verdicts and copies
no vendor data, so a kit under a licence forbidding redistribution may be tested.

1101 models across three kits, 205 findings. Two of the four splitters here are
among them.

| Cell | Finding |
| --- | --- |
| `mmi1x2_cband` | Power out reaches 1.1249 of power in, above unity at every wavelength sampled from 1490 to 1610 nm. Three reflection magnitudes go negative, the worst at -0.3149 |
| `mmi2x2_cband` | Power out reaches 1.0255, above unity at the top of the band, with one negative magnitude |
| `mmi1x2_oband` | Admissible throughout, 0.986 to 0.999 |
| `mmi2x2_oband` | Admissible throughout, peaking at 0.995 near 1320 nm and falling to 0.81 at 1250 |

A circuit assembled on either C-band model draws energy from nowhere. The cause
is a polynomial fitted to a magnitude with no constraint holding it below one or
above zero, and it is a defect of the fit rather than of the device: the chain
finds the C-band 1x2 well behaved when it solves it.

## The cells, solved by the chain

The FDTD stage gained an `mmi` structure for this study, reading the splitter
geometry the layout already declares. Each cell is solved in the plane by the
effective-index reduction, with a normalisation run of the input guide alone,
and each carries a convergence guard at half the resolution.

| Cell | Section | Resolution | Transmission | Excess loss | Guard shift | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `mmi1x2_oband` | 15.8 um | 40 | 0.98376 | 0.0711 dB | 0.65 % | converged |
| `mmi1x2_cband` | 13.5 um | 40 | 0.98536 | 0.0641 dB | 0.29 % | converged |
| `mmi2x2_oband` | 97.5 um | 50 | 0.83544 | 0.7808 dB | 6.51 % | **refused** |
| `mmi2x2_cband` | 67.5 um | 50 | 0.65465 | 1.8399 dB | 5.38 % | **refused** |

The reflection into the input is below 3e-5 in every case, and the two ports of
each 1x2 are identical to eleven decimal places, the drawn geometry being
symmetric by construction rather than measured to be so.

**The two 1x2 cells converge, and convergence is not correctness.** The chain
puts their excess loss at 0.071 and 0.064 dB against the O-band model's
0.006 dB. The section below establishes that most of that difference is the
reduction placing the self-imaging length elsewhere, so the disagreement is the
model's and not the kit's.

**The two 2x2 cells refuse their guard at resolution 50**, so nothing in their
row is a measurement of a device. The section below explains why the guard could
not be satisfied at any affordable mesh.

## Why every cell disagreed, and it is the reduction rather than the device

The eigenmode expansion at
[`mmi_eme.py`](../../design-chain/src/picchain/mmi_eme.py) was built for this
question. It matches sections by overlap and propagates each in closed form, so
a section of ninety-seven micrometres carries no more phase error than one of
one, and the length ceases to be a source of error. It reproduces a uniform
guide exactly, transmitting 1.0 with a reflection of 5e-32.

It agrees with the time-domain solve on the two 2x2 cells. On a completed basis
of 32 lateral modes it returns 0.8052 for the O-band cell against the 0.8059 the
time-domain mesh extrapolates, and 0.6482 for the C-band cell against 0.6547
measured at resolution 50. Two instruments, one carrying a propagation mesh and
one carrying none, arriving within a per cent of each other.

That agreement is what makes the next measurement conclusive. Sweeping the
length of the multimode section costs seconds in this instrument, and every cell
tells the same story.

| Cell | Length drawn | Best length in the reduction | Transmission as drawn | Transmission at that best |
| --- | ---: | ---: | ---: | ---: |
| `mmi1x2_oband` | 15.8 um | 17.0 um, +7.6 % | 0.9767 | 0.9990 |
| `mmi2x2_cband` | 67.5 um | 74.0 um, +9.6 % | 0.6558 | 0.9919 |
| `mmi2x2_oband` | 97.5 um | 104.0 um, +6.7 % | 0.8070 | 0.9950 |

**Every cell reaches better than 99 per cent at a section between seven and ten
per cent longer than the kit draws, and each kit length is off that optimum by
the same fraction.** A systematic offset of one sign across three cells of two
port counts and two bands is a property of the model and not of three devices.

The cause is the effective-index reduction. What a multimode section does is set
by the spacing of the propagation constants of its guided modes, the
self-imaging length being fixed by that spacing. Collapsing the vertical
dimension into two indices changes the spacing, so the reduced structure images
at a different length. The kit chose its lengths where the spacing is right, and
in the reduction they are the wrong length.

**The apparent losses were therefore artefacts, and their size follows the
length.** The penalty for sitting a fixed fraction off the optimum grows with
the sharpness of the optimum, and the sharpness grows with length. The 1x2 cell
at 15.8 um sits 1.2 um off a broad peak and pays 0.10 dB. The 2x2 cell at
97.5 um sits 6.5 um off a sharp one and pays 0.93 dB. That accounts for the
whole disagreement with the kit, and it explains the time-domain behaviour as
well: a device on a steep slope moves under any change in the numerical index,
which is why the mesh would not converge.

**No excess loss of any of these four cells is established by this study.** The
figures both instruments report describe a structure of the wrong length. The
models shipped with the kit, stating 0.006 dB for the O-band 1x2 and 0.05 dB for
the O-band 2x2, are consistent with a device designed and evaluated where the
mode spacing is right.

One correction is recorded rather than hidden. The mode monitors of the
time-domain runner were first set to the port separation, so each plane reached
the neighbouring guide centre line and the eigenmode decomposition returned a
supermode as band one. The monitor is now bounded to the smaller of eight tenths
of the separation and four guide widths. That moved the cells by 0.07 to 0.37
per cent, so it was a real defect and the cause of nothing above.

## The two-junction cascade, and the question closed

A multimode splitter has exactly two planes where its cross-section changes
abruptly, being the faces of the multimode section. The access tapers vary
slowly by construction, so their junctions carry no reflection worth matching,
and treating them as matched junctions is what destroyed the conditioning: each
adds an over-determined continuity condition on a truncated basis, and there
are a dozen of them.

The cascade was therefore reduced to three sections and two junctions: the port
guides at the width the taper delivers, the multimode section, and the port
guides again. Every section is a full cross-section, being a trapezoidal ridge
on its slab in oxide at the declared 70 degree wall.

**The instrument now returns a proper self-image.** On the O-band 2x2 cell the
peak reaches 0.9988 of the input with an imbalance of 0.0006 dB, which is what
a balanced two-by-two splitter is supposed to do and what neither earlier
instrument could show.

| Instrument | Peak transmission | Where it peaks | Offset from the drawn 97.5 um |
| --- | ---: | ---: | ---: |
| Planar reduction, time domain | not converged | — | — |
| Planar reduction, eigenmode | 0.9950 | 104.0 um | +6.7 % |
| Cross-section, fourteen junctions | 1.0455, unphysical | 16.98 um on the 1x2 | +7.5 % |
| **Cross-section, two junctions** | **0.9988** | **101.0 um** | **+3.6 %** |
| Beat-length ratio, predicted | — | 101.1 um | +3.7 % |

**Two independent routes now agree to a tenth of a per cent.** The beat length
of the section in the full cross-section is 2.9 per cent shorter than in the
reduction, which predicted an optimum at 101.1 um, and the cascade finds 101.0.
The reduction's +6.7 per cent was very nearly twice the true offset, and that
error is now explained rather than merely observed.

### What the drawn length costs, and what the stack does to it

At 97.5 um the cell transmits 0.9000, being 0.458 dB of excess loss, against
0.9988 at 101.0. The optimum is sharp on a section this long, so 3.6 per cent
of length costs nearly half a decibel.

The sidewall angle moves the optimum, because it sets the effective width and
the imaging length follows the square of it.

| Sidewall | Peak at | Offset | Transmission at the drawn 97.5 um |
| --- | ---: | ---: | ---: |
| 70 degrees, as the layer stack declares | 101.07 um | +3.7 % | 0.8999, being 0.458 dB |
| 80 degrees | 100.27 um | +2.8 % | 0.9509, being 0.219 dB |
| 90 degrees, a vertical wall | 99.47 um | +2.0 % | 0.9664, being 0.148 dB |

So a stack detail of twenty degrees in the wall moves the optimum by 1.7 per
cent and changes the cost of the drawn length by a factor of three. Two per cent
remains between a vertical wall and the length the kit draws, and the candidates
for it are the index model, the etch depth and the film thickness, each of which
enters the effective width, and the possibility that the kit optimised for
bandwidth or balance rather than for peak transmission.

**The kit's own figure of 0.05 dB corresponds to a stack whose imaging length is
about two per cent shorter than the best estimate here.** That is a small
difference in the cross-section and it is not evidence that either party is
wrong. What is now established is the shape of the dependence and its
sensitivity, and a designer placing this cell should know that half a decibel
sits within four per cent of its length.

### All four cells on one instrument

The same cascade, sixteen modes in the multimode section and eight in the ports,
on every cell.

| Cell | Drawn | Transmission as drawn | Excess loss | Imbalance | Peak at | Peak | Offset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mmi1x2_oband` | 15.8 um | 0.9912 | 0.038 dB | 0.000 dB | 16.90 um | 1.0094 | +7.0 % |
| `mmi1x2_cband` | 13.5 um | 1.0103 | — | 0.001 dB | 14.48 um | 1.0213 | +7.3 % |
| `mmi2x2_oband` | 97.5 um | 0.8999 | 0.458 dB | 0.039 dB | 101.59 um | 0.9992 | +4.2 % |
| `mmi2x2_cband` | 67.5 um | 0.7901 | 1.023 dB | 0.035 dB | 71.96 um | 0.9975 | +6.6 % |

**The two topologies behave differently and only one set of figures is
quotable.** Both 2x2 cells peak below unity, at 0.9992 and 0.9975, so their
conditioning residue is a part in a thousand and their losses stand. Both 1x2
cells exceed unity, by 0.9 and 2.1 per cent, and the C-band one exceeds it at
the drawn length, so their absolute transmission carries a residue of that size
and no excess loss is quoted for the C-band cell.

**The 1x2 optimum is not well determined and it does not need to be.** Its peak
is broad: the O-band cell moves from 0.9912 to 1.0094 across seven per cent of
its length, which is a variation of 1.8 per cent against a residue of 0.9. An
argmax taken on that is worth little. What the same numbers do establish is that
the cell as drawn costs at most 0.04 dB, which is the question a designer asks.

The 2x2 optimum is well determined for the opposite reason. Its peak is sharp,
the O-band cell moving from 0.90 to 0.999 across four per cent, so a residue of
a part in a thousand does not move it.

### The beat-length shortcut, and where it applies

Scaling the planar optimum by the ratio of the beat lengths predicts 101.06 um
for the O-band 2x2 against 101.59 measured, agreeing to half a per cent. On the
1x2 it predicts 16.44 um against 16.90, and it fails.

The natural explanation, that a one-into-two splitter images on the spacing of
the even modes rather than of the first two, was tested and does not hold: the
ratio is 0.9671 on the spacing between the first and third modes against 0.9660
between the first and second, so both scale alike. The failure belongs to the
broad peak rather than to the physics, and the shortcut is therefore reliable
where the optimum is sharp and uninformative where it is not.

### What the kit says about the same four cells

| Cell | The kit's own model | This cascade at the drawn length |
| --- | ---: | ---: |
| `mmi1x2_oband` | 0.006 dB | 0.038 dB |
| `mmi1x2_cband` | unphysical, above unity across the band | above unity here as well |
| `mmi2x2_oband` | 0.05 dB | 0.458 dB |
| `mmi2x2_cband` | 0.45 dB at 1550 nm | 1.023 dB |

**The kit's own model agrees that the C-band 2x2 is the lossy one.** It states
0.45 dB where this cascade finds 1.02, and an excess loss of that order on an
MMI is the signature of a section away from its imaging length. The two
instruments differ by a factor of two on the amount and agree on the character.

On the O-band 2x2 they disagree in character as well as amount, the kit stating
0.05 dB where the cascade finds 0.458. Two per cent of imaging length separates
those two statements, which is a small difference in a cross-section.

### The limit that remains

The peak reaches 1.0006 at a vertical wall, being six parts in ten thousand
above unity, which is the residue of the same conditioning and is the bound on
every figure above. It stood at 4.5 per cent before the cascade was reduced.

## What remains

The O-band 2x2 cell is settled by the section above. The other three want the
same treatment through the two-junction cascade, which is now a run of a few
minutes each rather than a build.

What the earlier text said of all four remains true of the planar reduction. A multimode section is governed by the spacing of its modal
propagation constants, and no planar reduction reproduces that spacing closely
enough to place a self-imaging length to better than seven per cent. Both
instruments built here share that reduction, which is why they agree with each
other and neither agrees with the kit.

Three dimensions is reachable two ways, and one of them was found on
2026-09-05 not to exist. `meep_mmi.py` builds every shape with an infinite
extent in the third axis, so the splitter has no three-dimensional runner, and
`fdtd.dimensions: 3` was recorded in the payload while the plane reduction was
returned. The stage now refuses that setting for this structure. The defect and
the withdrawn run are described in
[`REPORT_ACCESS_TAPER.md`](REPORT_ACCESS_TAPER.md).

The time-domain path therefore needs a three-dimensional splitter runner
written, and would be an overnight job for a section of this length once it
exists. The eigenmode expansion would need the modes of the full
two-dimensional cross-section rather than of a lateral profile, which the
chain's own mode solver already computes, and it would then cost seconds rather
than a night.

The one structure whose runner does build a layer stack is the taper, and the
access taper of this cell has been solved in both dimensionalities. The study is
[`REPORT_ACCESS_TAPER.md`](REPORT_ACCESS_TAPER.md). It measures the plane
reduction giving the smaller loss for that taper, 0.0228 dB against 0.0304, and
it does not establish what the difference consists of: the vertical radiation
channel, the lateral channel and the accuracy of the effective-index reduction
all contribute and none was separated. It measures a taper of 5 um rather than
the 25 um this cell draws, and no length was swept, so the figure does not
transfer to the cell. Read the report's own limitations before quoting it.

Four defects were found and fixed in reaching it, one of which moved the plane
figure by a factor of two and had been present in three of the four FDTD runners
since they were written. Every splitter figure on this page predates that fix.
Re-solving the shortened splitter after it moved the transmission in the seventh
decimal place, the splitter's leads having carried only a mild form of the
defect, so the figures above stand.

The second is the better investment, and the length sweep above is the reason.
Once the beat length is right, the questions a designer asks are what the
optimum length is and how sharp it is, and both want an instrument cheap enough
to sweep.
