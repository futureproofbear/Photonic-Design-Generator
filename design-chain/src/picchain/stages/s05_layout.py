"""Stage 5 - mask layout.

The E-DBR is drawn as an explicit polygon list so the same geometry can be
emitted through either backend:

* **klayout** (``klayout.db``) - always available, and the same object model the
  DRC stage runs on;
* **gdsfactory** - used when installed, so the cell drops straight into a
  gdsfactory-based top-level assembly and inherits its netlist/port machinery.

The whole device is drawn by default. A 7.25 mm grating of 1.28 um period is
about 5,665 periods carrying two posts each, and emitting all of them was found
to cost 1.5 s against the 35 s the chain spends solving the mode. The saving
from drawing fewer is therefore not worth the consequence, which is that every
geometric figure the run reports describes a device that is not the one being
simulated.

``layout.draw_periods`` still accepts a count, and it is worth setting where the
die is being assembled: a split ladder multiplies the polygons by the number of
copies, and the fill placer and the netlist extraction scale with them. The run
records what was drawn either way, and ``layout.require_complete`` refuses a
partial mask outright.
"""

from __future__ import annotations

import math
from typing import Any

from .. import process
from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary

DBU = 0.001  # 1 nm database unit


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _facet_shear(angle_deg: float, width_um: float) -> float:
    """Longitudinal offset of one edge of a face cut at ``angle_deg``.

    The face is rotated about the guide axis, so one side advances by this
    amount and the other retreats by it. A zero angle gives a square end.
    """
    return 0.5 * width_um * math.tan(math.radians(float(angle_deg)))


def _angled_lead_in(angle_deg: float, radius_um: float, straight_um: float,
                    width_um: float, tip_width_um: float | None = None,
                    n_seg: int = 24):
    """The guide that meets a perpendicular die edge at ``angle_deg``.

    Returned as (polygon, dz, dy, entry_y), where the polygon runs from the die
    edge to the point at which the guide is once more parallel to the die axis,
    dz and dy are the extent it consumes along and across that axis, and entry_y
    is the lateral offset at the die edge.

    The route is a straight run at the angle, then a circular arc of the given
    radius turning back through the same angle. Keeping the die edge
    perpendicular is what makes this necessary: the alternative, shearing the end
    face and dicing the whole array at the angle, needs no bend and no lateral
    excursion, and is what `facet_route: sheared` draws.

    The arc is approximated by ``n_seg`` straight segments. The polygon is built
    as two offset rails so that the drawn width is the guide width measured
    perpendicular to its own axis rather than to the die axis, which a sheared
    rectangle would get wrong by 1/cos(angle).

    Where ``tip_width_um`` is given the straight run carries the taper, widening
    from the tip at the die edge to the full guide width by the start of the arc.
    The mode is then expanded before it is bent, which is the order that matters:
    a narrow guide is the one that radiates in a bend.
    """
    import math

    th = math.radians(float(angle_deg))
    w0 = float(tip_width_um if tip_width_um is not None else width_um)
    w1 = float(width_um)
    n_str = max(2, n_seg // 3)
    centre: list[tuple[float, float]] = []
    halves: list[float] = []
    # The tangent is carried per point rather than differenced from the
    # neighbours. A backward difference over the last arc chord points along
    # that chord and not along the guide, so the two rails ended at different z
    # and the junction with the feed carried a sliver a nanometre wide. Both
    # rule engines reported it as a minimum-gap violation. The tangent is known
    # in closed form at every point here, so it is used.
    tang: list[tuple[float, float]] = []

    # the straight run at the angle, leaving the die edge, carrying the taper
    for k in range(n_str + 1):
        t = k / n_str
        centre.append((straight_um * t * math.cos(th), straight_um * t * math.sin(th)))
        halves.append(0.5 * (w0 + (w1 - w0) * t))
        tang.append((math.cos(th), math.sin(th)))

    # the arc back to parallel: centre of curvature is perpendicular to the
    # current heading, on the side that turns the guide toward the die axis
    z0, y0 = centre[-1]
    cz = z0 + radius_um * math.sin(th)
    cy = y0 - radius_um * math.cos(th)
    for k in range(1, n_seg + 1):
        a = th * (1.0 - k / n_seg)
        centre.append((cz - radius_um * math.sin(a), cy + radius_um * math.cos(a)))
        halves.append(0.5 * w1)
        # travelling with a decreasing, the direction of travel is (cos a, sin a),
        # which is exactly axial at the final point where a is zero
        tang.append((math.cos(a), math.sin(a)))

    # two rails offset perpendicular to the local heading
    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []
    for i, (z, y) in enumerate(centre):
        tz, ty = tang[i]
        nz, ny = -ty, tz
        h = halves[i]
        left.append((z + h * nz, y + h * ny))
        right.append((z - h * nz, y - h * ny))

    poly = left + right[::-1]
    return poly, centre[-1][0], centre[-1][1], 0.0


def _required_axis(design: Design) -> str:
    """The crystal axis the declared electro-optic coefficient is reached along.

    For an X-cut film the crystal c-axis lies in the plane of the wafer. A
    quasi-TE mode has its dominant field in that plane, so r33 is presented to
    it only where the field is parallel to c, which requires propagation
    perpendicular to c. On a Z-cut film c is out of plane and r33 is reached by
    a quasi-TM mode instead. Stating which case obtains is the point; the chain
    does not rotate the tensor for an arbitrary orientation.
    """
    cut = design.platform.cut.lower()
    pol = design.mesh.polarisation.upper()
    coeff = design.electrodes.eo_coefficient.lower()
    if cut == "x":
        return ("propagation perpendicular to the in-plane c-axis, quasi-TE"
                if coeff == "r33" else "in-plane, quasi-TE")
    return ("out-of-plane field, quasi-TM" if coeff == "r33"
            else f"z-cut with {coeff} and {pol}")


def period_dither(period_um: float, n_periods: int, grid_nm: float) -> dict:
    """The distortion a manufacturing grid imposes on a periodic structure.

    A post nominally at k·Λ is written at the nearest grid point. Where Λ is
    not an integer number of grid steps the residual walks quasi-randomly
    across the grating, so the structure delivered is weakly chirped. The
    displacement is bounded by half a grid step and is therefore small against
    any dimension; it is not small against the phase budget of several thousand
    periods, which is what sets the Bragg condition.
    """
    grid_um = float(grid_nm) * 1e-3
    n = max(1, int(n_periods))
    err = [(round(k * period_um / grid_um) * grid_um) - k * period_um for k in range(n)]
    rms = math.sqrt(sum(e * e for e in err) / len(err)) * 1e3
    steps = period_um / grid_um
    return {
        "period_um": float(period_um),
        "periods": n,
        "period_on_grid": abs(steps - round(steps)) < 1e-9,
        "period_grid_steps": steps,
        "period_dither_nm_rms": rms,
        "period_dither_nm_max": max(abs(e) for e in err) * 1e3,
    }


def snap_polygons(polys: dict, grid_nm: float) -> tuple[dict, dict]:
    """Move every vertex onto the manufacturing grid, and report the cost.

    A foundry states a grid. Data off it is either refused or snapped without
    notice, and the second is worse on a periodic structure: the post at
    k·Λ lands on the nearest grid point, so the period acquires a
    quasi-random dither of up to half a grid step. Over several thousand
    periods that is a distortion of the Bragg condition rather than a rounding
    detail. Snapping here makes the emitted mask the one that will be printed,
    and the displacement it costs is measured rather than assumed.
    """
    grid_um = float(grid_nm) * 1e-3
    if grid_um <= 0:
        raise ValueError("process.grid_nm must be positive")
    worst = 0.0
    moved = 0
    total = 0
    out: dict[str, list] = {}
    for layer, plist in polys.items():
        snapped_list = []
        for poly in plist:
            pts = []
            for x, y in poly:
                sx = round(x / grid_um) * grid_um
                sy = round(y / grid_um) * grid_um
                d = math.hypot(sx - x, sy - y)
                total += 1
                if d > 1e-12:
                    moved += 1
                    worst = max(worst, d)
                pts.append((sx, sy))
            snapped_list.append(pts)
        out[layer] = snapped_list
    return out, {
        "grid_nm": float(grid_nm),
        "vertices": total,
        "vertices_moved": moved,
        "fraction_moved": (moved / total) if total else 0.0,
        "max_displacement_nm": worst * 1e3,
    }


def build_polygons(design: Design, ctx: RunContext) -> dict[str, list[list[tuple[float, float]]]]:
    """Return {layer_name: [polygon, ...]} in um.

    Every dimension here is the **drawn** one. Where the process carries a bias
    and pre-compensation is requested, the drawn dimension differs from the
    nominal figure in the design file, so that the printed feature lands on the
    nominal one. The physics is solved on the printed geometry instead; the two
    are reconciled by ``picchain.process``.
    """
    lay = design.layout
    g = design.grating
    e = design.electrodes
    cav = design.cavity
    geom = process.geometry(design, "drawn")

    grat = ctx.get("grating") or {}
    period = float(grat.get("period_um") or g.period_um or 1.0)
    post_len = geom.post_length_um
    wg_width = geom.wg_top_width_um

    n_draw = lay.draw_periods if lay.draw_periods else int(round(g.length_um / period))
    n_draw = max(1, min(n_draw, int(round(g.length_um / period))))
    drawn_length = n_draw * period

    out: dict[str, list] = {k: [] for k in lay.layer_map}
    texts: list[tuple[str, float, float]] = []

    z = 0.0
    # --- input taper, terminated on the angled facet ---------------------
    # The angle exists to steer the facet reflection out of the guide. It does
    # that only if the end face is cut at the angle, so the tip is drawn with a
    # slanted end rather than a square one. The shear is applied along the
    # propagation direction, which keeps the tip width, and therefore the mode
    # at the facet, equal to the figure the `facet` stage was given.
    tl = lay.taper_length_um
    tip = lay.taper_tip_width_um
    angled = lay.draw_facets and lay.facet_route == "angled"
    lead_excursion = 0.0
    # The optical path from the facet to the grating, which is what the cavity
    # stage computes its delay from. Under the sheared route it is the taper
    # length. Under the angled route the guide travels further than it advances,
    # so the two differ and the arc must be counted.
    lead_path = tl
    if angled:
        # The die edge is perpendicular and the guide is routed to meet it at the
        # declared angle: a straight run at that angle carrying the taper, then
        # an arc back to the die axis. The route is drawn from the die edge
        # inward and displaced laterally so that it arrives on the axis where the
        # feed begins, so nothing downstream of the lead-in moves.
        rad = lay.facet_bend_radius_um
        poly, dz_lead, dy_lead, _ = _angled_lead_in(
            lay.input_facet_angle_deg, rad, tl, wg_width, tip
        )
        out["WG"].append([(pz, py - dy_lead) for pz, py in poly])
        lead_excursion = abs(dy_lead)
        lead_path = tl + rad * math.radians(abs(lay.input_facet_angle_deg))
        z = dz_lead
    else:
        shear_in = _facet_shear(lay.input_facet_angle_deg, tip) if lay.draw_facets else 0.0
        out["WG"].append(
            [(z + shear_in, -tip / 2), (z + tl, -wg_width / 2),
             (z + tl, wg_width / 2), (z - shear_in, tip / 2)]
        )
        z += tl
    # --- feed waveguide ---
    # `cavity.feed_length_um` is the facet-to-grating distance the round-trip
    # delay is computed from, so the input taper is spent out of it and the
    # straight run carries the remainder. The output taper lies beyond the
    # mirror and is outside the cavity, so it is not deducted. Until 2026-08-06
    # both were deducted and the drawn cavity was one taper length short of the
    # modelled one, by 15 % at the length declared here.
    # The taper is spent out of the facet-to-grating distance, so a distance
    # shorter than the taper describes no geometry. The clamp below would have
    # drawn a 10 um stub and reported nothing, and the drawn cavity would then
    # have borne no relation to the delay the cavity stage computed from
    # `cavity.feed_length_um`. Refused instead. The case arises when the cavity
    # is shortened to raise the Pockels lever, which is the standard route to a
    # wider mode-hop-free range.
    if cav.feed_length_um < lead_path:
        what = ("the angled lead-in, being the taper plus the arc that returns "
                "the guide to the die axis, is") if angled else "layout.taper_length_um is"
        raise RuntimeError(
            f"cavity.feed_length_um is {cav.feed_length_um:.1f} um and "
            f"{what} {lead_path:.1f} um. The feed length is the "
            "facet-to-grating distance and the lead-in is drawn inside it, so it "
            "cannot be the shorter of the two. Shorten the taper, open the bend "
            "radius, or lengthen the feed"
        )
    # The straight run carrying the remainder of the facet-to-grating distance.
    # A 10 um floor is applied so that a degenerate case still draws something,
    # and where it binds the drawn cavity is longer than the modelled one. That
    # was silent until 2026-08-07, and it can bind under the angled route: the
    # arc consumes part of the distance the sheared route spends entirely on the
    # taper, so a feed that left 50 um of straight may leave none.
    feed = cav.feed_length_um - lead_path
    if feed < 10.0:
        ctx.warn(
            f"the straight run between the lead-in and the grating is "
            f"{feed:.1f} um and has been raised to the 10 um floor. The drawn "
            f"facet-to-grating distance is therefore {lead_path + 10.0:.1f} um "
            f"against the {cav.feed_length_um:.1f} um the cavity delay was "
            f"computed from. Open cavity.feed_length_um or tighten "
            f"layout.facet_bend_radius_um"
        )
        feed = 10.0
    out["WG"].append(_rect(z, -wg_width / 2, z + feed, wg_width / 2))
    z += feed

    # --- grating: straight waveguide + post pairs ---
    g0 = z
    out["WG"].append(_rect(g0, -wg_width / 2, g0 + drawn_length, wg_width / 2))
    inner = wg_width / 2 + geom.post_gap_um
    for k in range(n_draw):
        zc = g0 + (k + 0.5) * period
        for sgn in (-1, 1):
            yc = sgn * (inner + geom.post_width_um / 2)
            out["WG"].append(
                _rect(zc - post_len / 2, yc - geom.post_width_um / 2,
                      zc + post_len / 2, yc + geom.post_width_um / 2)
            )
    z = g0 + drawn_length

    # --- output taper, likewise terminated on its facet ------------------
    shear_out = _facet_shear(lay.output_facet_angle_deg, tip) if lay.draw_facets else 0.0
    out["WG"].append(
        [(z, wg_width / 2), (z, -wg_width / 2),
         (z + tl - shear_out, -tip / 2), (z + tl + shear_out, tip / 2)]
    )
    z_end = z + tl

    # --- electrodes flanking the grating ---
    if e.enabled:
        for sgn in (-1, 1):
            y_in = sgn * geom.electrode_gap_um / 2
            y_out = y_in + sgn * geom.electrode_width_um
            out["METAL"].append(
                _rect(g0, min(y_in, y_out), g0 + drawn_length, max(y_in, y_out))
            )
            # bond pad
            pad = 80.0
            out["PAD"].append(
                _rect(g0 + drawn_length / 2 - pad / 2, min(y_out, y_out + sgn * pad),
                      g0 + drawn_length / 2 + pad / 2, max(y_out, y_out + sgn * pad))
            )
            # Two labels per electrode, one on the pad and one on the conductor.
            # A net carrying both is a pad that reaches what it drives; a net
            # carrying one is a break, and a count of connected regions cannot
            # distinguish the two.
            side = "L" if sgn < 0 else "R"
            texts.append((f"E_{side}_PAD", g0 + drawn_length / 2, y_out + sgn * pad / 2))
            texts.append((f"E_{side}_ELEC", g0 + drawn_length * 0.25, (y_in + y_out) / 2))

    # --- slab / etch-clear region and floorplan ---
    # The angled route carries the guide off the die axis before it returns, so
    # the slab and the floor plan must reach past that excursion. Sizing them off
    # the electrodes alone would leave the lead-in outside the etch-clear region.
    pad_y = (geom.electrode_gap_um / 2 + geom.electrode_width_um + 30.0) if e.enabled else 30.0
    pad_y = max(pad_y, lead_excursion + 30.0)
    # The bond pads reach 80 um beyond the outer electrode edge, and the figure
    # above allowed only 30. The floor plan therefore stopped at 58.8 um while
    # the pads ran to 103.8, and the foundry runset reported the pads as lying
    # outside the usable area. Sized off the pads as well.
    if e.enabled:
        pad_y = max(pad_y, geom.electrode_gap_um / 2 + geom.electrode_width_um + 80.0 + 20.0)
    out["SLAB"].append(_rect(-5.0, -pad_y, z_end + 5.0, pad_y))
    out["FLOORPLAN"].append(_rect(-5.0, -pad_y - 5.0, z_end + 5.0, pad_y + 5.0))

    # --- the facet planes and the band the cleave or polish removes -------
    if lay.draw_facets:
        ko = lay.facet_keepout_um
        rec = lay.facet_recess_um
        for z_face, angle, sgn in ((0.0, lay.input_facet_angle_deg, -1.0),
                                   (z_end, lay.output_facet_angle_deg, +1.0)):
            # Under the angled route the angle is carried by the guide and not by
            # the end face, so the die edge is perpendicular and the band is
            # square. Shearing it here as well would apply the angle twice.
            face_angle = 0.0 if (angled and z_face == 0.0) else angle
            # the facet plane itself, drawn at its angle across the keep-out
            dz = _facet_shear(face_angle, 2 * ko)
            out["FACET"].append([
                (z_face - dz, -ko), (z_face + dz, ko),
                (z_face + dz + sgn * 0.5, ko), (z_face - dz + sgn * 0.5, -ko),
            ])
            # The recess: the material between the facet and the die edge that
            # the cleave or the polish removes. It must follow the facet plane,
            # not the die axis. Drawn as an axis-aligned rectangle until
            # 2026-08-07, it disagreed with the angled face it was meant to
            # produce: across a 30 um keep-out an 8 degree face spans 4.22 um in
            # z, against a recess only 5 um deep, so the two parted company over
            # nearly the whole band. The mask then said the cleave was
            # perpendicular while the facet it serves was angled.
            edge = z_face + sgn * rec
            out["FACET"].append([
                (z_face - dz, -ko), (z_face + dz, ko),
                (edge + dz, ko), (edge - dz, -ko),
            ])
    ctx.put("layout.facet_recess_um", lay.facet_recess_um if lay.draw_facets else 0.0)
    # How the guide reaches the end face, and what that route cost. Under
    # `sheared` the guides stay parallel and the array is diced at the angle, so
    # the excursion is zero. Under `angled` the die edge is perpendicular and the
    # excursion is the lateral offset the routing consumes, which the device
    # pitch must carry.
    ctx.put("layout.facet_route", lay.facet_route if lay.draw_facets else "none")
    ctx.put("layout.facet_lead_in_excursion_um", lead_excursion)
    ctx.put("layout.facet_lead_in_path_um", lead_path)
    ctx.put("layout.facet_bend_radius_um", lay.facet_bend_radius_um if angled else None)

    # --- the crystal orientation key --------------------------------------
    # `platform.cut` selects the permittivity tensor and therefore every
    # electro-optic figure the chain reports. Nothing on the mask stated the
    # orientation the wafer must be diced and mounted at, so a device rotated
    # against the crystal would have satisfied every check and presented a
    # different coefficient to the light.
    if lay.draw_orientation_key:
        arrow_y = pad_y + 25.0
        a0, a1 = z_end * 0.5 - 60.0, z_end * 0.5 + 60.0
        out["ORIENT"].append(_rect(a0, arrow_y - 2.0, a1 - 20.0, arrow_y + 2.0))
        out["ORIENT"].append([(a1 - 20.0, arrow_y - 8.0), (a1, arrow_y),
                              (a1 - 20.0, arrow_y + 8.0)])
    return_orientation = {
        "cut": design.platform.cut,
        "eo_coefficient": e.eo_coefficient,
        "misalignment_deg": lay.crystal_misalignment_deg,
        "required_axis": _required_axis(design),
    }
    ctx.put("layout.orientation", return_orientation)
    ctx.put("layout.texts", [{"text": t, "x_um": x, "y_um": y} for t, x, y in texts])

    ctx.put("layout.periods_drawn", n_draw)
    ctx.put("layout.periods_total", int(round(g.length_um / period)))
    ctx.put("layout.drawn_grating_length_um", drawn_length)
    ctx.put("layout.device_length_um", z_end)
    # where each feature begins, so that a drawing of the mask can zoom on it
    # without re-deriving the floor plan
    ctx.put("layout.taper_length_um", tl)
    ctx.put("layout.grating_start_um", g0)
    return out


def apply_derived_layers(polys: dict, layer_map: dict, derived) -> tuple[dict, list[dict]]:
    """Produce the layers a process asks for from the layers a designer draws.

    Mask polarity is the case that matters. A process wanting a trench, or a
    dark field, wants the inverse of what is convenient to draw, and the inverse
    is a drawn extent minus the drawn feature. Deriving it keeps one description
    of the device; drawing both senses by hand keeps two, and they diverge.

    Operations are applied in the order declared, so a derived layer may be the
    operand of a later one.
    """
    import klayout.db as db

    def region_of(name: str) -> "db.Region":
        r = db.Region()
        for p in polys.get(name, []):
            r.insert(db.DPolygon([db.DPoint(x, y) for x, y in p]).to_itype(DBU))
        return r.merged()

    out = dict(polys)
    described: list[dict] = []
    for spec in derived:
        if spec.a not in out:
            raise ValueError(
                f"derived layer {spec.name!r} reads {spec.a!r}, which is not drawn. "
                f"The layers available are {sorted(out)}"
            )
        ra = region_of(spec.a)
        if spec.op == "size":
            result = ra.sized(int(round(spec.by_um / DBU)))
        else:
            if not spec.b:
                raise ValueError(f"derived layer {spec.name!r} needs a second operand")
            if spec.b not in out:
                raise ValueError(
                    f"derived layer {spec.name!r} reads {spec.b!r}, which is not drawn"
                )
            rb = region_of(spec.b)
            result = {"not": lambda: ra - rb, "and": lambda: ra & rb,
                      "or": lambda: ra | rb, "xor": lambda: ra ^ rb}[spec.op]()
        result = result.merged()

        if spec.layer:
            layer_map[spec.name] = list(spec.layer)
        elif spec.name not in layer_map:
            raise ValueError(
                f"derived layer {spec.name!r} declares no layer number and is not "
                "present in layout.layer_map"
            )
        # A boolean result carries holes, and the pipeline downstream of here
        # is a list of vertex sequences with no way to express one. Taking the
        # hull alone would fill every hole in, so an inverse layer would come
        # out solid and overlap the feature it was derived to exclude. The holes
        # are therefore cut open first, which is what a mask writer does anyway.
        out[spec.name] = [
            [(pt.x * DBU, pt.y * DBU) for pt in poly.resolved_holes().each_point_hull()]
            for poly in result.each()
        ]
        described.append({
            "name": spec.name,
            "expression": (f"{spec.a} sized by {spec.by_um:+g} um" if spec.op == "size"
                           else f"{spec.a} {spec.op} {spec.b}"),
            "layer": layer_map[spec.name],
            "polygons": len(out[spec.name]),
            "area_um2": float(result.area()) * DBU * DBU,
        })
    return out, described


def _write_klayout(polys, layer_map, path, cell_name, grid_nm: float = 1.0,
                   texts=None, text_layer: str = "LABEL"):
    """Write the polygon list, snapped to the grid after merging.

    Snapping the vertices supplied is not sufficient. Two shapes on one layer
    that overlap are resolved into a single outline when the layer is merged,
    and the boolean introduces vertices at their intersections. Those vertices
    are computed rather than drawn, so they land wherever the crossing falls and
    need not be on the grid. The layer is therefore merged first and snapped
    afterwards, which is the order mask preparation uses.
    """
    import klayout.db as db

    ly = db.Layout()
    ly.dbu = DBU
    top = ly.create_cell(cell_name)
    step = max(1, int(round(float(grid_nm) * 1e-3 / DBU)))
    for name, plist in polys.items():
        if not plist:
            continue
        li, ld = layer_map[name]
        layer = ly.layer(li, ld)
        region = db.Region()
        for p in plist:
            region.insert(db.DPolygon([db.DPoint(x, y) for x, y in p]).to_itype(DBU))
        if step > 1:
            region = region.merged().snapped(step, step)
        top.shapes(layer).insert(region)
    # Text is written as text, not as polygons. The extraction takes a net name
    # from a label sitting on the conductor, which is what allows the connectivity
    # to be compared against an intended circuit rather than merely counted.
    if texts and text_layer in layer_map:
        tl = ly.layer(*layer_map[text_layer])
        for entry in texts:
            top.shapes(tl).insert(
                db.DText(entry["text"], entry["x_um"], entry["y_um"]))
    ly.write(str(path))
    return ly


def _min_interior_angle(poly) -> float:
    """Smallest interior angle of a polygon hull, in degrees.

    KLayout filters *edges* by their absolute angle, which is a different
    question: an edge at 45 degrees says nothing about the angle between it and
    its neighbour. The interior angle is what prints rounded, so it is computed
    here from the vertices.
    """
    pts = list(poly.each_point_hull())
    n = len(pts)
    if n < 3:
        return 0.0
    worst = 360.0
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        v1 = (a.x - b.x, a.y - b.y)
        v2 = (c.x - b.x, c.y - b.y)
        m1 = math.hypot(*v1)
        m2 = math.hypot(*v2)
        if m1 == 0 or m2 == 0:
            return 0.0                      # a repeated vertex: degenerate
        cosang = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (m1 * m2)))
        worst = min(worst, math.degrees(math.acos(cosang)))
    return worst


def check_geometry(gds_path, layer_map, *, min_angle_deg: float, max_vertices: int,
                   grid_nm: float = 1.0) -> dict:
    """Geometry a rule deck does not examine.

    A deck asks whether each shape is legal against a dimension. It does not ask
    whether the shape is a shape. Five conditions are checked here. Every one of
    them is legal to a width or a spacing rule, and none survives mask fracture
    intact:

    * a polygon that is not simple, being self-intersecting, self-touching or
      carrying a repeated vertex;
    * an interior angle below the floor, which prints as a rounded corner;
    * a vertex off the manufacturing grid, which verifies that the snap applied
      before writing actually took;
    * a duplicate, two identical shapes on one layer;
    * a vertex count above the cap most fracture tools impose.
    """
    import klayout.db as db

    ly = db.Layout()
    ly.read(str(gds_path))
    top = ly.top_cell()
    dbu = ly.dbu
    grid_dbu = max(1, int(round(float(grid_nm) * 1e-3 / dbu)))
    findings: dict[str, dict] = {}
    total_issues = 0

    for name, (li, ld) in layer_map.items():
        idx = ly.find_layer(li, ld)
        if idx is None:
            continue
        region = db.Region(top.begin_shapes_rec(idx))
        if region.is_empty():
            continue

        strange = int(region.strange_polygon_check().count())
        off_grid = int(region.grid_check(grid_dbu, grid_dbu).count())

        acute = 0
        over = 0
        worst_angle = 360.0
        seen, duplicates = set(), 0
        for poly in region.each():
            ang = _min_interior_angle(poly)
            worst_angle = min(worst_angle, ang)
            if min_angle_deg > 0 and ang < min_angle_deg:
                acute += 1
            if max_vertices > 0 and poly.num_points() > max_vertices:
                over += 1
            key = poly.to_s()
            if key in seen:
                duplicates += 1
            seen.add(key)

        issues = strange + acute + duplicates + over + off_grid
        findings[name] = {
            "shapes": int(region.count()),
            "strange_polygons": strange,
            "acute_corners": int(acute),
            "min_interior_angle_deg": round(worst_angle, 3),
            "off_grid_vertices": off_grid,
            "duplicate_shapes": int(duplicates),
            "over_vertex_cap": int(over),
            "area_um2": float(region.area()) * dbu * dbu,
            "issues": int(issues),
        }
        total_issues += issues

    return {
        "performed": True,
        "min_angle_deg": float(min_angle_deg),
        "max_vertices": int(max_vertices),
        "grid_nm": float(grid_nm),
        "total_issues": int(total_issues),
        "clean": total_issues == 0,
        "by_layer": findings,
    }


def write_layer_table(layer_map, path_lyp, path_map) -> None:
    """The layer table, beside the mask.

    A mask file carries layer numbers. What each number means is carried
    nowhere within it, so a mask sent without a table is a set of numbered
    polygons whose interpretation rests on correspondence. Two forms are
    written: KLayout layer properties for viewing, and a plain map for a
    recipient whose tools are not KLayout.
    """
    rows = sorted(layer_map.items(), key=lambda kv: (kv[1][0], kv[1][1]))
    colours = ["#e04a3f", "#3f8ee0", "#3fbf6f", "#c9a227", "#8e5fd4",
               "#d46fa8", "#4fc0c0", "#9a9a9a", "#e0803f", "#6f6fd4"]
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<layer-properties>"]
    for i, (name, (num, dt)) in enumerate(rows):
        lines += [
            " <properties>",
            f"  <frame-color>{colours[i % len(colours)]}</frame-color>",
            f"  <fill-color>{colours[i % len(colours)]}</fill-color>",
            "  <dither-pattern>I3</dither-pattern>",
            "  <visible>true</visible>",
            f"  <name>{name} {num}/{dt}</name>",
            f"  <source>{num}/{dt}@1</source>",
            " </properties>",
        ]
    lines.append("</layer-properties>")
    path_lyp.write_text("\n".join(lines) + "\n", encoding="utf-8")

    table = ["# layer table for this mask", "# name, layer, datatype"]
    table += [f"{name}, {num}, {dt}" for name, (num, dt) in rows]
    path_map.write_text("\n".join(table) + "\n", encoding="utf-8")


def _write_gdsfactory(polys, layer_map, path, cell_name) -> bool:
    try:
        import gdsfactory as gf
    except Exception:
        return False
    try:                       # a PDK must be active before Component() works
        gf.get_active_pdk()
    except Exception:
        gf.gpdk.PDK.activate()
    # The cell library is process-wide and a repeated name is refused. Anything
    # that emits a layout more than once in one process therefore loses this
    # backend after the first call, and with it the comparison against it. That
    # is the case for `corners`, which would have cross-checked its first corner
    # and none of the others.
    try:
        gf.clear_cache()
    except Exception:          # pragma: no cover - version dependent
        pass
    c = gf.Component(cell_name)
    for name, plist in polys.items():
        if not plist:
            continue
        for p in plist:
            c.add_polygon(p, layer=tuple(layer_map[name]))
    c.write_gds(str(path))
    return True


def compare_backends(gds_a, gds_b, layer_map) -> dict[str, Any]:
    """Exclusive-or of two emitted files, layer by layer.

    Two writers are given one polygon list, and the residual of their
    difference is the only evidence available that either wrote what it was
    given. The check costs a read and a boolean operation. It catches a unit
    error, a lost layer, a dropped polygon and a coordinate rounded to a
    different grid, none of which a rule deck detects, every one of them being
    legal geometry.
    """
    import klayout.db as db

    def regions(path):
        ly = db.Layout()
        ly.read(str(path))
        top = ly.top_cell()
        out = {}
        for name, (li, ld) in layer_map.items():
            idx = ly.layer(li, ld)
            out[name] = db.Region(top.begin_shapes_rec(idx)).merged()
        return out

    ra, rb = regions(gds_a), regions(gds_b)
    per_layer, total = {}, 0.0
    for name in layer_map:
        resid = (ra[name] ^ rb[name]).merged()
        area = resid.area() * (DBU**2)
        if area > 0:
            per_layer[name] = area
        total += area
    return {
        "performed": True,
        "residual_area_um2": total,
        "residual_by_layer_um2": per_layer,
        # a database unit is 1 nm, so a genuine agreement is exactly zero. A
        # tolerance would only conceal the rounding difference worth finding
        "agree": bool(total == 0.0),
    }


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    lay = design.layout
    if not lay.enabled:
        ctx.put("layout", {"enabled": False})
        return {"enabled": False}

    polys = build_polygons(design, ctx)
    derived: list[dict] = []
    if lay.derived_layers:
        polys, derived = apply_derived_layers(polys, lay.layer_map, lay.derived_layers)
    polys, snap = snap_polygons(polys, design.process.grid_nm)
    info0 = ctx.get("layout") or {}
    snap.update(period_dither(
        float((ctx.get("grating") or {}).get("period_um") or design.grating.period_um or 1.0),
        int(info0.get("periods_drawn") or 1),
        design.process.grid_nm,
    ))
    ctx.ensure()
    gds = ctx.run_dir / f"{design.meta.name}.gds"
    _write_klayout(polys, lay.layer_map, gds, lay.cell_name, design.process.grid_nm,
                   texts=(ctx.get('layout') or {}).get('texts'),
                   text_layer=design.mask.label_layer)

    oasis = None
    if lay.write_oasis:
        oasis = ctx.run_dir / f"{design.meta.name}.oas"
        _write_klayout(polys, lay.layer_map, oasis, lay.cell_name, design.process.grid_nm,
                       texts=(ctx.get('layout') or {}).get('texts'),
                       text_layer=design.mask.label_layer)

    if lay.write_layer_table:
        write_layer_table(lay.layer_map,
                          ctx.run_dir / f"{design.meta.name}.lyp",
                          ctx.run_dir / f"{design.meta.name}.layermap.txt")

    geometry = {"performed": False, "reason": "not requested"}
    if lay.check_geometry:
        try:
            geometry = check_geometry(gds, lay.layer_map,
                                      min_angle_deg=lay.min_angle_deg,
                                      max_vertices=lay.max_vertices,
                                      grid_nm=design.process.grid_nm)
        except Exception as exc:  # pragma: no cover - backend specific
            geometry = {"performed": False, "reason": f"check raised: {exc}"}

    gf_ok = False
    gds_gf = ctx.run_dir / f"{design.meta.name}.gdsfactory.gds"
    try:
        gf_ok = _write_gdsfactory(polys, lay.layer_map, gds_gf, lay.cell_name)
    except Exception as exc:  # pragma: no cover - backend specific
        ctx.warn(f"gdsfactory export failed ({exc}); klayout GDS is authoritative")

    xor: dict[str, Any] = {"performed": False, "reason": "second backend unavailable"}
    if gf_ok and lay.compare_backends:
        try:
            xor = compare_backends(gds, gds_gf, lay.layer_map)
        except Exception as exc:  # pragma: no cover - backend specific
            xor = {"performed": False, "reason": f"comparison raised: {exc}"}

    # --- is the emitted mask the device that was simulated ---------------
    info = ctx.get("layout") or {}
    drawn, total_p = int(info.get("periods_drawn", 0)), int(info.get("periods_total", 0))
    complete = bool(total_p and drawn >= total_p)
    fidelity = {
        "periods_drawn": drawn,
        "periods_total": total_p,
        "drawn_fraction": (drawn / total_p) if total_p else None,
        "grating_length_drawn_um": float(info.get("drawn_grating_length_um") or 0.0),
        "grating_length_simulated_um": float(design.grating.length_um),
        "mask_is_complete": complete,
    }

    counts = {k: len(v) for k, v in polys.items() if v}
    payload = {
        "enabled": True,
        "gds": str(gds),
        "oasis": str(oasis) if oasis else None,
        "gds_gdsfactory": str(gds_gf) if gf_ok else None,
        "backend_gdsfactory_available": gf_ok,
        "backend_xor": xor,
        "fidelity": fidelity,
        "mask_is_complete": complete,
        "grid": snap,
        "derived_layers": derived,
        "geometry": geometry,
        "geometry_issues": geometry.get("total_issues"),
        "orientation": (ctx.get("layout") or {}).get("orientation"),
        "process": process.summary(design),
        "polygon_counts": counts,
        "layer_map": lay.layer_map,
        **{k: v for k, v in (ctx.get("layout") or {}).items() if not isinstance(v, dict)},
    }
    ctx.put("layout", {**(ctx.get("layout") or {}), **payload})
    ctx.write_stage("layout", payload)

    if not complete:
        message = (
            f"the emitted mask carries {drawn} of {total_p} grating periods, being a "
            f"{fidelity['grating_length_drawn_um']:.0f} um grating against the "
            f"{design.grating.length_um:.0f} um that was simulated. The rule check, the "
            "polygon counts and the electrode length all describe the shortened "
            "device. Set layout.draw_periods to null before submission"
        )
        if lay.require_complete:
            raise RuntimeError(message)
        ctx.warn(message)

    if xor.get("performed") and not xor["agree"]:
        ctx.warn(
            f"the two layout backends disagree by {xor['residual_area_um2']:.4f} um2 "
            f"across {', '.join(xor['residual_by_layer_um2'])}. One of the two files "
            "does not carry the geometry that was constructed"
        )

    # --- the manufacturing grid ------------------------------------------
    limit = design.process.max_snap_displacement_nm
    if limit and snap["max_displacement_nm"] > limit:
        raise RuntimeError(
            f"snapping to the {snap['grid_nm']:g} nm grid displaces a vertex by "
            f"{snap['max_displacement_nm']:.3f} nm, above the "
            f"process.max_snap_displacement_nm of {limit:g} nm"
        )
    if snap["grid_nm"] > DBU * 1e3 and snap["vertices_moved"]:
        # a grid coarser than the database unit is a declared choice, and the
        # displacement it costs is therefore worth stating on its own
        ctx.warn(
            f"the {snap['grid_nm']:g} nm manufacturing grid is coarser than the "
            f"{DBU * 1e3:g} nm database unit and moved {snap['vertices_moved']} of "
            f"{snap['vertices']} vertices, by up to {snap['max_displacement_nm']:.3f} nm"
        )
    if not snap["period_on_grid"]:
        ctx.warn(
            f"the grating period of {snap['period_um'] * 1e3:.2f} nm is not an integer "
            f"number of {snap['grid_nm']:g} nm grid steps, so each post lands on the "
            f"nearest grid point and the period acquires a dither of "
            f"{snap['period_dither_nm_rms']:.3f} nm RMS over {snap['periods']} periods. "
            "This is a distortion of the Bragg condition rather than a rounding of a "
            "dimension, and it is not carried by any model in the chain"
        )

    # --- geometry the deck does not examine -------------------------------
    if geometry.get("performed") and not geometry["clean"]:
        detail = ", ".join(
            f"{name}: " + ", ".join(f"{k}={v}" for k, v in e.items()
                                    if k in ("non_simple", "acute_angle_edges",
                                             "duplicate_shapes", "over_vertex_cap") and v)
            for name, e in geometry["by_layer"].items() if e["issues"]
        )
        ctx.warn(
            f"{geometry['total_issues']} geometry conditions a rule deck does not "
            f"examine were found ({detail}). Each is legal to a width or a spacing "
            "rule and none survives mask fracture intact"
        )

    # --- the crystal orientation ------------------------------------------
    orient = payload["orientation"] or {}
    if abs(float(orient.get("misalignment_deg") or 0.0)) > 1e-9:
        ctx.warn(
            f"the device is declared {orient['misalignment_deg']:g} deg from the crystal "
            f"axis its {orient['eo_coefficient']} coefficient is reached along "
            f"({orient['required_axis']}). The electro-optic figures assume alignment, "
            "the chain not rotating the tensor for an arbitrary orientation"
        )
    if not lay.draw_orientation_key:
        ctx.warn(
            "no orientation key is drawn. The cut selects the permittivity tensor and "
            "therefore every electro-optic figure reported, and a die carrying no mark "
            "of the axis it must be aligned to can be diced and mounted rotated"
        )
    if not lay.draw_facets:
        ctx.warn(
            "the facets are not drawn, so the emitted guide has square ends. The facet "
            "angle carried in this design is used by the coupling calculation and "
            "reaches no polygon, and an angle that is not in silicon suppresses no "
            "reflection"
        )

    if not process.is_identity(design):
        pr = payload["process"]
        ctx.warn(
            "a process bias is declared, so the drawn and printed geometries differ: "
            f"post gap drawn {pr['drawn']['post_gap_um'] * 1000:.0f} nm against "
            f"{pr['printed']['post_gap_um'] * 1000:.0f} nm printed. The mask carries the "
            "drawn figure and the physics was solved on the printed one"
        )
    return payload
