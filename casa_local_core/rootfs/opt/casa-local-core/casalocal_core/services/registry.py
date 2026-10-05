from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from casalocal_core.models.device import DiscoveredDevice, LocalCapability


class DeviceRegistry:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    stable_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS device_preferences (
                    stable_id TEXT PRIMARY KEY,
                    friendly_name TEXT,
                    area TEXT
                )
                """
            )

    def _preferences(self, db: sqlite3.Connection, stable_id: str) -> tuple[str | None, str | None]:
        row = db.execute(
            "SELECT friendly_name, area FROM device_preferences WHERE stable_id = ?",
            (stable_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["friendly_name"], row["area"]

    def upsert_many(self, devices: list[DiscoveredDevice]) -> None:
        now = datetime.now(UTC)
        with self._connect() as db:
            for device in devices:
                row = db.execute(
                    "SELECT first_seen FROM devices WHERE stable_id = ?",
                    (device.stable_id,),
                ).fetchone()
                if row:
                    device.first_seen = datetime.fromisoformat(row["first_seen"])

                friendly_name, area = self._preferences(db, device.stable_id)
                device.friendly_name = friendly_name
                device.area = area
                device.last_seen = now

                payload = json.dumps(device.model_dump(mode="json"), ensure_ascii=False)
                db.execute(
                    """
                    INSERT INTO devices(stable_id, payload, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(stable_id) DO UPDATE SET
                        payload = excluded.payload,
                        last_seen = excluded.last_seen
                    """,
                    (
                        device.stable_id,
                        payload,
                        device.first_seen.isoformat(),
                        device.last_seen.isoformat(),
                    ),
                )

    def _row_to_device(self, db: sqlite3.Connection, row: sqlite3.Row) -> DiscoveredDevice:
        device = DiscoveredDevice.model_validate(json.loads(row["payload"]))
        friendly_name, area = self._preferences(db, device.stable_id)
        device.friendly_name = friendly_name
        device.area = area
        return device

    def all(self) -> list[DiscoveredDevice]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
            return [self._row_to_device(db, row) for row in rows]

    def get(self, stable_id: str) -> DiscoveredDevice | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM devices WHERE stable_id = ?",
                (stable_id,),
            ).fetchone()
            return self._row_to_device(db, row) if row else None

    def update_preferences(
        self,
        stable_id: str,
        friendly_name: str | None,
        area: str | None,
    ) -> DiscoveredDevice | None:
        with self._connect() as db:
            exists = db.execute(
                "SELECT 1 FROM devices WHERE stable_id = ?",
                (stable_id,),
            ).fetchone()
            if not exists:
                return None
            db.execute(
                """
                INSERT INTO device_preferences(stable_id, friendly_name, area)
                VALUES (?, ?, ?)
                ON CONFLICT(stable_id) DO UPDATE SET
                    friendly_name = excluded.friendly_name,
                    area = excluded.area
                """,
                (
                    stable_id,
                    (friendly_name or "").strip() or None,
                    (area or "").strip() or None,
                ),
            )
        return self.get(stable_id)

    def set_capability(
        self,
        stable_id: str,
        capability: LocalCapability,
        metadata_updates: dict | None = None,
    ) -> DiscoveredDevice | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM devices WHERE stable_id = ?",
                (stable_id,),
            ).fetchone()
            if not row:
                return None

            device = self._row_to_device(db, row)
            device.capability = capability
            if metadata_updates:
                device.metadata.update(metadata_updates)
            device.last_seen = datetime.now(UTC)
            payload = json.dumps(device.model_dump(mode="json"), ensure_ascii=False)
            db.execute(
                "UPDATE devices SET payload = ?, last_seen = ? WHERE stable_id = ?",
                (payload, device.last_seen.isoformat(), stable_id),
            )
        return self.get(stable_id)


    def apply_profile(
        self,
        stable_id: str,
        *,
        kind: str,
        metadata_updates: dict,
    ) -> DiscoveredDevice | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM devices WHERE stable_id = ?",
                (stable_id,),
            ).fetchone()
            if not row:
                return None

            device = self._row_to_device(db, row)
            try:
                device.kind = device.kind.__class__(kind)
            except ValueError:
                pass

            device.metadata.update(metadata_updates)
            device.last_seen = datetime.now(UTC)
            payload = json.dumps(device.model_dump(mode="json"), ensure_ascii=False)
            db.execute(
                "UPDATE devices SET payload = ?, last_seen = ? WHERE stable_id = ?",
                (payload, device.last_seen.isoformat(), stable_id),
            )
        return self.get(stable_id)
