from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
<<<<<<< HEAD
=======

>>>>>>> e47c39000c3dabd247a01b4b07f971f359cda407
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
