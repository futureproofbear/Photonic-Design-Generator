"""Markdown + figure reporting for a completed run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import dump_json


def _fmt(v: Any, nd: int = 4) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        if v != v:
            return "nan"
        if v == 0:
            return "0"
        if abs(v) >= 1e5 or abs(v) < 1e-3:
            return f"{v:.{nd}e}"
        return f"{v:.{nd}g}"
    return str(v)


def make_figures(run_dir: Path) -> list[Path]:
    """Render the standard figure set from the stage npz files."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figs: list[Path] = []
    fig_dir = run_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # some figures annotate themselves with a figure from another stage, so the
    # metric tree is read once here rather than per renderer
    metrics: dict = {}
    mp = run_dir / "metrics.json"
    if mp.exists():
        try:
            metrics = json.loads(mp.read_text(encoding="utf-8")).get("metrics", {})
        except (OSError, ValueError):
            metrics = {}

    # --- mode profile ---
    p = run_dir / "mode.npz"
    if p.exists():
        d = np.load(p)
        # a device with no grating writes no posted field, and one panel is drawn
        # rather than two. Drawing a posted panel for such a device would show a
        # structure it does not contain
        panels = [("field_bare", "bare ridge")]
        if "field_posts" in d:
            panels.append(("field_posts", "with Bragg posts"))
        fig, ax = plt.subplots(1, len(panels), figsize=(5 * len(panels), 3.6),
                               constrained_layout=True, squeeze=False)
        for a, (key, title) in zip(ax[0], panels):
            f = d[key]
            im = a.pcolormesh(d["x_um"], d["y_um"], (np.abs(f) ** 2 / np.abs(f).max() ** 2).T,
                              shading="auto", cmap="magma")
            a.set_xlabel("x (um)"); a.set_ylabel("y (um)"); a.set_title(f"|E|$^2$, {title}")
            a.set_xlim(-3, 3); a.set_aspect("equal")
            fig.colorbar(im, ax=a)
        out = fig_dir / "mode_profile.png"
        fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

    # --- grating spectrum ---
    p = run_dir / "grating.npz"
    if p.exists():
        d = np.load(p)
        f = d["freq_Hz"]; R = d["R"]
        f0 = f[int(np.argmax(R))]
        fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), constrained_layout=True)
        ax[0].plot((f - f0) / 1e9, R, lw=1.4)
        ax[0].set_xlabel("detuning (GHz)"); ax[0].set_ylabel("reflectivity")
        ax[0].set_title("DBR reflection"); ax[0].grid(alpha=.3)
        ax[1].semilogy((f - f0) / 1e9, np.maximum(R, 1e-8), lw=1.0)
        ax[1].set_xlabel("detuning (GHz)"); ax[1].set_ylabel("reflectivity (log)")
        ax[1].set_title("sidelobes"); ax[1].grid(alpha=.3)
        out = fig_dir / "grating_spectrum.png"
        fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

        if "sweep_R" in d:
            W, G = d["sweep_w"], d["sweep_g"]
            fig, ax = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
            for a, key, title in zip(ax, ["sweep_R", "sweep_BW_GHz"],
                                     ["peak reflectivity", "FWHM (GHz)"]):
                im = a.pcolormesh(W, G, d[key].T, shading="auto", cmap="viridis")
                cs = a.contour(W, G, d[key].T, colors="w", linewidths=.7)
                a.clabel(cs, inline=True, fontsize=7)
                a.set_xlabel("post width (um)"); a.set_ylabel("post gap (um)")
                a.set_title(title); fig.colorbar(im, ax=a)
            out = fig_dir / "grating_designspace.png"
            fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

    # --- RF field ---
    p = run_dir / "eo.npz"
    if p.exists():
        d = np.load(p)
        fig, ax = plt.subplots(figsize=(6, 3.4), constrained_layout=True)
        im = ax.pcolormesh(d["x_um"], d["y_um"], d["Ex"].T, shading="auto", cmap="RdBu_r")
        ax.contour(d["x_um"], d["y_um"], (d["intensity"] / d["intensity"].max()).T,
                   levels=[0.05, 0.5], colors="k", linewidths=.8)
        ax.set_xlabel("x (um)"); ax.set_ylabel("y (um)")
        ax.set_title("RF $E_x$ (V/um) with optical mode contours")
        fig.colorbar(im, ax=ax)
        out = fig_dir / "eo_field.png"
        fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

    # --- laser tuning ---
    p = run_dir / "cavity.npz"
    if p.exists():
        d = np.load(p)
        V, f = d["V_sweep"], d["f_laser_Hz"]
        if len(V) > 3:
            f0 = f[0]
            fig, ax = plt.subplots(1, 2, figsize=(10, 3.4), constrained_layout=True)
            ax[0].plot(V, (f - f0) / 1e9, lw=1.5)
            ax[0].set_xlabel("drive voltage (V)"); ax[0].set_ylabel("laser frequency shift (GHz)")
            ax[0].set_title("mode-hop-free tuning"); ax[0].grid(alpha=.3)
            k, b = np.polyfit(V, f, 1)
            ax[1].plot(V, (f - (k * V + b)) / 1e6, lw=1.2)
            ax[1].set_xlabel("drive voltage (V)"); ax[1].set_ylabel("deviation (MHz)")
            ax[1].set_title("chirp nonlinearity"); ax[1].grid(alpha=.3)
            out = fig_dir / "cavity_tuning.png"
            fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

    # --- the rate equations ---
    # Two panels, because the stage answers two unrelated questions. The
    # light-current curve is what the device delivers; the intensity noise is
    # what it delivers it with. The relaxation oscillation is marked on the
    # second, being the frequency the first says nothing about.
    p = run_dir / "dynamics.npz"
    dyn = metrics.get("dynamics")
    if p.exists() and dyn and dyn.get("enabled"):
        d = np.load(p)
        curve = dyn.get("light_current_curve") or []
        if curve:
            I = np.array([r["current_mA"] for r in curve])
            P = np.array([r["output_power_mW"] for r in curve])
            fig, ax = plt.subplots(1, 2, figsize=(10, 3.4), constrained_layout=True)
            ax[0].plot(I, P, "o-", lw=1.5, ms=4)
            I_th = dyn.get("threshold_current_mA")
            if I_th:
                ax[0].axvline(I_th, color="C3", ls="--", lw=1,
                              label=f"threshold {I_th:.0f} mA")
            I_op = dyn.get("operating_current_mA")
            P_op = dyn.get("operating_output_power_mW")
            if I_op and P_op:
                ax[0].plot([I_op], [P_op], "s", color="C2", ms=7,
                           label=f"{P_op:.1f} mW at {I_op:.0f} mA")
            P_dec = dyn.get("declared_output_power_mW")
            if P_dec:
                ax[0].axhline(P_dec, color="C7", ls=":", lw=1,
                              label=f"declared {P_dec:.0f} mW")
            ax[0].set_xlabel("drive current (mA)")
            ax[0].set_ylabel("output power (mW)")
            ax[0].set_title("light against current")
            ax[0].grid(alpha=.3); ax[0].legend(fontsize=7)

            f_r = dyn.get("relaxation_oscillation_GHz") or 0.0
            rin = d["rin_per_Hz"]
            fr_grid = d["rin_frequency_Hz"] / 1e9
            good = np.isfinite(rin) & (rin > 0)
            if good.any():
                ax[1].plot(fr_grid[good], 10 * np.log10(rin[good]), lw=1.4)
                if f_r > 0:
                    ax[1].axvline(f_r, color="C3", ls="--", lw=1,
                                  label=f"f_r = {f_r:.2f} GHz")
                fsr = (metrics.get("cavity") or {}).get("fsr_GHz")
                if fsr:
                    ax[1].axvline(fsr, color="C0", ls=":", lw=1,
                                  label=f"compound mode spacing {fsr:.1f} GHz")
                ax[1].legend(fontsize=7)
            ax[1].set_xlabel("offset frequency (GHz)")
            ax[1].set_ylabel("RIN (dB/Hz)")
            ax[1].set_title("relative intensity noise")
            ax[1].grid(alpha=.3)
            out = fig_dir / "laser_dynamics.png"
            fig.savefig(out, dpi=140); plt.close(fig); figs.append(out)

    # A drawing must never fail a run, and a drawing that fails must never do so
    # in silence. These renderers open a die layout of tens of megabytes, so
    # they are the first thing to fail under memory pressure or contention, and
    # the failure removes a figure from the run rather than raising.
    #
    # Observed 2026-08-18. Six of nineteen figures were absent from a run of
    # record, every renderer having raised while other work competed for the
    # machine. Each rendered correctly when called again on the same run
    # directory. The run reported nothing, and the published copies stayed at
    # their previous version, so a document would have shown six drawings of an
    # earlier device with no symptom. `tools/check_figures_current.py` is what
    # caught it, and that check is run by hand.
    # A renderer reports its outcome three ways and only one of them is an error.
    # It returns a path, it raises, or it returns None. **The third is the one
    # that was silent**, and it is the one that actually occurred: six of
    # nineteen drawings were lost from two consecutive runs of record with no
    # exception raised and no `figures.failed.json` written, and every one of the
    # six rendered correctly when called again on the same run directory.
    #
    # A None is legitimate where the stage that feeds the renderer did not run.
    # It is a failure where that stage's payload is present, and the two are
    # distinguished here by looking for the payload rather than by trusting the
    # renderer.
    needs = {
        "_fig_cross_section": "mode",
        "_fig_mask_plan": "layout",
        "_fig_mask_shot": "layout",
        "_fig_facet_route": "layout",
        "_fig_die_plan": "reticle",
        "_fig_die_shot": "reticle",
        "_fig_grating_cell": "layout",
    }

    def _record(fn, out, failed):
        name = fn.__name__
        stage = needs.get(name)
        if out is None and stage and (run_dir / f"{stage}.json").exists():
            failed.append(f"{name}: returned no figure although {stage}.json is present")
        return out

    failed: list[str] = []
    for renderer in (_fig_cross_section, _fig_mask_plan, _fig_mask_shot,
                     _fig_facet_route, _fig_die_plan, _fig_die_shot):
        try:
            out = renderer(run_dir, fig_dir)
        except Exception as exc:
            failed.append(f"{renderer.__name__}: {type(exc).__name__}: {exc}")
            out = None
        out = _record(renderer, out, failed)
        if out is not None:
            figs.append(out)

    try:
        out = _fig_grating_cell(run_dir, fig_dir, metrics)
    except Exception as exc:
        failed.append(f"_fig_grating_cell: {type(exc).__name__}: {exc}")
        out = None
    out = _record(_fig_grating_cell, out, failed)
    if out is not None:
        figs.append(out)

    if failed:
        dump_json(run_dir / "figures.failed.json", {"failed": failed})

    return figs, failed



# --------------------------------------------------------------------------
# detail drawings
#
# Each is read back from the file that was written, so it is a drawing of the
# mask rather than of the parameters that produced it. That distinction has
# earned its keep more than once here: a facet angle that fed a coupling
# calculation and drew nothing, and a recess drawn square against a sheared
# facet, were both found by looking at the emitted polygons.
# --------------------------------------------------------------------------
def _read_layers(gds, wanted, lmap, clip=None):
    """Merged polygons for the named layers, optionally clipped to a window."""
    import klayout.db as db

    layout = db.Layout()
    layout.read(str(gds))
    top = layout.top_cell()
    dbu = layout.dbu
    box = None
    if clip is not None:
        z0, y0, z1, y1 = clip
        box = db.Region(db.Box(int(z0 / dbu), int(y0 / dbu),
                               int(z1 / dbu), int(y1 / dbu)))
    out = {}
    for name in wanted:
        pair = lmap.get(name)
        if not pair:
            continue
        idx = layout.find_layer(int(pair[0]), int(pair[1]))
        if idx is None:
            continue
        region = db.Region(top.begin_shapes_rec(idx)).merged()
        if box is not None:
            region = region & box
        # A hull discards holes, so a seal ring drawn as an annulus paints as a
        # filled rectangle and hides the die beneath it. The holes are resolved
        # into the outline first, which traces them by a cut line and leaves one
        # closed contour that fills correctly.
        polys = [[(p.x * dbu, p.y * dbu)
                  for p in poly.resolved_holes().each_point_hull()]
                 for poly in region.each()]
        if polys:
            out[name] = polys
    return out


def _layout_info(run_dir: Path):
    import json
    p = run_dir / "layout.json"
    if not p.exists():
        return None
    info = json.loads(p.read_text(encoding="utf-8"))
    gds = info.get("gds")
    if not gds or not Path(gds).exists():
        return None
    return info


def _fig_facet_route(run_dir: Path, fig_dir: Path):
    """The route by which the guide reaches the die edge.

    Two things are drawn that no number in the metric tree carries. The end face
    of the taper tip is cut across the guide's own axis, so on an angled route it
    stands at the facet angle to the die edge, and the recess band must shear
    with the facet rather than stay square. Both were defects before they were
    drawings.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    info = _layout_info(run_dir)
    if not info:
        return None
    lmap = info.get("layer_map") or {}
    route = info.get("facet_route", "sheared")
    ax_extent = float(info.get("grating_start_um") or 220.0)
    exc = float(info.get("facet_lead_in_excursion_um") or 0.0)
    win = (-12.0, -(exc + 12.0), ax_extent + 30.0, 8.0)
    polys = _read_layers(info["gds"], ["SLAB", "FACET", "WG"], lmap, clip=win)
    if "WG" not in polys:
        return None

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.9),
                           gridspec_kw={"width_ratios": [2.5, 1]},
                           constrained_layout=True)

    def paint(a, window):
        for name, colour, z in (("SLAB", "#ffe0b2", 1), ("FACET", "#ef9a9a", 2),
                                ("WG", "#d95f02", 3)):
            for pts in polys.get(name, []):
                a.add_patch(Polygon(pts, facecolor=colour, edgecolor="#37474f",
                                    linewidth=0.4, zorder=z,
                                    alpha=0.45 if name == "FACET" else 1.0))
        a.set_xlim(window[0], window[2])
        a.set_ylim(window[1], window[3])
        a.set_xlabel("z (um)")
        a.set_ylabel("y (um)")

    paint(ax[0], win)
    ax[0].axvline(0.0, color="#b71c1c", lw=1.0)
    ax[0].axhline(0.0, color="#607d8b", lw=0.6, ls="-.")
    # The window is some 240 um along the die against 40 um across it, so the
    # panel is not to scale and the 8 degrees will not measure 8 degrees on the
    # page. Said here rather than left for a reader to discover with a protractor.
    zspan = win[2] - win[0]
    yspan = win[3] - win[1]
    title = f"facet route: {route}"
    if route == "angled":
        title += (f", bend R = {info.get('facet_bend_radius_um')} um, "
                  f"excursion {exc:.2f} um")
    title += f"  [y exaggerated {zspan / yspan:.1f}x]"
    ax[0].set_title(title, fontsize=10)

    # the tip, magnified: this is where the end face and the recess are read
    ys = [p[1] for pts in polys["WG"] for p in pts if p[0] < 2.0]
    yc = sum(ys) / len(ys) if ys else 0.0
    paint(ax[1], (-6.0, yc - 2.0, 4.0, yc + 2.0))
    ax[1].axvline(0.0, color="#b71c1c", lw=1.0)
    ax[1].set_title("the tip, and the recess it sits in", fontsize=10)

    out = fig_dir / "facet_route.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _fig_mask_shot(run_dir: Path, fig_dir: Path):
    """The mask as the layout viewer draws it, not as this module redraws it.

    The polygons were already read back from the emitted GDS, so the earlier
    plan view was of the mask rather than of the parameters. It was still a
    redrawing, with the window, the colours and the aspect chosen here, and those
    choices misled: a fixed vertical window of +-1.2 um about the die axis showed
    the tail of a routed lead-in and captioned it the input taper.

    This renders through KLayout with the layer properties the run itself
    emitted, so the colours are the process's own and the geometry is whatever
    the file contains. Where the viewer cannot be reached the earlier plan view
    remains and is produced alongside.
    """
    import json

    info = _layout_info(run_dir)
    if not info:
        return None
    gds = Path(info["gds"])
    lyp = gds.with_suffix(".lyp")

    try:
        import klayout.db as kdb
        import klayout.lay as klay
    except ImportError:
        return None

    exc = float(info.get("facet_lead_in_excursion_um") or 0.0)
    z0 = float(info.get("grating_start_um") or 200.0)
    period = 1.3
    try:
        period = float(json.loads((run_dir / "metrics.json").read_text(
            encoding="utf-8"))["metrics"]["grating"]["period_nm"]) / 1000.0
    except Exception:
        pass

    gap = wid = 0.0
    pad = 80.0
    try:
        d = json.loads((run_dir / "design.resolved.json").read_text(encoding="utf-8"))
        gap = float(d["electrodes"]["gap_um"]); wid = float(d["electrodes"]["width_um"])
        pad = float(d["layout"].get("bond_pad_um", 80.0))
    except Exception:
        pass
    half = gap / 2 + wid + 4.0 if gap else 30.0
    dev_len = float(info.get("device_length_um") or 11000.0)

    views = [
        ("shot_leadin", kdb.DBox(-8.0, -(exc + 3.0), z0 + 25.0, 3.0)),
        ("shot_taper_tip", kdb.DBox(-6.0, -(exc + 1.2), 8.0, -(exc - 1.6))),
        ("shot_grating", kdb.DBox(z0 - period, -2.6, z0 + 10 * period, 2.6)),
        ("shot_electrodes",
         kdb.DBox(dev_len / 2 - 60.0, -half, dev_len / 2 + 60.0, half)),
        # The electrode view above is a close one and its window stops at the
        # outer electrode edge, so it cut the bond pad off entirely. The pad is
        # the only place a lead can be attached, which makes it worth its own
        # view rather than an omission nobody noticed.
        ("shot_pad",
         kdb.DBox(dev_len / 2 - pad, gap / 2 - 12.0,
                  dev_len / 2 + pad, gap / 2 + wid + pad + 12.0)),
    ]

    lv = klay.LayoutView()
    lv.load_layout(str(gds), 0)
    if lyp.exists():
        try:
            lv.load_layer_props(str(lyp))
        except Exception:
            pass
    lv.max_hier()

    out = []
    for name, box in views:
        shot = fig_dir / f"{name}.png"
        lv.zoom_box(box)
        lv.save_image(str(shot), 1200, 440)
        out.append(shot)
    return out[0] if out else None


def _monitor_box(kdb, ret: dict, hw: float, hh: float):
    """The window holding the process-control monitors.

    Derived from where the reticle placed them rather than guessed. They sit
    below the device and are shifted with everything else when the die is
    centred on the origin, so a window written in die coordinates by hand lands
    on the wrong side: the first attempt showed the bottom-left corner and
    called it the monitor field.
    """
    dx, dy = (ret.get("chip_frame") or {}).get("translated_by_um") or [0.0, 0.0]
    ys = [row.get("y_um", 0.0)
          for m in (ret.get("monitors") or []) for row in (m.get("rows") or [])
          if row.get("y_um") is not None]
    lo = (min(ys) if ys else -520.0) + dy
    hi = (max(ys) if ys else 0.0) + dy
    pad = 90.0
    return kdb.DBox(max(-hw, dx - 40.0), max(-hh, lo - pad),
                    min(hw, dx + 720.0), min(hh, hi + pad))


def _fig_die_shot(run_dir: Path, fig_dir: Path):
    """The assembled die as the layout viewer draws it.

    The frame, the seal ring, the dicing lane, the overlay marks, the monitor
    field and the fill are all drawn by the reticle and mask stages and none of
    them appears in any other figure. A die whose frame is never shown is a die
    whose frame is taken on trust.
    """
    import json

    p = run_dir / "reticle.json"
    if not p.exists():
        return None
    ret = json.loads(p.read_text(encoding="utf-8"))
    gds = ret.get("filled_gds") or ret.get("gds")
    if not gds or not Path(gds).exists():
        gds = (json.loads((run_dir / "mask.json").read_text(encoding="utf-8"))
               .get("filled_gds") if (run_dir / "mask.json").exists() else None)
    if not gds or not Path(gds).exists():
        return None

    try:
        import klayout.db as kdb
        import klayout.lay as klay
    except ImportError:
        return None

    frame = ret.get("chip_frame") or {}
    ow, oh = frame.get("outer_um") or [ret.get("die_width_um"), ret.get("die_height_um")]
    if not ow:
        return None
    hw, hh = ow / 2.0, oh / 2.0

    # Where the guide leaves the die. This is the one feature of the die that
    # decides whether a butt-coupled part can be assembled at all, and it had no
    # view: the die shot is too coarse to resolve it and the device shots are
    # drawn on the device cell, which carries no frame. The window spans the
    # exclusion ring and the seal-ring opening either side of the guide.
    port = kdb.DBox(-hw - 10.0, -90.0, -hw + 190.0, 90.0)

    views = [
        ("shot_die", kdb.DBox(-hw * 1.02, -hh * 1.02, hw * 1.02, hh * 1.02)),
        ("shot_die_corner", kdb.DBox(-hw - 20, hh - 260, -hw + 260, hh + 20)),
        ("shot_monitors", _monitor_box(kdb, ret, hw, hh)),
        ("shot_port", port),
    ]

    lv = klay.LayoutView()
    lv.load_layout(str(gds), 0)
    lyp = Path(gds).with_suffix(".lyp")
    if not lyp.exists():
        lyp = next(iter(Path(gds).parent.glob("*.lyp")), None)
    if lyp and lyp.exists():
        try:
            lv.load_layer_props(str(lyp))
        except Exception:
            pass
    lv.max_hier()

    out = []
    for name, box in views:
        s = fig_dir / f"{name}.png"
        lv.zoom_box(box)
        lv.save_image(str(s), 1200, 420)
        out.append(s)
    return out[0] if out else None


def _fig_grating_cell(run_dir: Path, fig_dir: Path, metrics: dict):
    """A few periods of the grating, with the dimensions that set kappa.

    The post gap is the parameter this design turns on: it sets the coupling
    while the ridge sets the mode count, and decoupling those two is what opened
    a process window at all. It is drawn from the mask so that the gap the model
    used and the gap the mask carries can be compared by eye.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    info = _layout_info(run_dir)
    if not info:
        return None
    lmap = info.get("layer_map") or {}
    z0 = float(info.get("grating_start_um") or 0.0)
    g = (metrics.get("grating") or {})
    period = float(g.get("period_nm") or 1300.0) / 1000.0
    win = (z0 - period, -3.0, z0 + 5 * period, 3.0)
    polys = _read_layers(info["gds"], ["WG"], lmap, clip=win)
    if "WG" not in polys:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 3.4), constrained_layout=True)
    for pts in polys["WG"]:
        ax.add_patch(Polygon(pts, facecolor="#d95f02", edgecolor="#37474f",
                             linewidth=0.5))
    ax.set_xlim(win[0], win[2])
    ax.set_ylim(win[1], win[3])
    ax.set_xlabel("z (um)")
    ax.set_ylabel("y (um)")
    ax.set_aspect("equal")
    ax.set_title(
        f"grating, period {period * 1000:.2f} nm, order {g.get('order', 3)}, "
        f"kappa {g.get('kappa_per_cm', float('nan')):.3f} /cm", fontsize=10)

    # the gap, annotated between the ridge edge and the nearer post
    ridge = max(polys["WG"], key=lambda p: max(x for x, _ in p) - min(x for x, _ in p))
    ridge_top = max(y for _, y in ridge)
    posts = [p for p in polys["WG"] if p is not ridge]
    if posts:
        above = [p for p in posts if min(y for _, y in p) > ridge_top]
        if above:
            near = min(above, key=lambda p: min(y for _, y in p))
            y_post = min(y for _, y in near)
            x_post = sum(x for x, _ in near) / len(near)
            ax.annotate("", xy=(x_post, ridge_top), xytext=(x_post, y_post),
                        arrowprops=dict(arrowstyle="<->", color="#1565c0", lw=1.1))
            ax.text(x_post + 0.06 * period, 0.5 * (ridge_top + y_post),
                    f"post gap {y_post - ridge_top:.3f} um",
                    color="#1565c0", fontsize=8, va="center")
    out = fig_dir / "grating_cell.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _fig_die_plan(run_dir: Path, fig_dir: Path):
    """The die, its frame, and the two rectangles a rule deck reads.

    The footprint, the centring and the exclusion ring are checked against
    CHIP_OUTER and CHIP_INNER, and neither exists unless it is drawn. Showing
    them is the difference between a rule that passed and a rule that was silent.
    """
    import json

    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    p = run_dir / "reticle.json"
    lp = run_dir / "layout.json"
    if not p.exists() or not lp.exists():
        return None
    ret = json.loads(p.read_text(encoding="utf-8"))
    gds = ret.get("gds")
    if not gds or not Path(gds).exists():
        return None
    lmap = json.loads(lp.read_text(encoding="utf-8")).get("layer_map") or {}

    order = [("CHIP_OUTER", "none", "#b71c1c", "chip outer"),
             ("CHIP_INNER", "none", "#1565c0", "chip inner"),
             ("DICE", "#eceff1", "#90a4ae", "dicing lane"),
             ("SEAL", "#cfd8dc", "#607d8b", "seal ring"),
             ("SLAB", "#fff3e0", "#ffcc80", "slab"),
             ("WG", "#d95f02", "none", "waveguide"),
             ("METAL", "#f9a825", "none", "metal"),
             ("MARK", "#6a1b9a", "none", "marks")]
    polys = _read_layers(gds, [n for n, *_ in order], lmap)
    if not polys:
        return None

    fig, ax = plt.subplots(figsize=(11, 3.4), constrained_layout=True)
    for name, fill, edge, label in order:
        first = True
        for pts in polys.get(name, []):
            ax.add_patch(Polygon(
                pts, facecolor="none" if fill == "none" else fill,
                edgecolor="none" if edge == "none" else edge,
                linewidth=1.0 if fill == "none" else 0.4,
                linestyle="--" if fill == "none" else "-",
                label=label if first else None))
            first = False
    frame = ret.get("chip_frame") or {}
    ow, oh = (frame.get("outer_um") or [ret.get("die_width_um", 0),
                                        ret.get("die_height_um", 0)])
    ax.set_xlim(-0.55 * ow, 0.55 * ow)
    ax.set_ylim(-0.75 * oh, 0.75 * oh)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    offered = frame.get("footprint_is_offered")
    mark = "offered by the process" if offered else "NOT an offered footprint"
    ax.set_title(f"die {ow:.0f} x {oh:.0f} um, {mark}; "
                 f"usable {frame.get('inner_um', ['?', '?'])[0]:.0f} x "
                 f"{frame.get('inner_um', ['?', '?'])[1]:.0f} um", fontsize=10)
    ax.legend(loc="upper right", fontsize=7, ncol=4, framealpha=0.9)
    out = fig_dir / "die_plan.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out

# --------------------------------------------------------------------------
# geometry drawings
# --------------------------------------------------------------------------
#: fill, edge and label for each material class encountered in a cross-section
_MATERIAL_STYLE = {
    "LiNbO3": ("#d95f02", "#7f3b02", "film"),
    "LiTaO3": ("#d95f02", "#7f3b02", "film"),
    "SiO2": ("#cfd8dc", "#78909c", "oxide"),
    "Si": ("#546e7a", "#263238", "handle"),
    "Au": ("#f9a825", "#8d6e00", "metal"),
    "Air": ("#ffffff", "#b0bec5", "air"),
}


def _style(material: str):
    for key, value in _MATERIAL_STYLE.items():
        if key.lower() in material.lower():
            return value
    return ("#bdbdbd", "#616161", material)


def _fig_cross_section(run_dir: Path, fig_dir: Path):
    """The stack as drawn, with its dimensions and the mode contour over it.

    This is the drawing that answers what the waveguide *is*, as distinct from
    ``mode_profile.png``, which shows only the field it supports.
    """
    import json

    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    src = run_dir / "cross_section.json"
    if not src.exists():
        return None
    xs = json.loads(src.read_text(encoding="utf-8"))

    fig, ax = plt.subplots(figsize=(9, 4.2), constrained_layout=True)
    x0, x1, y0, y1 = xs["window"]
    bg_fill, bg_edge, bg_label = _style(xs["background"])
    ax.add_patch(Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                         facecolor=bg_fill, edgecolor="none", zorder=0))

    seen = {bg_label: bg_fill}
    for shape in xs["shapes"]:
        fill, edge, label = _style(shape["material"])
        ax.add_patch(Polygon(shape["points"], facecolor=fill, edgecolor=edge,
                             linewidth=0.8, zorder=1))
        seen.setdefault(label, fill)

    # the mode, as contours of |E|^2 at the tenth and the hundredth of the peak
    npz = run_dir / "mode.npz"
    if npz.exists():
        d = np.load(npz)
        f = np.abs(d["field_bare"]) ** 2
        f = f / f.max()
        ax.contour(d["x_um"], d["y_um"], f.T, levels=[0.01, 0.1, 0.5],
                   colors="#00e5ff", linewidths=[0.7, 1.0, 1.4], zorder=3)

    # dimensions of the ridge, taken from the drawn polygon rather than restated
    ridge = next((s for s in xs["shapes"] if "ridge" in s["name"].lower()), None)
    if ridge:
        px = [p[0] for p in ridge["points"]]
        py = [p[1] for p in ridge["points"]]
        top = max(py)
        w_top = max(p[0] for p in ridge["points"] if abs(p[1] - top) < 1e-9) - \
            min(p[0] for p in ridge["points"] if abs(p[1] - top) < 1e-9)
        x_left = min(p[0] for p in ridge["points"] if abs(p[1] - top) < 1e-9)
        x_right = max(p[0] for p in ridge["points"] if abs(p[1] - top) < 1e-9)
        ax.annotate("", xy=(x_left, top + 0.16), xytext=(x_right, top + 0.16),
                    arrowprops=dict(arrowstyle="<->", color="k", lw=0.9))
        ax.text((x_left + x_right) / 2, top + 0.21, f"{w_top:.3f} um", ha="center",
                fontsize=8)
        x_dim = max(px) + 0.30
        ax.annotate("", xy=(x_dim, min(py)), xytext=(x_dim, top),
                    arrowprops=dict(arrowstyle="<->", color="k", lw=0.9))
        ax.text(x_dim + 0.06, (top + min(py)) / 2, f"{top - min(py):.3f} um etch",
                fontsize=8, rotation=90, va="center")

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="#455a64")
               for c in seen.values()]
    ax.legend(handles, list(seen), loc="upper right", fontsize=8, framealpha=0.9)

    # frame the structure rather than the simulation window, which is mostly
    # cladding and carries nothing to look at. The blanket layers span the whole
    # window and are excluded, or the frame would not narrow at all.
    span = x1 - x0
    local = [s for s in xs["shapes"]
             if (max(p[0] for p in s["points"]) - min(p[0] for p in s["points"]))
             < 0.5 * span]
    px = [p[0] for s in local for p in s["points"]]
    py = [p[1] for s in local for p in s["points"]]
    if px:
        x0 = max(x0, min(px) - 1.1); x1 = min(x1, max(px) + 1.1)
        y0 = max(y0, min(py) - 0.9); y1 = min(y1, max(py) + 0.6)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.set_xlabel("x (um)"); ax.set_ylabel("y (um)")
    ax.set_title(f"cross-section as drawn, with |E|$^2$ contours at "
                 f"{xs['wavelength_um']:.4g} um")
    out = fig_dir / "cross_section.png"
    fig.savefig(out, dpi=140); plt.close(fig)
    return out


def _fig_mask_plan(run_dir: Path, fig_dir: Path):
    """Plan view of the emitted mask, rendered without a graphical application.

    The polygons are read back from the GDS that was actually written, so the
    drawing is of the mask rather than of the parameters that produced it. Two
    insets carry the dimensions that matter: the input taper and a few grating
    periods.
    """
    import json

    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    info_path = run_dir / "layout.json"
    if not info_path.exists():
        return None
    gds = json.loads(info_path.read_text(encoding="utf-8")).get("gds")
    if not gds or not Path(gds).exists():
        return None

    import klayout.db as db
    layout = db.Layout()
    layout.read(str(gds))
    top = layout.top_cell()
    dbu = layout.dbu

    info = json.loads(info_path.read_text(encoding="utf-8"))
    # fill, label and paint order: the slab is the ground plane and every other
    # layer is drawn over it, or the waveguide disappears beneath it.
    #
    # Keyed by NAME and resolved through the run's own layer map. The numbers
    # were written in here until 2026-08-09, and when the design was remapped to
    # the foundry numbering the renderer went on believing 1/0 was the waveguide
    # and 2/0 the slab. It then painted the guide in the slab's colour and lost
    # the metal entirely, and the figure said so in neither its legend nor its
    # caption. A drawing keyed to numbers the design is free to change is a
    # drawing that misreports without failing.
    lmap = info.get("layer_map") or {}
    named = {"SLAB": ("#ffe0b2", "slab", 1), "WG": ("#d95f02", "waveguide", 2),
             "METAL": ("#f9a825", "metal", 3), "PAD": ("#fbc02d", "pad", 4),
             "FLOORPLAN": ("none", "floor plan", 5)}
    style = {}
    for name, spec in named.items():
        pair = lmap.get(name)
        if pair:
            style[f"{int(pair[0])}/{int(pair[1])}"] = spec

    polys: dict[str, list] = {}
    for index in layout.layer_indexes():
        key = str(layout.get_info(index))
        out: list[list[tuple[float, float]]] = []
        for shape in top.each_shape(index):
            if shape.is_box() or shape.is_polygon() or shape.is_path():
                poly = shape.polygon
                if poly is None:
                    continue
                # holes resolved, or an annulus fills as a solid rectangle
                out.append([(pt.x * dbu, pt.y * dbu)
                            for pt in poly.resolved_holes().each_point_hull()])
        if out:
            polys[key] = out

    bbox = top.dbbox()
    fig = plt.figure(figsize=(11, 6.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.1])
    ax_full = fig.add_subplot(gs[0, :])
    ax_taper = fig.add_subplot(gs[1, 0])
    ax_grating = fig.add_subplot(gs[1, 1])

    def draw(ax, xlim, ylim, title):
        for key in sorted(polys, key=lambda k: style.get(k, (None, None, 9))[2]):
            fill, label, order = style.get(key, ("#90a4ae", key, 9))
            for pts in polys[key]:
                ax.add_patch(Polygon(
                    pts, facecolor="none" if fill == "none" else fill,
                    edgecolor="#37474f" if fill == "none" else "none",
                    linewidth=0.6, linestyle=":" if fill == "none" else "-",
                    zorder=order))
        ax.set_xlim(*xlim); ax.set_ylim(*ylim)
        ax.set_xlabel("x (um)"); ax.set_ylabel("y (um)")
        ax.set_title(title, fontsize=10)

    draw(ax_full, (bbox.left, bbox.right), (bbox.bottom, bbox.top), "")
    ax_full.set_title(
        f"mask as written: {bbox.width():.0f} x {bbox.height():.0f} um, "
        f"{info.get('periods_drawn')} of {info.get('periods_total')} periods drawn",
        fontsize=10)

    # The window is taken from the geometry rather than fixed at +-1.2 um about
    # the die axis. On a routed facet the guide leaves the die edge well off that
    # axis, 23.3 um below it on the validation baseline, and climbs back only at
    # the end of the arc. A fixed window then showed the tail of the bend and
    # called it the taper.
    taper_len = float(info.get("taper_length_um") or 150.0)
    exc = float(info.get("facet_lead_in_excursion_um") or 0.0)
    x_end = float(info.get("grating_start_um") or (1.4 * taper_len))
    if exc > 1.0:
        y_win = (-(exc + 2.0), 2.0)
        title = (f"the routed lead-in: {taper_len:.0f} um of taper on the angled "
                 f"run, then the arc back to the axis")
    else:
        y_win = (-1.2, 1.2)
        title = f"input taper over {taper_len:.0f} um, vertical scale exaggerated"
    draw(ax_taper, (bbox.left, bbox.left + 1.15 * x_end), y_win, title)
    # a dozen micrometres of the grating shows the posts either side of the
    # ridge at their true spacing
    g_start = float(info.get("grating_start_um") or (bbox.left + taper_len)) + 2.0
    draw(ax_grating, (g_start, g_start + 12.0), (-3, 3),
         "grating, twelve micrometres of the drawn window")
    ax_grating.set_aspect("equal")     # the taper inset is deliberately not to scale

    handles, labels = [], []
    for key, (fill, label, _order) in style.items():
        if key in polys:
            handles.append(plt.Rectangle((0, 0), 1, 1,
                                         facecolor="none" if fill == "none" else fill,
                                         edgecolor="#37474f"))
            labels.append(label)
    ax_full.legend(handles, labels, fontsize=8, ncol=len(labels),
                   loc="lower left", framealpha=0.92, borderpad=0.4)

    out = fig_dir / "mask_plan.png"
    fig.savefig(out, dpi=140); plt.close(fig)
    return out


SECTIONS = [
    ("mode", "Waveguide mode", [
        ("n_eff_bare", "n_eff (bare ridge)", ""),
        ("n_g", "n_g", ""),
        ("dn_eff_posts", "dn_eff from Bragg posts", ""),
        ("confinement_film", "confinement in EO film", ""),
        ("n_guided_modes", "guided modes", ""),
        ("single_mode", "single mode", ""),
    ]),
    ("fem", "Finite-element cross-check", [
        ("n_eff_bare_fd", "n_eff, finite difference", ""),
        ("n_eff_bare_fem", "n_eff, finite element", ""),
        ("n_eff_bare_rel_delta", "n_eff disagreement", "fraction"),
        ("dn_eff_posts_fd", "dn_eff from posts, finite difference", ""),
        ("dn_eff_posts_fem", "dn_eff from posts, finite element", ""),
        ("dn_eff_rel_delta", "dn_eff disagreement", "fraction"),
        ("confinement_film_fem", "confinement in EO film", ""),
        ("polarisation_purity", "polarisation purity", ""),
        ("transversality", "transversality", ""),
        ("mesh_elements", "mesh elements", ""),
    ]),
    ("grating", "Bragg grating", [
        ("order", "grating order m", ""),
        ("period_nm", "period", "nm"),
        ("duty_cycle", "duty cycle", ""),
        ("n_periods", "periods", ""),
        ("kappa_per_cm", "kappa", "1/cm"),
        ("kappa_L", "kappa L", ""),
        ("bragg_wavelength_nm", "Bragg wavelength", "nm"),
        ("peak_reflectivity", "peak reflectivity", ""),
        ("fwhm_GHz", "FWHM", "GHz"),
        ("sidelobe_suppression_dB", "sidelobe suppression", "dB"),
        ("penetration_depth_mm", "penetration depth", "mm"),
        ("mirror_round_trip_delay_ps", "mirror round-trip delay", "ps"),
    ]),
    ("eo", "Pockels electrodes", [
        ("eo_overlap_gamma", "EO overlap Gamma", ""),
        ("dn_eff_per_V", "dn_eff per volt", "1/V"),
        ("tuning_MHz_per_V", "mirror tuning", "MHz/V"),
        ("VpiL_V_cm", "Vpi.L (with overlap)", "V.cm"),
        ("VpiL_ideal_V_cm", "Vpi.L (Gamma=1)", "V.cm"),
        ("capacitance_pF_per_cm", "capacitance", "pF/cm"),
        ("lumped_RC_bandwidth_MHz", "lumped RC bandwidth", "MHz"),
        ("mode_overlap_with_metal", "mode overlap with metal", ""),
    ]),
    ("cavity", "Hybrid laser cavity", [
        ("tau_roundtrip_ps", "round-trip delay", "ps"),
        ("fsr_GHz", "cavity FSR", "GHz"),
        ("pockels_lever", "Pockels lever tau_DBR/tau_rt", ""),
        ("laser_tuning_MHz_per_V", "laser tuning", "MHz/V"),
        ("mode_hop_free_range_GHz", "mode-hop-free range", "GHz"),
        ("chirp_nonlinearity_rms_percent", "chirp nonlinearity (RMS)", "%"),
        ("modal_threshold_gain_per_cm", "modal threshold gain", "1/cm"),
        ("schawlow_townes_henry_linewidth_kHz", "S-T-H linewidth", "kHz"),
        ("smsr_dB", "SMSR", "dB"),
    ]),
]



# --------------------------------------------------------------------------
# provenance: which instrument produced which quantity, in execution order
# --------------------------------------------------------------------------
#: (stage key, what it answers, how it is computed, the results to quote).
#: The "how" is a callable where the instrument is chosen at run time, so the
#: table states the backend that actually ran rather than the one configured.
def _tool_fem(sec):
    return f"full-vectorial finite elements, by femwell {sec.get('femwell_version', '')} on a gmsh triangulation"


def _tool_fdtd(sec):
    st = sec.get("structure", "")
    solver = sec.get("solver", "meep")
    ver = sec.get("solver_version", "")
    if st == "bandstructure":
        return f"photonic band structure of one period, by {solver} {ver}, in its own environment"
    return f"finite-difference time domain, {sec.get('dimensions', 2)}D, by {solver} {ver}, in its own environment"


def _tool_layout(sec):
    xor = sec.get("backend_xor") or {}
    if xor.get("performed"):
        return "polygon construction, emitted by gdsfactory and by KLayout, compared by exclusive-or"
    return "polygon construction, emitted through KLayout"


def _tool_circuit(sec):
    return f"scattering-matrix assembly, by sax {sec.get('sax_version', '')}"


def _tool_drc(sec):
    if sec.get("deck_violations") is not None:
        return "rule engine on KLayout regions, plus a foundry runset through the KLayout application"
    return "rule engine on KLayout regions (declared rules only, not a foundry deck)"


PROVENANCE: list[tuple[str, str, Any, list[tuple[str, str]]]] = [
    ("mode", "what shape does the light take, and what index does it see",
     "semi-vectorial finite-difference mode solver, Stern formulation, anisotropic diagonal permittivity, on a graded mesh",
     [("n_eff_bare", "n_eff"), ("n_g", "n_g"), ("dn_eff_posts", "dn_eff from the posts"),
      ("n_guided_modes", "guided modes")]),
    ("fem", "does a second instrument agree on that cross-section", _tool_fem,
     [("d_n_eff_percent", "disagreement on n_eff"), ("d_dn_eff_percent", "disagreement on dn_eff"),
      ("polarisation_purity", "polarisation purity")]),
    ("taper", "does the taper carry the light without disturbing it",
     "eigenmode expansion over the local modes of a staircase of slices",
     [("transmission", "conversion"), ("adiabaticity_margin_min", "worst adiabaticity margin")]),
    ("fdtd", "what does a solver that assumes less say", _tool_fdtd,
     [("kappa_per_cm", "kappa"), ("kappa_ratio_mpb_over_chain", "ratio to coupled mode")]),
    ("bend", "at what radius does a routing bend stop being a guide",
     "conformal transformation of the bend into a graded straight guide, solved by the same mode solver",
     [("min_safe_radius_um", "smallest bound radius")]),
    ("facet", "what is lost coupling into the chip",
     "overlap integral of the solved guide mode against a declared elliptical Gaussian, with Fresnel and Snell",
     [("mode_overlap", "mode overlap"), ("total_loss_dB", "total loss")]),
    ("grating", "at what wavelength does the mirror reflect, how strongly, how wide",
     "coupled-mode theory, the closed-form Fourier coefficient of the longitudinal profile at the working order, evaluated by transfer matrix",
     [("kappa_per_cm", "kappa"), ("peak_reflectivity", "peak reflectivity"),
      ("fwhm_GHz", "bandwidth"), ("penetration_depth_mm", "penetration depth")]),
    ("eo", "how far does the wavelength move per volt",
     "finite-difference electrostatic solve of the electrode field, overlapped with the optical mode",
     [("eo_overlap_gamma", "overlap"), ("tuning_MHz_per_V", "mirror tuning"), ("VpiL_V_cm", "Vpi.L")]),
    ("modulator", "what drive does the interferometer demand, and across what band",
     "the single-arm electro-optic solve converted for the two arms it sits in, "
     "and the travelling-wave response evaluated at the edges of the declared band",
     [("Vpi_V", "Vpi", " V"), ("VpiL_device_V_cm", "Vpi.L device", " V.cm"),
      ("worst_in_band_dB", "worst in band", " dB")]),
    ("cavity", "what does the laser do",
     "closed-form composite-cavity analysis, with the lasing mode followed numerically against applied voltage",
     [("pockels_lever", "Pockels lever"), ("mode_hop_free_range_GHz", "mode-hop-free range"),
      ("schawlow_townes_henry_linewidth_kHz", "linewidth"), ("smsr_dB", "SMSR")]),
    ("dynamics", "what current does it need, what power results, is it stable",
     "single-mode carrier and photon rate equations, solved in closed form at the steady state",
     [("threshold_current_mA", "threshold current"), ("operating_output_power_mW", "output power"),
      ("relaxation_oscillation_GHz", "relaxation oscillation"), ("feedback_regime", "feedback regime")]),
    ("circuit", "what mirror does the gain chip actually see", _tool_circuit,
     [("facet_etalon_ripple_percent", "facet etalon ripple")]),
    ("layout", "what does the mask look like", _tool_layout,
     [("device_length_um", "device length"), ("mask_is_complete", "every period drawn")]),
    ("reticle", "what does the die look like",
     "die assembly through KLayout: frame, seal ring, nested overlay marks, monitors and a split ladder",
     [("die_width_um", "die width"), ("die_height_um", "die height")]),
    ("drc", "can the mask be manufactured", _tool_drc,
     [("rules_checked", "rules checked"), ("error_violations", "violations at severity error")]),
    ("mask", "is the mask connected as intended",
     "connected-region and netlist extraction by KLayout, with density by tile",
     [("net_count", "extracted nets"), ("shorts", "layer-to-layer shorts")]),
    ("release", "may this be submitted",
     "artifact inventory with SHA-256, against ten conditions of readiness",
     [("ready", "ready")]),
    ("verify", "does the design meet its declared requirements",
     "each target evaluated against the metric tree",
     [("verdict", "verdict")]),
]


def _provenance_rows(m: dict) -> list[str]:
    """The sequence of instruments, as it actually ran."""
    out = ["| # | stage | question | instrument | result |", "|---|---|---|---|---|"]
    n = 0
    for key, question, tool, fields in PROVENANCE:
        sec = m.get(key)
        if not sec or sec.get("enabled") is False:
            continue
        n += 1
        how = tool(sec) if callable(tool) else tool
        vals = [f"{label} {_fmt(sec[f])}" for f, label in fields if f in sec and sec[f] is not None]
        out.append(f"| {n} | `{key}` | {question} | {how} | {'; '.join(vals) or '-'} |")
    return out


def render_markdown(metrics_path: Path, figures: list[Path] | None = None) -> str:
    import json
    doc = json.loads(metrics_path.read_text(encoding="utf-8"))
    m = doc["metrics"]
    L: list[str] = []
    L.append(f"# Run `{doc['run_id']}` - {doc['status']}")
    L.append("")
    L.append(f"* elapsed: {doc['elapsed_s']} s")
    env = doc["environment"]
    pk = ", ".join(f"{k} {v}" for k, v in env["packages"].items() if v)
    L.append(f"* python {env['python']} on {env['platform']}")
    L.append(f"* packages: {pk}")
    L.append("")

    rows = _provenance_rows(m)
    if len(rows) > 2:
        L.append("## What was computed, by what, in order")
        L.append("")
        L.append("The design chain is sequential: each stage reads only the results of")
        L.append("those before it. The table states the instrument that actually ran,")
        L.append("so a stage that fell back or was skipped is visible here.")
        L.append("")
        L.extend(rows)
        L.append("")

    for key, title, fields in SECTIONS:
        sec = m.get(key)
        if not sec or sec.get("enabled") is False:
            continue
        L.append(f"## {title}")
        L.append("")
        L.append("| quantity | value | unit |")
        L.append("|---|---:|---|")
        for f, label, unit in fields:
            if f in sec:
                L.append(f"| {label} | {_fmt(sec[f])} | {unit} |")
        L.append("")

    lay = m.get("layout")
    if lay and lay.get("enabled"):
        fid, xor = lay.get("fidelity") or {}, lay.get("backend_xor") or {}
        proc = lay.get("process") or {}
        L.append("## The mask as emitted")
        L.append("")
        L.append("| question | answer |")
        L.append("|---|---|")
        L.append(f"| is every grating period drawn | {'yes' if fid.get('mask_is_complete') else 'no'}"
                 f" ({fid.get('periods_drawn')} of {fid.get('periods_total')}) |")
        L.append(f"| do the two backends agree | "
                 + ("yes, exactly" if xor.get("agree") else
                    (f"no, {xor.get('residual_area_um2')} um2 residual" if xor.get("performed")
                     else f"not performed: {xor.get('reason')}")) + " |")
        L.append(f"| do the drawn and printed geometries coincide | "
                 f"{'yes, no process bias declared' if proc.get('identity') else 'no'} |")
        ret = m.get("reticle")
        if ret and ret.get("enabled"):
            L.append(f"| die | {ret['die_width_um']:.0f} x {ret['die_height_um']:.0f} um,"
                     f" label {ret['label']} |")
            L.append(f"| frame | seal ring {ret['seal_ring_width_um']:.0f} um,"
                     f" dicing lane {ret['dicing_lane_um']:.0f} um,"
                     f" {ret['alignment_marks']} overlay marks |")
            L.append(f"| process control monitors | "
                     + ", ".join(mo["structure"] for mo in ret.get("monitors", [])) + " |")
        else:
            L.append("| die assembly | not performed; the device cell alone was emitted |")
        L.append("")

    drc = m.get("drc")
    if drc and drc.get("enabled"):
        L.append("## DRC")
        L.append("")
        L.append("| rule | kind | limit (um) | violations | status |")
        L.append("|---|---|---:|---:|---|")
        for r in drc["results"]:
            L.append(f"| {r.get('name')} | {r.get('kind','-')} | {_fmt(r.get('value_um'))} | "
                     f"{r.get('violations','-')} | {r.get('status')} |")
        L.append("")

    ver = m.get("verify")
    if ver:
        L.append(f"## Verification - **{ver['verdict']}**")
        L.append("")
        L.append(f"{ver['n_pass']}/{ver['n_targets']} targets met. "
                 f"{ver['must_failures']} unmet at severity must; "
                 f"{ver['should_failures']} unmet at severity should. "
                 f"The verdict is set by the severity-must count alone.")
        L.append("")
        L.append("| metric | criterion | actual | unit | sev | status | source |")
        L.append("|---|---|---:|---|---|---|---|")
        for r in ver["rows"]:
            L.append(
                f"| `{r['metric']}` | {r['criterion']} | {_fmt(r['actual'])} | {r['unit']} | "
                f"{r['severity']} | {r['status']} | {r['source']} |"
            )
        L.append("")

    if doc.get("warnings"):
        L.append("## Warnings")
        L.append("")
        for w in doc["warnings"]:
            L.append(f"* {w}")
        L.append("")

    if figures:
        L.append("## Figures")
        L.append("")
        for f in figures:
            L.append(f"![{f.stem}](figures/{f.name})")
            L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# the sensitivity matrix, drawn
# --------------------------------------------------------------------------
def sensitivity_heatmap(record: dict, out_path: Path) -> Path | None:
    """Draw the elasticity and contribution matrices side by side.

    Two panels because the tables answer different questions and inviting the
    reader to compare a cell in one against the same cell in the other is the
    point. Elasticity ranks the knobs and is physics; contribution ranks the
    process and depends on how well each parameter is held.

    The elasticity scale is diverging and symmetric about zero, so sign is read
    from colour and magnitude from saturation. It is clipped at a robust
    percentile: a single large value would otherwise flatten every other cell to
    the same shade, and on this design one entry is twenty times the median. A
    clipped cell keeps its printed number, so nothing is concealed by the clip.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    params = list(record.get("parameters") or {})
    if not params:
        return None
    metrics = [m for m, v in (record.get("nominal") or {}).items() if v is not None]
    if not metrics:
        return None

    E = np.full((len(metrics), len(params)), np.nan)
    C = np.full((len(metrics), len(params)), np.nan)
    exc = record.get("excursions") or {}
    for j, p in enumerate(params):
        row = record["parameters"][p]
        nom = row.get("nominal") or 0.0
        for i, m in enumerate(metrics):
            e = (row.get("elasticity") or {}).get(m)
            if e is None or e != e:
                continue
            E[i, j] = e
            d = exc.get(p)
            if d is not None and nom:
                C[i, j] = abs(e) * abs(d) / abs(nom) * 100.0

    finite = E[np.isfinite(E)]
    lim = float(np.percentile(np.abs(finite), 90)) if finite.size else 1.0
    lim = max(lim, 1e-6)

    short_m = [m.split(".")[-1] for m in metrics]
    short_p = [p.split(".")[-1] for p in params]

    fig, ax = plt.subplots(1, 2, figsize=(3.2 + 1.35 * len(params) * 2, 1.4 + 0.46 * len(metrics)),
                           constrained_layout=True)

    im0 = ax[0].imshow(E, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax[0].set_title("elasticity  d(ln metric) / d(ln parameter)\nphysics: which knob moves what",
                    fontsize=9)
    fig.colorbar(im0, ax=ax[0], fraction=0.03, pad=0.02)

    cmax = float(np.nanmax(C)) if np.isfinite(C).any() else 1.0
    im1 = ax[1].imshow(C, cmap="YlOrRd", vmin=0.0, vmax=max(cmax, 1e-6), aspect="auto")
    ax[1].set_title("contribution over the declared excursion, %\nprocess: which one is a risk",
                    fontsize=9)
    fig.colorbar(im1, ax=ax[1], fraction=0.03, pad=0.02)

    for a, M, fmt in ((ax[0], E, "{:+.2f}"), (ax[1], C, "{:.1f}")):
        a.set_xticks(range(len(params)), short_p, rotation=35, ha="right", fontsize=8)
        a.set_yticks(range(len(metrics)), short_m, fontsize=8)
        for i in range(len(metrics)):
            for j in range(len(params)):
                v = M[i, j]
                if not np.isfinite(v):
                    a.text(j, i, "-", ha="center", va="center", fontsize=7, color="0.55")
                    continue
                rel = abs(v) / (lim if M is E else max(cmax, 1e-6))
                a.text(j, i, fmt.format(v), ha="center", va="center", fontsize=7,
                       color="white" if rel > 0.6 else "black")
        a.set_xticks(np.arange(-.5, len(params), 1), minor=True)
        a.set_yticks(np.arange(-.5, len(metrics), 1), minor=True)
        a.grid(which="minor", color="white", linewidth=1.0)
        a.tick_params(which="minor", length=0)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path
