# A test chip that measures the electro-optic overlap of the LTOI300 arm

## What this device is for

It is not a modulator anyone should ship. It is an instrument, drawn on the
LTOI300 process, whose output is one number that this chain and the foundry kit
disagree about.

The half-wave voltage of a push-pull interferometer on an X-cut Pockels film is

    Vpi . L  =  lambda . g  /  ( 2 . n_eff^3 . r33 . Gamma )

Every term on the right but the last is known to better than a per cent. The
wavelength is chosen, the gap is drawn, the effective index is solved by two
independent solvers that agree, and r33 is a material constant the foundry
manual states.

**The second solver was run on 2026-09-05 and it narrows the experiment.** The
finite-element stage solves the same cross-section full-vectorially on a
conforming triangulation, and it returns:

| | |
| --- | ---: |
| `n_eff`, finite difference | 1.7713563 |
| `n_eff`, finite element | 1.7712140 |
| Relative disagreement | **8.0e-5** |
| Polarisation purity | **0.99961** |
| Film confinement, the two solvers | 0.65218, 0.65206 |
| Mesh convergence | resolved, shift 9e-6 |
| Anisotropy bracket, weighted | 2e-6 |

**Every term of the expression above but the last two is now confirmed by an
independent route.** The mode is 99.96 per cent transverse-electric, so the
semi-vectorial approximation the overlap is computed under is sound on this
cross-section, and the two solvers agree on the effective index to the fourth
decimal. The 31 per cent disagreement therefore does not live in the optical
mode. It lives in the overlap integral, in the electrostatic solve that feeds
it, or in the kit's own model, and the ladder is built to separate the first of
those from r33. **Gamma, the overlap between the applied electric field and the
optical mode, is the only free term, and the two available models of it differ
by 38 per cent.**

| | Vpi.L, one arm | Implied Gamma |
| --- | ---: | ---: |
| This chain, on the rail cross-section it solves | 7.3482 V.cm | 0.3880 raw |
| The same, homogenised over the drawn T-rail | 7.7384 V.cm | — |
| The kit's own compact model | 5.6000 V.cm | 0.5091 implied |

**The chain solves one cross-section per run and the drawn electrode is two.**
The modulation section is periodically interrupted, holding a 5.5 um gap for 53
of every 58 um and opening to 11.5 um for the remaining 5, so the figure a run
returns is that of the rail section alone. Homogenising the two over the period
raises it by 5.31 per cent, which the [Mach-Zehnder study](../ltoi300_mzm/README.md) computes and this concept
carries as a stated correction rather than as something the run performs. Every
target below is set against what the run returns, and the corrected figure is
reported beside it.

The disagreement is not academic. Over the 5 mm the cell draws it is the
difference between a driver that must deliver 7.74 V and one that must deliver
5.60 V, and no measurement anywhere in this repository settles it. This device
exists to produce that measurement. An earlier revision of this paragraph gave
3.9 and 2.8, which are the half-wave figures in volt-centimetres read as though
they were volts, and understated the drive by a factor of two.

## By what principle it settles it

**One device cannot settle it.** A single half-wave voltage constrains the
product `r33 . Gamma` and nothing else. Any disagreement in Gamma can be
absorbed by moving r33, which carries its own uncertainty on thin film, so a
single measured Vpi.L would leave both models standing.

**A ladder over the electrode gap can.** Stepping the gap and measuring Vpi.L at
each rung separates the two, because r33 multiplies every rung by the same
factor while Gamma changes shape across them. That r33 is uncertain on thin film
is the reason the ladder is needed; the sentence above says every term but Gamma
is known to a per cent, and r33 is the exception it is known to less well
than. The measured curve Vpi.L(g) is
therefore a test of the overlap model that is independent of the material
constant.

The asymmetry between the two models is what makes this worth fabricating. This
chain computes Gamma from an electrostatic solve at whatever gap it is given, so
it predicts the whole curve. **The kit's model has no gap dependence at all**:
`design-chain/pdk/lxt_pdk_gf/ltoi300/models.py` sets the half-wave voltage from wavelength and length alone,
so it predicts one point and is silent at every other rung. The ladder therefore
tests this chain's model against the wafer, and uses the kit's figure as the one
external check at the gap the kit draws.

## What each clause of that principle requires, and what expresses it

| Clause of the principle | The quantity that expresses it | Where it comes from |
| --- | --- | --- |
| It modulates by the Pockels effect at all | `eo.VpiL_V_cm`, and `eo.eo_overlap_gamma` as the quantity within it the chip measures | the electrostatic solve and the overlap integral |
| It is a push-pull interferometer, so the device figure is half the arm figure | `modulator.VpiL_device_V_cm` | the interferometer transfer function |
| The rungs differ enough to be told apart | the spread of `eo.VpiL_V_cm` across the ladder | **not computed.** The split draws each rung and solves none; the electro-optic stage runs at one gap |
| Each rung is measurable with a laboratory source | `modulator.Vpi_V` | the arm figure over the drawn length |
| The optical null is deep enough to find | **no stage computes it** | declared as a limitation below |
| The measurement is not distorted by the electrode at speed | `eo.travelling_wave.far_end_worst_penalty_dB` | the travelling-wave model, on the open line this mask draws |
| The drive reaches the electrode rather than reflecting | `eo.travelling_wave.characteristic_impedance_ohm` | the line parameters |
| It can be made | the rule deck returning no violation on the die | `drc` and `mask` |

## The trace from each clause to the target that tests it

The table is machine-read by `design-chain/tools/check_concept_trace.py`, which requires that
every declared target appear here and every traced clause carry a target. The
column after the clause is the metric and the one after it the severity.

| Clause | Metric | Severity | Why that severity |
| --- | --- | --- | --- |
| Every rung is reachable by a laboratory source | `modulator.Vpi_V` | must | Above 25 V the null cannot be found and the rung measures nothing. |
| The device modulates at all | `eo.eo_overlap_gamma` | must | An overlap below five per cent is not a modulator, whatever the ladder does. |
| It modulates by the Pockels effect, against the kit's figure | `eo.VpiL_V_cm` | should | The disagreement is the subject of the experiment. A must here would assert the answer the chip is built to find. |
| The push-pull convention is applied | `modulator.VpiL_device_V_cm` | should | The same physics read through the convention, and the same reason. |
| The measurement is not distorted at the speed it is taken | `eo.travelling_wave.far_end_worst_penalty_dB` | should | The mask draws an open far end, and the self-referred 3 dB point of an open line measures the loss of a doubling rather than a loss. The penalty against a matched line is what a measurement sees. |
| The drive reaches the electrode | `eo.travelling_wave.characteristic_impedance_ohm` | should | A mismatch costs drive and is corrected in the measurement, not in the mask. |

Two clauses of the principle carry no row, and each is accounted for elsewhere.
**The rungs being distinguishable** is a property of the ladder rather than of
any single run, so no metric of one run expresses it; it is checked by reading
the split description the reticle stage emits and is reported in the study.
**Manufacturability** is not a metric but a verdict, and it is gated by the
`drc` and `mask` stages raising rather than by a target.

**The two `must` rows are the ones that decide whether the chip is an
instrument.** The rows carrying the disagreement are deliberately `should`,
because the purpose is to find out which side is right and a `must` on either
would be the chain asserting its own answer. That is the distinction chain rule
16 exists to preserve: a target encodes the requirement, and the requirement
here is that the experiment be able to discriminate, not that it come out one
way.

## What this concept does not claim

**It does not claim the chain is right.** The 38 per cent is stated as an open
disagreement in both directions. The [modulator study](../ltoi300_modulator/README.md) attributes part of it to
the electrostatic mesh and part to the normalisation of the overlap integral,
and applies neither correction.

**It does not claim the ladder is sufficient.** The gap changes the metal loss
seen by the optical mode as well as the overlap, and the two are not separated
by this measurement alone. A rung at very small gap is limited by absorption
rather than by overlap, and `eo.mode_overlap_with_metal` is read to find where
that begins.

**It does not claim the process is characterised.** The propagation loss enters
every figure as a bracket transferred from the literature, and no rung of this
ladder measures it.

**The extinction is a declared limitation and not a target.** Finding the null
is a precondition of measuring a half-wave voltage, and no stage of this chain
computes the extinction of an interferometer: `modulator` emits the half-wave
voltage, the drive and the in-band response, and nothing about the depth of the
null. The budget carried instead is the one the [Mach-Zehnder study](../ltoi300_mzm/README.md) computed by
hand, being 48 dB at the kit's own stated splitter imbalance of 0.06 dB and
51 dB on the 2x2 as measured. Both are far deeper than a measurement needs, so
the risk this limitation carries is small. It is recorded here rather than
converted into a target, because a target naming a metric no stage emits would
pass by being unevaluated.
