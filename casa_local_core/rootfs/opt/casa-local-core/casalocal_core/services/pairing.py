from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


class PairingError(RuntimeError):
    pass


class PairingService:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._active_code_hash: str | None = None
        self._expires_at: datetime | None = None
        self._attempts_left = 0
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS api_tokens (
                    token_hash TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT
                )
                """
            )

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def start(self) -> dict[str, str | int]:
        code = f"{secrets.randbelow(100_000_000):08d}"
        self._active_code_hash = self._hash(code)
        self._expires_at = datetime.now(UTC) + timedelta(minutes=5)
        self._attempts_left = 10
        return {
            "code": code,
            "expires_in": 300,
        }

    def complete(self, code: str, label: str = "Home Assistant") -> str:
        now = datetime.now(UTC)
        if not self._active_code_hash or not self._expires_at:
            raise PairingError("No active pairing session.")
        if now > self._expires_at:
            self.cancel()
            raise PairingError("Pairing code expired.")
        if self._attempts_left <= 0:
            self.cancel()
            raise PairingError("Too many failed attempts.")

        self._attempts_left -= 1
        if not secrets.compare_digest(self._hash(code.strip()), self._active_code_hash):
            raise PairingError("Invalid pairing code.")

        token = secrets.token_urlsafe(48)
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO api_tokens(token_hash, label, created_at, last_used_at)
                VALUES (?, ?, ?, NULL)
                """,
                (self._hash(token), label[:80] or "Home Assistant", now.isoformat()),
            )

        self.cancel()
        return token

    def cancel(self) -> None:
        self._active_code_hash = None
        self._expires_at = None
        self._attempts_left = 0

    def validate_token(self, token: str) -> bool:
        token_hash = self._hash(token)
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM api_tokens WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
            if not row:
                return False
            db.execute(
                "UPDATE api_tokens SET last_used_at = ? WHERE token_hash = ?",
                (datetime.now(UTC).isoformat(), token_hash),
            )
        return True
