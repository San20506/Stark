"""
Life OS Context Manager
=======================
Reads, writes, and indexes life context files.

All context files use YAML frontmatter + markdown body.
Call ``read_all()`` to get a snapshot of Sandy's full life context.
Call ``update()`` to write changes back (auto-bumps ``last_updated``).
Call ``embed_all()`` to sync to ChromaDB (no-op if chromadb is not installed).
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter

from core.constants import (
    LIFE_OS_CHROMA_COLLECTION,
    LIFE_OS_CONTEXT_DIR,
    PROJECT_ROOT,
)

logger = logging.getLogger(__name__)

CONTEXT_FILES: tuple[str, ...] = (
    "profile.md",
    "goals.md",
    "habits.md",
    "projects.md",
    "weekly_review.md",
)


class ContextManager:
    """Manages reading and writing life context files."""

    def __init__(self, context_dir: Path | None = None) -> None:
        self._dir = context_dir or LIFE_OS_CONTEXT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_all(self) -> dict[str, dict[str, Any]]:
        """
        Read all five context files and return structured data.

        Returns:
            Dict keyed by file stem (e.g. "profile", "goals") with
            ``metadata`` and ``body`` sub-keys.
        """
        result: dict[str, dict[str, Any]] = {}
        for fname in CONTEXT_FILES:
            key = fname.removesuffix(".md")
            result[key] = self.read(fname)
        return result

    def read(self, filename: str) -> dict[str, Any]:
        """
        Read a single context file.

        Args:
            filename: Basename within the context directory (e.g. "goals.md").

        Returns:
            Dict with ``metadata`` (frontmatter dict) and ``body`` (markdown str).
        """
        path = self._dir / filename
        if not path.exists():
            logger.warning("Context file missing: %s", path)
            return {"metadata": {}, "body": ""}
        post = frontmatter.load(str(path))
        meta = dict(post.metadata)
        # Normalize datetime.date / datetime.datetime to ISO string so callers
        # always receive a consistent type regardless of YAML parsing.
        if "last_updated" in meta and not isinstance(meta["last_updated"], str):
            meta["last_updated"] = str(meta["last_updated"])
        return {"metadata": meta, "body": post.content}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def update(
        self,
        filename: str,
        body: str,
        extra_meta: dict[str, Any] | None = None,
    ) -> None:
        """
        Overwrite the markdown body of a context file.

        Automatically bumps ``last_updated`` in the YAML frontmatter.

        Args:
            filename: Basename of the context file to update.
            body: New markdown body content.
            extra_meta: Additional frontmatter key/value pairs to set.
        """
        path = self._dir / filename
        if path.exists():
            post = frontmatter.load(str(path))
        else:
            post = frontmatter.Post("")

        post.content = body
        post.metadata["last_updated"] = datetime.now().date().isoformat()
        if extra_meta:
            post.metadata.update(extra_meta)

        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        logger.info("Updated context file: %s", filename)

    def update_section(
        self,
        filename: str,
        section_header: str,
        new_content: str,
    ) -> None:
        """
        Replace the content of a named ``## Section`` within a file body.

        If the section is not found it is appended at the end.

        Args:
            filename: Basename of the context file.
            section_header: Full header line to locate (e.g. ``"## Goals"``).
            new_content: Replacement content for the section (not including header).
        """
        data = self.read(filename)
        body: str = data["body"]
        lines = body.split("\n")

        start_idx: int | None = None
        end_idx = len(lines)
        for i, line in enumerate(lines):
            if line.strip() == section_header.strip():
                start_idx = i
            elif start_idx is not None and line.startswith("## ") and i > start_idx:
                end_idx = i
                break

        if start_idx is None:
            new_body = body.rstrip() + f"\n\n{section_header}\n{new_content}\n"
        else:
            new_lines = (
                lines[: start_idx + 1]
                + [new_content]
                + lines[end_idx:]
            )
            new_body = "\n".join(new_lines)

        self.update(filename, new_body)

    # ------------------------------------------------------------------
    # ChromaDB embedding
    # ------------------------------------------------------------------

    def embed_all(self) -> None:
        """
        Embed all context files into ChromaDB for semantic retrieval.

        No-op if chromadb is not installed (R4: degrade gracefully).
        """
        try:
            import chromadb  # type: ignore
        except ImportError:
            logger.debug("chromadb not installed — skipping life_os embedding")
            return

        try:
            client = chromadb.PersistentClient(
                path=str(PROJECT_ROOT / ".stark" / "rag_index")
            )
            collection = client.get_or_create_collection(LIFE_OS_CHROMA_COLLECTION)
            all_data = self.read_all()
            for key, data in all_data.items():
                body = data["body"].strip()
                if not body:
                    continue
                collection.upsert(
                    ids=[key],
                    documents=[body],
                    metadatas=[
                        {
                            "file": f"{key}.md",
                            "last_updated": data["metadata"].get("last_updated", ""),
                        }
                    ],
                )
            logger.info("Embedded %d life_os context files into ChromaDB", len(all_data))
        except Exception:
            logger.exception("ChromaDB embed failed — continuing without embedding")


# ==============================================================================
# Episodic DB helper
# ==============================================================================


def store_episode(
    episode_type: str,
    content: str,
    tags: list[str] | None = None,
    db_path: Path | None = None,
) -> str:
    """
    Write a life_os event to the shared episodic.db.

    Args:
        episode_type: One of LIFE_OS_EPISODE_TYPES (e.g. "morning_briefing").
        content: Full text of the briefing/review/update.
        tags: Optional list of tag strings for filtering.
        db_path: Override the default episodic.db path (for testing).

    Returns:
        The UUID string of the new episode row.
    """
    from memory.episodic_schema import ensure_episodic_schema

    db_path = ensure_episodic_schema(db_path)
    episode_id = str(uuid.uuid4())
    now = datetime.now().timestamp()
    metadata = json.dumps({"episode_type": episode_type, "source": "life_os"})
    tags_str = json.dumps(tags or [])

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO episodes
              (id, content, timestamp, metadata, strength, access_count, last_accessed, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (episode_id, content, now, metadata, 1.0, 0, now, tags_str),
        )
    logger.debug("Stored %s episode: %s", episode_type, episode_id)
    return episode_id


# ==============================================================================
# Singleton
# ==============================================================================

_instance: ContextManager | None = None


def get_context_manager() -> ContextManager:
    """Return the module-level ContextManager singleton."""
    global _instance
    if _instance is None:
        _instance = ContextManager()
    return _instance
