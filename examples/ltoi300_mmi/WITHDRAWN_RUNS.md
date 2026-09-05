# Withdrawn runs of this example

Run artifacts are excluded from version control by `.gitignore`, so the
withdrawal notice held beside each run does not travel with the repository. The
notices are reproduced here, which is the tracked record.

Three of the run directories also carry their own `WITHDRAWN.md` in a working
copy where the run tree exists: `20260905-160542`, `20260905-161543` and
`20260905-162912`. The seven taper runs withdrawn for the boundary defect carry
no such file and are recorded here only.

Ten runs are withdrawn in total.

## `20260905-160542-ltoi300_mmi1x2_cband_3d`

The payload of this run is stamped `dimensions: 3` and carries a two-dimensional
result. It is retained as the evidence for the defect and for no other purpose.
No figure of it may be quoted.

### What produced it

`fdtd.structure: mmi` is solved by `meep_mmi.py`, which builds every shape with
an infinite extent in the third axis and whose background index is the effective
index of the film. The runner is two-dimensional by construction. The stage
recorded `fdtd.dimensions` in the payload of every structure and passed it to
the runner of one, `taper` being the only structure whose runner reads the layer
stack. The declared value was therefore recorded and never acted on.

The job dictionary omitted the field as well, so the content key of this job
equalled that of run `20260905-160444`, which had solved the same geometry in
two dimensions, and the solver was not invoked. `meep_mmi_run.log` records the
reuse and names that run. The transmission of 0.977346 agrees with it to every
digit written, and the payload also carries `n_core_effective_index`, which is a
quantity of the two-dimensional reduction. The run took 13.9 seconds.

### What was changed

`s09_fdtd.py` refuses a dimensionality its runner does not build, before the
solver environment is probed. The same design now fails at the `fdtd` stage in
5.7 seconds with the field and the remedy named, which is run
`20260905-161123`. Every job dictionary carries its dimensionality, so a
two-dimensional solve can no longer satisfy a three-dimensional request. The
conditions are held by `design-chain/tests/test_fdtd_dimensions.py`.

### The denominator

Sixteen FDTD payloads are held under `examples/`. One carried a dimensionality
its runner does not build, and it is this one. The fifteen others declare two
dimensions and were solved in two dimensions.

### The standing figure

The two-dimensional result for this splitter is run `20260905-160444`:
transmission 0.977346, excess loss 0.0995 dB, imbalance 0.0 dB, reflection
5.1e-05. Its tapers are shortened to 5 um and its leads to 1 um, so it is not
comparable with the full-length splitter of `20260903-164912`. The vertical
radiation channel is absent from a two-dimensional solve, and the excess loss is
therefore a lower bound.

## `20260905-161543-ltoi300_access_taper_3d`

The three-dimensional cell was filled with the wrong ambient index. No figure of
this run may be quoted.

### What produced it

`_effective_indices` in `s09_fdtd.py` returns two quantities of the plane
reduction: the effective index of the slab through the ridge, and the effective
index of the unetched film beside it. The second is passed to the runner as
`n_clad`, and `meep_taper.py` used it as `default_material` for the whole cell
in both dimensionalities.

In two dimensions that is the reduction and is correct. In three dimensions the
runner builds the slab and the ridge explicitly at the film index, so the
surround is the cladding and the buried oxide. Using the slab's effective index
there places the slab a second time and fills the cell with a medium of 1.5509,
which exists nowhere in the device. The cladding of this stack is 1.4440.

The error raises the index of everything outside the guide by 0.107, which
weakens the lateral and vertical confinement of every cross-section in the
problem and leaves a continuous 0.12 um slab of index 2.152 guiding in an
ambient it should not be guiding against.

### What was changed

The taper job carries `n_ambient`, the higher of the cladding and the buried
oxide, and the three-dimensional cell is filled with it. The plane reduction
continues to use `n_clad`, which is what the reduction means. Held by
`design-chain/tests/test_fdtd_dimensions.py`.

### The record

This run was made while the first three-dimensional solve of the repository was
being brought up. Its two-dimensional counterpart is unaffected, the reduction
being the case the index was correct for.

## `20260905-162912-ltoi300_access_taper_3d`

The three-dimensional cell was filled with the wrong ambient index. No figure of
this run may be quoted.

### What produced it

`_effective_indices` in `s09_fdtd.py` returns two quantities of the plane
reduction: the effective index of the slab through the ridge, and the effective
index of the unetched film beside it. The second is passed to the runner as
`n_clad`, and `meep_taper.py` used it as `default_material` for the whole cell
in both dimensionalities.

In two dimensions that is the reduction and is correct. In three dimensions the
runner builds the slab and the ridge explicitly at the film index, so the
surround is the cladding and the buried oxide. Using the slab's effective index
there places the slab a second time and fills the cell with a medium of 1.5509,
which exists nowhere in the device. The cladding of this stack is 1.4440.

The error raises the index of everything outside the guide by 0.107, which
weakens the lateral and vertical confinement of every cross-section in the
problem and leaves a continuous 0.12 um slab of index 2.152 guiding in an
ambient it should not be guiding against.

### What was changed

The taper job carries `n_ambient`, the higher of the cladding and the buried
oxide, and the three-dimensional cell is filled with it. The plane reduction
continues to use `n_clad`, which is what the reduction means. Held by
`design-chain/tests/test_fdtd_dimensions.py`.

### The record

This run was made while the first three-dimensional solve of the repository was
being brought up. Its two-dimensional counterpart is unaffected, the reduction
being the case the index was correct for.

## Every taper run before `20260905-1847`

The guide was terminated at the inner face of the absorber rather than carried
out through the cell, so the mode met an abrupt end of the ridge exactly where
the absorber began, at both ends. That facet reflects, and it reflects by an
amount that depends on the width of the guide meeting it, so a structure
normalised against a straight guide of a different width inherited the
difference.

Withdrawn on that ground:

| run | note |
|---|---|
| `20260905-161456-ltoi300_access_taper_2d` | plane, 6 x 4 um cell |
| `20260905-162834-ltoi300_access_taper_2d` | plane, 10 x 6 um cell |
| `20260905-170647-ltoi300_access_taper_2d` | plane, after the ambient fix |
| `20260905-180529-ltoi300_access_taper_2d` | plane, and reused a stale result, see below |
| `20260905-180907-ltoi300_access_taper_2d` | plane, with the third simulation |
| `20260905-170719-ltoi300_access_taper_3d` | three dimensions, ambient corrected |
| `20260905-181023-ltoi300_access_taper_3d` | three dimensions, with the third simulation |

The two runs `20260905-161543` and `20260905-162912` are withdrawn above on the
separate ground of the ambient index, and carry this defect as well.

The runs of record are `20260905-184712-ltoi300_access_taper_2d` and
`20260905-184841-ltoi300_access_taper_3d`.

Effect of the correction on the plane reduction: the fundamental-mode reflection
fell from 0.00353 to 0.0000542, the straight guide's loss over its own length
from 0.109 per cent to 0.0002, and the transmission rose from 0.98844 to
0.99475.

## `20260905-180529-ltoi300_access_taper_2d`, additionally

This run returned a cached result. A third simulation and six output fields had
been added to the runner, and the reuse key was computed over the job
dictionary, which had not changed. The payload carries none of the new fields.
The runner's content digest now enters the key.

## The splitter runs

`meep_mmi.py` carried a milder form of the same defect: its leads stopped 0.5 um
inside the absorber while its normalisation guide ran past the cell edge, so the
two runs terminated differently. Re-solving after the correction moved the
shortened splitter's transmission from 0.9773460207584127 to
0.9773462736895905, which is the seventh decimal place. The leads were already
1 um deep into a 1.5 um absorber, where the field is largely attenuated, so the
defect was real and its effect was immaterial. No splitter figure is withdrawn
on this ground.

## `20260905-184712-ltoi300_access_taper_2d`

Superseded rather than withdrawn. Its figures are correct and identical to those
of the run of record, `20260905-204348`, which repeats it after the two
passivity findings were acknowledged in the design. The earlier run carried them
unacknowledged.
