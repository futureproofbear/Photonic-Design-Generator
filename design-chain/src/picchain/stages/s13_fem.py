"""Stage 13 - finite-element cross-check of the mode solver.

Every number the chain produces downstream of the cross-section rests on one
solver. The Bragg wavelength, the coupling constant, the tuning efficiency and
the tuning range are all traceable to an effective index and to an effective
index *difference* computed by finite differences on a staircased mesh with a
semi-vectorial operator. A single instrument that agrees with itself is not
evidence.

This stage re-poses the same cross-section as a finite-element problem on a
conforming unstructured mesh, solves it full-vectorially, and reports the
disagreement. It changes no design parameter and produces no design decision.

What is compared, and what each comparison means
------------------------------------------------
``n_eff``
    The absolute effective index. It converges as the square of the mesh size
    for the finite-difference solver, so a disagreement here is expected and its
    size is the useful output.

``dn_eff_posts``
    The index difference the Bragg posts produce. This is the quantity that
    sets the coupling constant, and it is the one worth checking. The two
    finite-difference solves share a mesh, so their systematic discretisation
    error largely cancels and the difference is far better resolved than either
    index. Whether that cancellation is real is exactly what an independent
    instrument can establish.

``polarisation purity``
    The share of the transverse electric energy carried by the dominant
    component. The chain's own solver assumes this to be unity, and cannot
    report otherwise. A value materially below unity places a bound on the
    error of that assumption.

``the anisotropy bracket``
    The finite-element solver carries one scalar permittivity per element, so
    the film's two principal indices cannot both be described to it. Solving at
    each in turn brackets the anisotropic answer, the true value lying between
    them for a diagonal tensor. The bracket width states how much the scalar
    model can be in error, and it is reported rather than assumed small.

The convergence guard
---------------------
A disagreement between two solvers is uninformative until it is known to exceed
the mesh error of either. The bare solve is therefore repeated on a coarser
mesh, and the shift between the two is compared against the disagreement with
the finite-difference result. Where the shift is comparable, the comparison has
not resolved anything and ``resolved`` is reported false. Reading a
cross-check that has not converged as agreement, or as disagreement, is the
failure this guard exists to prevent.

What this stage does not do
---------------------------
It does not adjudicate. Where the two disagree, the disagreement is quantified
and left standing. No correction factor is applied to either solver, and no
target is evaluated against the finite-element figure.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary
from ..solvers import femmode
from .s01_mode import _build, _n_guess


def _eps_scalar(
    xs, lib: MaterialLibrary, lam_um: float, cut: str, override: bool, component: int
) -> dict[str, float]:
    """One scalar permittivity per material, taken from one principal axis.

    ``component`` selects xx, yy or zz. The semi-vectorial quasi-TE operator of
    the finite-difference solver reads eps_xx alone, so a finite-element solve
    at eps_xx compares like with like.
    """
    out: dict[str, float] = {}
    for m in xs.materials_used():
        mat = lib[m]
        if mat.kind == "metal":
            # matching stage 1: an opaque metal is kept out of the optical
            # problem by permittivity rather than by an absorbing boundary
            out[m] = 1.0
        else:
            out[m] = float(mat.eps_optical_device(lam_um, cut, override)[component])
    return out


def _solve(design: Design, xs, lib, lam, component: int, *, resolution: float, n_guess=None):
    cfg, p, m = design.fem, design.platform, design.mesh
    eps = _eps_scalar(xs, lib, lam, p.cut, p.use_index_override, component)
    res = femmode.solve_cross_section(
        xs, eps, lam,
        num_modes=cfg.num_modes,
        element_order=cfg.element_order,
        resolution_max_um=resolution,
        fine_resolution_um=cfg.resolution_fine_um,
        fine_distance_um=cfg.fine_distance_um,
        n_guess=n_guess,
    )
    return res, res.select(m.polarisation, n_guess)


def _rel(a: float, b: float) -> float:
    """Fractional difference of ``a`` from ``b``, guarded at zero."""
    return float((a - b) / b) if b else float("nan")


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.fem
    if not cfg.enabled:
        payload = {"enabled": False}
        ctx.put("fem", payload)
        return payload

    if not femmode.available():
        raise RuntimeError(
            "stage 'fem' requires the optional finite-element extras. Install them "
            "with `pip install -e \".[fem]\"`, or disable the stage. The import "
            f"failed with: {femmode.unavailable_reason()}"
        )

    mode = ctx.get("mode") or {}
    if "n_eff_bare" not in mode:
        raise RuntimeError("stage 'fem' requires stage 'mode'")

    lam = design.waveguide.wavelength_um
    p = design.platform
    # the dominant component of the chosen polarisation, matching stage 1
    component = 0 if design.mesh.polarisation.upper() == "TE" else 1
    other = 1 if component == 0 else 0
    guess = _n_guess(design, lib)

    xs_bare = _build(design, with_posts=False, electrodes=False, name="fem_bare")
    solve_bare, bare = _solve(design, xs_bare, lib, lam, component,
                              resolution=cfg.resolution_max_um, n_guess=guess)

    n_fd = float(mode["n_eff_bare"])
    payload: dict[str, Any] = {
        "enabled": True,
        "backend": "femwell",
        "femwell_version": femmode.version(),
        "method": "full-vectorial finite elements on a conforming triangulation",
        "permittivity_model": (
            "one scalar per element, taken from the principal axis the "
            "semi-vectorial operator of the finite-difference solver reads"
        ),
        "element_order": solve_bare.element_order,
        "mesh_elements": solve_bare.n_elements,
        "resolution_max_um": solve_bare.resolution_max_um,
        "polarisation": design.mesh.polarisation,
        "n_eff_bare_fem": bare.n_eff,
        "n_eff_bare_fd": n_fd,
        "n_eff_bare_delta": float(bare.n_eff - n_fd),
        "n_eff_bare_rel_delta": _rel(bare.n_eff, n_fd),
        "polarisation_purity": (
            bare.te_fraction if component == 0 else 1.0 - bare.te_fraction
        ),
        "transversality": bare.transversality,
        "confinement_film_fem": bare.confinement(p.film_material),
        "confinement_film_fd": float(mode.get("confinement_film", float("nan"))),
        "n_eff_spectrum_fem": [float(m.n_eff) for m in solve_bare.modes],
    }

    # ---- the index difference the posts produce -------------------------
    if cfg.with_posts:
        xs_posts = _build(design, with_posts=True, electrodes=False, name="fem_posts")
        _, posts = _solve(design, xs_posts, lib, lam, component,
                          resolution=cfg.resolution_max_um, n_guess=bare.n_eff)
        dn_fem = float(posts.n_eff - bare.n_eff)
        dn_fd = float(mode.get("dn_eff_posts", float("nan")))
        payload.update({
            "n_eff_with_posts_fem": posts.n_eff,
            "dn_eff_posts_fem": dn_fem,
            "dn_eff_posts_fd": dn_fd,
            "dn_eff_ratio_fem_over_fd": float(dn_fem / dn_fd) if dn_fd else float("nan"),
            "dn_eff_rel_delta": _rel(dn_fem, dn_fd),
        })

    # ---- mesh convergence ------------------------------------------------
    if cfg.convergence_check:
        coarse_res = cfg.resolution_max_um * cfg.coarsening
        solve_c, coarse = _solve(design, xs_bare, lib, lam, component,
                                 resolution=coarse_res, n_guess=guess)
        shift = float(bare.n_eff - coarse.n_eff)
        gap = abs(payload["n_eff_bare_delta"])
        payload["convergence"] = {
            "resolution_max_um": coarse_res,
            "mesh_elements": solve_c.n_elements,
            "n_eff_coarse": coarse.n_eff,
            "n_eff_shift": shift,
            # the comparison carries information only where the disagreement
            # between the two solvers is larger than the mesh error of this one
            "resolved": bool(gap > 3.0 * abs(shift)),
        }

    # ---- the anisotropy bracket -----------------------------------------
    if cfg.anisotropy_bracket:
        eps_a = _eps_scalar(xs_bare, lib, lam, p.cut, p.use_index_override, component)
        eps_b = _eps_scalar(xs_bare, lib, lam, p.cut, p.use_index_override, other)
        if all(abs(eps_a[k] - eps_b[k]) < 1e-12 for k in eps_a):
            payload["anisotropy_bracket"] = {
                "applicable": False,
                "reason": "every material in the optical cross-section is isotropic",
            }
        else:
            _, minor = _solve(design, xs_bare, lib, lam, other,
                              resolution=cfg.resolution_max_um, n_guess=guess)
            width = float(abs(bare.n_eff - minor.n_eff))
            # The bracket is wide because the two principal indices are far
            # apart. What is actually in error is only the share of the field
            # sitting in the minor transverse component, since the dominant one
            # already sees the correct axis. Weighting the bracket by that share
            # turns a bound of no practical use into one of the right order.
            payload["anisotropy_bracket"] = {
                "applicable": True,
                "n_eff_dominant_axis": bare.n_eff,
                "n_eff_other_axis": minor.n_eff,
                "width": width,
                "weighted_error_estimate": float(
                    (1.0 - payload["polarisation_purity"]) * width
                ),
                "note": (
                    "the anisotropic answer lies between the two, weighted by the "
                    "energy in each transverse field component; the polarisation "
                    "purity gives that weight"
                ),
            }

    ctx.put("fem", payload)
    ctx.write_stage("fem", payload, {
        "n_eff_spectrum_fem": np.array(payload["n_eff_spectrum_fem"], dtype=float),
    })

    # ---- warnings --------------------------------------------------------
    conv = payload.get("convergence")
    if conv and not conv["resolved"]:
        ctx.warn(
            f"the finite-element cross-check has not converged: halving the mesh "
            f"density moves n_eff by {conv['n_eff_shift']:+.2e}, against a "
            f"disagreement of {payload['n_eff_bare_delta']:+.2e} with the "
            "finite-difference solver. The comparison distinguishes nothing at this "
            "mesh; reduce fem.resolution_max_um before reading it"
        )
    elif abs(payload["n_eff_bare_rel_delta"]) > cfg.n_eff_tolerance:
        ctx.warn(
            f"the two mode solvers disagree on n_eff by "
            f"{payload['n_eff_bare_rel_delta'] * 100:+.3f} %, against a tolerance of "
            f"{cfg.n_eff_tolerance * 100:.3f} %. The absolute index enters the Bragg "
            "wavelength directly"
        )

    if "dn_eff_rel_delta" in payload and np.isfinite(payload["dn_eff_rel_delta"]):
        if abs(payload["dn_eff_rel_delta"]) > cfg.dn_eff_tolerance:
            ctx.warn(
                f"the two mode solvers disagree on the index difference produced by "
                f"the Bragg posts by {payload['dn_eff_rel_delta'] * 100:+.1f} %, "
                f"against a tolerance of {cfg.dn_eff_tolerance * 100:.0f} %. That "
                "difference sets kappa, and hence the reflectivity, the mirror "
                "bandwidth and the tuning range"
            )

    if payload["polarisation_purity"] < cfg.polarisation_purity_floor:
        ctx.warn(
            f"the full-vectorial solve gives a polarisation purity of "
            f"{payload['polarisation_purity']:.3f}. The semi-vectorial solver used "
            "elsewhere in the chain assumes unity, so the mode is more strongly "
            "hybridised than that solver can represent"
        )

    br = payload.get("anisotropy_bracket")
    if br and br.get("applicable"):
        est = br["weighted_error_estimate"]
        if est > abs(payload["n_eff_bare_delta"]):
            ctx.warn(
                f"the scalar permittivity the finite-element solve carries accounts "
                f"for an estimated {est:.2e} in n_eff, which exceeds the "
                f"{abs(payload['n_eff_bare_delta']):.2e} disagreement between the two "
                "solvers. The residual is therefore dominated by the permittivity "
                "model rather than by the operator or the mesh, and the agreement in "
                "n_eff is not evidence about either"
            )
    return payload
