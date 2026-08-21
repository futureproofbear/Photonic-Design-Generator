# Platform tier

One folder per **film stack and its process**, holding what is true of that
stack regardless of which solver, layout engine or rule-check engine is used.

A stack is a reusable object. A design is not, and a project is not. The
distinction that decides placement here is whether a second design on the same
stack would need the statement.

## What belongs here

* Measured sensitivities of the stack: how a coupling constant, an effective
  index or an electro-optic overlap responds to a dimension of that
  cross-section, with the value measured and the cross-section it was measured
  on.
* Consequences of the material system: the permittivity contrast that decides
  how a field divides between film and cladding, the anisotropy, the damage and
  photorefractive behaviour.
* Geometry that the stack's own rules force, where the rule is the foundry's
  and not one design's choice.
* The provenance of the stack's material constants, and how far they are from
  process-control data.

## What does not belong here

* A parameter set of a delivered design. That is project content and stays in
  the project.
* A general relation of physics that holds on any platform. That belongs in
  [`../generic/`](../generic/).
* A behaviour of one solver. That belongs in [`../tool/`](../tool/).
* Foundry data received under a non-disclosure agreement. That stays in the
  project, and the generic tree records only that the quantity exists and is to
  be obtained.

## Adding a stack

Create `rules/platform/<stack>/README.md`, name the film, the thickness range,
the etch and the crystal cut it covers, and state at the head which designs the
folder is written from and how many. A sensitivity measured once, on one
cross-section, says so.

| folder | stack |
|---|---|
| [thin_film_pockels/](thin_film_pockels/) | X-cut thin-film lithium niobate and lithium tantalate on insulator, shallow-etched ridge |
