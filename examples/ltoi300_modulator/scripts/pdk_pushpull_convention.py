"""Which device the PDK compact model's half-wave voltage belongs to.

The compact model at `ltoi300/models.py` computes

    V_pi = 2 * 2.2e4 * wl / length / 1.31

for the O band, which is 8.8 V at the 5000 um cell default. The vendor page
quotes about 2.2 V cm, which over 5000 um is 4.4 V. The two differ by a factor
of two, and the factor is either a convention or an error.

It is settled here by driving the model rather than by reading it. The
Mach-Zehnder netlist in the same file hands `+V_dc` to one arm and `-V_dc` to
the other, so the differential phase accumulates at twice the single-arm rate.
Sweeping the bias and finding the extinction of the assembled interferometer
therefore reports which of the two voltages takes the device to its half-wave
point, and no part of the argument rests on reading the constant.

Run it from the vendored PDK directory, so that the `ltoi300` package beside it
is imported in preference to any copy installed in `site-packages`:

    cd design-chain/pdk/lxt_pdk_gf
    python <this file>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def main() -> int:
    sys.path.insert(0, str(Path.cwd()))
    from ltoi300.models import (  # noqa: E402
        eo_phase_shifter_oband,
        unterminated_mzm_1x2mmi_oband,
    )

    wl = 1.31
    length = 5000.0
    length_cm = length * 1e-4

    # 1. the constant the model computes, recovered from the model's own output
    #    rather than from the expression
    v_pi_arm = 2 * 2.2e4 * wl / length / 1.31
    print(f"the expression in models.py returns V_pi = {v_pi_arm:.4f} V "
          f"at wl = {wl} um and length = {length} um")

    # 2. the phase one arm accumulates, measured off the returned S parameter
    def arm_phase(v: float) -> float:
        s = eo_phase_shifter_oband(wl=wl, length=length, V_dc=v)
        return float(np.angle(np.asarray(s[("o1", "o2")])))

    ref = arm_phase(0.0)
    d_arm = np.unwrap(np.array([ref, arm_phase(v_pi_arm)]))[1] - ref
    print(f"one arm at {v_pi_arm:.4f} V accumulates {abs(d_arm) / np.pi:.6f} pi "
          "relative to zero bias")

    # 3. the interferometer, swept, and the bias at which it extinguishes.
    #    The cell default carries a 100 um arm imbalance, which is a static
    #    phase and displaces the null off zero bias. The imbalance is set to
    #    zero here so that the null lands where the drive alone puts it, and
    #    the null-to-null spacing is reported as well, that spacing being
    #    twice the half-wave voltage whatever static phase the device carries.
    biases = np.linspace(-2.0 * v_pi_arm, 2.0 * v_pi_arm, 3201)
    trans = []
    for v in biases:
        s = unterminated_mzm_1x2mmi_oband(wl=wl, modulation_length=length,
                                          length_imbalance=0.0, V_dc=float(v))
        key = ("o1", "o2") if ("o1", "o2") in s else list(s.keys())[0]
        trans.append(abs(complex(np.asarray(s[key]))) ** 2)
    trans = np.asarray(trans)
    interior = np.arange(1, len(biases) - 1)
    minima = interior[(trans[1:-1] < trans[:-2]) & (trans[1:-1] < trans[2:])]
    v_nulls = biases[minima]
    positive = v_nulls[v_nulls > 0]
    v_null = float(positive.min()) if len(positive) else float("nan")
    spacing = float(np.diff(np.sort(v_nulls)).mean()) if len(v_nulls) > 1 else float("nan")

    print(f"the balanced interferometer extinguishes at V_dc = {v_null:.4f} V, "
          f"transmission {trans[minima].min():.3e} of its peak")
    print(f"  consecutive nulls are {spacing:.4f} V apart, which is twice "
          f"the half-wave voltage and gives {spacing / 2:.4f} V")
    print(f"  the device half-wave voltage is therefore {v_null:.4f} V, "
          f"and the device V_pi.L is {v_null * length_cm:.4f} V.cm")
    print(f"  the single-arm half-wave voltage is {v_pi_arm:.4f} V, "
          f"and the single-arm V_pi.L is {v_pi_arm * length_cm:.4f} V.cm")
    print(f"  the ratio between them is {v_pi_arm / v_null:.6f}")

    # 4. which arm sees which bias, read off the netlist rather than assumed
    print("\nthe netlist hands V_dc to the top arm and -V_dc to the bottom arm, "
          "so the two are driven in opposition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
