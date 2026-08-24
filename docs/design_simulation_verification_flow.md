# Design, Simulation and Verification Flow

The proposed flow, the toolset from which it is assembled, and its implementation
in [`../design-chain/`](../design-chain/) are described below.

---

## 1. Principles

Four decisions determine the structure of everything that follows.

**Operation without a graphical interface.** Each step is invoked as a command
and returns a machine-readable result. Graphical tools are excluded from the
execution path, so that identical behaviour is obtained on a workstation, within
continuous integration, and under agent control. Graphical tools (KLayout,
ParaView) are reserved for the inspection of results and are never used for their
production.

**One design corresponds to one folder.** A dedicated directory is allocated to
each standalone PIC, holding its `design.yaml`, its acceptance targets, and all
of its run artifacts. Only the toolchain and the platform file are held in
common. Isolation of this kind prevents a change made to the chirped laser from
silently displacing the sampler.

**Acceptance criteria are held with the design in machine-checkable form.** A
design is regarded as complete only against a declared and sourced target list.
A non-zero exit code is returned by `verify` when a `must` target is unmet. That
single property is what permits the flow to be automated, since a condition on
which an agent or a continuous-integration job can branch is thereby provided.

**Provenance is recorded as a schema field.** A `provenance` string is carried by
each material; entries tagged `needs_confirmation` are reported on every run and
may be configured as a hard block. An `# ASSUMPTION:` annotation is carried by
each design-file quantity that cannot be traced to the literature, to a project
statement of requirements, or to a foundry document. On a programme whose target platform (TFLT) possesses no mature
public parameter set, this distinction separates a model from an estimate.

---

## 2. Toolset

The toolset is selected from
[joamatab/awesome_photonics](https://github.com/joamatab/awesome_photonics). Four
status values are used, and they are to be read strictly.

**The licence of a candidate is examined before its capability.** This framework
is distributed under the MIT licence, so a copyleft library imported by a stage
would propagate its terms to the whole tree. A copyleft *executable* invoked as a
separate process does not, no linking occurring, and that is the arrangement
already used for the time-domain solver. The distinction decides the form an
adoption may take rather than whether it may occur, and it is recorded in the
tables below wherever it applies.

| status | meaning |
|---|---|
| **now** | imported by a stage and exercised on every run |
| **declared** | present as an optional dependency in `pyproject.toml` and reported by `picchain doctor`, but imported by no stage. Availability is reported; use is not |
| **next** | identified as the intended insertion point, and not installed |
| **surveyed** | examined against the catalogue and not adopted at present, with the trigger for revisiting the decision recorded |

### 2.1 In Use and Intended

| function | tool | status | rationale |
|---|---|---|---|
| layout / DRC engine | **KLayout** (`klayout.db`) | now (primary) | a single object model serves both GDS writing and DRC execution; the reference viewer for the format |
| layout | **gdsfactory** | now (secondary backend) | the established Python layout framework; ports, netlists and hierarchy are provided for the full transceiver assembly. **kfactory** is obtained as a transitive dependency of gdsfactory version 8 and is not imported directly |
| optical modes | in-chain semi-vectorial FD solver | now | approximately 200 lines of numpy/scipy, validated against the analytic slab; installation burden is minimal |
| electrostatics / EO overlap | in-chain anisotropic FV solver | now | validated against the parallel-plate case; the mode mesh is shared |
| gratings | in-chain CMT + TMM | now | apodisation, chirp, loss, group delay and penetration depth are supported |
| material data | in-chain YAML with provenance | now | Sellmeier coefficients, EO tensor and RF permittivity, per material |
| optical modes, FEM cross-check | **femwell** (scikit-fem, gmsh) | now (optional stage) | full-vectorial finite elements on a conforming triangulation, reached by the `fem` stage. The FD core is thereby checked against a second numerical method on the device cross-section itself, and no longer against the analytic slab alone. One scalar permittivity per element is carried, so the anisotropic problem is bracketed rather than posed |
| circuit assembly | **SAX** | now (optional stage) | reached by the `circuit` stage, which assembles the passive circuit from scattering matrices and is anchored to the closed-form two-mirror result. It is the first stage that describes a circuit rather than a component: a netlist of three blocks and one of thirty differ only in the dictionary |
| tapers, by eigenmode expansion | in-chain local-mode EME (`picchain.eme`) | now | guided-mode conversion and the adiabaticity margin, on the mesh already built for the mode solve. Radiation into the continuum is outside a guided-mode basis and is not computed |
| taper radiation | **meep** (FDTD) | now (optional stage) | open source, executed locally, no account and no per-run cost. There is no Windows build, so it is held in a WSL 2 environment and reached through a JSON bridge. Two dimensions by effective index is minutes; three dimensions is an offline job |
| component S-parameters (MMIs, couplers, bends) | **meep** (FDTD) | next | the solver is now in place; what is missing is the geometry description for components other than a width taper |
| the same, as a service | **tidy3d** | surveyed, not adopted | the solve executes on the vendor's servers under an API key and is billed in credits. Geometry would leave the machine, which is inadmissible for project designs, and a network dependency in continuous integration is the condition the exclusion below was written to avoid |
| travelling-wave electrode | in-chain (`picchain.rf`) | now | microwave index and impedance from the capacitance solved with and without the dielectrics; skin-effect loss; the phasor-sum response. Eight closed-form tests |
| RF link budget and cascades | **scikit-rf** | declared | installed with the circuit extras and imported by no stage. The receiver noise-figure cascade and a matching network for the electrode, whose impedance the chain now computes |
| the same, when wired | **scikit-rf** | next | the receiver noise-figure cascade, and matching networks for the electrode now that its impedance is known |
| lab automation | **pymeasure** / **autosweep** / **LabExT** | next | for device characterisation; the same YAML target lists become test limits |
| system-level DSP | numpy/scipy | external | supplied by the scope; device parameters are provided to it by the chain |
| eigenmode expansion, second implementation | **meow** | declared | Apache 2.0, installed and importable. The in-chain local-mode expansion is presently checked against nothing. A second implementation of the same method would establish whether the adiabaticity margin rests on the method or on one coding of it, in the way femwell established that for the mode solve |
| time-domain, native to Windows | **fdtdx** | declared | MIT, installed and importable, JAX-native, and it carries no external environment. The time-domain solver in use has no Windows build and is reached through a bridge into a second operating system, which is the single heaviest installation requirement the chain places on a machine. A solver that installs by `pip` removes that requirement, and being differentiable it also admits gradients the present one does not |

### 2.2 Surveyed and Not Adopted

The catalogue holds capability bearing on deliverables already on the register.
Each entry below was examined and set aside. The trigger column states the
condition under which the decision is to be revisited, so that an omission is not
mistaken for an oversight.

| catalogue entry | function | bearing on this work | trigger for adoption |
|---|---|---|---|
| **mpb** | Bloch mode solver | **adopted.** The photonic band gap yields κ with no length, no propagation and no radiation channel. It found the coupled-mode construction to over-predict κ, which qualified the lithographic-bias reading of the baseline | in use as `fdtd.structure: bandstructure` |
| **optolithium**, **dimmilitho**, **keras_litho** | lithography simulation | the baseline established that κ is exponentially sensitive to a post gap below 100 nm, and attributed a 132 nm discrepancy to combined stepper and etch bias. That displacement is at the upper end of what the process plausibly delivers, so part of it is likely to belong to the model. A litho model converts that attribution from an argument into a computation | a mask-to-silicon bias measurement, or a second design whose κ misses in the same direction |
| **palace**, **elmer**, **ngsolve** | FEM electromagnetics | the microwave eigenmode and driven solve required for a travelling-wave electrode, which the lumped electrostatic model cannot supply | any modulator specified above 10 GHz |
| **devsim** | TCAD | no semiconductor device model exists in the chain. The UTC photodiode on which carrier synthesis depends lies outside every present stage | commencement of photodiode design |
| **PyLLE**, **PyGLLE**, **PyNLO**, **Laserfun** | Lugiato-Lefever, nonlinear Schrödinger | the sinc-pulse sampler requires a resonant comb. Neither comb formation nor nonlinear propagation is modelled | commencement of the sampler |
| **philsol**, **pymode** | mode solvers admitting bends | bend loss of the PDH resonator. The in-chain `bend` stage now gives the bend mode and the radius at which the caustic reaches the guide, but refuses the leaky regime beyond it | a bend tighter than that radius, where a loss in decibels per turn is required |
| **ceviche**, **spins**, **jaxwell** | FDFD | a two-dimensional frequency-domain solve is cheaper than 3D FDTD, installs natively on Windows, and would bound the taper radiation that the guided-mode basis cannot reach | adopted if the FDTD stage proves too costly to run under continuous integration, or as the interim measure while WSL is arranged |
| **S4**, **FMMAX**, **grcwa**, **nannos**, **inkstone** | RCWA | surface gratings and grating couplers | a decision to couple by surface grating rather than by edge |
| **optiCommPy**, **QAMpy** | optical communications DSP | the DSP chain is presently marked external. Two maintained options exist in the catalogue | a requirement for the chain to close the loop from device parameters to a range-Doppler result |
| **lumopt**, **angler**, **SPLayout**, **ceviche-challenges** | inverse design | taper and coupler optimisation | availability of a propagation solver, which is a precondition |
| **Luxtelligence `lxt_pdk_gf`** | foundry process design kit for thin-film lithium niobate (LNOI400) and thin-film lithium tantalate (LTOI300) | the only open process kit found for either platform. MIT licensed, installed with pip, native to gdsfactory, which the layout stage already carries. It supplies a component library, KLayout layer properties and a downloadable rule runset | adopt when a design is taken toward a fabrication run. It replaces the five hand-declared geometric rules with the foundry deck and fixes the layer stack, at which point the platform file must be reconciled with the process the kit describes |
| **emepy** | eigenmode expansion | the same capability as **meow** above, under the MIT licence. **Not adopted on maintenance grounds**: the last commit to its repository is dated October 2022, so it is unmaintained by any ordinary reading. Recorded so that it is not proposed again | resumption of maintenance, or a defect in meow that emepy is found to handle |
| **Xyce** | circuit simulation, SPICE | the chain computes an electrode capacitance and a lumped bandwidth, and it models no driver at all. Where a design is bounded by its drive rather than by its optics, the driver and the electrode form one circuit and neither alone answers the question. Xyce is GPLv3 and is therefore to be **invoked as a separate process against a netlist**, in the manner of the time-domain bridge, and never imported | a design whose acceptance set carries a drive-voltage row, or a ramp whose fidelity is specified |
| **PySpice** | Python bindings to SPICE engines | the convenient route to the above, and **it may not be taken**. PySpice is GPLv3 and a stage importing it would place the whole framework under that licence. The netlist route above obtains the same result and preserves the MIT terms | it does not become adoptable by any technical development; only a relicensing would change this |
| **lcapy** | symbolic linear circuit analysis | the RC and transmission-line algebra the electrode stage performs by hand, done symbolically. LGPL 2.1, which for a pure-Python import is a weaker obligation than the GPL and is not a settled question | a decision on the LGPL position, which is to be taken before the import and not after |
| **openVAF** | Verilog-A compilation | compact models for the gain chip and the photodiodes, in the form a circuit simulator consumes. GPL 3.0, and a compiler, so it is invoked as a process | adoption of Xyce together with a need for a device model beyond its built-in set |
| **SiPANN** | neural surrogates for photonic components | the staged search of section 3 exists because the expensive model cannot sit inside it, so the search runs on closed form and the solver runs afterwards. A surrogate trained on the solver would collapse that separation. MIT | a search whose closed-form stage is found to mis-rank candidates that the solver then re-orders |
| **rii_pandas** | refractive index database | a candidate source for clearing entries tagged `needs_confirmation` | preferred only where foundry process control monitor data is unavailable |
| **simphony**, **photontorch**, **opics**, **lekkersim** | circuit solvers | alternatives to SAX, of which photontorch adds time domain | a requirement for time-domain circuit behaviour |
| **lytest** | layout regression testing | the layout stage carries no test, whereas the solvers carry eleven | any change to the layout stage beyond the present fixed floor plan |
| **speedsterpy** | parasitic extraction | electrode and routing parasitics beyond the lumped capacitance | adoption of a travelling-wave electrode |
| **kweb**, **GDS3D**, **GDS2WebGL** | GDS viewing without a graphical interface | mask inspection under continuous integration, which is not presently provided | a requirement to review a mask remotely |
| **wafermap**, **pandas**, **dask** | data analysis | characterisation data, once devices return from fabrication | first wafer out |

### 2.3 Categories Excluded as Inapplicable

Approximately half the catalogue does not apply to this programme and was not
examined further. The silicon process kits carried by the catalogue
(**ubcpdk**, **skywater130**, **gf180**, **vtt**, **siepic-ebeam-pdk**) target
platforms other than thin-film lithium niobate or tantalate. It is to be noted
that the catalogue lists no kit for either of those two platforms, and that this
absence is not evidence that none exists: one does, and it is recorded in §2.2. The superconducting and quantum entries
(**KQcircuits**, **qiskit-metal**, **soen-pdk**) address a different device class.
The free-space, ray-tracing and adaptive-optics sections address bulk optics. The
alternative layout frameworks (**gdstk**, **nazca**, **phidl**, **picwriter**,
**masque**, **dphox**) would duplicate a capability already held.

### 2.4 Order of Adoption

**meep has since been adopted** and is reached through WSL 2, so the item that
stood as the largest gap is now partly closed: the taper is solved in the time
domain and its radiation is quantified. What remains of that gap is the geometry
description for components other than a width taper, and the cost of running in
three dimensions rather than by effective index.

**mpb has since been adopted** and is reached through the same bridge. It gives κ
from the photonic band gap of a single period, with no length, no propagation and
no radiation channel, and it settled a question the time-domain check could not:
the coupled-mode construction over-predicts κ. The finding is recorded in
[`../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md`](../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md).

**femwell has since been adopted** and is reached in process, the finite-element
libraries having Windows builds. The mode solver is now checked against an
independent numerical method on the device cross-section rather than against the
analytic slab alone. The result is recorded in
[`../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md`](../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md).
The list of items awaiting adoption is thereby exhausted. What follows is
**SAX**, for circuit-level assembly, and a thermal and mechanical stage, for
which the finite-element libraries are now present.

**Two libraries were installed on 2026-08-24 and neither is yet imported by a
stage**, so both stand at `declared` and the distinction the status table draws is
to be respected: their availability is reported and their use is not. **meow**
supplies a second implementation of the eigenmode expansion, and **fdtdx**
supplies a time-domain solve that installs natively. The case for each is a
dependence that the chain presently carries on a single implementation, and
in the second instance on a second operating system.

The eigenmode expansion and the time-domain solve answer different questions and
are both retained. The expansion reports conversion between guided modes and the
adiabaticity margin at a cost of one mode solve per slice, and it reports where
radiation is to be expected. The time-domain solve reports how much.

**Deliberate exclusion of commercial FDTD and mode solvers.** The exclusion is
not made on capability grounds. It is made because a licence server in the
execution path defeats reproducibility without a graphical interface and blocks
continuous integration. Where commercial tools are already available, they are
appropriately placed as an *optional cross-check stage* operating on the same
JSON contract, and never on the critical path.

**The exclusion extends to solvers offered as a service.** A cloud solver
introduces the same dependency in a different form, and adds two of its own: a
per-run cost, and the transmission of the geometry to a third party. The second
is decisive for anything under `projects/`, since a design cannot be uploaded
without the authorisation of the party whose intellectual property it is. Where
such a tool is adopted, it is to be restricted to the public examples, disabled
by default, and gated behind an explicit flag.

---

## 3. The Flow

```
   design.yaml  ────────────────────────────────────────────────┐
   (+ platform, + materials, + targets)                         │
        │                                                       │
   ┌────▼─────┐  n_eff, n_g, Δn_eff, confinement, mode count    │
   │  mode    │  FD semi-vectorial, graded mesh, subpixel ε     │
   └────┬─────┘                                                 │
        ├──────────────► ┌─────────┐  the same section by FEM:  │
        │                │   fem   │  n_eff, Δn_eff, purity,    │
        │                └─────────┘  convergence, anisotropy   │
        │                             (optional; read by none)  │
   ┌────▼─────┐  spatial Fourier → κ_m ; TMM → R(f), FWHM,      │
   │ grating  │  sidelobes, group delay, penetration depth      │
   └────┬─────┘                                                 │
        │                                                       │
   ┌────▼─────┐  anisotropic electrostatics on a wide RF mesh,  │
   │   eo     │  overlapped with the optical mode → Γ, MHz/V,   │
   └────┬─────┘  Vπ·L, C, RC bandwidth                          │
        │                                                       │
   ┌────▼─────┐  round-trip phase against voltage → FSR,        │
   │  cavity  │  Pockels lever, tuning, mode-hop-free range,    │
   └────┬─────┘  chirp nonlinearity, S-T-H linewidth, SMSR      │
        │                                                       │
   ┌────▼─────┐  polygons → GDS (klayout + gdsfactory, compared │
   │  layout  │  by exclusive-or). Drawn frame, so a process    │
   └────┬─────┘  bias is carried into the drawing               │
        │                                                       │
   ┌────▼─────┐  the die: seal ring, dicing lane, overlay marks,│
   │ reticle  │  label, and the monitors that measure the       │
   └────┬─────┘  process (optional)                             │
        │                                                       │
   ┌────▼─────┐  KLayout Region checks, violations → marker GDS │
   │   drc    │                                                 │
   └────┬─────┘                                                 │
        │                                                       │
   ┌────▼─────┐◄────────────────────────────────────────────────┘
   │  verify  │  each target evaluated → PASS/FAIL + exit code
   └────┬─────┘
        │
   metrics.json · report.md · figures/ · *.gds
```

Upstream metrics are read by each stage from the run context, and upstream arrays
from the `.npz` files of that run; its own results are then written. Dependencies
are resolved automatically: a request for `cavity` causes
`mode,grating,eo,cavity` to be executed.

### Verification at Five Levels

1. **Solver validation, against closed-form results.** The FD mode solver is
   checked against the analytic asymmetric-slab dispersion relation, the FEM
   mode solver against the same relation and against the closed-form slab
   confinement factor, the electrostatic solver against a parallel-plate
   capacitor, and the TMM against `tanh²(κL)` and against its own piecewise
   form. One hundred and thirty-six tests are provided; execute `pytest tests/ -q`. The mask
   structures are included at this level, each measured against the geometric
   property it is required to have rather than against the parameters that
   produced it. The *tools* are validated here.
2. **Method cross-check, by a second and unrelated instrument.** A closed-form
   anchor establishes that a solver is correct on a problem simple enough to
   have an analytic answer. It does not establish that the same solver is
   correct on the device. Two quantities are therefore computed twice by
   unrelated methods. The cross-section is solved by finite differences and, in
   the `fem` stage, by finite elements on a conforming triangulation. The
   coupling constant is constructed by coupled-mode theory and, in the `fdtd`
   stage, measured from the photonic band gap. Each cross-check carries its own
   convergence guard, and is not to be read where that guard reports the
   comparison unresolved. The *applicability* of a tool to the device is
   established at this level.
3. **Physical invariants, evaluated on every design run rather than in tests
   alone.** A grating FWHM below the transform limit `0.886·c/(2 n_g L)`; more
   than one guided mode; optical power reaching the electrodes; an electrode too
   slow for the chirp harmonics. These are surfaced as `warnings` within
   `metrics.json`.
4. **Baseline against measurement.** The complete chain is run against a
   published, measured device, with tolerances declared before the output is
   examined. See
   [`../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md`](../examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md).
   The *chain* is validated at this level.
5. **Acceptance targets, per design**, sourced to the project requirement or to
   the literature, and carrying `must`/`should`/`info` severity. The *design* is validated
   at this level.

---

## 4. Operation Under Agent Control

The flow has been constructed for execution by Claude Code as readily as by an
operator. The properties by which this is achieved are as follows.

- **A single input file.** One `design.yaml` is held per PIC. A change is
  proposed by editing exactly one field, or probed without editing by means of
  `--set grating.length_um=9000`.
- **A single output file.** Every quantity, the resolved design, the environment
  fingerprint and the warnings are carried by `metrics.json`. Log parsing is not
  required.
- **Exit codes as the branch condition.** 0 indicates that targets are met, 1
  that a stage has raised, 2 that verification has failed, and 3 that the
  invocation was malformed.
- **A written operating manual.**
  [`../design-chain/PICCHAIN_REFERENCE.md`](../design-chain/PICCHAIN_REFERENCE.md) states the loop, the
  exit-code contract, the correspondence between each control and the quantity it
  moves, and — of equal importance — the boundaries of what is modelled, so that
  coverage is not assumed where it is absent.
- **A sweep primitive provided natively.** `picchain sweep --param ... --values
  ... --metric ...` returns one JSON row per point, by which sensitivity
  questions are answered without bespoke scripting. Both quantitative findings
  recorded in the baseline report were obtained from two such commands.

The intended loop is:

```
run → read verify.rows → change one field → run → …
```

with the operator retained in the loop for decisions that carry cost — platform
selection, target changes, tape-out — and with sweeping, bisection and
book-keeping delegated to the agent. **A target is never edited in order to make
a run pass.** Where a target is incorrect, that condition constitutes a finding
to be stated and sourced, and not a quantity to be relaxed.

---

## 5. Mapping onto a Programme Plan

The flow is agnostic to any particular programme structure, but the
correspondence between a typical PIC development plan and the chain is
consistent:

| programme activity | correspondence in this flow |
|---|---|
| upgrade the simulation framework with measured component data | the provenance fields of `pdk/materials.yaml`; the `# ASSUMPTION:` register in each design file constitutes the work list |
| design several PICs in parallel | one folder per PIC beneath the project `designs/` directory, with a shared platform file incorporated by `extends:` |
| **DRC-clean GDSII milestone** | the `layout` and `drc` stages; `drc.error_violations == 0` is declared as a `must` target on every design |
| fabricate and characterise | the same target lists are adopted as test limits; measured values are returned into a project materials file by `pymeasure`/`autosweep`, clearing `needs_confirmation` |
| RF board design | the `scikit-rf` insertion point |
| system integration | the `SAX` insertion point: per-block S-parameters are assembled into a system model and compared against the earlier prediction |

The DRC-clean GDSII milestone is the one most directly addressed by the flow,
and it is already exercised end to end.

A project may record its own mapping, against its own work-package codes and
dates, within its project folder. Such a mapping is project information and is
not held here.

---

## 6. Declared Limits

The following are stated so that capability is not assumed where it is absent.

- **FDTD is present for the taper only, and by effective index.** meep is
  reached through WSL 2 and solves the width taper, in two dimensions by
  default. MMIs, bends, directional couplers and facet coupling have no
  geometry description in the chain and are not simulated; their loss figures in
  the design files remain assumptions. The vertical radiation channel requires
  `fdtd.dimensions: 3`, which is an offline job rather than a chain stage.
- **The travelling-wave model is quasi-static.** `eo.travelling_wave` gives the
  microwave index, the characteristic impedance, the conductor loss and the
  electro-optic bandwidth, from the capacitance solved with and without the
  dielectrics. It does not carry the microwave field pattern, the substrate mode
  or radiation from the line, for which a microwave eigenmode solve is required.
  The lumped `eo.lumped_RC_bandwidth_MHz` is retained beside it and is now known
  to understate the bandwidth of a long electrode by an order of magnitude; a
  warning is raised where the two diverge.
- **Thermal and stress/piezoelectric models are absent.** The 19.8 MHz
  bulk-acoustic resonance and the 70 kHz mechanical mode measured in the
  reference paper are not predicted.
- **The mode solver is semi-vectorial with a diagonal permittivity tensor.** This
  is correct for quasi-TE in X-cut LN/LT. Magneto-optic non-reciprocity (as
  required by an isolator) and strongly hybridised modes are outside its scope.
  The `fem` stage measures the polarisation purity of the mode, which is the
  quantity that bounds the error of the semi-vectorial assumption on any given
  cross-section, and it was found to be 0.996 on the validation baseline.
- **The finite-element cross-check cannot pose the anisotropic problem.** One
  scalar permittivity per element is carried by the solver. The solve is
  therefore performed at the principal axis the semi-vectorial operator reads,
  which holds the permittivity model fixed and isolates the operator and the
  mesh. The second principal axis is solved separately, and the pair brackets
  the anisotropic answer. The bracket is wide on a strongly birefringent film,
  and is reported weighted by the polarisation purity for that reason.
- **The laser model is single-mode and steady-state.** Rate-equation dynamics, a
  relative-intensity-noise model and the self-injection-locking regime are
  excluded. The SMSR figure in particular is model-dependent, scaling with the
  assumed n_sp, and is to be read as an ordering rather than as an absolute
  value.
- **`scikit-rf` is installed with the circuit extras and used by no stage.**
  Availability is reported by `picchain doctor`; use is not.
- **Bend loss is bounded rather than computed.** The `bend` stage gives the bend
  mode and the radius at which the radiation caustic reaches the guide. It
  refuses radii beyond that point rather than returning the wall-bound artefact
  a conformal transformation produces there, so a loss in decibels per turn
  still requires a leaky-mode or time-domain solve.
- **Fill is placed against a declared pattern, and the pattern is a
  placeholder.** The `mask` stage places fill on the lattice, pitch and
  exclusion given to it, and re-measures the density afterwards. Those three
  figures are a foundry statement, and until one is obtained the values in the
  design file are assumptions like any other.
- **Mask polarity is expressed as a derived layer.** `layout.derived_layers`
  produces a layer by boolean operation on the drawn ones, so an inverse tone is
  a field minus a feature rather than a second drawing. The layer table is
  exported beside the mask, as KLayout properties and as a plain map.
- **The crystal orientation is drawn and reported, and it is not modelled.** The
  key on the die states the axis the device must be aligned to, and a declared
  misalignment raises a warning. The permittivity tensor is not rotated, so a
  misaligned device is flagged rather than computed.
- **Connectivity is compared against a schematic; no device is recognised.**
  Text on the label layer names the net it sits on, and the named nets are
  compared against `mask.schematic`. That establishes that the things declared
  to be one net are one net. It does not establish what the connected thing is,
  so a short through the wrong component would present as a correct net.
- **One die is assembled, and no step and repeat across a reticle field is
  performed.** Arraying is carried out against the foundry frame.
- **The mode on the far side of a facet is declared, not solved.** The `facet`
  stage separates overlap, Fresnel and the facet angle, and computes the guide
  mode at the taper tip, but the gain-chip or fibre mode is an elliptical
  Gaussian of the mode-field diameters supplied to it.

The order in which these are to be closed is given in §2.4. The two low-cost
cross-checks that preceded them have both been taken: κ is evaluated
independently by Bloch band structure, and the cross-section is evaluated
independently by finite elements.
