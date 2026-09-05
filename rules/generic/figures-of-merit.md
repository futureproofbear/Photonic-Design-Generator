# A figure of merit carries a reference, and a self-referred one cannot compare two devices

*Tier: generic. Confidence: high, the mechanism is analytic and one case
inverted a verdict.*

A figure of merit is a ratio. The numerator is usually stated and the
denominator is usually a convention. Where the denominator is a property of the
device under test, the ratio measures the denominator, two devices cannot be
ranked by it, and a sound device can be reported as failing.

## The three forms this takes

**A response normalised to its own zero-frequency value.** A transmission line
left open at its far end returns the wave, and the returned wave adds to the
forward wave at zero frequency, so the reference is twice that of the same line
terminated. The roll-off so reported is the decay of that doubling. On one 5 mm
electrode the self-referred 3 dB point read 4.4 GHz while the device was within
half a decibel of a matched line above 49 GHz.

**A quantity computed at an idealised value of a term it contains.** A half-wave
voltage-length product computed at unit electro-optic overlap differs from the
physical figure by the reciprocal of that overlap, which falls between 0.3 and
0.5 for coplanar electrodes on a high-permittivity film. A published figure that
appears optimistic by a factor of two to three is frequently the un-derated one.

**A quantity computed under a convention that halves or doubles it.** A
push-pull interferometer figure and a single-arm figure differ by a factor of
two and are routinely compared as though alike.

## The practice

**State the reference beside the figure, always.** A figure whose reference is
not stated will be read against the reader's own convention.

**Where two devices are to be compared, drive them identically and remove the
normalisation from both.** The comparison is then the worst and the best the
difference does across the declared band, each with the frequency at which it
occurs. That is the quantity a driver is sized against.

**Where an acceptance target names a figure of merit, confirm the figure is the
comparative one.** A target written against a self-referred quantity will fail a
device that works and pass one that does not, and the failure reads as physics.

**Report the idealised figure and the physical figure in one table, never in
separate places.** A reader given one will assume it is the other.

## Evidence

[`../../.claude/LESSONS.md`](../../.claude/LESSONS.md) L006 on overlap-free
figures of merit against physical ones, L032 on a self-referred figure of merit,
and T065 on a travelling-wave model with no far end and a normalisation that
removed the loss. The implementation is
[`design-chain/src/picchain/rf.py`](../../design-chain/src/picchain/rf.py),
whose `response_loaded` states its two references and whose `far_end_penalty`
computes the comparative one.
