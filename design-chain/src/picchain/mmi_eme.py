"""A multimode splitter by eigenmode expansion, carrying no propagation mesh.

Why this exists
---------------
The time-domain solve of a multimode section will not converge at a mesh this
machine can afford. The output of such a section is set by the relative phase of
several modes after its whole length, a finite-difference scheme carries a
numerical dispersion that makes each phase slightly mesh-dependent, and the
error accumulates over every wavelength travelled. On the LTOI300 kit the 1x2
cells at 15.8 um converge to better than one per cent while both 2x2 cells, at
67.5 and 97.5 um, refuse their convergence guard at resolution 50.

An eigenmode expansion has no such error. Within a uniform section the phase is
``exp(i k0 n_eff L)`` evaluated in closed form, so a section of ninety-seven
micrometres costs exactly what a section of one does and carries the same error,
being that of the mode solve alone. The length stops being a source of error and
becomes a parameter.

What is represented
-------------------
The device is reduced to one lateral coordinate by the effective-index method,
exactly as the two-dimensional time-domain solve reduces it, so the two
instruments may be compared like for like. The stack enters as two indices: the
column through the ridge, and the column through the unetched slab beside it.

The sections are the input guide or guides, a staircase of access-taper slices,
the multimode section, a second staircase, and the output guides. Every
interface is matched by continuity of the transverse fields through
``picchain.eme``, which retains reflection.

What is not represented
-----------------------
Radiation. Only the guided modes of each lateral profile are retained, so power
leaving the guided set at a junction is reported as missing rather than followed.
For a taper drawn over twenty-five micrometres that is a small quantity, and the
sum over the ports states how small on any given structure.

The vertical channel is absent, this being a planar reduction. An excess loss
from this instrument is therefore a lower bound in the same sense as the
two-dimensional time-domain figure.
"""

from __future__ import annotations

import numpy as np

from . import eme
from .solvers.fdmode import solve_lateral_modes


def lateral_profile(x: np.ndarray, centres, width: float,
                    n_core: float, n_background: float) -> np.ndarray:
    """Index along the lateral coordinate for guides of one width."""
    n = np.full_like(np.asarray(x, dtype=float), float(n_background))
    for c in np.atleast_1d(np.asarray(centres, dtype=float)):
        n[np.abs(x - c) <= width / 2.0] = float(n_core)
    return n


def _stack(job: dict, x: np.ndarray):
    """The sections of the device, in order, with their lengths."""
    w, wp = job["width_um"], job["port_width_um"]
    Wm, Lm, Lt = job["mmi_width_um"], job["mmi_length_um"], job["taper_length_um"]
    sep, lead = job["port_separation_um"], job["lead_um"]
    slices = int(job.get("taper_slices", 12))
    n_core, n_bg = job["n_core"], job["n_background"]
    n_modes = int(job.get("num_modes", 10))

    outs = [+sep / 2, -sep / 2]
    ins = [0.0] if int(job["ports_in"]) == 1 else outs

    profiles: list[tuple[np.ndarray, float]] = []
    profiles.append((lateral_profile(x, ins, w, n_core, n_bg), lead))
    for k in range(slices):                       # input access taper
        u = (k + 0.5) / slices
        profiles.append((lateral_profile(x, ins, w + (wp - w) * u, n_core, n_bg),
                         Lt / slices))
    profiles.append((lateral_profile(x, [0.0], Wm, n_core, n_bg), Lm))
    for k in range(slices):                       # output access taper
        u = (k + 0.5) / slices
        profiles.append((lateral_profile(x, outs, wp + (w - wp) * u, n_core, n_bg),
                         Lt / slices))
    profiles.append((lateral_profile(x, outs, w, n_core, n_bg), lead))

    n_effs, fields, lengths = [], [], []
    for prof, L in profiles:
        ne, F = solve_lateral_modes(x, prof, job["wavelength_um"], n_modes,
                                    guided_only=bool(job.get("guided_only", True)))
        n_effs.append(ne)
        fields.append(F)
        lengths.append(float(L))
    return n_effs, fields, lengths, ins, outs


def solve(job: dict) -> dict:
    """Transmission into each output port, the imbalance, and the reflection.

    The launch is the fundamental mode of one input guide, expanded on the modes
    of the first section: where the input plane carries two guides those modes
    are supermodes, and a single guide is their sum. The output is reconstructed
    from the transmitted amplitudes and projected onto the mode of one isolated
    output guide, which is what a measurement at that port would collect.
    """
    span = job.get("window_um") or (2.5 * max(job["mmi_width_um"],
                                              job["port_separation_um"] + 2 * job["width_um"]))
    nx = int(job.get("window_points", 3201))
    x = np.linspace(-span / 2, span / 2, nx)
    dA = np.gradient(x)

    n_effs, fields, lengths, ins, outs = _stack(job, x)
    norm = [eme.normalise(F, dA) for F in fields]

    # the launch: one input guide, on the first section's basis
    guide_in = lateral_profile(x, [ins[0]], job["width_um"],
                               job["n_core"], job["n_background"])
    ne_in, F_in = solve_lateral_modes(x, guide_in, job["wavelength_um"], 2)
    e_in = eme.normalise(F_in[:1], dA)[0]
    a = norm[0] @ (e_in * dA)                     # projection onto section 0
    p_in = float(np.sum(n_effs[0] * np.abs(a) ** 2))
    if p_in <= 0:
        raise RuntimeError("the launch carries no power in the first section")

    S11, _, S21, _ = eme.slice_chain(n_effs, fields, dA, lengths,
                                     job["wavelength_um"])
    b = S21 @ a
    r = S11 @ a

    # the collected field at the output plane, and each port's share of it
    e_out = np.tensordot(b, norm[-1], axes=(0, 0))
    ports = []
    for c in outs:
        guide = lateral_profile(x, [c], job["width_um"],
                                job["n_core"], job["n_background"])
        ne_p, F_p = solve_lateral_modes(x, guide, job["wavelength_um"], 2)
        e_p = eme.normalise(F_p[:1], dA)[0]
        amp = complex(np.sum(e_p * e_out * dA))
        ports.append(float(ne_p[0] * abs(amp) ** 2 / p_in))

    guided = float(np.sum(n_effs[-1] * np.abs(b) ** 2) / p_in)
    reflected = float(np.sum(n_effs[0] * np.abs(r) ** 2) / p_in)
    total = sum(ports)
    return {
        "port_transmission": ports,
        "transmission": total,
        "excess_loss_dB": float(-10.0 * np.log10(max(total, 1e-12))),
        "imbalance_dB": float(10.0 * np.log10(max(ports[0], 1e-12)
                                              / max(ports[1], 1e-12))),
        "reflection": reflected,
        "guided_at_output": guided,
        "accounted": total + reflected,
        "modes_per_section": [int(len(v)) for v in n_effs],
        "sections": len(n_effs),
    }


# ---------------------------------------------------------------------------
# The same device in the full cross-section
# ---------------------------------------------------------------------------
#
# The planar reduction places the self-imaging length seven to ten per cent
# beyond where the kit draws it, because collapsing the vertical dimension into
# two indices changes the spacing of the propagation constants and that spacing
# is what fixes the imaging length. The remedy is to keep the vertical dimension
# and match the modes of the real cross-section instead.
#
# The cost falls where it can be afforded. Every section is solved once, and the
# length of the multimode section then enters through one diagonal matrix, so a
# sweep over that length costs a cascade rather than a solve.


# WHAT THIS ROUTE CAN AND CANNOT BE ASKED, as measured on 2026-09-04.
#
# It returns a smooth response whose shape is physical, and it does not yet
# return an absolute transmission that may be quoted. On the O-band 1x2 cell a
# basis of twelve modes per section delivers 1.0285 of the input at the drawn
# length, which a passive splitter cannot do, and raising the basis to
# twenty-four diverges by eighteen orders of magnitude. Both are the
# conditioning of the interface matching rather than the physics: the
# continuity conditions are over-determined on a truncated basis, and the
# pseudo-inverse that resolves them loses rank once the basis carries many
# nearly degenerate states.
#
# The remedy is the path the taper stage already takes. `eme.local_mode_chain`
# propagates the local modes adiabatically and is well conditioned, and full
# matching is required only at the two abrupt faces of the multimode section.
# Splitting the cascade that way is the work outstanding.
#
# Until then the length at which this route peaks is reported as an
# observation, and the transmission it returns is not to be quoted.


def cross_section_eps(x, y, centres, width_um: float, stack: dict) -> "np.ndarray":
    """Permittivity of a ridge, or a pair of them, on its slab in oxide.

    ``y = 0`` is the top of the buried oxide. The slab occupies the film that
    the etch leaves, the ridge stands on it, and the wall leans out downward at
    the declared angle, so the ridge is wider at its base than at its top.
    """
    t_film, t_etch = stack["film_um"], stack["etch_um"]
    t_slab = t_film - t_etch
    n_film, n_clad = stack["n_film"], stack["n_clad"]
    tan_wall = np.tan(np.radians(float(stack.get("sidewall_deg", 90.0))))

    eps = np.full((len(x), len(y)), n_clad ** 2, dtype=float)
    slab = (y >= 0.0) & (y <= t_slab)
    #: the slab spans the window unless the stack states a strip. An edge
    #: coupler is drawn inside the negative layer, where the slab is present
    #: only as the strip the lower taper draws, and that strip is what carries
    #: the mode at the facet
    slab_w = stack.get("slab_width_um")
    if slab_w is None:
        eps[:, slab] = n_film ** 2
    else:
        within = np.abs(x - float(stack.get("slab_centre_um", 0.0))) <= float(slab_w) / 2
        eps[np.ix_(within, slab)] = n_film ** 2
    if float(stack.get("ridge_height_um", t_etch)) <= 0.0:
        return eps
    for j, yy in enumerate(y):
        if not (t_slab < yy <= t_film):
            continue
        flare = (t_film - yy) / tan_wall if tan_wall > 0 else 0.0
        half = width_um / 2.0 + flare
        for c in np.atleast_1d(np.asarray(centres, dtype=float)):
            eps[np.abs(x - c) <= half, j] = n_film ** 2
    return eps


def stack_3d(job: dict) -> dict:
    """Solve every section of the splitter in its own cross-section, once."""
    from .solvers.fdmode import solve_modes

    w, wp = job["width_um"], job["port_width_um"]
    Wm, Lt = job["mmi_width_um"], job["taper_length_um"]
    sep, lead = job["port_separation_um"], job["lead_um"]
    slices = int(job.get("taper_slices", 6))
    n_modes = int(job.get("num_modes", 12))
    lam = job["wavelength_um"]
    stack = job["stack"]

    x, y = job["x"], job["y"]
    dA = np.outer(np.gradient(x), np.gradient(y))
    outs = [+sep / 2, -sep / 2]
    ins = [0.0] if int(job["ports_in"]) == 1 else outs

    plan: list[tuple] = [(ins, w, lead)]
    for k in range(slices):
        u = (k + 0.5) / slices
        plan.append((ins, w + (wp - w) * u, Lt / slices))
    plan.append(([0.0], Wm, job["mmi_length_um"]))
    for k in range(slices):
        u = (k + 0.5) / slices
        plan.append((outs, wp + (w - wp) * u, Lt / slices))
    plan.append((outs, w, lead))

    n_effs, fields, lengths = [], [], []
    for centres, width, L in plan:
        eps = cross_section_eps(x, y, centres, width, stack)
        modes = solve_modes(x, y, eps, eps, lam, job.get("polarisation", "TE"),
                            n_modes, None)
        if not modes:
            raise RuntimeError(f"a {width:.2f} um section guides no mode")
        n_effs.append(np.array([m.n_eff for m in modes], dtype=float))
        fields.append(np.array([m.field for m in modes], dtype=float))
        lengths.append(float(L))

    #: the isolated guides the ports are measured against
    port_modes = {}
    for tag, centre in (("in", ins[0]), ("out", outs[0]), ("out2", outs[1])):
        eps = cross_section_eps(x, y, [centre], w, stack)
        m = solve_modes(x, y, eps, eps, lam, job.get("polarisation", "TE"), 1, None)
        port_modes[tag] = (float(m[0].n_eff), eme.normalise(
            np.array([m[0].field], dtype=float), dA)[0])

    return {"n_effs": n_effs, "fields": fields, "lengths": lengths, "dA": dA,
            "ports": port_modes, "mmi_index": 1 + slices,
            "wavelength_um": lam, "outs": outs}


def solve_from_stack(st: dict, mmi_length_um: float | None = None) -> dict:
    """Cascade a solved stack, optionally at a different multimode length."""
    lengths = list(st["lengths"])
    if mmi_length_um is not None:
        lengths[st["mmi_index"]] = float(mmi_length_um)
    dA = st["dA"]
    norm = [eme.normalise(F, dA) for F in st["fields"]]

    n_in, e_in = st["ports"]["in"]
    a = norm[0].reshape(len(norm[0]), -1) @ (e_in * dA).reshape(-1)
    p_in = float(np.sum(st["n_effs"][0] * np.abs(a) ** 2))

    S11, _, S21, _ = eme.slice_chain(st["n_effs"], st["fields"], dA, lengths,
                                     st["wavelength_um"])
    b, r = S21 @ a, S11 @ a
    e_out = np.tensordot(b, norm[-1], axes=(0, 0))

    ports = []
    for tag in ("out", "out2"):
        n_p, e_p = st["ports"][tag]
        # the projection is complex, the transmitted amplitudes carrying the
        # phase each mode accumulated. Taking its real part discards that phase
        # and makes the port power oscillate with the length of the section,
        # which reads as a device whose transmission collapses at particular
        # lengths. The power is the modulus squared.
        amp = complex(np.sum(e_p * e_out * dA))
        ports.append(float(n_p * abs(amp) ** 2 / p_in))
    total = sum(ports)
    return {
        "mmi_length_um": lengths[st["mmi_index"]],
        "port_transmission": ports,
        "transmission": total,
        "excess_loss_dB": float(-10.0 * np.log10(max(total, 1e-12))),
        "imbalance_dB": float(10.0 * np.log10(max(ports[0], 1e-12)
                                              / max(ports[1], 1e-12))),
        "reflection": float(np.sum(st["n_effs"][0] * np.abs(r) ** 2) / p_in),
    }


def solve_faces(job: dict) -> dict:
    """The splitter reduced to the two junctions that carry its physics.

    Full mode matching is required where the cross-section changes abruptly, and
    a multimode splitter has exactly two such planes: the faces of the
    multimode section. The access tapers vary slowly by construction, so their
    behaviour is adiabatic and their junctions carry no reflection worth
    matching. Treating them as matched junctions is what destroys the
    conditioning, since each adds an over-determined continuity condition on a
    truncated basis and there are a dozen of them.

    The cascade is therefore three sections and two junctions: the port guides
    at the width the taper delivers, the multimode section, and the port guides
    again. The taper's own transmission is measured separately by the local-mode
    path, where it is well conditioned, and multiplies the result.

    The launch is the fundamental of one isolated port guide, and each output is
    what an isolated port guide collects.
    """
    from .solvers.fdmode import solve_modes

    x, y, stack = job["x"], job["y"], job["stack"]
    lam = job["wavelength_um"]
    pol = job.get("polarisation", "TE")
    wp, Wm = job["port_width_um"], job["mmi_width_um"]
    sep, lead = job["port_separation_um"], job["lead_um"]
    dA = np.outer(np.gradient(x), np.gradient(y))

    outs = [+sep / 2, -sep / 2]
    ins = [0.0] if int(job["ports_in"]) == 1 else outs
    n_port = int(job.get("port_modes", 6))
    n_mmi = int(job.get("num_modes", 12))

    def solve(centres, width, count):
        eps = cross_section_eps(x, y, centres, width, stack)
        modes = solve_modes(x, y, eps, eps, lam, pol, count, None)
        if not modes:
            raise RuntimeError(f"a {width:.2f} um section guides no mode")
        return (np.array([m.n_eff for m in modes], dtype=float),
                np.array([m.field for m in modes], dtype=float))

    ne_in, F_in = solve(ins, wp, n_port)
    ne_mm, F_mm = solve([0.0], Wm, n_mmi)
    ne_out, F_out = solve(outs, wp, n_port)

    #: the isolated guide each port is measured against
    ne_g, F_g = solve([ins[0]], wp, 1)
    e_launch = eme.normalise(F_g[:1], dA)[0]
    collectors = []
    for c in outs:
        ne_c, F_c = solve([c], wp, 1)
        collectors.append((float(ne_c[0]), eme.normalise(F_c[:1], dA)[0]))

    norm_in = eme.normalise(F_in, dA)
    norm_out = eme.normalise(F_out, dA)
    a = norm_in.reshape(len(norm_in), -1) @ (e_launch * dA).reshape(-1)
    p_in = float(np.sum(ne_in * np.abs(a) ** 2))

    def at_length(L: float) -> dict:
        S11, _, S21, _ = eme.slice_chain(
            [ne_in, ne_mm, ne_out], [F_in, F_mm, F_out], dA,
            [lead, float(L), lead], lam)
        b, r = S21 @ a, S11 @ a
        e_out = np.tensordot(b, norm_out, axes=(0, 0))
        ports = []
        for n_c, e_c in collectors:
            amp = complex(np.sum(e_c * e_out * dA))
            ports.append(float(n_c * abs(amp) ** 2 / p_in))
        total = sum(ports)
        return {
            "mmi_length_um": float(L),
            "port_transmission": ports,
            "transmission": total,
            "excess_loss_dB": float(-10.0 * np.log10(max(total, 1e-12))),
            "imbalance_dB": float(10.0 * np.log10(max(ports[0], 1e-12)
                                                  / max(ports[1], 1e-12))),
            "reflection": float(np.sum(ne_in * np.abs(r) ** 2) / p_in),
        }

    return {"at_length": at_length,
            "modes": {"port": len(ne_in), "mmi": len(ne_mm)},
            "n_mmi": ne_mm}
