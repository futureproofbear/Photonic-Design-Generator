# References

The literature and vendor documentation underpinning the validation designs.

**The documents themselves are not held in this repository.** They are the
copyright of their authors and publishers, and a supplier datasheet in
particular is not redistributable. Each is listed here with what is needed to
obtain it, and `.gitignore` excludes the files so that a copy placed in this
directory for local use is never committed.

## The validation baseline

**A. Siddharth, et al., "Ultrafast tunable photonic integrated Pockels
extended-DBR laser"**
arXiv:2408.01743 &middot; published as *Nature Photonics* **19**, 709–717 (2025)
&middot; <https://doi.org/10.1038/s41566-025-01660-x>

The device reproduced by `examples/edbr_tfln_baseline/`. Every geometric figure
in `design.yaml` is cited to this paper inline, and
[`TOOLCHAIN_VALIDATION.md`](../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md)
records where the chain agrees with it and where it does not.

## Supporting

**Thin-film lithium niobate electro-optic modulators**
arXiv:1902.08969 &middot; background on the platform and on electrode design.

## Vendor documentation

**LD-PD HP-GC-1550-1**, reflective semiconductor optical amplifier
<https://www.ld-pd.com/?a=cp3&id=653>

The gain chip the candidate design is built around: 1000 ±20 µm long, rear
facet 90 %, front facet 0.01 %, 40 mW at 200 mA, threshold 20 to 40 mA. The
datasheet is obtained from the supplier and **is not redistributed here**.

The figures taken from it are marked `SOURCED` in
[`design_candidate.yaml`](../examples/edbr_tfln_baseline/design_candidate.yaml),
and those inferred from it are marked `CALIBRATED`. The distinction matters: the
active-layer thickness of 24 nm is a three-well stack inferred from the
threshold, not a stated figure.

**SemiNex SOA/RSOA chip, COC and array**
<https://seminex.com/semiconductor-optical-amplifier> &middot; distributed in the
United Kingdom by AP Technologies

The C-band reflective SOA family. Part `CHP-286`, and its chip-on-carrier
variant `COC-286`, is the 1550 nm single-emitter gain chip: 2500 µm long,
500 µm wide, 4 µm aperture, curved waveguide, front facet below 0.1 %, rear
facet 98 %, 80 nm gain bandwidth, 1 A and 2 V operating point, −20 to 75 °C.
Gain is not quoted for the reflective parts; the companion SOA table gives 30 to
32 dB at 10 µW input with a 6 to 7 dB noise figure.

**The part is excluded from this design on delay grounds and not on
performance grounds.** The mode-hop-free requirement inverts to a bound on the
un-tuned round-trip delay, `tau_u < 1/(2*delta_nu)`, which is 50 ps at the
10 GHz target. A 2500 µm chip at a group index of 3.6 contributes 60.0 ps by
itself, so the bound is exceeded before the feed waveguide is counted and no
grating design recovers it. Substituted into the baseline delay budget the part
returns a lever of 0.257 and a mode-hop-free range of 1.72 GHz, against 0.401
and 4.59 GHz for the incumbent. The admissible gain-chip length at this target
is about 1900 µm with a 300 µm feed, and about 1470 µm with a 1000 µm feed.

### Gain-chip survey, 2026-08-12

Conducted after the ML4011 datasheet was found to describe a DFB laser rather
than a gain element. Recorded so that the search is not repeated.

| Supplier | C-band gain chip | Disposition |
|---|---|---|
| Modulight | none | `ML4011` is a 1545 nm DFB laser with 35 dB SMSR and supplies no cavity parameter. The gain elements in the catalogue, `ML5071` and `ML3307`, are 780 nm. |
| Innolume | none | The quantum-dot platform spans 780 to 1350 nm. The Type C gain-chip architecture is instructive, deep anti-reflection on the feedback facet against 5 to 15 % on the output facet, but no C-band part is offered. |
| SemiNex | `CHP-286` / `COC-286` | Specified in full above. Excluded at 2500 µm by the delay bound. |
| Thorlabs | `SAF1550` series | Single-angled-facet chips centred at 1550 nm, the ridge curved to meet the facet off-normal. The architecture matches the angled facet this mask draws. Length and confinement factor were not obtained; the product pages are script-rendered and the datasheet has not been retrieved. |
| LD-PD | `HP-GC-1550-1` | Retained. 1000 µm satisfies the delay bound with margin. |

Four parameters the `cavity.rsoa` block requires are published by no supplier
surveyed: confinement factor, internal loss, group index and the linewidth
enhancement factor. These remain assumptions in every candidate, and are marked
as such.

## Platform literature, thin-film lithium tantalate

**Mohanraj, Shi, Yang, Zhou, Zhu — integrated photon-pair sources on
periodically poled thin-film lithium tantalate.** arXiv:2605.24988v1.

A spontaneous-parametric photon-pair source on TFLT, reported as two devices: a
periodically poled straight waveguide on a 310 nm film with a 200 nm etch, and a
periodically poled racetrack on a 575 nm film with a 300 nm etch. Both are 2 um
wide. Pump at 783 nm, signal and idler at 1560 and 780 nm.

Held for three platform figures that are hard to obtain elsewhere.

**A demonstrated film and etch.** 310 nm with a 200 nm etch, oxide-clad, is
shown to be fabricable and to guide.

**A loss figure.** The racetrack returns an intrinsic Q of 1.11e6 at the
fundamental and 6.22e5 loaded. At a group index near 2.06 and 1560 nm these are
0.325 and 0.580 dB/cm through alpha = 2*pi*n_g/(Q*lambda). The guide is 575 nm
thick, air-clad and 2 um wide, so its mode meets the etched sidewall far less
than a thin, narrow ridge does; the figure is a floor for the platform rather
than a value transferable to another geometry.

**A thermal-budget constraint.** Periodically poled domains are reported to
revert in part after etching and PECVD, attributed to the 600 to 700 C Curie
temperature of lithium tantalate. Any TFLT process step with a comparable
thermal budget is to be assessed against this, whether or not the device uses
poling.

It reports no refractive index away from its own operating points, no r33 and no
electro-optic coefficient.

**Li, Kotz, Schwarzenberger, Koos, Kippenberg — low voltage and high-bandwidth
thin-film lithium tantalate modulator on a silicon dioxide substrate.**
arXiv:2604.14836v1.

A Mach-Zehnder modulator on a 600 nm LiTaO3 film with a 440 nm etch and a 160 nm
slab, transferred to fused silica, 1.5 um oxide cladding, 18 mm arms and a 5 um
electrode gap. **The most useful electro-optic reference on the platform so
far.**

**A half-wave voltage of 1.53 V at 1550 nm and 1.21 V at 1300 nm.** Through
Vpi*L = lambda*G/(n_e^3 * r33 * Gamma) at n_e = 2.115, this gives r33*Gamma of
29.7 pm/V read single-arm and 14.9 pm/V read push-pull. Half-wave voltages for
Mach-Zehnder modulators are conventionally quoted push-pull, and on that reading
the paper establishes r33 >= 14.9 pm/V, since Gamma cannot exceed one. Gamma is
not stated. **The paper's own convention is needed before this is quoted as an
r33 measurement.**

**A switching voltage constant down to 10 mHz**, with DC stability stated to
exceed lithium niobate's. This is the citation to use where a thermal or DC
operating point is relied on to hold, in place of an argument from the
photorefractive coefficient.

3 dB electro-optic bandwidth 64 GHz, 100 GHz projected; microwave loss 4.6 dB/cm
at 120 GHz; 440.6 Gbit/s PAM8 at 176 GBd; better than 95 % film-transfer yield
at 100 mm. Birefringence is given as 0.004 against 0.074 for lithium niobate,
which is a second source for the near-isotropy of the platform.

It tabulates no index against wavelength, states no r33 directly and reports no
propagation loss. It contains no grating, DBR or laser content.

## Process documentation

**Luxtelligence LNOI400 open process design kit**
<https://github.com/Luxtelligence/lxt_pdk_gf> &middot; MIT

Layer numbering, cross-sections, the 13° sidewall angle and the admissible die
footprints are read from this kit. It is installed rather than vendored; see
[`design-chain/PICCHAIN_REFERENCE.md`](../design-chain/PICCHAIN_REFERENCE.md).

**Luxtelligence LT-PRO, lithium tantalate on insulator**
<https://luxtelligence.ai/product/lt-pro/> &middot; retrieved 2026-08-16

The vendor page for the 300 nm TFLT platform. Propagation loss below 0.2 dB/cm,
electro-optic bandwidth above 110 GHz, Vpi*L about 2.2 V.cm in the O band.
Minimum waveguide width 250 nm and minimum electrode gap 800 nm. O-band, C-band
and visible operation, with high power handling quoted for 450 to 900 nm.
Multi-layer metal with on-chip RF terminations. 100 mm wafers, with 150 and
200 mm in progress. Multi-project runs take die of 5x5, 10x5 or 20x5 mm at
twelve copies or more, dedicated runs give a 2x2 cm design space, and the lead
time is 18 weeks.

**It publishes no refractive index, no r33, no electrode metallurgy, no
buried-oxide thickness and no process tolerances.** The Vpi*L figure is quoted
for the O band without the electrode gap or the overlap factor, so it cannot be
inverted for r33.

**LN-CORE lnoi400 and LT-PRO ltoi300 KLayout rule decks**

Obtained from Luxtelligence under their terms and not redistributed. Without one
the `drc` stage runs its declared rules only, which are a smoke test and not a
foundry check.

**The two decks are near-identical in rule values and differ in what they read.**
RIDGE is 2/0 on LN-CORE and 2/10 on LT-PRO, SLAB is 3/0 against 3/10, and the
first metal moves from 21/0 to 20/0. LT-PRO additionally carries
`M1.sep(RIDGE, 1.5 um)`, which LN-CORE has not, and declares the same three
supported outer die edges of 5050, 10100 and 20200 um.

**A design pointed at the wrong one of these returns a clean report rather than
an obvious failure**, because the rules find no geometry on the layers they
name. `drc.deck` reports which layers a runset names and which of them the mask
leaves empty, for that reason.
