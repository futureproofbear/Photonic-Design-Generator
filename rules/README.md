# Rules

Short, resident rules of method. Each file states one rule, gives the mechanism
that makes it true, and cites the ledger entries that record where it was
learnt.

**These files are meant to be in context while work is done.** That is the
property they are written for, and it is what distinguishes them from
[`.claude/LESSONS.md`](../.claude/LESSONS.md). The ledger is the evidence, held
in full and never deleted. A rule is the operative instruction distilled from
it, kept short enough to be read before every design activity.

The chain's own obligations are stated elsewhere and are not repeated here.
[`design-chain/CLAUDE.md`](../design-chain/CLAUDE.md) holds the contract between
an agent and the chain, including the required loop, the exit codes and the
eighteen numbered rules governing its use. What is written here is the method
that applies whether or not this chain is the instrument.

## The three tiers

```
rules/generic/              true of any photonic design, on any platform, with any tool
rules/platform/<stack>/     true of one film stack and its process, on any tool
rules/tool/<tool>/          true of one solver, layout engine or rule-check engine,
                            on any platform
```

**Tier placement is a decision and it is to be made explicitly.** Three
questions settle it, and the narrowest tier that remains true is the correct
one.

1. Does the statement hold for any photonic design regardless of platform and
   tool? It belongs in `generic/`.
2. Does it hold for any design on this film stack regardless of the tool used?
   It belongs in `platform/<stack>/`.
3. Does it hold for this tool regardless of the platform it is applied to? It
   belongs in `tool/<tool>/`.

Where the answer is "only for this design", the statement belongs in that
design's own `design.yaml` comment or its report, and it is to stay there.

**A fact placed in a tier broader than its truth will misinform a design that
lacks the narrower context it depends on.** A sidewall-angle sensitivity
measured on one film stack is a platform fact. A solver boundary condition is a
tool fact. Promoting either to `generic/` asserts a generality that was never
established.

## The intellectual-property boundary applies here

`rules/` sits outside `projects/` and is therefore scanned by
[`tools/check_ip_boundary.py`](../tools/check_ip_boundary.py). Every rule must
survive that check, and the sanitisation test in
[`.claude/LESSONS.md`](../.claude/LESSONS.md) applies unchanged: a rule is
admissible only where it remains true and useful with the originating scope
entirely removed.

A platform-tier file names a film stack and a foundry process, which is
admissible where the platform is publicly offered. A platform-tier file does not
name a project, an application, a deliverable code or the parameter set of a
delivered design.

## Where the method rules sit relative to each other

Three files describe the conduct of a design from its requirements to its mask,
and they are written to be read in that order.

[`requirements-before-design.md`](generic/requirements-before-design.md) covers
the layer above the chain: elicitation, recomputation of the source, the
conflict and decision registers, the open questions, the re-derivation of an
inherited target, the architecture rows and the review that precedes baselining.

[`staged-design.md`](generic/staged-design.md) covers the ordering of the design
itself, from the algebra that refutes an architecture before anything is run to
the layout that ends it, and states what each stage exists to refute.

[`design-under-uncertainty.md`](generic/design-under-uncertainty.md) covers the
method by which a design point is chosen when parameters are unmeasured, which
is what the second stage of that ordering performs.

## Contribution discipline

**State the mechanism, and not the symptom alone.** A rule earns its place by
giving the behaviour that causes the failure. A record that something once went
wrong belongs in the ledger.

**Update rather than duplicate.** Search this tree before adding a file. Where a
finding refines an existing rule, amend that rule and cite the new evidence.
Two files on one subject will drift, and the second will be believed.

**Cite the evidence.** Each rule names the ledger entries behind it, so a reader
who doubts the rule can reach the case that produced it.

**Record what is provisional as provisional.** A rule derived from one
measurement on one cross-section says so in the file, rather than being stated
as settled.

## Which rules apply to a given design

A design states its platform in `design.yaml` and its tools follow from the
stages it enables. The applicable set is therefore `rules/generic/` in full,
`rules/platform/<its stack>/`, and one `rules/tool/` folder per external tool
the run invokes.

| tier | file | subject |
|---|---|---|
| generic | [reference-extraction.md](generic/reference-extraction.md) | a machine-extracted copy of a reference is not the reference |
| generic | [measurement-validity.md](generic/measurement-validity.md) | a passing check is evidence in proportion to its ability to fail |
| generic | [independent-cross-checks.md](generic/independent-cross-checks.md) | what makes two routes to one quantity independent |
| generic | [parameter-scans.md](generic/parameter-scans.md) | a scan is invalid unless every dependent field moves with it |
| generic | [corrections-and-fits.md](generic/corrections-and-fits.md) | adopting, testing and withdrawing a correction factor |
| generic | [expensive-solves.md](generic/expensive-solves.md) | scoping, launching and reading a solve that costs hours |
| generic | [slides-and-figures.md](generic/slides-and-figures.md) | a slide that overflows loses its conclusion silently |
| generic | [prose-and-register.md](generic/prose-and-register.md) | the register every document takes; a house standard, adopted by decision rather than derived from evidence |
| platform | [thin_film_pockels/](platform/thin_film_pockels/) | thin-film lithium niobate and lithium tantalate |
| tool | [klayout/](tool/klayout/) | the rule-check engine and foundry runsets |
| tool | [gdsfactory/](tool/gdsfactory/) | the second layout backend |
| tool | [femwell_gmsh/](tool/femwell_gmsh/) | the finite-element mode solver |
| tool | [meep_mpb/](tool/meep_mpb/) | the time-domain and band-structure solvers |
