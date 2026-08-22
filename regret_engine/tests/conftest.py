from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ["GUARDIAN_STORAGE_BACKEND"] = "memory"
os.environ["GUARDIAN_VECTOR_BACKEND"] = "memory"
os.environ["GUARDIAN_EMBEDDING_PROVIDER"] = "hash"
os.environ["LLM_CHAIN"] = "deterministic"
