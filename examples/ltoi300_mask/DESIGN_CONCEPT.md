# Concept: an instrument for the mask path, drawn on ltoi300

## 1. What this design is for

This design is an instrument rather than a device. Its purpose is to drive
stages 5, 6, 12 and 14 of the chain against the Luxtelligence LT-PRO ltoi300
process and to establish where the emission departs from what that process
requires. The optical function is subordinate to that purpose, and it is
chosen to be the smallest structure that puts every question under
examination onto a polygon.

Three properties are asked of the drawn object.

**It carries a guiding structure of the declared cross-section.** The stack is
a 300 nm lithium tantalate film on a 7 um buried oxide, etched 180 nm to leave
a 120 nm slab, with a 70 degree sidewall and a 2 um cladding, on an x-cut
wafer. The guide is a 0.7 um ridge operated at 1310 nm. Single lateral-mode
operation is required, because a multimode guide would make the drawn width
unrepresentative of the width the process is asked to print.

**It carries a grating.** The manual reserves layer 2/11 for small repeating
features such as a Bragg reflector or a photonic crystal, and the question of
whether the chain can reach that layer is answered only where a repeating
feature exists. A third-order mirror is drawn, because a first-order mirror at
1310 nm asks for a longitudinal gap the process forbids, and that finding is
itself part of the study.

**It carries a die.** The exclusion zone, the admissible footprints, the
reserved corners and the edge-coupler placement rule are properties of a die
and cannot be tested against a device cell. The reticle stage is therefore
enabled and the rule deck is run against the assembled die.

## 2. By what principle each clause is tested

**The cross-section is single-moded.** The mode solve returns the guided-mode
count at 1310 nm on the printed geometry.

**The drawn mask meets the minima the process states.** Six rules are declared
and evaluated by the in-process engine. They restate the layer table: 250 nm
minimum width and 300 nm minimum gap on the ridge etch, 250 nm minimum width on
the slab, 800 nm width and a 1000 nm gap on the first metal, and 1500 nm from
the first metal to the ridge. They are a smoke test and they localise a failure
before the deck is read.

**The submitted object passes the foundry runset.** The deck at
`design-chain/pdk/LXT_KLayout_DRC_Runsets/LT_PRO_ltoi300.lydrc` is executed by
the KLayout application against the assembled die. This is the check a
fabrication run is actually made against, and its verdict is the one the
design is graded on.

**The mirror lands in the O band.** The design declares a target wavelength
rather than a period, so the grating stage solves the period and the reported
Bragg wavelength returns that target. The row is therefore an identity and it
tests the arithmetic of the solve rather than the drawn structure. The drawn
period carries a 0.288 nm RMS grid dither which this metric does not see, and
that dither is reported in [`REPORT.md`](REPORT.md).

The strength of the mirror is graded by no target. This design terminates in
no cavity and reaches no threshold, so the reflectivity carries no requirement
here; it is acknowledged as a finding under `warnings.acknowledged` with that
reason.

## 3. Trace

| clause | target metric | severity |
|---|---|---|
| §2 single lateral mode at 1310 nm | `mode.n_guided_modes` | must |
| §2 the drawn mask meets the declared minima | `drc.error_violations` | must |
| §2 the die passes the foundry runset | `drc.deck.violations_total` | must |
| §2 the mirror lands in the O band | `grating.bragg_wavelength_nm` | should |

## 4. What the concept does not claim

The clean verdict of §2 is a statement about the rules the deck evaluated
against geometry that exists. The deck declares 46 rule categories and 30 of
them read only layers that carry no polygon on this mask, so 16 rules were
exercised. The departures this instrument was built to find are recorded in
[`REPORT.md`](REPORT.md), and several of them are invisible to the deck by
construction.
