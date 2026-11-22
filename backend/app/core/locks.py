"""Process-wide write locks for the single-process demo.

The demo runs one uvicorn process against one SQLite file. A few writes target
rows with deterministic ids (the exposure snapshot, the demo world rebuild), so
two requests can race the same row. This lock serializes those writes in-process;
the services keep their database-level guards for anything that still slips
through (for example a second process during local development).
"""

from __future__ import annotations

import threading

DEMO_WRITE_LOCK = threading.Lock()
