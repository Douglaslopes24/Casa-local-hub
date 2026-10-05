from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet


class LocalVault:
    def __init__(self, database_path: Path, master_key_path: Path) -> None:
        self.database_path = database_path
        self.master_key_path = master_key_path
        self.master_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())
        self._init_db()

    def _load_or_create_key(self) -> bytes:
        if self.master_key_path.exists():
            return self.master_key_path.read_bytes().strip()

        key = Fernet.generate_key()
        self.master_key_path.write_bytes(key)
        try:
            os.chmod(self.master_key_path, 0o600)
        except OSError:
            pass
        return key

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS secrets (
                    stable_id TEXT NOT NULL,
                    secret_name TEXT NOT NULL,
                    ciphertext BLOB NOT NULL,
                    PRIMARY KEY (stable_id, secret_name)
                )
                """
            )

    def set_secret(self, stable_id: str, secret_name: str, value: str) -> None:
        ciphertext = self._fernet.encrypt(value.encode("utf-8"))
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO secrets(stable_id, secret_name, ciphertext)
                VALUES (?, ?, ?)
                ON CONFLICT(stable_id, secret_name) DO UPDATE SET
                    ciphertext = excluded.ciphertext
                """,
                (stable_id, secret_name, ciphertext),
            )

    def get_secret(self, stable_id: str, secret_name: str) -> str | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT ciphertext FROM secrets WHERE stable_id = ? AND secret_name = ?",
                (stable_id, secret_name),
            ).fetchone()
        if not row:
            return None
        return self._fernet.decrypt(row[0]).decode("utf-8")

    def has_secret(self, stable_id: str, secret_name: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM secrets WHERE stable_id = ? AND secret_name = ?",
                (stable_id, secret_name),
            ).fetchone()
        return bool(row)
