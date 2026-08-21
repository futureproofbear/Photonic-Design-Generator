# A slide that overflows loses its conclusion silently

*Tier: generic. Confidence: high on the mechanism, and the height check is an
estimate until a render is read.*

A slide deck renderer given more content than the frame holds **clips the excess
and reports nothing**. The author sees the whole slide in the editor. The reader
receives a slide whose foot is absent and has no way to know it. The part most
often lost is the last paragraph, which on a technical slide is the conclusion.

This is the same class as a stale figure and a superseded number. The output
looks finished, carries no marker, and is believed.

## The budget is arithmetic and it is worth stating

A 16:9 canvas is 1280 by 720, and the theme's padding takes about 70 px top and
bottom, so roughly **580 px of usable height**. At a 22 px body face and a line
height of 1.5 that is about **17 rendered lines**, and a heading, a figure or a
table each consume a large share of it.

Three quantities dominate and each is checkable before rendering.

**A figure's height is its declared width times its aspect ratio.** The aspect
is read from the file and is not to be assumed. Two figures in one deck differed
by a factor of two in aspect, so the same declared width produced 380 px in one
case and 615 px in the other, and only the second overflowed.

**A table row costs its font size times the line height, plus its border.** A
fourteen-row table at 18 px is over 380 px before any prose.

**Prose wraps.** A source line is not a rendered line. Count characters against
the column width rather than counting lines in the editor.

## The practice

**Check every slide against the budget before the deck is shown**, and check it
again after any edit that adds content. An edit that adds two sentences to a
slide that was already near the limit is the usual way a deck starts clipping.

**Size a figure to the space its slide has left**, and not to a width that looks
right in isolation. Compute the space from the slide's other content.

**Split rather than shrink.** Reducing the type to make content fit trades a
silent loss for an unreadable slide, and a deck whose font size varies slide to
slide reads as unfinished. A slide carrying two findings is two slides.

**A two-column layout halves the height of what it holds**, and a checker that
sums the body as one column will flag slides that fit. State the layout in a
form the check can see.

## The check

`design-chain/tools/check_slide_overflow.py` estimates the rendered height of
every slide from the deck's own style block and reports those that will not fit.

    $PY tools/check_slide_overflow.py <deck.md>
    $PY tools/check_slide_overflow.py <deck.md> --verbose

**It estimates and does not measure.** No renderer is invoked, so it reports a
prediction. It is calibrated to be pessimistic, and its purpose is to make the
question askable on a machine that has no renderer installed, which is the
common case and is exactly when a deck gets edited anyway.

**Where the renderer is available, render the deck and read it.** An estimate
that says a deck fits is weaker evidence than a page you have looked at, and
this rule does not pretend otherwise.

## A drawing coloured by layer shows the process, not the design

Where two structures share a layer number because one lithographic step patterns
both, a plan view coloured by layer renders them in one colour and a reader
cannot tell them apart. On one device two electrode pairs at different gaps, and
the four bond pads driving them, all sat on one layer; the drawing showed that
metal existed and nothing else.

**Ask, for any layer carrying more than one kind of structure, whether a reader
of the drawing can tell them apart.** Where the answer is no, the drawing needs a
second basis for identification. Geometry usually supplies one: a compact shape
is a pad and a long thin one is a conductor, and the grouping follows.

**Take the geometry from the emitted layout rather than from the design file**,
so that the drawing describes the mask that will be made.

A deck inherits this blindness through its figures. Where a design gains a second
instance of something, the slides describing the first are to be checked, and a
slide written for the predecessor is to say so.

**A renderer with a hard-coded window renders the design it was written for.**
Fixed views chosen when a device had one electrode pair do not gain a second view
when it gains a second pair, and the omission is invisible because every figure
that exists still looks correct. **After adding a structure, ask which existing
figure shows it.** Where the answer is none, the figure set has stopped
describing the device.

Prefer a renderer that takes its window and its layer subset as arguments. It
should refuse a layer name the design does not declare rather than dropping it,
since a view that quietly omits what was asked for is a view of the wrong thing.

## A stated quantity is checked against the run, not read

A document accumulates numbers across revisions, and a stale one looks exactly
like a current one. Reading does not find them. Comparing does.

`design-chain/tools/check_doc_numbers.py` scans a document for lines naming a
known quantity and reports any line whose numbers match no run of record.

    $PY tools/check_doc_numbers.py <doc.md> --design <dir>=<TAG> [--design ...]

Three things had to be taught to it before it was usable, and each is a general
point about a checker.

**A bound is not a claim.** `threshold gain <= 40 /cm` states the requirement,
and judging it against the run's 29.5 reports correct text as wrong.

**A corner extreme is a real figure.** A deck quoting the worst of a sweep is
quoting a measurement, and comparing only against the nominal reported it wrongly.

**A deliberately frozen section is correct and describes another device.** The
document declares the span rather than the tool guessing:

    <!-- frozen: the platform comparison, held at the transition -->
    ...
    <!-- /frozen -->

That is the mechanism a document carrying two designs needs anyway, made
checkable.

**A checker that reports correct work as wrong is one the reader learns to
skip**, so each of the three was fixed in the tool rather than by editing the
document to suit it.

## The rendered artifact and its source are two objects

A deck's PDF is a generated view of its Markdown, and it goes stale the moment
the source is edited. **A stale render carries no marker a reader can see.**
Where the renderer is unavailable and the source has moved on, rename the render
to say so rather than leaving it in place, and record the build command beside
the source. A file named for what it is will not be handed out by accident; a
file that merely happens to be old will.

## Evidence

`.claude/LESSONS.md` T016 (a hand-drawn figure sits outside the geometry checks),
T017 (an editable figure carries two descriptions), T024 (a drawing keyed to
numbers the design may change), T032 (a generated view is read before it is
shown), T049 (the published figure is not the run's figure), T058, T059, T060.

See also [measurement-validity.md](measurement-validity.md) on quiet failures
that produce no symptom to reason from.
