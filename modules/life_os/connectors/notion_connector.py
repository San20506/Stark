"""
Notion Connector
================
Reads tasks and writes weekly summaries via the Notion REST API.

Required env vars:
  NOTION_TOKEN          Internal Integration Token
  NOTION_TASKS_DB_ID    Database ID for your task tracker
  NOTION_WEEKLY_DB_ID   Database ID for weekly review pages

All methods return empty results gracefully when NOTION_TOKEN is unset.
"""
import logging
import os
from datetime import date, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_NOTION_API_BASE: str = "https://api.notion.com/v1"
_NOTION_VERSION: str = "2022-06-28"
_REQUEST_TIMEOUT: int = 15


class NotionConnector:
    """Thin wrapper around the Notion REST API for life_os use cases."""

    def __init__(self) -> None:
        token = os.environ.get("NOTION_TOKEN", "")
        if not token:
            logger.warning("NOTION_TOKEN not set — Notion connector disabled")
        self._token = token
        self._tasks_db = os.environ.get("NOTION_TASKS_DB_ID", "")
        self._weekly_db = os.environ.get("NOTION_WEEKLY_DB_ID", "")
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_due_tasks(self, days_ahead: int = 1) -> list[dict[str, Any]]:
        """
        Return tasks that are overdue or due within the next ``days_ahead`` days.

        Args:
            days_ahead: How many days ahead to look for due dates.

        Returns:
            List of task dicts with keys: id, title, due, status.
        """
        if not self._token or not self._tasks_db:
            return []

        cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
        payload: dict[str, Any] = {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Due", "date": {"on_or_before": cutoff}},
                ]
            }
        }
        try:
            resp = requests.post(
                f"{_NOTION_API_BASE}/databases/{self._tasks_db}/query",
                headers=self._headers,
                json=payload,
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return [self._parse_task(page) for page in resp.json().get("results", [])]
        except requests.RequestException as exc:
            logger.error("Notion get_due_tasks failed: %s", exc)
            return []

    def create_weekly_page(self, title: str, content_md: str) -> str:
        """
        Create a new page in the weekly reviews database.

        Args:
            title: Page title string.
            content_md: Markdown body to convert to Notion blocks.

        Returns:
            New page ID string, or empty string on failure.
        """
        if not self._token or not self._weekly_db:
            logger.warning("Notion weekly DB not configured — skipping push")
            return ""

        payload: dict[str, Any] = {
            "parent": {"database_id": self._weekly_db},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
            },
            "children": self._md_to_blocks(content_md),
        }
        try:
            resp = requests.post(
                f"{_NOTION_API_BASE}/pages",
                headers=self._headers,
                json=payload,
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            page_id: str = resp.json()["id"]
            logger.info("Created Notion weekly page: %s", page_id)
            return page_id
        except requests.RequestException as exc:
            logger.error("Notion create_weekly_page failed: %s", exc)
            return ""

    def update_task_status(self, task_id: str, status: str) -> None:
        """
        Update the Status property of a Notion task page.

        Args:
            task_id: Notion page ID of the task.
            status: New status name (must match a valid Notion status option).
        """
        if not self._token:
            return

        payload: dict[str, Any] = {
            "properties": {"Status": {"status": {"name": status}}}
        }
        try:
            resp = requests.patch(
                f"{_NOTION_API_BASE}/pages/{task_id}",
                headers=self._headers,
                json=payload,
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Notion update_task_status failed: %s", exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_task(page: dict[str, Any]) -> dict[str, Any]:
        props = page.get("properties", {})
        title_parts = props.get("Name", {}).get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts)
        due_raw = (props.get("Due") or {}).get("date") or {}
        status_raw = (props.get("Status") or {}).get("status") or {}
        return {
            "id": page.get("id", ""),
            "title": title,
            "due": due_raw.get("start", ""),
            "status": status_raw.get("name", ""),
        }

    @staticmethod
    def _md_to_blocks(md: str) -> list[dict[str, Any]]:
        """Convert simple markdown lines to Notion block objects."""
        blocks: list[dict[str, Any]] = []
        for line in md.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": stripped[3:]}}]
                    },
                })
            elif stripped.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": stripped[4:]}}]
                    },
                })
            elif stripped.startswith(("- ", "* ")):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]
                    },
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": stripped}}]
                    },
                })
        return blocks
