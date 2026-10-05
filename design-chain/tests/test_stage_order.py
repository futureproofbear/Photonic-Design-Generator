"""A stage that reads another optionally is ordered by registration alone.

`resonator` takes its power coupling from `fdtd` where that stage solved a
coupler, and from the design file where it did not. Making `fdtd` a dependency
would force an external time-domain solve on a stage that is otherwise closed
form and costs microseconds, so it is not one. The planner sorts topologically
and breaks ties by the registration order of `STAGES`, which leaves that
registration as the only thing ordering the pair.

Registered beside `bend` it ran first. The run wrote a `resonator` payload built
from the declared coupling, then wrote an `fdtd` payload carrying the measured
one, and reported the source as declared. The metrics were internally consistent
and the plan was `mode, resonator, grating, fdtd`.
"""

from __future__ import annotations

from picchain.stages import DEPENDENCIES, STAGES


def plan(requested: list[str]) -> list[str]:
    """The planner of `cli._plan`, reproduced here over the registration map."""
    order = list(STAGES)
    want: set[str] = set()

    def add(s: str) -> None:
        if s in want:
            return
        for dep in DEPENDENCIES[s]:
            add(dep)
        want.add(s)

    for s in requested:
        add(s)

    out: list[str] = []
    done: set[str] = set()
    while len(out) < len(want):
        ready = [s for s in order
                 if s in want and s not in done
                 and all(d in done for d in DEPENDENCIES[s])]
        assert ready, f"cycle among {sorted(want - done)}"
        out.append(ready[0])
        done.add(ready[0])
    return out


def test_the_resonator_runs_after_the_solve_it_reads_its_coupling_from():
    ordered = plan(["mode", "grating", "fdtd", "resonator"])
    assert ordered.index("fdtd") < ordered.index("resonator")


def test_the_resonator_runs_after_the_bend_whose_row_it_reads():
    ordered = plan(["mode", "bend", "resonator"])
    assert ordered.index("bend") < ordered.index("resonator")


def test_the_resonator_still_runs_without_either():
    assert plan(["resonator"]) == ["mode", "resonator"]


def test_every_stage_is_registered_after_the_stages_it_depends_on():
    """The tie-break only helps where the declared order already agrees."""
    order = list(STAGES)
    for stage, deps in DEPENDENCIES.items():
        for dep in deps:
            assert order.index(dep) < order.index(stage), (
                f"{stage!r} is registered before its dependency {dep!r}; the "
                "topological sort still orders them, and every tie around them is "
                "then broken against the declared order")
