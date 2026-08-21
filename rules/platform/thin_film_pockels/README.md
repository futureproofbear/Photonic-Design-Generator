# X-cut thin-film Pockels platforms

Lithium niobate and lithium tantalate on insulator, film thickness 300 nm to
400 nm, shallow-etched ridge with a residual slab, coplanar electrodes on the
unetched surface, quasi-TE operation with propagation perpendicular to the
in-plane c-axis so that r₃₃ is accessed.

*Written from four designs on two films. Every measured sensitivity below states
the cross-section it was taken on, and a figure measured once is marked as
such.*

---

## 1. The film draws the field, and the mode is only partly inside it

The film permittivity at radio frequency greatly exceeds that of the oxide
below and the cladding above, so a coplanar electrode pair concentrates its
field in the film. The optical mode is not wholly inside the film, so the
electro-optic overlap Γ falls well below unity.

**Measured range on these stacks: Γ between 0.24 and 0.35** for coplanar
electrodes at gaps of 6 to 8 µm. The lower figures belong to the thinner film,
which holds the mode less tightly.

Two consequences follow.

**A published V<sub>π</sub>·L computed at unit overlap differs from the physical
value by 1/Γ**, which is a factor of three to four here. A figure appearing
optimistic by that much is frequently the un-derated one. Report both.

**The electrostatic window is to be sized for the fringing field and not for
the mode.** The field setting the electrode capacitance extends far further than
the optical field. A window sized for the mode under-read a capacitance by
approximately a factor of four. Two meshes are appropriate: a fine narrow one
for the optics and a coarse wide one for the electrostatics, with interpolation
between them.

**Weaker confinement is not purely a cost.** A thinner film holds the mode less
tightly, so the mode is larger at a taper tip and the butt joint to a
semiconductor gain chip improves. Across one 400 nm to 300 nm film change the
electro-optic overlap fell by 31 % while the coupling loss per facet fell by
0.87 dB, twice per round trip, and the threshold and linewidth held up against
the weaker mirror that resulted.

## 2. Side-coupled gratings are exponentially sensitive to the gap

Where a grating is formed by elements placed beside the guide rather than
patterned into it, the index perturbation decays exponentially with the
separation, at the transverse decay constant of the guided mode.

**Measured: d(ln Δn_eff)/d(gap) between −5.4 and −5.55 µm⁻¹** on shallow-etched
thin-film cross-sections, a decay length near 180 nm. The lower magnitude
belongs to the same cross-section drawn with vertical walls, so the sidewall
angle moves the sensitivity as well as the value.

**A ±20 nm lithographic error is therefore a ±11 % error in κ**, and κ sets
reflectivity, mirror bandwidth, penetration depth and continuous tuning range.
A design on this platform is either centred where ∂(performance)/∂κ is flat or
provided with a trim, and monitor structures with stepped gaps belong on the
first reticle so that the process is measured.

**Read [`../../generic/parameter-scans.md`](../../generic/parameter-scans.md)
before declaring that sensitivity as a process window.** The gap and the feature
size move together under a lithographic excursion, and on a grating of order
above one the two terms oppose.

## 3. Sloped sidewalls strengthen a side-coupled grating

Sloping the walls of a ridge and its adjacent elements **increases** Δn_eff,
because a trapezoidal element presents a wider base positioned closer to the
ridge. The intuition that removing material weakens the perturbation is
incorrect for side-coupled geometries.

Measured on one shallow-etched cross-section against the same structure drawn
with vertical walls:

| wall angle from horizontal | Δn_eff, relative | λ_B shift |
|---:|---:|---:|
| 90° | 1.00 | — |
| 85° | 1.12 | +1.7 nm |
| 80° | 1.26 | +3.3 nm |
| 77° | 1.35 | +4.3 nm |
| 70° | 1.61 | +6.6 nm |
| 60° | 2.13 | +10.1 nm |

A wall angle typical of an ion-beam etch on these stacks lies near 77°, which is
a third of the way to doubling the coupling constant. The same change displaces
the Bragg wavelength by about 10 nm across that range. **Sidewall angle is a
first-order parameter for both κ and λ_B on this platform**, and it belongs in
any declared process window.

## 4. Where the grating feature sits decides whether the coupling is usable

Metal must stay clear of the waveguide layer by a foundry rule of order 1.5 to
2 µm. Bragg posts placed beside the guide push the metal outward by their own
offset, and the electrode gap and the tuning efficiency follow.

Moving the feature **into** the ridge, as a periodic widening rather than as
islands beside it, frees the metal and raises the tuning. It was built and
measured: tuning rose 51 % to 610 MHz/V, and **the coupling constant rose
105-fold**, from 0.76 to 79.8 /cm, the perturbation having moved from the tail of
the mode into its centre. The penetration depth is 1/2κ at strong coupling, so it
collapsed from 5.6 mm to 63 µm, taking the tuning lever with it. Linewidth went
from 4.5 to 52.5 kHz and side-mode suppression from 46 to 7 dB.

**On this platform a corrugated ridge and a side-coupled post array are different
devices and not two drawings of one.** Where an extended cavity depends on
penetration depth, the coupling must be weak, and weak coupling on this stack
means the feature stays in the evanescent tail.

## 5. Coherent addition over a long mirror is a film-uniformity requirement

A distributed reflector with a penetration depth of millimetres adds coherently
only while the film holds the Bragg phase over that length. The budget is
computed from d(Δn_eff)/d(film thickness) and is of order **0.1 nm of film
thickness over several millimetres**, which is a few hundredths of one per cent.
Foundry film specifications are ordinarily stated in per cent.

**Declare `platform.film_nonuniformity_nm` or record the assumption.** Where it
is absent, coherent addition over the mirror is assumed and not established.

## 6. The material constants

Bulk congruent values differ materially from thin-film measured values on both
films, and the difference is not a refinement. Propagation loss in particular
differs by more than a factor of three between a bulk-derived figure and a
measured thin-film one.

**Thin-film literature is not process-control data.** A constant measured on a
600 nm film by another group, with different poling and a different etch,
describes a neighbouring stack. The provenance tag records which of the three
states applies: bulk, thin-film literature, or confirmed against this foundry's
process-control monitors. Reaching the third state is a design activity and not a
documentation step.

Two qualitative properties motivate lithium tantalate over lithium niobate on
this platform, and both are recorded rather than assumed: the photorefractive
resonance shift is about fivefold smaller, and the optical damage threshold is
higher.

## 7. The optical window over a high-index handle

The stack is film, buried oxide, and a high-index handle wafer. **A mode-solver
window that truncates the buried oxide and then includes the handle returns
substrate modes at the handle index.** Where the real oxide is thick enough to
isolate the mode, the handle is excluded from the optical problem and retained
only for the electrostatic problem, which does need it.

**Blanket layers are drawn beyond the window edge.** Sub-pixel material averaging
reports a half-filled cell where a blanket layer terminates exactly at the
boundary, which computes a lateral-guidance floor too low and miscounts slab
continuum states as guided modes.

**A mode is laterally guided only while n_eff exceeds the effective index of the
unpatterned slab.** Counting against the cladding index classifies every
discretised slab continuum state as a guided mode. This applies to any rib
waveguide and is repeated here because the residual slab on this platform makes
it constantly relevant.

## Evidence

`.claude/LESSONS.md` L002, L003, L005, L006, L013, T001, T002, T003, T004, T040,
and the material provenance entries in `design-chain/pdk/materials.yaml`.
