"""spanweave-zoo: a recorder for what real OTLP exporters actually send.

The zoo captures telemetry and never improves it (`CLAUDE.md` §0.6). Nothing
here parses a trace, fixes a trace, or has an opinion about one. The audit
module -- the single exception, written by A5 -- is the only place `spanweave`
or `spanweave_live` may be imported, and `tests/gates.py` holds that.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Pre-release, and saying so in the only place a tool reads. Nothing in this
# repository is frozen: not the CLI, not the capture layout, not `MANIFEST.json`.
__version__ = "0.0.1"
