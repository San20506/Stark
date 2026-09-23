#!/usr/bin/env python3
"""Weekly maintenance utilities for STARK memory databases.

Run via: python scripts/db_maintenance.py
Or schedule via cron/APScheduler for automated upkeep.
"""

import sqlite3
import sys
from pathlib import Path


def maintain_episodic_db(db_path: str) -> dict:
    """Run SQLite maintenance on the episodic diary database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Dict with maintenance results and stats.
    """
    conn = sqlite3.connect(db_path)
    results = {}

    # Get DB size before
    size_before = Path(db_path).stat().st_size / (1024 * 1024)
    results["size_before_mb"] = round(size_before, 2)

    # Run maintenance PRAGMAs
    conn.execute("PRAGMA incremental_vacuum")
    conn.execute("PRAGMA optimize")
    conn.execute("PRAGMA analyze")

    # Get stats
    cursor = conn.execute("SELECT COUNT(*) FROM episodes")
    results["episode_count"] = cursor.fetchone()[0]

    size_after = Path(db_path).stat().st_size / (1024 * 1024)
    results["size_after_mb"] = round(size_after, 2)
    results["freed_mb"] = round(size_before - size_after, 2)

    conn.close()
    return results


def maintain_chroma(persist_dir: str) -> dict:
    """Run ChromaDB maintenance (requires chromadb-ops).

    Args:
        persist_dir: Path to ChromaDB persist directory.

    Returns:
        Dict with maintenance status.
    """
    results = {"status": "skipped", "reason": ""}

    try:
        import chromadb_ops as chops  # type: ignore
    except ImportError:
        results["reason"] = "chromadb-ops not installed. Install: pip install chromadb-ops"
        return results

    try:
        chops.db_clean(persist_dir)
        results["status"] = "cleaned"
    except Exception as e:
        results["status"] = "error"
        results["reason"] = str(e)

    return results


def main() -> None:
    """Run all maintenance tasks."""
    from core.constants import DATA_DIR

    db_path = str(Path(DATA_DIR) / "memory" / "episodic.db")

    print(f"=== STARK DB Maintenance ===")
    print(f"Database: {db_path}")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print("\n--- Episodic DB ---")
    results = maintain_episodic_db(db_path)
    for k, v in results.items():
        print(f"  {k}: {v}")

    print("\n--- ChromaDB ---")
    chroma_dir = str(Path(DATA_DIR) / "memory" / "semantic_chroma")
    chroma_results = maintain_chroma(chroma_dir)
    for k, v in chroma_results.items():
        print(f"  {k}: {v}")

    print("\nDone.")


if __name__ == "__main__":
    main()
