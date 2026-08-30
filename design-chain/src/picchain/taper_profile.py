"""The width profile of a taper, in one place.

The eigenmode-expansion stage evaluates a taper and the layout stage draws one.
Where each carried its own profile, the two diverged: a quadratic profile was
evaluated and returned an adiabaticity margin of 5.656 against a floor of 3.0,
while the mask drew a single linear trapezoid whose margin on the same data is
2.407, below the floor. The stage reported a structure the mask does not carry,
and the warning that would have failed the run was never raised.

Both stages now call `widths_at` and the divergence cannot recur.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

Profile = Literal["linear", "raised_sine", "quadratic"]


def shape(u: np.ndarray | float, profile: str) -> np.ndarray | float:
    """The normalised width, rising from 0 at the tip to 1 at the full width."""
    if profile == "linear":
        return u
    if profile == "raised_sine":
        # the rate of change vanishes at both ends, which is the usual remedy
        # where a linear taper is too abrupt at its tip
        return u - np.sin(2.0 * np.pi * np.asarray(u)) / (2.0 * np.pi)
    if profile == "quadratic":
        return np.asarray(u) ** 2
    raise ValueError(f"unknown taper profile {profile!r}")


def widths_at(tip: float, full: float, u: np.ndarray | float,
              profile: str) -> np.ndarray | float:
    """The width at fractional position `u` along the taper."""
    return tip + (full - tip) * shape(u, profile)


def slice_widths(tip: float, full: float, n: int, profile: str) -> np.ndarray:
    """Section-centre widths for a staircase of `n` slices."""
    return np.asarray(widths_at(tip, full, (np.arange(n) + 0.5) / n, profile))


def outline(tip: float, full: float, length: float, profile: str,
            segments: int = 64, x0: float = 0.0, reverse: bool = False,
            y0: float = 0.0) -> list[tuple[float, float]]:
    """The taper as one closed polygon, tip at `x0` unless reversed.

    The polygon follows the same profile the eigenmode stage evaluates, sampled
    at `segments + 1` stations, so the drawn edge and the solved edge are the
    same curve to within the sampling.
    """
    u = np.linspace(0.0, 1.0, int(segments) + 1)
    w = np.asarray(widths_at(tip, full, u, profile), dtype=float)
    x = x0 + (length * (1.0 - u) if reverse else length * u)
    lower = [(float(xi), float(y0 - wi / 2.0)) for xi, wi in zip(x, w)]
    upper = [(float(xi), float(y0 + wi / 2.0)) for xi, wi in zip(x, w)]
    return lower + upper[::-1]
