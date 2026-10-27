from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class DraftStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS approvals (
                nonce TEXT PRIMARY KEY, session_id TEXT NOT NULL, student_id TEXT NOT NULL,
                digest TEXT NOT NULL, expires REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, student_id TEXT NOT NULL, opportunity_id TEXT NOT NULL,
                payload TEXT NOT NULL, created_at REAL NOT NULL,
                UNIQUE(student_id, opportunity_id)
            );
        """)

    def close(self):
        self.connection.close()

    def count(self, student_id: str | None = None) -> int:
        if student_id is None:
            return self.connection.execute("SELECT count(*) FROM drafts").fetchone()[0]
        return self.connection.execute("SELECT count(*) FROM drafts WHERE student_id=?", (student_id,)).fetchone()[0]

    def existing(self, student_id: str, opportunity_id: str) -> dict | None:
        row = self.connection.execute("SELECT id,payload FROM drafts WHERE student_id=? AND opportunity_id=?",
                                      (student_id, opportunity_id)).fetchone()
        return {"draft_id": row["id"], **json.loads(row["payload"])} if row else None

    def issue_approval(self, session_id: str, student_id: str, payload: dict, ttl: float = 300) -> str:
        """Host-only API. Never registered as an LLM or MCP tool."""
        nonce = secrets.token_urlsafe(32)
        with self.connection:
            self.connection.execute("INSERT INTO approvals VALUES (?,?,?,?,?,0)",
                                    (nonce, session_id, student_id, fingerprint(payload), time.time() + ttl))
        return nonce

    def commit(self, nonce: str, session_id: str, student_id: str, payload: dict) -> dict:
        """One-use, content-bound approval plus insert are one SQLite transaction."""
        if payload.get("student_id") != student_id or payload.get("status") != "Draft":
            raise PermissionError("Invalid draft owner or status")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT * FROM approvals WHERE nonce=?", (nonce,)).fetchone()
            if not row or row["consumed"] or row["expires"] < time.time() or row["session_id"] != session_id or row["student_id"] != student_id or row["digest"] != fingerprint(payload):
                raise PermissionError("Missing, expired, replayed or mismatched human approval")
            self.connection.execute("UPDATE approvals SET consumed=1 WHERE nonce=?", (nonce,))
            prior = self.existing(student_id, payload["opportunity_id"])
            if prior:
                return {**prior, "status": "existing"}
            draft_id = "DRAFT-" + secrets.token_hex(5).upper()
            self.connection.execute("INSERT INTO drafts VALUES (?,?,?,?,?)",
                                    (draft_id, student_id, payload["opportunity_id"], json.dumps(payload, ensure_ascii=False), time.time()))
        return {**payload, "draft_id": draft_id, "status": "Draft"}
