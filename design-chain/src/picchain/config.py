"""Design-file schema.

A *design* is one standalone PIC (or one PIC building block) described by a
single ``design.yaml``.  The schema is deliberately flat and fully explicit:
every number that enters a simulation lives here, so a run is reproducible from
the design file plus the pinned environment, and an agent can propose a change
by editing exactly one field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class Meta(BaseModel):
    name: str
    title: str = ""
    description: str = ""
    #: free-form provenance, e.g. the paper or project deliverable this maps to
    reference: str = ""
    deliverable: str = ""
    status: Literal["scaffold", "in_progress", "baselined", "frozen"] = "scaffold"


class Platform(BaseModel):
    """Process stack."""
    cut: Literal["x", "z"] = "x"
    film_material: str = "LiNbO3"
    film_thickness_um: float = 0.400
    etch_depth_um: float = 0.200
    #: how far the unetched slab extends either side of a guide, um.
    #:
    #: Left unset the slab is a blanket, unbroken across the whole cross-section
    #: and across the whole die. That is what a design released from this chain
    #: drew: one polygon 19326 by 1669 um spanning both modulators and both
    #: facets. A slab of index above the cladding guides, so an unbroken sheet
    #: offers a facet-to-facet path that bypasses the device, couples the arms of
    #: an interferometer along their whole length, and carries a strong signal
    #: across to a weak one. It also puts high-permittivity material under every
    #: conductor, which the microwave solve then reports.
    #:
    #: Set, the slab is drawn as a strip of `width + 2 * offset` around each
    #: guide and the conductors sit on the buried oxide outside those strips.
    #: `lxt_pdk_gf` uses 6.0 um.
    slab_offset_um: float | None = None
    #: the handle wafer's resistivity, ohm.cm. Left unset the handle is modelled
    #: as a lossless dielectric and no dielectric-loss term enters the
    #: bandwidth. The outcome is a binary rather than a tolerance: at 10 ohm.cm
    #: the loss tangent at 15 GHz is of order unity and the line is unusable
    #: over centimetres, and at 1 kohm.cm it is negligible. The energy fraction
    #: the handle carries is computed and reported either way
    substrate_resistivity_ohm_cm: float | None = None
    sidewall_deg: float = 90.0
    box_material: str = "SiO2"
    box_thickness_um: float = 4.7
    clad_material: str = "SiO2"
    clad_thickness_um: float = 2.0
    substrate_material: str = "Si"
    propagation_loss_dB_per_cm: float = 0.2
    use_index_override: bool = False
    materials_file: str | None = None
    #: the foundry's identifier for this stack, as it appears in the rule deck,
    #: for example ``ltoi300`` or ``lnoi400``. Set it and the chain refuses a
    #: deck belonging to another stack.
    #:
    #: A tantalate design was drawn on the niobate stack's layer numbers and
    #: checked against the niobate deck. It returned zero violations, ten of ten
    #: release conditions and a signed manifest, because two runsets from one
    #: foundry differ in their layer datatypes and in nothing a reader notices.
    #: Nothing in the chain connected the declared platform to the deck, so
    #: nothing could contradict it. This field is that connection.
    stack: str | None = None
    #: peak-to-peak film thickness variation across the device length, in
    #: nanometres, as the foundry specifies it. The `grating` stage compares it
    #: against the uniformity a long mirror needs to stay in phase along its own
    #: length. Zero means undeclared, and the stage says so rather than assuming
    #: the film is perfect.
    film_nonuniformity_nm: float = 0.0


class Mesh(BaseModel):
    d_fine_um: float = 0.010
    d_coarse_um: float = 0.060
    fine_margin_um: float = 0.5
    subsample: int = 3
    num_modes: int = 2
    polarisation: Literal["TE", "TM"] = "TE"
    #: solve once more on a slightly thicker film, to obtain dn_eff/d(film).
    #: One extra mode solve. It is what the grating coherence check needs, and
    #: nothing else uses it, so it is off by default.
    film_sensitivity: bool = False


class Waveguide(BaseModel):
    top_width_um: float = 1.0
    wavelength_um: float = 1.55


class Grating(BaseModel):
    enabled: bool = True
    order: int = 3
    period_um: float | None = None          # if None, solved from target_wavelength_um
    target_wavelength_um: float | None = None
    length_um: float = 7250.0
    post_width_um: float = 0.30             # along x AND along z (square posts)
    post_gap_um: float = 0.63               # from waveguide top edge
    post_length_um: float | None = None     # along z; defaults to post_width_um
    #: RMS length of a Gaussian smoothing of the longitudinal index profile, in
    #: micrometres. Zero is the identity and assumes a perfectly rectangular
    #: profile, which is what the closed-form Fourier coefficient describes.
    #: A non-zero value suppresses the m-th harmonic by
    #: exp(-(2*pi*m*sigma/Lambda)^2/2), which is quadratic in the order: an
    #: assumption that is benign at first order is not benign at third. The
    #: value is a measurement, obtained by setting the coupled-mode kappa
    #: against a band-structure or time-domain solve, and it is not to be
    #: adjusted to make a target pass.
    profile_sigma_um: float = 0.0
    apodisation: Literal["uniform", "gaussian", "raised_cosine", "tanh"] = "uniform"
    apod_fraction: float = 1.0
    n_sections: int = 201
    span_GHz: float = 160.0
    points: int = 4001
    #: sweep grid for the design-space map (Fig. 1d of arXiv:2408.01743)
    sweep_post_width_um: list[float] = Field(default_factory=list)
    sweep_post_gap_um: list[float] = Field(default_factory=list)


class Electrodes(BaseModel):
    enabled: bool = True
    gap_um: float = 7.0
    width_um: float = 20.0
    thickness_um: float = 0.9
    material: str = "Au"
    eo_coefficient: str = "r33"
    test_voltage_V: float = 1.0
    #: the electro-optically active electrode run, um. Where it is unset the
    #: grating length is used, which is correct for a mirror whose electrodes
    #: flank the grating and wrong for every other electro-optic device. A
    #: modulator carries no grating, so its length is declared here and the
    #: capacitance, the lumped RC figure and the travelling-wave bandwidth all
    #: follow from the figure declared rather than from a grating that is
    #: absent. The chain reports which of the two was used.
    length_um: float | None = None
    #: the largest drive the electrode will actually see, volts. The mode-hop
    #: search is bounded by it, so a tuning range is reported over the excursion
    #: a driver can deliver rather than over whatever span the sweep happened to
    #: cover. Zero leaves the search unbounded, which is the earlier behaviour
    max_drive_voltage_V: float = 0.0
    #: lumped-electrode bandwidth estimate
    drive_impedance_ohm: float = 50.0
    #: series resistance per unit length of the metal, ohm/um (0 -> ignore)
    series_R_ohm_per_um: float = 0.0
    #: how far past the electrodes the electrostatic window extends (um).
    #: The fringing field that sets the capacitance reaches much further
    #: than the optical mode, and the outer walls are zero-flux.
    rf_window_pad_um: float = 40.0
    #: the travelling-wave model: one extra electrostatic solve with the
    #: dielectrics removed, which yields the inductance and hence the microwave
    #: index and the characteristic impedance
    travelling_wave: bool = True
    #: conductor for the skin-effect loss. 4.1e7 S/m is bulk gold; an evaporated
    #: thin film is lower, and the loss scales as its reciprocal square root
    conductivity_S_per_m: float = 4.1e7
    #: what sits at the far end of the travelling-wave line, ohm. Unset states a
    #: termination matched to the line, which returns nothing and is the model
    #: the chain carried alone until 2026-09-04. A resistor of a declared value
    #: returns (Z_L - Z0)/(Z_L + Z0) of the wave. A pad with nothing behind it
    #: is an open end, and is stated as 1e9 or above.
    #:
    #: A kit that ships terminated and unterminated variants of the same
    #: modulator described them by the same bandwidth while this was absent, so
    #: a design pointing at the unterminated cell was graded by the model of the
    #: terminated one.
    far_end_load_ohm: float | None = None
    #: the unmodulated line between the end of the modulation section and the
    #: far-end load, um. The optical carrier does not travel it and the
    #: microwave does, twice, so on a line that reflects it rotates the returned
    #: wave and moves the null. It does nothing where the far end is matched.
    #:
    #: The LTOI300 unterminated modulator draws its signal metal to 5220 um
    #: against 5045 for the terminated one, on a modulation section of 5000, so
    #: the two variants differ by 175 um of stub as well as by the resistor.
    far_end_stub_um: float = 0.0

    # --- the convergence guard on the electrostatic solve -------------------
    # The capacitance sets the microwave index, the impedance and the bandwidth,
    # and it is an integral of a field over a mesh. A design was released whose
    # bandwidth moved between 19.6 and 26.1 GHz across four refinements, and at
    # one of them two `must` rows failed at the worst corner that pass at the
    # mesh as run. A figure read off an unconverged solve carries no margin.
    #: the fine cell of the electrostatic mesh, um. Where this is unset the
    #: cell is five times the optical one and never below 50 nm. That floor was
    #: found to hold the solve short of convergence whatever the optical mesh
    #: was set to, so the quantity is declarable rather than derived
    rf_mesh_fine_um: float | None = None
    #: how far the fine cell extends either side of a material interface, um
    rf_mesh_fine_margin_um: float = 2.0
    #: re-solve the electrostatic problem on a finer mesh and report the shift
    convergence_check: bool = True
    #: the factor the fine cell size is multiplied by for the refined solve
    refinement: float = 0.5
    #: the fractional shift in capacitance below which the solve is called
    #: resolved. The microwave index goes as the square root of it, so a 2 per
    #: cent capacitance shift is one per cent of index
    convergence_tolerance: float = 0.02
    #: "slot" places two conductors either side of one guide, which is the mirror
    #: of a distributed-reflector laser. "gsg" places a signal conductor between
    #: two grounds with a guide centred in EACH gap, which is the coplanar line a
    #: push-pull interferometer carries.
    #:
    #: The two are different transmission lines. Solving a slot line for a device
    #: drawn as ground-signal-ground overstates the impedance and understates the
    #: capacitance and the conductor loss, and the drive a 50 ohm source actually
    #: launches into the line follows from the impedance.
    topology: Literal["slot", "gsg"] = "slot"
    #: ground conductor width for the gsg topology; defaults to the signal width
    ground_width_um: float | None = None


class ModulatorCfg(BaseModel):
    """A Mach-Zehnder amplitude modulator, as distinct from one of its arms.

    The electro-optic stage solves one guide between two electrodes. What a link
    budget consumes is the interferometer, which reaches its half-wave point at
    half the single-arm voltage when the arms are driven in opposition. The
    convention is declared here so that a reported V_pi states which device it
    belongs to.
    """
    enabled: bool = False
    configuration: Literal["mach_zehnder"] = "mach_zehnder"
    #: push_pull drives the two arms in opposition and halves V_pi; single_arm
    #: leaves the second arm as a passive reference and does not
    drive: Literal["push_pull", "single_arm"] = "push_pull"
    #: the band the device must pass, GHz. A modulator carrying a signal about a
    #: carrier is required to work across a band, and a 3 dB bandwidth quoted at
    #: the carrier describes a device 3 dB down where it is used. Declaring the
    #: band causes the response to be reported at its edges
    rf_band_GHz: list[float] = Field(default_factory=list)


class GainMedium(BaseModel):
    """Carrier dynamics of the gain chip.

    Every quantity here is a property of the semiconductor and of the active
    waveguide, and none is obtainable from the photonic design. A gain chip is
    bought against a datasheet, so these are to be replaced by the figures of
    the part actually selected. The defaults are ordinary for a 1550 nm InP
    multiple-quantum-well ridge and are stated as assumptions.

    Nothing outside the `dynamics` stage reads them.
    """
    #: differential gain dg/dN at threshold
    differential_gain_cm2: float = 2.5e-16
    #: carrier density at which the medium becomes transparent
    transparency_density_per_cm3: float = 1.0e18
    #: total carrier recombination lifetime at threshold
    carrier_lifetime_ns: float = 1.0
    #: nonlinear gain compression coefficient
    gain_compression_cm3: float = 1.5e-17
    #: fraction of spontaneous emission entering the lasing mode
    spontaneous_coupling_beta: float = 1.0e-4
    #: fraction of the injected current reaching the active region
    injection_efficiency: float = 0.80
    #: active stripe, from which the volume is formed with the chip length
    active_width_um: float = 2.0
    active_thickness_um: float = 0.10


class RSOA(BaseModel):
    """Gain chip for the hybrid external-cavity laser."""
    length_um: float = 1000.0
    group_index: float = 3.6
    back_facet_R: float = 0.90
    front_facet_R: float = 1.0e-4          # AR + angled facet
    internal_loss_per_cm: float = 10.0
    coupling_loss_dB_per_facet: float = 1.5
    confinement_factor: float = 0.06
    linewidth_enhancement_alpha: float = 3.0
    spontaneous_emission_factor_nsp: float = 2.0
    #: Output power. This is an INPUT to the linewidth and is not predicted by
    #: the chain unless the `dynamics` stage is enabled, which computes it from
    #: the drive current and the rate equations instead.
    output_power_mW: float = 15.0
    gain: GainMedium = Field(default_factory=GainMedium)


class PhaseSection(BaseModel):
    """An intracavity phase electrode over a passive stretch of the cavity.

    The mirror and the mode comb are set by different things. Tuning the mirror
    slides its stop band; the comb is fixed by the round-trip optical path and
    does not follow. The mode therefore slips across the comb at ``(1-r)*S`` per
    volt and eventually hands over to a neighbour, which is the mode hop.

    A phase section changes the round-trip path without touching the mirror, so
    the comb can be driven in step with the stop band and the hand-over never
    happens. It converts a placed, commissioned tuning range into a continuous
    one.

    It is not free: a second electrode, a second drive channel, a driver that
    coordinates the two, and cavity length that the die must accommodate. The
    length it needs follows from the slip it must cancel:

        slip  = (1-r) * S * V_max                        Hz
        phi   = 2*pi * slip / FSR                        rad of round-trip phase
        L_ph  = phi * lambda / (4*pi * dn_per_V * V_ph)

    The electrodes may sit far closer than the mirror's, because a phase section
    carries no Bragg posts: the only constraint is the metal-to-ridge rule and
    the optical overlap with the metal.
    """
    enabled: bool = False
    #: length of the phase electrode along the guide
    length_um: float = 1500.0
    #: electrode gap. Unconstrained by the grating posts, so it may be much
    #: tighter than the mirror's, bounded by the foundry metal-to-ridge rule
    gap_um: float = 4.0
    width_um: float = 20.0
    #: the drive available to the phase electrode
    max_drive_voltage_V: float = 25.0
    #: separation between the phase electrode and the mirror electrode, along
    #: the guide, so the two do not merge on the mask
    separation_um: float = 50.0



class PhaseTrimmer(BaseModel):
    """A thermal actuator that sets the cavity phase once, at commissioning.

    It exists to answer one question: whether the mode comb can be placed. The
    excursion a laser guarantees before commissioning is smaller than the one it
    delivers after, by `ceil(hops) + 1`, and the difference is entirely the
    cavity phase, which no process controls. A design with no way to set that
    phase is graded on the guaranteed figure, and the framework's rules say so.

    Declaring one is not enough, and this block is checked rather than believed:
    the cavity stage computes the round-trip phase the trimmer can actually
    deliver and reports whether it reaches a full free spectral range. A trimmer
    that cannot move the comb through one whole mode spacing cannot place it.

    It is thermal rather than electro-optic on purpose. The degraded mode this
    supports is the one with the Pockels phase section unpowered, so an actuator
    sharing that section's failure would be no answer at all.
    """
    enabled: bool = False
    #: the guide length the heater runs over, um
    length_um: float = 0.0
    #: thermo-optic coefficient of the guiding film, per kelvin. It belongs to
    #: the material and is declared here until the material file carries it
    dn_dT_per_K: float = 3.0e-5
    #: the cladding's own thermo-optic coefficient. A heater warms the cladding
    #: as well as the film, and the mode's effective index moves by the
    #: sensitivity-weighted sum of the two. Left at zero the reach is understated
    #: by the cladding's share, which is the conservative direction.
    dn_dT_cladding_per_K: float = 0.0
    #: dn_eff/dn for the guiding film and for the cladding, MEASURED by
    #: perturbing each index and re-solving the mode.
    #:
    #: These are the correct weights. The film confinement was used as a proxy
    #: for the first and understated it by 28 per cent on one design, the
    #: confinement being the fraction of POWER in the film while this is the
    #: fraction of the effective index that follows the film's own. Left unset,
    #: the confinement is used and a warning says so.
    #:
    #: They are pure properties of the cross-section, so they are measured once
    #: and declared rather than re-solved on every run: two extra mode solves
    #: per run is the cost, and the mode solve is the expensive stage.
    index_sensitivity_film: float | None = None
    index_sensitivity_cladding: float | None = None
    #: where the two above came from, carried into the payload so a reader can
    #: find the runs that measured them
    index_sensitivity_provenance: str = ""
    #: the temperature rise the heater is driven to, K
    max_delta_T_K: float = 40.0
    #: drawn width of the resistive wire, um
    width_um: float = 1.5
    #: which intracavity section the wire runs over. Both lie inside the
    #: cavity and either sets the round-trip phase; they differ in how much
    #: length is available and therefore in the temperature rise required.
    #: The feed carries no electrode to clear; the phase section is longer.
    over: Literal["feed", "phase_section"] = "feed"
    #: the landing at each end of the wire, um square
    pad_um: float = 60.0


class Cavity(BaseModel):
    enabled: bool = True
    #: passive PIC length between the chip facet and the start of the grating
    feed_length_um: float = 1000.0
    rsoa: RSOA = Field(default_factory=RSOA)
    #: an intracavity phase electrode, driven synchronously with the mirror
    phase_section: PhaseSection = Field(default_factory=PhaseSection)
    #: a thermal actuator that sets the cavity phase once, at commissioning
    phase_trimmer: PhaseTrimmer = Field(default_factory=PhaseTrimmer)


class DynamicsCfg(BaseModel):
    """Single-mode rate equations for the composite cavity.

    Disabled by default. The stage introduces no solver and costs milliseconds;
    it is off because it requires the gain-chip parameters under
    `cavity.rsoa.gain`, and a figure produced from an unstated assumption is
    worse than no figure. Enabling it without reviewing those parameters
    produces a plausible light-current curve for a chip nobody has selected.
    """
    enabled: bool = False
    #: drive currents at which the light-current curve is evaluated, in mA
    current_sweep_mA: list[float] = Field(
        default_factory=lambda: [0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 150.0, 200.0])
    #: the current at which the small-signal and noise figures are reported
    operating_current_mA: float = 150.0
    #: frequency grid for the intensity-noise spectrum
    rin_span_GHz: float = 20.0
    rin_points: int = 2001
    #: offset at which a single RIN figure is quoted, for comparison with a
    #: datasheet, which ordinarily states one
    rin_quote_offset_GHz: float = 1.0


class ChirpDrive(BaseModel):
    """FMCW drive conditions - links the device to the radar waveform."""
    enabled: bool = False
    bandwidth_GHz: float = 3.0
    chirp_duration_us: float = 50.0
    waveform: Literal["triangle", "sawtooth"] = "triangle"
    drive_amplitude_Vpp: float | None = None


class TaperCfg(BaseModel):
    """Eigenmode-expansion evaluation of the input taper.

    Disabled by default, since it costs one mode solve per slice and is not
    required by every design. Where ``length_um`` or ``tip_width_um`` is left
    unset, the value drawn on the mask (``layout``) is used, so that the figure
    computed here describes the structure actually emitted.
    """
    enabled: bool = False
    length_um: float | None = None
    tip_width_um: float | None = None
    profile: Literal["linear", "raised_sine", "quadratic"] = "linear"
    #: staircase sections. Loss falls as this rises until the staircase converges
    n_slices: int = 16
    #: modes carried at every slice. Power unaccounted for by this basis is
    #: reported as a power-balance deficit rather than silently discarded
    num_modes: int = 4
    #: repeat at half the slice count and report the difference
    convergence_check: bool = True
    #: a warning is raised where the local adiabaticity margin falls below this.
    #: The criterion compares the rate at which the guide changes against the
    #: beat length with the state into which power would be lost. It is a screen
    #: and not a loss estimate: it takes no account of the overlap with that
    #: state, and a symmetric taper couples only weakly to the symmetric
    #: radiation continuum. On the validation baseline a margin of 2.7 was found
    #: to correspond to lateral radiation below 0.01 dB when solved in the time
    #: domain, so a margin below this floor calls for the `fdtd` stage rather
    #: than for a redesign
    adiabaticity_floor: float = 3.0


class BendCfg(BaseModel):
    """Bend modes at a set of radii, by conformal transformation.

    Disabled by default. Each radius costs one mode solve. The radii are those a
    routing decision would choose between, and the stage reports where the bend
    stops being a straight guide with a label on it.
    """
    enabled: bool = False
    radii_um: list[float] = Field(default_factory=lambda: [500.0, 200.0, 100.0, 50.0])


class FacetCfg(BaseModel):
    """Coupling across the facet to a gain chip or a fibre.

    The partner mode is described rather than solved: its mode-field diameters
    are a datasheet quantity. Disabled by default because those diameters are a
    declared assumption and a figure produced from an unstated one is worse than
    no figure.
    """
    enabled: bool = False
    partner_mfd_x_um: float = 3.0        # 1/e^2 diameter, lateral
    partner_mfd_y_um: float = 3.0        # 1/e^2 diameter, vertical
    partner_index: float = 3.2           # the medium the mode arrives from
    ar_reflectivity: float | None = 1.0e-4
    partner_tilted: bool = True          # the usual arrangement for an angled facet
    #: physical separation between the two facets, um. A butt-coupled pair is
    #: not in contact, and the beam crosses the gap at the angle the gap medium
    #: imposes rather than at the angle it will have inside the partner. The
    #: lateral walk-off that produces is a design offset, not a loss
    gap_um: float = 0.0
    #: index of whatever fills the gap: 1.0 for air, about 1.5 for an
    #: index-matching epoxy
    gap_index: float = 1.0
    offset_x_um: float = 0.0
    offset_y_um: float = 0.0
    tolerance_dB: float = 1.0
    #: width of the guide at the facet; the taper tip is used when unset
    facet_width_um: float | None = None


class FDTDCfg(BaseModel):
    """Time-domain solve of the taper, executed by meep in its own environment.

    Disabled by default. A two-dimensional solve is minutes; a three-dimensional
    solve is an offline job. The solver is reached through WSL on Windows, and
    directly elsewhere.
    """
    enabled: bool = False
    #: which structure is solved. "taper" measures the radiation of the input
    #: taper; "grating" measures the reflection of a finite grating, which is an
    #: independent check on the coupled-mode kappa
    structure: Literal["taper", "grating", "bandstructure", "coupler", "mmi"] = "taper"
    grating_periods: int = 100           # a finite section, not the full mirror
    #: Point-coupler geometry, being a bus running past a ring of the given
    #: radius. The chain carries no resonator block, so the geometry is declared
    #: beside the solve that consumes it. The guide width is the ridge width the
    #: design already states, and the two indices come from the same
    #: effective-index reduction the taper uses.
    #:
    #: The two-dimensional reduction is valid only where the partially etched
    #: slab is continuous across the gap, which is what sets the decay of the
    #: evanescent field. Where a platform draws no slab between the two guides,
    #: `dimensions: 3` is required.
    coupler_gap_um: float = 1.0
    coupler_ring_radius_um: float = 200.0
    #: width of the ring guide where it differs from the bus. Unset, the
    #: two are equal and the coupler is synchronous. A kit pairing a
    #: single-mode bus with a wider multimode ring detunes the two
    #: propagation constants, and the coupling is then governed by that
    #: mismatch as much as by the gap
    coupler_ring_width_um: float | None = None
    #: modes of the ring guide the crossed power is resolved onto. One is
    #: sufficient for a single-mode ring. A wider ring carries more than
    #: one mode to receive the power, and coupling into a higher order is
    #: loss to the resonance the fundamental forms
    coupler_cross_bands: int = 1
    #: half the window along the bus. The coupling integrand falls as the ring
    #: curves away, so a window of 20 um at a 200 um radius omits about 2 % of
    #: the interaction and a shorter one omits materially more
    coupler_half_length_um: float = 20.0
    coupler_stations: int = 201           # polygon vertices along the ring edge
    coupler_port_width_um: float = 3.0    # mode monitor width at each port
    coupler_margin_um: float = 1.5        # lateral clearance outside the guides
    #: fractional half-width of the band over which the coupling is reported.
    #: The coupling of a point coupler varies strongly with wavelength, so a
    #: single frequency states less than it appears to
    coupler_bandwidth_frac: float = 0.04
    coupler_frequencies: int = 11
    #: MMI geometry beyond what `mzm` already declares, being the length of the
    #: access taper that carries each port from the guide width to the port
    #: width. The multimode section, the port width and the port separation are
    #: read from `mzm`, so the structure solved is the structure the layout
    #: draws rather than a second declaration of it.
    mmi_taper_length_um: float = 25.0
    #: straight guide either side of the tapers, inside the PML
    mmi_lead_um: float = 3.0
    #: inputs to the multimode section. One is a splitter and two is a coupler
    mmi_ports_in: Literal[1, 2] = 1
    #: band-structure check: bands solved at the zone edge, and the fraction of
    #: a band's energy that must sit in the core for it to count as guided
    num_bands: int = 16
    confinement_threshold: float = 0.25
    #: Convergence guard on the band-structure comparison. The gap is the
    #: difference of two nearly degenerate bands, so the discretisation error can
    #: exceed the quantity being measured and the comparison then distinguishes
    #: nothing. The structure is solved a second time on a coarser mesh and the
    #: shift between the two bounds that error. `None` takes half the primary
    #: resolution, which costs about an eighth of the primary solve. Zero
    #: disables the guard, and the comparison is then reported as unguarded.
    convergence_resolution: int | None = None
    n_frequencies: int = 201
    fractional_bandwidth: float = 0.03
    dimensions: Literal[2, 3] = 2
    resolution: int = 20                 # pixels per micrometre
    pml_um: float = 2.0
    cell_width_um: float = 24.0          # lateral extent, PML included
    cell_height_um: float = 6.0          # vertical extent, three dimensions only
    in_length_um: float = 6.0
    out_length_um: float = 6.0
    taper_stations: int = 61             # polygon vertices along the taper edge
    processes: int = 8
    wsl_distro: str = "Ubuntu"
    environment: str = "mp"
    #: wall-clock ceiling for one external solve. Raised from 7200 s on
    #: 2026-08-09: a band structure measured 6760 s on the validation baseline,
    #: which left 6.5 % of margin, and a busier machine would have tripped the
    #: ceiling partway through a solve that was proceeding correctly. A timeout
    #: is a guard against a hang and is not a schedule, so it is set well clear
    #: of the longest solve observed rather than just above it.
    timeout_s: int = 21600


class FemCfg(BaseModel):
    """Independent finite-element cross-check of the mode solver.

    The chain's own solver is finite-difference, structured and semi-vectorial.
    This stage re-solves the identical cross-section by finite elements on a
    conforming unstructured mesh, full-vectorially, and reports the
    disagreement. Disabled by default: the extras are optional and one solve
    costs several seconds.

    The quantity that carries the most weight is not the effective index but
    the index *difference* the Bragg posts produce. That difference sets the
    coupling constant, and hence the reflectivity, the mirror bandwidth and the
    tuning range.
    """
    enabled: bool = False
    #: coarse mesh size away from the guiding features, um
    resolution_max_um: float = 0.35
    #: mesh size across the ridge and the posts, um
    resolution_fine_um: float = 0.020
    #: distance over which the fine mesh is graded back to the coarse one, um
    fine_distance_um: float = 0.6
    #: 2 gives second-order elements. Order 1 is faster and markedly less
    #: accurate; it is retained for the mesh-convergence comparison
    element_order: Literal[1, 2] = 2
    num_modes: int = 4
    #: also solve the cross-section carrying the Bragg posts, giving dn_eff
    with_posts: bool = True
    #: repeat the bare solve on a coarser mesh. Without it a disagreement
    #: between the two solvers cannot be distinguished from an unconverged mesh
    convergence_check: bool = True
    coarsening: float = 2.0
    #: second solve at the other principal index of the film, which brackets
    #: the anisotropic answer the scalar-permittivity solver cannot pose
    anisotropy_bracket: bool = True
    #: fractional disagreement in n_eff above which a warning is raised
    n_eff_tolerance: float = 1.0e-3
    #: fractional disagreement in dn_eff above which a warning is raised
    dn_eff_tolerance: float = 0.10
    #: polarisation purity below which the semi-vectorial approximation of the
    #: chain's own solver is no longer supported by the full-vectorial result
    polarisation_purity_floor: float = 0.90


class ProcessCfg(BaseModel):
    """The displacement between the dimension drawn and the dimension printed.

    Defaults are zero, under which the drawn, printed and nominal geometries
    coincide and every result is that of a chain without this block. A
    characterised process is entered here, and two things follow: the mask is
    drawn pre-compensated so that the printed feature lands on the nominal
    dimension, and the physics is solved on the printed geometry rather than on
    the drawn one.

    ``bias_um`` is the change in a feature **width**, positive where the printed
    feature is wider. A gap between two features on the same layer therefore
    closes by the same amount. See ``picchain.process``.
    """
    #: per-layer lateral bias, um of width
    bias_um: dict[str, float] = Field(default_factory=dict)
    #: vertical bias on the etch depth, um. It cannot be pre-compensated by
    #: drawing, so it is applied to the printed geometry alone
    depth_bias_um: float = 0.0
    #: draw the mask inward by half the bias, so that the printed feature lands
    #: on the nominal dimension
    precompensate: bool = True
    #: which frame the cross-section solvers are posed on. "printed" is correct
    #: and is the default; "drawn" is retained for comparison
    simulate: Literal["printed", "drawn", "nominal"] = "printed"
    #: which layer name carries the guiding features and which the electrodes
    wg_layer: str = "WG"
    metal_layer: str = "METAL"
    #: the manufacturing grid, in nanometres. Every vertex on the emitted mask
    #: is snapped to it. A foundry states a grid and either refuses off-grid
    #: data or snaps it silently, and a silent snap is the worse outcome: on a
    #: periodic structure it dithers the period, which chirps the grating.
    #: 1 nm is the database unit and is therefore the identity.
    grid_nm: float = 1.0
    #: refuse rather than snap where the displacement exceeds this, in nm.
    #: Zero disables the guard
    max_snap_displacement_nm: float = 0.0


class SealRingCfg(BaseModel):
    """A closed ring of metal and etched material around the die.

    It arrests the cracks a dice saw starts and blocks the ingress of moisture
    along the film interfaces. A die without one is not submittable to most
    processes.
    """
    enabled: bool = True
    width_um: float = 20.0
    #: clearance between the device floorplan and the inner edge of the ring
    clearance_um: float = 60.0
    layers: list[str] = Field(default_factory=lambda: ["SEAL", "METAL"])


class AlignmentMarkCfg(BaseModel):
    """Marks by which each lithographic level is registered to the first.

    One mark per level is required, and they are drawn at more than one corner
    so that rotation is measurable as well as translation.
    """
    enabled: bool = True
    #: outer extent of one mark
    size_um: float = 40.0
    arm_width_um: float = 4.0
    #: a mark is drawn on each of these layers, offset so that overlay between
    #: the pair is readable under a microscope
    layers: list[str] = Field(default_factory=lambda: ["WG", "METAL"])
    #: separation between one level of the mark and the next. It must clear
    #: any layer-to-layer separation rule, or the frame fails its own deck
    clearance_um: float = 3.0
    #: a single layer carrying every level merged, so that the whole mark reads
    #: as one drawing. It is a convenience for inspection and it is NOT a
    #: manufacturing layer. Set it to null wherever the layer it names is one the
    #: process reads, or the composite becomes a duplicate of geometry already
    #: drawn on the lithographic levels, on a layer that may carry rules of its
    #: own. The LN-CORE lnoi400 runset is the case in point: its RIB_MARKERS must
    #: stand 15 um clear of the ridge, and a composite drawn there reproduces the
    #: ridge-level mark 3 um away from itself
    composite_layer: str | None = "MARK"
    #: which corners carry a mark
    corners: list[str] = Field(default_factory=lambda: ["SW", "SE", "NW", "NE"])


class MonitorsCfg(BaseModel):
    """Process control structures, drawn beside the device.

    A reticle carrying only the device measures nothing. Where a metric is more
    sensitive to a lithographic dimension than to any design choice, the first
    fabrication run is to be instrumented so that the process is measured and
    not inferred. Each structure below answers one question, and each is
    disabled individually.
    """
    enabled: bool = True
    #: how far the unetched slab reaches either side of a monitor's ridge, um.
    #:
    #: A monitor measures the process the device runs in, and a ridge with no
    #: slab under it is a different waveguide. A die released from this chain
    #: drew its slab across the device band only and left 18.3 per cent of the
    #: ridge area outside it: the loss cutback, the critical-dimension vernier
    #: and the electrode ladder all sat on bare oxide, so none of the four
    #: quantities they measure described the device beside them.
    #:
    #: Where `platform.slab_offset_um` is declared the device's own convention is
    #: used instead of this, so a design drawing local slab draws it the same way
    #: everywhere.
    slab_offset_um: float = 6.0
    #: gratings of stepped post gap, by which kappa against gap is measured
    #: directly on the delivered process rather than taken from a model
    kappa_ladder: bool = True
    kappa_gaps_um: list[float] = Field(default_factory=lambda: [0.53, 0.58, 0.63, 0.68, 0.73])
    kappa_periods: int = 300
    #: gratings of stepped LENGTH at one gap, by which phase coherence along a
    #: long mirror is measured. A post-gap ladder cannot reach this: every copy
    #: sits on the same film and sees the same thickness gradient. Coupled-mode
    #: theory says reflectivity follows tanh^2(kappa L); a mirror losing phase
    #: departs from that curve and broadens instead of narrowing.
    coherence_ladder: bool = False
    coherence_lengths_um: list[float] = Field(
        default_factory=lambda: [500.0, 2000.0, 5000.0, 10000.0])
    #: straight guides of several lengths, by which propagation loss is
    #: obtained by cut-back without reference to the coupling loss
    loss_cutback: bool = True
    loss_lengths_um: list[float] = Field(default_factory=lambda: [500.0, 1500.0, 3000.0])
    #: line and space arrays at stepped widths, by which the printed critical
    #: dimension is measured against the drawn one. This is the structure that
    #: turns the bias in `process.bias_um` from an assumption into a measurement
    cd_vernier: bool = True
    cd_widths_um: list[float] = Field(default_factory=lambda: [0.20, 0.25, 0.30, 0.40, 0.60])
    cd_repeats: int = 10
    #: electrode pairs at stepped gaps over a straight guide, by which the
    #: electro-optic overlap is measured against gap
    electrode_ladder: bool = True
    electrode_gaps_um: list[float] = Field(default_factory=lambda: [4.0, 7.0, 12.0])
    #: vertical pitch between structures within the monitor field
    row_pitch_um: float = 120.0


class SplitCfg(BaseModel):
    """Copies of the device across the die, differing in one parameter.

    A first fabrication run on an uncharacterised process is not an attempt to
    build the design; it is an attempt to find out where the design is. Where a
    metric is more sensitive to a lithographic dimension than to any design
    choice, one copy of the device gambles the whole run on the model being
    right about that dimension. A ladder of copies, stepped across the range the
    model and the process together leave open, returns a working device from the
    same run and locates the process at the same time.

    The monitors drawn beside the device measure the process. The split is what
    survives it.
    """
    enabled: bool = False
    #: dotted path into this design file, e.g. `grating.post_gap_um`
    parameter: str = "grating.post_gap_um"
    values: list[float] = Field(default_factory=list)
    #: vertical spacing between copies. Zero derives it from the device extent
    pitch_um: float = 0.0
    #: render the value of the split parameter beside each copy
    label_each: bool = True
    label_height_um: float = 25.0


class CompanionCfg(BaseModel):
    """A second device on the same die, differing in more than one parameter.

    A split ladder brackets one parameter of one design, and every rung is the
    same device. A companion is a DIFFERENT device that has to share the die.

    The case that motivated it: a coherent radar generates its microwave carrier
    as the beat between a chirped laser and a single-tone reference, so the
    carrier is the DIFFERENCE of two optical frequencies. Each laser's frequency
    moves about 3.9 GHz per kelvin. Placed on separate die the two drift
    independently and the beat drifts with them; placed on one die at one
    temperature they drift together, and the beat moves only by the mismatch
    between two nominally identical cavities.

    The device is re-drawn from the same builder with the overrides applied, so a
    companion is the design file's own physics evaluated at different values, and
    never a second drawing maintained by hand.
    """
    #: what the companion is, used to label it on the die and in the report
    name: str = ""
    #: dotted paths into this design file, each with the value the companion takes
    overrides: dict[str, Any] = Field(default_factory=dict)
    #: how many copies of the companion to place
    copies: int = 1
    #: what the companion is for, carried into the reticle payload
    purpose: str = ""
    #: the beat this companion is to produce against the primary device, in GHz,
    #: where the two are lasers heterodyned on one photodiode. Left unset, the
    #: beat is reported and not graded.
    beat_target_GHz: float | None = None
    #: the bound the companion's own side-mode suppression must clear at the
    #: setting chosen for the beat. The primary's rows are read from its window.
    beat_smsr_floor_dB: float = 40.0


class CompanionsCfg(BaseModel):
    """Companion devices placed on the die beside the primary one."""
    enabled: bool = False
    devices: list[CompanionCfg] = Field(default_factory=list)
    #: vertical spacing. Zero derives it from the device extent
    pitch_um: float = 0.0
    label_each: bool = True
    label_height_um: float = 25.0


class ChipFrameCfg(BaseModel):
    """The final chip boundary and the usable area inside it.

    A rule deck asks two questions of a die that a device cell cannot answer:
    whether the footprint is one the process offers, and whether anything has
    been placed where the process forbids it. Both are asked of two rectangles,
    an outer boundary and a usable area inset from it, and neither exists unless
    it is drawn. Until 2026-08-08 the chain drew a seal ring and a dicing lane
    and no such pair, so those rules were silent on every die it emitted. A
    silent rule is not a satisfied rule.

    The boundary is required to sit on the origin, so enabling this centres the
    die. The content is translated; nothing is resized.
    """
    enabled: bool = False
    #: the ring inside the boundary in which only the edge couplers routing to
    #: the facet may be placed. The LN-CORE lnoi400 process states 50 um.
    exclusion_zone_um: float = 50.0
    #: the footprints the process offers, as outer dimensions. Each edge of the
    #: die must match one of them. Left empty, no footprint check is made and
    #: the omission is reported.
    allowed_edges_um: list[float] = Field(default_factory=list)
    #: how near an edge must be to an allowed value to count as that value
    edge_tolerance_um: float = 0.005


class ReticleCfg(BaseModel):
    """Die assembly: the device, the frame and the monitors in one layout.

    The `layout` stage emits the device alone, which is the correct unit for
    simulation and for a rule check. It is not a submittable mask. This stage
    places that device on a die, draws the items a fabrication run requires,
    and adds the structures by which the returned wafer can be diagnosed.

    Disabled by default, a die floor plan being a decision rather than a
    default.
    """
    enabled: bool = False
    #: die extent. Left unset, it is sized from the device and the monitors
    die_width_um: float | None = None
    die_height_um: float | None = None
    #: clearance between the device and the seal ring, and the saw lane outside it
    margin_um: float = 40.0
    dicing_lane_um: float = 80.0
    seal_ring: SealRingCfg = Field(default_factory=SealRingCfg)
    chip_frame: ChipFrameCfg = Field(default_factory=ChipFrameCfg)
    marks: AlignmentMarkCfg = Field(default_factory=AlignmentMarkCfg)
    split: SplitCfg = Field(default_factory=SplitCfg)
    companions: CompanionsCfg = Field(default_factory=CompanionsCfg)
    monitors: MonitorsCfg = Field(default_factory=MonitorsCfg)
    #: Place the device so that its input facet lies on the sawn edge, and open
    #: the seal ring where the guide crosses it.
    #:
    #: FALSE, THE DEFAULT, PLACES THE DEVICE INSIDE THE FRAME. The facet then
    #: sits `margin + seal clearance + seal width + dicing lane` inside the die
    #: outline, which on the L-band design was 205 um. **A butt-coupled facet
    #: has to be the diced edge**, so a device that couples to a gain chip or to
    #: a fibre at its edge sets this true. The default is retained so that
    #: existing masks are unchanged.
    align_facet_to_edge: bool = False
    #: Vertical placement of the device within the frame. `top` reproduces the
    #: original behaviour and puts the guide close to one long edge. `centre`
    #: places it on the die axis, which keeps it away from dicing damage and in
    #: the flattest part of the thermal and stress fields.
    device_y: Literal["top", "centre"] = "top"
    #: die identification. Empty takes the design name
    label: str = ""
    revision: str = "A"
    label_height_um: float = 40.0
    label_layers: list[str] = Field(default_factory=lambda: ["LABEL", "METAL"])


class CircuitCfg(BaseModel):
    """Assembly of the passive circuit from scattering matrices, by SAX.

    Disabled by default: the extras are optional and the stage repeats, by a
    different route, a quantity the cavity stage already produces. Its value is
    that the route generalises. A netlist of three blocks and a netlist of
    thirty differ only in the dictionary.
    """
    enabled: bool = False
    #: amplitude power transmission of the chip facet, where the `facet` stage
    #: has not been run to supply it
    facet_transmission: float = 0.7
    #: the same for the input taper
    taper_transmission: float = 0.99
    #: prefer the figures the `facet` and `taper` stages computed where present
    use_facet_stage: bool = True
    use_taper_stage: bool = True
    #: fractional disagreement against the loss budget above which a warning is
    #: raised. The assembly and the budget describe the same cascade, so they
    #: should agree to numerical precision and not merely to a tolerance
    tolerance: float = 1.0e-6
    #: ripple across the stop band above which the facet etalon is reported.
    #: The cavity stage applies the mirror at a single plane and carries none
    etalon_contrast_floor: float = 0.01


class DerivedLayer(BaseModel):
    """A layer produced by a boolean operation on layers already drawn.

    Mask polarity lives here. A process asking for a dark field or a trench
    wants the inverse of what is convenient to draw, and the inverse is
    ``field NOT layer`` where the field is a drawn extent. Expressing it as an
    operation keeps one description of the device and derives the rest, rather
    than drawing the same geometry twice in two senses.
    """
    name: str
    op: Literal["not", "and", "or", "xor", "size"]
    a: str
    #: the second operand. Not read by `size`
    b: str | None = None
    #: for `size`, the amount to grow by in um; negative shrinks
    by_um: float = 0.0
    #: where this layer is placed. Omitted, it must already exist in layer_map
    layer: list[int] | None = None


class ReleaseCfg(BaseModel):
    """The submission manifest, and the conditions it is a claim about.

    Producing a manifest asserts that a set of files is ready to be sent. The
    conditions of readiness are evaluated rather than assumed, and each may be
    waived by name; a waiver is recorded in the manifest rather than removing
    the row.
    """
    enabled: bool = False
    revision: str = ""
    #: readiness conditions deliberately accepted as unmet, named exactly
    waive: list[str] = Field(default_factory=list)
    #: raise rather than warn where a condition blocks. A release step that only
    #: warns is a release step that will be ignored
    strict: bool = True


class MzmCfg(BaseModel):
    """The geometry of a Mach-Zehnder, beyond what the electrode already fixes.

    The arm separation is not declared: it follows from the line, an arm sitting
    on the centre line of each gap, so it is `electrode_width/2 + gap/2` and
    cannot drift from the electrode the electro-optic stage solved.
    """
    #: the multimode section of the 1x2 splitter, and the two access tapers that
    #: leave it. The defaults are those of `lxt_pdk_gf.ltoi300.cells.mmi1x2_cband`,
    #: which is qualified on this stack.
    #:
    #: The output gap is `port_separation_um - port_width_um`, and it is drawn
    #: open rather than closed. A junction whose two ports meet at the end face
    #: forces that gap through zero and breaks any minimum-space rule over the
    #: length of the access taper; the qualified cell leaves 0.60 um, which is
    #: twice the rule, so the gap never approaches it.
    mmi_width_um: float = 4.5
    mmi_length_um: float = 13.5
    #: centre-to-centre separation of the two access tapers at the end face
    port_separation_um: float = 2.55
    #: the width of each access taper where it meets the multimode section
    port_width_um: float = 1.95
    #: the S-bend that carries each arm from the splitter out to its gap. A
    #: raised cosine, so the curvature is zero where it meets a straight guide
    sbend_length_um: float = 220.0
    sbend_segments: int = 96
    #: how many modulators the cell carries. Mod 1 and Mod 2 are the same design
    #: and differ only in what drives them, so the pair is one cell rather than a
    #: parameter ladder: they must share a die, a process run and a thermal
    #: environment, their outputs being combined coherently
    count: int = 2
    #: centre-to-centre spacing of the modulators, um
    pitch_um: float = 1500.0
    #: a grounded strip between them. Mod 1 carries the transmit reference at
    #: full drive and Mod 2 the received echo, so a copy of the reference
    #: crossing into the echo path lands in band and coherent
    shield: bool = True
    shield_width_um: float = 60.0
    #: names drawn beside each modulator, in order
    labels: list[str] = Field(default_factory=lambda: ["MOD1-TX-REF", "MOD2-RX-ECHO"])
    #: the access taper from the multimode section out to the guide width
    port_taper_um: float = 25.0
    #: the minimum same-layer space the process declares, used only to report how
    #: far the splitting region falls below it
    min_space_um: float = 0.30
    #: straight guide between the taper and the splitter
    lead_straight_um: float = 50.0

    # --- the electrical terminals -------------------------------------------
    # A coplanar line with no terminals cannot be probed, driven or terminated,
    # and a device drawn without them is not a device. The pad structure follows
    # `lxt_pdk_gf`: the line is scaled up to the probe pitch over a taper, and
    # the two optical arms run in the two slots the whole way, so metal never
    # crosses a guide.
    #: ground-signal-ground probe pads at each end of the line
    pads: bool = True
    #: probe pitch, signal centre to ground centre, at the pad face. The whole
    #: cross-section is scaled to reach it, so the ratio of gap to conductor is
    #: held and with it the characteristic impedance
    pad_probe_pitch_um: float = 100.0
    #: the constant-width landing the probe sits on
    pad_straight_um: float = 60.0
    #: the taper from the pad cross-section down to the line
    pad_taper_um: float = 150.0
    pad_taper_segments: int = 96
    #: straps tying the shield to the ground planes on either side of it. The
    #: shield is otherwise a floating conductor as long as the electrode, which
    #: resonates at multiples of c/(2 n_m L) and cannot shield
    shield_straps: bool = True
    #: strap spacing. It is to stay well below a quarter of the microwave
    #: wavelength at the top of the band, which the layout stage checks
    shield_strap_pitch_um: float = 1000.0
    shield_strap_width_um: float = 20.0


class LayoutCfg(BaseModel):
    enabled: bool = True
    #: how many grating periods to draw. None draws the whole device, which is
    #: the default, because it costs about 1.5 s on a 5665-period grating and a
    #: mask that is not the device is a mask every geometric figure describes
    #: wrongly. A count is set only where the saving is worth having, which is
    #: the die-level work: a split ladder multiplies the polygons by the number
    #: of copies and the fill placer and the netlist extraction scale with them
    draw_periods: int | None = None
    #: which device is drawn. "edbr" is a gain chip butt-coupled to a passive
    #: circuit terminated in a distributed reflector; "mach_zehnder" is a
    #: push-pull interferometer on a coplanar ground-signal-ground line. The
    #: emission, the grid snap, the geometry check and the backend comparison are
    #: common to both, and only the polygons differ
    device: Literal["edbr", "mach_zehnder"] = "edbr"
    taper_length_um: float = 150.0
    taper_tip_width_um: float = 0.4
    #: stations at which the taper's profile is sampled when it is drawn. The
    #: curve itself is `taper.profile`, shared with the stage that evaluates it
    taper_segments: int = 64
    #: the narrowest slab feature the process allows, um. The slab derived from
    #: the ridges is opened by half of this, which removes the spikes sizing
    #: leaves at the acute tip of a facet taper
    slab_min_width_um: float = 0.30
    input_facet_angle_deg: float = 8.0
    output_facet_angle_deg: float = 0.0
    #: Side of the square bond pad on each electrode, in micrometres. This was a
    #: literal 80.0 in the layout stage until 2026-08-12, repeated in two places.
    #: 80 um accepts a probe or a wedge bond and is tight for a ball bond with
    #: 25 um gold wire, where 100 um is ordinary practice. The default is kept at
    #: 80.0 so that existing masks are unchanged; a design intended for wire
    #: bonding sets it explicitly. The slab and floor plan are sized from this
    #: value, so raising it widens the etch-clear region with it.
    bond_pad_um: float = 80.0
    cell_name: str = "EDBR"
    #: the layer the grating posts are drawn on, by name in `layer_map`. Left
    #: unset they are drawn on the guide layer with the ridge itself, which is
    #: what every mask this chain emitted before 2026-09-03 carries.
    #:
    #: A process may ask for them elsewhere. LT-PRO reserves 2/11 for small
    #: repeating features such as a Bragg reflector or a photonic crystal,
    #: stating that it eases the rule check and the reticle assembly, while the
    #: ridge itself is 2/10. Posts appended to the guide layer cannot be moved
    #: by a layer map or by a derived layer, because by then they are the same
    #: polygons as the guide.
    #:
    #: A rule written against the guide layer stops seeing the posts once they
    #: move, so the rule set is to be extended to the new layer at the same
    #: time. The DRC stage reports which layers a deck names and which of them
    #: the mask leaves empty, which is where that omission shows.
    grating_layer: str | None = None
    layer_map: dict[str, list[int]] = Field(
        default_factory=lambda: {
            "WG": [1, 0],
            "SLAB": [2, 0],
            "METAL": [10, 0],
            "PAD": [11, 0],
            "SEAL": [20, 0],
            "MARK": [21, 0],
            "DICE": [22, 0],
            "FACET": [23, 0],
            "ORIENT": [24, 0],
            "FILL": [25, 0],
            "LABEL": [66, 0],
            "FLOORPLAN": [99, 0],
            "CHIP_INNER": [6, 0],
            "CHIP_OUTER": [6, 1],
        }
    )
    #: the facet is drawn as an angled end face and the die edge is marked.
    #: The angle exists to keep the facet reflection out of the guide, and it
    #: only does so if it is in silicon rather than in a coupling calculation
    #: How the angle between the guide and the facet is realised on the mask.
    #:
    #: "sheared" keeps every guide parallel to the die axis and cuts the end
    #: face at the angle, which requires the die edge itself to be diced at that
    #: angle to the whole array.
    #:
    #: "angled" keeps the die edge perpendicular and routes the guide to meet it
    #: at the angle, through a bend of `facet_bend_radius_um` followed by a
    #: straight run of `facet_angled_length_um`. This is the ordinary practice,
    #: and it costs a lateral excursion the floor plan must carry.
    facet_route: Literal["sheared", "angled"] = "sheared"
    facet_bend_radius_um: float = 500.0
    facet_angled_length_um: float = 40.0
    draw_facets: bool = True
    #: distance from the drawn facet plane to the die edge, um. The guide is
    #: not drawn into this band; it is removed by the cleave or the polish
    facet_recess_um: float = 5.0
    #: how far the facet keep-out extends either side of the guide, um
    facet_keepout_um: float = 30.0
    #: orientation of the propagation direction with respect to the crystal
    #: axis that the declared electro-optic coefficient requires, in degrees.
    #: Zero is aligned. It is drawn on the die as a key and is checked against
    #: the platform cut, an X-cut film reached along the wrong axis not
    #: presenting r33 to a quasi-TE mode at all
    crystal_misalignment_deg: float = 0.0
    #: draw the orientation key and the cut legend on the die
    draw_orientation_key: bool = True
    #: refuse a mask that draws fewer than every grating period. The default is
    #: false, a partial mask being the right object for a rule smoke test. It is
    #: to be set on any design that will be submitted
    require_complete: bool = False
    #: read both emitted files back and take their exclusive-or. Two writers of
    #: one polygon list is a cross-check available at negligible cost
    compare_backends: bool = True
    #: emit OASIS beside GDSII. Several foundries require it, and it is smaller
    write_oasis: bool = True
    #: write the layer table beside the mask, as KLayout layer properties and as
    #: a plain map. A mask without one is a set of numbered layers
    write_layer_table: bool = True
    #: layers produced by boolean operation on the drawn ones, which is where
    #: mask polarity is expressed
    derived_layers: list[DerivedLayer] = Field(default_factory=list)
    #: geometry the rule deck does not examine: non-simple polygons, acute
    #: angles, slivers, coincident duplicates and vertex-count caps
    check_geometry: bool = True
    #: smallest interior angle admitted, degrees. An acute angle prints as a
    #: rounded one and is refused by most decks
    min_angle_deg: float = 30.0
    #: largest vertex count admitted on one polygon. Zero disables the check
    max_vertices: int = 200


class FillCfg(BaseModel):
    """Placement of the fill a density window requires.

    The `mask` stage sizes the shortfall; this places it. What a foundry states
    is the pattern, its pitch and how far it must stand off each feature, and
    those three are the fields here. Nothing is invented: with no values
    declared the placement is disabled and the shortfall is reported as before.
    """
    enabled: bool = False
    #: side of one fill element, um
    size_um: float = 2.0
    #: centre-to-centre spacing of the fill lattice, um
    pitch_um: float = 4.0
    #: how far the fill must stand off each named layer, um
    exclusion_um: dict[str, float] = Field(
        default_factory=lambda: {"WG": 5.0, "METAL": 5.0, "PAD": 10.0}
    )
    #: the layer the fill is drawn on. It is a layer of the process, so it is
    #: named here rather than assumed
    layer: str = "FILL"
    #: stop once the tile is inside its window. Filling past the minimum wastes
    #: area and, on a guide layer, adds scattering for nothing
    stop_at_minimum: bool = True


class SchematicNet(BaseModel):
    """One net of a declared schematic, named by the labels it must contain."""
    name: str
    #: the text labels the extraction must find on this one net
    labels: list[str] = Field(default_factory=list)


class MaskCfg(BaseModel):
    """Checks that a rule deck does not make: density, fill and connectivity."""
    enabled: bool = True
    #: as `drc.target`. Density in particular is a property of the die and
    #: not of the device, the frame and the monitors contributing to it
    target: Literal["device", "die"] = "device"
    #: a region within which violations are counted separately rather than as
    #: real, given as [x0, y0, x1, y1] in die coordinates. It exists for the
    #: process monitors: a critical-dimension vernier has to straddle the
    #: minimum width to find where printing fails, so its narrowest rungs breach
    #: the rule on purpose. Checked against the device cell those shapes are out
    #: of scope and the report is silent about them; checked against the die
    #: they are reported as real, and a reader cannot tell them from a defect.
    #: Left unset, every violation counts as real.
    #:
    #: The box is read from the reticle stage where that stage declares one, so
    #: it follows the monitors rather than being written out by hand.
    declared_region_from_reticle: bool = True
    #: layers whose shapes are merged and counted as connected regions
    connected_layers: list[str] = Field(default_factory=lambda: ["WG", "METAL", "PAD"])
    #: how many connected regions each layer should have when correct
    expected_regions: dict[str, int] = Field(default_factory=dict)
    #: which layout those counts describe. A device-level expectation compared
    #: against an assembled die reports a difference that is not a defect, so
    #: the comparison is reported as skipped rather than made
    expectations_describe: Literal["device", "die"] = "device"
    #: the same counts for the assembled die, which carries the frame, the
    #: monitors and the split ladder in addition to the device. Declaring both
    #: lets one design be checked at either scale without editing it: the stage
    #: selects the set matching what it is checking. Left empty, a die-level run
    #: reports the comparison as not made rather than comparing against figures
    #: that describe something else
    expected_regions_die: dict[str, int] = Field(default_factory=dict)
    #: layer pairs that must not overlap
    must_not_touch: list[list[str]] = Field(default_factory=lambda: [["WG", "METAL"]])
    #: extract a netlist rather than merely counting regions per layer. Layer
    #: pairs listed here are treated as electrically joined where they overlap,
    #: so that a pad reaching its electrode is one net and a break is two
    extract_netlist: bool = True
    joined_layers: list[list[str]] = Field(default_factory=lambda: [["METAL", "PAD"]])
    #: how many nets the extraction should find. A count above the expected
    #: figure is a break; below it is a short
    expected_nets: int | None = None
    #: as above, for the assembled die
    expected_nets_die: int | None = None
    #: the intended circuit, as named nets and the labels each must carry. The
    #: extraction is compared against it, which is layout versus schematic
    #: without device recognition: connectivity is established, and what the
    #: connected thing *is* remains undetermined
    schematic: list[SchematicNet] = Field(default_factory=list)
    #: the layer carrying the text labels the extraction takes net names from
    label_layer: str = "LABEL"
    fill: FillCfg = Field(default_factory=FillCfg)
    #: (layer, minimum, maximum) area fraction, per tile
    density_windows: list[list] = Field(default_factory=list)
    density_tile_um: float = 200.0


class DRCRule(BaseModel):
    name: str
    kind: Literal["min_width", "min_space", "min_area", "min_enclosure", "min_separation"]
    layer: str
    other_layer: str | None = None
    value_um: float
    severity: Literal["error", "warning"] = "error"
    #: corners at or above this interior angle are not reported as a width or a
    #: space violation. Every convex corner brings two edges arbitrarily close
    #: together, so a check without this threshold reports the corner itself.
    #: 90 degrees is the engine default and it is the wrong value wherever a
    #: feature is drawn at an angle: an 8 degree facet on a guide necessarily
    #: produces an 82 degree corner, which is manufacturable and is reported
    ignore_angle_deg: float = 90.0


class DRCCfg(BaseModel):
    """Geometric verification of the emitted mask.

    Two paths, and they are not equivalent. ``rules`` are declared here and
    evaluated by the KLayout Region engine in process, which is adequate for a
    smoke test and attests to nothing but the rules supplied. ``deck`` names a
    foundry runset, executed by the KLayout application in batch, which is what
    a fabrication run is actually checked against. Where a deck is given it is
    run in addition to the rules, and its violations are reported separately.
    """
    enabled: bool = True
    #: which layout is checked. "device" is the cell the layout stage emitted;
    #: "die" is the assembled reticle, being the object actually submitted.
    #: A frame that is drawn and never checked is a frame that is assumed
    target: Literal["device", "die"] = "device"
    rules: list[DRCRule] = Field(default_factory=list)
    #: path to a foundry `.lydrc` runset, relative to the design file
    deck: str | None = None
    #: the KLayout application. The Python module cannot run a runset; the
    #: application can. The portable build is the default location on Windows
    klayout_exe: str | None = None
    deck_timeout_s: int = 3600


class CornersCfg(BaseModel):
    """Process corners: the chain re-run at the edges of what will be fabricated.

    A single run describes the drawn design. What is delivered is a distribution,
    and the quantity that matters is how far the metrics move across it. Each
    entry of ``parameters`` names a dotted field of this design file and the
    excursion to apply either side of its nominal value.
    """
    enabled: bool = False
    #: "onefactor" moves one parameter at a time, giving 2n+1 runs;
    #: "factorial" takes every combination of low, nominal and high, giving 3^n
    mode: Literal["onefactor", "factorial"] = "onefactor"
    parameters: dict[str, float] = Field(default_factory=dict)
    #: dotted metric paths to tabulate. Empty means the targets of this design
    metrics: list[str] = Field(default_factory=list)


class SearchParameter(BaseModel):
    """One free variable of a directed search."""
    path: str                        # dotted design field
    min: float
    max: float
    #: fractional step used to probe the local sensitivity. Small enough to be
    #: local, large enough to exceed the numerical noise of the chain.
    probe: float = 0.05


class SearchCfg(BaseModel):
    """Directed search for a design meeting its declared targets.

    Not an optimiser. The bounds of every parameter are evaluated before any
    search begins, so that a requirement lying outside what a parameter can
    reach is reported as unreachable with the binding bound named, rather than
    approached until the budget is spent. Monotonicity across the bracket is
    checked, since a metric that is not monotone cannot be bisected and the fact
    is a finding about the metric.

    `constraints` are comparisons between two dotted fields, or between a field
    and a number. A candidate violating one is skipped rather than clamped.
    """
    enabled: bool = False
    parameters: list[SearchParameter] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    #: the stage subset to re-run per evaluation. Shorter is faster; it must
    #: nonetheless produce every metric the targets name.
    stages: list[str] = Field(default_factory=list)
    #: severities the search attempts to satisfy
    severities: list[str] = Field(default_factory=lambda: ["must", "should"])
    max_evaluations: int = 60


class Target(BaseModel):
    """One acceptance criterion."""
    metric: str                      # dotted path into the metrics dict
    value: float | None = None
    min: float | None = None
    max: float | None = None
    rel_tol: float | None = None     # fractional tolerance around `value`
    abs_tol: float | None = None
    unit: str = ""
    source: str = ""
    severity: Literal["must", "should", "info"] = "must"


def walk_dotted(obj: Any, parts: list[str]) -> Any:
    """Traverse a dotted path across model attributes and mapping keys alike.

    A per-layer quantity such as ``process.bias_um.WG`` is a key within a map
    rather than an attribute, and it is exactly the kind of quantity a corner
    study or a reticle split varies.
    """
    for p in parts:
        obj = obj[p] if isinstance(obj, dict) else getattr(obj, p)
    return obj


def get_dotted(obj: Any, dotted: str) -> Any:
    return walk_dotted(obj, dotted.split("."))


def set_dotted(obj: Any, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = walk_dotted(obj, parts[:-1])
    if isinstance(node, dict):
        node[parts[-1]] = value
    else:
        setattr(node, parts[-1], value)


class AcknowledgedFinding(BaseModel):
    """One warning the design accepts, with the reason it is accepted."""
    key: str
    reason: str


class WarningsCfg(BaseModel):
    """Findings the design has examined and accepted.

    The chain raises warnings from ninety call sites and, until 2026-08-17, no
    code read them: a run could emit seventeen findings and still be reported a
    clean pass, because the acceptance verdict grades targets and a finding
    carrying no threshold had no owner.

    A finding is therefore acknowledged here by key, with its reason, and
    `tools/warning_inventory.py` lists what a run emitted against what the design
    accepts. The value is not in recording the known findings; it is that a
    finding appearing for the first time is visible immediately, which is the
    only mechanism that catches what nobody anticipated.
    """
    acknowledged: list[AcknowledgedFinding] = Field(default_factory=list)
    #: fail the run on any finding the design has not acknowledged. Off by
    #: default: turning it on before the standing findings are recorded fails
    #: every released design at once, which teaches the reader to bypass the
    #: gate rather than to read it.
    enforce: bool = False


class Design(BaseModel):
    meta: Meta
    platform: Platform = Field(default_factory=Platform)
    mesh: Mesh = Field(default_factory=Mesh)
    waveguide: Waveguide = Field(default_factory=Waveguide)
    grating: Grating = Field(default_factory=Grating)
    electrodes: Electrodes = Field(default_factory=Electrodes)
    mzm: MzmCfg = Field(default_factory=MzmCfg)
    modulator: ModulatorCfg = Field(default_factory=ModulatorCfg)
    cavity: Cavity = Field(default_factory=Cavity)
    chirp: ChirpDrive = Field(default_factory=ChirpDrive)
    dynamics: DynamicsCfg = Field(default_factory=DynamicsCfg)
    search: SearchCfg = Field(default_factory=SearchCfg)
    taper: TaperCfg = Field(default_factory=TaperCfg)
    fdtd: FDTDCfg = Field(default_factory=FDTDCfg)
    bend: BendCfg = Field(default_factory=BendCfg)
    facet: FacetCfg = Field(default_factory=FacetCfg)
    fem: FemCfg = Field(default_factory=FemCfg)
    circuit: CircuitCfg = Field(default_factory=CircuitCfg)
    corners: CornersCfg = Field(default_factory=CornersCfg)
    process: ProcessCfg = Field(default_factory=ProcessCfg)
    layout: LayoutCfg = Field(default_factory=LayoutCfg)
    reticle: ReticleCfg = Field(default_factory=ReticleCfg)
    mask: MaskCfg = Field(default_factory=MaskCfg)
    drc: DRCCfg = Field(default_factory=DRCCfg)
    release: ReleaseCfg = Field(default_factory=ReleaseCfg)
    warnings: WarningsCfg = Field(default_factory=WarningsCfg)
    targets: list[Target] = Field(default_factory=list)
    allow_unconfirmed_materials: bool = True
    stages: list[str] = Field(
        default_factory=lambda: [
            "mode", "taper", "fem", "fdtd", "bend", "facet", "grating", "eo", "cavity",
            "circuit", "layout", "reticle", "drc", "mask", "verify", "release"
        ]
    )

    @model_validator(mode="after")
    def _check(self) -> "Design":
        g = self.grating
        if g.enabled and g.period_um is None and g.target_wavelength_um is None:
            raise ValueError("grating: set either period_um or target_wavelength_um")
        return self

    @classmethod
    def load(cls, path: Path | str) -> "Design":
        path = Path(path)
        with open(path, "r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        # allow `extends:` for shared platform files
        if "extends" in raw:
            base_path = (path.parent / raw.pop("extends")).resolve()
            with open(base_path, "r", encoding="utf-8") as fh:
                base = yaml.safe_load(fh)
            raw = _deep_merge(base, raw)
        d = cls.model_validate(raw)
        d._source_path = path  # type: ignore[attr-defined]
        return d

    @property
    def source_path(self) -> Path | None:
        return getattr(self, "_source_path", None)

    def materials_path(self) -> str | None:
        """Where ``platform.materials_file`` actually is.

        The path was previously handed to the loader as written, so it was
        resolved against the working directory and a design carrying a foundry
        material file ran from the repository root and failed from its own
        folder. Three locations are searched in order, the first that exists
        being taken: beside the design file, against the working directory,
        and against the root of the chain installation, which is where the
        vendored PDK material files live.

        A path that matches none of the three raises here, naming what was
        tried, rather than reaching the YAML loader as a bare file-not-found.
        """
        declared = self.platform.materials_file
        if declared is None:
            return None
        p = Path(declared)
        if p.is_absolute():
            if p.exists():
                return str(p)
            raise FileNotFoundError(f"platform.materials_file: {p} does not exist")

        here = Path(__file__).resolve()
        candidates: list[Path] = []
        src = self.source_path
        if src is not None:
            candidates.append(src.resolve().parent / p)
        candidates.append(Path.cwd() / p)
        candidates.append(here.parents[2] / p)     # the chain installation
        candidates.append(here.parents[3] / p)     # the repository above it
        tried: list[Path] = []
        for c in candidates:
            if c not in tried:
                tried.append(c)
        for candidate in tried:
            if candidate.exists():
                return str(candidate)
        raise FileNotFoundError(
            "platform.materials_file "
            f"{declared!r} was not found. Tried: "
            + ", ".join(str(t) for t in tried)
        )


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
