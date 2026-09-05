"""The modulator assembled from its own measured blocks.

Every figure this study has reported so far describes a part: the electrode, the
splitter, the taper, the heater. The cell is the three cascaded, and the
quantities a link budget consumes belong to the cascade rather than to any part
of it. This assembles them explicitly.

Nothing is assumed that has not been measured here. The splitter transmission
and imbalance come from the two-junction cascade in the full cross-section. The
half-wave voltage comes from the electrode stage. The propagation loss is the
one quantity nobody has measured, so it enters as the bracket transferred from
the literature and the result is reported across it.

    python examples/ltoi300_mzm/scripts/assembled.py
"""

from __future__ import annotations

import numpy as np

#: the splitter, from examples/ltoi300_mmi: the two-junction cascade at the
#: length the kit draws. The imbalance of a 1x2 is zero by symmetry of the
#: drawing, so the kit's own 2x2 figure is carried as the alternative
SPLITTERS = (
    ("the 1x2 as measured here", 0.9912, 0.000),
    ("the 2x2 as measured here", 0.8999, 0.039),
    ("the imbalance the kit states", 0.9912, 0.060),
)

VPI_ARM_V_CM = 5.5286        # electrode stage, O band, one arm
L_ELECTRODE_CM = 0.5         # the 5000 um the cell draws
DELTA_L_UM = 100.0           # the arm imbalance the cell draws
LOSSES_DB_CM = (0.31, 0.95)  # transferred to this cross-section


def transfer(v: np.ndarray, t_split: float, imbalance_dB: float,
             loss_dB_cm: float) -> np.ndarray:
    """Power at the through port of a push-pull interferometer.

    The two arms carry equal and opposite phase, so the differential phase
    reaches pi at half the single-arm voltage. Their amplitudes differ by the
    splitter's imbalance and by the loss over the length difference between
    them.
    """
    vpi_arm = VPI_ARM_V_CM / L_ELECTRODE_CM
    phi = np.pi * v / vpi_arm

    a_split = np.sqrt(t_split / 2.0)                 # amplitude into each arm
    r = 10 ** (-imbalance_dB / 20.0)                 # the imbalance, as amplitude
    a1, a2 = a_split, a_split * r

    # loss over each arm, the second being longer by the drawn imbalance
    l1 = 10 ** (-loss_dB_cm * L_ELECTRODE_CM / 20.0)
    l2 = 10 ** (-loss_dB_cm * (L_ELECTRODE_CM + DELTA_L_UM * 1e-4) / 20.0)

    field = a1 * l1 * np.exp(1j * phi) + a2 * l2 * np.exp(-1j * phi)

    # The combiner is a splitter of the same kind run backwards, so it carries
    # the same transmission and the same 1/sqrt(2) per branch. Writing that as
    # `(2.0 / t_split) * t_split` cancelled it, and the cell was priced with one
    # splitter where it draws two.
    return np.abs(field * np.sqrt(t_split / 2.0)) ** 2


def main() -> int:
    # the guard that would have caught the missing combiner: two lossless
    # splitters and balanced arms pass everything, and two splitters of
    # transmission t pass t squared
    assert abs(float(transfer(np.array([0.0]), 1.0, 0.0, 0.0)[0]) - 1.0) < 1e-12
    assert abs(float(transfer(np.array([0.0]), 0.9912, 0.0, 0.0)[0])
               - 0.9912**2) < 1e-12

    v = np.linspace(0.0, 12.0, 24001)
    print(f"{'splitter':>30} {'loss':>6} {'insertion':>10} {'extinction':>11} "
          f"{'Vpi device':>11}")
    for name, t_split, imb in SPLITTERS:
        for loss in LOSSES_DB_CM:
            p = transfer(v, t_split, imb, loss)
            peak, trough = float(np.max(p)), float(np.min(p))
            insertion = -10 * np.log10(max(peak, 1e-15))
            extinction = 10 * np.log10(peak / max(trough, 1e-15))
            v_pi = float(v[int(np.argmin(p))])
            print(f"{name:>30} {loss:5.2f}  {insertion:8.3f} dB "
                  f"{extinction:8.1f} dB {v_pi:9.3f} V")
    print("\nthe insertion loss is two splitters and one arm of propagation;")
    print("the extinction is set by the amplitude the two arms deliver, being the")
    print("splitter's imbalance and the loss over the 100 um the arms differ by")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
