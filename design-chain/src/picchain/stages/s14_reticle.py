"""Stage 14 - die assembly: the device, the frame, and the structures that
measure the process.

The `layout` stage emits the device alone. That is the correct unit for a
simulation and for a rule check, and it is not a mask. A mask that can be
submitted carries items the device does not need and a fabrication run cannot
proceed without, and it carries structures the device does not use and a
returned wafer cannot be diagnosed without.

What is added
-------------
**A seal ring.** A closed ring around the die. It arrests the cracks a dice saw
starts and blocks moisture ingress along the film interfaces.

**A dicing lane.** The saw removes material. The width it removes is declared
here and drawn as a keep-out, so that no structure is placed where it will be
destroyed.

**Alignment marks.** One per lithographic level, drawn at more than one corner
so that rotation is measurable as well as translation. Where the same mark is
drawn on two levels the overlay between them is read as the asymmetry of the
gap.

**A die label.** The design name and a revision, rendered as polygons on the
label layer and repeated in metal so that it is legible on the finished part.
An unlabelled die cannot be traced to the run that produced it.

**Process control monitors.** Structures that measure the process rather than
use it. What each isolates is set out in ``picchain.monitors``.

What is not done
----------------
Fill is not placed. The `mask` stage sizes the area each deficient tile
requires; placing it needs a foundry rule for the pattern, the exclusion around
a guide and the exclusion around a pad, and inventing one would be worse than
declaring the gap.

No reticle-level step and repeat is performed. One die is assembled. Arraying
it across a reticle field is a foundry operation carried out against their frame
rather than this one.
"""

from __future__ import annotations

from typing import Any

from .. import monitors, process
from ..artifacts import RunContext
from ..config import Design, set_dotted
from ..materials import MaterialLibrary

DBU = 0.001


def _text_polygons(text: str, height_um: float):
    """Render a string as polygons, scaled to the requested cap height."""
    import klayout.db as db

    gen = db.TextGenerator.default_generator()
    if gen is None:  # pragma: no cover - depends on the klayout installation
        raise RuntimeError("no font is available to the klayout text generator")
    region = gen.text(text, DBU, 1.0)
    box = region.bbox()
    if box.height() <= 0:
        raise RuntimeError(f"the text {text!r} rendered to nothing")
    mag = height_um / (box.height() * DBU)
    return gen.text(text, DBU, mag)


def _insert(cell, layout, layer_map, name, polys, dx=0.0, dy=0.0):
    import klayout.db as db

    if name not in layer_map or not polys:
        return 0
    li, ld = layer_map[name]
    idx = layout.layer(li, ld)
    for p in polys:
        cell.shapes(idx).insert(
            db.DPolygon([db.DPoint(x + dx, y + dy) for x, y in p])
        )
    return len(polys)


def _min_space(design: Design) -> float:
    """The tightest same-layer space the declared rules permit on the guide layer.

    A monitor exists to be measured, and a monitor that violates the deck is
    removed before submission. The vernier is therefore held to the rule rather
    than allowed to define its own pitch.
    """
    wg = design.process.wg_layer
    spaces = [r.value_um for r in design.drc.rules
              if r.kind == "min_space" and r.layer == wg]
    return max(spaces) if spaces else 0.0


def _min_separation(design: Design) -> float:
    """The tightest metal-to-guide separation the declared rules permit."""
    wg, metal = design.process.wg_layer, design.process.metal_layer
    vals = [r.value_um for r in design.drc.rules
            if r.kind in ("min_separation", "min_space")
            and {r.layer, r.other_layer} == {wg, metal}]
    return max(vals) if vals else 0.0


def _build_monitors(design: Design, ctx: RunContext) -> tuple[dict[str, list], list[dict]]:
    """Every enabled monitor, packed into rows below one another."""
    cfg = design.reticle.monitors
    geom = process.geometry(design, "drawn")
    grat = ctx.get("grating") or {}
    period = float(grat.get("period_um") or design.grating.period_um or 1.0)

    out: dict[str, list] = {}
    described: list[dict] = []
    cursor_y = 0.0
    gap_between = 80.0

    def take(polys: dict[str, list], desc: dict[str, Any]):
        nonlocal cursor_y
        for layer, plist in polys.items():
            if plist:
                out.setdefault(layer, []).extend(
                    [[(x, y + cursor_y) for x, y in p] for p in plist]
                )
        desc = dict(desc)
        desc["origin_y_um"] = cursor_y
        described.append(desc)
        cursor_y -= desc.get("height_um", 0.0) + gap_between

    if cfg.kappa_ladder and cfg.kappa_gaps_um:
        take(*monitors.kappa_ladder(
            gaps_um=cfg.kappa_gaps_um, period_um=period, n_periods=cfg.kappa_periods,
            wg_width_um=geom.wg_top_width_um, post_width_um=geom.post_width_um,
            post_length_um=geom.post_length_um, row_pitch_um=cfg.row_pitch_um,
        ))
    if cfg.loss_cutback and cfg.loss_lengths_um:
        take(*monitors.loss_cutback(
            lengths_um=cfg.loss_lengths_um, wg_width_um=geom.wg_top_width_um,
            row_pitch_um=cfg.row_pitch_um,
        ))
    if cfg.cd_vernier and cfg.cd_widths_um:
        take(*monitors.cd_vernier(
            widths_um=cfg.cd_widths_um, repeats=cfg.cd_repeats,
            length_um=cfg.row_pitch_um * 0.5, row_pitch_um=cfg.row_pitch_um,
            min_space_um=_min_space(design),
        ))
    if cfg.electrode_ladder and cfg.electrode_gaps_um:
        take(*monitors.electrode_ladder(
            gaps_um=cfg.electrode_gaps_um, electrode_width_um=geom.electrode_width_um,
            length_um=400.0, wg_width_um=geom.wg_top_width_um, pad_um=80.0,
            row_pitch_um=cfg.row_pitch_um,
            min_separation_um=_min_separation(design),
        ))
    return out, described


def _split_cells(design: Design, ctx: RunContext, layout, lmap) -> tuple[list, list[dict]]:
    """One device cell per value of the split parameter.

    The device is re-drawn rather than re-placed, the parameter being a
    geometric one. Each copy is snapped to the same manufacturing grid as the
    primary device, so the ladder is subject to the same dither as the design it
    brackets.
    """
    from . import s05_layout

    cfg = design.reticle.split
    sep = _min_separation(design)
    cells, described = [], []
    for i, value in enumerate(cfg.values):
        variant = design.model_copy(deep=True)
        set_dotted(variant, cfg.parameter, float(value))

        # Opening the post gap moves the posts outward, toward the electrodes.
        # A ladder drawn to bracket kappa therefore walks into the metal-to-guide
        # rule at its weak-coupling end, which is the end the ladder exists to
        # reach. The electrode gap is widened by the amount the rule requires and
        # the adjustment is reported, since it changes the overlap on that copy
        # and the copy is no longer the design with one parameter moved.
        widened = None
        if sep > 0:
            g = process.geometry(variant, "drawn")
            need = 2.0 * (g.wg_top_width_um / 2 + g.post_gap_um + g.post_width_um + sep)
            if need > g.electrode_gap_um:
                widened = round(need, 4)
                variant.electrodes.gap_um = widened

        polys = s05_layout.build_polygons(variant, ctx)
        polys, _ = s05_layout.snap_polygons(polys, design.process.grid_nm)

        name = f"{design.layout.cell_name}_S{i:02d}"
        cell = layout.create_cell(name)
        for layer, plist in polys.items():
            _insert(cell, layout, lmap, layer, plist)
        cells.append(cell)
        described.append({
            "index": i,
            "cell": name,
            "parameter": cfg.parameter,
            "value": float(value),
            "electrode_gap_widened_to_um": widened,
            "extent_um": [cell.dbbox().width(), cell.dbbox().height()],
        })
    return cells, described


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.reticle
    if not cfg.enabled:
        payload = {"enabled": False}
        ctx.put("reticle", payload)
        return payload

    lay_info = ctx.get("layout") or {}
    device_gds = lay_info.get("gds")
    if not device_gds:
        raise RuntimeError("stage 'reticle' requires stage 'layout'")

    import klayout.db as db

    lmap = design.layout.layer_map
    layout = db.Layout()
    layout.dbu = DBU

    # the device, imported as a cell and instanced rather than flattened, so
    # that the die remains readable and the device can be replaced in isolation
    device_layout = db.Layout()
    device_layout.read(str(device_gds))
    src_top = device_layout.top_cell()
    device_cell = layout.create_cell(src_top.name)
    device_cell.copy_tree(src_top)
    dev_box = device_cell.dbbox()

    die = layout.create_cell(f"{design.layout.cell_name}_DIE")

    # --- the split ladder, placed below the primary device ----------------
    split_cells, split_desc = ([], [])
    if cfg.split.enabled and cfg.split.values:
        split_cells, split_desc = _split_cells(design, ctx, layout, lmap)
    split_pitch = cfg.split.pitch_um or (dev_box.height() + 60.0)
    split_h = len(split_cells) * split_pitch if split_cells else 0.0
    split_w = max((c.dbbox().width() for c in split_cells), default=0.0)

    # --- monitors, placed below the device ------------------------------
    mon_polys, mon_desc = ({}, [])
    if cfg.monitors.enabled:
        mon_polys, mon_desc = _build_monitors(design, ctx)

    mon_height = 0.0
    mon_width = 0.0
    for plist in mon_polys.values():
        for p in plist:
            ys = [y for _, y in p]
            xs = [x for x, _ in p]
            mon_height = max(mon_height, -min(ys))
            mon_width = max(mon_width, max(xs))

    # --- floor plan ------------------------------------------------------
    m = cfg.margin_um
    content_w = max(dev_box.width(), mon_width, split_w)
    monitor_gap = 150.0 if mon_desc else 0.0
    content_h = dev_box.height() + split_h + monitor_gap + mon_height

    # Every band between the content and the sawn edge is deducted here, or the
    # die comes out larger than it was declared. The seal-ring clearance was
    # omitted until 2026-08-09, and since the ring is placed that far outside the
    # floor plan the deficit reappeared on the emitted die: a declared
    # 20200 x 5050 um was written as 20320 x 5170. Nothing reported it, no
    # boundary being drawn against which a footprint could be checked. On a
    # process offering a fixed set of die sizes that is a refusal at submission.
    bands = m + cfg.seal_ring.clearance_um + cfg.seal_ring.width_um + cfg.dicing_lane_um
    inner_w = cfg.die_width_um - 2 * bands if cfg.die_width_um else content_w
    inner_h = cfg.die_height_um - 2 * bands if cfg.die_height_um else content_h
    if inner_w < content_w or inner_h < content_h:
        raise RuntimeError(
            f"the declared die of {cfg.die_width_um} x {cfg.die_height_um} um leaves "
            f"{inner_w:.0f} x {inner_h:.0f} um inside the frame, against content of "
            f"{content_w:.0f} x {content_h:.0f} um. Enlarge the die, or reduce the monitors"
        )

    seal_clear = cfg.seal_ring.clearance_um
    ring_in_x0 = -m - seal_clear
    ring_in_y1 = m + seal_clear
    ring_in_x1 = ring_in_x0 + inner_w + 2 * (m + seal_clear)
    ring_in_y0 = ring_in_y1 - inner_h - 2 * (m + seal_clear)

    sw = cfg.seal_ring.width_um if cfg.seal_ring.enabled else 0.0
    die_x0, die_y0 = ring_in_x0 - sw, ring_in_y0 - sw
    die_x1, die_y1 = ring_in_x1 + sw, ring_in_y1 + sw

    counts: dict[str, int] = {}

    def add(layer, polys, dx=0.0, dy=0.0):
        n = _insert(die, layout, lmap, layer, polys, dx, dy)
        if n:
            counts[layer] = counts.get(layer, 0) + n

    # place the device at the top-left of the content area
    die.insert(db.DCellInstArray(
        device_cell.cell_index(),
        db.DTrans(db.DVector(-dev_box.left, ring_in_y1 - m - dev_box.top)),
    ))
    dev_dy = ring_in_y1 - m - dev_box.top

    # the ladder below it, one copy per value, each labelled with the value it
    # carries so that a returned die can be identified under a microscope
    split_top = dev_dy + dev_box.bottom
    for k, (cell, desc) in enumerate(zip(split_cells, split_desc)):
        box = cell.dbbox()
        dy = split_top - k * split_pitch - 40.0 - box.top
        die.insert(db.DCellInstArray(
            cell.cell_index(), db.DTrans(db.DVector(-box.left, dy))))
        desc["placed_y_um"] = dy
        if cfg.split.label_each:
            text = f"{desc['parameter'].split('.')[-1]}={desc['value']:g}"
            reg = _text_polygons(text, cfg.split.label_height_um)
            tb = reg.bbox()
            polys = [[(pt.x * DBU, pt.y * DBU) for pt in poly.each_point_hull()]
                     for poly in reg.each_merged()]
            add("LABEL", polys, -box.left - tb.left * DBU - 260.0,
                dy + box.top - tb.bottom * DBU + 8.0)

    # monitors below the ladder
    mon_dy = split_top - split_h - monitor_gap
    for layer, plist in mon_polys.items():
        add(layer, plist, -dev_box.left, mon_dy)

    # --- the frame -------------------------------------------------------
    if cfg.seal_ring.enabled:
        ring = monitors.seal_ring(x0=die_x0, y0=die_y0, x1=die_x1, y1=die_y1, width_um=sw)
        for layer in cfg.seal_ring.layers:
            add(layer, ring)

    lane = cfg.dicing_lane_um
    if lane > 0:
        add("DICE", monitors.seal_ring(
            x0=die_x0 - lane, y0=die_y0 - lane, x1=die_x1 + lane, y1=die_y1 + lane,
            width_um=lane,
        ))

    if cfg.marks.enabled:
        # one figure per lithographic level, nested rather than superimposed
        levels = {
            layer: monitors.alignment_mark(
                size_um=cfg.marks.size_um, arm_width_um=cfg.marks.arm_width_um,
                level=i, n_levels=len(cfg.marks.layers),
                clearance_um=cfg.marks.clearance_um,
            )
            for i, layer in enumerate(cfg.marks.layers)
        }
        inset = cfg.marks.size_um / 2 + 10.0
        positions = {
            "SW": (ring_in_x0 + inset, ring_in_y0 + inset),
            "SE": (ring_in_x1 - inset, ring_in_y0 + inset),
            "NW": (ring_in_x0 + inset, ring_in_y1 - inset),
            "NE": (ring_in_x1 - inset, ring_in_y1 - inset),
        }
        for corner in cfg.marks.corners:
            if corner not in positions:
                raise ValueError(f"unknown mark corner {corner!r}; use SW, SE, NW or NE")
            px, py = positions[corner]
            for layer, figure in levels.items():
                add(layer, figure, px, py)
            # the composite, so that the whole mark is one drawing on one layer.
            # Suppressed where the layer named is already one of the levels, the
            # composite being an inspection aid rather than a drawn level.
            comp = cfg.marks.composite_layer
            if comp and comp not in levels:
                for figure in levels.values():
                    add(comp, figure, px, py)

    # --- the die label ---------------------------------------------------
    label_text = f"{cfg.label or design.meta.name} REV{cfg.revision}".upper()
    region = _text_polygons(label_text, cfg.label_height_um)
    tbox = region.bbox()
    # The label is placed along the bottom edge, centred, and clear of the mark
    # field. Placing it in the corner collides with the corner mark, and since
    # the label is repeated in metal that collision is a short between metal and
    # the guide layer rather than a cosmetic overlap.
    mark_field = (cfg.marks.size_um + 40.0) if cfg.marks.enabled else 0.0
    text_w = tbox.width() * DBU
    tx = (ring_in_x0 + ring_in_x1) / 2 - text_w / 2 - tbox.left * DBU
    ty = ring_in_y0 + mark_field + 20.0 - tbox.bottom * DBU
    if text_w > (ring_in_x1 - ring_in_x0) - 40.0:
        raise RuntimeError(
            f"the die label {label_text!r} is {text_w:.0f} um wide and does not fit "
            f"inside {ring_in_x1 - ring_in_x0:.0f} um. Shorten reticle.label or reduce "
            "reticle.label_height_um"
        )
    label_polys = [[(p.x * DBU, p.y * DBU) for p in poly.each_point_hull()]
                   for poly in region.each_merged()]
    for layer in cfg.label_layers:
        add(layer, label_polys, tx, ty)

    # --- the chip frame ---------------------------------------------------
    # A rule deck asks two things of a die that a device cell cannot answer:
    # whether the footprint is one the process offers, and whether anything sits
    # where the process forbids it. Both are asked of an outer boundary and a
    # usable area inset from it, and neither exists until it is drawn. The chain
    # drew a seal ring and a dicing lane and no such pair until 2026-08-08, so
    # those rules were silent on every die it emitted, and silence there reads as
    # compliance.
    frame: dict[str, Any] = {"enabled": False}
    if cfg.chip_frame.enabled:
        import klayout.db as db

        emitted_w = die_x1 - die_x0 + 2 * lane
        emitted_h = die_y1 - die_y0 + 2 * lane
        outer_w = cfg.die_width_um or emitted_w
        outer_h = cfg.die_height_um or emitted_h
        if outer_w + 1e-6 < emitted_w or outer_h + 1e-6 < emitted_h:
            raise RuntimeError(
                f"the declared die of {outer_w:.1f} x {outer_h:.1f} um is smaller "
                f"than the {emitted_w:.1f} x {emitted_h:.1f} um the frame and its "
                "contents occupy. The chip boundary cannot be drawn inside them"
            )

        # The boundary is required to sit on the origin, so the die is moved to
        # it rather than the boundary moved to wherever the content landed.
        cx = 0.5 * ((die_x0 - lane) + (die_x1 + lane))
        cy = 0.5 * ((die_y0 - lane) + (die_y1 + lane))
        die.transform(db.DTrans(db.DVector(-cx, -cy)))

        ez = cfg.chip_frame.exclusion_zone_um
        hw, hh = outer_w / 2.0, outer_h / 2.0
        add("CHIP_OUTER", [[(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]])
        add("CHIP_INNER", [[(-hw + ez, -hh + ez), (hw - ez, -hh + ez),
                            (hw - ez, hh - ez), (-hw + ez, hh - ez)]])

        allowed = cfg.chip_frame.allowed_edges_um
        tol = cfg.chip_frame.edge_tolerance_um
        if allowed:
            bad = [e for e in (outer_w, outer_h)
                   if not any(abs(e - a) <= tol for a in allowed)]
            if bad:
                ctx.warn(
                    f"the die edges {outer_w:.1f} x {outer_h:.1f} um are not among "
                    f"the footprints the process offers, {allowed}. The frame is "
                    "drawn as declared and the deck will report it"
                )
        else:
            ctx.warn(
                "reticle.chip_frame.allowed_edges_um is empty, so the footprint "
                "was not checked. A process offers a fixed set of die sizes and "
                "an unchecked footprint is an assumption"
            )

        frame = {
            "enabled": True,
            "outer_um": [outer_w, outer_h],
            "inner_um": [outer_w - 2 * ez, outer_h - 2 * ez],
            "exclusion_zone_um": ez,
            "centred_on_origin": True,
            "translated_by_um": [-cx, -cy],
            "allowed_edges_um": allowed,
            "footprint_is_offered": bool(allowed) and all(
                any(abs(e - a) <= tol for a in allowed) for e in (outer_w, outer_h)
            ),
        }

    gds = ctx.run_dir / f"{design.meta.name}.die.gds"
    ctx.ensure()
    layout.write(str(gds))

    payload = {
        "enabled": True,
        "gds": str(gds),
        "cell_name": die.name,
        "die_width_um": die_x1 - die_x0 + 2 * lane,
        "die_height_um": die_y1 - die_y0 + 2 * lane,
        "chip_frame": frame,
        "device_extent_um": [dev_box.width(), dev_box.height()],
        "seal_ring_width_um": sw,
        "dicing_lane_um": lane,
        "label": label_text,
        "alignment_marks": len(cfg.marks.corners) if cfg.marks.enabled else 0,
        "mark_layers": cfg.marks.layers if cfg.marks.enabled else [],
        # the device is an instance rather than a copy, so these count only
        # what this stage added: the frame, the label and the monitors
        "polygon_counts": counts,
        "split": {
            "enabled": bool(cfg.split.enabled and cfg.split.values),
            "parameter": cfg.split.parameter,
            "copies": len(split_desc),
            "rows": split_desc,
        },
        "devices_on_die": 1 + len(split_desc),
        "monitors": mon_desc,
        "monitor_structures": len(mon_desc),
        "fill_placed": False,
    }
    ctx.put("reticle", payload)
    ctx.write_stage("reticle", payload)

    widened = [r for r in split_desc if r.get("electrode_gap_widened_to_um")]
    if widened:
        ctx.warn(
            "the split ladder required the electrode gap to be widened on "
            + ", ".join(f"{r['cell']} ({r['value']:g} um post gap -> "
                        f"{r['electrode_gap_widened_to_um']:g} um electrode gap)"
                        for r in widened)
            + ". Opening the post gap moves the posts toward the electrodes, so those "
            "copies differ from the primary device in two parameters rather than one "
            "and their electro-optic overlap is lower"
        )

    for m in mon_desc:
        raised = m.get("gaps_raised_to_the_rule") or []
        if raised:
            ctx.warn(
                f"the {m['structure']} could not be drawn at every gap requested: "
                + ", ".join(f"{r['requested_um']:.2f} um raised to {r['drawn_um']:.2f}"
                            for r in raised)
                + f". The metal-to-guide rule of {m['separation_floor_um']:.2f} um sets "
                "the floor, so the tightest gap the design uses is not measured by "
                "this monitor"
            )
    if not mon_desc:
        ctx.warn(
            "the die carries no process control structures. A returned wafer on which "
            "a metric disagrees with prediction cannot then be attributed to the "
            "lithography, to the etch or to the model"
        )
    if not cfg.seal_ring.enabled:
        ctx.warn("the die carries no seal ring; most processes refuse such a submission")
    if not design.mask.fill.enabled:
        ctx.warn(
            "no fill is placed. The mask stage sizes the shortfall and will place it "
            "where mask.fill declares a pattern, a pitch and an exclusion; those three "
            "figures are a foundry statement and none is declared here"
        )
    return payload
