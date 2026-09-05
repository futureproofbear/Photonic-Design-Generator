"""Every geometric figure the design files declare, measured back off the cell.

A quantity written in a design file is an assertion about the mask until a
polygon is measured. The modulator designs in this folder declare an electrode
gap, a central-conductor width, a ground width, an arm separation and a
modulation-section guide width, each read from the PDK source. This builds the
cell, cuts it transversely through the modulation section, and measures all
five off the polygons. It also reports the one feature the source alone does
not make obvious: the electrode is periodically loaded with T-rails, so the gap
the light sees is not one number.

Run it from the vendored PDK directory, so that the `ltoi300` package beside it
is imported in preference to any copy installed in `site-packages`:

    cd design-chain/pdk/lxt_pdk_gf
    python <this file>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def polygons(component, layer) -> list[np.ndarray]:
    """Every polygon on one layer, as arrays of edge endpoints in micrometres.

    Each entry is an (n, 4) array of x0, y0, x1, y1 covering the outer contour
    of one polygon and every hole in it. The holes matter here: the two arms of
    the interferometer and the loop that joins them are one polygon with a hole
    between them, so a cut taking the outer contour alone reports the pair as
    one 28 um strip. Sorting the crossings of hull and holes together and
    pairing them is the even-odd rule, which gives the two arms.
    """
    import gdsfactory as gf
    index = gf.kcl.layout.layer(*gf.get_layer_tuple(layer))
    out = []
    for poly in component.get_polygons(merge=False).get(index, []):
        contours = [list(poly.each_point_hull())]
        for h in range(poly.holes()):
            contours.append(list(poly.each_point_hole(h)))
        edges = []
        for pts in contours:
            a = np.array([(q.x / 1000.0, q.y / 1000.0) for q in pts])
            if len(a) >= 3:
                edges.append(np.hstack([a, np.roll(a, -1, axis=0)]))
        if edges:
            out.append(np.vstack(edges))
    return out


def cut(polys: list[np.ndarray], x: float) -> list[tuple[float, float]]:
    """The y intervals the layer occupies on the vertical line at x.

    Each polygon is crossed on its own, its own crossings paired, and the
    resulting intervals then unioned, so that two shapes drawn over one another
    report the material once rather than interleaving their crossings into a
    false pairing.
    """
    spans: list[tuple[float, float]] = []
    for e in polys:
        x0, y0, x1, y1 = e[:, 0], e[:, 1], e[:, 2], e[:, 3]
        dx = x1 - x0
        ok = (np.abs(dx) > 1e-12) & (((x0 - x) * (x1 - x)) < 0)
        if not ok.any():
            continue
        tt = (x - x0[ok]) / dx[ok]
        ys = sorted((y0[ok] + tt * (y1[ok] - y0[ok])).tolist())
        spans += [(a, b) for a, b in zip(ys[0::2], ys[1::2]) if b - a > 1e-6]
    out: list[tuple[float, float]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + 1e-6:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def main() -> int:
    sys.path.insert(0, str(Path.cwd()))
    import gdsfactory as gf  # noqa: E402
    from ltoi300.cells import terminated_mzm_1x2mmi_oband  # noqa: E402
    from ltoi300.tech import LAYER  # noqa: E402

    c = terminated_mzm_1x2mmi_oband().copy()
    c.flatten()
    print(f"cell {c.name}, bounding box {c.dxsize:.1f} by {c.dysize:.1f} um")

    m1 = polygons(c, gf.get_layer_tuple(LAYER.M1))
    ridge = polygons(c, gf.get_layer_tuple(LAYER.LT_RIDGE))
    slab = polygons(c, gf.get_layer_tuple(LAYER.LT_SLAB))
    print(f"polygons: M1 {len(m1)}, ridge {len(ridge)}, slab {len(slab)}")

    x_mid = 0.5 * (c.dxmin + c.dxmax)

    # one T-rail period, sampled finely, keeping only cuts that meet three
    # conductors, which is the coplanar section rather than a pad or a taper
    period = 58.0
    samples = []
    for dx in np.linspace(0.0, period, 233):
        s = cut(m1, x_mid + dx)
        if len(s) == 3:
            samples.append((dx, s[1][0] - s[0][1], s[1][1] - s[1][0],
                            s[0][1] - s[0][0]))
    if not samples:
        print("no three-conductor cut was found; the sample window missed the line")
        return 1

    gaps = np.array([s[1] for s in samples])
    sig = np.array([s[2] for s in samples])
    gnd = np.array([s[3] for s in samples])
    narrow, wide = float(gaps.min()), float(gaps.max())
    i_n, i_w = int(gaps.argmin()), int(gaps.argmax())
    print(f"  at the T-rail:      gap {narrow:6.3f} um, signal {sig[i_n]:6.3f} um, "
          f"ground {gnd[i_n]:6.3f} um")
    print(f"  between T-rails:    gap {wide:6.3f} um, signal {sig[i_w]:6.3f} um, "
          f"ground {gnd[i_w]:6.3f} um")
    duty = float(np.mean(gaps < 0.5 * (narrow + wide)))
    print(f"  the narrow gap occupies {100 * duty:.1f} per cent of the "
          f"{period:.0f} um period")

    r = cut(ridge, x_mid)
    s = cut(slab, x_mid)
    print("  ridge on the cut:   " +
          ", ".join(f"[{a:.3f}, {b:.3f}] width {b - a:.3f}" for a, b in r))
    if len(r) == 2:
        c1 = 0.5 * (r[0][0] + r[0][1])
        c2 = 0.5 * (r[1][0] + r[1][1])
        sep = abs(c2 - c1)
        print(f"  arm separation {sep:.3f} um, each arm {sep / 2:.3f} um "
              "off the signal axis")
    print("  slab on the cut:    " +
          ", ".join(f"[{a:.3f}, {b:.3f}] width {b - a:.3f}" for a, b in s))
    if len(r) == 2 and len(s) == 2:
        off = 0.5 * ((s[0][1] - s[0][0]) - (r[0][1] - r[0][0]))
        print(f"  the slab reaches {off:.3f} um beyond each ridge edge")

    eff = duty / narrow + (1.0 - duty) / wide
    print(f"\n  a cross-section carrying only the narrow gap overstates the "
          f"mean field by {100 * (1 / narrow / eff - 1):.1f} per cent. That is "
          "an upper bound on the penalty: the widened stretch is shorter than "
          "the gap itself, so the field there does not relax to its "
          "two-dimensional value")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
