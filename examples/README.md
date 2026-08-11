# Examples

Validation designs drawn from public literature. These are generic and
shareable. No project-proprietary content is permitted here, and the boundary
check enforces that.

```
examples/
  edbr_tfln_baseline/
    design.yaml                  the device, its acceptance targets and its process corners
    TOOLCHAIN_VALIDATION.md      what the chain reproduces, and every disagreement quantified
    DESIGN_REPORT.md             what the design is, written for a reader new to it
    smoke_deck.drc               a demonstration rule deck, exercising the foundry-deck path
    sweep_post_gap.json          the sensitivity of kappa to the post gap
    sweep_sidewall.json          the sensitivity to the sidewall angle
```

Two documents accompany the design and answer different questions.
`TOOLCHAIN_VALIDATION.md` asks whether the instrument is calibrated;
`DESIGN_REPORT.md` presents the measurement that instrument produced.

## Purpose

An example exists so that the toolchain can be shown to reproduce a **published,
measured** device before it is applied to work whose answer is not known in
advance. Tolerances are declared before the output is examined, and no quantity
is adjusted in order to obtain agreement.

Where a chain result and a published result disagree, that disagreement is
recorded and quantified rather than reconciled by adjustment. Two of the more
useful findings held in `.claude/LESSONS.md` were obtained in exactly this way.

## Execution

```bash
cd ../design-chain
./.venv/Scripts/python.exe -m picchain.cli run ../examples/edbr_tfln_baseline/design.yaml
```

## Adding an Example

An example is admissible where:

1. the device is described in public literature, with sufficient geometry stated
   for the chain to be run from that description alone;
2. measured performance figures are published against which the result may be
   compared;
3. the acceptance targets cite the publication, and are declared before the
   chain is run;
4. no project-proprietary content is involved, whether in the geometry, the
   targets or the commentary.

The supporting publication is placed in `../references/`. Client documents are
never placed there; they belong in the project folder that received them.
