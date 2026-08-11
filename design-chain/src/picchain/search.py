"""Directed search for a design that meets its declared targets.

A naive optimiser wrapped around the chain would fail in five distinct ways,
each of which was encountered while this baseline was being brought to a passing
configuration by hand. The procedure below is arranged so that each failure is
detected rather than suffered.

**A target may be unreachable by the knob chosen, at any value it can take.**
Weakening the Bragg mirror raises the Pockels lever, but the penetration depth
cannot exceed half the grating length, so the mode-hop-free range approaches
7.47 GHz and stops. A search that only descends a gradient spends its whole
budget approaching that asymptote and reports failure without saying why. The
bounds are therefore evaluated *before* any search, and the reachable interval of
every target is stated. Where a requirement lies outside every interval, the
answer is that no single parameter reaches it, and the binding bound is named.

**A metric may not be smooth in the parameter.** The mode-hop-free range measured
from zero bias moved between 0.37 and 6.86 GHz on cavities differing by a
fraction of a wavelength, because it was a property of the starting phase rather
than of the design. Bisecting on such a quantity converges on noise. Monotonicity
across the bracket is therefore checked, and a metric that fails the check is
reported as unsearchable rather than searched.

**One knob moves several targets.** The coupling constant sets the reflectivity,
the bandwidth and the tuning range together. Sensitivity is therefore measured as
a matrix over all declared parameters and all target metrics, and not one pair at
a time.

**Parameters constrain one another.** The facet-to-grating distance contains the
taper and cannot be shorter than it. Declared constraints are evaluated before a
point is run, and an infeasible point is skipped rather than clamped, a clamp
producing a geometry that no longer matches the model.

**Fixing one target degrades another.** Shortening the gain chip widened the
tuning range and doubled the linewidth. Every target is therefore evaluated at
every candidate, and what worsened is reported beside what improved.

Nothing here is a global optimiser. It is a bounded, instrumented search that
states what it can reach and what it cannot.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Design, Target, get_dotted


# --------------------------------------------------------------------------
# what a target asks for
# --------------------------------------------------------------------------
@dataclass
class Requirement:
    """A target reduced to an interval the metric must lie in."""
    metric: str
    severity: str
    lo: float | None
    hi: float | None
    source: str = ""

    def satisfied_by(self, x: float | None) -> bool:
        if x is None or x != x:
            return False
        if self.lo is not None and x < self.lo:
            return False
        if self.hi is not None and x > self.hi:
            return False
        return True

    def direction(self, x: float) -> int:
        """+1 if the metric must increase, -1 if it must decrease, 0 if met."""
        if self.lo is not None and x < self.lo:
            return 1
        if self.hi is not None and x > self.hi:
            return -1
        return 0

    def shortfall(self, x: float | None) -> float:
        """How far outside the interval, as a fraction of the nearer bound.

        Zero when satisfied. Expressed relatively so that requirements in
        different units may be ranked against one another.
        """
        if x is None or x != x:
            return float("inf")
        if self.lo is not None and x < self.lo:
            return (self.lo - x) / abs(self.lo) if self.lo else float("inf")
        if self.hi is not None and x > self.hi:
            return (x - self.hi) / abs(self.hi) if self.hi else float("inf")
        return 0.0

    def describe(self) -> str:
        if self.lo is not None and self.hi is not None:
            if math.isclose(self.lo, self.hi, rel_tol=1e-12):
                return f"= {self.lo:g}"
            return f"{self.lo:g} to {self.hi:g}"
        if self.lo is not None:
            return f">= {self.lo:g}"
        if self.hi is not None:
            return f"<= {self.hi:g}"
        return "unconstrained"


def requirement_from_target(t: Target) -> Requirement:
    """Reduce a declared target to an interval."""
    lo, hi = t.min, t.max
    if t.value is not None:
        tol = t.rel_tol if t.rel_tol is not None else 0.0
        lo = t.value - abs(t.value) * tol
        hi = t.value + abs(t.value) * tol
        if t.abs_tol is not None:
            lo = t.value - t.abs_tol
            hi = t.value + t.abs_tol
    return Requirement(metric=t.metric, severity=t.severity, lo=lo, hi=hi,
                       source=t.source or "")


# --------------------------------------------------------------------------
# constraints between parameters
# --------------------------------------------------------------------------
_CONSTRAINT = re.compile(r"^\s*([\w.]+)\s*(>=|<=|>|<)\s*([\w.]+|-?[\d.eE+]+)\s*$")


def check_constraints(design: Design, expressions: list[str]) -> list[str]:
    """Return the expressions that the design violates.

    Only the comparison of two dotted fields, or of a field against a number, is
    supported. A constraint that cannot be parsed is reported as violated rather
    than ignored, so that a typo cannot silently disable a check.
    """
    bad: list[str] = []
    for e in expressions:
        m = _CONSTRAINT.match(e)
        if not m:
            bad.append(f"{e}  (unparseable)")
            continue
        lhs, op, rhs = m.groups()
        try:
            a = float(get_dotted(design, lhs))
            b = float(rhs) if _is_number(rhs) else float(get_dotted(design, rhs))
        except Exception:
            bad.append(f"{e}  (field not found)")
            continue
        ok = {">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b}[op]
        if not ok:
            bad.append(f"{e}  ({lhs} = {a:g}, {rhs} = {b:g})")
    return bad


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------
# sensitivity
# --------------------------------------------------------------------------
@dataclass
class Sensitivity:
    """Normalised derivatives of every metric with respect to one parameter."""
    parameter: str
    nominal: float
    probed: float
    #: metric -> d(ln metric)/d(ln parameter)
    elasticity: dict[str, float] = field(default_factory=dict)

    def dominant(self, metrics: list[str]) -> tuple[str, float] | None:
        best = None
        for m in metrics:
            e = self.elasticity.get(m)
            if e is None or e != e:
                continue
            if best is None or abs(e) > abs(best[1]):
                best = (m, e)
        return best


def elasticity(nominal_value: float, probed_value: float,
               nominal_metric: float, probed_metric: float) -> float:
    """d(ln metric) / d(ln parameter), which is dimensionless.

    Expressed logarithmically so that parameters and metrics carrying different
    units and magnitudes can be compared in one table. Returns NaN where either
    quantity passes through zero, the logarithm being undefined there.
    """
    if nominal_value <= 0 or probed_value <= 0:
        return float("nan")
    if nominal_metric == 0 or probed_metric == 0:
        return float("nan")
    if nominal_metric * probed_metric < 0:
        return float("nan")
    dv = math.log(probed_value / nominal_value)
    if dv == 0:
        return float("nan")
    return math.log(abs(probed_metric / nominal_metric)) / dv


# --------------------------------------------------------------------------
# reachability
# --------------------------------------------------------------------------
@dataclass
class Reach:
    """What one parameter can do to one metric, across its declared range."""
    parameter: str
    metric: str
    at_min: float | None
    at_max: float | None
    monotone: bool

    @property
    def interval(self) -> tuple[float, float] | None:
        vals = [v for v in (self.at_min, self.at_max) if v is not None and v == v]
        if len(vals) < 2:
            return None
        return (min(vals), max(vals))

    def can_reach(self, req: Requirement) -> bool:
        iv = self.interval
        if iv is None:
            return False
        lo, hi = iv
        # the requirement is reachable if the achievable interval intersects it
        want_lo = req.lo if req.lo is not None else -math.inf
        want_hi = req.hi if req.hi is not None else math.inf
        return not (hi < want_lo or lo > want_hi)


def bracket_is_monotone(samples: list[float]) -> bool:
    """Whether a metric moves in one direction across the sampled bracket.

    A metric that does not is not searchable by bisection, and the fact is a
    finding about the metric rather than about the design.
    """
    vals = [v for v in samples if v is not None and v == v]
    if len(vals) < 3:
        return True
    d = [b - a for a, b in zip(vals, vals[1:])]
    pos = all(x >= 0 for x in d)
    neg = all(x <= 0 for x in d)
    return pos or neg


# --------------------------------------------------------------------------
# the solve
# --------------------------------------------------------------------------
def bisect_to_requirement(
    evaluate: Callable[[float], float | None],
    lo: float,
    hi: float,
    req: Requirement,
    max_iterations: int = 12,
    tolerance: float = 1e-3,
) -> tuple[float | None, list[tuple[float, float | None]]]:
    """Find a parameter value satisfying one requirement, by bisection.

    `evaluate` maps a parameter value to the metric. The bracket must already be
    known to contain a satisfying point; `Reach.can_reach` establishes that.
    Returns the value and every point evaluated, so the caller can report the
    path rather than only the answer.
    """
    trail: list[tuple[float, float | None]] = []
    f_lo = evaluate(lo); trail.append((lo, f_lo))
    if req.satisfied_by(f_lo):
        return lo, trail
    f_hi = evaluate(hi); trail.append((hi, f_hi))
    if req.satisfied_by(f_hi):
        return hi, trail
    if f_lo is None or f_hi is None:
        return None, trail

    # the target interval must be straddled for bisection to be meaningful
    d_lo, d_hi = req.direction(f_lo), req.direction(f_hi)
    if d_lo == d_hi:
        return None, trail

    a, b = lo, hi
    for _ in range(max_iterations):
        mid = 0.5 * (a + b)
        f_mid = evaluate(mid)
        trail.append((mid, f_mid))
        if req.satisfied_by(f_mid):
            return mid, trail
        if f_mid is None:
            return None, trail
        if req.direction(f_mid) == d_lo:
            a, f_lo, d_lo = mid, f_mid, req.direction(f_mid)
        else:
            b = mid
        if abs(b - a) <= tolerance * max(abs(lo), abs(hi), 1.0):
            break
    return None, trail


# --------------------------------------------------------------------------
# choosing a value for a parameter that several requirements share
# --------------------------------------------------------------------------
def score_point(values: dict[str, float | None], reqs: list[Requirement]) -> tuple[int, float]:
    """How good a candidate is, against EVERY requirement.

    Returns the number satisfied and the total relative shortfall, so a point is
    ranked first by how many requirements it meets and then by how close it is on
    the ones it misses.

    Scoring against every requirement rather than against the one being solved is
    what prevents a fix from breaking something that already worked. Solving the
    reflectivity and the bandwidth sequentially on the same control produced a
    mirror of 6 % reflectivity, a guide carrying two modes and a linewidth five
    times the requirement, each of those having been met before the solve began.
    """
    met = sum(1 for r in reqs if r.satisfied_by(values.get(r.metric)))
    short = 0.0
    for r in reqs:
        s = r.shortfall(values.get(r.metric))
        short += min(s, 1e6) if s == s else 1e6
    return met, short


def better(a: tuple[int, float], b: tuple[int, float]) -> bool:
    """Whether score `a` is preferable to score `b`."""
    if a[0] != b[0]:
        return a[0] > b[0]
    return a[1] < b[1]


def scan_grid(lo: float, hi: float, n: int) -> list[float]:
    """Evenly spaced values across a parameter's declared range.

    A scan rather than a solve. Where one control carries several requirements
    the satisfying set is an intersection of intervals, and a scan finds it
    without assuming the intervals overlap. Where the intersection is empty the
    scan says so, which a bisection on either requirement alone cannot.
    """
    if n < 2:
        return [0.5 * (lo + hi)]
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]
