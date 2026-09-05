"""Where the CORNERSTONE SiN 200 nm kit's compact models fail physics, and why.

`tools/check_pdk_models.py` reports which models are unphysical. This asks the
next question, which is what the failures have in common, and the answer turns
out to be one property of the port arrangement.

Three quantities are taken from each tabulated scattering matrix. The worst
power leaving for one unit entering, over every channel and every wavelength
sampled. The worst departure from reciprocity. And, for a two-channel device,
the transmission in each direction separately, since a violation that sits in
one direction alone is a normalisation and a violation in both is a solver.

Every model is then classed by whether its ports carry waveguides of one width
or of more than one. That is measured rather than assumed: the black box the kit
ships for each cell draws its pins on layer 1/10 with the width of the waveguide
each terminates, so the class is read off the file. Classing by the cell name
was tried first and agrees, and a polygon is the better authority.

No scattering matrix, no geometry between the ports and no file of the kit is
copied. Only counts, verdicts and correlations are printed.

    python examples/cs_sin200_models/scripts/model_audit.py [pdk_dir]
"""

from __future__ import annotations

import collections
import csv
import glob
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / "design-chain" / "pdk" / "wp_cs_sin_200nm_gf_pdk_v0_0_1"
TOL = 1e-3

_PORT = re.compile(r"^s_(\d+)@(\w+)_(\d+)@(\w+)_(re|im)$")
_HASH = re.compile(r"([0-9a-f]{24})")
PIN_LAYER = (1, 10)


def cell_names(pdk: Path) -> dict[str, tuple[str, int]]:
    """Which cell declares each scattering-matrix file, and in which band."""
    out: dict[str, tuple[str, int]] = {}
    for mod in glob.glob(str(pdk / "**" / "wl*" / "**" / "__init__.py"), recursive=True):
        band = int(re.search(r"wl(\d+)", mod).group(1))
        src = Path(mod).read_text(encoding="utf-8")
        for m in re.finditer(r"def (\w+)\(.*?(?=\ndef |\Z)", src, re.S):
            for h in set(_HASH.findall(m.group(0))):
                out.setdefault(h, (m.group(1), band))
    return out


def pin_widths(gds: str) -> list[float]:
    """The port widths, measured off the black box the kit ships.

    A cell of this kit imports a GDS holding an outline, a label and its pins,
    and the pins are drawn on 1/10 with the width of the waveguide they
    terminate. So the one geometric property that matters here is readable even
    though the device between the ports is not, which is chain rule 11 applied
    to what the file does carry.

    Classing by the cell name instead was tried and it agrees, but a name is a
    statement and a polygon is the thing.
    """
    import klayout.db as kdb

    ly = kdb.Layout()
    ly.read(gds)
    dbu = ly.dbu
    out = []
    for sh in ly.top_cell().shapes(ly.layer(*PIN_LAYER)).each():
        b = sh.bbox()
        out.append(round(max(b.right - b.left, b.top - b.bottom) * dbu, 4))
    return sorted(out)


def ports_differ(widths: list[float]) -> bool | None:
    """Whether the drawn pins carry more than one width."""
    if not widths:
        return None
    return len(set(widths)) > 1


def read(path: str):
    """The channel list and the matrix at each wavelength."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    pairs: dict[tuple[str, str], tuple[str, str]] = {}
    for key in rows[0]:
        m = _PORT.match(key)
        if m and m.group(5) == "re":
            pairs[(f"{m.group(1)}@{m.group(2)}",
                   f"{m.group(3)}@{m.group(4)}")] = (key, key[:-2] + "im")
    channels = sorted({i for i, _ in pairs} | {j for _, j in pairs})
    return rows, pairs, channels


def measure(path: str) -> dict:
    rows, pairs, ch = read(path)
    if not pairs:
        return {}
    worst_p, worst_r = 0.0, 0.0
    fwd, rev = 0.0, 0.0
    for row in rows:
        def s(i, j):
            k = pairs.get((i, j))
            return 0j if k is None else complex(float(row[k[0]]), float(row[k[1]]))
        for j in ch:
            worst_p = max(worst_p, sum(abs(s(i, j)) ** 2 for i in ch))
        for a in ch:
            for b in ch:
                if b > a:
                    worst_r = max(worst_r, abs(s(a, b) - s(b, a)))
        if len(ch) == 2:
            a, b = ch
            fwd = max(fwd, abs(s(b, a)) ** 2)
            rev = max(rev, abs(s(a, b)) ** 2)
    return {"power": worst_p, "reciprocity": worst_r,
            "forward": fwd, "reverse": rev, "channels": len(ch),
            "ports": len({c.split("@")[0] for c in ch})}


def main(argv: list[str]) -> int:
    pdk = Path(argv[1]) if len(argv) > 1 else DEFAULT
    names = cell_names(pdk)
    files = sorted(glob.glob(str(pdk / "**" / "sparams" / "*.csv"), recursive=True))
    if not files:
        print(f"no tabulated models under {pdk}")
        return 1

    black_boxes = {
        _HASH.search(Path(g).name).group(1): g
        for g in glob.glob(str(pdk / "**" / "gds" / "*_BB.gds"), recursive=True)
        if _HASH.search(Path(g).name)
    }

    rows = []
    for f in files:
        h = _HASH.search(Path(f).name)
        key = h.group(1) if h else ""
        name, band = names.get(key, ("", 0))
        m = measure(f)
        if not m:
            continue
        gds = black_boxes.get(key)
        widths = pin_widths(gds) if gds else []
        rows.append(dict(m, name=name, band=band, cls=ports_differ(widths),
                         widths=widths))
    unmatched = sum(1 for r in rows if not r["widths"])
    if unmatched:
        print(f"{unmatched} models have no black box to read pins from\n")

    print(f"{len(rows)} tabulated models under {pdk.name}\n")

    label = {False: "every drawn pin one width", True: "pins of differing width",
             None: "no pin drawn"}
    print(f"{'class':28} {'models':>7} {'above unity':>12} {'worst':>8} {'median':>8}")
    for cls in (False, True, None):
        v = [r for r in rows if r["cls"] is cls]
        if not v:
            continue
        p = sorted(r["power"] for r in v)
        print(f"{label[cls]:28} {len(v):7d} "
              f"{sum(1 for x in p if x > 1 + TOL):12d} {max(p):8.4f} "
              f"{statistics.median(p):8.4f}")
    over = [r for r in rows if r["power"] > 1 + TOL]
    mixed = [r for r in over if r["cls"] is True]
    print(f"\n{len(over)} models deliver more power than they were given, and "
          f"{len(mixed)} of those {len(over)} have ports of differing width")

    print("\nby family")
    fam = collections.defaultdict(list)
    for r in rows:
        fam[re.split(r"_", r["name"])[0] or "unnamed"].append(r)
    print(f"{'family':22} {'models':>7} {'channels':>9} {'worst':>8} {'over unity':>11}")
    for k, v in sorted(fam.items(), key=lambda kv: -max(r["power"] for r in kv[1])):
        print(f"{k:22} {len(v):7d} {v[0]['channels']:9d} "
              f"{max(r['power'] for r in v):8.4f} "
              f"{sum(1 for r in v if r['power'] > 1 + TOL):11d}")

    two = [r for r in rows if r["channels"] == 2 and r["cls"] is True
           and r["name"].startswith("Taper")]
    if two:
        print(f"\nthe two-channel case, where a direction can be separated "
              f"({len(two)} tapers)")
        f_over = sum(1 for r in two if r["forward"] > 1 + TOL)
        r_over = sum(1 for r in two if r["reverse"] > 1 + TOL)
        print(f"  the forward direction exceeds unity in {f_over} of {len(two)}")
        print(f"  the reverse direction exceeds unity in {r_over} of {len(two)}")
        print(f"  the worst forward is {max(r['forward'] for r in two):.4f} "
              f"and the worst reverse {max(r['reverse'] for r in two):.4f}")

        ratios, excess = [], []
        for r in two:
            m = re.match(r"Taper_wi([\dp]+)_wo([\dp]+)$", r["name"])
            if m:
                wi = float(m.group(1).replace("p", "."))
                wo = float(m.group(2).replace("p", "."))
                ratios.append(wo / wi)
                excess.append(r["power"])
        if len(ratios) > 2:
            print(f"  the width ratio spans {min(ratios):.1f} to {max(ratios):.1f} "
                  f"and correlates with the excess at {corr(ratios, excess):+.3f}")
            bands = [r["band"] for r in two]
            print(f"  the design wavelength correlates with it at "
                  f"{corr(bands, excess):+.3f}")

    recip = [r for r in rows if r["reciprocity"] > 5e-3]
    print(f"\n{len(recip)} models break reciprocity by more than 0.005, the worst by "
          f"{max((r['reciprocity'] for r in recip), default=0):.4f}")
    both = [r for r in recip if r["power"] > 1 + TOL]
    print(f"{len(both)} of those {len(recip)} are also above unity")

    multimode = [r for r in rows if r["channels"] > r["ports"]]
    print(f"\n{len(multimode)} models carry more channels than ports, being "
          f"multimode. A reader keying on the port number alone mis-tests every "
          f"one of them")
    return 0


def corr(xs, ys) -> float:
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
