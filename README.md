# Photonic Design Generator

A design, simulation and verification generator for photonic integrated
circuits, operated without a graphical interface and drivable by an agent. A
design is expressed as a single YAML file carrying its own acceptance criteria;
the chain returns a JSON metric tree and a non-zero exit code where those
criteria are unmet.

The repository is organised so that reusable capability and client-proprietary
work are kept strictly apart, and so that the separation is enforced
mechanically rather than by convention.

```
Photonic-Design-Generator/
├── design-chain/       the toolchain: solvers, stages, CLI, PDK, tests   [GENERIC]
├── docs/               methodology: the flow, the toolset, its limits    [GENERIC]
├── .claude/            skills, sub-agents and the sanitised lessons ledger [GENERIC]
├── examples/           validation designs drawn from public literature   [GENERIC]
├── references/         public literature underpinning the examples       [GENERIC]
├── tools/              the IP boundary check                        [GENERIC]
└── projects/           one folder per design scope             [PROPRIETARY]
    ├── _template/          copy this to start a new scope
    └── <scope>/            self-contained: designs, docs, references, PDK
```

## The IP Boundary

**Everything outside `projects/` is generic and shareable. Everything inside a
project folder is proprietary to that project and must not leave it.**

Capability flows inward. Project information never flows outward. Where a
technique developed within a project is of general value, it is to be
re-expressed without project-identifying content and contributed to
`design-chain/`, `docs/` or `.claude/skills/` as a separate, sanitised change.

The boundary is enforced by a check rather than by recollection. Each project
declares its own `proprietary_terms.txt`; the checker reads every such list and
searches for those terms across the generic tree only.

```bash
python tools/check_ip_boundary.py
```

A non-zero exit code is returned where a project term is found outside its own
folder. The check is to be run before any commit and before any part of the
generator is shared.

## Entry Points

| objective | document |
|---|---|
| understand the design, simulation and verification flow | [docs/design_simulation_verification_flow.md](docs/design_simulation_verification_flow.md) |
| **operate the chain** | [design-chain/PICCHAIN_REFERENCE.md](design-chain/PICCHAIN_REFERENCE.md) |
| assess whether the toolchain is trustworthy | [examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md](examples/edbr_tfln_baseline/TOOLCHAIN_VALIDATION.md) |
| install and execute the chain | [design-chain/PICCHAIN_REFERENCE.md](design-chain/PICCHAIN_REFERENCE.md) |
| start a new design scope | [projects/README.md](projects/README.md) |
| accumulated design knowledge | [.claude/skills/](.claude/skills/) and [.claude/LESSONS.md](.claude/LESSONS.md) |

## Prerequisites

**Nothing below is needed to run the chain's own solvers.** Python and the
declared dependencies compute the cross-section, the grating, the electrodes and
the cavity, and produce a mask. The external tools are needed for the checks
that make a mask submittable and for the independent cross-checks, and each
stage that wants one reports its absence rather than failing.

`python -m picchain.cli doctor` names what is missing and what to install.

### Required

**Python 3.11 or later.** Declared as 3.10 in `pyproject.toml` and developed on
3.13. Where the Luxtelligence PDK is installed alongside it, note that the kit
declares `requires-python = "~=3.12"`.

Everything else required arrives with `pip install -e design-chain`.

### For a mask that could be submitted

**The KLayout application**, from <https://www.klayout.de/build.html>. This is
**not** the `klayout` Python module, which is a required dependency and arrives
with the install. The application is what executes a foundry rule deck, and
`drc.deck` cannot run without it. The usual install locations on Windows, macOS
and Linux are searched, and `drc.klayout_exe` names it explicitly.

Without it the `drc` stage runs only the rules declared in the design file.
Those are a smoke test and they are not a foundry check.

### For the independent cross-checks — the part that wants Linux

**MEEP and MPB**, for the `fdtd` stage: a time-domain solve of the taper, and
the photonic band structure that yields a coupling constant independent of
coupled-mode theory.

| host | how it is reached |
|---|---|
| Linux, macOS | natively, through a `micromamba` environment |
| **Windows** | **through WSL** &mdash; the chain shells out to `wsl.exe -d <distro>` |

On Windows this is a genuine Linux requirement rather than a convenience. MEEP
has no native Windows build, so a WSL distribution must be installed with MEEP
in a `micromamba` environment inside it, and `fdtd.wsl_distro` and
`fdtd.environment` set to match. `picchain doctor` reports whether that
environment can be reached.

**Budget the time before enabling it.** A converged band structure at resolution
40 takes about **three hours**, and its convergence guard solves the structure a
second time. The other sixteen stages together take about fifteen minutes. See
"Running the Chain Efficiently" in
[`design-chain/PICCHAIN_REFERENCE.md`](design-chain/PICCHAIN_REFERENCE.md).

### Optional extras

```bash
pip install -e "design-chain[layout]"    # gdsfactory: a second mask writer,
                                         # compared against the first
pip install -e "design-chain[fem]"       # femwell, gmsh: an independent mode
                                         # solver on a conforming mesh
pip install -e "design-chain[circuit]"   # sax: circuit assembly by S-matrix
pip install -e "design-chain[dev]"       # pytest
```

## Quick Start

The commands below use a Windows virtual environment. On Linux or macOS the
interpreter is `.venv/bin/python`, or simply `picchain` where the environment is
active.

**The smallest thing that works.** No external tool, about a minute:

```bash
cd design-chain
python -m pip install -e .
python -m picchain.cli run ../examples/minimal_ridge/design.yaml
```

One cross-section, one first-order mirror, three targets. Exit 0 means every
`must` target was met; exit 2 means one was not, and `runs/<id>/metrics.json`
says which.

```bash
cd design-chain
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[layout]"
./.venv/Scripts/python.exe -m pip install -e ".[fem]"      # optional cross-check solver
./.venv/Scripts/python.exe -m picchain.cli doctor
./.venv/Scripts/python.exe -m pytest tests/ -q            # closed-form solver tests

# the public validation baseline
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml

# the same cross-section by an independent numerical method
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml \
       --stages mode,fem --set fem.enabled=true

# a mask that could be submitted: every period, the die frame and its monitors,
# a ladder of device copies, the fill placed, the die checked, and a manifest
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml \
       --set layout.draw_periods=null --set layout.require_complete=true \
       --set reticle.enabled=true --set reticle.split.enabled=true \
       --set drc.target=die --set mask.target=die \
       --set mask.fill.enabled=true --set release.enabled=true

# the emitted mask against its stored reference
./.venv/Scripts/python.exe -m picchain.cli golden ../examples/edbr_tfln_baseline/design.yaml

# one self-contained HTML page: which stages ran and when, which targets are met
# and by how much, and what the run raised that no target expresses
./.venv/Scripts/python.exe -m picchain.cli dashboard        ../examples/edbr_tfln_baseline/design_candidate.yaml --open
```

The full extended-DBR chain executes in approximately 50 s on a single core,
without a graphical interface and without a licence server.

## Present Capability

Seventeen stages are implemented, covering an extended-DBR laser from
cross-section through to a die with a submission manifest:

```
mode → taper → fem → fdtd → bend → facet → grating → eo → cavity → circuit
     → layout → reticle → drc → mask → verify → release
```

Two quantities are computed twice by unrelated methods. The cross-section is
solved by finite differences and, in the `fem` stage, by finite elements. The
coupling constant is constructed by coupled-mode theory and, in the `fdtd`
stage, measured from the photonic band gap.

The emitted die carries a seal ring, a dicing lane, nested overlay marks, a
label and process control monitors. The difference between the dimension drawn
and the dimension printed is expressed rather than assumed: a declared bias
draws the mask pre-compensated and the physics is solved on the printed
geometry.

MMIs and facet coupling are **not** yet simulated in three dimensions, nor are
thermal or piezoelectric effects, or magneto-optic non-reciprocity. No device is
recognised by the connectivity check, and the fill pattern is a placeholder
until a foundry states one. The gaps are enumerated in
[docs/design_simulation_verification_flow.md §6](docs/design_simulation_verification_flow.md)
and in [design-chain/PICCHAIN_REFERENCE.md](design-chain/PICCHAIN_REFERENCE.md), so that capability is
not assumed where it is absent.

## Accumulation of Knowledge

The generator is intended to improve across successive design scopes. Two
mechanisms are provided:

* **Skills** in `.claude/skills/` hold transferable design knowledge — the
  physics, the sensitivities, the failure modes and the correspondence between
  each control and the quantity it moves.
* **A lessons ledger** in `.claude/LESSONS.md` records what was learnt from each
  completed design activity, in sanitised form.

Both are located outside `projects/` and are therefore covered by the
IP boundary check. Entries are required to be stated as general technical
findings. No client, programme, application, deliverable code or specific design
parameter set is to be recorded. The procedure is defined in
[.claude/LESSONS.md](.claude/LESSONS.md).
