# The edge couplers of the LTOI300 kit

`edge_coupler_oband` and `edge_coupler_cband`, being the two cells of the kit
that had never been evaluated at all, and the ones a chip cannot be used
without.

Conducted 2026-09-03 and 2026-09-04, and re-run on 2026-09-04 against the drawn polygons.

## What the cell is

A double inverse taper. The lower taper is drawn on the slab layer and runs the
whole 160 um, from 0.35 um at the tip toward 5.6 um. The ridge appears over the
last 80 um, from 0.25 um to the guide width, on an exponential. The surrounding
slab is cleared by the negative layer over a 20 um transverse window, so at the
facet one strip of the 120 nm film remains in oxide, and that strip carries the
mode a fibre sees.

The builder states its design target: the default values are optimised for an
O-band lensed fibre of 2.15 um mode-field diameter.

Every width quoted below is cut out of the emitted GDS by
[`tools/measure_layout.py`](../../design-chain/tools/measure_layout.py), which
is chain rule 11 applied to a vendor kit. **The first version of this study
reimplemented the kit's profile function from its parameters and the
reimplementation was wrong**, in two ways. It put the break between the linear
and the exponential branch at a quarter of the length for both cells, where the
C-band cell puts it at a half. It also interpolated the exponential branch
between the break width and 5.6 um, where the kit grows it from a fixed offset
of 0.418 um and clips it at 5.6. The consequences were large. The drawn O-band
slab is 1.500 um wide where the ridge begins and the reimplementation said
1.093. The drawn slab reaches its full 5.6 um at about 105 um and holds it for
the remaining 55, where the reimplementation was still tapering at 160.

The facet figures in the next section are unaffected, resting on the tip width
alone, and the drawn tips are 0.350 and 0.500 um as the builder declares.

## The facet, and what a fibre collects

| | O band | C band |
| --- | ---: | ---: |
| Tip strip | 0.35 um wide, 120 nm thick | 0.50 um wide, 120 nm thick |
| `n_eff` at the tip | 1.45154 | 1.45020 |
| Width through the peak | 1.300 by 1.140 um | 1.560 by 1.332 um |
| Second-moment width | 4.073 by 3.962 um | 4.227 by 4.085 um |
| Overlap with the 2.15 um fibre | 0.8027, being 0.95 dB | 0.7883, being 1.03 dB |
| One decibel of misalignment | 0.61 um lateral, 0.60 vertical | 0.62, 0.61 |
| Facet reflection into air | 3.39 % | 3.38 % |
| Facet reflection, index matched | 2.7e-6 | 4.6e-6 |

**The two definitions of mode size differ by a factor of three, and that is the
physics.** The tip index sits five thousandths above the oxide, so the mode is
barely bound and most of its power lies outside the strip. The width through the
peak measures the spike in the core and the second moment measures the mode.

That governs the coupling. Against larger fibres the overlap improves
monotonically, which a mode of one and a half micrometres could not do.

| Fibre | O band | C band |
| --- | ---: | ---: |
| 1.8 um | 1.38 dB | 1.49 dB |
| 2.15 um, the fibre the kit names | 0.95 dB | 1.03 dB |
| 2.5 um | 0.68 dB | 0.73 dB |
| 3.0 um | 0.46 dB | 0.48 dB |
| 4.0 um | 0.40 dB | 0.37 dB |

**The cell as drawn is better matched to a 3 to 4 um fibre than to the 2.15 um
one its own builder cites, by about half a decibel.** That rests on a mode
barely above cutoff, where the solve is most sensitive to the window and to the
index model, so it is worth putting to the foundry rather than acting on.

## The transition behind the facet

Twenty-two stations along the 160 um, each cut out of the emitted GDS and solved
as a full cross-section. The stations are placed where the drawn profile moves:
seven over the first 80 um, twelve between 80 and 110 where the slab widens
fastest, and three over the uniform remainder.

The effective index rises from 1.45224 at the tip to 1.74872 at the output, and
it does so smoothly at every station but one. The tip figure is 1.45154 in the
facet table above, the two differing in the fifth decimal because the facet
study solves a wider window on a finer transverse grid, the tip mode being
barely bound and reaching far into the cladding.

**The station indices are the result of this section. The propagation along them
is not, and it is withdrawn.** The reason is given under "The cascade that does
not converge" below.

| z | Slab strip | Ridge | `n_eff` |
| ---: | ---: | ---: | ---: |
| 68.6 um | 0.944 um | none | 1.51616 |
| 80.0 um | 1.500 um | 0.250 um | 1.62912 |
| 107.3 um | 5.600 um | 0.304 um | 1.65099 |
| 160.0 um | 5.600 um | 0.700 um | 1.74872 |

**The ridge begins abruptly.** At 80 um it appears at 0.25 um wide and at its
full 180 nm height. The station-to-station step across it is 0.113, against
0.040 for the largest of the twenty other steps and 0.003 for the median. That
station step is not the discontinuity alone, the stations either side of it
being 11.4 and 2.7 um away and each carrying its own taper, and the plane is
therefore measured on its own below, where the ridge is the only thing that
changes and the step is 0.080.

That plane was measured on its own by
[`scripts/ridge_plane.py`](scripts/ridge_plane.py), which solves the
cross-section either side of it and takes the overlap. The slab strip is the
same on both sides to within the nanometre the cut window resolves, so the step
is the ridge alone.

| Quantity | O band | C band |
| --- | ---: | ---: |
| Slab strip at the plane | 1.500 um | 1.504 um |
| `n_eff` before, after | 1.54912, 1.62912 | 1.50941, 1.56681 |
| Index step | +0.0800 | +0.0574 |
| Fundamental to fundamental overlap | 0.97087 | 0.97579 |
| Power transmitted | 0.94259 | 0.95216 |
| Loss at that one plane | **0.257 dB** | **0.213 dB** |
| Reflection implied by the index step | 6.3e-4 | 3.5e-4 |

The power that fails to project leaves the guided set altogether. The O-band
cross-section binds a second mode at that plane and the C-band one does not, and
in the O-band case the second mode receives nothing, being odd where the
incident field is even. So in both cells the 5.7 and 4.8 per cent are radiation
rather than conversion, and it is a property of the drawn cell rather than of
the fabrication.

Whether the rest of the taper is adiabatic is not settled here. The cascade that
would settle it does not converge.

## The budget for one facet

| Term | O band, 2.15 um fibre |
| --- | ---: |
| Mode mismatch at the facet | 0.95 dB |
| Facet reflection into air | 0.15 dB |
| The plane where the ridge begins | 0.26 dB |
| **Measured so far** | **1.36 dB** |
| The rest of the taper | not established |

The three measured terms are each a single calculation on one or two
cross-sections, and each reproduces exactly. The fourth would come from
propagating along the taper, and that calculation does not converge, so the
total is a floor rather than a budget.

Two of the three are addressable without touching the process. Index matching
removes the reflection term almost entirely, taking it to 2.7e-6. A larger
fibre removes about half a decibel of the mismatch. Starting the ridge
narrower, or introducing it over a short additional length, addresses the
0.26 dB, and that is a change to the cell rather than to the assembly.

## The C-band cell, and the same plane

The C-band coupler was measured at the same plane and through the same stations.

| | O band | C band |
| --- | ---: | ---: |
| Slab strip where the ridge begins | 1.500 um | 1.504 um |
| Index step at that plane | 0.0800 | 0.0574 |
| Loss at that plane | 0.257 dB | **0.213 dB** |

**Both cells lose most of their measured transition at the same place and for
the same reason.** They arrive at that plane with almost the same slab strip,
1.500 um against 1.504, the O-band cell reaching it on a linear-then-exponential
profile and the C-band cell on a straight line from 0.500 um. The C-band cell
loses four hundredths of a decibel less there, its index step being 0.0574
against 0.0800, because its wider ridge and longer wavelength put less index
contrast into the same 180 nm of etch.

Which of the two tapers is the more adiabatic away from that plane is not
settled. An earlier revision of this study stated the C band by a factor of
thirteen and a later one stated the O band by a factor of three, and both rested
on the cascade withdrawn below.

The budget for the C-band facet, with the same 2.15 um fibre:

| Term | C band |
| --- | ---: |
| Mode mismatch at the facet | 1.03 dB |
| Facet reflection into air | 0.15 dB |
| The plane where the ridge begins | 0.21 dB |
| **Measured so far** | **1.39 dB** |
| The rest of the taper | not established |

## The cascade that does not converge

The transition was to be propagated by the local-mode path, projecting the modes
of each station onto the next and neglecting reflection, which is the
well-conditioned route for a structure designed to vary slowly. Chain rule 15
requires the convergence guard to pass before the result is read. It does not
pass. The station count was multiplied by two and by three, every other input
held:

| O band | 22 stations | 44 | 66 |
| --- | ---: | ---: | ---: |
| Transmission into the fundamental | 0.81822 | 0.83894 | 0.95032 |
| Power retained in the guided set | 0.82129 | 0.85233 | **1.50316** |
| Conversion into higher-order modes | 3.07e-3 | 1.34e-2 | 5.53e-1 |
| Staircase deficit | 0.1787 | 0.1477 | 0.0000 |

| C band | 22 stations | 44 |
| --- | ---: | ---: |
| Transmission into the fundamental | 0.83198 | 0.89888 |
| Power retained in the guided set | 0.83709 | 0.90103 |
| Conversion into higher-order modes | 5.11e-3 | 2.15e-3 |
| Staircase deficit | 0.1629 | 0.0990 |

**At sixty-six stations the guided power is 1.503, which is above unity and
therefore not a physical answer.** Nothing about the cell changed between the
three columns. The conversion channel moves by a factor of one hundred and
eighty in the O band across the refinement and by a factor of two in the other
direction in the C band, so it is not measuring the taper.

The cause is the basis. The cascade carries three modes, and the cross-section
binds one guided mode over the first 80 um and two after the ridge appears, with
the remainder sitting at the cladding index where they are radiation modes
discretised by the window rather than modes of the structure. Projecting between
two stations whose radiation sets differ is not a unitary operation, and the
deficit that leaves is redistributed rather than lost. Adding stations adds
junctions and compounds it.

**Every propagated figure this study reported before 2026-09-04 is therefore
withdrawn**, being 0.77792 and 0.78288 in the first revision and 0.81964 and
0.83965 in the second. They were single draws from an unconverged calculation
and two of them were also drawn from a solver started at random.

What replaces them is the plane measurement above, which is one junction rather
than twenty-one, is bounded by unity by construction, and reproduces to the last
digit. It measures the term that dominates and it measures nothing else. A
converged figure for the remainder wants either a basis that carries the
radiation continuum properly or a three-dimensional propagation, and neither was
run.

## What is not covered

Reflection along the taper is neglected, which is the assumption an inverse
taper is built to satisfy. At the one plane where that assumption fails, the
index step implies a reflected power of 6.3e-4 in the O band and 3.5e-4 in the
C band, which is 30 dB below the transmission loss at the same plane.

The adiabatic loss of the taper away from that plane is unmeasured, for the
reason set out above.

Both cells have had their facet measured and the one plane that dominates their
transition measured, and both are solved from the polygons the kit writes. The
adiabatic remainder of the transition is measured for neither.

What a cut cannot see is the third dimension. Every cross-section here is taken
as uniform along z, so a taper is a staircase of them, and the plane measurement
treats the ridge as appearing across a plane of zero thickness where the drawn
polygon has a vertex.
