# Design Concept — Extended-DBR Pockels Laser, Validation Baseline

**Design:** [`design.yaml`](design.yaml)
**Report:** [`DESIGN_REPORT.md`](DESIGN_REPORT.md)
**Toolchain validation:** [`TOOLCHAIN_VALIDATION.md`](TOOLCHAIN_VALIDATION.md)

**This document states what the device does and by what principle. The
acceptance targets in `design.yaml` are derived from it, and §4 gives the trace
from each clause to the target that tests it.**

It exists as much to demonstrate the convention as to describe this device.
**Every design in this repository carries a concept document, and
`design-chain/tools/check_concept_trace.py` verifies that each declared target
appears in its trace table and each traced clause has a target.** The reason is
given in §5.

---

## 1. What the device is

A reproduction of the extended-DBR Pockels laser of Siddharth *et al.*,
*Nat. Photon.* **19**, 709 (2025), on 400 nm X-cut thin-film lithium niobate. It
is the chain's validation baseline: **the published device is the reference, and
the purpose of the design is to be compared against it rather than to be
optimised.**

That purpose sets the form of the targets. Each one brackets a published figure
with a stated tolerance, so a run either reproduces the paper within that
tolerance or it does not. A target here is a claim about the toolchain, not a
requirement on a product.

## 2. The principle of operation

### 2.1 What sets the lasing frequency

The laser oscillates where two conditions meet.

* **The round-trip phase is a multiple of 2π.** The frequencies satisfying this
  are the cavity mode comb, spaced by the free spectral range.
* **The mirror returns enough light.** The Bragg grating reflects over its stop
  band, and the comb line nearest the peak has the lowest threshold.

An InP reflective gain chip supplies the gain and one cavity end. The grating
etched into the niobate film supplies the other, and the length of film the
light penetrates before turning around is what makes the cavity long.

### 2.2 Where the narrow linewidth comes from

The Schawlow-Townes-Henry linewidth falls with the square of the **active
fraction**, which is the share of the round-trip delay spent inside the
semiconductor:

    F = tau_soa / tau_rt

A deep Bragg penetration lengthens `tau_rt` without adding spontaneous emission,
so `F` falls and the linewidth falls with it. **The extended cavity is the
linewidth mechanism**, and the grating strength is the control on it.

### 2.3 What tuning does

Voltage on electrodes flanking the grating changes the film index through the
Pockels effect, which slides the stop band. The comb is set by the whole
round-trip path, so only the fraction inside the tuned mirror follows:

    r = tau_dbr / tau_rt

The mirror moves at `S` and the laser follows at `r*S`, and the difference is a
slip of the mirror across the comb. **The slip ends the continuous sweep**, by a
mode hop once it reaches one free spectral range.

### 2.4 The trade the design sits on

The grating strength moves the two headline quantities in opposite directions. A
weaker grating gives a deeper penetration, so a longer cavity, so a lower active
fraction and a narrower linewidth; it also gives a narrower stop band and a
weaker mirror. **The baseline sits where the published device sits**, and the
post-gap ladder in the sweeps records the trade rather than resolving it.

## 3. The quantities the concept commits the design to

| the concept says | the quantity that expresses it |
|---|---|
| the mirror sits under the gain peak | Bragg wavelength |
| the mirror returns enough light to oscillate | peak reflectivity |
| the stop band admits the intended excursion | stop-band FWHM |
| the sweep is electrically driven | mirror tuning `S` |
| the electrode is efficient | V_pi L |
| the drive does not absorb the mode | mode overlap with metal |
| the continuous sweep is wide enough | mode-hop-free range |
| the extended cavity delivers the linewidth | Schawlow-Townes-Henry linewidth |
| the device is single-frequency | guided modes, SMSR |
| the mask is manufacturable | rule-deck violations, mask completeness |

## 4. Trace from the concept to the acceptance targets

| clause | target metric | severity |
|---|---|---|
| §2.1 single transverse mode | `mode.n_guided_modes` | must |
| §2.1 the mirror sits under the gain peak | `grating.bragg_wavelength_nm` | must |
| §2.1 the mirror returns enough light | `grating.peak_reflectivity` | must |
| §2.3 the stop band admits the excursion | `grating.fwhm_GHz` | should |
| §2.3 the sweep is electrically driven | `eo.tuning_MHz_per_V` | must |
| §2.3 electrode efficiency | `eo.VpiL_ideal_V_cm` | should |
| §2.3 the drive does not absorb the mode | `eo.mode_overlap_with_metal` | must |
| §2.3 the continuous sweep is wide enough | `cavity.mode_hop_free_range_GHz` | should |
| §2.2 the extended cavity delivers the linewidth | `cavity.schawlow_townes_henry_linewidth_kHz` | should |
| §2.1 single-frequency operation | `cavity.smsr_dB` | should |
| manufacture | `drc.error_violations` | must |
| manufacture | `layout.mask_is_complete` | info |

## 5. Why the trace is checked mechanically

**A target carries a mechanism as well as a number.** Where a design replaces
the mechanism, the target stops testing the requirement and starts testing the
absence of the change, and it does so without any visible symptom: the run still
passes, the metric is still computed, and only a reader who holds the concept in
mind can see that the wrong question is being asked.

The shape of the case that produced this convention: a design gains an element
that removes a limiting mechanism rather than working within it. Its targets are
inherited from the design it supersedes, so the row carrying the requirement
still measures the mechanism that is no longer present. **The new design then
scores worse than its predecessor on the very quantity its new element exists to
improve**, and a share of the process window appears to fail. Re-derived from
its own concept it is the stronger device on that quantity.

The verdict inverts on which concept the target encodes, and not on any property
of the device. **Rereading the documents would not catch it**, because each
remains internally consistent; only comparing the targets against a written
statement of the principle exposes it. The worked instance is recorded in the
lessons ledger.

Two habits follow.

* **When the architecture changes, re-derive the targets from the new concept**
  rather than inheriting them. Where the old row still describes a real degraded
  mode, keep it at a lower severity so the degradation stays on the record.
* **Keep the trace machine-checked.** A prose cross-reference between two
  documents will drift, and the drift is invisible.
