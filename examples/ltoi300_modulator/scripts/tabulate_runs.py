"""Tabulate the electro-optic and radio-frequency figures of every run in a tree.

The study poses one cross-section to the chain repeatedly, under two material
files and over a ladder of electrostatic mesh densities, and the comparison is
between runs rather than within one. This reads every `metrics.json` beneath
the run directory and prints the quantities the study turns on, so that a table
in the README is taken from the runs rather than transcribed.

    python examples/ltoi300_modulator/scripts/tabulate_runs.py [runs_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FIELDS = [
    ("name", lambda m, r: r["_design"].get("meta", {}).get("name", "")),
    ("h_um", lambda m, r: m["eo"]["rf_mesh"]["d_fine_um"]),
    ("gap_um", lambda m, r: m["eo"]["electrode_gap_um"]),
    ("wg_um", lambda m, r: m["mode"]["geometry_um"]["wg_top_width_um"]),
    ("conf", lambda m, r: m["mode"]["confinement_film"]),
    ("L_um", lambda m, r: m["eo"]["electrode_length_um"]),
    ("n_e", lambda m, r: m["eo"]["n_extraordinary"]),
    ("n_g", lambda m, r: m["eo"]["n_g_used"]),
    ("Gamma", lambda m, r: m["eo"]["eo_overlap_gamma"]),
    ("VpiL_arm", lambda m, r: m["eo"]["VpiL_V_cm"]),
    ("VpiL_dev", lambda m, r: (m.get("modulator") or {}).get("VpiL_device_V_cm")),
    ("C_pF_cm", lambda m, r: m["eo"]["capacitance_pF_per_cm"]),
    ("n_m", lambda m, r: m["eo"]["travelling_wave"]["microwave_index"]),
    ("Z0_ohm", lambda m, r: m["eo"]["travelling_wave"]["characteristic_impedance_ohm"]),
    ("dn", lambda m, r: m["eo"]["travelling_wave"]["velocity_mismatch"]),
    ("f3dB_GHz", lambda m, r: m["eo"]["travelling_wave"]["electro_optic_3dB_GHz"]),
    ("aC_dB_cm_10G", lambda m, r: m["eo"]["travelling_wave"]["conductor_loss_dB_per_cm_at_10GHz"]),
    ("E_Si", lambda m, r: m["eo"]["microwave_energy_by_material"].get("Si", 0.0)),
    ("E_LT", lambda m, r: m["eo"]["microwave_energy_by_material"].get("LiTaO3", 0.0)),
    ("conv", lambda m, r: m["eo"]["convergence"].get("resolved")),
    ("dGamma", lambda m, r: m["eo"]["convergence"].get("eo_overlap_gamma_rel_shift")),
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parent.parent / "runs")
    rows = []
    for p in sorted(root.glob("*/metrics.json")):
        raw = json.loads(p.read_text(encoding="utf-8"))
        m = raw.get("metrics", raw)
        if "eo" not in m or not m["eo"].get("enabled"):
            continue
        rd = p.parent / "design.resolved.json"
        raw["_design"] = (json.loads(rd.read_text(encoding="utf-8"))
                          if rd.exists() else {})
        row = {"run": p.parent.name[:15]}
        for k, f in FIELDS:
            try:
                row[k] = f(m, raw)
            except (KeyError, TypeError):
                row[k] = None
        rows.append(row)

    if not rows:
        print(f"no electro-optic runs under {root}")
        return 1

    keys = ["run"] + [k for k, _ in FIELDS]
    widths = {k: max(len(k), *(len(_fmt(r.get(k))) for r in rows)) for k in keys}
    print("  ".join(k.ljust(widths[k]) for k in keys))
    for r in rows:
        print("  ".join(_fmt(r.get(k)).ljust(widths[k]) for k in keys))
    return 0


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.5g}"
    return str(v)


if __name__ == "__main__":
    raise SystemExit(main())
