"""Selection of the layout a geometric stage is evaluated against."""

from __future__ import annotations


def resolve_target(design, ctx, stage: str) -> tuple[str, str]:
    """Which emitted layout the stage is to be evaluated against.

    "device" is the cell the layout stage wrote. "die" is the assembled reticle,
    which is the object actually submitted. A frame that is drawn and never
    checked is a frame that is assumed, so the second is available wherever the
    reticle stage has run.
    """
    cfg = getattr(design, stage)
    want = getattr(cfg, "target", "device")
    if want == "die":
        ret = ctx.get("reticle") or {}
        if not ret.get("enabled") or not ret.get("gds"):
            raise RuntimeError(
                f"stage {stage!r} is set to check the die, but no die was assembled. "
                "Two things are required and both are easy to supply only one of: "
                "`reticle` must appear in the design's `stages:` list, and "
                "`reticle.enabled` must be true. Alternatively set "
                f"{stage}.target back to 'device'"
            )
        return str(ret["gds"]), "die"
    lay = ctx.get("layout") or {}
    if not lay.get("gds"):
        raise RuntimeError(f"stage {stage!r} requires stage 'layout'")
    return str(lay["gds"]), "device"
