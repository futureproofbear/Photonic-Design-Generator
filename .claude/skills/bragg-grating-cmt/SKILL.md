---
name: bragg-grating-cmt
description: Design, compute and sanity-check Bragg gratings by coupled-mode theory and the 2x2 transfer matrix, covering the coupling constant from geometry and from the transverse overlap integral, reflectivity, the stopband in both the weak and strong regimes, sidelobes, apodisation, phase-shifted and chirped structures, penetration depth and high-order gratings. Use whenever a grating period, coupling strength, reflectivity or bandwidth is being chosen, whenever a non-uniform, apodised or phase-shifted grating must be evaluated section by section, or whenever a published grating specification is to be checked for internal consistency.
---

# Bragg Gratings: Coupled-Mode Theory and Transfer Matrices

## The Coupled-Mode Equations

The transverse field inside the grating is carried by two counter-propagating
envelopes,

$$E(z) = R(z)\,e^{-i\beta_0 z} + S(z)\,e^{+i\beta_0 z}, \qquad \beta_0 = \frac{\pi}{\Lambda}$$

whose evolution is governed by

$$\frac{dR}{dz} = i\sigma R + i\kappa S, \qquad \frac{dS}{dz} = -i\sigma S - i\kappa^{*} R$$

Two parameters appear and they are to be kept distinct. $\kappa$ is the coupling
per unit length, which transfers power between the two directions. $\sigma$ is
the detuning from the Bragg condition,

$$\sigma = 2\pi n_{\text{eff}}\left(\frac{1}{\lambda} - \frac{1}{\lambda_B}\right) + \sigma_{\text{self}}$$

in which $\sigma_{\text{self}}$ carries the mean index shift the perturbation
itself introduces. Omitting that term displaces the whole spectrum, so it is not
a refinement.

## The Transfer Matrix

Over a uniform segment of length $\Delta z$ the system solves in closed form, and
the solution is a $2\times2$ matrix relating the amplitudes at the two ends:

$$\begin{pmatrix} R(z) \\ S(z) \end{pmatrix} = \mathbf{T}\begin{pmatrix} R(z+\Delta z) \\ S(z+\Delta z) \end{pmatrix}$$

$$T_{11} = \cosh(\gamma \Delta z) - i\frac{\sigma}{\gamma}\sinh(\gamma \Delta z), \qquad T_{12} = -i\frac{\kappa}{\gamma}\sinh(\gamma \Delta z)$$

$$T_{21} = +i\frac{\kappa^{*}}{\gamma}\sinh(\gamma \Delta z), \qquad T_{22} = \cosh(\gamma \Delta z) + i\frac{\sigma}{\gamma}\sinh(\gamma \Delta z)$$

$$\gamma = \sqrt{|\kappa|^2 - \sigma^2}$$

**Two properties are to be asserted in any implementation**, since both fail
loudly when the algebra is wrong and silently when it is merely inconsistent:

$$\det(\mathbf{T}) = T_{11}T_{22} - T_{12}T_{21} = 1, \qquad T_{22} = T_{11}^{*},\; T_{21} = T_{12}^{*}$$

the second holding for a lossless grating with real coupling.

### The two spectral regimes are the same equations

| | stopband, $|\kappa| > |\sigma|$ | passband, $|\kappa| < |\sigma|$ |
|---|---|---|
| $\gamma$ | real | imaginary, $\gamma = iq$, $q=\sqrt{\sigma^2-|\kappa|^2}$ |
| functions | $\cosh$, $\sinh$ | $\cos$, $\sin$ |
| the wave | evanescent, decaying | oscillatory, transmitted |
| what is seen | the reflection peak | the sidelobe ripple |

A single implementation covers both. Where $\gamma$ is carried as a complex
number the hyperbolic functions continue analytically into the trigonometric
ones, so branching on the regime is unnecessary and is a common source of a
discontinuity at the band edge.

### Reflectivity from the matrix

With no wave injected from the far end, $S(L) = 0$,

$$r = \frac{S(0)}{R(0)} = \frac{T_{21}}{T_{11}}, \qquad t = \frac{1}{T_{11}}$$

$$R = |r|^2 = \frac{|\kappa|^2\sinh^2(\gamma L)}{\gamma^2\cosh^2(\gamma L) + \sigma^2\sinh^2(\gamma L)}$$

At exact phase matching $\sigma = 0$ and $\gamma = |\kappa|$, which reduces to

$$R_{\max} = \tanh^2(|\kappa| L)$$

**This is why the matrix is worth carrying even where the closed form suffices.**
The closed form gives one number at one wavelength; the matrix gives the whole
spectrum, the sidelobes, and every structure below.

### Cascading, which is the entire point

A non-uniform grating is subdivided into $N$ segments each uniform enough, and
the segment matrices multiply:

$$\mathbf{T}_{\text{total}} = \mathbf{T}_1 \mathbf{T}_2 \cdots \mathbf{T}_N$$

Apodisation varies $\kappa$ between segments, a chirp varies $\Lambda$ and hence
$\sigma$, and a loss is admitted by taking $\sigma$ complex. Convergence in $N$
is to be demonstrated and not assumed: the segment must be short against both
$1/|\kappa|$ and the scale on which the profile varies.

## Phase-Shifted Gratings

A discrete phase shift $\Delta\phi$ inserted between two sections is a diagonal
matrix,

$$\mathbf{T}_{\text{shift}} = \begin{pmatrix} e^{+i\Delta\phi/2} & 0 \\ 0 & e^{-i\Delta\phi/2}\end{pmatrix}$$

and the quarter-wave shift, $\Delta\phi = \pi$, gives $\mathrm{diag}(i, -i)$.

**A quarter-wave shift opens a narrow transmission resonance at the exact centre
of the stopband.** The two halves form a cavity whose mirrors are each other, so
the structure ceases to be a mirror and becomes a resonator. This is the basis of
the single-mode DFB laser, and of the narrow bandpass filter.

Four consequences follow and each has caught somebody.

**The resonance narrows as the grating strengthens.** Its width falls roughly as
$e^{-2\kappa L}$, so a stronger grating gives a sharper line and a longer photon
lifetime, which is the opposite of the intuition carried over from a uniform
mirror where strength buys width.

**A shift is a quarter of a period, not half.** The optical phase acquired per
round trip through $\Lambda/4$ is $\pi$. Implementing $\Lambda/2$ gives
$\Delta\phi = 2\pi$, which is no shift at all, and the structure reverts to a
uniform mirror with a defect nobody can see in the spectrum.

**Placement decides the symmetry.** A shift at the centre gives equal mirrors and
the highest resonance transmission. Displacing it biases the output between the
two ends, which is exploited deliberately in a DFB laser to raise the front-facet
efficiency, and suffered accidentally where the lithography places it off centre.

**Spatial hole burning defeats it at high power.** The mode of a centrally
shifted structure is peaked at the centre, so the carrier density is depressed
there and the effective shift moves under drive. A corrugation-pitch-modulated
or multi-phase-shift design distributes the field instead.

## From Geometry to the Coupling Constant

### The rigorous statement

$\kappa$ is a transverse overlap between the unperturbed mode and the index
perturbation, and only then a longitudinal Fourier coefficient:

$$\kappa_m = \frac{\pi}{\lambda_B}\, a_m, \qquad a_m = \frac{2}{\pi m}\,\Delta n_{\text{eff}}\,\sin(\pi m D)$$

$$\Delta n_{\text{eff}} = \frac{\displaystyle\iint_{A_{\text{pert}}} \Delta n(x,y)\,n(x,y)\,|E(x,y)|^2\,dA}{\displaystyle\iint_{-\infty}^{\infty} n(x,y)\,|E(x,y)|^2\,dA}$$

with $D$ the duty cycle and $m$ the grating order. **The transverse integral is
the physics and the Fourier coefficient is the bookkeeping.** A perturbation
placed where the mode is weak contributes nothing however large its index step,
which is the whole behaviour of a side-coupled grating.

### The practical statement

$\Delta n_{\text{eff}}$ is to be obtained as the **difference of two mode solves
on an identical mesh**, one containing the perturbing feature and one without.
That difference evaluates the integral above numerically and without the
first-order approximation, and systematic discretisation error largely cancels,
so a difference of order $10^{-4}$ is trustworthy where the absolute
$n_{\text{eff}}$ is not.

### The Bragg condition takes the period-averaged index

$$\lambda_B = \frac{2\,\bar{n}\,\Lambda}{m}, \qquad \bar{n} = n_{\text{base}} + D\,\Delta n$$

High-order gratings, $m = 3$ and above, are chosen where a first-order period
would demand sub-100 nm features. The cost is a smaller $a_m$ together with
additional radiation channels; the benefit is manufacturability by conventional
lithography.

**The rectangular profile is an assumption and it is quadratic in the order.** A
real profile is rounded by the process, and smoothing of RMS length $s$ suppresses
the $m$-th harmonic by $\exp[-(2\pi m s/\Lambda)^2/2]$. An assumption benign at
first order is not benign at third, and the discrepancy presents as a coupling
constant lower than the closed form predicts.

## Invariants to Be Checked on Every Design

**Peak reflectivity.** $R = \tanh^2(\kappa L)$. No other quantity enters.

**Bandwidth, and it has two regimes.** The stopband between the first nulls is

$$\Delta\lambda \simeq \frac{\lambda_B^2}{\pi n_g}\sqrt{\kappa^2 + \left(\frac{\pi}{L}\right)^2}$$

which covers both limits and should be preferred to either alone:

* **weak, $\kappa L \ll 1$:** the length term dominates and the width is set by
  the finite aperture. The FWHM floor is
  $\Delta f_{\min} = 0.886\,c / (2 n_g L)$, and **no uniform grating can be
  narrower at that length whatever its coupling**. A specification below it is
  unachievable, and this check has already found a mutually inconsistent
  reflectivity-and-bandwidth pair in published work.
* **strong, $\kappa L \gg 1$:** the coupling dominates and the width saturates at
  $\Delta\lambda \simeq \lambda_B^2 \kappa / (\pi n_g)$, **independent of
  length**. Lengthening such a grating raises reflectivity and penetration depth
  and does not narrow it.

The two are different measurements and are not to be compared directly: the
null-to-null stopband is roughly $2.3\times$ the FWHM in the weak limit. State
which is quoted.

**Penetration depth.** $L_{\text{pen}} = \tanh(\kappa L)/(2\kappa)$, tending to
$L/2$ for a weak grating and to $1/(2\kappa)$ for a strong one. This sets the
mirror's contribution to the round-trip delay of a laser cavity, and it is
bounded above by $L/2$ however weak the grating is made.

**Group index, not phase index.** A uniform index perturbation displaces the
Bragg wavelength by $\delta\lambda/\lambda = \delta n / n_g$ and not by
$\delta n / n_{\text{eff}}$. Use of the phase index over-predicts by the ratio
$n_g/n_{\text{eff}}$, typically 25 % for a shallow-etched thin-film ridge.

## Side-Coupled Gratings

Where the grating is formed by features placed **beside** the waveguide rather
than patterned into it, $\Delta n_{\text{eff}}$ decays exponentially with the
separation, at the transverse decay constant of the guided mode. This is the
overlap integral above with the perturbation moved into the evanescent tail.
Decay lengths of order 150 to 200 nm are typical for a shallow-etched
high-index-contrast ridge, from which:

* $\kappa$ is exponentially sensitive to a single sub-100 nm dimension;
* a 20 nm lithographic error constitutes roughly a 10 % error in $\kappa$;
* sloped sidewalls **increase** $\kappa$, a trapezoidal feature presenting a
  wider base positioned closer to the ridge. The opposing intuition is incorrect.

Design implication: centre the design where the derivative of performance with
respect to $\kappa$ is flat, and place monitor structures with stepped
separations on the first reticle so that the process is measured rather than
assumed.

## Apodisation

A uniform grating exhibits first sidelobes near $-9$ dB. Within a laser these
pull the longitudinal mode and appear as chirp nonlinearity; within a filter they
appear as crosstalk. Gaussian or raised-cosine apodisation suppresses them at a
modest cost in peak reflectivity for a given length.

Apodisation is the correct first response to poor chirp linearity, since the
grating is not shortened and the cavity delay budget is therefore undisturbed.

Apodising $\kappa$ alone shifts the local Bragg wavelength along the grating,
because the mean index varies with the perturbation amplitude. Where the sidelobe
requirement is severe the mean index is to be held constant along the structure,
by varying the duty cycle against the amplitude, and the residual chirp is to be
reported either way.

## What Must Be Reported

A grating is not specified until the following are stated together. Each row
exists because omitting it has misled somebody.

| quantity | why it must appear |
|---|---|
| $\Lambda$, $m$, $D$, and $\bar{n}$ | the Bragg condition cannot be checked without all four |
| $\Delta n_{\text{eff}}$, and how it was obtained | a differenced pair of solves and a closed form are not the same claim |
| $\kappa$, $L$ and the product $\kappa L$ | every invariant below is a function of the product |
| $R = \tanh^2(\kappa L)$ | the peak, and the only quantity the closed form gives |
| bandwidth, **with the measure named** | null-to-null and FWHM differ by about $2.3\times$ |
| which regime, $\kappa L$ against unity | lengthening a strong grating does not narrow it |
| the transform-limited floor at that length | a specification below it is unachievable, not merely difficult |
| $L_{\text{pen}}$ | the mirror's share of a laser round trip, bounded by $L/2$ |
| sidelobe level, and the apodisation if any | $-9$ dB uniform, and it appears as chirp nonlinearity |
| the profile-smoothing assumption | suppression is quadratic in $m$ and bites at third order |
| for a phase-shifted design: $\Delta\phi$, its position, and the resonance width | a shift of $\Lambda/2$ is no shift at all |
| the segment count $N$, and the convergence in it | a matrix cascade that has not converged is an arbitrary spectrum |

Where a figure cannot be produced, say so and say why. An absent row is a
question nobody asked, and it reads exactly like a favourable answer.
