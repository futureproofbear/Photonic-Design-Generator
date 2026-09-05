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

**C. Wang, Z. Li, J. Riemensberger, et al., "Lithium tantalate photonic
integrated circuits for volume manufacturing"**
*Nature* **629**, 784 (23 May 2024) &middot;
<https://doi.org/10.1038/s41586-024-07369-1>

The source of the thin-film constants held for lithium tantalate in
[`design-chain/pdk/materials.yaml`](../design-chain/pdk/materials.yaml). The
figures taken from it are the ordinary and extraordinary indices of 2.119 and
2.123, a birefringence of 0.004, and a modulation efficiency of 1.9 V cm at
1550 nm and 1.6 V cm at 1310 nm. Three propagation losses are reported and they
differ by a factor of three: 5.6 dB/m on unreduced material, 7.3 dB/m on the
wafer used for optical applications, and 17.1 dB/m on a mass-manufactured LTOI
substrate. The last is the figure a volume process is most likely to present,
and all three appear on the loss axis of
[`examples/ltoi300_ring/`](../examples/ltoi300_ring/README.md).

**Z. Li, A. Kotz, A. Schwarzenberger, C. Koos and T. J. Kippenberg, "Low
voltage and high-bandwidth thin-film lithium tantalate modulator on a silicon
dioxide substrate"**
arXiv:2604.14836 &middot; 16 April 2026

A travelling-wave modulator on a 100 mm fused-silica substrate, velocity
matched by a T-shaped segmented slow-wave electrode. The measured figures are a
3 dB electro-optic bandwidth of 64 GHz at a half-wave voltage of 1.53 V, an
electrical bandwidth of 100 GHz, a microwave loss of 4.6 dB/cm at 120 GHz, a
switching voltage constant down to 10 mHz, and a net single-lane rate of
440.6 Gbit/s under PAM8. It bears on electrode design on this platform and on
the bias stability that distinguishes lithium tantalate from lithium niobate.

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

**Luxtelligence LT-PRO design manual**
Obtained from the foundry under their terms and not redistributed &middot;
read 2026-09-03

The document that states what the vendor page omits. **Its content is not
reproduced here.** The working notes taken from it are held untracked at
`design-chain/pdk/LXT_LT_PRO/MANUAL_NOTES.md`, under the same exclusion as the
materials file and the rule decks, and a reader holding the manual can follow
every citation below from them.

What the manual governs, so that a reader knows what they are missing:

* the optical dispersion of the thin film and its radio-frequency permittivity,
  which are held in the untracked `materials_lt_pro.yaml` and reached through
  `platform.materials_file`;
* the layer numbers, the etch depths and the minimum widths, gaps, separations
  and enclosures, which reach a design through `layout.layer_map` and the
  `drc.rules` each design declares;
* the die footprints the process offers, which reach a design through
  `reticle.die_width_um`, `reticle.die_height_um` and
  `reticle.chip_frame.allowed_edges_um`;
* the wafer orientation, and the drawing guidance for edge couplers and for bend
  discretisation.

**Two corrections it made to the vendor-page entry above are recorded because
they are corrections to this repository rather than content of the manual.** The
5 by 5 mm multi-project die recorded from the vendor page is not a footprint the
process offers. And the 800 nm figure taken from that page is a minimum metal
width and not an electrode gap.

Individual figures drawn from the manual appear in the design files that use
them, each carrying its provenance, which is engineering use rather than
redistribution. Whether that line is drawn in the right place is a question for
the licensor and is flagged rather than assumed.

**ubcpdk, the same UBC process for gdsfactory**
<https://github.com/gdsfactory/ubc> &middot; <https://gdsfactory.github.io/ubc/>
&middot; MIT &middot; repository at 3.3.5, read 2026-09-03; release 3.3.4 installed
2026-09-05

The gdsfactory-native form of the SiEPIC EBeam kit below, and the one this
chain could drive directly, gdsfactory being the layout engine here. Its layer
map agrees with the KLayout kit in every position checked: the guide is 1/0,
the 150 nm slab 2/0, the heater metal 11/0, the router 12/0, the pad opening
13/0, `DevRec` 68/0 and the ports 1/10 and 1/11. It adds `WG2` at 31/0.

Its declared stack is 220 nm of silicon at a 10 degree sidewall, a 3.0 um
buried oxide, a 750 nm titanium-nitride heater, a 700 nm aluminium router and a
10 um substrate. Strip guides carry a 5 um minimum radius and the heater is
4 um wide.

**Two artifacts bear this kit's name and they are not the same.** The
repository at `main` is version 3.3.5 and requires `gdsfactory~=9.45.0`. The
latest release on the package index is 3.3.4 and requires `gdsfactory~=9.34.0`.
Everything above was read from the repository and describes 3.3.5. Anything
below attributed to the installation describes 3.3.4, which is what `pip` gives.

The heater figure alone was wrong when this entry was written, being 700 nm
here against the 750 nm both the repository and the release declare, and it is
corrected above. The version and the dependency constraint recorded here were
right, and were briefly and wrongly overwritten with the release's figures on
2026-09-05 before the repository was re-read.

The layer stack extrudes seven levels over four device layers and the layer map
declares sixteen names, and
[`examples/ubc_soi220_stack/`](../examples/ubc_soi220_stack/README.md) sets both
against the layers the cells draw.

**The two UBC kits disagree about the stack, and how much it matters was
settled on 2026-09-05.** The cross-section script of the KLayout kit grows a
2.0 um buried oxide against the 3.0 um declared here, and it makes the heater
metal 200 nm against 750 nm. A heater's resistance and its thermal time constant
both follow its thickness, so a design taking the figure from one kit and the
geometry from the other is wrong by a factor of 3.75 in the quantity that sets
the drive.

The oxide disagreement is worth nothing for the transverse-electric mode and a
factor of twelve thousand in substrate tunnelling for the transverse-magnetic
one, which is measured in
[`examples/ubc_soi220_stack/`](../examples/ubc_soi220_stack/README.md). The kit
ships four TM cells and they are the ones for which the two stacks are not
interchangeable.

**It cannot share an environment with the kits already installed, and it now
has its own.** The repository requires gdsfactory `~=9.45.0` and the release
requires `~=9.34.0`; this installation runs 9.48.0 for the Luxtelligence kit and
the layout stage, so neither admits it. `design-chain/.venv-ubcpdk/` holds the
release, being ubcpdk 3.3.4 on gdsfactory 9.34.2, and is excluded from version
control with every other environment. The kit is therefore run rather than read,
**and what is run is one version behind what is described above**.

**SiEPIC EBeam PDK, silicon on insulator by electron-beam lithography**
<https://github.com/SiEPIC/SiEPIC_EBeam_PDK> &middot; MIT &middot; read 2026-09-03

A third platform, and it is silicon rather than a Pockels material. It is held
here because it is open, because its rule deck and layer table are published in
full, and because its fabrication runs publish measurements, which is the one
thing the lithium tantalate work has no access to.

**Every figure below was reconfirmed on 2026-09-05** by cloning the repository
and reading `klayout/EBeam/xsect/EBeam_ANT.xs` and `klayout/EBeam/EBeam.lyp`
directly. The cross-section script grows the oxide at 2.0, the silicon at 0.22
with a 3 degree taper, the nitride at 0.4 with a 5 degree taper, the cladding at
2.2, the heater metal at 0.2 and the router at 0.7, and etches the pad opening
at 0.3. It binds `si` to 1/0 and `sin` to 4/0. The layer properties file names
2/0 "Si - 90 nm rib". The entry as first written was right on all of it.

*Stack*, from the cross-section script `EBeam_ANT.xs`: 220 nm silicon on a
2.0 um buried oxide at a 3 degree etch taper, an optional 400 nm silicon
nitride at 5 degrees, a 2.2 um cladding oxide, a 200 nm upper metal for
heaters, a 700 nm lower metal for routing, and a 300 nm etch to open a pad.

*Layers*, from `EBeam.lyp`: silicon 1/0, the 90 nm rib 2/0, nitride 4/0, oxide
open 6/0, text 10/0, the heater metal 11/0, the router metal 12/0, the pad
opening 13/0, the via 40/0, doping 20/0 and 24/0, floor plan 99/0, deep trench
201/0, keep-out 202/0, dicing 210/0, and the chip design area 290/0. The
verification layers are `DevRec` 68/0, `PinRec` 1/10 and `FbrTgt` 81/0.

*Rules*, from `drc/SiEPIC_EBeam.drc`: silicon at 70 nm minimum width and space,
nitride at 120 nm, the first metal at 3.0 um for both, the second at 5.0 um
width against 8.0 um space with a 3.0 um overlap onto the first, a pad opening
at 10.0 um, and 20.0 um from a deep trench to metal. Two checks are not
geometric: devices may not overlap on `DevRec`, and every device must sit
inside the floor plan.

*Cells*: directional couplers, a ring resonator, a taper and a Bragg grating as
parametric cells, with `Silicon.lbr` and `SiN.lbr` as fixed libraries.

*Fabrication*: Applied Nanotools NanoSOI by 100 keV direct-write electron-beam
lithography on 8-inch wafers, and the openEBL service, whose runs return
measured data. Applied Nanotools states that propagation loss is tracked on
every run by cut-back on 500 nm strip waveguides under 2.2 um of cladding.

**This platform is not to be confused with the two lithium platforms beside
it.** Silicon carries no Pockels effect, so a modulator on it is carrier-based
and none of the electro-optic figures of the LNOI400 or LT-PRO entries
transfers. The layer numbers differ in every position: silicon is 1/0 here,
2/0 on LN-CORE and 2/10 on LT-PRO.

The licence permits redistribution, and the kit is nonetheless installed rather
than vendored, on the same terms as every other PDK in
`design-chain/pdk/`.

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
