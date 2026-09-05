# A scan is invalid unless every dependent field moves with it

*Tier: generic. Confidence: high, three cases, one of them measured to reverse
the sign of a reported result.*

A scan varies one declared field and compares the result across the points. The
comparison is between different designs wherever a second field depends on the
first and was held fixed. A metric tree conceals this by construction, every
number in it remaining correct while their combination is meaningless.

## The three dependencies to enumerate before scanning

**A field that is a manual copy of a computed quantity.** Where one stage
computes a quantity and another consumes a declared copy of it, a scan reaching
the first must re-declare the second at every point. A scan of facet coupling
loss was evaluated against one declared output power while the computed power
fell by 34 % across the scan. The reported linewidth improved monotonically.
Reconciled point by point against its own computed power it worsens
monotonically, the threshold gain falling by 11 % while the power falls by 34 %.
The two effects oppose and the scan concealed it.

**A field the process cannot move in isolation.** A scan parameter must
correspond to something a fabrication run can actually deliver on its own. Two
features patterned on one layer by one exposure and one etch cannot vary
independently: a lithographic excursion widens both and closes the gap between
them in the same step. Declaring the gap alone as the process excursion
describes a placement error that the process does not produce, and it omits the
term that opposes it.

**A field that enters the same metric through a second path.** On a grating of
order above one, a lithographic excursion reaches the coupling constant twice
and the two terms oppose. Closing the gap raises the index contrast. Widening
the feature along the propagation direction raises the duty cycle, and the
coupling depends on the duty cycle through the Fourier amplitude of the m-th
harmonic,

> a_m ∝ Δn · sin(m π D) / m

which is maximised at D = 1/(2m) and falls on either side.

**The two excursions were measured against each other on one cross-section**,
each displaced by ±20 nm with every other parameter held at nominal:

| excursion | κ across the span | span |
|---|---|---:|
| the drawn gap alone | 1.0477 to 0.8480 /cm | **−21.2 %** |
| the process bias | 0.9092 to 0.9558 /cm | **+4.9 %** |

**The gap-only excursion overstates the sensitivity by a factor of about four
and reverses its sign.** Closing a drawn gap raises κ; a process printing wide
raises it far less, the duty term taking most of it back. The response to bias
is also asymmetric, κ rising 1.4 % at +20 nm and falling 3.5 % at −20 nm.

An estimate made from the two terms separately, before the sweep was run,
predicted the net at under one per cent. The measured figure is 4.9 %. **The
cancellation is real and its magnitude is not predictable from the two terms
taken at a single point**, because their curvatures differ. Run the sweep.

## The practice

**Scan the quantity the process varies, and not the geometric field it happens
to reach.** Where the chain offers a parameter representing the process
displacement itself, that parameter is the correct corner input, because it
moves every dependent dimension coherently and in the right direction. Here that
parameter is `process.bias_um`, which grows a width by the full bias and shrinks
a gap between two features on the same layer by the same amount.

**A pre-compensated bias is a no-op on the printed geometry**, by construction:
pre-compensation exists so that the printed dimension lands on the nominal one.
A corner excursion therefore represents the residual the process leaves after
compensation, and it is taken with pre-compensation off so that the displacement
reaches the physics.

**Where two stages hold one physical quantity, print the divergence on every
run.** A field reconciled by hand at revisions will be stale for most of its
life.

**Vary a second, unrelated parameter before a relationship is written down.** A
ratio held between 1.13 and 1.34 across five points of one parameter, which
looked like a law. Both quantities varied smoothly with that parameter, so the
tight ratio carried no causal content. Scanning a different parameter broke it
immediately, giving 1.32, 1.95 and 1.83 at three values. A correlation observed
along one axis is not a law.

**A result arriving in the convenient direction earns more scrutiny.** The
linewidth scan above was written into a design report before it was checked.

## Centring is a choice available at no cost

Where a metric depends on a field through a function with an interior extremum,
placing the design at that extremum removes the first-order sensitivity. A
third-order grating placed at D = 1/(2m) = 1/6 is insensitive to the duty term
at first order and gives the largest available harmonic amplitude. A design
sitting away from it pays twice, in amplitude and in sensitivity, and moving to
it costs a dimension change and no performance.

## What correcting a window can do

Replacing a gap-only excursion with the process bias on one design changed three
things at once, and the direction was different in each.

* **A `must` row that had never failed began to fail.** The guided-mode count
  reached two against a ceiling of one, in five of eighty-one corners, at
  positive bias with a deep etch. The previous window moved no dimension of the
  guide, so the row returned one everywhere and read as insensitive.
* **A `should` failure was withdrawn.** A linewidth reported as exceeding its
  bound at nine corners is met at every corner on the corrected window.
* **A quoted spread narrowed.** The coupling constant had been reported as
  spanning 63.6 % and spans 46.4 %, the difference being the duty term.

**A metric that is flat across a window may be insensitive, or may be
unreachable by that window.** The two are distinguished by naming which declared
excursion moves it, and a metric no excursion reaches is to be reported as
unreached rather than as stable.

## A sweep exercises the parameters its metrics respond to, and not the parameters it declares

A factorial sweep reports a corner count and a spread. Neither states how many of
the declared parameters reached the physics. One sweep of seven corners over
three parameters was a sweep over one.

**Two mechanisms produce a dead parameter and both are silent.** A
pre-compensated bias moves nothing by construction, so a window declared on it
represents the residual only where pre-compensation is switched off. A parameter
whose nominal value is zero has no relative excursion, so a window expressed as a
fraction of the nominal collapses to a point and the parameter is dropped.

**A guard that names the correct parameter does not establish that the parameter
is live.** The guard requiring a window to vary the process bias rather than a
drawn dimension is correct and was followed, and the resulting window varied
nothing at all.

**The tell is the sensitivity table.** The elasticity column is blank for every
metric with respect to a parameter the sweep could not move. A second signature
is arithmetic: where one parameter's half-span contribution doubles exactly to
the full window, the window has one live parameter.

**Report, for each declared corner parameter, which metrics it moved.** A
parameter that moved none is named as unexercised, and the corner count is not
quoted without it.

## Evidence

`.claude/LESSONS.md` L014 (a lithographic bias moves a high-order grating in two
opposing ways), L021 (a process window states which excursions the sweep can
represent, and the rest read as insensitive), L011 (the nominal point is not the
design, the window is), T036
(a parameter scan is invalid unless every dependent field moves with it), T043
(the correction that was itself a spurious correlation), and
`design-chain/src/picchain/process.py`, which states the width and gap
convention and implements it.
