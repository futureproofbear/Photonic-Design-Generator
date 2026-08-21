"""Process control structures, as polygon lists.

A reticle carrying only the device measures nothing. When the wafer returns,
every quantity that disagrees with prediction has at least three candidate
causes, and no structure on the mask separates them. The structures here each
isolate one.

The case for them on this class of device is quantitative rather than
procedural. The coupling constant of a side-coupled grating decays at roughly
5.4 µm⁻¹ with the separation, so a 20 nm lithographic error is an 11 % error in
κ. Across an ordinary process window the continuous tuning range of the
validation baseline moves by a factor of five while the Bragg wavelength moves
by under one per cent. A first fabrication run that measures none of this
returns a device that works or does not, and no information about why.

What each structure isolates
----------------------------
``kappa_ladder``
    Gratings identical but for the post gap, stepped across the window. The
    measured reflectivity against gap gives dκ/d(gap) on the delivered process,
    which replaces the modelled sensitivity. It also locates the gap at which
    the printed structure reaches the intended κ, which is the trim the
    validation record calls for.
``loss_cutback``
    Straight guides of several lengths. The slope of transmission against
    length is the propagation loss with the coupling loss eliminated, that being
    the common intercept. The guides are drawn straight rather than folded, so
    that no bend loss enters the slope.
``cd_vernier``
    Line and space arrays at stepped widths, equal line to space. Measured
    against the drawn dimension they give the lateral bias directly, which is
    the quantity ``picchain.process`` otherwise has to be told. This structure
    is what converts ``process.bias_um`` from an assumption into a measurement.
``electrode_ladder``
    Electrode pairs at stepped gaps over a straight guide. The tuning measured
    against gap gives the electro-optic overlap against gap on the delivered
    film, the overlap being the factor by which a material coefficient becomes a
    volts figure.

Every builder returns ``(polygons, description)``. Polygons are keyed by layer
name and expressed in micrometres about a local origin at the left-hand end, on
the guide axis. The description is written into the metric tree, so that the
reticle states what it measures and a returned wafer can be read against it.
"""

from __future__ import annotations

from typing import Any


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _blank() -> dict[str, list]:
    return {"WG": [], "METAL": [], "PAD": [], "LABEL": []}


def kappa_ladder(
    *,
    gaps_um: list[float],
    period_um: float,
    n_periods: int,
    wg_width_um: float,
    post_width_um: float,
    post_length_um: float,
    row_pitch_um: float,
    lead_um: float = 40.0,
) -> tuple[dict[str, list], dict[str, Any]]:
    """Gratings differing only in the post gap.

    Every other dimension is held, so that the reflectivity measured across the
    set is a function of the gap alone. The number of periods is well below the
    device figure, the purpose being a measurable reflectivity rather than a
    mirror.
    """
    polys = _blank()
    length = n_periods * period_um
    rows = []
    for i, gap in enumerate(sorted(gaps_um)):
        y0 = -i * row_pitch_um
        polys["WG"].append(
            _rect(0.0, y0 - wg_width_um / 2, length + 2 * lead_um, y0 + wg_width_um / 2)
        )
        inner = wg_width_um / 2 + gap
        for k in range(n_periods):
            xc = lead_um + (k + 0.5) * period_um
            for sgn in (-1.0, 1.0):
                yc = y0 + sgn * (inner + post_width_um / 2)
                polys["WG"].append(
                    _rect(xc - post_length_um / 2, yc - post_width_um / 2,
                          xc + post_length_um / 2, yc + post_width_um / 2)
                )
        rows.append({"gap_um": float(gap), "y_um": float(y0), "n_periods": int(n_periods),
                     "length_um": float(length)})
    return polys, {
        "structure": "kappa_ladder",
        "measures": "kappa against post gap, on the delivered process",
        "rows": rows,
        "extent_um": [0.0, length + 2 * lead_um],
        "height_um": (len(rows) - 1) * row_pitch_um if rows else 0.0,
    }


def coherence_ladder(
    *,
    lengths_um: list[float],
    gap_um: float,
    period_um: float,
    wg_width_um: float,
    post_width_um: float,
    post_length_um: float,
    row_pitch_um: float,
    lead_um: float = 40.0,
) -> tuple[dict[str, list], dict[str, Any]]:
    """Gratings differing only in length, by which phase coherence is measured.

    Every dimension but the length is held, so the reflectivity measured across
    the set is a function of the length alone. Coupled-mode theory says it
    follows tanh^2(kappa L) and saturates. **A grating that loses phase along
    its own length departs from that curve**: the reflectivity stops rising
    where the accumulated Bragg detuning reaches a radian or so, and the stop
    band broadens instead of narrowing.

    This is the one process quantity a post-gap ladder cannot reach, because
    every copy of that ladder sits on the same film and sees the same gradient.
    The lengths are to span from well inside the coherence budget to well past
    it, so the departure has somewhere to show.

    The structures are passive and carry no electrode, so the set is thin in y
    and sits in the monitor field rather than taking a device slot.
    """
    polys = _blank()
    rows = []
    y = 0.0
    longest = max(lengths_um) if lengths_um else 0.0
    for i, L in enumerate(sorted(lengths_um)):
        n = int(L // period_um)
        y0 = -i * row_pitch_um
        polys["WG"].append(
            _rect(0.0, y0 - wg_width_um / 2, longest + 2 * lead_um, y0 + wg_width_um / 2)
        )
        inner = wg_width_um / 2 + gap_um
        for k in range(n):
            xc = lead_um + (k + 0.5) * period_um
            for sgn in (-1.0, 1.0):
                yc = y0 + sgn * (inner + post_width_um / 2)
                polys["WG"].append(
                    _rect(xc - post_length_um / 2, yc - post_width_um / 2,
                          xc + post_length_um / 2, yc + post_width_um / 2)
                )
        rows.append({"length_um": float(n * period_um), "n_periods": int(n),
                     "y_um": float(y0)})
        y = y0
    return polys, {
        "structure": "coherence_ladder",
        "measures": (
            "reflectivity and stop band against grating length, by which phase "
            "coherence along a long mirror is separated from kappa"
        ),
        "rows": rows,
        "gap_um": float(gap_um),
        "extent_um": [0.0, longest + 2 * lead_um],
        "height_um": abs(y),
    }


def loss_cutback(
    *,
    lengths_um: list[float],
    wg_width_um: float,
    row_pitch_um: float,
) -> tuple[dict[str, list], dict[str, Any]]:
    """Straight guides of several lengths, for a cut-back measurement.

    The guides are straight. A folded structure fits into less area and
    introduces bend loss into the slope, which is the quantity being measured.
    """
    polys = _blank()
    rows = []
    for i, L in enumerate(sorted(lengths_um)):
        y0 = -i * row_pitch_um
        polys["WG"].append(_rect(0.0, y0 - wg_width_um / 2, L, y0 + wg_width_um / 2))
        rows.append({"length_um": float(L), "y_um": float(y0)})
    longest = max(lengths_um) if lengths_um else 0.0
    return polys, {
        "structure": "loss_cutback",
        "measures": "propagation loss by the slope, with coupling loss as the intercept",
        "rows": rows,
        "extent_um": [0.0, longest],
        "height_um": (len(rows) - 1) * row_pitch_um if rows else 0.0,
    }


def cd_vernier(
    *,
    widths_um: list[float],
    repeats: int,
    length_um: float,
    row_pitch_um: float,
    min_space_um: float = 0.0,
) -> tuple[dict[str, list], dict[str, Any]]:
    """Line and space arrays at stepped widths.

    A single isolated line measures the bias of an isolated line. A dense array
    measures the bias of a dense one, and the two differ on most processes, so
    each width is drawn as an array at equal line and space.

    ``min_space_um`` is the floor the array is held to. A monitor that violates
    the rule deck cannot be submitted, and a line narrower than the minimum
    space would place one there. The space is therefore widened to the floor at
    the narrow end, and the pitch actually drawn is reported so that a dense
    reading is not taken from an array that is not dense.
    """
    polys = _blank()
    rows = []
    for i, w in enumerate(sorted(widths_um)):
        y0 = -i * row_pitch_um
        space = max(w, float(min_space_um))
        pitch = w + space
        span = repeats * pitch
        for k in range(repeats):
            x0 = k * pitch
            polys["WG"].append(_rect(x0, y0 - length_um / 2, x0 + w, y0 + length_um / 2))
        rows.append({"drawn_width_um": float(w), "space_um": float(space),
                     "pitch_um": float(pitch), "equal_line_space": bool(space == w),
                     "repeats": int(repeats), "span_um": float(span), "y_um": float(y0)})
    widest = max((r["span_um"] for r in rows), default=0.0)
    return polys, {
        "structure": "cd_vernier",
        "measures": "printed width against drawn width, giving the lateral bias directly",
        "rows": rows,
        "extent_um": [0.0, widest],
        "height_um": (len(rows) - 1) * row_pitch_um if rows else 0.0,
    }


def electrode_ladder(
    *,
    gaps_um: list[float],
    electrode_width_um: float,
    length_um: float,
    wg_width_um: float,
    pad_um: float,
    row_pitch_um: float,
    min_separation_um: float = 0.0,
) -> tuple[dict[str, list], dict[str, Any]]:
    """Electrode pairs at stepped gaps over a straight guide.

    A monitor is held to the same rule deck as the device. The tightest gap a
    designer would like to probe is frequently below what the metal-to-guide
    separation rule permits, and a monitor field that fails the deck is removed
    before submission, which is the least useful outcome available. Each gap is
    therefore raised to the rule where it falls below it, and every gap so
    raised is reported against the figure requested.

    The row pitch is enlarged where the electrodes are wider than the pitch
    allows, so that adjacent rows do not merge into one another.
    """
    polys = _blank()
    floor = 2.0 * (float(min_separation_um) + wg_width_um / 2)
    resolved = sorted({max(float(g), floor) for g in gaps_um}) if gaps_um else []
    clamped = [
        {"requested_um": float(g), "drawn_um": floor}
        for g in sorted(gaps_um) if float(g) < floor
    ]
    span = max(row_pitch_um,
               2.0 * (max(resolved) / 2 + electrode_width_um + pad_um + 20.0)) \
        if resolved else row_pitch_um
    rows = []
    for i, gap in enumerate(resolved):
        y0 = -i * span
        polys["WG"].append(_rect(0.0, y0 - wg_width_um / 2, length_um, y0 + wg_width_um / 2))
        for sgn in (-1.0, 1.0):
            y_in = y0 + sgn * gap / 2
            y_out = y_in + sgn * electrode_width_um
            polys["METAL"].append(
                _rect(0.0, min(y_in, y_out), length_um, max(y_in, y_out))
            )
            y_pad = y_out + sgn * pad_um
            polys["PAD"].append(
                _rect(length_um / 2 - pad_um / 2, min(y_out, y_pad),
                      length_um / 2 + pad_um / 2, max(y_out, y_pad))
            )
        rows.append({"gap_um": float(gap), "y_um": float(y0),
                     "metal_to_guide_um": (gap - wg_width_um) / 2})
    return polys, {
        "structure": "electrode_ladder",
        "measures": "electro-optic overlap against electrode gap, on the delivered film",
        "rows": rows,
        "gaps_raised_to_the_rule": clamped,
        "separation_floor_um": float(min_separation_um),
        "extent_um": [0.0, length_um],
        "height_um": (len(rows) - 1) * span if rows else 0.0,
        "row_pitch_um": float(span),
    }


def alignment_mark(
    *,
    size_um: float,
    arm_width_um: float,
    level: int = 0,
    n_levels: int = 2,
    clearance_um: float = 3.0,
) -> list[list[tuple[float, float]]]:
    """One level of a box-in-box overlay mark, about the origin.

    The figure differs per level and the levels nest without touching. Level
    zero is the outermost square annulus; each subsequent level sits inside the
    one before it, separated by ``clearance_um``; the innermost is solid.

    Drawing the *same* figure on two levels is the obvious construction and it
    is wrong twice over. The two levels then overlap by their whole area, which
    any layer-to-layer separation rule reports as a short, and the overlay
    cannot be read, there being no gap whose asymmetry carries it. Nesting gives
    a gap on all four sides, and the difference between opposite gaps is the
    registration error directly.
    """
    if level < 0 or level >= max(1, n_levels):
        raise ValueError(f"level {level} is outside the {n_levels} declared")
    step = arm_width_um + clearance_um
    half = size_um / 2 - level * step
    if half <= arm_width_um:
        raise ValueError(
            f"a mark of {size_um} um cannot carry {n_levels} levels at "
            f"{arm_width_um} um arms and {clearance_um} um clearance; level {level} "
            "closes on itself. Enlarge marks.size_um"
        )
    if level == n_levels - 1:                       # the innermost is solid
        return [_rect(-half, -half, half, half)]
    inner = half - arm_width_um
    return [
        _rect(-half, -half, half, -inner),
        _rect(-half, inner, half, half),
        _rect(-half, -inner, -inner, inner),
        _rect(inner, -inner, half, inner),
    ]


def seal_ring(
    *, x0: float, y0: float, x1: float, y1: float, width_um: float,
    left_openings: list[tuple[float, float]] | None = None,
) -> list[list[tuple[float, float]]]:
    """A ring, as overlapping bars, optionally opened on the left edge.

    It is expressed as bars rather than as a polygon with a hole, every mask
    format handling the former and not every one the latter.

    `left_opening` is a (y_lo, y_hi) band over which the left bar is omitted.
    An optical port has to reach the sawn edge, so the guide crosses the line
    the ring occupies. A ring drawn through it would place metal across the
    waveguide. The ring is therefore interrupted, which is ordinary practice
    wherever a die carries an edge coupler, and the two remaining segments still
    arrest a crack travelling along the other three edges.
    """
    w = width_um
    bars = [
        _rect(x0, y0, x1, y0 + w),
        _rect(x0, y1 - w, x1, y1),
        _rect(x1 - w, y0, x1, y1),
    ]
    if not left_openings:
        bars.append(_rect(x0, y0, x0 + w, y1))
        return bars

    # Every optical port needs its own gap. A reticle carrying a ladder has one
    # per copy, so the bar is cut into the segments between them.
    spans = sorted((max(min(a, b), y0), min(max(a, b), y1))
                   for a, b in left_openings)
    merged: list[list[float]] = []
    for lo, hi in spans:
        if hi <= lo:
            continue
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    cursor = y0
    for lo, hi in merged:
        if lo > cursor:
            bars.append(_rect(x0, cursor, x0 + w, lo))
        cursor = max(cursor, hi)
    if cursor < y1:
        bars.append(_rect(x0, cursor, x0 + w, y1))
    return bars
