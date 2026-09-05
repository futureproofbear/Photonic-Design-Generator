"""The edge-coupler transition, by local-mode propagation, on the drawn polygons.

The facet study measured what a fibre collects from the tip. This measures what
happens over the 160 um behind it, where the mode is handed from a bare strip of
the slab film to a ridge on a wide slab.

The structure varies slowly by construction, which is what an inverse taper is
for, so the local-mode path applies: the modes of each station are projected
onto the next and reflection is neglected. That path is well conditioned, which
full mode matching on a truncated basis is not, and it reports three quantities.
The conversion into higher-order modes is the physical loss channel within this
basis. The staircase deficit is the power that fails to project between adjacent
stations, which falls as the station count rises and is a measure of the
discretisation rather than of radiation. The effective index at each station
shows where the hand-over happens.

Where the profile comes from
----------------------------
Every width is cut out of the emitted GDS, which is chain rule 11 applied to a
vendor kit. The first version of this script reimplemented the kit's profile
function from its parameters, and the reimplementation was wrong: it placed the
break between the linear and the exponential branch at a quarter of the length
for both cells, where the C-band cell places it at a half, and it interpolated
the exponential branch between the break width and 5.6 um where the kit grows it
from a fixed offset of 0.418 um and clips it at 5.6. The drawn O-band slab is
1.500 um wide where the ridge begins and the reimplementation said 1.093, and
the drawn slab reaches its full width at 105 um and holds it, where the
reimplementation was still tapering at 160.

    python examples/ltoi300_edge_coupler/scripts/transition.py [oband|cband] [modes] [refine]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "design-chain" / "src"))
sys.path.insert(0, str(ROOT / "design-chain" / "tools"))
sys.path.insert(0, str(ROOT / "design-chain" / "pdk" / "lxt_pdk_gf"))

from measure_layout import cut                            # noqa: E402
from picchain import eme                                  # noqa: E402
from picchain.materials import MaterialLibrary            # noqa: E402
from picchain.mmi_eme import cross_section_eps            # noqa: E402
from picchain.solvers.fdmode import solve_modes           # noqa: E402

MATERIALS = ROOT / "design-chain" / "pdk" / "LXT_LT_PRO" / "materials_lt_pro.yaml"
GDS_DIR = Path(__file__).resolve().parents[1] / "runs" / "gds"

#: LT_RIDGE and LT_SLAB of the kit's layer map
RIDGE_LAYER, SLAB_LAYER = (2, 10), (3, 10)

CELLS = {
    "oband": dict(cell="edge_coupler_oband", lam=1.31),
    "cband": dict(cell="edge_coupler_cband", lam=1.55),
}
TOTAL_UM, UPPER_UM = 160.0, 80.0
STACK = dict(film_um=0.300, etch_um=0.180, sidewall_deg=70.0)


def emit(cell: str) -> Path:
    """Write the kit's cell and return the file, building it once per session."""
    path = GDS_DIR / f"{cell}.gds"
    if path.exists():
        return path
    import ltoi300
    from ltoi300 import cells

    ltoi300.PDK.activate()
    GDS_DIR.mkdir(parents=True, exist_ok=True)
    getattr(cells, cell)().write_gds(str(path))
    return path


def widths(gds: Path, z: float) -> tuple[float, float]:
    """The slab strip and the ridge at one station, measured off the file.

    The taper tip sits at z = 0 and the facet extension runs to negative z, so a
    station is offset by the left edge of the ridge layer minus the taper length.
    Both layers are centred on y = 0, which the study checks separately.
    """
    slab = cut(str(gds), *SLAB_LAYER, "x", z)
    ridge = cut(str(gds), *RIDGE_LAYER, "x", z)
    w_s = max((hi - lo for lo, hi in slab), default=0.0)
    w_r = max((hi - lo for lo, hi in ridge), default=0.0)
    return w_s, w_r


def graded(half_fine, d_fine, half_total, d_coarse):
    fine = np.arange(0.0, half_fine + d_fine / 2, d_fine)
    coarse = np.arange(half_fine + d_coarse, half_total + d_coarse / 2, d_coarse)
    half = np.concatenate([fine, coarse])
    return np.concatenate([-half[:0:-1], half])


def main(argv: list[str]) -> int:
    key = argv[1] if len(argv) > 1 else "oband"
    c = CELLS[key]
    lam = c["lam"]
    gds = emit(c["cell"])

    lib = MaterialLibrary(MATERIALS) if MATERIALS.exists() else MaterialLibrary()
    stack = dict(STACK, n_film=float(lib["LiTaO3"].index(lam, "e")),
                 n_clad=float(lib["SiO2"].index(lam)))

    x = graded(3.5, 0.025, 8.0, 0.15)
    y = np.concatenate([np.arange(-4.0, -0.2, 0.12), np.arange(-0.2, 0.501, 0.010),
                        np.arange(0.51, 4.01, 0.12)])
    dA = np.outer(np.gradient(x), np.gradient(y))
    n_modes = int(argv[2]) if len(argv) > 2 else 3

    #: stations, concentrated where the ridge appears and where the slab is
    #: still growing. The drawn slab reaches 5.6 um at about 105 um and holds
    #: it, so the last stretch is uniform and needs two stations rather than ten.
    #: ``refine`` multiplies every count, which is how the staircase deficit is
    #: shown to be a property of the cell rather than of the sampling
    refine = int(argv[3]) if len(argv) > 3 else 1
    zs = np.concatenate([np.linspace(0.0, UPPER_UM, 7 * refine, endpoint=False),
                         np.linspace(UPPER_UM, 110.0, 12 * refine),
                         np.linspace(110.0, TOTAL_UM - 1e-3, 3 * refine + 1)[1:]])
    print(f"{key}: {c['cell']}, {len(zs)} stations from the drawn polygons, "
          f"{len(x)} by {len(y)} grid, {n_modes} modes each")

    n_effs, fields, lengths = [], [], []
    print(f"\n{'z (um)':>8} {'slab (um)':>10} {'ridge (um)':>11} {'n_eff':>9}")
    for k, z in enumerate(zs):
        w_s, w_r = widths(gds, float(z))
        h_r = STACK["etch_um"] if w_r > 0 else 0.0
        eps = cross_section_eps(x, y, [0.0], max(w_r, 1e-3),
                                dict(stack, slab_width_um=w_s, ridge_height_um=h_r))
        modes = solve_modes(x, y, eps, eps, lam, "TE", n_modes, None)
        if not modes:
            raise RuntimeError(f"no mode at z = {z:.1f} um")
        n_effs.append(np.array([m.n_eff for m in modes], dtype=float))
        fields.append(np.array([m.field for m in modes], dtype=float))
        lengths.append(float(zs[k + 1] - z) if k + 1 < len(zs) else 0.0)
        print(f"{z:8.1f} {w_s:10.3f} {w_r:11.3f} {modes[0].n_eff:9.5f}")

    r = eme.local_mode_chain(fields, dA, n_effs, lengths, lam)
    print(f"\n  transmission into the fundamental   {r['transmission_fundamental']:.5f}")
    print(f"  power retained in the guided set    {r['transmission_guided']:.5f}")
    print(f"  conversion into higher-order modes  {r['conversion_to_higher_order']:.3e}")
    print(f"  conversion loss                     {r['conversion_loss_dB']:.4f} dB")
    print(f"  staircase deficit                   {r['staircase_deficit']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
