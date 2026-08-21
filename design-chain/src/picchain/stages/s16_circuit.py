"""Stage 16 - circuit assembly, by SAX.

Every other stage in this chain models one component. The cavity stage then
combines them arithmetically: a round-trip delay is summed from three lengths,
and a mirror response is applied at one plane. That arithmetic is correct for
the arrangement it was written for, and it is the arrangement that is the
assumption. It cannot be applied to a resonator on a bus, to an interferometer,
or to any circuit whose topology differs from the one it encodes.

This stage assembles the same passive circuit from scattering matrices instead.
The blocks are connected by a netlist, the netlist is solved, and the result is
the reflection presented to the gain chip at its facet.

Why it is worth doing on a device the cavity stage already handles
------------------------------------------------------------------
Two reasons, and the second is the durable one.

The immediate reason is that it is a second instrument on a quantity that
matters. The mirror the laser sees is not the grating; it is the grating behind
a taper and a length of feed waveguide, and the phase of that feed enters the
round-trip condition. The cavity stage adds that phase as a delay. The assembly
computes it by cascading the matrices, and the two can be compared.

The lasting reason is that the assembly does not know what it is assembling. A
netlist of three blocks and a netlist of thirty differ only in the dictionary,
so this stage is the first piece of the chain that can describe a circuit rather
than a component.

What is assembled
-----------------
``facet`` → ``taper`` → ``feed`` → ``grating``

The grating is not re-modelled. Its complex reflection and transmission are
taken from the transfer-matrix spectrum the `grating` stage already computed and
interpolated onto the wavelength grid, so a disagreement between this stage and
the cavity stage is a disagreement about the assembly and not about the mirror.

What is not carried
-------------------
The gain chip is not a scattering block here. Gain, saturation and the carrier
dynamics are outside a linear passive assembly, so the laser condition is still
evaluated by the `cavity` stage. This stage supplies the passive reflection that
condition is applied to.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary

_IMPORT_ERROR: str | None = None
try:  # pragma: no cover - exercised by the availability test
    import sax as _sax

    _AVAILABLE = True
except Exception as exc:  # pragma: no cover
    _AVAILABLE = False
    _IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

C0 = 299792458.0


def available() -> bool:
    return _AVAILABLE


def unavailable_reason() -> str | None:
    return _IMPORT_ERROR


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------
def straight(wl=1.55, length_um=1000.0, neff=1.8, ng=2.2, wl0=1.55,
             loss_dB_per_cm=0.0):
    """A length of guide, to first order in dispersion.

    The phase index is expanded about ``wl0`` using the group index, which is
    the same expansion the cavity stage uses for its delay. Holding the two to
    one dispersion model is deliberate: a disagreement between them should be
    about the assembly, and a second dispersion model would confound that.
    """
    wl = np.asarray(wl, dtype=float)
    neff_wl = neff - (wl - wl0) * (ng - neff) / wl0
    phase = 2 * np.pi * neff_wl * length_um / wl
    amp = 10.0 ** (-loss_dB_per_cm * (length_um * 1e-4) / 20.0)
    # SIGN CORRECTED 2026-08-17. This returned exp(+i phase), whose phase rises
    # with frequency, while the grating's stored phase falls with it. The group
    # delay is read as -d(phase)/d(omega), so the feed entered the assembled
    # delay with the wrong sign and was SUBTRACTED from the mirror's.
    #
    # It was found by scale rather than by inspection. Two designs whose modelled
    # feeds differ by a factor of 6.4 both matched
    #
    #     assembled delay  =  tau_dbr - 2 * feed delay
    #
    # to better than 0.2 ps, and the disagreement with the expectation was twice
    # the round-trip feed delay in each. A single design could not have
    # distinguished this from a modelling residue; the pair did.
    #
    # Two elements of one assembly must share a phase convention, and the
    # grating's is the one that arrives from the transfer-matrix solve, so the
    # straight adopts it.
    return _sax.reciprocal({("in0", "out0"): amp * np.exp(-1j * phase)})


def lossy_coupler(wl=1.55, transmission=1.0, reflection=0.0):
    """A facet or a taper, as an amplitude transmission and a reflection.

    Neither is computed here. The transmission is the figure the `facet` and
    `taper` stages produced, or the assumption standing in for them, and it is
    carried through the assembly so that the reflection presented to the chip
    includes it.
    """
    wl = np.asarray(wl, dtype=float)
    one = np.ones_like(wl)
    t = np.sqrt(max(float(transmission), 0.0)) * one
    r = np.sqrt(max(float(reflection), 0.0)) * one
    return _sax.reciprocal({
        ("in0", "out0"): t,
        ("in0", "in0"): r,
        ("out0", "out0"): r,
    })


def make_grating_model(wl_grid_um, r_complex, t_complex):
    """A two-port whose response is the spectrum the grating stage computed.

    The transfer-matrix result is interpolated rather than recomputed, real and
    imaginary parts separately. Interpolating a magnitude and a phase would
    unwrap badly across the stop band, where the phase turns quickly.
    """
    wl_grid = np.asarray(wl_grid_um, dtype=float)
    order = np.argsort(wl_grid)
    wl_s = wl_grid[order]
    rr, ri = np.real(r_complex)[order], np.imag(r_complex)[order]
    tr, ti = np.real(t_complex)[order], np.imag(t_complex)[order]

    def grating(wl=1.55):
        wl = np.asarray(wl, dtype=float)
        r = np.interp(wl, wl_s, rr) + 1j * np.interp(wl, wl_s, ri)
        t = np.interp(wl, wl_s, tr) + 1j * np.interp(wl, wl_s, ti)
        return _sax.reciprocal({
            ("in0", "in0"): r,
            ("in0", "out0"): t,
            ("out0", "out0"): r,
        })

    return grating


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _fwhm(x: np.ndarray, y: np.ndarray) -> float:
    """Full width at half maximum of a single peak, by linear interpolation."""
    peak = float(np.max(y))
    if peak <= 0:
        return float("nan")
    half = peak / 2.0
    above = np.flatnonzero(y >= half)
    if above.size < 2:
        return float("nan")
    lo, hi = above[0], above[-1]

    def cross(i, j):
        if y[j] == y[i]:
            return float(x[i])
        return float(x[i] + (half - y[i]) * (x[j] - x[i]) / (y[j] - y[i]))

    left = cross(lo, lo - 1) if lo > 0 else float(x[lo])
    right = cross(hi, hi + 1) if hi + 1 < len(x) else float(x[hi])
    return abs(right - left)


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.circuit
    if not cfg.enabled:
        payload = {"enabled": False}
        ctx.put("circuit", payload)
        return payload

    if not available():
        raise RuntimeError(
            "stage 'circuit' requires the optional circuit extras. Install them with "
            f"`pip install -e \".[circuit]\"`. The import failed with: {_IMPORT_ERROR}"
        )

    mode = ctx.get("mode") or {}
    grat = ctx.get("grating") or {}
    if "n_eff_bare" not in mode or "bragg_wavelength_nm" not in grat:
        raise RuntimeError("stage 'circuit' requires stages 'mode' and 'grating'")

    npz = ctx.run_dir / "grating.npz"
    if not npz.exists():
        raise RuntimeError(
            "stage 'circuit' reads the transfer-matrix spectrum from grating.npz, "
            "which was not written. Re-run the grating stage"
        )
    with np.load(npz) as data:
        keys = set(data.files)
        needed = {"freq_Hz", "R", "phase_rad"}
        if not needed <= keys:
            raise RuntimeError(
                f"grating.npz carries {sorted(keys)}; the assembly needs {sorted(needed)}"
            )
        f_Hz = np.asarray(data["freq_Hz"], dtype=float)
        # the complex reflection, reconstructed from the magnitude and the phase
        # the transfer-matrix evaluation already wrote
        r_c = np.sqrt(np.clip(np.asarray(data["R"], dtype=float), 0.0, None)) *             np.exp(1j * np.asarray(data["phase_rad"], dtype=float))
        # The transmission phase is not stored and is not reconstructed. The far
        # port is external, so light passing through the grating leaves the
        # circuit and does not return; the transmission therefore affects the
        # power leaving the far end and not the reflection presented to the chip,
        # which is the quantity compared below.
        t_c = np.sqrt(np.clip(1.0 - np.abs(r_c) ** 2, 0.0, None)).astype(complex)

    wl_um = (C0 / f_Hz) * 1e6
    lam0 = float(design.waveguide.wavelength_um)

    # --- the netlist -----------------------------------------------------
    # facet -> taper -> feed -> grating. The taper is drawn on the mask and its
    # length is therefore taken from the layout, not declared twice.
    #
    # CORRECTED 2026-08-17. The subtraction was `2 * taper_length` against the
    # ONE taper instance the netlist below carries, so the straight was short by
    # a taper on every design. The error was invisible wherever the feed was long
    # and catastrophic where it was not: on a 210 um feed with a 150 um taper it
    # drove the length negative, the clamp below returned 1 um, and the stage
    # then assembled a cavity with no feed at all. Every circuit figure for that
    # design described a different device, and the group-delay cross-check
    # agreed to 0.3 % because its expectation was computed from the same clamped
    # value. **A clamp that rescues a nonsensical input turns a modelling failure
    # into a passing check**, so the condition now raises instead.
    feed_len = design.cavity.feed_length_um - design.layout.taper_length_um
    if feed_len <= 0.0:
        raise RuntimeError(
            f"the feed is {design.cavity.feed_length_um:.1f} um and the taper drawn "
            f"inside it is {design.layout.taper_length_um:.1f} um, so no straight "
            f"guide remains between the taper and the grating. The circuit cannot be "
            f"assembled from a negative length. Lengthen cavity.feed_length_um beyond "
            f"layout.taper_length_um, or shorten the taper"
        )
    taper_t = float(cfg.taper_transmission)
    tp = ctx.get("taper") or {}
    if cfg.use_taper_stage and tp.get("enabled") and tp.get("transmission") is not None:
        taper_t = float(tp["transmission"])
    facet_t = float(cfg.facet_transmission)
    fc = ctx.get("facet") or {}
    if cfg.use_facet_stage and fc.get("enabled") and fc.get("total_efficiency") is not None:
        facet_t = float(fc["total_efficiency"])

    netlist = {
        "instances": {
            "facet": "coupler",
            "taper": "coupler",
            "feed": "straight",
            "grating": "grating",
        },
        "connections": {
            "facet,out0": "taper,in0",
            "taper,out0": "feed,in0",
            "feed,out0": "grating,in0",
        },
        "ports": {"chip": "facet,in0", "far": "grating,out0"},
    }
    models = {
        "coupler": lossy_coupler,
        "straight": straight,
        "grating": make_grating_model(wl_um, r_c, t_c),
    }
    circuit, _ = _sax.circuit(netlist=netlist, models=models)

    settings = {
        "wl": wl_um,
        "facet": {"transmission": facet_t,
                  "reflection": float(design.facet.ar_reflectivity or 0.0)},
        "taper": {"transmission": taper_t, "reflection": 0.0},
        "feed": {"length_um": feed_len,
                 "neff": float(mode["n_eff_bare"]),
                 "ng": float(mode["n_g"]),
                 "wl0": lam0,
                 "loss_dB_per_cm": float(design.platform.propagation_loss_dB_per_cm)},
    }
    S = circuit(**settings)
    r_chip = np.asarray(S[("chip", "chip")])
    R = np.abs(r_chip) ** 2

    # --- the closed form the assembly is checked against ------------------
    # A facet and a grating separated by a length of guide form an etalon. The
    # standard two-mirror result gives the reflection at the chip directly, and
    # it is an anchor of the kind every solver in this chain carries: an
    # expression known analytically, evaluated on the same inputs, against which
    # the cascade the netlist solver performed can be compared.
    #
    # A single-pass loss budget is not such an anchor. It omits the resonance
    # between the two reflectors, and on this device that omission is worth
    # 4.6 % of the reflected power.
    r_f = np.sqrt(max(float(design.facet.ar_reflectivity or 0.0), 0.0))
    amp = 10.0 ** (-design.platform.propagation_loss_dB_per_cm * (feed_len * 1e-4) / 20.0)
    neff_wl = float(mode["n_eff_bare"]) - (wl_um - lam0) * (
        float(mode["n_g"]) - float(mode["n_eff_bare"])) / lam0
    phi = 2 * np.pi * neff_wl * feed_len / wl_um
    # SIGN CORRECTED 2026-08-17, with the `straight` model above and for the same
    # reason. In the exp(+i omega t) convention a forward wave accumulates
    # exp(-i beta z), so a round trip over the feed is exp(-2 i phi) and the
    # group delay -d(phase)/d(omega) comes out positive, which is what a length
    # of passive guide must contribute.
    #
    # THIS CROSS-CHECK PASSED FOR AS LONG AS BOTH SIDES WERE WRONG. The netlist
    # and this cascade shared the convention, so the residual was exactly zero
    # and the agreement established only that the same expression had been
    # evaluated twice. It became visible the moment the netlist was corrected,
    # and the residual of 2.6e-02 that then appeared is the measure of the error
    # both had been carrying.
    #
    # Two implementations agreeing to numerical precision is weak evidence when
    # they share an author and a convention. The anchor that settled it is
    # physical rather than numerical: the assembled round-trip delay must exceed
    # the bare mirror's, and before the correction it did not.
    round_trip = taper_t * (amp ** 2) * r_c * np.exp(-2j * phi)
    r_closed = r_f + facet_t * round_trip / (1.0 - r_f * round_trip)
    R_closed = np.abs(r_closed) ** 2
    residual = float(np.max(np.abs(R - R_closed)))

    R_mirror = np.abs(r_c) ** 2
    peak_mirror = float(np.max(R_mirror))
    peak_chip = float(np.max(R))

    f_GHz = f_Hz / 1e9
    fwhm_mirror = _fwhm(f_GHz, R_mirror)
    fwhm_chip = _fwhm(f_GHz, R)

    # --- what the assembly says that the arithmetic cannot ----------------
    # Within the stop band the residual facet reflection modulates the mirror
    # the laser actually sees. An anti-reflection coating at 1e-4 is not zero,
    # and the ripple is a property of the pair rather than of either element.
    #
    # The ripple is taken against the same circuit with the facet reflection
    # removed, not against a flat line. The grating's own reflectivity varies by
    # a factor of two across its half-maximum band by definition, so a contrast
    # measured on the reflectivity itself would report that lineshape and call
    # it an etalon.
    r_smooth = facet_t * round_trip
    R_smooth = np.abs(r_smooth) ** 2
    band = R_mirror >= 0.5 * peak_mirror
    if int(band.sum()) >= 3 and np.all(R_smooth[band] > 0):
        ratio = R[band] / R_smooth[band]
        band_hi, band_lo = float(np.max(ratio)), float(np.min(ratio))
        contrast = ((band_hi - band_lo) / (band_hi + band_lo)
                    if (band_hi + band_lo) else 0.0)
    else:
        band_hi = band_lo = contrast = float("nan")

    # the single-pass product, which is the form the cavity stage's arithmetic takes
    single_pass = peak_mirror * (facet_t ** 2) * (taper_t ** 2) * (amp ** 4)

    # the round-trip group delay, from the assembled phase
    phase = np.unwrap(np.angle(r_chip))
    omega = 2 * np.pi * f_Hz
    i0 = int(np.argmax(R))
    tau_ps = float(-np.gradient(phase, omega)[i0] * 1e12)

    cav = ctx.get("cavity") or {}
    tau_expected = None
    if cav.get("enabled") is not False and "tau_dbr_ps" in cav:
        tau_expected = float(cav["tau_dbr_ps"]) + 2.0 * (
            feed_len * 1e-6 * float(mode["n_g"]) / C0) * 1e12

    payload: dict[str, Any] = {
        "enabled": True,
        "backend": "sax",
        "sax_version": getattr(_sax, "__version__", "unknown"),
        "blocks": list(netlist["instances"]),
        "connections": len(netlist["connections"]),
        "feed_length_um": feed_len,
        "facet_transmission": facet_t,
        "taper_transmission": taper_t,
        "peak_reflectivity_at_chip": peak_chip,
        "peak_reflectivity_of_mirror": peak_mirror,
        "closed_form_max_residual": residual,
        "matches_closed_form": bool(residual <= cfg.tolerance),
        "single_pass_product": float(single_pass),
        "etalon_ripple_max": band_hi,
        "etalon_ripple_min": band_lo,
        "facet_etalon_contrast": contrast,
        "fwhm_GHz_at_chip": fwhm_chip,
        "fwhm_GHz_of_mirror": fwhm_mirror,
        "fwhm_rel_delta": float((fwhm_chip - fwhm_mirror) / fwhm_mirror)
        if fwhm_mirror and np.isfinite(fwhm_mirror) else None,
        "group_delay_at_peak_ps": tau_ps,
        "group_delay_expected_ps": tau_expected,
        "group_delay_rel_delta": (
            float((tau_ps - tau_expected) / tau_expected)
            if tau_expected else None
        ),
    }
    ctx.put("circuit", payload)
    ctx.write_stage("circuit", payload, {
        "frequency_Hz": f_Hz,
        "reflectivity_at_chip": R,
        "phase_at_chip": phase,
    })

    # --- what the comparison is allowed to conclude ----------------------
    if not payload["matches_closed_form"]:
        ctx.warn(
            f"the assembled reflection departs from the closed-form two-mirror "
            f"result by up to {residual:.3e} in reflected power, against a tolerance "
            f"of {cfg.tolerance:.1e}. The netlist solver and the analytic cascade "
            "describe the same circuit, so they are expected to agree to numerical "
            "precision"
        )
    if np.isfinite(contrast) and contrast > cfg.etalon_contrast_floor:
        ctx.warn(
            f"the residual facet reflection modulates the mirror the laser sees by "
            f"{contrast * 100:.1f} % across the stop band, the reflected power "
            f"ranging over {band_lo:.4f} to {band_hi:.4f} of the value the same "
            "circuit gives with that reflection removed. The cavity stage applies "
            "the mirror at a single plane and "
            "carries no such ripple, so its threshold and its side-mode margin are "
            "evaluated against a mirror smoother than this one"
        )
    if payload["fwhm_rel_delta"] is not None and abs(payload["fwhm_rel_delta"]) > 0.02:
        ctx.warn(
            f"the mirror bandwidth seen at the chip facet is "
            f"{payload['fwhm_rel_delta'] * 100:+.1f} % from the bandwidth of the "
            "grating alone. A passive feed does not filter, so a shift of this size "
            "indicates an interference the assembly is carrying and the cavity model "
            "is not"
        )
    if payload["group_delay_rel_delta"] is not None and \
            abs(payload["group_delay_rel_delta"]) > 0.05:
        ctx.warn(
            f"the group delay the assembly reports at the mirror peak is "
            f"{tau_ps:.2f} ps against {tau_expected:.2f} ps from the grating delay "
            "plus twice the feed. That delay sets the Pockels lever, and the lever "
            "sets the mode-hop-free range"
        )
    return payload
