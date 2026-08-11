"""The difference between the dimension drawn and the dimension printed.

Every dimension in a design file states an intent. Three distinct quantities
follow from it, and a chain that conflates them cannot be used to order a mask.

``nominal``
    the dimension the designer intends to exist in silicon.
``drawn``
    the dimension placed on the mask. This is what a foundry receives and what
    a rule deck is evaluated against.
``printed``
    the dimension that exists in silicon after lithography and etch. This is
    what the light sees, and it is therefore what the physics is to be solved
    on.

The three coincide only for a process of zero bias. Real processes print wide
or narrow by tens of nanometres, and on a side-coupled grating that is not a
detail. A measured decay of d(ln Δn_eff)/d(gap) = −5.4 µm⁻¹ makes a 20 nm error
an 11 % error in the coupling constant.

The convention
--------------
``bias_um`` is stated per layer as the change in a feature **width**, positive
where the printed feature is wider than the drawn one. Each edge on that layer
therefore advances outward by half the bias. Two consequences follow and both
are handled here:

* a width grows by the full bias;
* a **gap between two features on the same layer shrinks by the full bias**,
  each of the two facing edges having advanced into it.

The second is the one that is missed by hand. A process that prints 40 nm wide
closes a 630 nm post gap to 590 nm, and the grating is stronger than drawn for
two reasons rather than one.

Pre-compensation
----------------
Where ``precompensate`` is set, every edge is drawn inward by half the bias, so
that the printed dimension lands on the nominal one. This is the operation that
makes a mask orderable against a characterised process. It is applied to the
drawing alone. A vertical bias on the etch depth cannot be pre-compensated by
drawing, and is applied to the printed geometry only.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal


@dataclass(frozen=True)
class Geometry:
    """One consistent set of lateral dimensions, in micrometres."""

    frame: Literal["nominal", "drawn", "printed"]
    wg_top_width_um: float
    post_width_um: float
    post_length_um: float
    post_gap_um: float
    etch_depth_um: float
    electrode_gap_um: float
    electrode_width_um: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _shift(value: float, delta: float, kind: str, name: str) -> float:
    """Apply an edge displacement to a width or to a gap.

    A width gains the full bias; a gap loses it. A dimension driven negative is
    refused rather than clipped, a mask on which a feature has closed being a
    different design from the one requested.
    """
    out = value + delta if kind == "width" else value - delta
    if out <= 0.0:
        raise ValueError(
            f"{name} resolves to {out:.4f} um under a bias of {delta:+.4f} um. "
            f"The feature closes; the bias exceeds what this geometry tolerates"
        )
    return out


def resolve(
    *,
    frame: Literal["nominal", "drawn", "printed"],
    wg_top_width_um: float,
    post_width_um: float,
    post_length_um: float,
    post_gap_um: float,
    etch_depth_um: float,
    electrode_gap_um: float,
    electrode_width_um: float,
    bias_um: dict[str, float] | None = None,
    depth_bias_um: float = 0.0,
    precompensate: bool = True,
    wg_layer: str = "WG",
    metal_layer: str = "METAL",
) -> Geometry:
    """Return the nominal dimensions expressed in the requested frame.

    The arguments are the nominal dimensions, being those written in the design
    file. ``frame`` selects which of the three sets is returned.
    """
    bias = dict(bias_um or {})
    bw = float(bias.get(wg_layer, 0.0))
    bm = float(bias.get(metal_layer, 0.0))

    if frame == "nominal":
        dw = dm = 0.0
        dd = 0.0
    elif frame == "drawn":
        # pre-compensation moves each edge inward by half the bias, so the
        # printed feature lands on the nominal one. Without it the mask carries
        # the nominal dimension and the printed one is displaced.
        dw, dm = (-bw, -bm) if precompensate else (0.0, 0.0)
        dd = 0.0
    elif frame == "printed":
        # with pre-compensation the drawing already absorbed the bias
        dw, dm = (0.0, 0.0) if precompensate else (bw, bm)
        dd = float(depth_bias_um)
    else:
        raise ValueError(f"unknown frame {frame!r}")

    return Geometry(
        frame=frame,
        wg_top_width_um=_shift(wg_top_width_um, dw, "width", "waveguide top width"),
        post_width_um=_shift(post_width_um, dw, "width", "Bragg post width"),
        post_length_um=_shift(post_length_um, dw, "width", "Bragg post length"),
        post_gap_um=_shift(post_gap_um, dw, "gap", "Bragg post gap"),
        etch_depth_um=_shift(etch_depth_um, dd, "width", "etch depth"),
        electrode_gap_um=_shift(electrode_gap_um, dm, "gap", "electrode gap"),
        electrode_width_um=_shift(electrode_width_um, dm, "width", "electrode width"),
    )


def geometry(design, frame: Literal["nominal", "drawn", "printed"]) -> Geometry:
    """Resolve a ``Design`` into one frame."""
    p, w, g, e, pr = (
        design.platform, design.waveguide, design.grating, design.electrodes, design.process,
    )
    return resolve(
        frame=frame,
        wg_top_width_um=w.top_width_um,
        post_width_um=g.post_width_um,
        post_length_um=g.post_length_um or g.post_width_um,
        post_gap_um=g.post_gap_um,
        etch_depth_um=p.etch_depth_um,
        electrode_gap_um=e.gap_um,
        electrode_width_um=e.width_um,
        bias_um=pr.bias_um,
        depth_bias_um=pr.depth_bias_um,
        precompensate=pr.precompensate,
        wg_layer=pr.wg_layer,
        metal_layer=pr.metal_layer,
    )


def is_identity(design) -> bool:
    """Whether the three frames coincide, the process carrying no bias."""
    pr = design.process
    return not any(abs(float(v)) > 0.0 for v in pr.bias_um.values()) and \
        abs(float(pr.depth_bias_um)) == 0.0


def summary(design) -> dict[str, Any]:
    """The three frames side by side, for the metric tree.

    Reported on every run so that a reader can see at a glance whether the mask
    and the simulation describe the same object.
    """
    frames = {f: geometry(design, f).as_dict() for f in ("nominal", "drawn", "printed")}
    for f in frames.values():
        f.pop("frame", None)
    pr = design.process
    return {
        "bias_um": dict(pr.bias_um),
        "depth_bias_um": float(pr.depth_bias_um),
        "precompensate": bool(pr.precompensate),
        "identity": is_identity(design),
        "nominal": frames["nominal"],
        "drawn": frames["drawn"],
        "printed": frames["printed"],
    }
