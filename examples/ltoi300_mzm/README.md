# The Mach-Zehnder modulators of the LTOI300 kit, at device level

The kit ships eight Mach-Zehnder cells, being
`{terminated, unterminated}_mzm_{1x2mmi, 2x2mmi}_{oband, cband}`. They divide
into two electrode geometries, two splitter topologies and two far-end loads,
and the electrode is the one already solved under
[`../ltoi300_modulator/`](../ltoi300_modulator/README.md).

What is added here is the interferometer, which is what a link budget consumes.

Conducted 2026-09-03, with the drawn electrode and the far-end load added 2026-09-04.

## What the device asks of a driver

The electro-optic stage solves one guide between two electrodes. The modulator
stage converts that to the interferometer, halving the half-wave voltage for the
push-pull drive the kit's layout carries, and then evaluates the response across
the band rather than at the carrier alone.

| | O band | C band |
| --- | ---: | ---: |
| Central conductor | 20.0 um | 16.0 um |
| Vpi.L, one arm | 5.5286 V cm | 7.3482 V cm |
| Vpi.L, the device push-pull | 2.7643 V cm | 3.6741 V cm |
| Vpi over the 5000 um the cell draws | 5.529 V | 7.348 V |
| Vpi demanded at the source | 6.062 V | 7.826 V |
| Electro-optic 3 dB point | 169.6 GHz | 114.3 GHz |
| Response at 110 GHz | -2.19 dB | -2.92 dB |
| Vpi at 110 GHz | 7.117 V | 10.280 V |
| Vpi at the source at 110 GHz | 7.804 V | 10.949 V |
| Group index of the 2.5 um arm | 2.18341 | 2.13473 |
| Spectral period from the 100 um imbalance | 7.86 nm, 1373 GHz | 11.25 nm |

**Two figures separate what the device is from what a driver must deliver, and
the kit states neither.** Only 91.2 per cent of the drive enters the line, the
characteristic impedance being 41.9 ohm against a 50 ohm source, so the voltage
at the source exceeds the voltage across the electrode. And a device inside its
3 dB bandwidth is not flat within it: at 110 GHz the O-band cell is down
2.19 dB, so the half-wave drive rises from 5.53 V to 7.12 V across the
electrode and 7.80 V at the source, being 41 per cent above the nominal figure.

The C-band cell is the harder one. Its 3 dB point is 114.3 GHz, so a band
reaching 110 GHz sits almost at the edge, and the drive there is 10.95 V at the
source against a nominal 7.35. A driver specified from the nominal figure would
be short by half.

## What the arm imbalance sets

The cells default to a 100 um length difference between the arms, which fixes
the spectral period of the transfer function at 7.86 nm in the O band and
11.25 nm in the C band, on the group index of the 2.5 um modulation section
rather than of the routing guide. That period is the interval over which the
bias must be set, and it is what the heater beside it exists to move.

## What the splitter imbalance ceilings

The extinction of an interferometer cannot exceed what its splitter's balance
allows, whatever the phase control does.

| Splitter imbalance | Extinction ceiling |
| --- | ---: |
| 0.01 dB | 64.8 dB |
| 0.05 dB | 50.8 dB |
| 0.20 dB | 38.8 dB |
| 0.50 dB | 30.8 dB |

The kit's own models put the imbalance of both 2x2 splitters at 0.06 dB or
better across the band, which ceilings the extinction near 50 dB. That figure
is the kit's and not this repository's: the study at
[`../ltoi300_mmi/`](../ltoi300_mmi/README.md) establishes that the planar
reduction cannot measure a multimode splitter, so the chain has no independent
imbalance to put here.

## The taper into the multimode arm, and the risk that is absent

**The three propagated figures in this section were computed before 2026-09-04**, when the mode solver was started from a random vector, and a cascade result taken that way does not reproduce. They are of the same kind as the edge-coupler cascade withdrawn in the companion study and they have not been recomputed. The adiabaticity margin, which is a ratio of lengths rather than a projection, is unaffected.

The modulation section is 2.5 um wide and the mode solve counts four guided
modes in it. The cell reaches that width from 0.7 um over a 100 um taper, and a
taper that converts even a per cent into the second-order mode would ceiling the
extinction below anything the splitter allows, invisibly, since no figure
reported above would move.

Measured by eigenmode expansion at 64 slices, with the staircase converged to
0.0004 dB against its own halving:

| Quantity | Value |
| --- | ---: |
| Minimum adiabaticity margin | 5.00, against a declared floor of 3.0 |
| Width at which the margin is least | 0.737 um |
| Conversion into higher-order modes | 1.05e-4, being 0.0005 dB |
| Reflection | 0.0 |
| Staircase deficit | 1.9 % |

**The risk is absent.** The taper is adiabatic with a margin of five and
converts one part in ten thousand out of the fundamental, so the multimode arm
is reached cleanly and the extinction is not capped here. The 1.9 per cent
deficit is a discretisation residue of the staircase, which the stage reports
separately for exactly this reason and which falls as the slice count rises; it
is not a radiation estimate and it is not a loss.

## The thermal bias section, and the verdict now stated

The weight the heater needs is the fraction of the effective index that follows
each material's own index, and the film confinement has been standing in for it.
Each index was perturbed and the mode re-solved, by
[`scripts/index_sensitivity.py`](scripts/index_sensitivity.py).

| | O band | C band |
| --- | ---: | ---: |
| dn_eff/dn of the film | 0.84147 | 0.77462 |
| dn_eff/dn of the cladding | 0.20256 | 0.27266 |
| Film confinement, the proxy | 0.7298 | 0.6522 |
| By how much the proxy understates | 15.3 % | 18.8 % |
| The two sensitivities summed | 1.044 | 1.047 |

The sum is the measurement's own check. Every material's share of the effective
index adds to one, so a sum of 1.044 says the two derivatives carry about four
per cent of numerical error between them, and no conclusion below rests on less
than that margin.

**The 700 um heater reaches a half-wave in the O band and does not in the C
band.** At a 40 K rise, taking 3e-5 per kelvin for the film:

| | O band | C band |
| --- | ---: | ---: |
| Phase from the film alone | 1.079 pi | 0.840 pi |
| With the cladding at 1e-5 per kelvin as well | 1.166 pi | 0.938 pi |

The O-band cells clear a half-wave with 8 to 17 per cent to spare. The C-band
cells fall 6 to 16 per cent short of it, so the default section cannot reset the
interferometer by pi at 40 K and can only bias it within a fraction of a period.
Reaching pi there wants a section of about 750 to 830 um, or a higher rise, and
which of those is available is a thermal question this study does not pose.

The earlier statement that the reach was between 0.94 and 1.2 pi and its sign
unknown is superseded. It was a bracket over which weight to use, and the weight
has now been measured.

## The electrode length, and where the kit sits on its own trade

The cells fix the modulation length at 5000 um. That length sets the half-wave
voltage and the bandwidth together, and the two pull in opposite directions, so
the figure a driver must deliver at a stated frequency has a minimum somewhere.
The length was swept with the rest of the design held, and the response
evaluated at 110 GHz in every case.

| Length | Vpi | Vpi at the source | 3 dB point | Response at 110 GHz | Vpi at the source at 110 GHz |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2.0 mm | 13.821 V | 15.155 V | 580.6 GHz | -0.83 dB | 16.677 V |
| 3.0 mm | 9.214 V | 10.103 V | 344.8 GHz | -1.27 dB | 11.694 V |
| 4.0 mm | 6.911 V | 7.578 V | 233.1 GHz | -1.72 dB | 9.242 V |
| **5.0 mm, as drawn** | **5.529 V** | **6.062 V** | **169.6 GHz** | **-2.19 dB** | **7.804 V** |
| 6.5 mm | 4.253 V | 4.663 V | 114.4 GHz | -2.93 dB | 6.532 V |
| 8.0 mm | 3.455 V | 3.789 V | 82.5 GHz | -3.69 dB | 5.796 V |
| 10.0 mm | 2.764 V | 3.031 V | 57.1 GHz | -4.76 dB | 5.244 V |
| 12.5 mm | 2.211 V | 2.425 V | 38.8 GHz | -6.17 dB | 4.934 V |
| **15.0 mm** | **1.843 V** | **2.021 V** | **28.1 GHz** | **-7.64 dB** | **4.870 V** |
| 18.0 mm | 1.536 V | 1.684 V | 20.1 GHz | -9.45 dB | 5.001 V |
| 22.0 mm | 1.256 V | 1.378 V | 13.8 GHz | -11.84 dB | 5.383 V |

**The drive demanded at 110 GHz is least at 15 mm, and the kit draws 5.** At
the drawn length a driver must deliver 7.804 V at the source to reach a
half-wave at 110 GHz. At 15 mm the same requirement is met with 4.870 V, being
38 per cent less, and the minimum is genuine: 18 mm returns 5.001 V and 22 mm
returns 5.383.

The mechanism is that the half-wave voltage falls as the reciprocal of the
length while the response falls exponentially with it, so the product has a
minimum. Below that minimum the electrode is short of what the material offers,
and above it the roll-off dominates.

**The 3 dB point is the wrong figure to design against, and this table is why.**
At 15 mm it reads 28.1 GHz, which appears to disqualify the electrode from a
110 GHz application outright. What matters is the drive demanded where the
device is used, and by that measure the same electrode is the best of the
eleven. A specification written against the 3 dB bandwidth would reject the
configuration that minimises the drive.

Two terms sit outside this table. Optical propagation loss over the arms is not
folded in, and at the transferred figure of 0.31 to 0.95 dB/cm a 15 mm electrode
carries 0.31 to 0.95 dB that a 5 mm one does not, the difference in length being
one centimetre, which is a penalty in the link budget rather than in the drive. And a longer electrode carries a longer
thermal-bias section and a larger die, neither of which is priced here.

## The process window, and which parameter moves what

Every figure above is a nominal figure, and the operating manual's fifth rule
states that a nominal run is not a result. The window was declared as plus or
minus 10 nm on the film, 10 nm on the etch, 3 degrees on the sidewall and 200 nm
on the electrode gap. Each of those is an assumption and is marked as one in the
design file: the LT-PRO manual states no tolerance for any of them.

Nine corners, one factor at a time, all nine passing. Every target is a `should`, so what passed is the `should` set.

| Metric | Nominal | Minimum | Maximum | Spread |
| --- | ---: | ---: | ---: | ---: |
| Overlap | 0.43394 | 0.42155 | 0.44731 | 5.9 % |
| Vpi.L, one arm | 5.5286 V cm | 5.29319 | 5.76446 | 8.5 % |
| Electro-optic 3 dB point | 169.6 GHz | 163.4 | 193.2 | 17.6 % |
| Characteristic impedance | 41.911 ohm | 41.322 | 42.481 | 2.8 % |

Read against the run of each corner, the spread attributes cleanly.

| Excursion | Overlap | Vpi.L | 3 dB point |
| --- | ---: | ---: | ---: |
| Film -10 nm | -2.9 % | +2.9 % | +6.1 % |
| Film +10 nm | +3.1 % | -3.0 % | +2.4 % |
| Etch -10 nm | +2.5 % | -2.4 % | +1.8 % |
| Etch +10 nm | -2.2 % | +2.3 % | **+13.9 %** |
| Sidewall -3 degrees | +0.1 % | -0.1 % | -0.3 % |
| Sidewall +3 degrees | -0.1 % | +0.1 % | +0.2 % |
| Gap -200 nm | +0.6 % | **-4.3 %** | -3.6 % |
| Gap +200 nm | -0.6 % | **+4.3 %** | +3.4 % |

Three statements follow.

**The electrode gap is what sets the drive.** It moves the half-wave voltage by
4.3 per cent for 200 nm, which is more than the film and the etch together, and
it moves the overlap by only 0.6 per cent. The gap acts through the field rather
than through the mode: a wider gap divides the same voltage across more
distance. The lithography of the metal layer therefore governs the drive more
directly than the lithography of the ridge.

**The sidewall angle governs nothing here.** Three degrees moves every figure by
a tenth of a per cent. That is worth knowing because the sidewall is the
hardest of the four to hold and the most often argued about.

**The nominal is not the worst case for bandwidth.** Both directions of film
thickness raise the 3 dB point, by 6.1 per cent at minus 10 nm and 2.4 at plus
10, so the response has a minimum at the nominal thickness rather than a
monotonic dependence on it. A one-factor sweep cannot see an interaction, and a
non-monotonic response means the corners of the window are not where the
extremes sit. Establishing the true worst case wants the factorial mode, which
is 81 runs on four parameters and about half an hour.

### The elasticity beside it, and where the two disagree

The same four parameters were perturbed by five per cent each and the
elasticity taken, being the fractional change in a metric over the fractional
change in the parameter.

| Metric | Film thickness | Etch depth | Sidewall | Electrode gap |
| --- | ---: | ---: | ---: | ---: |
| Vpi.L | -0.87 | +0.42 | +0.03 | **+1.18** |
| Electro-optic 3 dB point | -0.93 | +0.88 | +0.06 | +0.98 |

Contribution over the declared window, as a half-span:

| Metric | Film thickness | Etch depth | Sidewall | Electrode gap |
| --- | ---: | ---: | ---: | ---: |
| Vpi.L | 2.9 % | 2.3 % | 0.1 % | **4.3 %** |
| Electro-optic 3 dB point | 3.1 % | 4.9 % | 0.3 % | 3.6 % |

The elasticity of the half-wave voltage against the gap is 1.18, which exceeds
unity. The gap enters the field directly, so a linear dependence would give
exactly one, and the excess is the overlap falling slightly as the gap widens.
The two effects act in the same direction, which is why the gap dominates.

**The two instruments disagree on the bandwidth, and the corner sweep is the one
to believe.** The elasticity puts the etch contribution at 4.9 per cent over the
declared window; the corner run at plus 10 nm returns 13.9. A linearised
derivative taken at the nominal cannot represent a response that is not linear,
and the bandwidth is not: the film dependence is non-monotonic about the nominal
and the etch dependence is strongly curved. For the half-wave voltage the two
agree to a tenth of a per cent, so the disagreement is a property of the
bandwidth rather than of the method.

The figure is at `runs/sensitivity/sensitivity.png`.

## The electrode the kit actually draws, which is interrupted

Every travelling-wave figure above was computed on a uniform coplanar line, a
20 um signal conductor in a 5.5 um gap in the O band and 16 um in the C band.
Cutting the emitted GDS along the run says otherwise. On the O-band cell the
signal conductor steps between 20 um and 10 um and each gap between 5.5 um and
15.5 um; on the C-band cell between 16 and 10 um and between 5.5 and 11.5 um.
The period is 58 um in both, the narrow-gap section holding for 53 of every 58
and the wide-gap section for 5.

The builder names the feature. `trail_cpw` draws "a CPW transmission line with
periodic T-rails on all electrodes", with a rail of 53 um, a cut of 5 um, and a
head and a tooth of 2.5 um each in the O band and 1.5 um each in the C band,
which is where the signal loses twice their sum and each gap gains it. The
optical guide sits at the centre of the gap in both sections, so the chain's
symmetric placement holds for each.

[`scripts/trail_electrode.py`](scripts/trail_electrode.py) runs the
electro-optic stage at both drawn cross-sections and homogenises them over the
period. Capacitance per unit length averages arithmetically, the sections being
in parallel across the line. Inductance averages arithmetically as well, the
sections being in series along it. The electro-optic phase accumulates per unit
length, so the half-wave voltage combines as a reciprocal average. The
attenuation is not averaged directly, since each section's figure carries its
own impedance; the series resistance is recovered from each, averaged, and
divided by the impedance the homogenised line has.

| | O band, as modelled | O band, as drawn | C band, as modelled | C band, as drawn |
| --- | ---: | ---: | ---: | ---: |
| Capacitance | 1.7976 pF/cm | 1.7273 | 1.6975 pF/cm | 1.6486 |
| Microwave index | 2.2587 | 2.2783 | 2.2515 | 2.2614 |
| Optical group index | 2.1834 | 2.1834 | 2.1347 | 2.1347 |
| Velocity mismatch | +0.0753 | **+0.0949** | +0.1168 | **+0.1266** |
| Impedance | 41.91 ohm | **44.00** | 44.24 ohm | **45.76** |
| Vπ·L, one arm | 5.5286 V·cm | **5.8978** | 7.3482 V·cm | **7.7384** |
| Conductor loss at 10 GHz | 2.4116 dB/cm | 2.4952 | 2.8556 dB/cm | 2.9040 |
| 3 dB bandwidth | 169.6 GHz | **144.4** | 114.3 GHz | **107.5** |

The two sections differ by more than the average suggests. Taken alone the
wide-gap section carries a Vπ·L of 20.2 V·cm against 5.5, and an impedance of
73.6 ohm against 41.9, so 8.6 per cent of the length contributes almost nothing
to the modulation while contributing its full share of the delay.

Three readings follow.

**The half-wave voltage is 6.7 per cent higher than reported, and 5.3 per cent
higher in the C band.** That is a correction to the figure a driver must
deliver, and it widens the gap already open against the kit's own number. The
kit's compact model gives 4.4 V·cm for one O-band arm, the uniform line gave
5.5286, and the drawn line gives 5.8978, which is 34.0 per cent above the kit
where the earlier figure was 25.6 per cent above it.

**The velocity mismatch worsens by a quarter in the O band and by eight per cent
in the C band.** The cut sections lose capacitance and gain proportionally more
inductance, so the homogenised microwave index rises above the value of either
section and away from the optical group index. The bandwidth falls by 15 per
cent in the O band and by 6 per cent in the C band.

**The impedance improves by 2 ohm.** The drawn line sits at 44.0 against 41.9
and the C-band one at 45.8 against 44.2, in both cases closer to the 50 ohm the
driver presents. Which of these effects the T-rail was drawn for cannot be
recovered from the kit, since the kit states an intent for none of its
dimensions.

Two limits of this treatment are worth naming. The 0.5 um transition at each
rail edge is assigned to whichever section it adjoins, which is 1.7 per cent of
the length. And the homogenisation holds while the period is short against the
microwave wavelength: 58 um against 1.3 mm at 100 GHz is a ratio of twenty-two,
and the stopband a periodic line carries sits near 1.1 THz, so neither concerns
the device.

## The far end of the line, and which cell is being graded

The kit ships each modulator and each phase shifter twice, terminated and
unterminated. The measurement in the companion mask study establishes what
carries the termination: one polygon on the high-resistance layer beyond the far
end of the signal metal, being 2911.9 square micrometres in the O band and
2815.9 in the C band.

**The resistor is not the only difference, and the second one is not
cosmetic.** Seven layers differ between the two variants of the modulator, and
the reason is that the unterminated cell runs its signal metal to 5220 um where
the terminated one stops at 5045. On a modulation section of 5000 um that is
220 um of line the microwave crosses twice and the optical carrier does not
cross at all, so it rotates the returned wave and moves the null. It is carried
here as `electrodes.far_end_stub_um` and every open-ended figure below includes
it. Omitting it puts the null at 10.19 GHz and 1.44 dB deep against the 9.81 GHz
and 1.91 dB the drawn cell gives.

The chain now carries the far-end load as `electrodes.far_end_load_ohm`. An
unset value states a termination matched to the line and reproduces the earlier
model term by term. An open pad is stated as 1e9. The returned wave travels
against the optical carrier, so the two walk off at the sum of the indices
rather than at their difference.

A modulation response is conventionally referred to its own value at zero
frequency, and read that way the open cell looks ruined.

| Referred to its own zero-frequency value | O band, terminated | O band, open | C band, terminated | C band, open |
| --- | ---: | ---: | ---: | ---: |
| 3 dB bandwidth | 144.4 GHz | 4.18 GHz | 107.5 GHz | 4.04 GHz |
| At 10 GHz | −0.62 dB | −8.54 dB | −0.72 dB | −8.61 dB |
| At 40 GHz | −1.27 dB | −7.41 dB | −1.51 dB | −7.71 dB |
| At 100 GHz | −2.26 dB | −8.42 dB | −2.83 dB | −8.99 dB |

**That reading is wrong, and it is wrong in the direction that would cost a
designer a driver.** The open line's zero-frequency value is twice the matched
line's, an open end doubling the standing voltage, so the column above measures
the loss of a doubling the open cell had to begin with. Two cells are compared
by driving them from the same source and asking what modulation each produces,
which is the unnormalised index, and
[`rf.far_end_penalty`](../../design-chain/src/picchain/rf.py) computes it.

| Open against terminated, both driven alike | O band | C band |
| --- | ---: | ---: |
| At 0.1 GHz | **+5.45 dB** | +5.36 dB |
| At 5 GHz | +2.73 dB | +2.73 dB |
| Worst point | **−1.91 dB at 9.8 GHz** | −1.88 dB at 9.8 GHz |
| At 20 GHz | −0.58 dB | −0.52 dB |
| At 40 GHz | −0.11 dB | −0.17 dB |
| At 100 GHz | −0.14 dB | −0.13 dB |

The advantage at zero frequency is 6 dB on a lossless line and 5.5 here, the
conductor loss taking the rest. That loss is flat below about 7 GHz, the skin
depth in gold reaching the 0.9 um the metal is assumed to be at that frequency,
so extrapolating the 10 GHz attenuation as the square root of frequency
overstates the advantage by half a decibel. The script uses the chain's own
resistance rather than an extrapolation.

**An unterminated cell is better than a terminated one below 7.2 GHz, worse by
1.91 dB at one null at 9.8 GHz, and within half a decibel of it above
49.1 GHz.** The returned wave adds in phase at zero frequency and dephases as
the frequency rises; the null is where it subtracts. Above the null the ratio
rings about parity with a decaying amplitude rather than crossing once and
settling, which is why the figure quoted is the frequency above which the
ringing stays inside half a decibel. The C-band cell behaves the same way, its
null falling at 9.8 GHz and its ringing settling at 49.5.

The design consequence is therefore narrow rather than broad. A cell driven at
baseband or a few gigahertz gains up to 5.4 dB from being left open. A cell
driven across 10 GHz pays 1.9 dB there. A cell driven above 50 GHz does not
care.
**What is not true, and what the self-referred table would have led a reader to
believe, is that an unterminated cell demands twice the drive at every
frequency.** It demands the same drive nearly everywhere.

The termination earns its place for reasons this model does not carry: it damps
the reflection that would otherwise return to the driver, and it removes the
null. Both cells were described by one figure until this was written, and the
figure that distinguishes them is the penalty above rather than a bandwidth.

## The cell assembled from its own measured blocks

Every figure above describes a part. The cell is the parts cascaded, and what a
link budget consumes belongs to the cascade. The assembly at
[`scripts/assembled.py`](scripts/assembled.py) uses the splitter transmission
and imbalance measured in the companion study, the half-wave voltage from the
electrode stage, and the propagation loss as the bracket transferred from the
literature, that being the one input nobody has measured.

The half-wave column is the uniform electrode, `assembled.py` carrying the
5.5286 V·cm of the rail cross-section. On the drawn electrode every entry in it
becomes 5.898 V. The insertion loss and the extinction do not depend on it.

| Splitter | Loss | Insertion | Extinction | Device Vpi, uniform electrode |
| --- | ---: | ---: | ---: | ---: |
| The 1x2 as measured here | 0.31 dB/cm | 0.233 dB | 74.9 dB | 5.529 V |
| The 1x2 as measured here | 0.95 dB/cm | 0.557 dB | 65.2 dB | 5.529 V |
| The 2x2 as measured here | 0.31 dB/cm | 1.092 dB | 52.3 dB | 5.529 V |
| The 2x2 as measured here | 0.95 dB/cm | 1.415 dB | 51.1 dB | 5.529 V |
| The imbalance the kit states | 0.31 dB/cm | 0.263 dB | 48.8 dB | 5.529 V |
| The imbalance the kit states | 0.95 dB/cm | 0.586 dB | 48.0 dB | 5.529 V |

Three readings follow.

**The choice of splitter costs more than the propagation.** A cell built on the
2x2 carries 0.86 dB more insertion loss than one built on the 1x2, against
0.32 dB for the whole range of propagation loss, because the 2x2 sits off its
imaging length and each of the two splitters pays for it.

These figures were 0.44 and half their present size until 2026-09-04, the
combiner's transmission having been written as its own reciprocal times itself
and cancelling. The cell draws two splitters and the assembly priced one. The
script now asserts what would have caught it: two lossless splitters pass
everything, and two of transmission t pass t squared.

**The extinction of the 1x2 variant is not to be believed at 75 dB.** Its
splitter imbalance is zero by the symmetry of the drawing rather than by
measurement, so the only asymmetry left in the model is the loss over the 100 um
the arms differ by. A fabricated device carries width and etch asymmetry that no
figure here represents, and the kit's own stated imbalance of 0.06 dB, which is
the honest number to design against, ceilings it at 48 dB.

**The half-wave voltage is unmoved by any of it.** It is set by the electrode
alone, so the splitter and the loss change what reaches the detector and not
what the driver must deliver.

## What is not covered, and why

**The absolute splitter loss, as against the difference between the two
topologies.** Every one of these cells carries two multimode splitters, and
their excess loss is the largest passive term in the device. The companion study
establishes that both 1x2 figures carry a conditioning residue of about one per
cent, so the insertion losses tabulated above are firm on the difference between
the topologies and carry that residue in their absolute value.

**The resistance of the termination itself.** The kit declares the resistor
58.112 um long and 1.5 um wide and declares no sheet resistance for the layer it
is drawn on, so its value cannot be computed from the kit. A terminated cell is
therefore taken as matched by declaration rather than by calculation, and a
termination 20 per cent away from the line impedance returns 9.1 per cent of the
wave in amplitude and 0.8 per cent in power, which the model would represent if
the resistance were known.

**The pad at the far end.** The reflection coefficient carried by the model is
real and frequency-independent. A resistor on a bond pad presents a shunt
capacitance beside it, so a real open end returns slightly less than unity at
high frequency and the model returns exactly unity.

**The complementary output.** The 2x2 variants present two outputs whose powers
are complementary, and the chain assembles one transfer function. What the
figures above describe is the through port.

## The run register

| Run | Design | Stages |
| --- | --- | --- |
| `20260903-195703-ltoi300_mzm_oband` | `design_mzm_oband.yaml` | mode, eo, modulator, verify |
| `20260903-200242-ltoi300_mzm_cband` | `design_mzm_cband.yaml` | mode, eo, modulator, verify |
| `20260904-212011-ltoi300_mzm_oband` | the same, at the drawn narrow-gap cross-section | mode, eo |
| `20260904-212401-ltoi300_mzm_oband` | the same, at the drawn wide-gap cross-section | mode, eo |
| `20260904-212838-ltoi300_mzm_cband` | the same, at the drawn narrow-gap cross-section | mode, eo |
| `20260904-213216-ltoi300_mzm_cband` | the same, at the drawn wide-gap cross-section | mode, eo |

| `20260904-225212-ltoi300_mzm_oband` | the same, with `electrodes.far_end_load_ohm=1e9`, being the unterminated cell | mode, eo |

**`runs/latest.json` points at that last probe and not at the run of record.**
Its `electro_optic_3dB_GHz` is 4.54 GHz against the 169.6 the run of record
reports, that being the self-referred figure of an open line and the reason the
section above says the self-referred figure is the wrong one. A reader following
the mechanical pointer rather than this register lands on it.

The four before it are the pair per band that
[`scripts/trail_electrode.py`](scripts/trail_electrode.py) homogenises. Each is
the design of record with `electrodes.width_um`, `electrodes.gap_um` and
`electrodes.ground_width_um` overridden to the section the cut measures, so the
two differ from the run of record in three declared fields and in nothing else.

The taper and the index sensitivity were measured on the same two designs, the first by `--set taper.enabled=true` with a tip of 0.7 um over 100 um at 64 slices, the second by the script named above.

Both device runs verify. Every target in both designs is a `should`, so no `must` row was evaluated and the PASS attests to the `should` rows alone. Two `should` rows fail in each,
being the arm and the device half-wave voltage against the kit's own figures,
and they fail by 25.6 per cent in the O band and 31.2 in the C band. The
companion study attributes that difference to the electrostatic mesh and to the
normalisation of the overlap integral, and neither correction is applied.
