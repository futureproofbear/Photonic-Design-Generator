"""Stage 18 - the Mach-Zehnder modulator: the device figures, from one arm.

The electro-optic stage solves one guide between two electrodes and reports the
single-arm figures. A Mach-Zehnder is two arms, and what a data sheet quotes and
a link budget consumes is the device figure, so the conversion is performed here
and the convention is stated in the payload rather than left to the reader.

**The factor of two is the whole content of this stage, and it is where the
convention is lost.** A push-pull interferometer drives its two arms in
opposition, so the differential phase accumulates at twice the single-arm rate
and V_pi is half the single-arm figure. A vendor relation that omits which of
the two it quotes cannot be reconciled with a solve, and the same ambiguity has
been observed to propagate into an electro-optic overlap that differs by two.

Why the band matters more than the bandwidth
--------------------------------------------
A modulator carrying a signal about a carrier passes a band, and a 3 dB
bandwidth quoted against the carrier frequency describes a device that is 3 dB
down where it is required to work. The response is therefore evaluated at the
edges of the declared band, and the drive the device actually demands there is
reported beside the nominal V_pi.
"""

from __future__ import annotations

import math
from typing import Any

from .. import process, rf
from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary


def drive_factor(drive: str) -> float:
    """The factor by which the interferometer beats one of its arms.

    Push-pull drives the arms in opposition, so the differential phase reaches pi
    at half the single-arm voltage. A single-arm drive reaches it at the
    single-arm voltage, the second arm being a passive reference.

    Held as its own function because it is the one number the conversion turns
    on, and because a stage is to report the value it used.
    """
    return 2.0 if drive == "push_pull" else 1.0


def device_VpiL(single_arm_VpiL_V_cm: float, drive: str) -> float:
    """The device half-wave figure from the single-arm one."""
    return single_arm_VpiL_V_cm / drive_factor(drive)


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    m = design.modulator
    if not m.enabled:
        payload = {"enabled": False}
        ctx.put("modulator", payload)
        return payload

    eo = ctx.get("eo")
    if eo is None or not eo.get("enabled"):
        raise RuntimeError("stage 'modulator' requires stage 'eo' to have run with electrodes enabled")

    e = design.electrodes
    geom = process.geometry(design, design.process.simulate)

    L_um = float(eo["electrode_length_um"])
    L_m = L_um * 1e-6
    L_cm = L_um * 1e-4

    single = float(eo["VpiL_V_cm"])
    dev_VpiL = device_VpiL(single, m.drive)
    Vpi = dev_VpiL / L_cm if L_cm > 0 else float("inf")

    tw = eo.get("travelling_wave") or {}

    # What a source of the declared impedance has to supply.
    #
    # Vpi_V is a voltage across the electrode. A link budget consumes the drive a
    # source delivers, and a line whose impedance differs from the source's takes
    # a different share of it: the launched wave is 2*Z0/(Z0 + Zs) of what the
    # same source puts into a matched line. Reporting only the electrode voltage
    # flatters a low-impedance line, and a ground-signal-ground line on this
    # platform sits near 31 ohm against a 50 ohm driver.
    launch = float(tw.get("drive_transmitted_into_line") or 1.0)

    payload: dict[str, Any] = {
        "enabled": True,
        "configuration": m.configuration,
        "drive": m.drive,
        # the factor the conversion below actually applied, rather than an arm
        # count no calculation reads. `configuration` already states the
        # geometry, and a reported number that nothing computed from is the
        # shape of thing that is later quoted as a result
        "drive_factor": drive_factor(m.drive),
        "electrode_length_um": L_um,
        "VpiL_single_arm_V_cm": single,
        "VpiL_device_V_cm": dev_VpiL,
        "Vpi_V": Vpi,
        "drive_transmitted_into_line": launch,
        "Vpi_at_source_V": Vpi / launch if launch > 0 else float("inf"),
        "note_convention": (
            "VpiL_single_arm_V_cm is what the electro-optic stage solves, one guide "
            "between two electrodes. VpiL_device_V_cm is the interferometer, that "
            f"figure divided by drive_factor {drive_factor(m.drive):.0f} for the "
            f"declared '{m.drive}' drive. Vpi_V is the device figure over the "
            "declared electrode length"
        ),
    }

    # -- the response across the band the device must actually pass ---------
    if tw.get("enabled") and m.rf_band_GHz:
        Z0 = float(tw["characteristic_impedance_ohm"])
        n_m = float(tw["microwave_index"])
        n_g = float(tw["optical_group_index"])

        # The number of conductors carrying the return is read from the
        # electro-optic stage rather than assumed here. Assuming it made this a
        # second implementation of the same loss, and the two diverged the moment
        # the first learned about ground-signal-ground lines: the bandwidth was
        # computed at 1.5 conductors and the in-band response at 2.
        n_cond = float(tw.get("conductors_carrying_the_return") or 2.0)

        def alpha(f_Hz: float) -> float:
            R = rf.skin_resistance_per_m(f_Hz, e.conductivity_S_per_m,
                                         geom.electrode_width_um * 1e-6,
                                         e.thickness_um * 1e-6,
                                         n_conductors=n_cond)
            return R / (2.0 * Z0)

        f_lo, f_hi = float(min(m.rf_band_GHz)), float(max(m.rf_band_GHz))
        points = [f_lo, 0.5 * (f_lo + f_hi), f_hi]
        band = []
        for f_GHz in points:
            resp = rf.response(f_GHz * 1e9, L_m, alpha(f_GHz * 1e9), n_m, n_g)
            band.append({
                "frequency_GHz": f_GHz,
                "response": resp,
                "response_dB": 20 * math.log10(resp) if resp > 0 else float("-inf"),
                # the drive the device demands at this frequency to reach the
                # same optical modulation the DC figure delivers
                "Vpi_effective_V": Vpi / resp if resp > 0 else float("inf"),
                "Vpi_at_source_V": (Vpi / resp / launch
                                    if resp > 0 and launch > 0 else float("inf")),
            })

        worst = min(band, key=lambda r: r["response"])

        # Cross-check: the bandwidth the electro-optic stage reported must be the
        # frequency at which THIS loss model crosses the same level. Where a
        # quantity can be reached by two routes, make them meet and report the
        # residual, rather than printing one beside the other.
        f3 = tw.get("electro_optic_3dB_GHz")
        if f3:
            m_at_f3 = rf.response(float(f3) * 1e9, L_m, alpha(float(f3) * 1e9), n_m, n_g)
            residual = abs(m_at_f3 - 1.0 / math.sqrt(2.0))
            payload["response_at_the_reported_3dB_point"] = m_at_f3
            payload["loss_model_residual"] = residual
            if residual > 5e-3:
                ctx.warn(
                    f"this stage and the electro-optic stage disagree about the "
                    f"electrode loss: at the reported {float(f3):.2f} GHz the response "
                    f"here is {m_at_f3:.4f} against the {1/math.sqrt(2):.4f} that "
                    "figure asserts. The two are computing the same quantity by two "
                    "routes and one of them is wrong",
                    key="modulator.loss_model_disagreement",
                )
        payload.update({
            "rf_band_GHz": [f_lo, f_hi],
            "band_response": band,
            "worst_in_band_dB": worst["response_dB"],
            "worst_in_band_frequency_GHz": worst["frequency_GHz"],
            "Vpi_effective_at_worst_V": worst["Vpi_effective_V"],
            # the figure the link budget actually consumes: the worst frequency
            # in the band, referenced to what the source must supply
            "Vpi_at_source_at_worst_V": worst["Vpi_at_source_V"],
            "electro_optic_3dB_GHz": tw.get("electro_optic_3dB_GHz"),
        })

        if tw.get("electro_optic_3dB_GHz") is not None and \
                float(tw["electro_optic_3dB_GHz"]) < f_hi:
            ctx.warn(
                f"the 3 dB bandwidth is {float(tw['electro_optic_3dB_GHz']):.1f} GHz and "
                f"the band reaches {f_hi:.1f} GHz, so the device is beyond its own "
                f"3 dB point at the top of the band it must pass. The drive required "
                f"there is {worst['Vpi_effective_V']:.2f} V against {Vpi:.2f} V at DC"
            )

    ctx.put("modulator", payload)
    ctx.write_stage("modulator", payload, {})
    return payload
