# The UBC electron-beam kit: what its cells draw against what it declares

`ubcpdk` is the gdsfactory form of the UBC silicon-on-insulator process run by
Applied Nanotools, and it is the kit this chain could drive directly, gdsfactory
being the layout engine here. It ships 119 cells. This asks whether the kit's
own three descriptions of a layer agree with each other: the name its layer map
gives it, the thickness and material its layer stack gives that name, and the
polygons its cells actually draw.

Conducted 2026-09-05. Both kits are MIT licensed and quoted freely.

## The environment, which is the first thing that had to be built

The kit could not be installed beside the others. It requires a gdsfactory this
chain does not run, 9.48.0 being installed here for the Luxtelligence kit and
the layout stage, so installing it here would take gdsfactory out from under the
chain. One environment per kit is the remedy and `design-chain/.venv-ubcpdk/` is
that environment.

**Which version is in it matters, and it is not the one the reference
describes.** Two artifacts bear this kit's name. The repository at `main` is
3.3.5 and requires `gdsfactory~=9.45.0`. The latest release on the package index
is 3.3.4 and requires `~=9.34.0`, and that is what `pip` installs and what every
measurement below was made on.

[`references/README.md`](../../references/README.md) was written from the
repository on 2026-09-03 and recorded 3.3.5 and `~=9.45.0`. **Both were correct
and this study briefly overwrote them with the release's figures before checking,
which was an error and is reverted.** One figure in that entry was genuinely
stale: the heater, recorded at 700 nm against the 750 nm that both the repository
and the release declare, which makes the disagreement with the sibling kit's
200 nm a factor of 3.75 rather than 3.5.

**What the version gap costs this study is stated where it bites.** The
structural findings below were checked against the repository's own `tech.py`
and hold on 3.3.5: `SLAB150` is named there and absent from the layer stack, no
nitride layer is declared, and no layer numbered 4/0 appears in either the map or
the stack. What was measured on 3.3.4 alone, and is not claimed of 3.3.5, is
every per-cell count: the 118 cells, the nineteen that draw on 4/0, and every
area in the table.

## Eighteen layers are drawn, fourteen are named, five are given a thickness

Measured on release 3.3.4. The repository's map declares sixteen names over the
same set of numbers, two of them aliases, and the same seven stack levels.

[`scripts/layer_audit.py`](scripts/layer_audit.py) builds every cell, writes it,
and reads back the layers that carry polygons.

| Layer | Named | Extruded | Cells | Area um² | What the sibling kit calls it |
| ---: | --- | ---: | ---: | ---: | --- |
| 68/0 | `DEVREC` | no | 97 | 539673.3 | DevRec |
| 1/0 | `WG` | **yes** | 74 | 19395.6 | silicon |
| 1/10 | `PORT` | no | 73 | 6.4 | |
| 12/0 | `M2_ROUTER` | **yes** | 32 | 324018.1 | router metal |
| 81/0 | — | no | 24 | 1138.6 | FbrTgt |
| 998/0 | — | no | 20 | 20210.3 | |
| 4/0 | — | no | 19 | 2091.8 | **silicon nitride** |
| 11/0 | `M1_HEATER` | **yes** | 16 | 16623.2 | heater metal |
| 10/0 | `TEXT` | no | 8 | 4204746.7 | text |
| 1/11 | `PORTE` | no | 8 | 58.0 | |
| 13/0 | `PAD_OPEN` | no | 7 | 200549.0 | pad opening |
| 203/0 | — | no | 4 | 39439.6 | |
| 1/99 | — | no | 4 | 221.9 | |
| 201/0 | — | no | 3 | 30000.0 | deep trench |
| 6/0 | — | no | 2 | 5954.0 | oxide open |
| 200/0 | — | no | 1 | 30.0 | |
| 99/0 | `FLOORPLAN` | no | 1 | 206800.0 | floor plan |
| 31/0 | `WG2` | **yes** | 1 | 123.9 | |

118 of the 119 cells build. The one refusal is `import_gds`, a helper that wants
a path rather than a device.

**Eight of the eighteen carry polygons and are named by neither the layer map nor
the layer stack**, being 1/99, 4/0, 6/0, 81/0, 200/0, 201/0, 203/0 and 998/0.

**The most consequential is 4/0, which is silicon nitride in the sibling kit and
is drawn by nineteen cells here.** That identification is not a guess from the
layer table: the sibling's own cross-section script binds `sin = layer("4/0")`
and grows it 400 nm thick at a 5 degree taper. Every nitride device the kit ships — the SiN
grating couplers, the SiN crossings, the 895 nm couplers, the 1310 nm
interferometer — puts its guiding layer on a number the kit gives no name, no
thickness and no material. A three-dimensional solve of any of them sees an
empty stack where the waveguide should be, a cross-section view draws nothing,
and a rule written against a layer name matches nothing. The polygons are
correct and everything that would interpret them is absent.

## The layer named for a slab that no cell draws

`SLAB150` at 2/0 is one of four names the layer map declares and no cell draws.
It is also absent from the layer stack, so it has a name and nothing else.

That would be unremarkable were it not for `ebeam_gc_te1550_90nmSlab`, a cell
whose name promises a shallow etch. It draws 27 polygons and every one of them
is on 1/0, the full 220 nm silicon. Nothing sits on 2/0 or on any second etch
layer.

| | `ebeam_gc_te1550` | `ebeam_gc_te1550_90nmSlab` |
| --- | ---: | ---: |
| Polygons on 1/0 | 53 | 27 |
| Area on 1/0 | 248.397 um² | 344.508 um² |
| Polygons on 2/0 | 0 | **0** |
| Bounding box | 39.97 by 27.17 um | 41.00 by 27.40 um |

**The two are genuinely different devices**, their drawn silicon differing by
224.7 um² over 32 polygons, so the cell is not a duplicate under another name.
What it is not is a shallow-etch grating coupler as drawn. Either the etch is
expected to be produced by something the emitted file does not express, or the
name describes a device the kit does not draw. A user picking it for its
published shallow-etch performance would tape out a full-etch coupler.

## The buried oxide the two kits disagree about, and what it is worth

The sibling KLayout kit grows a 2.0 um buried oxide and ubcpdk declares 3.0.

Both figures were read from the kits themselves on 2026-09-05. The sibling's
cross-section script at `klayout/EBeam/xsect/EBeam_ANT.xs` grows its oxide at
2.0 and its heater metal at 0.2, against the 3.0 and 0.75 ubcpdk's layer stack
declares, so the two disagreements are real and are a factor of 1.5 and of 3.75.

The oxide is what separates the mode from the silicon handle, and the handle's index
is above the mode's, so a strip on this platform has no bound mode at all. It
has a leaky one, and the leakage falls exponentially with the oxide it must
tunnel through:

    alpha ~ exp(-2 gamma t),    gamma = k0 sqrt(n_eff² - n_ox²)

[`scripts/box_leakage.py`](scripts/box_leakage.py) solves the effective index
and evaluates the exponent. The prefactor is common to both thicknesses and
cancels in the ratio, which is the quantity the disagreement calls for.

| Case | `n_eff` | 2.0 um | 3.0 um | The thin one leaks more by |
| --- | ---: | ---: | ---: | ---: |
| 0.50 um strip, TE | 2.50009 | 4.25e-15 | 2.77e-22 | 71.9 dB |
| 0.50 um strip, **TM** | 1.84939 | 7.30e-09 | 6.24e-13 | **40.7 dB** |
| 0.50 um rib on a 130 nm slab, TE | 2.64936 | 2.28e-16 | 3.45e-24 | 78.2 dB |
| 0.50 um rib on a 130 nm slab, TM | 1.86595 | 4.77e-09 | 3.29e-13 | 41.6 dB |
| 3.00 um multimode rib, TE | 2.83685 | 6.38e-18 | 1.61e-26 | 86.0 dB |

**The disagreement does not matter for the transverse-electric mode and it is
the only case that matters for the transverse-magnetic one.** At 1550 nm a TE
strip on either oxide tunnels at 1e-15 or below, which no prefactor rescues into
relevance. The TM mode sits at an effective index of 1.85 against the oxide's
1.44, so its tunnelling factor is six orders of magnitude larger, and there the
extra micrometre is worth a factor of twelve thousand.

The kit ships TM devices: `ebeam_gc_tm1550`, `ebeam_adiabatic_tm1550`,
`ebeam_bdc_tm1550` and `ebeam_Polarizer_TM_1550_UQAM`. **Those are the cells for
which the two kits' stacks are not interchangeable**, and they are exactly the
cells a designer is most likely to take a published figure for.

## The kit's own effective-index table, and two solvers against it

`ubcpdk` ships `simulation/find_neff_vs_width.csv`, four modes of a 220 nm strip
against width. It is the one quantitative artifact in the kit that can be
reproduced without the foundry, and its provenance is readable from the kit
itself: MPB, through `gplugins.modes.find_neff_vs_width`, at 1.55 um with the
core index held at 3.47 and the cladding at 1.44, on a rectangular
cross-section, over a 2 by 2 um cell, with no parity imposed so the four columns
are ordered by effective index and mix the polarisations. Those constants are
used here rather than the chain's own materials, a cross-check being between
solvers rather than between material files.

### The chain's default solver cannot make the comparison

[`scripts/neff_cross_check.py`](scripts/neff_cross_check.py) attempts it with
the finite-difference solver the chain uses everywhere, and the attempt fails
its own convergence guard.

| Cell | `n_eff` at 0.5 um | Moved |
| ---: | ---: | ---: |
| 40 nm | 2.664073 | |
| 20 nm | 2.573708 | 9.04e-02 |
| 10 nm | 2.527801 | 4.59e-02 |
| 5 nm | 2.504328 | **2.35e-02** |

The convergence is first order and it is nowhere near settled at 5 nm.
Richardson extrapolation of that sequence gives 2.481, still 0.04 from the
answer below. A first attempt with a uniform mesh was worse still, wandering by
7e-3 at the finest step and reversing direction, because a uniform mesh laid
across a high-contrast interface staircases it and refining moves the boundary
as well as the sampling. Meshing each region separately fixed the wandering and
did not fix the convergence.

**The cause is the contrast and the approximation, not the mesh.** This
cross-section carries an index step of 2.03 between silicon and oxide, against
0.71 on the LTOI300 ridge the chain was built for. The solver is semi-vectorial,
which is a statement that the polarisations barely couple, and at that contrast
they do. Run against the LTOI300 ridge the same ladder settles to 2.4e-4 by a
10 nm cell, so the limitation is of the platform and not of the code.

### The finite-element path can, and it agrees with itself immediately

[`scripts/neff_cross_check_fem.py`](scripts/neff_cross_check_fem.py) poses the
same problem to the full-vectorial finite-element solver the chain carries for
its `fem` stage, on a conforming triangulation that does not staircase.

| Resolution | `n_eff` at 0.5 um | Moved |
| ---: | ---: | ---: |
| 50 nm | 2.438076 | |
| 25 nm | 2.438068 | 7.4e-06 |
| 12.5 nm | 2.438038 | **3.1e-05** |

It is also insensitive to the window it is posed in, moving by 4e-6 between a
2 um domain and a 6 um one, so the truncation is not carrying the answer.

### The kit's table sits above a converged solve, everywhere

| Width | kit m1 | fem | d | kit m2 | fem | d | kit m3 | fem | d |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.2000 | 1.5075 | 1.4876 | −0.0199 | 1.4908 | 1.4680 | −0.0228 | 1.3344 | — | |
| 0.3455 | 2.0517 | 2.0264 | −0.0253 | 1.6579 | 1.6320 | −0.0259 | 1.4071 | — | |
| 0.4909 | 2.4301 | 2.4233 | −0.0069 | 1.7798 | 1.7562 | −0.0236 | 1.4716 | 1.4654 | −0.0061 |
| 0.6364 | 2.5973 | 2.5909 | −0.0064 | 1.8640 | 1.8392 | −0.0248 | 1.7875 | 1.7806 | −0.0069 |
| 0.7818 | 2.6846 | 2.6748 | −0.0098 | 2.1447 | 2.1272 | −0.0175 | 1.9217 | 1.8931 | **−0.0286** |
| 1.0000 | 2.7465 | 2.7391 | −0.0074 | 2.4190 | 2.4119 | −0.0070 | 1.9693 | 1.9425 | −0.0268 |

Six of the twelve widths are shown and the full run is in the script. **The
converged solve sits below the kit's table at every one of the thirty-two
comparisons**, by 0.006 to 0.029, which is up to 935 times the mesh error and
therefore real.

That the offset has one sign says the two are not posed identically rather than
that either is noisy, and its size tracks confinement: the magnetic mode, the
least confined of the three, carries 0.023 to 0.026 across the middle of the
range where the fundamental carries 0.006 to 0.010, and the fundamental's
largest offsets are at the narrowest widths where it too spreads.

**The most likely cause is the resolution the table was computed at**, the kit's
own call leaving `get_mode_solver_rib` at its default of 32 pixels per
micrometre, which is a 31 nm cell across a 220 nm film. That cannot be confirmed
here: MPB is not installed in either environment, and the table ships without a
convergence record of its own. What can be said is that the table is not the
converged answer to the problem it states, and that a resonator designed against
it would sit about 11 nm from where the table puts it, an index offset of 0.029
being that much of a wavelength at a group index of 4.2.

## What is not covered

**No absolute leakage figure is given.** The exponent is computed and the
prefactor is not, so the table above is a ratio and not a loss. Turning it into
decibels per centimetre wants a leaky-mode solver, which this chain does not
have, and the conclusion drawn does not need one: a factor whose larger member
is 1e-9 is negligible in absolute terms whatever the prefactor, and that is what
settles the TE case.

**The sibling KLayout kit was not installed.** Its stack figures are those
recorded in the reference from reading `EBeam_ANT.xs`, and the disagreement is
therefore between a kit that was run and a document that was read. Installing it
would settle whether the 2.0 um figure is current.

**No cell's optical behaviour was computed.** The effective-index table is a
cross-section and not a device. Whether `ebeam_bdc_te1550` splits evenly is a
question for a propagation solver, and the finding above settles which solver it
must be put to: not the chain's default one, on this platform.

**The 90 nm slab question is not closed.** That the cell draws no second etch
layer is a fact about the emitted file. Whether the process produces one anyway,
by a step the layout does not express, is a question for the foundry.

## The files

| File | What it is |
| --- | --- |
| [`scripts/layer_audit.py`](scripts/layer_audit.py) | every cell built and read back, the drawn layers against the declared ones |
| [`scripts/box_leakage.py`](scripts/box_leakage.py) | what the two declared oxide thicknesses are worth, by mode solve |
| [`scripts/neff_cross_check.py`](scripts/neff_cross_check.py) | the kit's table against the chain's finite-difference solver, which fails its guard |
| [`scripts/neff_cross_check_fem.py`](scripts/neff_cross_check_fem.py) | the same against the full-vectorial finite-element solver, which passes |
| `design-chain/.venv-ubcpdk/` | the kit's own environment, excluded from version control |
