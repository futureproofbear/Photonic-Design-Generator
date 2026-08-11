# Project IP — Restricted Material

The contents of this folder are project-proprietary. They comprise material
received from the client and analysis derived from it.

## Restrictions

1. No content from this folder is to be copied, summarised, quoted or
   paraphrased into any location outside it. This includes the generator
   documentation, the shared toolchain, the public examples, the skills and
   sub-agents under `.claude/`, and commit messages.
2. The client name, the programme identity, the application, the deliverable
   codes and the work-package codes are all proprietary. The list held in
   `proprietary_terms.txt` is authoritative.
3. `proprietary_terms.txt` is itself proprietary and is not to be relocated.
4. Foundry data received under a non-disclosure agreement is to be placed in
   `pdk/` within this folder and referenced by means of the `materials_file`
   field of a design, never by editing the shared `design-chain/pdk/`.

## Enforcement

The boundary is checked mechanically. Execute from the repository root:

```bash
python tools/check_ip_boundary.py
```

A non-zero exit code is returned where any declared term is found outside this
folder. The check is to be run before any commit and before any part of the
generator is shared.

## Permitted Direction of Flow

Generic capability may flow **into** this folder: the shared toolchain, the
public examples, the methodology documentation and the accumulated skills may
all be used here.

Project information must never flow **out**. Where a technique developed here is
of general value, it is to be re-expressed without project-identifying content
and contributed to the generic tree as a separate, sanitised change. The
procedure is defined in [`../.claude/LESSONS.md`](../.claude/LESSONS.md).
