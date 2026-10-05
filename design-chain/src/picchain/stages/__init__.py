"""Chain stages.

Each stage exposes ``run(design, ctx, lib) -> dict`` and is pure with respect to
the run directory: it reads earlier stages' metrics from ``ctx`` (and their
``.npz`` files from ``ctx.run_dir``) and writes its own.
"""

from . import (
    s01_mode, s02_grating, s03_eo, s04_cavity, s05_layout, s06_drc, s07_verify,
    s08_taper, s09_fdtd, s10_bend, s11_facet, s12_mask, s13_fem, s14_reticle, s15_release, s16_circuit,
    s17_dynamics, s18_modulator, s19_resonator,
)

STAGES = {
    "mode": s01_mode.run,
    "taper": s08_taper.run,
    "fem": s13_fem.run,
    # `grating` precedes `fdtd` because `fdtd` depends on it. The planner
    # sorts topologically and would order the pair correctly either way,
    # and a declared order contradicting the map still does harm: it
    # decides every tie against a stage whose dependencies keep it waiting.
    "grating": s02_grating.run,
    "fdtd": s09_fdtd.run,
    "bend": s10_bend.run,
    "facet": s11_facet.run,
    "eo": s03_eo.run,
    "modulator": s18_modulator.run,
    "cavity": s04_cavity.run,
    "dynamics": s17_dynamics.run,
    "circuit": s16_circuit.run,
    # Registered after `fdtd` and `grating` rather than beside `bend`, and the
    # position is load-bearing. The planner sorts topologically and breaks ties
    # by registration order, so a stage that READS another optionally, without
    # declaring it a dependency, is ordered only by where it sits here. This
    # stage takes the power coupling from `fdtd` where that stage solved a
    # coupler. Registered beside `bend` it ran first, took the declared value
    # instead of the measured one, and reported it as declared, which is visible
    # only to a reader who checks `kappa_squared_source`.
    "resonator": s19_resonator.run,
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
    # the loop needs the group index; the coupling is read from the fdtd
    # stage where that stage ran, and declared in the design file where it
    # did not, so fdtd is not made a dependency of a closed-form stage
    "resonator": ["mode"],
    "facet": ["mode"],
    "grating": ["mode"],
    "eo": ["mode", "grating"],
    # the device figures are the arm figures the electro-optic stage returns,
    # converted for the interferometer the arms sit in
    "modulator": ["eo"],
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
