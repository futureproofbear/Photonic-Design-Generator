# Toolchain Baseline Against arXiv:2408.01743v1

**Purpose.** A published and measured device is to be reproduced end to end
before the same chain is applied to the TFLT radar PICs. The device is the
thin-film lithium niobate extended-DBR Pockels laser of

> A. Siddharth, S. Bianconi, R. N. Wang, Z. Qiu, A. S. Voloshin, M. J. Bereyhi,
> J. Riemensberger, T. J. Kippenberg, *"Ultrafast tunable photonic integrated
> Pockels extended-DBR laser"*, arXiv:2408.01743v1 (2024); published as
> Nat. Photon. **19**, 709–717 (2025).

The device is a widely cited reference architecture for frequency-agile,
low-noise integrated sources, and is therefore a suitable subject against which
the chain may be validated.

Reproduction is defined as follows: only the geometry stated in the paper is
adopted, the chain is executed, and the result is compared against the figures
reported in the paper using tolerances declared **before** the output was
examined. No quantity was adjusted in order to obtain agreement.

## Nomenclature

The symbols used throughout this document are defined here. The final column
gives the dotted path at which the quantity is found in `metrics.json`, so that
any figure quoted below can be traced to the run that produced it.

| symbol | quantity | definition or relation | metric path |
|---|---|---|---|
| n_eff | effective index of the guided mode | the propagation constant divided by the free-space wavenumber | `mode.n_eff_bare` |
| Δn_eff | index perturbation contributed by the Bragg posts | the difference between the effective index with the posts present and that of the bare ridge | `mode.dn_eff_posts` |
| D | duty cycle of the grating | the fraction of one period occupied by the posts; 0.234 in this device | `grating.duty_cycle` |
| n̄ | mean effective index over one grating period | n̄ = n_eff + Δn_eff·D; it is this average, and not n_eff, that sets the Bragg wavelength | `grating.n_bar` |
| n_g | group index | n_eff − λ·dn_eff/dλ; it sets the round-trip delay and the free spectral range | `mode.n_g` |
| Λ | grating period | λ_B = 2·n̄·Λ/m, with m the grating order | `grating.period_um` |
| m | grating order | 3 in this device; the third harmonic of the Bragg condition is used so that the period is lithographically attainable | `grating.order` |
| λ_B | Bragg wavelength | the wavelength at which the grating reflects | `grating.bragg_wavelength_nm` |
| a_m | amplitude of the m-th cosine harmonic of the index profile | a_m = 2·Δn_eff·sin(π·m·D)/(π·m) for a rectangular profile | `grating.fourier_amplitude_a_m` |
| κ | coupling constant of the grating | the reflection per unit length; κ = π·a_m/λ_B | `grating.kappa_per_cm` |
| L | grating length | 7.25 mm in this device | `grating.length_um` |
| κL | integrated coupling strength | the dimensionless product that fixes the peak reflectivity | `grating.kappa_L` |
| R | peak reflectivity of the mirror | R = tanh²(κL) for a uniform grating | `grating.peak_reflectivity` |
| FWHM | full width at half maximum of the reflection band | the mirror bandwidth | `grating.fwhm_GHz` |
| L_pen | penetration depth | the mean distance into the grating at which the light turns; it rises as κ falls | `grating.penetration_depth_mm` |
| Γ | electro-optic overlap factor | the fraction of the optical mode that experiences the applied field | `eo.eo_overlap_gamma` |
| Vπ·L | half-wave voltage-length product | the voltage-length product required for a π phase shift; quoted at Γ = 1 or with Γ included | `eo.VpiL_ideal_V_cm`, `eo.VpiL_V_cm` |
| τ_DBR, τ_rt | group delay in the grating, and the cavity round-trip delay | the delays that fix the tuning lever | `cavity.tau_dbr_ps`, `cavity.tau_roundtrip_ps` |
| τ_a | group delay within the active section | the delay contributed by the RSOA alone; the ratio (τ_a/τ_rt)² is the factor by which an extended cavity narrows the linewidth | `cavity.tau_soa_ps` |
| r | Pockels lever | r = τ_DBR/τ_rt; the fraction of the round-trip delay that follows the mirror when voltage is applied | `cavity.pockels_lever` |
| FSR | free spectral range of the cavity | the longitudinal mode spacing, equal to 1/τ_rt | `cavity.fsr_GHz` |
| MHF | mode-hop-free range | the continuous frequency excursion obtained before the lowest-threshold longitudinal mode changes. It is computed by tracking the modes across the voltage sweep. The closed form r/(1−r)·FSR/2 is retained separately as a cross-check | `cavity.mode_hop_free_range_GHz`, `cavity.mode_hop_free_range_GHz_analytic` |
| SMSR | side-mode suppression ratio | the power ratio between the lasing mode and the strongest side mode | `cavity.smsr_dB` |
| α | linewidth enhancement factor | the ratio of the real to the imaginary part of the change in refractive index with carrier density; the linewidth scales as (1 + α²) | design input |
| n_sp | spontaneous emission factor | the population inversion factor of the gain medium; both the linewidth and the SMSR scale with it | design input |

The abbreviations used are: **E-DBR** extended distributed Bragg reflector;
**RSOA** reflective semiconductor optical amplifier, being the gain chip;
**TFLN** thin-film lithium niobate; **TFLT** thin-film lithium tantalate;
**TMM** transfer-matrix method; **DRC** design rule check; **GDS** the mask
layout format; **DUV** deep ultraviolet; **CD** critical dimension.

## Result

```
$ picchain run ../examples/edbr_tfln_baseline/design.yaml
verify: FAIL  (9/12 targets met; 1 unmet at severity must, 2 at severity should)
```

### Construction of the Verdict

Three distinct items are carried by each row of the table below, and they are not
to be conflated.

* **Criterion.** The admissible interval. It was written into the `targets:`
  block of `design.yaml` before the chain was executed, and it was derived from
  the figure published in the paper. The published figure is stated separately in
  the column beside it.
* **Result.** The value computed by the chain for that metric.
* **Status.** `pass` where the result lies within the interval. `fail` where it
  lies outside. `missing` where the metric was not produced at all.

The effect of a status upon the run verdict is governed by the severity declared
alongside the criterion. A target of severity `must` that does not pass sets the
verdict to FAIL and the process exit code to 2. A target of severity `should`
that does not pass is recorded and counted, and the verdict is left unchanged.
The verdict of this run is FAIL. It is set by the single reflectivity row, that
being the only target of severity `must` that was not met.

### The Declared Acceptance Targets
<!-- what is fwhm? -->
| metric | criterion | published figure from which it was drawn | result | severity | status |
|---|---|---|---:|---|---|
| `mode.n_guided_modes` | ≤ 1 | single-mode operation is asserted by design | 1 | must | pass |
| `grating.bragg_wavelength_nm` | 1545.9 nm ± 2 %, that is 1515.0 to 1576.8 | 1545.9 nm measured, stated as 1.2 % from the design value | 1530.8 nm | must | pass |
| `grating.peak_reflectivity` | 0.75 ± 20 %, that is 0.600 to 0.900 | Fig. 1d, approximately 75 % simulated | 0.975 | must | **fail** |
| `grating.fwhm_GHz` | 5.0 to 14.0 GHz | 6.5 GHz simulated, 8 GHz measured off chip | 21.38 GHz | should | **fail** |
| `eo.tuning_MHz_per_V` | 550 MHz/V ± 30 %, that is 385 to 715 | Fig. 2a, 550 MHz/V measured at the mirror | 708.1 MHz/V | must | pass |
| `eo.VpiL_ideal_V_cm` | 4.0 V·cm ± 25 %, that is 3.00 to 5.00 | 4 V·cm simulated, quoted without overlap derating | 3.56 V·cm | should | pass |
| `eo.mode_overlap_with_metal` | ≤ 1 × 10⁻⁵ | electrodes described as placed conservatively to avoid loss | 1.30 × 10⁻⁸ | must | pass |
| `cavity.mode_hop_free_range_GHz` | ≥ 8.0 GHz | abstract, continuous tuning in excess of 10 GHz | 3.85 GHz | should | **fail** |
| `cavity.schawlow_townes_henry_linewidth_kHz` | 2.8 kHz ± 100 %, that is 0 to 5.6 | 2.8 kHz intrinsic, inferred from 800 Hz²/Hz at 2 MHz offset | 4.88 kHz | should | pass |
| `cavity.smsr_dB` | ≥ 40 dB | 63 dB at 0.02 nm resolution bandwidth | 52.6 dB | should | pass |
| `drc.error_violations` | ≤ 0 | not applicable; a chain requirement | 0 of 5 rules | must | pass |
| `layout.mask_is_complete` | ≥ 1 | not applicable; a chain requirement | true | info | pass |

Two of the criteria are deliberately looser than the published figure they cite.
The linewidth is admitted at a factor of two, the RSOA parameters on which it
depends being assumptions rather than measurements. The SMSR floor is set at
40 dB rather than at the measured 63 dB, since the chain models only the nearest
side mode. Both relaxations were declared in advance and are recorded here so
that the passes they produce are not read as stronger than they are.

### Quantities Computed but Not Placed Under a Target

No criterion was declared for the following, the paper not having quoted a value
against which one could be written. They are reported because the interpretation
of the three misses rests upon them.

| quantity | result |
|---|---|
| n_eff (bare ridge) / n_g | 1.7939 / 2.2158 |
| Δn_eff contributed by the Bragg posts | 1.119 × 10⁻³ |
| κ, and κ·L over the 7.25 mm grating | 3.91 cm⁻¹, κL = 2.836 |
| grating penetration depth | 1.269 mm |
| electro-optic overlap Γ | 0.373 |
| Vπ·L including the overlap derating | 9.55 V·cm |
| Pockels lever τ_DBR/τ_rt | 0.326 |
| cavity free spectral range | 17.37 GHz |
| laser tuning rate, being the lever times the mirror rate | 269.0 MHz/V |
<!--what is κ?-->
Execution time for the full chain is approximately **50 s** on a single core,
without GPU acceleration and without a licence server.

## What Is Established

The following elements of the chain are confirmed against measurement:

* **The mode solver.** The Bragg wavelength is determined solely by n̄ and the
  stated period, and the computed value falls 0.98 % from the measured 1545.9 nm.
  The paper records its own design as having sat 1.2 % from the same measurement.
  Two independent routes to the same approximately 1.2 % offset constitute a
  strong check on n_eff. The cross-section has since been re-solved by finite
  elements on a conforming triangulation, which agrees to 2.6 × 10⁻⁴ in n_eff
  and to 1.8 % on the index difference produced by the Bragg posts.
* **The electro-optics.** Vπ·L at Γ = 1 is obtained as 3.55 V·cm against the
  4 V·cm quoted in the paper, which incidentally identifies the nature of that
  quoted figure: it is the un-derated, perfect-overlap value. The physical
  Vπ·L, once the computed overlap Γ = 0.369 is included, is 9.6 V·cm.
* **The laser physics.** The Schawlow–Townes–Henry linewidth, evaluated with the
  extended-cavity (τ_a/τ_rt)² reduction, is obtained as 4.14 kHz against a
  measured 2.8 kHz, from RSOA parameters that are themselves assumptions.
  Agreement within a factor of 1.5 on an absolute linewidth is the result of
  interest.
* **Mask generation and DRC.** GDS is produced through both <span style="color:#1a73e8"><strong>klayout</strong></span> and
  <span style="color:#1a73e8"><strong>gdsfactory</strong></span>, and the result is DRC clean.

## The Three Misses and Their Interpretation

### 1. κ is stronger by a factor of 2.15, which constitutes a manufacturability finding

> **SUPERSEDED, 2026-08-10. The factor of 2.15 is retained as the record of what
> was measured and is not to be quoted as the present finding.**
>
> Two things have changed beneath it. The comparison against the band structure
> was not like for like, one side applying a longitudinal profile smoothing and
> the other applying none, and the geometry has since moved: the post gap is
> 855 nm where this section describes 630 nm, and the profile smoothing is zero
> where this section assumes 57.1 nm.
>
> The converged measurement is **1.184**, taken at the present geometry, and it
> is set out under "The Coupling Constant, Measured Twice and Converged" below.
> The excess over the value the paper implies is a separate question from the
> agreement between two of this chain's own routes, and this section conflates
> them.
>
> What survives unchanged is the *manufacturability* argument this section
> exists to make: κ is exponential in the post gap, a 20 nm lithographic error
> is roughly 11 % of κ, and a design is therefore to be centred where the
> derivative of performance with respect to κ is flat. That reasoning does not
> depend on the numerical factor.


*Re-derived on 2026-08-04, the sidewall angle having been corrected from 90° to
77°. The figures previously recorded in this section were taken at 90° and the
excess then stood at 1.60. What changed and why is set out under "The
re-baseline" below.*

A single discrepancy is responsible for the three misses. Four quantities lie
downstream of κ and all four are displaced by it: the reflectivity at 97.5 %
against 75 %, the bandwidth at 21.4 GHz against 8 GHz, the penetration depth at
1.27 mm, and the mode-hop-free range that follows from the penetration depth.
The computed Δn_eff is 1.119 × 10⁻³. The 75 % reflectivity of the paper at
L = 7.25 mm implies κL = 1.317, that is, κ = 1.82 cm⁻¹ against the 3.91 cm⁻¹
computed here.

The sharpness of the lever is quantified by a gap sweep
(`sweep_post_gap.json`):

| post gap (nm) | Δn_eff | κ (cm⁻¹) | κL | R | FWHM (GHz) |
|---:|---:|---:|---:|---:|---:|
| **630** | **1.119e-3** | **3.912** | **2.836** | **0.975** | **21.4** |
| 680 | 8.475e-4 | 2.964 | 2.149 | 0.933 | 17.5 |
| 730 | 6.421e-4 | 2.246 | 1.628 | 0.841 | 14.4 |
| **~762** | **~5.4e-4** | **~1.87** | **~1.36** | **~0.75** | **~12.9** |
| 770 | 5.143e-4 | 1.799 | 1.304 | 0.728 | 12.6 |
| 800 | 4.355e-4 | 1.523 | 1.104 | 0.628 | 11.5 |
| 850 | 3.300e-4 | 1.154 | 0.837 | 0.455 | 10.2 |

The measured sensitivity is d(ln Δn_eff)/d(gap) = **−5.55 µm⁻¹**, corresponding
to a 180 nm decay length. It follows that:

* a post gap of approximately 762 nm reproduces the 75 % figure of the paper.
  That gap is **132 nm** greater than the nominal 630 nm. The offset is large
  for a single lithographic bias, and part of it is known to belong to the model
  rather than to the process; see the two subsections that follow.
* **a ±20 nm lithography error constitutes a ±12 % error in κ.** For any
  programme adopting this architecture this is the principal result: κ, and
  hence mirror reflectivity, penetration depth and mode-hop-free tuning range,
  is exponentially sensitive to a single sub-100 nm dimension. Such a design
  must therefore either be centred where ∂(performance)/∂κ is small, or be
  equipped with a κ-trim mechanism, and the first reticle must carry a
  stepped-gap monitor so that the sensitivity is measured rather than modelled.

#### The sidewall angle was the alternative explanation, and it was corrected rather than excluded

This section previously recorded a sidewall sweep run as the competing candidate
and reported it as excluding the sidewall. That reading was correct as far as the
direction of the effect, and wrong about what to do next.

The design file carried 90°, annotated as an assumption because the paper quotes
no angle. An ion-beam-etched thin-film lithium niobate ridge does not have a
vertical wall, so 90° was not a conservative placeholder; it was a value the
process cannot deliver. The open Luxtelligence `lnoi400` kit declares 13° from
the normal, which is 77°, for the same 400 nm film, 200 nm etch and 4.7 µm oxide
stack. That figure has been adopted.

| quantity | at 90° (as carried until 2026-08-04) | at 77° (adopted) |
|---|---:|---:|
| n_eff | 1.7889 | 1.7939 |
| Δn_eff | 8.277 × 10⁻⁴ | 1.119 × 10⁻³ |
| κ | 2.90 cm⁻¹ | 3.91 cm⁻¹ |
| λ_B | 1526.4 nm | 1530.8 nm |
| excess over the paper-implied κ | ×1.60 | **×2.15** |

**The correction enlarges the discrepancy rather than resolving it.** A
trapezoidal post presents a wider base positioned nearer the ridge, so sloping
the wall raises Δn_eff, and the more physically plausible geometry is the one
that disagrees more strongly with the paper. The Bragg wavelength moves 4.3 nm
toward the measurement at the same time, so the two residuals do not share a
cause.

This is recorded as an instance of a general point. Replacing an assumption with
a sourced value is not a step toward agreement; it is a step toward knowing what
the model actually says. Here it made the open question larger and better posed.

#### The hypothesis, tested

The gap sweep predicts that a post gap of approximately 762 nm reproduces the
published reflectivity. That prediction was tested directly. One parameter was
moved and nothing else, the design file itself being left at the published
630 nm.

```
$ picchain run ../examples/edbr_tfln_baseline/design.yaml       --set grating.post_gap_um=0.762 --tag gap762
```

| quantity | at 630 nm, as published | at 762 nm | target | published figure |
|---|---:|---:|---|---|
| κ | 3.91 cm⁻¹ | 1.87 cm⁻¹ | — | — |
| κL | 2.836 | 1.359 | — | — |
| peak reflectivity | 0.975 **fail** | **0.751 pass** | 0.75 ± 20 % | ≈ 75 % |
| mirror bandwidth | 21.4 GHz **fail** | **12.9 GHz pass** | 5 to 14 GHz | 8 GHz measured |
| mode-hop-free range | 3.85 GHz **fail** | 4.78 GHz **fail** | ≥ 8 GHz | > 10 GHz |
| SMSR | 52.6 dB | 50.6 dB | ≥ 40 dB | 63 dB |
| Bragg wavelength | 1530.8 nm | 1530.6 nm | 1545.9 ± 2 % | 1545.9 nm |
| sidelobe suppression | 5.4 dB | 9.9 dB | — | — |
| DRC | 0 violations | **800 violations** | 0 | — |

**One parameter, displaced by 132 nm, now reconciles three of the four published
figures rather than all four.** Reflectivity, bandwidth and side-mode
suppression are recovered. The continuous tuning range is not: it reaches
4.78 GHz against the 8 GHz target and the greater than 10 GHz reported.

That is a weaker result than this section previously recorded, and the weakening
is informative. At 90° the same probe returned a mode-hop-free range of 12.0 GHz
and the reconciliation appeared complete. The difference is not in the mirror.
At 762 nm the penetration depth is 2.34 mm, the round-trip delay 73.3 ps and the
Pockels lever 0.471, giving a free spectral range of 13.6 GHz and a closed-form
excursion of 6.07 GHz, against 4.78 GHz from the mode-tracking solve. A
weakened, longer-penetrating mirror raises the lever and lowers the free
spectral range at the same time, and on this geometry the second effect wins.

**A single geometric offset is therefore no longer sufficient as an
explanation.** Two readings remain open and they are not exclusive. Either the
gain chip and feed lengths, both of which are assumptions in this file and both
of which set the lever, are shorter in the real device than the 1 mm assumed
here; or the reported tuning range involves co-tuning of the drive current,
which the paper describes as its second control parameter and which this model
does not carry.

**The published geometry is nevertheless retained and the design continues to
fail.** The 630 nm figure is what the paper states. Substituting 762 nm would
replace the published geometry with a hypothesis about what was fabricated, and
this design exists to run the published numbers and report where they disagree.

**A second finding falls out of the probe, and it is a design constraint rather
than a validation result.** At 762 nm the mask fails `METAL_to_WG_sep` with 800
violations. **Weakening the grating pushes the posts toward the electrodes.**
The two constraints are coupled, and clearing the rule requires the electrode gap
to be widened, at a cost in overlap and therefore in tuning efficiency. Any
design that reduces κ by opening the post gap is to be checked against the
electrode separation in the same step.

#### κ checked against two solvers, and a correction to the reading above

The coupled-mode κ has since been tested against instruments that owe it
nothing. Both are applied to the identical two-dimensional reduction of the
structure, so that the mode solver is held fixed and only the coupled-mode
construction is under test.

| instrument | what it measures | κ against the coupled-mode value |
|---|---|---:|
| <span style="color:#1a73e8"><strong>MPB</strong></span> band structure, resolution 32 / 48 / 64 | the width of the stop band at the zone edge. No length, no propagation, no radiation channel | 0.88 / 0.78 / **0.74**, still falling |
| <span style="color:#1a73e8"><strong>meep</strong></span>, 250 periods at a 450 nm gap | the reflection of a finite grating, with 3.6 % of the power radiated | **0.53** |

**Both say the coupled-mode construction over-predicts κ, by between a quarter
and a half.** Neither is fully converged and the two do not yet agree with one
another, so the factor is bounded rather than pinned.

This qualifies the fabrication-bias reading given above and does not overturn
it. If coupled-mode theory over-predicts by approximately 1.35, then of the
factor 2.15 by which the chain exceeds the value the paper implies, roughly 1.35
is the model and roughly 1.6 remains for the geometry. A lithographic bias of
132 nm was inferred on the assumption that the whole factor was geometric; on
the corrected reading the implied bias is smaller, and the 762 nm figure is an
upper bound on the displacement rather than an estimate of it.

**These two ratios were measured on the 90° structure and have not been
re-derived at 77°.** Both the band-structure and the finite-grating checks pose
the same geometry to a second solver, so a change of geometry moves the
numerator and the denominator together and the ratio is expected to be stable.
It is expected to be stable, and it has not been shown to be. Re-running the
band-structure check on the sloped cross-section is the outstanding item here.

Two cautions attach to the numbers above. The band gap is a difference of two
eigenvalues of order 6 × 10⁻⁵ in units of c/a, so it converges slowly and the
series has not flattened. The finite-grating measurement is confounded by
radiation, which coupled-mode theory does not model at all, and 3.6 % of the
power was unaccounted for even at the weakest perturbation that remained
measurable.

#### The band-structure check re-run at 77°, and what it established

Re-running the band-structure check on the sloped cross-section was recorded
above as the outstanding item. It has been carried out, and the result is that
**the comparison does not converge at the resolutions attempted and therefore
establishes nothing.**

| resolution, pixels per period | gap df, units of c/a | κ, /cm | ratio to coupled mode |
|---:|---:|---:|---:|
| 20 | 6.175 × 10⁻⁵ | 3.359 | 0.911 |
| 30 | 7.388 × 10⁻⁵ | 4.018 | 1.089 |
| 40 | 4.151 × 10⁻⁵ | 2.258 | 0.612 |

The series is not monotone. Refining from 20 to 40 moves κ by 1.10 /cm, while
the disagreement with the coupled-mode value being tested is 0.88 /cm. The mesh
error exceeds the effect, so no extrapolation is possible and no ratio may be
read off. A verdict was nonetheless reported from the resolution-40 solve alone
and attributed in a warning to the coupled-mode construction. That verdict was
worth nothing and is withdrawn.

This does not overturn the 90° series of 0.88 / 0.78 / 0.74 recorded above.
Those were taken at 32, 48 and 64 pixels per period, are monotone, and were
correctly described at the time as still falling. The 77° series was run
coarser, and it is the coarser series that is uninformative. The two geometries
have not been compared on a common mesh.

Three defects were found in the runner while diagnosing this, and all three bear
on why the coarse series scatters.

**The declared unit was not the unit used.** `fdtd.resolution` is documented as
pixels per micrometre, and it was passed to <span style="color:#1a73e8"><strong>MPB</strong></span> unconverted. The <span style="color:#1a73e8"><strong>MPB</strong></span> lattice
unit is the grating period, so every band-structure solve ever run by this chain
executed at 1/1.28 of the density requested. The 32 / 48 / 64 series above is
therefore in pixels per period and not per micrometre, as is the series here.

**The subpixel averaging ran on its default sub-grid.** <span style="color:#1a73e8"><strong>MPB</strong></span> builds an effective
permittivity tensor for each boundary pixel on a sub-grid of `mesh_size`,
defaulting to 3. The residual staircase is negligible against a band frequency
and is not negligible against the difference of two bands separated by 5 × 10⁻⁵
of it. The 300 nm post and the 630 nm gap both land on non-integer pixel counts
that change with resolution, which is the mechanism by which the residual varies
non-monotonically with the mesh.

**The eigensolver tolerance was referenced to the wrong quantity.** A relative
tolerance of 10⁻⁷ was applied to the eigenvalue while the quantity of interest
is the difference between two of them.

The unit is now converted, `mesh_size` is 7, and the tolerance is 10⁻⁹.

**A convergence guard has been added, and it should have existed from the
start.** The stage now solves the structure a second time on a coarser mesh and
reports `fdtd.convergence.resolved` against the criterion the finite-element
cross-check already applied, being that the effect must stand clear of the mesh
shift by a factor of three. The warning attributing a disagreement to the
coupled-mode construction is gated on that verdict. Rule 15 of the operating
manual had required this guard for as long as the rule existed; the rule was
being followed in reading the output and the guard itself was absent. The lesson
is recorded as T018.

#### The rectangular longitudinal profile, which is the leading candidate

The coupled-mode κ is built from the closed-form Fourier coefficient of a
**rectangular** longitudinal index profile,

    a_m = 2 Δn sin(m π D) / (m π),

evaluated at the working order m = 3. The paper obtains the same coefficient by
spatial Fourier analysis of a profile extracted from a finite-element solve, and
such a profile is not rectangular. Two things round it. The lithography rounds
the corners of a post. The guided mode cannot resolve a step over a distance
short compared with its own transverse extent, so it responds to a
longitudinally averaged perturbation, and the post is 300 nm long against a
1280 nm period.

Modelling the rounding as a convolution with a Gaussian of RMS length σ
multiplies the m-th coefficient by exp(−(2πmσ/Λ)²/2). The exponent carries the
order squared, so the assumption is benign at first order and is not benign at
third.

| σ | first harmonic retained | third harmonic retained | factor explained |
|---:|---:|---:|---:|
| 0 | 1.000 | 1.000 | 1.00 |
| 40 nm | 0.981 | 0.841 | 1.19 |
| 80 nm | 0.926 | 0.500 | 2.00 |
| **84 nm** | **0.919** | **0.465** | **2.15** |
| 120 nm | 0.841 | 0.210 | 4.77 |

**A smoothing of 84 nm accounts for the whole factor of 2.15.** That is a full
width of 198 nm against a post 300 nm long, which is an ordinary degree of
corner rounding. The same smoothing costs the first harmonic 8 %, so the
sensitivity at third order exceeds that at first by a factor of 26. This is
consistent with the finite-element result below, which confirms the index
modulation itself to 2.0 %: the error lies in the shape of the longitudinal
profile and not in the depth of the modulation.

Two further consequences follow, and neither was fitted.

Setting σ to 84 nm gives a peak reflectivity of 0.735 against the 0.75 the paper
quotes, and a bandwidth of 12.67 GHz, which falls inside the declared target
band of 5 to 14 GHz. Both failing grating targets would pass. σ was chosen to
reproduce the reflectivity alone; the bandwidth was not fitted.

**The assumption is now stated rather than hidden.** `grating.profile_sigma_um`
declares the smoothing length and defaults to zero, which is the rectangular
case and reproduces κ = 3.91227 /cm and R = 0.974879 without change. Five
closed-form tests pin the factor.

**It has since been measured, and adopted.** See below.

#### The converged band-structure measurement, and the re-baseline of 2026-08-07

With the resolution unit corrected, the subpixel sub-grid raised to 7 and the
eigensolver tolerance tightened to 10⁻⁹, the band-structure comparison converges.

| | value |
|---|---|
| resolution | 20 px/µm, being 26 px/period |
| relative band gap | 5.70 × 10⁻⁵ |
| κ from the band gap | 2.590 /cm |
| κ from coupled-mode theory, same 2D structure | 3.689 /cm |
| **ratio** | **0.702** |
| guard resolution | 14 px/µm |
| κ at the guard resolution | 2.420 /cm |
| mesh shift | 0.170 /cm |
| difference under test | 1.099 /cm |
| **`fdtd.convergence.resolved`** | **true**, by a factor of 6.5 |

The band gap sits at 1532.18 nm against the coupled-mode 1538.86 nm, agreeing to
0.43 %, which confirms that the pair of bands identified is the intended third
order.

**The coupled-mode construction overstates κ by 1.424 on this structure.** The
smoothing length reproducing that ratio is **57.1 nm**, a full width of 135 nm
against a post 300 nm long. The same length costs the first harmonic 4 %.

`grating.profile_sigma_um` is set to 0.0571 in the baseline. Three conditions
were required before doing so and all three are met. The value is measured by an
instrument that assumes nothing about the longitudinal profile. The comparison
carries a convergence guard and the guard passes. And **adopting it makes no
target pass**, so it is not a correction factor fitted to a disagreement:

| | σ = 0 | σ = 57.1 nm | target |
|---|---:|---:|---|
| κ | 3.912 /cm | 2.747 /cm | — |
| κL | 2.836 | 1.992 | — |
| peak reflectivity | 0.9749 | 0.9133 | 0.60 to 0.90, still **fails** |
| bandwidth | 21.38 GHz | 16.55 GHz | 5 to 14 GHz, still **fails** |
| penetration depth | 1.269 mm | 1.754 mm | — |
| τ_DBR | 18.77 ps | 25.93 ps | — |
| Pockels lever | 0.326 | 0.401 | — |
| mode-hop-free range | 3.80 GHz | 4.62 GHz | ≥ 8 GHz, still fails |
| laser tuning | 268.2 MHz/V | 328.1 MHz/V | — |
| linewidth | 4.88 kHz | 4.26 kHz | ≤ 5.6 kHz, passes |

A weaker mirror penetrates further, which lengthens the grating delay and raises
the Pockels lever. Correcting κ downward therefore *improves* the tuning range,
the linewidth and the output power together. That direction was not anticipated.

**A residual factor of 1.51 against the published device remains, and it has a
simple reading.** Of the original 2.15, the longitudinal profile shape accounts
for 1.42. The remaining 1.51 is what a post gap of 700 nm would produce in place
of the 630 nm the paper quotes.

| post gap | κ | peak reflectivity | bandwidth |
|---:|---:|---:|---:|
| 630 nm, as quoted | 2.747 cm⁻¹ | 0.913, target **fails** | 16.55 GHz, target **fails** |
| **700 nm** | **1.862 cm⁻¹** | **0.748**, target passes | **12.84 GHz**, target passes |

The measured logarithmic decay of κ with the gap is 5.55 µm⁻¹ on this
cross-section, so 70 nm is a factor of 1.48, which is the residual to within the
precision of either figure. Both mirror targets are met exactly at that gap, and
the reflectivity lands on 0.748 against the 0.75 the paper quotes.

The most economical reading of the whole 2.15 is therefore that the closed-form
Fourier coefficient overstates the third harmonic by 1.42, which is measured, and
that the gap on the fabricated device is about 70 nm wider than the drawn figure,
whether through process bias or through the quoted dimension being the drawn one.

**This is a reading and not a measurement.** No independent evidence of the
fabricated gap exists here. The alternative candidates remain the two-dimensional
reduction under which the profile ratio was measured differing from the
three-dimensional device, and any other error in the coupled-mode construction.
The `cd_vernier` monitor drawn by the reticle stage is what would settle it on a
returned wafer, and the κ ladder spanning 530 to 730 nm is what would bracket it.

One assumption is carried by the adoption. The ratio was measured on the
two-dimensional effective-index reduction and is applied to the
three-dimensional value. The smoothing length is longitudinal and the
longitudinal profile is identical in both, so it is expected to transfer. It is
expected to transfer, and it has not been shown to.

#### The remaining suspect, eliminated: Δn_eff checked by finite elements

The coupled-mode construction takes Δn_eff from the mode solver and Fourier
analyses it. Two candidates therefore stood behind the over-prediction: the
construction itself, and the Δn_eff supplied to it. The second has now been
tested by re-solving the identical cross-section with an unrelated numerical
method, the `fem` stage carrying full-vectorial finite elements on a conforming
triangulation.

| quantity | finite difference | finite element | disagreement |
|---|---:|---:|---:|
| n_eff, bare ridge | 1.793880 | 1.793489 | −2.2 × 10⁻⁴ (fractional) |
| **Δn_eff from the Bragg posts** | **1.11870 × 10⁻³** | **1.09585 × 10⁻³** | **−2.0 %** |
| confinement in the film | 0.7169 | 0.7157 | −0.17 % |

The comparison is resolved rather than merely favourable. Halving the mesh
density moves the finite-element index by 8.0 × 10⁻⁵, which is one fifth of the
3.9 × 10⁻⁴ separating the two solvers, so the disagreement exceeds the mesh
error of the instrument measuring it.

**Δn_eff is therefore confirmed to within 2.0 %, and cannot account for an
over-prediction of a quarter to a half.** The whole of that factor belongs to
the coupled-mode construction, and the split between model and geometry given
above stands unaltered.

The check carries more weight on the sloped cross-section than it did on the
vertical one. A finite-difference solver represents a 77° wall as a staircase on
a structured mesh; the finite-element mesh conforms to the edge exactly. The
staircase is the approximation most likely to be exposed by a sloped wall, and
the two solvers still agree on Δn_eff to two per cent. The figures above were
re-derived at 77°; those recorded before 2026-08-04 were taken at 90° and gave
2.6 × 10⁻⁴ and 1.8 % respectively.

Two further quantities are obtained, neither of which the finite-difference
solver is able to report:

* **Polarisation purity 0.9965.** The semi-vectorial operator assumes unity. The
  minor transverse component carries 0.35 % of the energy on this cross-section,
  so the assumption is supported here. It is a property of the cross-section and
  not of the solver, and is to be re-measured on any section that is more
  strongly hybridised.
* **The anisotropy bracket, 0.064 wide in n_eff.** The finite-element solver
  carries one scalar permittivity per element, so it was run at each principal
  index of the film in turn. The two solves are 0.064 apart, which is the
  birefringence of the film seen through the mode. Weighted by the polarisation
  purity, the scalar model accounts for approximately 2.3 × 10⁻⁴ of the residual,
  which is well over half of the 3.9 × 10⁻⁴ disagreement observed. The agreement in
  absolute n_eff is consequently of a lower standing than the agreement in
  Δn_eff, where the two cross-sections share both the mesh and the permittivity
  model and the systematic part cancels.

### 2. The simulated bandwidth reported in the paper falls below the transform limit

Independently of the computed κ, the simulated pair reported in the paper (75 %
reflectivity, 6.5 GHz FWHM) is not self-consistent for a 7.25 mm uniform grating:

* R = 75 % ⇒ κL = 1.317 ⇒ FWHM = **12.7 GHz** by the TMM implemented here.
* The narrowest FWHM attainable by *any* uniform 7.25 mm grating, at n_g = 2.216,
  is the κ→0 sinc limit 0.886·c/(2·n_g·L) = **8.27 GHz**.

A value of 6.5 GHz is therefore unattainable at the stated length. The measured
8 GHz falls essentially at the transform limit, which would in turn imply a very
weak grating (κL ≲ 0.3, R ≲ 9 %). Such a grating is inconsistent with the 30 %
measured off-chip reflectivity. A close-in sidelobe is itself noted in the paper
and attributed to "a local distortion of the grating Bragg period, possibly due
to height variations of the LiNbO₃ thin film". A period distortion shortens the
*coherent* grating length, by which the response is broadened and the peak
lowered. Both quantities are thereby moved in the direction required, although an
effective length has not been fitted here.

This condition is flagged rather than resolved. Access to the raw data of the
authors is required. The quantity `grating.transform_limit_fwhm_GHz` is now
carried by the chain, and a warning is raised whenever a computed bandwidth falls
below the floor, so that the check is applied to every design from this point
onward.

### 3. Mode-hop-free range of 3.85 GHz against a measured 10 GHz

This is the miss of greatest consequence for the radar, and it is only partly
attributable to the κ discrepancy.

A **Pockels lever** of r = τ_DBR/τ_rt = **0.326** is computed by the chain: only
33 % of the round-trip delay resides within the electro-optically tuned grating.
The remainder is contributed by the RSOA and by the passive feed, neither of
which moves when voltage is applied. Two consequences follow:

* the laser tunes at r × the mirror rate, giving 269 MHz/V against the mirror
  rate of 708 MHz/V;
* the mirror slips against the mode comb at (1−r) × its own rate, so that a hop
  is incurred. The mode-tracking computation, which follows the lowest-threshold
  mode across the voltage sweep and is the figure reported by `verify`, places
  the hop at 3.85 GHz. The closed form r/(1−r) × FSR/2 is optimistic because it
  assumes a hop only at the half-FSR crossing, whereas the mirror peak is broad
  enough that the adjacent mode takes the lower threshold before that point is
  reached.

A point worth isolating, since it runs against intuition: the lever **fell**
from 0.389 to 0.326 when the sidewall was corrected, and the mode-hop-free range
**rose** from 2.84 to 3.85 GHz. A stronger grating turns the light sooner, so
the penetration depth fell from 1.67 to 1.27 mm; that shortens the delay inside
the mirror, which lowers the lever, and shortens the round trip, which raises
the free spectral range from 15.7 to 17.4 GHz. The excursion depends on both,
and here the second effect dominates. Neither the lever nor the free spectral
range predicts the tuning range by itself.

The *laser* and the *mirror* tuning efficiency are both reported in the paper as
550 MHz/V, which requires r → 1. With a weaker grating (κL = 1.36,
L_pen = 2.34 mm) the lever rises to 0.471. The improvement is
insufficient, unity remaining distant. Attaining r ≈ 0.9 requires the non-grating delay to fall to
approximately one ninth of the grating delay, that is, an RSOA of a few hundred
micrometres and a feed section of comparable order.

Two readings are possible, and they cannot be distinguished by the chain from the
paper alone. Either the RSOA and feed lengths are considerably shorter than the
1 mm each assumed here (neither is stated in the paper), or the reported 10 GHz
continuous range involves co-tuning of the RSOA drive current, which is described
in the paper as the second control parameter. **The same design action follows
from both readings**, so progress is not blocked by the ambiguity:

> The ratio (grating group delay) : (all remaining delay) is to be treated as a
> primary design variable of the TFLT chirped laser. Both the tuning efficiency
> and the mode-hop-free range are set by it, and it is fixed at layout time.

For this reason `D1a_edbr_tflt_chirp` is initialised with a 500 µm RSOA, a 400 µm
feed and a 12 mm grating, rather than by copying the baseline geometry.

## The Input Taper

The taper is evaluated separately, the stage being disabled by default on
account of its cost. It carries the mode from the 0.4 µm tip at the facet to the
1.0 µm ridge over 150 µm, both figures being taken from the paper.

```
$ picchain run ../examples/edbr_tfln_baseline/design.yaml --stages taper \
      --set taper.enabled=true
```

| quantity | result |
|---|---|
| n_eff at the tip / at full width | 1.7005 / 1.7865 |
| guided modes, along the whole length | 1 |
| conversion into a higher-order guided mode | 0, no second guided mode existing |
| minimum adiabaticity margin | **2.74** |
| width at which that minimum occurs | 0.425 µm |
| beat length against the slab at that width | 38.7 µm |

**The taper is single-moded from end to end, so the only loss channel available
to it is radiation, and radiation is precisely what a guided-mode basis cannot
compute.** The computed conversion loss is therefore zero by construction, and
it is not to be read as an insertion loss of zero. The figure is supplied by the
time-domain solve below.

The quantity that does carry information is the adiabaticity margin, which
compares the rate at which the guide changes against the beat length with the
slab. A margin well above unity denotes a section through which power follows
the local mode; a margin of order unity denotes a section that radiates. The
minimum obtained is 2.74, against the value of 10 used here as the floor, and it
occurs at the narrow end where the mode is weakly confined and the beat length
is longest.

The margin locates the narrow end as the section to examine. It does not by
itself establish that power is lost there, for the reason set out below. Where a
margin of this order is obtained, the time-domain stage is to be run rather than
the taper lengthened.

### The Radiation, by Time-Domain Solve

Quantifying the radiation requires a solver that carries the continuum. The
`fdtd` stage supplies it, <span style="color:#1a73e8"><strong>meep</strong></span> being executed in a separate environment.

```
$ picchain run ../examples/edbr_tfln_baseline/design.yaml --stages fdtd \
      --set fdtd.enabled=true
```

The model is two-dimensional by effective index, the two indices being solved
from the same cross-section the rest of the chain uses: 1.8660 through the ridge
and 1.6606 through the unetched film either side. Only the lateral channel is
therefore represented.

| resolution (px/µm) | transmission into the fundamental | total flux transmitted | reflection | loss (dB) |
|---:|---:|---:|---:|---:|
| 14 | 0.99831 | 0.99936 | 2.7 × 10⁻⁴ | 0.0073 |
| 20 | 0.99910 | 0.99919 | 2.8 × 10⁻³ | 0.0039 |
| 32 | 0.99942 | 0.99888 | 2.9 × 10⁻³ | 0.0025 |

**The taper is adiabatic in the lateral channel.** The loss falls monotonically
as the resolution rises, which is the signature of a numerical floor rather than
of a physical loss. Two further observations fix the accuracy of the statement.
The transmitted flux and the transmitted fundamental mode disagree by
approximately 5 × 10⁻⁴ at the finest resolution, the flux falling below the mode
amplitude, which is unphysical and therefore measures the residual error. The
normalisation run itself transmits 0.9964 of its own input, which is a further
0.36 %.

The correct statement is accordingly an upper bound rather than a value: the
lateral radiation of this taper is **below approximately 0.015 dB**, that bound
being set by the consistency of the solve and not by any loss the solve
resolves.

**This contradicts the pessimistic reading of the adiabaticity margin, and the
time-domain solve is the arbiter.** A margin of 2.74 was obtained above, and a
margin of that order was initially treated as indicating a section that
radiates. It does not, and the reason is that the criterion takes no account of
the overlap with the state into which power would be lost: a symmetric taper
couples only weakly to the symmetric radiation continuum. The margin is retained
as a screen, its default floor has been lowered to 3, and the warning now
directs the reader to this stage rather than to a redesign.

Two matters remain open, and neither is closed by the figures above:

* the vertical radiation channel is absent from a two-dimensional model. It
  requires `fdtd.dimensions: 3`, which is implemented and is a question of run
  time rather than of capability;
* the 1.5 dB per facet carried in `design.yaml` covers the chip-to-chip
  interface as a whole, of which the taper is one part. The taper is now shown
  not to be the dominant term in the lateral plane.

## Reproduction

```bash
cd design-chain
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml

# the two sensitivity studies quoted above
./.venv/Scripts/python.exe -m picchain.cli sweep ../examples/edbr_tfln_baseline/design.yaml \
    --param grating.post_gap_um --values 0.63,0.68,0.73,0.77,0.80,0.85 \
    --stages grating \
    --metric mode.dn_eff_posts,grating.kappa_per_cm,grating.kappa_L,grating.peak_reflectivity,grating.fwhm_GHz \
    --out ../examples/edbr_tfln_baseline/sweep_post_gap.json

./.venv/Scripts/python.exe -m picchain.cli sweep ../examples/edbr_tfln_baseline/design.yaml \
    --param platform.sidewall_deg --values 90,85,80,77,70,60 --stages grating \
    --metric mode.n_eff_bare,mode.dn_eff_posts,grating.kappa_per_cm,grating.kappa_L,grating.peak_reflectivity,grating.bragg_wavelength_nm,grating.fwhm_GHz \
    --out ../examples/edbr_tfln_baseline/sweep_sidewall.json

# the finite-element cross-check of the cross-section (about 2 min, four solves)
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml \
    --stages mode,fem --set fem.enabled=true

# the gap at which the published reflectivity is recovered
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml \
    --set grating.post_gap_um=0.762 --tag gap762

# the process window, which now includes the sidewall angle
./.venv/Scripts/python.exe -m picchain.cli corners ../examples/edbr_tfln_baseline/design.yaml
```

## Assumptions Not Stated in the Paper

Each of the following is annotated `# ASSUMPTION:` within `design.yaml`. They
constitute the first candidates for replacement with measured data.

| assumption | value adopted | significance |
|---|---|---|
| sidewall angle | **77°**, sourced 2026-08-04 to the open Luxtelligence `lnoi400` kit for the same stack. It was 90°, which the process cannot deliver | 35 % of κ against the former value, and 4.3 nm on λ_B. It remains an assumption about *this* device, that kit describing a different fabricator |
| RSOA length | 1000 µm | sets the Pockels lever, and hence the MHF range and tuning efficiency |
| RSOA group index | 3.6 | as above |
| feed waveguide length | 1000 µm | as above |
| RSOA internal loss | 10 cm⁻¹ | sets the threshold gain, and hence the linewidth |
| linewidth enhancement α | 3.0 | linewidth scales as (1+α²) |
| n_sp | 2.0 | both linewidth and SMSR scale with it |
| propagation loss | 0.2 dB/cm | second-order in this context |
| electrode width | 20 µm | affects capacitance and RC bandwidth only |

## The Re-Baseline of 2026-08-04

Two corrections were applied on the same day and every figure in this document
was re-derived. Both are recorded here because the second was exposed by the
first, and because their effects on the verdict run in opposite directions.

**The sidewall angle, 90° to 77°.** Set out under miss 1 above. It raises κ by
35 % and moves the excess over the paper from ×1.60 to ×2.15.

**The propagation loss, which was acting as gain.** The loss entered the complex
detuning of the coupled-mode solution with the sign of a gain. The reflectivity
therefore *rose* with loss instead of falling, and the two evaluation paths in
`picchain.tmm`, the closed form and the piecewise cascade, disagreed about which
sign that was.

| κL | R at 0.2 dB/cm, as computed before | R correctly |
|---:|---:|---:|
| 2.10 | 0.9569 | 0.9279 |
| 2.84 | 1.0034 | 0.9749 |
| 3.17 | 1.0064 | 0.9826 |

The error was invisible while the coupling was moderate. At the κL of 2.10 that
this design carried until today it displaced the reflectivity by 0.029, which no
target resolved. It became visible only when the sidewall correction raised κL
past 3, at which point a process corner returned a reflectivity of 1.0034 on a
passive grating.

Three properties of the defect are worth separating.

1. **It was surfaced by an unrelated correction.** Nothing was looking for it.
   Improving one input pushed the model into a regime where a second error
   violated a bound.
2. **The existing test could not have found it.** A test comparing the two
   evaluation paths at real detuning was already present and passing. For a real
   detuning the two conjugate conventions give the same reflected magnitude, so
   that test passes under either and distinguishes nothing. The disagreement
   exists only when the detuning is complex, which is to say only when a loss is
   present.
3. **The invariant that would have caught it was not being checked.** A passive
   grating cannot reflect more than it receives. This is now enforced twice: as
   a test across κL and loss, and as a runtime condition in the `grating` stage
   that raises rather than warns, a value above unity meaning the model is wrong
   rather than the design.

The reflectivity previously recorded for this baseline, 0.957, was therefore
inflated by the loss-sign error. At 90° with the correct sign it is 0.928.

## The Geometry This Document Describes

Sections above this point describe the **published** geometry, which is what the
validation exercise set out to reproduce: a 630 nm post gap on a 1.00 µm ridge
with a 200 nm etch. Sections below describe the **candidate**, which departs from
it in order to meet the declared targets.

| | published, `design.yaml` | candidate, `design_candidate.yaml` |
|---|---|---|
| post gap | 630 nm | **855 nm** |
| ridge width | 1.00 µm | 0.90 µm |
| etch depth | 200 nm | 210 nm |
| sidewall | not stated, assumed 77° | 77° |
| grating length | 7250 µm | 11000 µm |
| profile smoothing | — | **0**, withdrawn 2026-08-10 |
| period | 1.27979 µm stated | **1.302 µm**, fixed to the 1 nm grid |

**The departure at the post gap is 36 % and it is the third movement of that
parameter.** The chain asserts that the candidate geometry works. It does not
assert that it is the paper's, and no claim of replication attaches to the
grating.

## The Coupling Constant, Measured Twice and Converged

**This is the principal result of the exercise and it supersedes every earlier
statement about kappa in this document.**

The coupled-mode coupling constant is obtained here from a closed-form Fourier
coefficient of a rectangular longitudinal index profile. The photonic band gap
of the identical two-dimensional structure is an independent route to the same
quantity, computed by <span style="color:#1a73e8"><strong>MPB</strong></span>, and it assumes nothing about the profile.
It carries no radiation channel, so a disagreement between the two cannot be
radiation.

Two geometries were measured at resolution 40, each with the convergence guard
satisfied.

| | post gap 820 nm | post gap 855 nm |
|---|---:|---:|
| run | `20260809-193521-BANDS40` | `20260810-223801-BANDS855` |
| kappa from the band gap | 1.8803 /cm | 1.5661 /cm |
| kappa from coupled-mode theory | 1.6195 /cm | 1.3224 /cm |
| **ratio, band gap over coupled mode** | **1.161** | **1.184** |
| mesh shift, resolution 20 to 40 | 0.0850 /cm | 0.0669 /cm |
| the effect being measured | 0.2608 /cm | 0.2437 /cm |
| guard resolved | yes | yes |
| cost | 3.2 h | 2.7 h |

**Coupled-mode theory with the closed-form coefficient understates kappa by 16 to
18 % on this structure.** The two geometries agree, the guard is satisfied in
both, and the residue is attributable to the coupled-mode approximation itself.
It is stated here and it is not absorbed into any fitted parameter.

Resolution 40 was necessary. At resolution 20 the guard refused the comparison,
the mesh moving kappa by 0.220 /cm against a difference of 0.346 /cm, which is
64 % of the effect. Three earlier attempts at lower resolution produced verdicts
that were withdrawn.

### The comparison was wrong for three days, and the correction changed the design

A longitudinal profile smoothing of 57.1 nm was carried from 2026-08-07, and a
value of 42.86 nm briefly replaced it on 2026-08-09. Both were calibrated to
reconcile the two routes. Both rested on a comparison that was not like for like.

The two-dimensional reduction inside the `fdtd` stage called the Fourier
coefficient with four of its six arguments. The trailing two, the period and the
smoothing, defaulted to zero. **One side of the comparison therefore applied the
smoothing the design declared and the other applied none**, and no output said
so. The disagreement that resulted was attributed to the physics and a
correction was fitted to close it.

With the arguments supplied the disagreement reverses sign. The band gap lies
above the coupled-mode value, not below, so every non-zero smoothing makes the
agreement worse:

| smoothing | coupled-mode kappa | ratio |
|---|---:|---:|
| 0 nm | 1.6195 /cm | 1.161 |
| 42.86 nm | 1.3357 /cm | 1.408 |
| 57.10 nm | 1.1505 /cm | 1.634 |

Both calibrations were withdrawn. `grating.profile_sigma_um` is now zero, and it
is zero because no measurement supports a non-zero value rather than because the
profile is believed rectangular.

**The consequence was not favourable and was reported before it was addressed.**
Withdrawal raised kappa from 1.276 to 1.796 /cm, which put peak reflectivity at
0.903 against a bound of 0.90 and the linewidth at 5.572 kHz against 5.6. The
design did not meet its targets on the best-supported physics, and every earlier
pass had been obtained with a correction factor the measurement does not support.

Recovery was made in the geometry and not in the factor. The coupling is
exponential in the post gap at about 5.45 /um, so 35 nm is 16 % of kappa, and the
figure was computed from that decay rate before it was simulated. Opening the gap
from 820 to 855 nm returns kappa to 1.479 /cm and every target to its bounds with
margin. Choosing a different smoothing would have achieved the same numbers and
would have been the prohibited move; it would have looked identical in the metric
tree.

**The departure from the published device is now large.** The paper states a
630 nm post gap and this design carries 855 nm, a difference of 36 %. The chain
asserts that this geometry works. It does not assert that this geometry is the
paper's, and no claim of replication attaches to the grating.

## Defects Identified in the Chain by This Exercise

The following are recorded because they constitute the justification for
performing the baseline.

1. The truncated BOX above the silicon handle was included in the optical window,
   so that substrate modes at n_eff = 3.28 were returned by the solver. Resolved:
   the handle is now present for the RF problem only.
2. Blanket layers were drawn exactly to the window edge, so that the boundary
   column was sub-pixel-averaged to a half-empty state. The lateral-guidance
   floor was consequently obtained as 1.556 rather than 1.660, and four slab
   continuum states were miscounted as guided modes. Resolved: blanket layers now
   extend 1 µm beyond the window.
3. Capacitance was in error by a factor of 10⁶, arising from a spurious unit
   conversion (E expressed in V/µm and dA in µm² already cancel).
4. The electrostatic window was undersized for the fringing field, under-reading
   the capacitance by approximately a factor of four (RC bandwidth 14.5 GHz →
   3.7 GHz). The result remains an upper bound.
5. Electrode polarity produced a negative Γ, which propagated into an infinite
   Vπ·L and a voltage sweep of zero length.
6. The emitted mask carried 400 of 5665 grating periods by default, and nothing
   reported the difference. The default was corrected to draw the whole device
   on 2026-08-06, the saving having been measured at 1.5 s. Every geometric figure produced from it, being the
   rule verdict, the polygon counts, the connected-region counts, the density
   and the electrode length, described a 512 µm grating while the physics
   described a 7250 µm one. Resolved: `layout.mask_is_complete` is reported on
   every run, a warning names the shortfall, and `layout.require_complete`
   refuses the partial mask outright.
7. Two mask files were written by two independent backends on every run and
   never compared. Resolved: their exclusive-or is taken layer by layer. The
   residual on the validation baseline is exactly zero at full scale, so the
   agreement is now evidence rather than an assumption.
8. The second layout backend was silently lost after the first emission within
   one process, its cell library refusing a repeated name. The metric recorded
   the backend as unavailable, which is also what an uninstalled backend
   records, so the condition was indistinguishable from an absent dependency.
   The corner study, which emits seven times, cross-checked its first corner and
   none of the others. Resolved: the library is cleared before each emission,
   and all seven corners now compare.
9. `--set` could not clear an optional field to null, so `layout.draw_periods`
   could not be set to draw the whole grating from the command line. The
   coercion applied the type of the field's present value to the new one.
   Resolved, together with an ordering error by which a boolean field was
   coerced as an integer, `bool` being a subclass of `int`.
10. A dotted path could not reach into a mapping, so a per-layer quantity such
    as `process.bias_um.WG` could be neither probed nor varied across corners.
    That is precisely the quantity a critical-dimension corner displaces.
    Resolved: the traversal handles attributes and mapping keys alike.
11. The propagation loss entered the coupled-mode solution with the sign of a
    gain, so reflectivity rose with loss and passed unity at strong coupling. The
    two evaluation paths disagreed about which sign was the loss, and a test
    comparing them at real detuning could not detect it, both conjugate
    conventions giving the same magnitude there. Set out in full under "The
    Re-Baseline" above. Resolved, with the passive-grating bound now enforced as
    a test and as a runtime condition.
12. The finite-element solve was posed under the natural boundary condition of
   the curl-curl formulation, which is a magnetic wall and forces the tangential
   *magnetic* field to zero at the window edge. A film reaching that edge is
   incompatible with it, and the solver lost 4 × 10⁻³ in effective index against
   the analytic slab, which is a hundred times the error of the finite-difference
   solver on the same problem. Resolved: the electric wall is imposed, matching
   the condition the finite-difference solver applies to its dominant component.
   The defect is recorded because it presents as a plausible number rather than
   as a failure, and a cross-check reporting it would have been read as a
   disagreement between methods.

13. The band-structure cross-check ran without a convergence guard and reported a
    verdict from a single unconverged solve, attributing a disagreement of 1.63
    to the coupled-mode construction in a warning. Refining the mesh moved the
    measured κ by more than the disagreement being claimed. A gap that is 5 × 10⁻⁵
    of the band frequency is the difference of two nearly degenerate eigenvalues,
    and the discretisation error is carried by each separately and does not
    cancel. The guard now exists, the warning is gated on it, and the verdict was
    withdrawn. Recorded as lesson T018.

14. The <span style="color:#1a73e8"><strong>MPB</strong></span> resolution was passed in the wrong unit. `fdtd.resolution` is declared
    as pixels per micrometre and the MPB lattice unit is the grating period, so
    every band-structure solve the chain ever performed ran at 1/1.28 of the
    density requested. The subpixel-averaging sub-grid was also left at its
    default of 3 and the eigensolver tolerance at 10⁻⁷, neither being adequate to
    a quantity formed as the difference of two eigenvalues.

15. The facet stage applied `facet.offset_x_um` with the wrong sign. The field
    displaces the partner mode in the overlap integral, so declaring the offset
    that compensates a walk-off moved the partner away from the beam rather than
    onto it. Declaring the correct compensation of 0.489 µm raised the coupling
    loss from 3.12 dB to 3.73 dB instead of removing the 0.61 dB penalty. The
    overlap now sees the residual between where the beam lands and where the
    partner is placed.

16. The walk-off penalty was computed from a closed form requiring both modes to
    be Gaussian. The guide mode on a shallow-etched ridge is not Gaussian, and
    the approximation understated the cost by 25 %. The penalty is now the ratio
    of the overlap at the residual to the overlap with the partner centred, which
    closes exactly against the reported totals.

17. The layout deducted a taper length at each end of the feed waveguide, but the
    output taper lies beyond the mirror and is outside the cavity. The drawn
    facet-to-grating distance was therefore one taper length shorter than the
    distance the round-trip delay was computed from, by 15 % at the declared
    lengths. Raising the taper to the 450 µm its cited reference gives would have
    made the discrepancy 45 %.

18. The cavity stage swept the drive voltage without a ceiling while searching for
    the mode hop, reaching 69.3 V against the 20 V the paper reports the
    electronics delivering. A tuning range was reported that no supply on the
    bench could produce. `electrodes.max_drive_voltage_V` now clamps the sweep and
    the stage states whether the range it found was ended by the hop or by the
    limit.

19. The figure renderer caught every exception while reading the metric tree,
    including the `NameError` raised by a module that had never imported `json`.
    A figure was silently omitted rather than failing. The exception is now
    narrowed to the two conditions actually anticipated.

20. The cavity mode finder inverted the round-trip phase by interpolation, which
    assumes that phase increases with frequency. It does not. A Bragg mirror's
    phase steps by pi at each sidelobe null, so the round-trip group delay dips
    to −2733 ps across 5.5 % of the scanned band. `np.interp` returned a wrong
    root in silence, and the tracked laser mode jumped discontinuously, by 4 GHz
    on the baseline and by 12 GHz on a short-cavity variant. Every root is now
    found by bracketing a sign change, roots landing where the mirror does not
    reflect are discarded, and the mode is followed by continuity of frequency
    rather than by index alone.

    The baseline figure of 3.80 GHz is unchanged, its measured window having
    contained no jump. Configurations with a shorter cavity were wrong by up to a
    factor of 4.5: the 500 µm / 200 µm configuration read 2.32 GHz and delivers
    10.60 GHz. The defect therefore concealed the only route by which this design
    reaches its declared mode-hop-free range.

21. The layout clamped an infeasible geometry rather than refusing it. The feed
    length is the facet-to-grating distance and the taper is drawn inside it, so
    a feed shorter than the taper describes nothing. A 10 µm stub was drawn and
    nothing was reported, and the drawn cavity then bore no relation to the delay
    the cavity stage computed. The case arises exactly when the cavity is
    shortened to widen the mode-hop-free range, so it was reachable by the
    ordinary use of the design controls.

22. Introduced while correcting defect 20, and found the same day. The
    reflectivity floor added to discard spurious roots at the sidelobe nulls was
    applied to the side-mode search as well as to the mode tracking. Where the
    free spectral range exceeds the mirror bandwidth the neighbouring mode falls
    outside the stop band, the floor removed it, and the side-mode suppression
    was reported as NaN. That is the single-mode-by-construction case and is the
    most favourable configuration the design admits, so the metric returned a
    value indistinguishable from a failure precisely where the device is best. A
    target on that metric would have carried the NaN to an error.

    The side mode is now taken from the mode adjacent in index wherever it lies,
    the floor being applied only to the tracking. A neighbour outside the band is
    suppressed by the mirror rolloff rather than absent, and suppression is the
    quantity being measured. The metric reports 52.3 dB with the neighbour in
    band and 50.2 dB with it outside, the latter saturating at the spontaneous
    emission floor.

    The general point is that a filter introduced for one consumer of a
    computation was inherited by a second consumer for which it was wrong.

23. The mode-hop-free range was measured from zero bias, which made it a
    property of the arbitrary cavity phase at zero volts rather than of the
    design. At a 700 nm post gap the 1000 µm / 1000 µm cavity reported 0.37 GHz
    from zero bias and 6.86 GHz between hops, the laser happening to begin near a
    hop boundary. A design differing only in optical path length by a fraction of
    a wavelength reported an order of magnitude more.

    A DC offset places the laser wherever in its mode is wanted, so the span
    between hops is the quantity the design controls, and it is what the
    acceptance target means. The metric now reports the largest continuous span,
    the zero-bias span beside it, the number of hops in the sweep, and
    `bias_offset_needed` where the two differ.

    This is the third defect found in one metric. Two concerned how the
    resonance was solved and one concerns what was being measured. The last was
    the hardest to see, because every value it produced was a real excursion of a
    real mode.
