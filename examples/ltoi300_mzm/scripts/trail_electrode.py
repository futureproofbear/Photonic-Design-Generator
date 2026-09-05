"""The electrode the kit draws, which is periodically interrupted.

Every travelling-wave figure this study has reported treats the modulator
electrode as a uniform coplanar line of a 20 um signal conductor in a 5.5 um
gap. The drawn polygons say otherwise. Cutting the emitted GDS along the run
shows the signal conductor stepping between 20 um and 10 um and the gap between
5.5 um and 15.5 um, on a period of 58 um, with the narrow-gap section holding
for 53 of every 58 and the wide-gap section for 5.

The builder names the feature. ``trail_cpw`` draws "a CPW transmission line with
periodic T-rails on all electrodes", and the O-band parameters are a rail length
of 53 um, a cut of 5 um, and a head and a tooth of 2.5 um each, which is where
the signal conductor loses 2(th + tt) = 10 um and each gap gains the same. The
C-band cell uses 1.5 um for both, so its signal steps from 16 um to 10 um and
its gap from 5.5 um to 11.5 um.

A T-rail exists to separate two quantities a plain line ties together. The
capacitance that sets the microwave index is loaded by the narrow-gap sections,
while the metal that carries the current, and therefore the conductor loss, is
set by the full conductor. What it means for a model that assumes one uniform
cross-section is that the model is solving the loaded section and applying it
over the whole length.

This runs the electro-optic stage at both drawn cross-sections and combines them
along the line. Capacitance per unit length averages arithmetically, since the
sections are in parallel across the line. Inductance per unit length averages
arithmetically as well, the sections being in series along it, and follows from
each section's capacitance with the dielectrics removed. The electro-optic phase
accumulates per unit length, so the half-wave voltage combines as a reciprocal
average.

The period is 58 um against a microwave wavelength of 1.3 mm at 100 GHz, so the
line is homogenisable over more than twenty periods and this average is the
right instrument. A stopband sits near the frequency at which one period is half
a wavelength, which for this pitch is about 1.1 THz and does not concern the
device.

    python examples/ltoi300_mzm/scripts/trail_electrode.py [oband|cband]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain import rf                                    # noqa: E402

#: the two drawn cross-sections, from _builders/mzms.py and confirmed by cuts
#: through the emitted GDS at tools/measure_layout.py
CELLS = {
    "oband": dict(
        design="examples/ltoi300_mzm/design_mzm_oband.yaml",
        loaded=dict(width=20.0, gap=5.5, ground=50.0),
        cut=dict(width=10.0, gap=15.5, ground=45.0),
    ),
    "cband": dict(
        design="examples/ltoi300_mzm/design_mzm_cband.yaml",
        loaded=dict(width=16.0, gap=5.5, ground=50.0),
        cut=dict(width=10.0, gap=11.5, ground=47.0),
    ),
}
RAIL_UM, CUT_UM = 53.0, 5.0        # tl and tc of DEFAULT_TRAIL_PARAMS
C0 = 299792458.0


def run(design: str, geom: dict[str, float]) -> dict:
    """The electro-optic stage at one cross-section, through the chain itself."""
    cmd = [sys.executable, "-m", "picchain.cli", "run", str(ROOT / design),
           "--stages", "eo", "--json",
           "--set", f"electrodes.width_um={geom['width']}",
           "--set", f"electrodes.gap_um={geom['gap']}",
           "--set", f"electrodes.ground_width_um={geom['ground']}"]
    p = subprocess.run(cmd, cwd=ROOT / "design-chain", capture_output=True, text=True)
    if p.returncode not in (0, 2):
        sys.stderr.write(p.stdout[-4000:] + p.stderr[-4000:])
        raise SystemExit(f"the chain exited {p.returncode}")
    start = p.stdout.index("{")
    return json.loads(p.stdout[start:])["metrics"]


def report(name: str, m: dict) -> dict[str, float]:
    tw = m["eo"]["travelling_wave"]
    out = dict(
        C=m["eo"]["capacitance_pF_per_cm"] * 1e-12 * 100,
        C_air=tw["capacitance_air_pF_per_cm"] * 1e-12 * 100,
        n_m=tw["microwave_index"],
        Z0=tw["characteristic_impedance_ohm"],
        VpiL=m["eo"]["VpiL_V_cm"],
        gamma=m["eo"]["eo_overlap_gamma"],
        f3=tw["electro_optic_3dB_GHz"],
        alpha10=tw["conductor_loss_dB_per_cm_at_10GHz"],
        n_g=tw["optical_group_index"],
    )
    print(f"  {name:24} C {out['C']*1e12/100:7.4f} pF/cm   n_m {out['n_m']:7.4f}   "
          f"Z0 {out['Z0']:6.2f} ohm   VpiL {out['VpiL']:7.4f} V.cm   "
          f"Gamma {out['gamma']:.4f}")
    return out


def main(argv: list[str]) -> int:
    key = argv[1] if len(argv) > 1 else "oband"
    c = CELLS[key]
    f_l = RAIL_UM / (RAIL_UM + CUT_UM)
    f_c = 1.0 - f_l

    print(f"{key}: the rail holds {RAIL_UM} um of every {RAIL_UM + CUT_UM} um, "
          f"so {100 * f_l:.1f} per cent of the run is at the narrow gap\n")
    loaded = report("narrow gap, as modelled", run(c["design"], c["loaded"]))
    cutsec = report("wide gap, the T-rail cut", run(c["design"], c["cut"]))

    # the line, homogenised over the period
    C = f_l * loaded["C"] + f_c * cutsec["C"]
    L = (f_l / (C0**2 * loaded["C_air"]) + f_c / (C0**2 * cutsec["C_air"]))
    n_m = C0 * (L * C) ** 0.5
    Z0 = (L / C) ** 0.5

    # the half-wave voltage, the phase accumulating per unit length
    VpiL = 1.0 / (f_l / loaded["VpiL"] + f_c / cutsec["VpiL"])

    # the loss. The stage reports an attenuation, which is a resistance divided
    # by twice the local impedance, so the resistance is recovered from each
    # section, averaged along the line as a series element, and divided by the
    # impedance the homogenised line has. Averaging the attenuations directly
    # would divide each by the wrong impedance.
    n_g = loaded["n_g"]

    def resistance(sec):
        a = sec["alpha10"] * 100 / rf.NEPER_TO_DB       # Np/m at 10 GHz
        return 2.0 * a * sec["Z0"]                      # ohm/m at 10 GHz

    R10 = f_l * resistance(loaded) + f_c * resistance(cutsec)
    alpha0 = R10 / (2.0 * Z0) / (1e10) ** 0.5

    def alpha(f):
        return alpha0 * f**0.5

    L_m = 5000e-6
    f3 = rf.bandwidth(L_m, alpha, n_m, n_g) / 1e9
    f3_uniform = loaded["f3"]

    print(f"\n  the line homogenised over one period")
    print(f"    capacitance          {C * 1e12 / 100:8.4f} pF/cm  against "
          f"{loaded['C'] * 1e12 / 100:.4f} uniform")
    print(f"    microwave index      {n_m:8.4f}        against {loaded['n_m']:.4f}")
    print(f"    optical group index  {n_g:8.4f}")
    print(f"    velocity mismatch    {n_m - n_g:+8.4f}        against "
          f"{loaded['n_m'] - n_g:+.4f}")
    print(f"    impedance            {Z0:8.2f} ohm    against {loaded['Z0']:.2f}")
    print(f"    VpiL                 {VpiL:8.4f} V.cm   against {loaded['VpiL']:.4f}")
    print(f"    conductor loss       {alpha0 * (1e10) ** 0.5 * rf.NEPER_TO_DB / 100:8.4f} "
          f"dB/cm at 10 GHz against {loaded['alpha10']:.4f}")
    print(f"    3 dB bandwidth       {f3:8.2f} GHz    against {f3_uniform:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
