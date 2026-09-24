"""Make the cloudflare toolchain's local packages importable during collection.

B-HOUSE-2 (2026-08-06): the tests under ``tests/`` and ``tests_connectors/``
import ``rmv2_extension`` and ``rmv2_connectors`` as top-level packages. Both
packages live in *this* directory, so they import fine when pytest is invoked
from here, but a repo-root ``python3 -m pytest`` run leaves this directory off
``sys.path`` and every module fails to collect (12 ``ModuleNotFoundError``
collection errors). Prepending this directory fixes collection at the root
without touching or weakening any test — all 69 pass either way.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
