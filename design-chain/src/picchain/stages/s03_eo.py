"""Stage 3 - Pockels electrodes: RF field, EO overlap, tuning efficiency.

Two meshes, deliberately:

* the **optical** mesh from stage 1 - a few um wide, 10 nm fine, no metal, no
  handle wafer (the real 4.7 um BOX isolates the mode, and putting a truncated
  BOX over silicon invites spurious substrate modes);
* an **RF** mesh - tens of um wide, coarse, *with* the gold electrodes and the
  silicon handle, because the electrostatic problem is set by geometry an
  order of magnitude larger than the mode.

The electrostatic potential is solved on the RF mesh and interpolated onto the
optical mesh for the overlap integral.  The RF field is smooth on the scale of
the optical mode, so this costs nothing in accuracy and saves ~30x in runtime
versus meshing the whole electrode span at optical resolution.

Why the group index appears in the tuning
-----------------------------------------
The Bragg condition is lambda_B = 2 n_eff Lambda / m, but n_eff is itself
dispersive.  Perturbing both sides,

    d(lambda_B)/lambda_B = dn / n_g          (NOT dn / n_eff)

because n_g = n_eff - lambda dn_eff/dlambda.  For a shallow-etched thin-film
LN/LT ridge n_g/n_eff ~ 1.25, so using n_eff would over-predict the tuning
efficiency by ~25%.  This is the easiest way to mis-size a Pockels DBR.
"""

from __future__ import annotations

import cmath
import math
from typing import Any

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .. import process
from ..artifacts import RunContext
from ..config import Design
from ..geometry import RasterGrid, graded_axis, material_mask, rasterise
from ..materials import MaterialLibrary
from ..solvers.electrostatic import eo_overlap, solve_potential
from .s01_mode import _build

_INTERP = "linear"  # cubic was tried and moved Gamma by 0.06 per cent
C0 = 299792458.0
EPS0 = 8.8541878128e-12  # F/m



def travelling_wave(grid, eps_x, eps_y, drive, V, C_per_m, e, n_g, length_m, geom,
                    n_conductors=2.0):
    """Microwave index, impedance, conductor loss and the bandwidth they imply.

    The closed-form parts live in ``picchain.rf`` and are tested there. What is
    done here is the one thing that needs the mesh: the same electrostatic
    problem solved with every dielectric removed, which gives the inductance,
    since a magnetostatic problem does not see them.
    """
    import numpy as np

    from .. import rf

    ones = np.ones_like(eps_x)
    es_air = solve_potential(grid.x, grid.y, ones, ones, drive)
    C_air = 2 * (es_air.energy(ones, ones) * EPS0) / (V**2)
    if C_air <= 0 or C_per_m <= 0:
        return {"enabled": False, "reason": "a capacitance was not positive"}

    line = rf.line_parameters(C_per_m, C_air)
    Z0 = line["characteristic_impedance_ohm"]
    n_m = line["microwave_index"]

    def alpha(f_Hz):
        R = rf.skin_resistance_per_m(f_Hz, e.conductivity_S_per_m,
                                     geom.electrode_width_um * 1e-6, e.thickness_um * 1e-6,
                                     n_conductors=n_conductors)
        return R / (2.0 * Z0)

    gamma = rf.load_reflection(e.far_end_load_ohm, Z0)
    if gamma <= -0.999:
        # A shorted far end holds the drive at zero everywhere at zero
        # frequency, so the response has no value to be referred to and the
        # bandwidth below is a number without a meaning. The kit draws no such
        # cell; a design that declares one is told rather than given a figure.
        raise ValueError(
            "electrodes.far_end_load_ohm declares a short, for which the "
            "modulation response is zero at zero frequency and the 3 dB "
            "bandwidth is undefined. Declare the load the cell draws")
    f_3dB = rf.bandwidth(length_m, alpha, n_m, n_g, reflection=gamma)
    f_6dB = rf.bandwidth(length_m, alpha, n_m, n_g, level=0.5, reflection=gamma)
    stub_m = e.far_end_stub_um * 1e-6
    penalty = rf.far_end_penalty(length_m, alpha, n_m, n_g, gamma, 1e8, 2e11,
                                 stub_m=stub_m)
    mismatch = abs((Z0 - e.drive_impedance_ohm) / (Z0 + e.drive_impedance_ohm))

    return {
        "enabled": True,
        "capacitance_air_pF_per_cm": C_air * 1e12 / 100,
        "inductance_nH_per_cm": line["inductance_H_per_m"] * 1e9 / 100,
        "microwave_index": n_m,
        "optical_group_index": n_g,
        "velocity_mismatch": n_m - n_g,
        "characteristic_impedance_ohm": Z0,
        "reflection_at_driver": mismatch,
        "return_loss_dB": -20 * math.log10(mismatch) if mismatch > 0 else float("inf"),
        "conductor_loss_dB_per_cm_at_10GHz": alpha(1e10) * rf.NEPER_TO_DB / 100,
        "electro_optic_3dB_GHz": f_3dB / 1e9,
        "electro_optic_6dB_GHz": f_6dB / 1e9,
        # what the far end returns, and hence which of the two variants of the
        # cell this bandwidth describes
        "far_end_load_ohm": e.far_end_load_ohm,
        "far_end_reflection": gamma,
        "far_end_is_matched": gamma == 0.0,
        # The two figures above are referred to this line's own value at zero
        # frequency, which on an unmatched line is not the value a terminated
        # one has. What a driver is sized against is the comparison between the
        # two lines driven alike, and that is what these report.
        "far_end_worst_penalty_dB": penalty["worst_dB"],
        "far_end_worst_penalty_at_GHz": penalty["worst_at_Hz"] / 1e9,
        "far_end_best_advantage_dB": penalty["best_dB"],
        "far_end_best_advantage_at_GHz": penalty["best_at_Hz"] / 1e9,
        "far_end_stub_um": e.far_end_stub_um,
        "electrode_length_mm": length_m * 1e3,
        "topology": str(e.topology),
        "conductors_carrying_the_return": n_conductors,
        # what a source of the declared impedance launches into this line
        "drive_transmitted_into_line": 2 * Z0 / (Z0 + e.drive_impedance_ohm),
    }


def electrode_extent(design: Design, grating: dict) -> tuple[float, str, float, str]:
    """The electrode run and the wavelength it acts at, and where each came from.

    An electrode flanking a Bragg mirror runs the length of the grating and acts
    at the Bragg wavelength, the two being one structure. An electrode on a
    modulator arm runs a length of its own and acts at the wavelength the guide
    carries. Reading the grating in the second case returns the length and the
    wavelength of a structure the device does not contain, and `grating.length_um`
    holds a schema default whether or not a grating exists, so the figure returned
    would look ordinary while describing another device.

    Returned with the field each value was taken from, so that a run states which
    of the two rules applied rather than leaving it to be inferred.
    """
    if design.electrodes.length_um is not None:
        return (float(design.electrodes.length_um), "electrodes.length_um",
                float(design.waveguide.wavelength_um), "waveguide.wavelength_um")

    length_um = float(grating.get("length_um", design.grating.length_um))
    lam_B = grating.get("bragg_wavelength_um")
    if lam_B:
        return (length_um, "grating.length_um",
                float(lam_B), "grating.bragg_wavelength_um")
    return (length_um, "grating.length_um",
            float(design.waveguide.wavelength_um), "waveguide.wavelength_um")


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    e = design.electrodes
    if not e.enabled:
        ctx.put("eo", {"enabled": False})
        return {"enabled": False}

    p, mesh = design.platform, design.mesh
    lam = design.waveguide.wavelength_um
    V = e.test_voltage_V
    # every electrode dimension below is the printed one, matching the
    # cross-section stage 1 solved and not the figure drawn on the mask
    geom = process.geometry(design, design.process.simulate)

    # ---- optical mode from stage 1 (same mesh, no re-solve) -------------
    mode_npz = ctx.run_dir / "mode.npz"
    if not mode_npz.exists():
        raise RuntimeError("stage 'eo' requires stage 'mode' artifacts")
    md = np.load(mode_npz)
    ox, oy = md["x_um"], md["y_um"]
    intensity = np.abs(md["field_bare"]) ** 2
    mask_film_opt = md["mask_film"]

    # ---- RF problem on its own, coarser, wider mesh ---------------------
    xs_rf = _build(design, with_posts=False, electrodes=True, name="rf")
    d_fine_rf = (float(e.rf_mesh_fine_um) if e.rf_mesh_fine_um
                 else max(mesh.d_fine_um * 5, 0.05))
    d_coarse_rf = max(mesh.d_coarse_um * 10, 0.60)
    # Grid the RF problem explicitly rather than through build_grid: the
    # blanket layers span the whole (deliberately huge) window, so the generic
    # "fine across all features" rule would mesh the entire fringing volume at
    # 50 nm.  Only the electrode gap and the film stack need resolving.
    x0, x1, y0, y1 = xs_rf.window
    slab_y = design.platform.film_thickness_um - design.platform.etch_depth_um
    # Fixed points at every material interface the cross-section actually
    # draws, taken from the shapes rather than written out by hand.
    #
    # They were previously the slot topology: the guide on the axis and an
    # electrode edge at half the gap either side of it. A ground-signal-ground
    # line puts nothing at either place. Its edges are at half the signal width,
    # at that plus the gap, and at that plus the ground width, and its guides
    # sit on the gap centre lines. The mesh was therefore refined on the axis,
    # where the field is uniform inside the signal conductor, and left coarse at
    # every edge that carries a field singularity. The buried oxide's lower
    # interface, across which the permittivity trebles, was not a fixed point in
    # either topology.
    def _interfaces(index: int, lo: float, hi: float) -> list[float]:
        vals = {float(pt[index]) for sh in xs_rf.shapes for pt in sh.points}
        return sorted(v for v in vals if lo < v < hi)

    fx = _interfaces(0, x0, x1)
    fy = _interfaces(1, y0, y1)

    # The window the overlap integral is taken over is a fixed region too.
    #
    # Gamma is the electrostatic field interpolated onto the optical mesh and
    # integrated over it. That mesh reaches `ox` either side of each guide, and
    # the fine cells reached only `rf_mesh_fine_margin_um` either side of the
    # ridge, so the tails of the mode were sampled on the coarse cell and
    # interpolated linearly from it. The capacitance did not notice, being an
    # integral over the whole domain; the overlap moved by several per cent
    # between meshes while the guard reported two tenths of one.
    _arm = (geom.electrode_width_um / 2 + geom.electrode_gap_um / 2
            if str(e.topology).lower() == "gsg" else 0.0)
    for sgn in ((-1.0, 1.0) if _arm else (1.0,)):
        for edge in (float(ox.min()), float(ox.max())):
            v = sgn * _arm + edge
            if x0 < v < x1:
                fx.append(v)
    fx = sorted(set(fx))
    eps_rf = {m: lib[m].eps_rf_device(p.cut) for m in xs_rf.materials_used()}

    def _rf_solve(d_fine: float, d_coarse: float):
        """The electrostatic problem at one mesh density.

        Returned so that the same problem can be posed twice and the shift
        between the two reported, rather than a single mesh being trusted.
        """
        g = RasterGrid(
            graded_axis(x0, x1, fx, d_fine, d_coarse,
                        fine_margin=float(e.rf_mesh_fine_margin_um)),
            graded_axis(y0, y1, fy, d_fine, d_coarse,
                        fine_margin=float(e.rf_mesh_fine_margin_um)),
        )
        ex = rasterise(xs_rf, g, {m: v[0] for m, v in eps_rf.items()}, subsample=2)
        ey = rasterise(xs_rf, g, {m: v[1] for m, v in eps_rf.items()}, subsample=2)
        met = material_mask(xs_rf, g, e.material, subsample=2)
        if str(e.topology).lower() == "gsg":
            hs = geom.electrode_width_um / 2
            dr = [(met * (np.abs(g.x)[:, None] <= hs + 1e-9), V),
                  (met * (np.abs(g.x)[:, None] > hs + 1e-9), 0.0)]
        else:
            dr = [(met * (g.x[:, None] < 0), +V / 2), (met * (g.x[:, None] > 0), -V / 2)]
        sol = solve_potential(g.x, g.y, ex, ey, dr)
        c_per_m = 2.0 * (sol.energy(ex, ey) * EPS0) / (V ** 2)
        return g, ex, ey, dr, sol, c_per_m

    grid, eps_x, eps_y, _drive_unused, _es_nominal, _C_unused = _rf_solve(d_fine_rf, d_coarse_rf)

    metal = material_mask(xs_rf, grid, e.material, subsample=2)
    gsg = str(e.topology).lower() == "gsg"
    if gsg:
        # Signal on axis against two grounds. The potential difference across
        # each gap is V, matching the slot convention, so the parallel-plate
        # reference below is the same quantity in both topologies.
        half_signal = geom.electrode_width_um / 2
        signal = metal * (np.abs(grid.x)[:, None] <= half_signal + 1e-9)
        grounds = metal * (np.abs(grid.x)[:, None] > half_signal + 1e-9)
        drive = [(signal, V), (grounds, 0.0)]
        arm_offset_um = half_signal + geom.electrode_gap_um / 2
        # two grounds carry the return in parallel, so the series resistance is
        # the signal conductor's plus half of one ground's
        n_conductors = 1.5
    else:
        mask_L = metal * (grid.x[:, None] < 0)
        mask_R = metal * (grid.x[:, None] > 0)
        drive = [(mask_L, +V / 2), (mask_R, -V / 2)]
        arm_offset_um = 0.0
        n_conductors = 2.0
    es = solve_potential(grid.x, grid.y, eps_x, eps_y, drive)

    # ---- interpolate E_x onto the optical mesh --------------------------
    # The optical mesh is centred on its own guide, so the field is sampled
    # about that guide's position in the line rather than about the axis.
    # The interpolation order was investigated and is not the limitation.
    #
    # Gamma converges as roughly the 0.8 power of the cell while the capacitance
    # converges cleanly, and the natural suspect was this interpolant carrying a
    # first-order error. Solving at 50, 35 and 25 nm with a cubic interpolant
    # instead moved Gamma by 0.06 per cent and left the convergence order
    # unchanged. What converges slowly is the field itself at the conductor
    # corner, where it is singular, and Gamma integrates that field 1.8 um away
    # from it.
    interp = RegularGridInterpolator(
        (grid.x, grid.y), es.Ex, method=_INTERP, bounds_error=False, fill_value=0.0
    )
    OX, OY = np.meshgrid(ox + arm_offset_um, oy, indexing="ij")
    Ex_opt = interp(np.stack([OX.ravel(), OY.ravel()], axis=-1)).reshape(OX.shape)

    def _gamma_from(solution) -> float:
        """The electro-optic overlap from one electrostatic solution."""
        f = RegularGridInterpolator((solution.x, solution.y), solution.Ex,
                                    method=_INTERP, bounds_error=False,
                                    fill_value=0.0)
        ex = f(np.stack([OX.ravel(), OY.ravel()], axis=-1)).reshape(OX.shape)
        return eo_overlap(ex, intensity, mask_film_opt, ox, oy,
                          geom.electrode_gap_um, V)

    gamma = eo_overlap(Ex_opt, intensity, mask_film_opt, ox, oy, geom.electrode_gap_um, V)

    mat = lib[p.film_material]
    n_e = mat.index(lam, "e", p.use_index_override)
    r = mat.r_pm_per_V(e.eo_coefficient) * 1e-12  # m/V

    E_ref = V / (geom.electrode_gap_um * 1e-6)                  # parallel-plate reference, V/m
    dn_ideal = 0.5 * n_e**3 * r * E_ref
    dn_eff = gamma * dn_ideal
    dn_eff_per_V = dn_eff / V

    grating = ctx.get("grating") or {}
    n_g = float(grating.get("n_g") or (ctx.get("mode") or {}).get("n_g") or n_e)

    L_electrode_um, length_from, lam_B_um, wavelength_from = electrode_extent(design, grating)
    f_B = C0 / (lam_B_um * 1e-6)

    tuning_Hz_per_V = f_B * dn_eff_per_V / n_g
    VpiL_V_cm = (
        (lam_B_um * 1e-6) * (geom.electrode_gap_um * 1e-6) / (n_e**3 * r * abs(gamma)) * 100
        if abs(gamma) > 0 else float("inf")
    )
    VpiL_ideal_V_cm = (lam_B_um * 1e-6) * (geom.electrode_gap_um * 1e-6) / (n_e**3 * r) * 100

    # capacitance per unit length from the stored energy (F/m)
    # E is in V/um and dA in um^2; those two unit factors cancel exactly, so
    # this is already joules per metre of electrode run.
    W = es.energy(eps_x, eps_y) * EPS0
    C_per_m = 2 * W / (V**2)
    L_electrode_m = L_electrode_um * 1e-6
    C_total_F = C_per_m * L_electrode_m
    f_rc_Hz = 1.0 / (2 * math.pi * e.drive_impedance_ohm * C_total_F) if C_total_F > 0 else float("inf")

    # optical power beyond the electrode inner edge -> metal absorption proxy
    dxo, dyo = np.gradient(ox), np.gradient(oy)
    dA = np.outer(dxo, dyo)
    def _tail_at(gap_um: float) -> float:
        """The mode power beyond a conductor's inner edge, at any gap."""
        beyond = np.abs(ox)[:, None] >= (float(gap_um) / 2)
        return float(np.sum(intensity * beyond * dA) / np.sum(intensity * dA))

    tail = _tail_at(geom.electrode_gap_um)

    # Every conductor pair the design carries, not only the one this stage
    # solved the field for.
    #
    # The proxy is an integral of the optical mode alone, so evaluating it at a
    # second gap costs nothing. A design carrying a mirror electrode at 6.41 um
    # and a phase section at 4.80 graded this row at the wider one and passed by
    # a factor of 84; at the narrower it passes by 7 per cent, and across that
    # design's own process window it breaches at 34 corners of 81. Its own
    # documentation had named the configuration and warned against exactly this.
    gaps = {"electrodes": float(geom.electrode_gap_um)}
    ps = getattr(getattr(design, "cavity", None), "phase_section", None)
    if ps is not None and getattr(ps, "enabled", False):
        g2 = getattr(ps, "gap_um", None)
        if g2:
            gaps["cavity.phase_section"] = float(g2)
    tails = {k: _tail_at(v) for k, v in gaps.items()}
    worst_where = max(tails, key=lambda k: tails[k])

    tw = travelling_wave(grid, eps_x, eps_y, drive, V, C_per_m, e, n_g,
                         L_electrode_m, geom, n_conductors) if e.travelling_wave \
        else {"enabled": False}

    # ---- where the microwave energy sits, by material --------------------
    #
    # The handle wafer is modelled as a lossless dielectric. Whether that is
    # defensible depends on its resistivity and on how much of the field it
    # carries, and the second the solve already knows. It was quoted in one
    # design as "about 18 per cent", taken from the stack geometry and from no
    # computation. It is computed here.
    dens = _es_nominal.energy_density(eps_x, eps_y)
    w_total = float(np.sum(dens))
    energy_by_material: dict[str, float] = {}
    if w_total > 0:
        for mat in sorted(xs_rf.materials_used()):
            mk = material_mask(xs_rf, grid, mat, subsample=2)
            energy_by_material[mat] = float(np.sum(dens * (mk > 0.5))) / w_total

    # The dielectric loss the handle would add, given a resistivity for it.
    # tan d = 1 / (w eps0 eps_r rho), and a quasi-TEM line carries
    # alpha_d = (w / 2c) n_m sum_i f_i tan d_i over the materials it passes.
    substrate_loss: dict = {
        "resistivity_ohm_cm": None,
        "reason": "platform.substrate_resistivity_ohm_cm is unset, so the handle "
                  "is modelled lossless and this term is absent from the bandwidth",
    }
    rho = getattr(design.platform, "substrate_resistivity_ohm_cm", None)
    f_sub = energy_by_material.get(design.platform.substrate_material, 0.0)
    if rho and tw.get("enabled") and f_sub > 0:
        f_ref = 1e10
        eps_sub = float(np.mean(lib[design.platform.substrate_material]
                                .eps_rf_device(p.cut)))
        tan_d = 1.0 / (2 * math.pi * f_ref * EPS0 * eps_sub * (float(rho) * 1e-2))
        alpha_d = (2 * math.pi * f_ref / (2 * C0)) * tw["microwave_index"] * f_sub * tan_d
        substrate_loss = {
            "resistivity_ohm_cm": float(rho),
            "energy_fraction": f_sub,
            "loss_tangent_at_10GHz": tan_d,
            "dielectric_loss_dB_per_cm_at_10GHz": alpha_d * 8.685590811 / 100,
            "conductor_loss_dB_per_cm_at_10GHz":
                tw.get("conductor_loss_dB_per_cm_at_10GHz"),
        }

    # ---- the convergence guard on the electrostatic solve ----------------
    convergence: dict = {"performed": False, "reason": "not requested"}
    if e.convergence_check:
        d_fine_r = d_fine_rf * float(e.refinement)
        d_coarse_r = d_coarse_rf * float(e.refinement)
        gr, exr, eyr, drr, _sr, C_ref = _rf_solve(d_fine_r, d_coarse_r)
        rel = abs(C_ref - C_per_m) / C_per_m if C_per_m else float("inf")
        # The overlap is recomputed on the refined mesh as well.
        #
        # It was not, and the omission was the whole of what the guard missed.
        # The capacitance is an integral of the field energy over the domain and
        # converges as the square of the cell; the overlap is that field
        # interpolated linearly onto the optical mesh, through a region holding a
        # ridge corner and the metal edge singularity, so it converges as the
        # first power. A guard reporting 0.21 per cent on the capacitance was
        # read as authorising a Vpi whose overlap was still moving by several per
        # cent between meshes.
        gamma_ref = _gamma_from(_sr)
        g_rel = abs(gamma_ref - gamma) / abs(gamma) if gamma else float("inf")
        convergence = {
            "performed": True,
            "d_fine_um": d_fine_r,
            "nx": int(len(gr.x)), "ny": int(len(gr.y)),
            "capacitance_pF_per_cm": C_ref * 1e12 / 100,
            "capacitance_rel_shift": rel,
            "eo_overlap_gamma_refined": gamma_ref,
            "eo_overlap_gamma_rel_shift": g_rel,
            "tolerance": float(e.convergence_tolerance),
            "resolved": bool(rel <= float(e.convergence_tolerance)
                             and g_rel <= float(e.convergence_tolerance)),
        }
        if e.travelling_wave:
            tw_r = travelling_wave(gr, exr, eyr, drr, V, C_ref, e, n_g,
                                   L_electrode_m, geom, n_conductors)
            for key in ("microwave_index", "characteristic_impedance_ohm",
                        "electro_optic_3dB_GHz"):
                a, b = tw.get(key), tw_r.get(key)
                if a and b:
                    convergence[key + "_refined"] = b
                    convergence[key + "_rel_shift"] = abs(b - a) / abs(a)
            bw_shift = convergence.get("electro_optic_3dB_GHz_rel_shift")
            if bw_shift is not None and bw_shift > float(e.convergence_tolerance):
                convergence["resolved"] = False
        if not convergence["resolved"]:
            ctx.warn(
                "the electrostatic solve is not converged: halving the cell moves "
                "the electro-optic overlap by %.1f per cent, the capacitance by "
                "%.1f per cent and the 3 dB bandwidth by %.1f per cent, against a "
                "tolerance of %.1f. Every figure this stage reports carries at "
                "least that uncertainty, and a margin smaller than it is not a "
                "margin" % (
                    g_rel * 100,
                    rel * 100,
                    100 * (convergence.get("electro_optic_3dB_GHz_rel_shift") or 0.0),
                    100 * float(e.convergence_tolerance)))

    payload = {
        "enabled": True,
        "electrode_gap_um": geom.electrode_gap_um,
        "electrode_width_um": geom.electrode_width_um,
        "test_voltage_V": V,
        "eo_coefficient": e.eo_coefficient,
        "r_pm_per_V": r * 1e12,
        "n_extraordinary": n_e,
        "eo_overlap_gamma": gamma,
        "dn_ideal_per_V": dn_ideal / V,
        "dn_eff_per_V": dn_eff_per_V,
        "tuning_MHz_per_V": tuning_Hz_per_V / 1e6,
        "tuning_GHz_per_V": tuning_Hz_per_V / 1e9,
        "VpiL_V_cm": VpiL_V_cm,
        "VpiL_ideal_V_cm": VpiL_ideal_V_cm,
        "capacitance_pF_per_cm": C_per_m * 1e12 / 100,
        "capacitance_total_pF": C_total_F * 1e12,
        "electrode_length_um": L_electrode_um,
        "electrode_length_from": length_from,
        "wavelength_um": lam_B_um,
        "wavelength_from": wavelength_from,
        "lumped_RC_bandwidth_MHz": f_rc_Hz / 1e6,
        "mode_overlap_with_metal": tail,
        # the same proxy at every conductor pair the design declares, and the
        # worst of them, which is the figure a target should be written against
        "mode_overlap_with_metal_by_gap": tails,
        "mode_overlap_with_metal_gaps_um": gaps,
        "mode_overlap_with_metal_worst": tails[worst_where],
        "mode_overlap_with_metal_worst_at": worst_where,
        "rf_mesh": {"nx": int(len(grid.x)), "ny": int(len(grid.y)),
                    "d_fine_um": d_fine_rf, "d_coarse_um": d_coarse_rf},
        "convergence": convergence,
        "microwave_energy_by_material": energy_by_material,
        "substrate_dielectric_loss": substrate_loss,
        "n_g_used": n_g,
        "note_group_index": "tuning uses dlambda/lambda = dn/n_g (dispersive Bragg condition)",
        "note_metal_overlap": "reported as the fraction of |E|^2 beyond the electrode inner edge",
        "travelling_wave": tw,
    }

    ctx.put("eo", payload)
    ctx.write_stage(
        "eo",
        payload,
        {"x_um": ox, "y_um": oy, "Ex": Ex_opt, "intensity": intensity,
         "mask_film": mask_film_opt, "rf_x_um": grid.x, "rf_y_um": grid.y,
         "rf_V": es.V, "rf_Ex": es.Ex, "rf_Ey": es.Ey},
    )

    if tw.get("enabled") and tw["electro_optic_3dB_GHz"] > 5 * (f_rc_Hz / 1e9):
        ctx.warn(
            f"the lumped RC estimate gives {f_rc_Hz / 1e9:.2f} GHz against "
            f"{tw['electro_optic_3dB_GHz']:.1f} GHz from the travelling-wave model. "
            f"Over {tw['electrode_length_mm']:.1f} mm the electrode is a transmission "
            "line, not a capacitor, and the lumped figure is not the bandwidth"
        )
    if tw.get("enabled") and tw["return_loss_dB"] < 10.0:
        ctx.warn(
            f"the electrode presents {tw['characteristic_impedance_ohm']:.0f} ohm "
            f"against a {e.drive_impedance_ohm:.0f} ohm driver, a return loss of "
            f"{tw['return_loss_dB']:.1f} dB. The reflected power does not modulate"
        )
    if tail > 1e-4:
        ctx.warn(
            f"{tail:.2e} of the optical power sits beyond the electrode inner edge; "
            "metal absorption will dominate the propagation loss - widen the gap"
        )
    if f_rc_Hz < 20e6:
        ctx.warn(
            f"lumped-electrode RC bandwidth is {f_rc_Hz/1e6:.1f} MHz over the full "
            f"{L_electrode_m*1e3:.2f} mm; segment the electrode or go travelling-wave "
            "if the chirp rate needs more"
        )
    return payload
