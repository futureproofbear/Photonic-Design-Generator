"""Cross-section construction and rasterisation.

A cross-section is an ordered list of `Shape`s (later shapes paint over
earlier ones) plus a background material.  It is rasterised onto a
piecewise-uniform (graded) tensor-product grid with sub-pixel material
averaging, which is what makes the ~5e-4 effective-index *differences* the
grating stage needs numerically trustworthy: both the perturbed and the
unperturbed cross-section are solved on the identical mesh, so the systematic
discretisation error largely cancels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import math

import numpy as np


# --------------------------------------------------------------------------
# shapes
# --------------------------------------------------------------------------
@dataclass
class Shape:
    material: str
    #: polygon vertices [(x, y), ...] in um, closed implicitly
    points: list[tuple[float, float]]
    name: str = ""

    @staticmethod
    def rect(material: str, x0: float, x1: float, y0: float, y1: float, name: str = "") -> "Shape":
        return Shape(material, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], name)

    @staticmethod
    def trapezoid(
        material: str,
        x_center: float,
        top_width: float,
        height: float,
        y_base: float,
        sidewall_deg: float = 90.0,
        name: str = "",
    ) -> "Shape":
        """Ridge with sloped sidewalls.  ``sidewall_deg`` = 90 gives a rectangle;
        a typical ion-beam-etched LN ridge is 60-75 deg."""
        overhang = height / np.tan(np.deg2rad(sidewall_deg)) if sidewall_deg < 89.999 else 0.0
        bw = top_width + 2 * overhang
        return Shape(
            material,
            [
                (x_center - bw / 2, y_base),
                (x_center + bw / 2, y_base),
                (x_center + top_width / 2, y_base + height),
                (x_center - top_width / 2, y_base + height),
            ],
            name,
        )

    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), max(xs), min(ys), max(ys)

    def x_edges(self) -> list[float]:
        return sorted({p[0] for p in self.points})

    def y_edges(self) -> list[float]:
        return sorted({p[1] for p in self.points})


@dataclass
class CrossSection:
    background: str
    shapes: list[Shape] = field(default_factory=list)
    #: simulation window (xmin, xmax, ymin, ymax) in um
    window: tuple[float, float, float, float] = (-4.0, 4.0, -2.0, 2.0)
    name: str = ""

    def add(self, shape: Shape) -> "CrossSection":
        self.shapes.append(shape)
        return self

    def materials_used(self) -> list[str]:
        return sorted({self.background} | {s.material for s in self.shapes})

    def critical_x(self) -> list[float]:
        out: list[float] = []
        for s in self.shapes:
            out.extend(s.x_edges())
        return sorted(set(out))

    def critical_y(self) -> list[float]:
        out: list[float] = []
        for s in self.shapes:
            out.extend(s.y_edges())
        return sorted(set(out))


# --------------------------------------------------------------------------
# graded axes
# --------------------------------------------------------------------------
def graded_axis(
    lo: float,
    hi: float,
    features: list[float],
    d_fine: float,
    d_coarse: float,
    fine_margin: float = 0.4,
) -> np.ndarray:
    """Piecewise-uniform axis with every feature coordinate on a node.

    The feature coordinates are breakpoints of the mesh, so each is a node
    exactly and each interval between consecutive breakpoints is uniform. An
    interval within ``fine_margin`` of a feature is meshed at ``d_fine`` and the
    rest at ``d_coarse``.

    The earlier form laid a uniform axis and then moved the nearest node onto
    each feature. That displaces the two cells either side of every interface by
    an amount depending on where the uniform mesh happened to fall, so the
    discretisation error moves with the mesh instead of falling with it. On a
    thin-film stack the effect was large: refining the electrostatic mesh in
    four steps moved the microwave index non-monotonically and the bandwidth
    between 19.6 and 31.3 GHz, and two `must` rows failed at one refinement and
    passed at the next. Inserting the breakpoints instead makes refinement
    monotone, because every interface stays put and only the cell count grows.
    """
    # Two breakpoints a floating-point epsilon apart leave a cell of zero
    # width, and `np.unique` keeps both because they differ in the last bit.
    # The energy integral over such a mesh diverges: one electrode thickness in
    # a sweep returned a capacitance of 6.7e26 pF/cm and an impedance of
    # 1.7e-12 ohm, between two neighbouring thicknesses that were both sound.
    # A margin edge landing on a feature is the way it arises, `f - margin`
    # rarely being bit-identical to the feature it lands on.
    tol = max(1e-9, 1e-12 * abs(hi - lo))

    def _merge(values: list[float]) -> list[float]:
        out: list[float] = []
        for v in sorted(values):
            if not out or v - out[-1] > tol:
                out.append(v)
        return out

    feats = _merge([float(f) for f in features if lo + tol < f < hi - tol])
    if not feats:
        n = max(1, int(math.ceil((hi - lo) / d_coarse - 1e-9)))
        return np.linspace(lo, hi, n + 1)

    marks = [float(lo), float(hi)]
    for f in feats:
        marks.append(f)
        marks.append(max(lo, f - fine_margin))
        marks.append(min(hi, f + fine_margin))
    edges = _merge(marks)

    parts: list[np.ndarray] = []
    for a, b in zip(edges, edges[1:]):
        if b - a <= tol:
            continue
        mid = 0.5 * (a + b)
        near = any(abs(mid - f) <= fine_margin + tol for f in feats)
        d = d_fine if near else d_coarse
        n = max(1, int(math.ceil((b - a) / d - 1e-9)))
        parts.append(np.linspace(a, b, n + 1))
    axis = np.concatenate(parts)
    keep = np.concatenate(([True], np.diff(axis) > tol))
    return axis[keep]

def _point_in_poly(px: np.ndarray, py: np.ndarray, poly: list[tuple[float, float]]) -> np.ndarray:
    """Vectorised even-odd point-in-polygon test."""
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cond = (y0 > py) != (y1 > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x1 - x0) * (py - y0) / (y1 - y0) + x0
        inside ^= cond & (px < xint)
    return inside


@dataclass
class RasterGrid:
    x: np.ndarray  # node coordinates, um  (nx,)
    y: np.ndarray  # node coordinates, um  (ny,)

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.x), len(self.y)

    def cell_areas(self) -> np.ndarray:
        dx = np.gradient(self.x)
        dy = np.gradient(self.y)
        return np.outer(dx, dy)


def build_grid(
    xs: CrossSection, d_fine: float, d_coarse: float, fine_margin: float = 0.4
) -> RasterGrid:
    x0, x1, y0, y1 = xs.window
    return RasterGrid(
        graded_axis(x0, x1, xs.critical_x(), d_fine, d_coarse, fine_margin),
        graded_axis(y0, y1, xs.critical_y(), d_fine, d_coarse, fine_margin),
    )


def rasterise(
    xs: CrossSection,
    grid: RasterGrid,
    value_of: dict[str, float],
    subsample: int = 3,
) -> np.ndarray:
    """Return a (nx, ny) array of material values with sub-pixel averaging.

    ``value_of`` maps material name -> scalar (e.g. eps_xx).  Each node is
    represented by its Voronoi cell, sampled on a ``subsample`` x ``subsample``
    lattice; the returned value is the arithmetic mean over those samples.
    """
    x, y = grid.x, grid.y
    nx, ny = len(x), len(y)
    hx = np.gradient(x)
    hy = np.gradient(y)

    # sub-sample offsets in [-0.5, 0.5]
    if subsample <= 1:
        offs = np.array([0.0])
    else:
        offs = (np.arange(subsample) + 0.5) / subsample - 0.5

    acc = np.zeros((nx, ny))
    for ox in offs:
        for oy in offs:
            px = (x + ox * hx)[:, None] * np.ones((1, ny))
            py = np.ones((nx, 1)) * (y + oy * hy)[None, :]
            vals = np.full((nx, ny), value_of[xs.background], dtype=float)
            for s in xs.shapes:
                mask = _point_in_poly(px, py, s.points)
                vals[mask] = value_of[s.material]
            acc += vals
    return acc / (len(offs) ** 2)


def material_mask(xs: CrossSection, grid: RasterGrid, material: str, subsample: int = 3) -> np.ndarray:
    """Fractional occupancy (0..1) of ``material`` per node cell."""
    vals = {m: 0.0 for m in xs.materials_used()}
    vals[material] = 1.0
    return rasterise(xs, grid, vals, subsample=subsample)


# --------------------------------------------------------------------------
# E-DBR specific cross-sections
# --------------------------------------------------------------------------
def edbr_cross_section(
    *,
    film_material: str,
    film_thickness_um: float,
    etch_depth_um: float,
    wg_top_width_um: float,
    sidewall_deg: float = 90.0,
    box_thickness_um: float = 4.7,
    clad_thickness_um: float = 2.0,
    clad_material: str = "SiO2",
    box_material: str = "SiO2",
    substrate_material: str = "Si",
    with_posts: bool = False,
    post_width_um: float = 0.30,
    post_gap_um: float = 0.63,
    electrodes: bool = False,
    electrode_gap_um: float = 7.0,
    electrode_width_um: float = 20.0,
    electrode_thickness_um: float = 0.9,
    electrode_material: str = "Au",
    #: "slot" places two conductors either side of one guide, which is the
    #: mirror of a distributed-reflector laser. "gsg" places a signal conductor
    #: between two grounds with a guide centred in EACH gap, which is the
    #: coplanar line of a push-pull interferometer. The two differ in the
    #: capacitance, the impedance and the conductor loss, and a device drawn as
    #: one and solved as the other reports the line it does not have.
    electrode_topology: str = "slot",
    #: ground conductor width for "gsg"; defaults to the signal width
    ground_width_um: float | None = None,
    #: how far the unetched slab reaches either side of a guide. Left unset the
    #: slab is a blanket across the whole cross-section
    slab_offset_um: float | None = None,
    window_pad_x_um: float = 3.0,
    window_pad_y_um: float = 0.0,
    include_substrate: bool = True,
    box_model_depth_um: float = 1.8,
    name: str = "",
) -> CrossSection:
    """Shallow-etched ridge on a thin film, optionally with Bragg posts
    either side and coplanar electrodes.

    Coordinate convention: y = 0 at the top of the buried oxide, so the film
    occupies 0 .. film_thickness; the ridge top is at ``etch_depth`` above the
    remaining slab.
    """
    slab = film_thickness_um - etch_depth_um
    if slab < -1e-9:
        raise ValueError("etch depth exceeds film thickness")

    gsg = electrodes and str(electrode_topology).lower() == "gsg"
    w_gnd = float(ground_width_um) if ground_width_um else electrode_width_um
    # the guides of a gsg line sit centred in the two gaps, so the cross-section
    # is symmetric about the signal conductor and carries two ridges
    arm_offset = (electrode_width_um / 2 + electrode_gap_um / 2) if gsg else 0.0
    if gsg:
        electrode_extent = electrode_width_um / 2 + electrode_gap_um + w_gnd
    elif electrodes:
        electrode_extent = electrode_gap_um / 2 + electrode_width_um
    else:
        electrode_extent = 0.0
    half_x = max(
        electrode_extent,
        arm_offset + wg_top_width_um / 2 + post_gap_um + post_width_um,
    ) + window_pad_x_um
    box_model = min(box_thickness_um, box_model_depth_um)
    y_lo = -box_model
    y_hi = max(film_thickness_um + min(clad_thickness_um, 1.6), film_thickness_um + 1.2)
    if electrodes:
        y_hi = max(y_hi, slab + electrode_thickness_um + 0.8)
    y_bottom = y_lo - (0.8 if include_substrate else 0.0) - window_pad_y_um
    y_hi = y_hi + window_pad_y_um

    xs = CrossSection(
        background=clad_material,
        window=(-half_x, half_x, y_bottom, y_hi),
        name=name,
    )
    # Handle wafer.  Included for the RF problem (it is a high-permittivity
    # ground plane at DC); omitted for the optical problem, where the real
    # 4.7 um BOX isolates the mode completely and a truncated BOX would
    # otherwise let the solver find spurious substrate modes.
    # Blanket layers are drawn 1 um beyond the window so that sub-pixel
    # averaging at the boundary columns still sees solid material - otherwise
    # the edge column reports a half-empty slab and the lateral-guidance floor
    # comes out too low.
    xe = half_x + 1.0
    if include_substrate:
        xs.add(Shape.rect(substrate_material, -xe, xe, y_bottom - 1.0, y_lo, "substrate"))
    xs.add(Shape.rect(box_material, -xe, xe, y_lo, 0.0, "box"))
    # The unetched slab, blanket or in strips around each guide.
    #
    # A blanket slab puts high-permittivity film under every conductor and
    # offers a lateral path the whole width of the window. Where an offset is
    # declared the slab is drawn only around the guides, as the process draws
    # it, and the conductors then sit on the buried oxide across most of their
    # width. The two give materially different capacitances and the difference
    # is a fact about the device rather than about the model.
    guide_centres = [-arm_offset, arm_offset] if gsg else [0.0]
    slab_spans: list[tuple[float, float]] = []
    if slab > 1e-9:
        if slab_offset_um is None:
            slab_spans = [(-xe, xe)]
        else:
            half = wg_top_width_um / 2 + float(slab_offset_um)
            raw = sorted((c - half, c + half) for c in guide_centres)
            for a, b in raw:                       # merge any that touch
                if slab_spans and a <= slab_spans[-1][1] + 1e-9:
                    slab_spans[-1] = (slab_spans[-1][0], max(slab_spans[-1][1], b))
                else:
                    slab_spans.append((a, b))
        for i, (a, b) in enumerate(slab_spans):
            tag = "slab" if len(slab_spans) == 1 else f"slab_{i}"
            xs.add(Shape.rect(film_material, a, b, 0.0, slab, tag))

    def _metal_base(x_lo: float, x_hi: float) -> list[tuple[float, float, float]]:
        """Split a conductor at the slab edges, with its floor at each piece.

        Metal over the slab starts at the slab's top face. Metal beyond it
        reaches down to the buried oxide, the film having been etched away, so
        the conductor is 120 nm thicker there. Splitting the shape states that
        step rather than averaging it away.
        """
        edges = {x_lo, x_hi}
        for a, b in slab_spans:
            if x_lo < a < x_hi:
                edges.add(a)
            if x_lo < b < x_hi:
                edges.add(b)
        marks = sorted(edges)
        out = []
        for a, b in zip(marks, marks[1:]):
            if b - a <= 1e-9:
                continue
            mid = 0.5 * (a + b)
            on_slab = any(lo - 1e-9 <= mid <= hi + 1e-9 for lo, hi in slab_spans)
            out.append((a, b, slab if on_slab else 0.0))
        return out
    # ridge, or one ridge per gap for a gsg line
    if gsg:
        for sgn, tag in ((-1.0, "ridge_L"), (+1.0, "ridge_R")):
            xs.add(Shape.trapezoid(film_material, sgn * arm_offset, wg_top_width_um,
                                   etch_depth_um, slab, sidewall_deg, tag))
    else:
        xs.add(
            Shape.trapezoid(
                film_material, 0.0, wg_top_width_um, etch_depth_um, slab, sidewall_deg, "ridge"
            )
        )
    # Bragg posts (the grating perturbation, seen in this cut when the plane
    # passes through a post)
    if with_posts:
        inner = wg_top_width_um / 2 + post_gap_um
        for sgn in (-1.0, +1.0):
            xc = sgn * (inner + post_width_um / 2)
            xs.add(
                Shape.trapezoid(
                    film_material, xc, post_width_um, etch_depth_um, slab, sidewall_deg,
                    f"post_{'L' if sgn < 0 else 'R'}",
                )
            )
    # coplanar electrodes, sitting in cladding recesses in contact with the slab
    def _add_conductor(x_lo: float, x_hi: float, tag: str) -> None:
        top = slab + electrode_thickness_um
        pieces = _metal_base(min(x_lo, x_hi), max(x_lo, x_hi))
        for j, (a, b, floor) in enumerate(pieces):
            name = tag if len(pieces) == 1 else f"{tag}_{j}"
            xs.add(Shape.rect(electrode_material, a, b, floor, top, name))

    if gsg:
        # signal on axis, a ground beyond each gap, and a guide in each gap
        _add_conductor(-electrode_width_um / 2, electrode_width_um / 2, "electrode_S")
        for sgn, tag in ((-1.0, "electrode_GL"), (+1.0, "electrode_GR")):
            x_in = sgn * (electrode_width_um / 2 + electrode_gap_um)
            _add_conductor(x_in, x_in + sgn * w_gnd, tag)
    elif electrodes:
        for sgn in (-1.0, +1.0):
            x_in = sgn * electrode_gap_um / 2
            _add_conductor(x_in, x_in + sgn * electrode_width_um,
                           f"electrode_{'L' if sgn < 0 else 'R'}")
    return xs
