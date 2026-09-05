"""The normalisation of the overlap integral, and the residual it accounts for.

The electro-optic stage forms

    Gamma = (G/V) * Int_film( E_rf |E_opt|^2 ) / Int_all( |E_opt|^2 )

and converts it to an effective-index change by

    dn_eff = Gamma * (1/2) n_e^3 r33 (V/G),

which is equivalent to weighting the local index change by the optical
intensity and dividing by the total intensity. First-order perturbation theory
for a guided mode weights it differently. Taking the standard result

    d(beta) = (omega eps0 / 4) Int( d(eps) |E|^2 ) / P,
    P       = v_g U,
    U       = (eps0 / 4) Int( d(omega eps)/d(omega) |E|^2 ) + (mu0 / 4) Int(|H|^2),

and using d(omega eps_r)/d(omega) = 2 n n_g,mat for a dispersive dielectric,

    dn_eff = n_g n_e Int_film( dn |E|^2 ) / Int_all( n n_g,mat |E|^2 ).

The two agree only where n_g n_e equals the intensity-weighted mean of
n n_g,mat, which holds for a mode wholly inside a non-dispersive film. On a
thin-film ridge a quarter of the mode sits in oxide, where n n_g,mat is half
its value in the film, so the two differ by a factor this script computes.

The ratio is formed from the run artefacts: the intensity map and the film mask
the stage itself wrote, and the material indices evaluated by the chain's own
library on the material file the design declared.

    python examples/ltoi300_modulator/scripts/perturbation_normalisation.py \
        <run_dir> [<run_dir> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))
from picchain.materials import MaterialLibrary  # noqa: E402


def group_index(lib: MaterialLibrary, name: str, lam: float, axis: str,
                cut: str, dlam: float = 0.005) -> tuple[float, float]:
    """The phase and group index of one material at one wavelength.

    The group index is differenced off the same dispersion the mode solve used,
    rather than taken from a second source, so that the ratio below is formed
    from one material model.
    """
    mat = lib[name]
    n = float(mat.index(lam, axis, False))
    n_p = float(mat.index(lam + dlam, axis, False))
    n_m = float(mat.index(lam - dlam, axis, False))
    return n, n - lam * (n_p - n_m) / (2 * dlam)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    for a in args:
        run_dir = Path(a)
        raw = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        m = raw.get("metrics", raw)
        design = json.loads((run_dir / "design.resolved.json").read_text(encoding="utf-8"))
        d = np.load(run_dir / "eo.npz")

        lam = float(m["eo"]["wavelength_um"])
        plat = design["platform"]
        lib = MaterialLibrary(_materials_path(plat.get("materials_file")))

        n_e, ng_film = group_index(lib, plat["film_material"], lam, "e",
                                   plat.get("cut", "x"))
        n_c, ng_clad = group_index(lib, plat.get("clad_material", "SiO2"), lam,
                                   "o", plat.get("cut", "x"))

        ox, oy = d["x_um"], d["y_um"]
        dA = np.outer(np.gradient(ox), np.gradient(oy))
        inten = d["intensity"]
        film = d["mask_film"]

        total = float(np.sum(inten * dA))
        in_film = float(np.sum(inten * film * dA))
        f = in_film / total

        # n n_g,mat weighted by intensity, film against everything else
        denom = f * n_e * ng_film + (1.0 - f) * n_c * ng_clad
        n_g_mode = float(m["eo"]["n_g_used"])
        ratio = n_g_mode * n_e / denom

        gamma = float(m["eo"]["eo_overlap_gamma"])
        arm = float(m["eo"]["VpiL_V_cm"])
        dev = float((m.get("modulator") or {}).get("VpiL_device_V_cm", arm / 2))

        print(f"{run_dir.name}")
        print(f"  wavelength {lam:.3f} um, film {plat['film_material']}, "
              f"cladding {plat.get('clad_material', 'SiO2')}")
        print(f"  film   n {n_e:.5f}, material group index {ng_film:.5f}, "
              f"product {n_e * ng_film:.5f}")
        print(f"  clad   n {n_c:.5f}, material group index {ng_clad:.5f}, "
              f"product {n_c * ng_clad:.5f}")
        print(f"  the mode puts {100 * f:.2f} per cent of its intensity in the film")
        print(f"  intensity-weighted <n n_g,mat> = {denom:.5f}")
        print(f"  n_g of the mode {n_g_mode:.5f}, times n_e = {n_g_mode * n_e:.5f}")
        print(f"  ratio of the two normalisations = {ratio:.5f}")
        print(f"  the stage reports Gamma {gamma:.5f}; energy-normalised it is "
              f"{gamma * ratio:.5f}")
        print(f"  V_pi.L per arm {arm:.4f} -> {arm / ratio:.4f} V.cm")
        print(f"  V_pi.L of the device {dev:.4f} -> {dev / ratio:.4f} V.cm")
        print()
    return 0


def _materials_path(declared: str | None) -> Path | None:
    if not declared:
        return None
    p = Path(declared)
    for cand in (p, ROOT / p, Path.cwd() / p):
        if cand.exists():
            return cand
    raise FileNotFoundError(declared)


if __name__ == "__main__":
    raise SystemExit(main())
