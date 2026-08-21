# Tool tier

One folder per external tool, holding what is true of that tool regardless of
the platform it is applied to.

A tool fact is a behaviour of the instrument. It presents as a property of the
device under study, which is what makes it expensive: a solver returning a
plausible wrong number is attributed to the physics, and a rule engine returning
a clean report is attributed to the mask.

## What belongs here

* A default that changes the meaning of a result without announcing it.
* A boundary condition, a representation or a data structure the tool imposes.
* A failure mode that returns a plausible number rather than an error.
* The conditions under which a check the tool performs is not actually
  performed.

## What does not belong here

* A property of the physical stack. That belongs in
  [`../platform/`](../platform/).
* A method that would apply to any tool computing the same quantity. That
  belongs in [`../generic/`](../generic/).
* An installation instruction. That belongs in
  [`../../design-chain/PICCHAIN_REFERENCE.md`](../../design-chain/PICCHAIN_REFERENCE.md).

## The folders

| folder | tool | subject |
|---|---|---|
| [klayout/](klayout/) | KLayout, and foundry runsets executed through it | layer binding, unexercised rules, geometry representation |
| [gdsfactory/](gdsfactory/) | gdsfactory | the second layout backend and the conditions under which it is skipped |
| [femwell_gmsh/](femwell_gmsh/) | femwell and gmsh | the finite-element mode solve used as a cross-check |
| [meep_mpb/](meep_mpb/) | MEEP and MPB | the time-domain and band-structure solves |
