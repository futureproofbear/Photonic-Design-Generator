"""picchain - a headless, agent-drivable design chain for photonic integrated circuits.

Built on the open toolset catalogued in joamatab/awesome_photonics:
klayout / gdsfactory for layout and DRC, a dependency-light FD mode and
electrostatic core for the physics (with femwell as an optional FEM
cross-check), and coupled-mode + transfer-matrix theory for the gratings.

The unit of work is a *design*: one standalone PIC (or PIC building block)
described by a single ``design.yaml`` in its own folder, with its acceptance
targets declared alongside it.  Every run is reproducible from that file plus
the pinned environment, and every result is a JSON metric tree.
"""

__version__ = "0.1.0"

from .config import Design  # noqa: E402,F401
from .materials import MaterialLibrary  # noqa: E402,F401

__all__ = ["Design", "MaterialLibrary", "__version__"]
