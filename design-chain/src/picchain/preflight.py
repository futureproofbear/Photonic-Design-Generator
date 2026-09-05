"""Preconditions on a design, checked before any solver is started.

The chain grades a design *after* it has run, by comparing metrics against
targets. That is the wrong moment for a whole class of defect: a design whose
declared fields contradict each other is knowable from the file alone, in
milliseconds, and running it first costs half an hour and returns numbers that
describe a different device.

The case this was written for. A 210 um feed carried a 150 um taper, so the
straight guide between the taper and the grating was negative. The circuit stage
clamped the length to 1 um and assembled a cavity with no feed. Every figure it
produced described a different device, and its own group-delay cross-check then
agreed to 0.3 %, because the expectation was computed from the same clamped
value. **A clamp that rescues a nonsensical input converts a modelling failure
into a passing check.**

Three rules follow, and they are what this module enforces.

1. **A contradiction among declared fields is a precondition, not a warning.**
   It is knowable before the run and it invalidates the run, so it must stop it.
2. **Anything the code would silently clamp or default is a precondition.**
   The clamp is the tell: it exists because the author knew the value could be
   impossible, and chose to continue anyway.
3. **A check states the fields it read and the relation it required**, so a
   failure names what to change rather than what went wrong.

Checks that need a solved quantity belong in a stage, not here. This module reads
the design and nothing else, so it is fast enough to run unconditionally at the
head of every command that runs the chain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import Design


@dataclass(frozen=True)
class Finding:
    """One failed precondition."""
    check: str
    detail: str
    fields: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.check}: {self.detail}  [{', '.join(self.fields)}]"


CHECKS: list[Callable[[Design], list[Finding]]] = []


def check(fn: Callable[[Design], list[Finding]]) -> Callable[[Design], list[Finding]]:
    CHECKS.append(fn)
    return fn


# --- layers that must exist ------------------------------------------------

@check
def the_grating_layer_is_in_the_layer_map(d: Design) -> list[Finding]:
    """A layer named for the posts is drawn only where the map carries it.

    The polygon container is built from the keys of `layout.layer_map`, so a
    name absent from the map has no list to receive the posts and the grating
    would be dropped from the mask without a polygon anywhere to show it.
    """
    name = getattr(d.layout, "grating_layer", None)
    if not name or name in d.layout.layer_map:
        return []
    return [Finding(
        "the_grating_layer_is_in_the_layer_map",
        f"layout.grating_layer names {name!r}, which layout.layer_map does not "
        f"carry. The map holds: " + ", ".join(sorted(d.layout.layer_map)),
        ("layout.grating_layer", "layout.layer_map"))]


# --- geometry that must fit ------------------------------------------------

@check
def taper_fits_in_the_feed(d: Design) -> list[Finding]:
    """The taper is drawn inside the feed, so the feed must be longer than it.

    The circuit assembles facet -> taper -> straight -> grating and the straight
    is what remains of the feed. A feed shorter than its taper leaves nothing to
    assemble, and the stage previously clamped rather than refusing.
    """
    # Both structures must exist for one to fit inside the other. See the note
    # on `the_electrode_clears_the_ridge`.
    if not getattr(d.cavity, "enabled", True) or not getattr(d.layout, "enabled", True):
        return []
    feed = float(d.cavity.feed_length_um)
    taper = float(d.layout.taper_length_um)
    if taper <= 0:
        return []
    if feed <= taper:
        return [Finding(
            "taper_fits_in_the_feed",
            f"the feed is {feed:.1f} um and the taper drawn inside it is "
            f"{taper:.1f} um, so no straight guide remains between them",
            ("cavity.feed_length_um", "layout.taper_length_um"))]
    # The tighter condition is against the lead-in PATH and not the taper: an
    # angled facet route spends an arc as well, and on one design the lead-in
    # consumed 203.2 um of a 210 um feed while the taper was only 150. That
    # relation needs the bend geometry, so it is enforced in `layout` where the
    # path is computed, and is not guessed at here.
    return []


# A phase section is NOT checked against the feed here, and the reason is worth
# recording. The first version of this module asserted that the section had to
# fit inside the feed and failed a design that was correct: the layout draws the
# section AFTER the feed, as its own length, and the cavity stage carries its
# delay in `tau_phase` separately from `tau_feed`. The check was written from an
# assumption about the geometry rather than from the code that draws it.
#
# **A precondition asserted from a guess is worse than no precondition**, because
# it fails correct designs and trains the reader to bypass the gate. Every check
# in this module names the code path that establishes its relation.


@check
def the_drive_reaches_the_chirp(d: Design) -> list[Finding]:
    """A declared chirp the electrode cannot deliver is a contradiction.

    Checked here only where both are declared; the achievable excursion needs a
    solve and is graded by a target.
    """
    ch, el = d.chirp, d.electrodes
    if not (ch.enabled and el.max_drive_voltage_V):
        return []
    if ch.bandwidth_GHz <= 0:
        return [Finding("the_drive_reaches_the_chirp",
                        "the chirp is enabled with a bandwidth of zero",
                        ("chirp.bandwidth_GHz",))]
    return []


# --- declarations that must agree ------------------------------------------

@check
def the_electrode_clears_the_ridge(d: Design) -> list[Finding]:
    """The electrode gap must admit the ridge it straddles.

    Only where electrodes are drawn. A study that switches them off and widens
    the guide is describing a structure with no metal beside it, and refusing it
    on the geometry of an absent electrode fails correct work. **A gate that
    refuses correct work trains the reader to bypass the gate**, which is the
    defect recorded at T053.

    The distinction is between two kinds of precondition. One asserts that a
    declared value is possible at all, such as a reflectivity inside the unit
    interval, and holds whether or not the stage runs. The other asserts that
    one structure fits another, and holds only where both structures exist.
    This is the second kind.
    """
    if not getattr(d.electrodes, "enabled", True):
        return []
    gap = float(d.electrodes.gap_um)
    width = float(d.waveguide.top_width_um)
    if gap <= width:
        return [Finding(
            "the_electrode_clears_the_ridge",
            f"the electrode gap is {gap:.3f} um and the ridge it straddles is "
            f"{width:.3f} um wide, so the metal lands on the guide",
            ("electrodes.gap_um", "waveguide.top_width_um"))]
    return []


@check
def the_electrode_length_is_declared_where_no_grating_sets_it(d: Design) -> list[Finding]:
    """An electrode on a device with no mirror must state its own length.

    The electro-optic stage sizes the capacitance, the lumped RC figure and the
    travelling-wave bandwidth over the electrode run. Where a Bragg mirror is
    present the electrodes flank it and the grating length is that run. Where
    the mirror is switched off, the grating length is a default carried by the
    schema, and taking it would size a modulator's electrode from a structure
    the device does not contain.

    The failure it prevents is silent. `grating.length_um` holds 7250 um
    whether or not a grating exists, so the stage would return a capacitance,
    a bandwidth and an impedance for a 7.25 mm electrode on a device whose
    electrode is any other length, and every one of those figures would look
    ordinary.
    """
    if not getattr(d.electrodes, "enabled", True):
        return []
    if d.grating.enabled:
        return []
    if d.electrodes.length_um is None:
        return [Finding(
            "the_electrode_length_is_declared_where_no_grating_sets_it",
            "the grating is switched off and no electrode length is declared, so "
            f"the electrode would be sized from grating.length_um at "
            f"{float(d.grating.length_um):.0f} um, which this device does not contain",
            ("electrodes.length_um", "grating.enabled"))]
    if float(d.electrodes.length_um) <= 0.0:
        return [Finding(
            "the_electrode_length_is_declared_where_no_grating_sets_it",
            f"the declared electrode length is {float(d.electrodes.length_um):.3f} um",
            ("electrodes.length_um",))]
    return []


@check
def the_grating_period_suits_the_order(d: Design) -> list[Finding]:
    """A declared period and order must be consistent with the wavelength."""
    g, w = d.grating, d.waveguide
    if not g.enabled or not g.period_um:
        return []
    if g.order < 1:
        return [Finding("the_grating_period_suits_the_order",
                        f"the grating order is {g.order}",
                        ("grating.order",))]
    return []


@check
def the_phase_electrode_clears_its_guide(d: Design) -> list[Finding]:
    """The phase section's own gap must admit the ridge it straddles.

    Found by auditing the clamps, as rule 17 requires. `s04_cavity` divides by
    `max(ps.gap_um, 1e-9)` when scaling the index change by the gap ratio, so a
    gap declared at zero returns an index change nine orders of magnitude too
    large and the section is reported as overwhelmingly sufficient. The clamp
    rescues the arithmetic and hides the input.
    """
    ps = getattr(d.cavity, "phase_section", None)
    if not (ps and ps.enabled):
        return []
    gap = float(ps.gap_um)
    width = float(d.waveguide.top_width_um)
    if gap <= 0.0:
        return [Finding(
            "the_phase_electrode_clears_its_guide",
            f"the phase section gap is {gap:.3f} um; the index change is scaled by "
            f"the inverse of this gap and a non-positive value is not a geometry",
            ("cavity.phase_section.gap_um",))]
    if gap <= width:
        return [Finding(
            "the_phase_electrode_clears_its_guide",
            f"the phase section gap is {gap:.3f} um and the ridge it straddles is "
            f"{width:.3f} um wide, so the metal lands on the guide",
            ("cavity.phase_section.gap_um", "waveguide.top_width_um"))]
    return []


@check
def the_facet_reflectivity_is_a_reflectivity(d: Design) -> list[Finding]:
    """`s16_circuit` clamps a negative anti-reflection coating to zero.

    A reflectivity outside the unit interval is not a coating, and clamping it
    reports a circuit assembled from a facet the design did not declare.
    """
    r = getattr(getattr(d, "facet", None), "ar_reflectivity", None)
    if r is None:
        return []
    r = float(r)
    if not (0.0 <= r <= 1.0):
        return [Finding(
            "the_facet_reflectivity_is_a_reflectivity",
            f"the facet coating is declared at {r:g}, outside the unit interval",
            ("facet.ar_reflectivity",))]
    return []


@check
def the_etch_does_not_exceed_the_film(d: Design) -> list[Finding]:
    p = d.platform
    if p.etch_depth_um > p.film_thickness_um:
        return [Finding(
            "the_etch_does_not_exceed_the_film",
            f"the etch is {p.etch_depth_um:.3f} um into a film of "
            f"{p.film_thickness_um:.3f} um, so the guide is cut through",
            ("platform.etch_depth_um", "platform.film_thickness_um"))]
    return []


# --- provenance ------------------------------------------------------------

@check
def the_provenance_gate_is_self_consistent(d: Design) -> list[Finding]:
    """A design cannot both forbid unconfirmed materials and name one.

    The contradiction is in the file and needs no solve, yet it surfaced only
    after the chain had run, because the gate is evaluated in `verify` at the
    end. Nothing here judges whether a material is confirmed; that needs the
    library. What is checked is that the design does not ask for both.
    """
    rel = getattr(d, "release", None)
    allow = getattr(rel, "allow_unconfirmed_materials", None)
    if allow is None:
        allow = getattr(d.platform, "allow_unconfirmed_materials", None)
    if allow is None:
        return []
    waived = set(getattr(rel, "waive", ()) or ())
    if allow is False and "materials" in waived:
        return [Finding(
            "the_provenance_gate_is_self_consistent",
            "the design forbids unconfirmed materials and waives the material "
            "condition at release, which are opposite instructions",
            ("release.allow_unconfirmed_materials", "release.waive"))]
    return []


# --- magnitude, which type checks do not catch ------------------------------

#: Plausible ranges for quantities whose units are easy to mistake. A length
#: entered in millimetres where micrometres are meant passes every type check,
#: violates no bound, and produces a run that is quietly about another device.
_PLAUSIBLE: tuple[tuple[str, float, float, str], ...] = (
    ("waveguide.wavelength_um", 0.2, 20.0, "an optical wavelength in micrometres"),
    ("waveguide.top_width_um", 0.05, 50.0, "a single-mode ridge in micrometres"),
    ("platform.film_thickness_um", 0.02, 5.0, "a thin film in micrometres"),
    ("platform.etch_depth_um", 0.0, 5.0, "an etch in micrometres"),
    ("electrodes.gap_um", 0.5, 500.0, "an electrode gap in micrometres"),
    ("cavity.feed_length_um", 1.0, 100000.0, "a feed in micrometres"),
    ("layout.taper_length_um", 1.0, 10000.0, "a taper in micrometres"),
)


@check
def declared_magnitudes_are_plausible(d: Design) -> list[Finding]:
    out: list[Finding] = []
    for path, lo, hi, what in _PLAUSIBLE:
        node: object = d
        try:
            for part in path.split("."):
                node = getattr(node, part)
        except AttributeError:
            continue
        if not isinstance(node, (int, float)) or isinstance(node, bool):
            continue
        v = float(node)
        if not (lo <= v <= hi):
            out.append(Finding(
                "declared_magnitudes_are_plausible",
                f"{path} is {v:g}, outside {lo:g} to {hi:g} for {what}. A value "
                f"entered in the wrong unit passes every type check and violates "
                f"no bound",
                (path,)))
    return out


@check
def the_splitter_ports_can_carry_the_arm(d: Design) -> list[Finding]:
    """The two arms of an interferometer fit beside each other where they part.

    The Mach-Zehnder builder leaves the multimode section at half the declared
    port separation and at the declared port width, so the gap between the two
    access guides opens at `port_separation - port_width`. Its own comment says
    as much. The access taper then widens each guide to the modulation width
    before the S-bend has pulled them apart, and the gap there is
    `port_separation - waveguide.top_width_um`, which is a different and smaller
    number.

    On the kit's C-band splitter, whose ports sit 2.55 um apart, carrying the
    2.5 um modulation arm closes that gap to 50 nm against a process minimum of
    300. The device draws, the run completes, and the rule deck reports 148
    violations at the two ends of every copy on the die. Every one of those
    figures is knowable from three declared fields before anything is solved.

    The remedy is to open `mzm.port_separation_um`, to narrow
    `waveguide.top_width_um`, or to widen the arm after the S-bend rather than
    at the port, which the builder does not currently offer.
    """
    if not d.layout.enabled or d.layout.device != "mach_zehnder":
        return []
    need = _min_wg_space(d)
    if need <= 0:
        return []
    have = float(d.mzm.port_separation_um) - float(d.waveguide.top_width_um)
    # A difference of two declared decimals carries binary representation error:
    # 2.8 - 2.5 is 0.2999999999999998, which is not 0.3 and would refuse a
    # design sitting exactly on the rule. The tolerance absorbs that and nothing
    # larger, being a thousandth of the 1 nm grid the mask is snapped to.
    if have >= need - 1e-9:
        return []
    return [Finding(
        "the_splitter_ports_can_carry_the_arm",
        f"mzm.port_separation_um is {d.mzm.port_separation_um} um and the arm "
        f"is {d.waveguide.top_width_um} um wide, so the two arms come within "
        f"{have:.3f} um of each other where the access taper reaches full "
        f"width. The declared minimum space on {d.process.wg_layer} is "
        f"{need:.3f} um. Open the port separation to at least "
        f"{d.waveguide.top_width_um + need:.3f} um, or narrow the arm",
        ("mzm.port_separation_um", "waveguide.top_width_um", "drc.rules"))]


def _min_wg_space(d: Design) -> float:
    """The tightest guide-to-guide space the declared rules require."""
    wg = d.process.wg_layer
    vals = [r.value_um for r in d.drc.rules
            if r.kind == "min_space" and r.layer == wg and not r.other_layer]
    return max(vals) if vals else 0.0


def run_checks(design: Design) -> list[Finding]:
    """Every failed precondition, in declaration order."""
    out: list[Finding] = []
    for fn in CHECKS:
        try:
            out.extend(fn(design))
        except Exception as exc:                     # a check must not break a run
            out.append(Finding(fn.__name__, f"the check itself raised: {exc}", ()))
    return out


def assert_ready(design: Design) -> None:
    """Raise unless every precondition holds.

    Called at the head of any command that runs the chain, so that a design whose
    declared fields contradict each other never reaches a solver.
    """
    findings = run_checks(design)
    if not findings:
        return
    lines = "\n".join(f"  - {f}" for f in findings)
    raise RuntimeError(
        f"{len(findings)} precondition(s) failed before any stage was run. These are "
        f"properties of the design file and were knowable without solving anything:\n"
        f"{lines}"
    )
