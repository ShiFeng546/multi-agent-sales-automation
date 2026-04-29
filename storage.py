from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "automation.db"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                campaign_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )


def save_run(run_id: str, campaign_name: str, created_at: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO runs (id, campaign_name, created_at, payload_json, result_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, campaign_name, created_at, json.dumps(payload, ensure_ascii=False), json.dumps(result, ensure_ascii=False)),
        )


def list_runs(limit: int = 10) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, campaign_name, created_at, result_json
            FROM runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        result = json.loads(row["result_json"])
        summary = result.get("summary", {})
        items.append(
            {
                "id": row["id"],
                "campaign_name": row["campaign_name"],
                "created_at": row["created_at"],
                "qualified_leads": summary.get("qualified_leads", 0),
                "top_segment": summary.get("top_segment", "暂无"),
            }
        )
    return items


def get_run(run_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, campaign_name, created_at, payload_json, result_json
            FROM runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "campaign_name": row["campaign_name"],
        "created_at": row["created_at"],
        "payload": json.loads(row["payload_json"]),
        "result": json.loads(row["result_json"]),
    }
