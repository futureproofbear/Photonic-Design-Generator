# The register of every document is fixed, and it is fixed here

This file governs the form of every document produced within the framework: the
reference manual, a design report, a concept statement, a ledger entry, a rule,
a commit message and the prose returned by an agent in the course of work. It
is resident under `rules/generic/` because it applies to any photonic design, on
any platform, with any tool.

Its provenance differs from that of the rules beside it, and the difference is
stated under "Provenance" at the foot of this file.

## Core Tone
- Maintain a strictly formal, objective, and detached professional register.
- Eliminate all colloquialisms, conversational filler, expressions of enthusiasm, and contractions (e.g., use "do not" instead of "don't").
- Address the user or subject matter with academic or corporate decorum; personal pronouns ("I", "you") are minimized.

## Syntactic Constraints (Passive Voice)
- Default to the passive voice for all general assertions, explanations, and procedural descriptions. 
- Restrict active voice strictly to necessary imperative command sequences within technical instructions.
- Reframe active statements (e.g., "The system processes data") into passive equivalents (e.g., "Data is processed by the system").

## Vocabulary Restrictions
- Avoid negative colloquial declarations or informal architectural summaries, such as "Nothing in the chain opens a GUI".
- Avoid compound buzzwords and hyphenated technical slang, such as "dependency-light", "zero-dependency", "cloud-native", or "production-ready".
- Avoid conversational qualifiers or meta-commentary, specifically words like "honest", "honestly", "frankly", "to be fair", or "truthfully".
- Avoid marketing-centric or idiomatic engineering jargon, such as "first-class field", "first-class citizen", "cutting-edge", or "game-changer".
- Avoid: "delve", "leverage", "utilize", "robust", "seamless", "furthermore", "in conclusion", "it's worth noting".
- Prefer formal transitions and technical descriptions: "It is observed", "It has been determined", "Consideration must be given", "The field is natively supported".
- Avoid vocabulary denoting security classification or information secrecy markings. The separation maintained between the generic tree and project work is an intellectual-property boundary, and is to be described as such: "proprietary", "IP boundary", "project IP", "restricted to the project scope".

## Sentence Structure
- Do not interrupt a sentence between its subject and its verb with a parenthetical enumeration set off by dashes. Reject constructions of the form "Every quantity downstream of X — a, b, c and d — arises from a single cause". The enumeration is to be placed after the main clause, or presented as a list, or given its own sentence.
- Restrict dashes to a single terminal clause where one is required at all. Paired dashes enclosing an embedded aside are not to be used.
- Avoid contrastive endings appended for rhetorical emphasis, such as "rather than from three", "and not by convention", or "not merely recorded". Where a contrast is material, it is to be stated as a separate assertion.
- One assertion per sentence. Where a clause carries a second finding, it is to be separated.

## Directness and Negation

- State what is the case. A sentence whose entire content is a denial is to be
  rewritten as the corresponding assertion. Reject "Nothing is waived" in favour
  of "Every condition was met on its own terms". Reject "None is a defect in the
  mask" in favour of "All three arise from the physics and the mask is sound".
- Do not define a thing by what it is not. Reject "The gain element is bought,
  not designed" in favour of "The gain element is a purchased part, and its
  datasheet figures enter the chain as inputs".
- Eliminate double negatives. Reject "none of the twelve `must` rows is unmet"
  in favour of "all twelve `must` rows are met". Reject "no condition was
  waived" in favour of "every condition was satisfied".
- Words of negation are to be counted and reduced. "none", "nothing", "neither"
  and "nor" each signal a sentence that is likely to read better as a positive
  assertion. Where a negative is the true statement, one plain "not" is
  sufficient.
- A requirement, a procedure or a derivation is to be described by what was
  done, in the order it was done. Reject compressed nominal forms such as "R8
  inverted is a procurement criterion", which names an operation without
  performing it. Write instead: "Requirement R8 sets a ceiling on the round-trip
  delay. That ceiling gives a maximum gain-chip length of 1900 um, and the parts
  were selected against it."
- Where a term of art is used, give the quantity it refers to in the same
  sentence. A reader is to be able to follow the argument without reconstructing
  an implied step.
- Constructions of the form "X shares no A and no B", "X carries no information"
  and "there is no quantity on which it is worse" are to be replaced by the
  positive equivalent. Write "the two solvers were written independently and
  discretise the cross-section by different methods"; write "which makes it
  uninformative"; write "it is equal or better on every quantity the
  requirements bound".

## Provenance

This file is a house standard, adopted by decision on 2026-08-22. It is derived
from no design activity, and it cites no entry of the ledger.

The citation requirement stated in [`../README.md`](../README.md) is therefore
waived for this file, and the waiver is deliberate. A rule that governs the form
of an assertion is settled by choice. A rule that governs the substance of an
assertion is settled by evidence, and the requirement stands unchanged for every
other file in this tier.

## How this file is reached

The file is tracked, so it travels with the framework. Two paths reach it.

Work conducted inside the framework repository reaches it through the root
`CLAUDE.md`, which imports it. That root file is excluded from version control,
in keeping with the policy that an operating file is instruction to an agent.

A scope that mounts the framework as a submodule at `.framework/` reaches it by
writing `@.framework/rules/generic/prose-and-register.md` in the `CLAUDE.md` at
its own root. Automatic loading of a `CLAUDE.md` held inside the submodule is
conditional on what the session reads. An explicit import is deterministic, and
the explicit import is required.
