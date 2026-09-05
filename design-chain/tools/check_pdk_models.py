#!/usr/bin/env python3
"""Test every compact model a process design kit ships against physics.

A kit states the behaviour of its cells so that a circuit can be assembled from
them without solving each one. Those statements are fits and tabulations, and
nothing in a kit checks them: a polynomial fitted to a magnitude is free to
return a negative one, and a scattering matrix tabulated from a simulation is
free to deliver more power than it was given. A circuit assembled from such a
model draws energy from nowhere, and the symptom appears as a result rather
than as an error.

Three properties are tested here and none of them depends on the device.

**Passivity.** For every input port, the power leaving through all ports may not
exceed the power entering. A passive splitter, coupler or crossing that returns
more than unity is unphysical whatever its geometry.

**Realisability.** A magnitude is not negative and a transmission is not above
one. A fit unconstrained at its edges breaks this before it breaks passivity.

**Reciprocity.** A structure of reciprocal materials satisfies S_ij = S_ji. A
tabulated matrix that does not is either a solver artefact or a mislabelled
port.

A channel is a port and a mode together, and the three tests are applied over
channels. A kit carrying a mode converter labels its entries `s_2@TE1_1@TE0` and
the rest, and a reader keying on the port number alone silently discards every
cross-mode term.

Nothing is written. The vendor's own numbers are read and only the verdict is
reported, so a kit under a licence forbidding redistribution may be tested
without any part of it being copied into a tracked file.

    python design-chain/tools/check_pdk_models.py [pdk_dir ...]
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

TOL = 1e-3          # power may exceed unity by this before it is reported
ROOT = Path(__file__).resolve().parents[1] / "pdk"


# ---------------------------------------------------------------- polynomials
def _poly_models(pdk: Path) -> list[tuple[str, Path]]:
    return [(p.stem, p) for p in sorted(pdk.rglob("data/*.json"))]


def check_polynomial(tag: str, path: Path) -> list[str]:
    """A model held as polynomial coefficients about a centre wavelength."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{tag}: unreadable, {exc}"]
    if "center_wavelength" not in d:
        return []
    wl0 = float(d["center_wavelength"])
    span = 0.06 if wl0 > 1.0 else 0.03
    lam = [wl0 - span + i * (2 * span / 24) for i in range(25)]

    def ev(key):
        c = list(d[key])[::-1]
        return [sum(a * (x - wl0) ** i for i, a in enumerate(c)) for x in lam]

    mags = {k: ev(k) for k in d if k.endswith("_abs")}
    out: list[str] = []

    negative = {k: min(v) for k, v in mags.items() if min(v) < 0}
    for k, v in sorted(negative.items(), key=lambda kv: kv[1]):
        out.append(f"{tag}: {k} reaches {v:+.4f}, and a magnitude is not negative")

    # power leaving, for the port arrangement the keys imply
    if "pol_trans_abs" in mags:                       # one in, two out
        power = [2 * t * t + r * r for t, r in
                 zip(mags["pol_trans_abs"], mags.get("pol_refl_in_abs", [0] * len(lam)))]
    elif "pol_trans_bar_abs" in mags:                 # two in, two out
        power = [b * b + c * c + rb * rb + rc * rc for b, c, rb, rc in zip(
            mags["pol_trans_bar_abs"], mags["pol_trans_cross_abs"],
            mags.get("pol_refl_bar_abs", [0] * len(lam)),
            mags.get("pol_refl_cross_abs", [0] * len(lam)))]
    else:
        return out

    worst = max(power)
    over = [x for x in power if x > 1.0 + TOL]
    if over:
        frac = 100.0 * len(over) / len(power)
        out.append(f"{tag}: power out reaches {worst:.4f} of power in, above unity at "
                   f"{frac:.0f} % of the band sampled")
    return out


# ------------------------------------------------------------- tabulated S(f)
_PORT = re.compile(r"^s_(\d+)@(\w+)_(\d+)@(\w+)_(re|im)$")


def check_tabulated(path: Path) -> list[str]:
    """A model held as a scattering matrix against wavelength."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except (OSError, ValueError) as exc:
        return [f"{path.name}: unreadable, {exc}"]
    if not rows:
        return [f"{path.name}: empty"]

    #: A channel is a port and a mode together. Keying on the port number alone
    #: collapses the sixteen entries of a two-port two-mode device into four,
    #: and the last one read wins. Every mode converter and mode splitter in the
    #: CORNERSTONE SiN kit was then reported as passing under two per cent of
    #: its power, which is an artefact of the reader and not a property of the
    #: model. The key is the pair of channels.
    pairs: dict[tuple[str, str], tuple[str, str]] = {}
    for key in rows[0]:
        m = _PORT.match(key)
        if m and m.group(5) == "re":
            out_ch = f"{m.group(1)}@{m.group(2)}"
            in_ch = f"{m.group(3)}@{m.group(4)}"
            pairs[(out_ch, in_ch)] = (key, key[:-2] + "im")
    if not pairs:
        return []
    channels = sorted({i for i, _ in pairs} | {j for _, j in pairs})

    worst_power = 0.0
    worst_recip = 0.0
    for row in rows:
        def s(i, j):
            k = pairs.get((i, j))
            if k is None:
                return 0j
            return complex(float(row[k[0]]), float(row[k[1]]))
        for j in channels:
            p = sum(abs(s(i, j)) ** 2 for i in channels)
            worst_power = max(worst_power, p)
        for a in channels:
            for b in channels:
                if b > a:
                    worst_recip = max(worst_recip, abs(s(a, b) - s(b, a)))

    out: list[str] = []
    if worst_power > 1.0 + TOL:
        out.append(f"{path.name}: {worst_power:.4f} of the power in leaves, "
                   f"which a passive device cannot do")
    if worst_recip > 5e-3:
        out.append(f"{path.name}: reciprocity broken by {worst_recip:.4f}")
    if len(channels) > len({c.split("@")[0] for c in channels}):
        # a multimode model, which is the case the port-keyed reader broke on
        out.append(f"{path.name}: read as {len(channels)} channels over "
                   f"{len({c.split('@')[0] for c in channels})} ports")
    return out


# ---------------------------------------------------------------------- sweep
def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or ([ROOT] if ROOT.is_dir() else [])
    if not roots:
        print("no PDK directory given and none found under design-chain/pdk/")
        return 2

    findings: list[str] = []
    n_poly = n_tab = 0
    for root in roots:
        for tag, path in _poly_models(root):
            n_poly += 1
            findings += check_polynomial(tag, path)
        for path in sorted(root.rglob("sparams/*.csv")):
            n_tab += 1
            findings += check_tabulated(path)

    print(f"{n_poly} polynomial models and {n_tab} tabulated matrices tested "
          f"under {', '.join(str(r) for r in roots)}")
    if not findings:
        print("every model tested is passive, realisable and reciprocal")
        return 0

    print(f"\n{len(findings)} finding(s):\n")
    for f in findings:
        print("  " + f)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
