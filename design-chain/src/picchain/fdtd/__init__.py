"""FDTD access.

The solver used is meep, which is executed in its own environment rather than
being imported here: it has no Windows build, and its MPI runtime is not one
that the rest of the chain should be made to depend upon. ``bridge`` holds the
invocation and the JSON contract; ``meep_taper`` is the script that runs on the
far side and imports meep.
"""

from . import bridge

__all__ = ["bridge"]
