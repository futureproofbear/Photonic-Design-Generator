# <Scope Name>

<One paragraph: what is being designed and for what purpose. This file lies
inside the IP boundary; the scope may be described plainly here.>

**Status:** <not started | in progress | delivered>
**Source of requirements:** <the client document, held in `references/`>

## Design Register

| design | requirement reference | last verdict | status |
|---|---|---|---|
| | | | |

## Structure

```
docs/            analysis produced for this scope
designs/         one folder per PIC; `_platform/` holds the shared process stack
references/      documents received from or produced for the client
pdk/             foundry data received under non-disclosure
```

## Execution

```bash
cd ../../design-chain
./.venv/Scripts/python.exe -m picchain.cli run ../projects/<scope-name>/designs/<design>/design.yaml
```

## Requirement Mapping

<Record here the correspondence between the client work packages or milestones
and the stages of the chain. This mapping is project information and is not held
in the generic documentation.>

## Open Items

<Assumptions awaiting confirmation, unresolved specification conflicts, and
decisions pending with the client.>
