"""Drop the segment_embeddings table to allow recreation with correct vector dimension."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.db.base import engine
from backend.app.core.config import settings

print(f"Dropping segment_embeddings table from {settings.DATABASE_URL}...")

with engine.connect() as conn:
    # Drop the table if it exists
    conn.execute("DROP TABLE IF EXISTS segment_embeddings;")
    conn.commit()

print("Done. The table will be recreated automatically on the next run with the correct dimension.")
