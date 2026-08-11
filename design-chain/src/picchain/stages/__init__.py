"""Chain stages.

Each stage exposes ``run(design, ctx, lib) -> dict`` and is pure with respect to
the run directory: it reads earlier stages' metrics from ``ctx`` (and their
``.npz`` files from ``ctx.run_dir``) and writes its own.
"""

from . import (
    s01_mode, s02_grating, s03_eo, s04_cavity, s05_layout, s06_drc, s07_verify,
    s08_taper, s09_fdtd, s10_bend, s11_facet, s12_mask, s13_fem, s14_reticle, s15_release, s16_circuit,
    s17_dynamics,
)

STAGES = {
    "mode": s01_mode.run,
    "taper": s08_taper.run,
    "fem": s13_fem.run,
    "fdtd": s09_fdtd.run,
    "bend": s10_bend.run,
    "facet": s11_facet.run,
    "grating": s02_grating.run,
    "eo": s03_eo.run,
    "cavity": s04_cavity.run,
    "dynamics": s17_dynamics.run,
    "circuit": s16_circuit.run,
    "layout": s05_layout.run,
    "reticle": s14_reticle.run,
    "drc": s06_drc.run,
    "mask": s12_mask.run,
    "verify": s07_verify.run,
    "release": s15_release.run,
}

#: stages that must have run before a given stage
DEPENDENCIES = {
    "mode": [],
    "taper": ["mode"],
    # the cross-check needs the finite-difference result to disagree with
    "fem": ["mode"],
    # grating is required for the period and for the three-dimensional kappa the
    # grating cross-check reports alongside its own; it costs seconds
    "fdtd": ["mode", "grating"],
    "bend": ["mode"],
    "facet": ["mode"],
    "grating": ["mode"],
    "eo": ["mode", "grating"],
    "cavity": ["grating", "eo"],
    "dynamics": ["cavity"],
    # the assembly reads the transfer-matrix spectrum the grating stage wrote
    "circuit": ["mode", "grating"],
    "layout": ["grating"],
    # the die is assembled from the device cell the layout stage emitted
    "reticle": ["layout"],
    "drc": ["layout"],
    "mask": ["layout"],
    "verify": [],
    # the manifest inventories what the earlier stages emitted
    "release": ["layout"],
}

__all__ = ["STAGES", "DEPENDENCIES"]
