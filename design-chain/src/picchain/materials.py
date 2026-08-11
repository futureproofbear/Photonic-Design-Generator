"""Material database access for the photonic-radar design chain.

Loads ``pdk/materials.yaml`` and exposes dispersive refractive indices, the
electro-optic tensor and the RF permittivity tensor in the *device* frame.

Crystal-frame -> device-frame mapping
-------------------------------------
For an X-cut film with the optical waveguide running along the crystal Y axis
(the geometry used in arXiv:2408.01743):

    device x (in-plane, transverse)  ->  crystal Z  (the c axis)
    device y (out-of-plane)          ->  crystal X
    device z (propagation)           ->  crystal Y

so a quasi-TE mode (dominant E_x) sees the *extraordinary* index and is
modulated through r33 by an in-plane E-field, which is exactly why the
electrodes sit either side of the ridge.  Z-cut would map differently; the
``cut`` field selects the mapping.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PDK_DIR = Path(__file__).resolve().parents[2] / "pdk"
DEFAULT_MATERIALS = PDK_DIR / "materials.yaml"


# --------------------------------------------------------------------------
# dispersion models
# --------------------------------------------------------------------------
def _sellmeier_1(lam_um: float, B, C) -> float:
    """n^2 = 1 + sum B_i lam^2 / (lam^2 - C_i)   with C_i already squared."""
    l2 = lam_um**2
    n2 = 1.0
    for b, c in zip(B, C):
        n2 += b * l2 / (l2 - c**2)
    return math.sqrt(n2)


def _sellmeier_zelmon(lam_um: float, p: dict) -> float:
    """n^2 = 1 + A l^2/(l^2-B) + C l^2/(l^2-D) + E l^2/(l^2-F)."""
    l2 = lam_um**2
    n2 = (
        1.0
        + p["A"] * l2 / (l2 - p["B"])
        + p["C"] * l2 / (l2 - p["D"])
        + p["E"] * l2 / (l2 - p["F"])
    )
    return math.sqrt(n2)


@dataclass(frozen=True)
class Material:
    name: str
    spec: dict[str, Any]

    # ---------------- optical ----------------
    @property
    def kind(self) -> str:
        return self.spec.get("kind", "isotropic")

    @property
    def is_uniaxial(self) -> bool:
        return self.kind == "uniaxial"

    def index(self, lam_um: float, axis: str = "o", use_override: bool = False) -> float:
        """Refractive index. ``axis`` is 'o' or 'e' for uniaxial materials."""
        spec = self.spec
        if use_override and "index_override_1550" in spec:
            ov = spec["index_override_1550"]
            return float(ov[axis] if isinstance(ov, dict) else ov)
        if "index_const" in spec:
            return float(spec["index_const"])
        sm = spec.get("sellmeier")
        if sm is None:
            raise KeyError(f"material {self.name!r} has no optical index model")
        form = sm["form"]
        if form == "sellmeier_1":
            return _sellmeier_1(lam_um, sm["B"], sm["C"])
        if form in ("sellmeier_zelmon_ln", "sellmeier_zelmon_lt"):
            return _sellmeier_zelmon(lam_um, sm[axis])
        raise ValueError(f"unknown sellmeier form {form!r}")

    def eps_optical_device(
        self, lam_um: float, cut: str = "x", use_override: bool = False
    ) -> tuple[float, float, float]:
        """Diagonal optical permittivity (eps_xx, eps_yy, eps_zz) in device frame."""
        if not self.is_uniaxial:
            n = self.index(lam_um, use_override=use_override)
            return (n * n,) * 3
        no = self.index(lam_um, "o", use_override)
        ne = self.index(lam_um, "e", use_override)
        if cut == "x":  # device x || crystal c
            return (ne**2, no**2, no**2)
        if cut == "z":  # device y (out of plane) || crystal c
            return (no**2, ne**2, no**2)
        raise ValueError(f"unsupported cut {cut!r} (use 'x' or 'z')")

    def eps_rf_device(self, cut: str = "x") -> tuple[float, float, float]:
        """Diagonal RF/DC permittivity in device frame."""
        e = self.spec.get("eps_rf")
        if e is None:
            return (1.0, 1.0, 1.0)
        if not isinstance(e, dict):
            return (float(e),) * 3
        perp, along = float(e["perp_c"]), float(e["along_c"])
        if cut == "x":
            return (along, perp, perp)
        if cut == "z":
            return (perp, along, perp)
        raise ValueError(f"unsupported cut {cut!r}")

    # ---------------- electro-optic ----------------
    def r_pm_per_V(self, coeff: str = "r33") -> float:
        eo = self.spec.get("eo_tensor")
        if eo is None:
            return 0.0
        return float(eo.get(coeff, 0.0))

    @property
    def loss_dB_per_cm(self) -> float:
        return float(self.spec.get("loss_dB_per_cm", 0.0))

    @property
    def provenance(self) -> str:
        return str(self.spec.get("provenance", "unspecified"))

    @property
    def needs_confirmation(self) -> bool:
        return self.provenance.lower().startswith("needs_confirmation")


class MaterialLibrary:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or DEFAULT_MATERIALS)
        with open(self.path, "r", encoding="utf-8") as fh:
            self._data = yaml.safe_load(fh)["materials"]

    def __contains__(self, name: str) -> bool:
        return name in self._data

    def __getitem__(self, name: str) -> Material:
        if name not in self._data:
            raise KeyError(
                f"material {name!r} not in {self.path.name}; available: "
                + ", ".join(sorted(self._data))
            )
        return Material(name, self._data[name])

    def names(self) -> list[str]:
        return sorted(self._data)

    def unconfirmed(self, used: list[str]) -> list[str]:
        return [n for n in used if n in self._data and self[n].needs_confirmation]


@functools.lru_cache(maxsize=8)
def load_library(path: str | None = None) -> MaterialLibrary:
    return MaterialLibrary(path)


def group_index_from_dispersion(
    mat: Material, lam_um: float, axis: str = "e", dlam: float = 0.005
) -> float:
    """Material group index n_g = n - lam dn/dlam (finite difference)."""
    n0 = mat.index(lam_um, axis)
    np_ = mat.index(lam_um + dlam, axis)
    nm = mat.index(lam_um - dlam, axis)
    return n0 - lam_um * (np_ - nm) / (2 * dlam)
