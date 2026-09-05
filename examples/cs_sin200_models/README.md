# The compact models of the CORNERSTONE SiN 200 nm kit

The kit ships 1092 tabulated scattering matrices covering 33 wavelength bands
from 493 to 1550 nm. A circuit is assembled from them without solving any cell,
so what they assert is what a design is built on. This tests those assertions
against physics.

Conducted 2026-09-04 and 2026-09-05.

## What may be written down, and what may not

**This kit is proprietary and its licence forbids redistribution or sharing in
whole or in part.** That is unlike the Luxtelligence LTOI300 kit the sibling
studies examine, which is under an MIT licence and whose dimensions are quoted
freely. The kit is excluded from version control by `.gitignore`, along with
every other vendored kit.

Everything below is a measurement made on the kit rather than a copy of it: a
count, a verdict, a correlation, and the handful of cell names needed to say
which class of model is affected. No scattering matrix, no geometry, no rule and
no file of the kit is reproduced here or anywhere in this repository.
[`scripts/model_audit.py`](scripts/model_audit.py) prints only counts and
verdicts by construction, and a reader without the kit can read the conclusions
without being given the thing they describe.

**A reader intending to publish this study should confirm that the framing above
is acceptable to the licensor.** The judgement made here is that reporting a
defect one has measured in a product is not redistribution of that product. That
judgement is stated rather than assumed.

## The two things every model in the kit declares

Each matrix arrives with a short metadata file, and all 1092 of them say the
same two things.

| | |
| --- | --- |
| `simulation.is_3d` | `false`, on all 1092 |
| `simulation.dispersive` | `false`, on all 1092 |

Each matrix is tabulated against wavelength at 101 or 202 points spanning about
two per cent about its design wavelength. So the models are two-dimensional
reductions with the material index frozen at band centre, swept over a narrow
band.

**The first of those is a known and quantified weakness on a confining stack and
a worse one here.** The companion study of the LTOI300 multimode splitters
established that collapsing the vertical dimension moves the self-imaging length
of a multimode section by seven to ten per cent, on a 300 nm lithium tantalate
ridge whose vertical confinement is strong. A 200 nm nitride film in oxide
confines far more weakly, the index step being 2.00 against 1.44 rather than
2.14 against 1.44 over a thicker film, so the vertical mode extends further into
the cladding and the reduction has more to discard. The kit's own multimode
interference models are all passive and none can be checked against a length
without geometry, so what follows measures the second declaration instead.

## What the frozen material index costs

A transmission barely notices a two per cent band. A group index is made of
nothing else.

[`scripts/dispersion_cost.py`](scripts/dispersion_cost.py) solves a nitride
strip twice: once with the nitride and the oxide dispersing as the literature
says they do, and once with both frozen at band centre, which is what a
non-dispersive simulation does. The group index follows from a central
difference in wavelength in each case.

| Band | Width | `n_eff` | `n_g`, dispersing | `n_g`, frozen | Error |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 532 nm | 0.50 um | 1.82777 | 2.24721 | 2.13783 | **−4.87 %** |
| 637 nm | 0.60 um | 1.77187 | 2.17492 | 2.10111 | −3.39 % |
| 780 nm | 0.70 um | 1.70653 | 2.10020 | 2.05095 | −2.35 % |
| 850 nm | 0.75 um | 1.67999 | 2.06691 | 2.02456 | −2.05 % |
| 1064 nm | 0.90 um | 1.61435 | 1.97199 | 1.94052 | −1.60 % |
| 1310 nm | 1.10 um | 1.56296 | 1.87682 | 1.84831 | −1.52 % |
| 1550 nm | 1.30 um | 1.52710 | 1.80164 | 1.77152 | **−1.67 %** |

The widths are this study's choice, holding the guide near single mode at each
band, and are taken from no cell. The materials are Luke 2015 for the nitride
and Malitson 1965 for the oxide, both now in
[`pdk/materials.yaml`](../../design-chain/pdk/materials.yaml). The nitride
entry carried a constant 1.996 until this study and now carries the dispersion,
which passes through 1.99637 at 1550 nm.

**A free spectral range computed from these models is too large by between one
and a half and five per cent, and a delay is too small by the same.** The error
is the material's own dispersion weighted by the fraction of the mode sitting in
the nitride: the material group index exceeds its phase index by 0.132 at 532 nm
and by 0.043 at 1550, and the measured errors imply a confinement between 0.7
and 0.83, which is what these widths should give.

The consequence is worst where the kit's coverage is densest. Twenty-six of the
33 bands lie below 1100 nm, and the error there runs from two to five per cent.
A ring designed for a 100 GHz free spectral range at 532 nm lands near 105.

## Where the models break passivity, and what the failures share

`python design-chain/tools/check_pdk_models.py` reports the violations.
[`scripts/model_audit.py`](scripts/model_audit.py) asks what they have in
common.

| Class, from the drawn pins | Models | Above unity | Worst | Median |
| --- | ---: | ---: | ---: | ---: |
| Every pin one width | 511 | **0** | 1.0000 | 0.9956 |
| Pins of differing width | 581 | **38** | 1.1747 | 0.9990 |

**Every one of the 38 models that delivers more power than it was given has pins
of differing width, and not one of the 511 whose pins are all one width does.
The worst of those 511 is 1.0000.** The partition is exact over all 1092 models
and none is unclassified.

The class is measured rather than inferred. Each black box draws its pins on
layer 1/10 with the width of the waveguide each terminates, so the widths are
read off the file. Classing instead by the cell name was tried first, a taper
being two widths by definition and a crossing being two where the wavelength of
its side arm differs from that of its through arm, and the two agree on every
violation. The 33 crossings whose arms carry the same wavelength are all
passive, and they are the control.

| Family | Models | Channels | Worst | Above unity |
| --- | ---: | ---: | ---: | ---: |
| Crossing | 533 | 4 | 1.1747 | 10 |
| Taper | 33 | 2 | 1.0968 | **28** |
| Mmi1x2 | 197 | 3 | 0.9996 | 0 |
| ModeConverter | 33 | 4 | 0.9994 | 0 |
| Mmi1x4 | 33 | 5 | 0.9992 | 0 |
| Mmi1x3 | 33 | 4 | 0.9992 | 0 |
| Mmi2x2 | 33 | 4 | 0.9989 | 0 |
| OpticalHybrid4x4 | 33 | 8 | 0.9943 | 0 |
| ModeSplitter | 33 | 6 | 0.9938 | 0 |
| Mmi2x4 | 33 | 6 | 0.9865 | 0 |
| GratCoupSimple | 98 | 2 | 0.4891 | 0 |

### The taper says which direction the error is in

A taper has two channels, so its transmission can be separated by direction, and
the separation is decisive.

| | Of 33 taper models |
| --- | ---: |
| The forward direction exceeds unity | 3 |
| The reverse direction exceeds unity | **28** |
| Worst forward | 1.0028 |
| Worst reverse | **1.0966** |

**The excess sits in one direction, and it is the direction that enters the wide
port.** Which port is which was not inferred from the cell name. The black box
carries its pins on layer 1/10 and their extents are the port widths, so the
narrow and the wide end are read off the file: on the 1550 nm taper the pin at
one end measures 1.500 um and the pin at the other 13.500. Light entering the
wide port and leaving the narrow one is reported at up to 1.0966 of the power it
was given, while the same structure in the other direction stays at unity.

A structure of reciprocal materials cannot do that, and the reflections are four
orders of magnitude below the discrepancy, so nothing physical accounts for it.
What does account for it is a mode power normalised inconsistently between two
ports of different width, which is an error a two-dimensional extraction can
make and a three-dimensional one is no less able to make.

The same asymmetry is why 160 models break reciprocity: it is one defect with
two symptoms. Twenty of the 160 are also above unity and 140 stay below it,
which is what a normalisation error does when it is small enough to hide inside
the loss.

### It is per-extraction and not systematic

The magnitude tracks neither of the two things it would track if it were a
formula applied wrongly.

| Correlation with the excess | |
| --- | ---: |
| Width ratio, over 8.5 to 14.7 | +0.156 |
| Design wavelength, over 493 to 1550 nm | −0.123 |

The excesses are bimodal instead, clustering near 1.002 and near 1.06, and the
same nominal taper appears in both clusters at different bands. That is the
signature of a per-simulation setting or a per-simulation convergence rather
than of a systematic scaling. **A user cannot therefore correct these models by
a rule.** The affected ones are to be identified and replaced.

## The defect this study found in its own instrument

`tools/check_pdk_models.py` keyed a scattering entry on the pair of port
numbers. A channel is a port and a mode together, and 66 of the kit's models are
multimode, so the sixteen entries of a two-port two-mode converter collapsed
into four and the last read won.

Every mode converter and mode splitter in the kit was reported as passing under
two per cent of its power. Corrected, they pass 0.9994 and 0.9938 and are
physical. **The false alarm was in the reader.**

The lesson is the one the chain already holds about cross-checks. An instrument
that reports a violation is trusted at the moment it is least examined, and this
one would have been believed: a mode converter losing 20 dB is exactly the kind
of thing a vendor kit might get wrong. What caught it was that the number was
absurd rather than merely bad.

## What is not covered

**Almost no geometry was checked.** The kit ships black boxes: each cell imports
a GDS holding an outline, a label and its pins rather than drawn polygons. The
measurement applied to the LTOI300 cells, setting every declared dimension
against a cut through the emitted file, has almost nothing to read here.

What it does have is the pins, whose extents are the port widths, and those were
read and used above. Everything between the ports is absent, so the scattering
matrices remain the only description of what these devices do.

**No model was reproduced independently.** Establishing that a taper is 5 per
cent non-passive says the model is wrong and does not say what the taper does. A
three-dimensional solve of one affected cell would give the correct figure, and
it would need the geometry the black box does not carry.

**The two-dimensional reduction is quantified nowhere for this stack.** The
argument above is transferred from a different platform and gives a direction
rather than a number. The instrument that would settle it exists, being the beat
length computed in the reduction and in the full cross-section, and it wants a
multimode section geometry that this kit does not publish.

**The grating couplers are reported passive and that means little.** A coupler
passing 0.49 of its power into a fibre is doing its job or failing at it, and
this study cannot tell which, having no independent model of the fibre.

## The files

| File | What it is |
| --- | --- |
| [`scripts/model_audit.py`](scripts/model_audit.py) | every tabulated model against passivity and reciprocity, classed by port width |
| [`scripts/dispersion_cost.py`](scripts/dispersion_cost.py) | what freezing the material index costs the group index, by mode solve |
| [`../../design-chain/tools/check_pdk_models.py`](../../design-chain/tools/check_pdk_models.py) | the general instrument, which names the offending files |
