"""The terminated cell against the unterminated one, on the drawn line.

The kit ships each modulator and each phase shifter twice, and the mask study
establishes that the two differ by one polygon on the high-resistance layer
beyond the far end of the signal metal. This computes what that polygon is worth.

Two units are reported and the difference between them is the whole point.

A modulation response is conventionally referred to its own value at zero
frequency, and `rf.bandwidth` needs it in that unit. On a line left open that
reference is twice the matched line's, an open end doubling the standing
voltage, so a 3 dB point read in that unit measures the loss of a doubling the
cell had to begin with. It falls to a few gigahertz and reads as a collapse.

Two cells are compared by driving them from the same source and asking what
modulation each produces, which is the unnormalised index. In that unit the open
cell is better at low frequency, worse at one null, and indistinguishable
elsewhere.

The line parameters are those of the homogenised T-rail electrode computed by
the companion script, since the electrode the kit draws is periodically
interrupted and a uniform cross-section is not the device.

    python examples/ltoi300_mzm/scripts/far_end_load.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))

from picchain import rf                                    # noqa: E402

#: the homogenised T-rail line, from scripts/trail_electrode.py, and the metal
#: the chain's own skin-effect model needs. The signal conductor is 20 um on the
#: O-band rail and 10 um where the rail is cut, and 16 and 10 in the C band.
LINES = {
    "O band": dict(n_m=2.2783, n_g=2.1834, Z0=44.00, w_rail=20e-6, w_cut=10e-6),
    "C band": dict(n_m=2.2614, n_g=2.1347, Z0=45.76, w_rail=16e-6, w_cut=10e-6),
}
LENGTH_M = 5000e-6              # the modulation length the cells draw
#: the unmodulated line beyond the modulation section, measured off the drawn
#: cell: the unterminated modulator runs its signal metal to 5220 um against
#: 5045 for the terminated one. The microwave crosses it twice and the optical
#: carrier does not cross it at all, so it rotates the returned wave
STUB_M = 220e-6
THICKNESS_M = 0.9e-6            # ASSUMPTION: the PDK draws no metal thickness
SIGMA = 4.1e7                   # bulk gold, as the design files declare
N_CONDUCTORS = 1.5              # what the electro-optic stage uses for a gsg line
RAIL_UM, CUT_UM = 53.0, 5.0
POINTS_GHz = (0.1, 5.0, 10.0, 20.0, 40.0, 100.0)


def attenuation(L: dict):
    """The attenuation of the homogenised line, from the chain's own resistance.

    Extrapolating the 10 GHz figure as the square root of frequency was tried
    and it is wrong below about 7 GHz, which is exactly where the far-end
    reflection matters. The skin depth in gold reaches the 0.9 um the metal is
    assumed to be at that frequency, and below it the current occupies the whole
    conductor and the resistance stops falling. At 0.1 GHz the square-root model
    understates the loss by a factor of nine and overstates the advantage an
    open end holds by half a decibel.

    The resistance is averaged along the line as a series element, the two
    sections differing in the width of the signal conductor.
    """
    f_l = RAIL_UM / (RAIL_UM + CUT_UM)
    f_c = 1.0 - f_l

    def alpha(f: float) -> float:
        r = (f_l * rf.skin_resistance_per_m(f, SIGMA, L["w_rail"], THICKNESS_M,
                                            n_conductors=N_CONDUCTORS)
             + f_c * rf.skin_resistance_per_m(f, SIGMA, L["w_cut"], THICKNESS_M,
                                              n_conductors=N_CONDUCTORS))
        return r / (2.0 * L["Z0"])

    return alpha


def bandwidth_with_stub(alpha, n_m, n_g, G) -> float:
    """The self-referred 3 dB point, the stub included where the line reflects."""
    lo, hi = 1e8, 1e12
    def m(f):
        return rf.response_loaded(f, LENGTH_M, alpha(f), n_m, n_g, G, "dc",
                                  STUB_M if G else 0.0)
    if m(lo) <= 1 / math.sqrt(2):
        return lo
    while hi - lo > 1e6:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if m(mid) > 1 / math.sqrt(2) else (lo, mid)
    return hi


def advantage_ends(alpha, n_m, n_g) -> float:
    """The frequency at which the open line stops being the better of the two."""
    def d(f):
        m = rf.response_loaded(f, LENGTH_M, alpha(f), n_m, n_g, 0.0, "incident")
        o = rf.response_loaded(f, LENGTH_M, alpha(f), n_m, n_g, 1.0, "incident",
                            STUB_M)
        return 20 * math.log10(o / m)

    lo, hi = 1e8, 2e10
    while hi - lo > 1e6:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if d(mid) > 0 else (lo, mid)
    return hi


def ripple_settles(alpha, n_m, n_g, bound_dB: float = 0.5,
                   f_hi: float = 2e11) -> float:
    """Above what frequency the two lines stay within ``bound_dB`` of each other.

    The ratio does not cross zero once and stay there. The returned wave
    dephases against the carrier and the ratio rings about parity with a
    decaying amplitude, so the honest statement is where the ringing falls
    inside a stated bound rather than where it last crosses.
    """
    def d(f):
        m = rf.response_loaded(f, LENGTH_M, alpha(f), n_m, n_g, 0.0, "incident")
        o = rf.response_loaded(f, LENGTH_M, alpha(f), n_m, n_g, 1.0, "incident",
                            STUB_M)
        return abs(20 * math.log10(o / m))

    n = 4001
    ratio = math.log(f_hi / 1e8) / (n - 1)
    settled = f_hi
    for k in range(n - 1, -1, -1):
        f = 1e8 * math.exp(ratio * k)
        if d(f) > bound_dB:
            break
        settled = f
    return settled


def main() -> int:
    for band, L in LINES.items():
        alpha = attenuation(L)
        n_m, n_g = L["n_m"], L["n_g"]
        print(f"\n{band}: {LENGTH_M * 1e3:.0f} mm, microwave index {n_m}, "
              f"group index {n_g}")

        print("\n  referred to each line's own value at zero frequency")
        for G, name in ((0.0, "terminated"), (1.0, "open")):
            f3 = bandwidth_with_stub(alpha, n_m, n_g, G) / 1e9
            row = "  ".join(
                f"{20 * math.log10(rf.response_loaded(f * 1e9, LENGTH_M, alpha(f * 1e9), n_m, n_g, G, 'dc', STUB_M if G else 0.0)):+6.2f}"
                for f in POINTS_GHz)
            print(f"    {name:11} 3 dB at {f3:8.2f} GHz   {row}")
        print("    " + " " * 30
              + "  ".join(f"{f:>6g}" for f in POINTS_GHz) + "  GHz")

        print("\n  open against terminated, both driven from the same source")
        row = "  ".join(
            f"{20 * math.log10(rf.response_loaded(f * 1e9, LENGTH_M, alpha(f * 1e9), n_m, n_g, 1.0, 'incident', STUB_M) / rf.response_loaded(f * 1e9, LENGTH_M, alpha(f * 1e9), n_m, n_g, 0.0, 'incident')):+6.2f}"
            for f in POINTS_GHz)
        print(f"    {'':11}{'':19}{row}")
        p = rf.far_end_penalty(LENGTH_M, alpha, n_m, n_g, 1.0, 1e8, 2e11,
                               stub_m=STUB_M)
        print(f"\n    best  {p['best_dB']:+6.2f} dB at {p['best_at_Hz'] / 1e9:7.2f} GHz")
        print(f"    worst {p['worst_dB']:+6.2f} dB at {p['worst_at_Hz'] / 1e9:7.2f} GHz")
        down = advantage_ends(alpha, n_m, n_g)
        settled = ripple_settles(alpha, n_m, n_g)
        print(f"    the open line is the better one below {down / 1e9:.2f} GHz")
        print(f"    the two stay within 0.5 dB of each other above "
              f"{settled / 1e9:.2f} GHz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
