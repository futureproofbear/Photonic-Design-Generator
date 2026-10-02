# femwell and gmsh

A full-vectorial finite-element mode solve on a conforming triangulation, used
as the independent cross-check against the chain's semi-vectorial
finite-difference solver on a structured mesh.

## The natural boundary condition is a magnetic wall

A curl-curl formulation imposes no essential condition by default, and the
resulting natural condition forces the tangential **magnetic** field to zero at
the window edge. That is a magnetic wall. A layer reaching that edge is
incompatible with it, and the solve returns an index low by a hundred times the
error of a comparable finite-difference solve on the same problem.

**Set the condition explicitly to the electric wall**, which forces the
tangential electric field to zero and matches what a finite-difference solver
with a Dirichlet window imposes on its dominant component.

The defect is recorded because of how it presents. It returns a plausible number
rather than a failure, and where this solver is being used as a cross-check the
discrepancy is attributed to the method under test rather than to the
instrument.

**A cross-check is anchored to a closed-form result before it is pointed at
anything.**

## The `radius` argument of `compute_modes` is an isotropic approximation

`femwell.maxwell.waveguide.compute_modes(radius=R)` scales an isotropic
permittivity by (1 + x/R)^2 and keeps mu = 1. The exact straight equivalent of
a bend is anisotropic, with eps' = eps diag(s, s, 1/s) and mu' = diag(s, s, 1/s)
for s = r/R. The two agree for a guide uniform normal to the plane of the bend.
On a 220 nm by 500 nm silicon strip at R = 10 um the isotropic form gave 3.7
times the index shift of a cylindrical eigenmode solve.

**Solve a bend through `femmode.solve_cross_section(radius_um=...)`**, which
applies the anisotropic tensors and projects H with mu'. Its fields are then
physical on the plane of a straight-to-bend junction, so
`FemModeResult.power_coupling` gives the mismatch of that junction directly.
A bend mode from femwell's own `radius` argument carries an H computed with
mu = 1, and an overlap formed from it is in error.

## What this solver adds that the finite-difference solver cannot report

**Polarisation purity.** A semi-vectorial formulation carries one transverse
field component and assumes the other absent. The share of transverse energy
actually carried by the minor component is invisible to it, and that share is
exactly the weight attaching to everything the formulation omits. A
full-vectorial solve returns it directly. **Read
`fem.polarisation_purity` before the semi-vectorial index is relied upon.**

**A usable anisotropy bracket.** A scalar-permittivity solver run at each
principal index of a birefringent film brackets the anisotropic answer, and the
bracket is as wide as the birefringence and of no practical use alone. Weighted
by the polarisation purity it becomes an estimate of the right order, the
dominant component already seeing the correct axis.

**A bound on the mesh error of a difference.** The two solvers discretise one
cross-section by different methods, so their spread on an index perturbation
bounds the mesh error on the quantity that sets a grating's coupling constant.
On one shallow-etched cross-section the absolute indices differed by 2.6 × 10⁻⁴
while the perturbation agreed to 1.8 %.

## The comparison is admissible only where it is resolved

Halving the mesh density of the finite-element solve moved its answer by one
sixth of the separation between the two solvers, so the comparison distinguished
something. Where the two were comparable, nothing would have been established in
either direction. **Read `fem.convergence.resolved` before the comparison.**

## A validation fixture placing an interface on a node is not a solver defect

A finite-difference validation in which a material interface coincides with a
node widens the core by one cell and biases n_eff upward. Where a solver appears
to disagree with an analytic result at the third decimal place, examine the
fixture before the solver. Production code sub-pixel averages; validation
fixtures stagger the interface between nodes.

## Evidence

`.claude/LESSONS.md` L012, L013, T005, T009, T018, T096.
