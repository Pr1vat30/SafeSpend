#!/usr/bin/env python3
"""Cross-platform script to initialize the SafeSpend PostgreSQL database.

Can be run directly with:
    python database/init_db.py
or from within backend:
    uv run python -m app.core.init_db
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.init_db import main

if __name__ == "__main__":
    main()
