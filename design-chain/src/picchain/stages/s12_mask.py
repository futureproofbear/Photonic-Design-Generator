"""Stage 12 - mask verification beyond geometry: density, fill and connectivity.

A design rule check asks whether each shape is legal. Three questions remain
that it does not ask, and each of them stops a fabrication run.

**Density.** Etch and deposition rates depend on how much of the local area is
patterned. A foundry states a window, typically per layer over a tile of a few
hundred micrometres, and a mask outside it prints differently from the drawing.
The remedy is fill, which this stage sizes rather than places: it reports the
area each deficient tile requires.

**Connectivity.** That two electrodes are drawn does not mean each reaches its
pad, nor that a waveguide is one guide rather than two that nearly touch. The
shapes are merged and the connected regions counted, so a break announces itself
as a change in that count rather than as a dark chip.

**Isolation.** Layers that must not touch are checked for the short a misplaced
polygon creates.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..artifacts import RunContext
from ..config import Design
from ..materials import MaterialLibrary
from ._target import resolve_target


def _regions(layout, layer_map, names):
    import klayout.db as db

    top = layout.top_cell()
    out = {}
    for name in names:
        if name not in layer_map:
            continue
        li, ld = layer_map[name]
        idx = layout.find_layer(li, ld)
        out[name] = db.Region(top.begin_shapes_rec(idx)) if idx is not None else db.Region()
    return out


def _extract_netlist(layout, layer_map, cfg) -> dict[str, Any]:
    """Connectivity as nets rather than as a count per layer.

    Merging one layer and counting the islands answers whether that layer is
    broken. It does not answer whether a pad reaches the electrode it is meant
    to drive, those being two shapes on two layers that touch. Extraction
    resolves both questions at once, and it resolves them the way a foundry
    does.

    Layer pairs named in ``joined_layers`` are treated as electrically joined
    where they overlap. Everything else is isolated, so an unintended overlap
    presents as a net count lower than expected.
    """
    import klayout.db as db

    top = layout.top_cell()
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(layout, top, []))
    layers = {}
    for name in cfg.connected_layers:
        if name not in layer_map:
            continue
        li, ld = layer_map[name]
        idx = layout.layer(li, ld)
        layers[name] = l2n.make_polygon_layer(idx, name)
    if not layers:
        return {"performed": False, "reason": "no named layer is present in the layer map"}

    # Text on the label layer names the net it sits on, which is what turns an
    # anonymous count into a circuit that can be compared against an intention.
    label_name = getattr(cfg, "label_layer", None)
    texts = None
    if label_name and label_name in layer_map:
        idx = layout.find_layer(*layer_map[label_name])
        if idx is not None:
            texts = l2n.make_text_layer(idx, label_name)

    for r in layers.values():
        l2n.connect(r)
    text_index = None
    if texts is not None:
        for r in layers.values():
            l2n.connect(r, texts)
        text_index = l2n.layer_index(texts)
    joined = []
    for pair in cfg.joined_layers:
        a, b = pair[0], pair[1]
        if a in layers and b in layers:
            l2n.connect(layers[a], layers[b])
            joined.append([a, b])

    l2n.extract_netlist()
    netlist = l2n.netlist()
    nets: list[dict[str, Any]] = []
    for circuit in netlist.each_circuit():
        for net in circuit.each_net():
            entry = {"circuit": circuit.name, "name": net.expanded_name()}
            if text_index is not None:
                entry["labels"] = sorted(
                    {t.string for t in l2n.texts_of_net(net, text_index).each()})
            else:
                entry["labels"] = []
            nets.append(entry)
    return {
        "performed": True,
        "joined_layers": joined,
        "layers_extracted": sorted(layers),
        "net_count": len(nets),
        "named_nets": [n for n in nets if n["labels"]],
        "nets": nets[:64],
    }


def _density(regions, windows, tile_um, bbox, dbu, extra_layer=None) -> dict[str, Any]:
    """Area fraction per layer, tile by tile, with the shortfall summed.

    ``extra_layer`` names a layer whose area counts toward the window as well as
    the layer itself, which is how fill is credited once it has been placed.
    """
    import klayout.db as db

    nx = max(1, int(np.ceil(bbox.width() / tile_um)))
    ny = max(1, int(np.ceil(bbox.height() / tile_um)))
    out: dict[str, Any] = {}
    for window in windows:
        name, lo, hi = window[0], float(window[1]), float(window[2])
        r = regions.get(name)
        if r is None:
            continue
        if extra_layer and regions.get(extra_layer) is not None:
            r = (r + regions[extra_layer]).merged()
        worst_low, worst_high = 1.0, 0.0
        deficit, tiles_low, tiles_high = 0.0, 0, 0
        for i in range(nx):
            for j in range(ny):
                x0 = bbox.left + i * tile_um
                y0 = bbox.bottom + j * tile_um
                box = db.DBox(x0, y0, min(x0 + tile_um, bbox.right),
                              min(y0 + tile_um, bbox.top))
                area = box.width() * box.height()
                if area <= 0:
                    continue
                clip = db.Region(db.DPolygon(box).to_itype(dbu))
                frac = (float((r & clip).area()) * dbu * dbu) / area
                worst_low = min(worst_low, frac)
                worst_high = max(worst_high, frac)
                if frac < lo:
                    tiles_low += 1
                    deficit += (lo - frac) * area
                if frac > hi:
                    tiles_high += 1
        out[name] = {
            "window": [lo, hi],
            "tile_um": tile_um,
            "tiles": nx * ny,
            "minimum_density": worst_low,
            "maximum_density": worst_high,
            "tiles_below_window": tiles_low,
            "tiles_above_window": tiles_high,
            "fill_area_required_um2": deficit,
        }
    return out


def _place_fill(layout, layer_map, cfg, density, bbox, tile_um) -> dict[str, Any]:
    """Place the fill the density windows require, and report what it cost.

    The shortfall was already sized. Placing it needs three figures a foundry
    states: the element, its pitch, and how far it must stand off each feature.
    The lattice is generated across each deficient tile and then cut by the
    exclusion around every named layer, so nothing is placed against a guide or
    a pad.

    Filling stops at the minimum of the window. Filling past it wastes area, and
    on a guide layer it adds a scattering surface for no benefit.
    """
    import klayout.db as db

    top = layout.top_cell()
    dbu = layout.dbu
    if cfg.layer not in layer_map:
        raise ValueError(
            f"mask.fill.layer is {cfg.layer!r}, which is not in layout.layer_map"
        )

    keep_out = db.Region()
    for name, clearance in cfg.exclusion_um.items():
        if name not in layer_map or clearance <= 0:
            continue
        idx = layout.find_layer(*layer_map[name])
        if idx is None:
            continue
        keep_out += db.Region(top.begin_shapes_rec(idx)).merged().sized(
            int(round(clearance / dbu)))
    keep_out.merge()

    fill_idx = layout.layer(*layer_map[cfg.layer])
    placed = 0
    area_placed = 0.0
    per_layer: dict[str, dict[str, Any]] = {}

    for name, d in density.items():
        if not d.get("tiles_below_window"):
            continue
        target_idx = layout.find_layer(*layer_map[name]) if name in layer_map else None
        existing = (db.Region(top.begin_shapes_rec(target_idx)).merged()
                    if target_idx is not None else db.Region())
        lo = float(d["window"][0])
        n_tiles = 0
        nx = max(1, int(np.ceil(bbox.width() / tile_um)))
        ny = max(1, int(np.ceil(bbox.height() / tile_um)))
        for i in range(nx):
            for j in range(ny):
                x0 = bbox.left + i * tile_um
                y0 = bbox.bottom + j * tile_um
                box = db.DBox(x0, y0, min(x0 + tile_um, bbox.right),
                              min(y0 + tile_um, bbox.top))
                area = box.width() * box.height()
                if area <= 0:
                    continue
                clip = db.Region(db.DPolygon(box).to_itype(dbu))
                have = float((existing & clip).area()) * dbu * dbu
                need = lo * area - have
                if need <= 0:
                    continue

                candidates = db.Region()
                k = 0
                fx = x0 + cfg.pitch_um / 2
                while fx < box.right:
                    fy = y0 + cfg.pitch_um / 2
                    while fy < box.top:
                        candidates.insert(db.DBox(
                            fx - cfg.size_um / 2, fy - cfg.size_um / 2,
                            fx + cfg.size_um / 2, fy + cfg.size_um / 2).to_itype(dbu))
                        fy += cfg.pitch_um
                    fx += cfg.pitch_um
                usable = (candidates - keep_out).merged()
                if usable.is_empty():
                    continue

                # take elements until the window is satisfied
                taken = db.Region()
                got = 0.0
                for poly in usable.each():
                    if cfg.stop_at_minimum and got >= need:
                        break
                    taken.insert(poly)
                    got += float(poly.area()) * dbu * dbu
                    k += 1
                top.shapes(fill_idx).insert(taken)
                placed += k
                area_placed += got
                n_tiles += 1
        per_layer[name] = {"tiles_filled": n_tiles}

    return {
        "performed": True,
        "layer": cfg.layer,
        "elements_placed": placed,
        "area_placed_um2": area_placed,
        "by_layer": per_layer,
    }


def _compare_schematic(netlist: dict, schematic) -> dict[str, Any]:
    """The extracted connectivity against the circuit that was intended.

    This is layout versus schematic without device recognition. It establishes
    that the things declared to be one net are one net, and that the things
    declared separate are separate. It does not establish what the connected
    thing is; no device is recognised, so a short through the wrong component
    would present as a correct net.
    """
    if not schematic:
        return {"performed": False, "reason": "no schematic declared"}
    if not netlist.get("performed"):
        return {"performed": False, "reason": "no netlist was extracted"}

    by_label: dict[str, str] = {}
    for net in netlist.get("named_nets", netlist.get("nets", [])):
        for label in net.get("labels", []):
            by_label[label] = net["name"]

    rows = []
    ok = True
    for want in schematic:
        found = {lab: by_label.get(lab) for lab in want.labels}
        missing = [lab for lab, net in found.items() if net is None]
        nets = {net for net in found.values() if net is not None}
        joined = len(nets) <= 1 and not missing
        if not joined:
            ok = False
        rows.append({
            "net": want.name,
            "labels": want.labels,
            "labels_not_found": missing,
            "extracted_nets": sorted(nets),
            "joined": joined,
        })

    # two declared nets sharing an extracted net is a short between them
    owner: dict[str, str] = {}
    shorts = []
    for row in rows:
        for net in row["extracted_nets"]:
            if net in owner and owner[net] != row["net"]:
                shorts.append([owner[net], row["net"]])
                ok = False
            owner[net] = row["net"]

    return {
        "performed": True,
        "matches": ok,
        "rows": rows,
        "shorted_pairs": shorts,
        "note": "connectivity only; no device recognition is performed",
    }


def run(design: Design, ctx: RunContext, lib: MaterialLibrary) -> dict[str, Any]:
    cfg = design.mask
    if not cfg.enabled:
        ctx.put("mask", {"enabled": False})
        return {"enabled": False}

    gds_path, checked = resolve_target(design, ctx, "mask")

    import klayout.db as db

    layout = db.Layout()
    layout.read(str(gds_path))
    top = layout.top_cell()
    bbox = top.dbbox()
    dbu = layout.dbu
    layer_map = design.layout.layer_map
    regions = _regions(layout, layer_map, list(layer_map))

    # ---- connectivity -------------------------------------------------
    connectivity = {}
    for name in cfg.connected_layers:
        r = regions.get(name)
        if r is None:
            continue
        merged = r.dup()
        merged.merge()
        connectivity[name] = {
            "drawn_polygons": int(r.count()),
            "connected_regions": int(merged.count()),
            "area_um2": float(merged.area()) * dbu * dbu,
        }

    # ---- isolation ----------------------------------------------------
    shorts = {}
    for pair in cfg.must_not_touch:
        a, b = pair[0], pair[1]
        ra, rb = regions.get(a), regions.get(b)
        if ra is None or rb is None:
            continue
        overlap = ra & rb
        shorts[f"{a}-{b}"] = {
            "overlapping_polygons": int(overlap.count()),
            "overlap_area_um2": float(overlap.area()) * dbu * dbu,
        }

    # ---- density, tile by tile ----------------------------------------
    density = _density(regions, cfg.density_windows, cfg.density_tile_um, bbox, dbu)

    # ---- connectivity as nets -----------------------------------------
    netlist: dict[str, Any] = {"performed": False, "reason": "not requested"}
    if cfg.extract_netlist:
        try:
            netlist = _extract_netlist(layout, layer_map, cfg)
        except Exception as exc:  # pragma: no cover - backend specific
            netlist = {"performed": False, "reason": f"extraction raised: {exc}"}

    fill = {"performed": False, "reason": "not requested"}
    filled_gds = None
    if cfg.fill.enabled and any(d.get("tiles_below_window") for d in density.values()):
        try:
            fill = _place_fill(layout, layer_map, cfg.fill, density, bbox,
                               cfg.density_tile_um)
            filled_gds = str(gds_path).replace(".gds", ".filled.gds")
            layout.write(filled_gds)
            # the density the filled mask actually carries, re-measured
            regions_after = _regions(layout, layer_map, list(layer_map))
            fill["density_after"] = _density(
                regions_after, cfg.density_windows, cfg.density_tile_um, bbox,
                dbu, cfg.fill.layer)
        except Exception as exc:  # pragma: no cover - backend specific
            fill = {"performed": False, "reason": f"fill raised: {exc}"}

    lvs = _compare_schematic(netlist, cfg.schematic)

    payload = {
        "enabled": True,
        "gds": str(gds_path),
        "filled_gds": filled_gds,
        "fill": fill,
        "lvs": lvs,
        "checked": checked,
        "extent_um": [bbox.width(), bbox.height()],
        "connectivity": connectivity,
        "netlist": netlist,
        "net_count": netlist.get("net_count"),
        "isolation": shorts,
        "density": density,
        "note_fill": "fill area is sized here, not placed; placement is a layout decision",
    }
    ctx.put("mask", payload)
    ctx.write_stage("mask", payload)

    # The expectations are per scale. A die carries the frame, the monitors and
    # the split ladder in addition to the device, so a device-level figure
    # compared against it reports a difference that is not a defect. Both sets
    # may be declared, and the one describing what was actually checked is used.
    if checked == "die":
        want_regions = cfg.expected_regions_die
        want_nets = cfg.expected_nets_die
        other = bool(cfg.expected_regions) or cfg.expected_nets is not None
    else:
        want_regions = (cfg.expected_regions
                        if cfg.expectations_describe == "device" else {})
        want_nets = cfg.expected_nets
        other = bool(cfg.expected_regions_die) or cfg.expected_nets_die is not None

    if not want_regions and want_nets is None and other:
        ctx.warn(
            f"the {checked} was checked and no expectation is declared for it, "
            "though one is declared for the other scale. The comparison was not "
            f"made. Declare mask.expected_regions"
            f"{'_die' if checked == 'die' else ''} and the matching net count, or "
            "set mask.target to the layout the declared figures describe"
        )
    for name, c in connectivity.items():
        expected = want_regions.get(name)
        if expected is not None and c["connected_regions"] != expected:
            ctx.warn(
                f"layer {name} merges into {c['connected_regions']} connected regions "
                f"against the {expected} expected on the {checked}. More than "
                "expected is a break; fewer is a short"
            )
    if netlist.get("performed") and want_nets is not None:
        found = netlist["net_count"]
        if found != want_nets:
            ctx.warn(
                f"the extraction found {found} nets on the {checked} against the "
                f"{want_nets} expected. A count above the expected figure is a break "
                "in something that was drawn continuous; below it is a short between "
                "two things that were drawn apart"
            )
    for pair, s in shorts.items():
        if s["overlapping_polygons"]:
            ctx.warn(f"{pair} overlap on {s['overlap_area_um2']:.2f} um2, which is a short")
    if lvs.get("performed") and not lvs["matches"]:
        detail = "; ".join(
            f"{r['net']}: " + (f"labels not found {r['labels_not_found']}"
                               if r["labels_not_found"]
                               else f"split across {r['extracted_nets']}")
            for r in lvs["rows"] if not r["joined"])
        ctx.warn(
            f"the extracted connectivity does not match the declared schematic. {detail}"
            + (f". Shorted pairs: {lvs['shorted_pairs']}" if lvs["shorted_pairs"] else "")
        )
    if fill.get("performed"):
        after = fill.get("density_after") or {}
        remaining = sum(v.get("tiles_below_window", 0) for v in after.values())
        ctx.warn(
            f"{fill['elements_placed']} fill elements were placed on layer "
            f"{fill['layer']}, covering {fill['area_placed_um2']:.0f} um2. "
            + (f"{remaining} tiles remain below their window; the exclusion around the "
               "existing features leaves no room for more"
               if remaining else "every tile now sits inside its window")
        )

    after = (fill.get("density_after") or {}) if fill.get("performed") else {}
    for name, d in density.items():
        resolved = name in after and not after[name].get("tiles_below_window")
        if resolved and not d["tiles_above_window"]:
            continue                      # the fill placed below satisfied it
        if d["tiles_below_window"] or d["tiles_above_window"]:
            ctx.warn(
                f"{name} density leaves {d['tiles_below_window']} tiles below and "
                f"{d['tiles_above_window']} above the window {d['window']}; "
                f"{d['fill_area_required_um2']:.0f} um2 of fill is required"
            )
    return payload
