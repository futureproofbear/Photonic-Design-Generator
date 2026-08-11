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

## Process documentation

**Luxtelligence LNOI400 open process design kit**
<https://github.com/Luxtelligence/lxt_pdk_gf> &middot; MIT

Layer numbering, cross-sections, the 13° sidewall angle and the admissible die
footprints are read from this kit. It is installed rather than vendored; see
[`design-chain/PICCHAIN_REFERENCE.md`](../design-chain/PICCHAIN_REFERENCE.md).

**LN-CORE lnoi400 KLayout rule deck**

Obtained from Luxtelligence under their terms and not redistributed. Without it
the `drc` stage runs its declared rules only, which are a smoke test and not a
foundry check.
