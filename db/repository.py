"""
Database repository for PineTime step tracking data.

Handles all SQLite operations for storing and retrieving health data.
"""

import sqlite3
import logging
from datetime import datetime, date
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .schema import SCHEMA_SQL

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Daily statistics record."""
    id: int
    date: str
    steps: int
    heart_rate_avg: float
    heart_rate_min: int
    heart_rate_max: int
    heart_rate_samples: int
    synced_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    date: str
    steps: int
    heart_rate: Optional[int]
    battery_level: Optional[int]
    error_message: Optional[str] = None


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class Database:
    """
    SQLite database handler for PineTime data.

    Usage:
        db = Database("pinetime_stats.db")
        db.initialize()

        result = await db.sync_data(steps=5000, heart_rate=72)
        stats = db.get_daily_stats(days=7)
    """

    def __init__(self, db_path: str = "pinetime_stats.db"):
        """
        Initialize database handler.

        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = Path(db_path).expanduser().absolute()
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            self._ensure_tables()
        return self._conn

    def _ensure_tables(self) -> None:
        """Ensure all required tables exist."""
        conn = self._conn
        cursor = conn.cursor()

        for statement in SCHEMA_SQL.split(";"):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except sqlite3.Error as e:
                    logger.warning(f"Schema statement error (may be OK): {e}")

        conn.commit()

    def initialize(self) -> None:
        """Initialize database connection and create tables."""
        try:
            conn = self._get_connection()
            logger.info(f"Database initialized at {self._db_path}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    def _row_to_daily_stats(self, row: sqlite3.Row) -> DailyStats:
        """Convert database row to DailyStats dataclass."""
        return DailyStats(
            id=row["id"],
            date=row["date"],
            steps=row["steps"],
            heart_rate_avg=row["heart_rate_avg"],
            heart_rate_min=row["heart_rate_min"],
            heart_rate_max=row["heart_rate_max"],
            heart_rate_samples=row["heart_rate_samples"] if "heart_rate_samples" in row.keys() else 0,
            synced_at=row["synced_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def sync_data(
        self,
        steps: int,
        heart_rate: Optional[int] = None,
        battery_level: Optional[int] = None,
        sync_date: Optional[str] = None,
    ) -> SyncResult:
        """
        Sync data from PineTime and store/update daily record.

        Args:
            steps: Current step count from PineTime.
            heart_rate: Current heart rate (optional).
            battery_level: Current battery level (optional).
            sync_date: Date for the sync (defaults to today).

        Returns:
            SyncResult with sync status and data.
        """
        if sync_date is None:
            sync_date = date.today().isoformat()

        now = datetime.now().isoformat()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, steps, heart_rate_avg, heart_rate_min,
                       heart_rate_max, heart_rate_samples
                FROM daily_stats
                WHERE date = ?
            """, (sync_date,))

            row = cursor.fetchone()

            if row:
                current_steps = row["steps"]
                current_avg = row["heart_rate_avg"]
                current_min = row["heart_rate_min"]
                current_max = row["heart_rate_max"]
                current_samples = row["heart_rate_samples"]

                new_steps = max(current_steps, steps)

                if heart_rate is not None:
                    if current_samples == 0:
                        new_avg = float(heart_rate)
                        new_min = heart_rate
                        new_max = heart_rate
                        new_samples = 1
                    else:
                        total_hr = current_avg * current_samples + heart_rate
                        new_samples = current_samples + 1
                        new_avg = total_hr / new_samples
                        new_min = min(current_min, heart_rate)
                        new_max = max(current_max, heart_rate)
                else:
                    new_avg = current_avg
                    new_min = current_min
                    new_max = current_max
                    new_samples = current_samples

                cursor.execute("""
                    UPDATE daily_stats
                    SET steps = ?,
                        heart_rate_avg = ?,
                        heart_rate_min = ?,
                        heart_rate_max = ?,
                        heart_rate_samples = ?,
                        synced_at = ?,
                        updated_at = ?
                    WHERE date = ?
                """, (
                    new_steps, new_avg, new_min, new_max,
                    new_samples, now, now, sync_date
                ))
            else:
                new_min = heart_rate if heart_rate is not None else 0
                new_max = heart_rate if heart_rate is not None else 0
                new_avg = float(heart_rate) if heart_rate is not None else 0.0
                new_samples = 1 if heart_rate is not None else 0

                cursor.execute("""
                    INSERT INTO daily_stats
                        (date, steps, heart_rate_avg, heart_rate_min,
                         heart_rate_max, heart_rate_samples, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    sync_date, steps, new_avg, new_min, new_max,
                    new_samples, now
                ))

            cursor.execute("""
                INSERT INTO sync_log
                    (synced_at, success, steps_read, heart_rate_read,
                     battery_level, error_message)
                VALUES (?, 1, ?, ?, ?, NULL)
            """, (now, steps, heart_rate or 0, battery_level or -1))

            conn.commit()

            logger.info(f"Sync successful: date={sync_date}, steps={steps}, "
                       f"hr={heart_rate}, battery={battery_level}")

            return SyncResult(
                success=True,
                date=sync_date,
                steps=steps,
                heart_rate=heart_rate,
                battery_level=battery_level,
            )

        except sqlite3.Error as e:
            error_msg = str(e)
            logger.error(f"Sync failed: {error_msg}")

            try:
                cursor.execute("""
                    INSERT INTO sync_log
                        (synced_at, success, steps_read, heart_rate_read,
                         battery_level, error_message)
                    VALUES (?, 0, ?, ?, ?, ?)
                """, (now, steps, heart_rate or 0, battery_level or -1, error_msg))
                conn.commit()
            except sqlite3.Error:
                pass

            return SyncResult(
                success=False,
                date=sync_date,
                steps=steps,
                heart_rate=heart_rate,
                battery_level=battery_level,
                error_message=error_msg,
            )

    def get_daily_stats(
        self,
        days: int = 7,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[DailyStats]:
        """
        Get daily statistics.

        Args:
            days: Number of past days to retrieve.
            start_date: Start date (YYYY-MM-DD), overrides days.
            end_date: End date (YYYY-MM-DD), defaults to today.

        Returns:
            List of DailyStats records, newest first.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if end_date is None:
                end_date = date.today().isoformat()

            if start_date is None:
                start_date = (
                    datetime.strptime(end_date, "%Y-%m-%d")
                    .replace(hour=0, minute=0, second=0)
                )
                for _ in range(days - 1):
                    start_date = start_date.replace(
                        day=max(1, start_date.day - 1)
                    )
                start_date = start_date.isoformat()[:10]

            cursor.execute("""
                SELECT id, date, steps, heart_rate_avg, heart_rate_min,
                       heart_rate_max, heart_rate_samples, synced_at,
                       created_at, updated_at
                FROM daily_stats
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (start_date, end_date))

            rows = cursor.fetchall()
            return [self._row_to_daily_stats(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Failed to get daily stats: {e}")
            return []

    def get_today_stats(self) -> Optional[DailyStats]:
        """
        Get today's statistics.

        Returns:
            DailyStats for today or None if no data.
        """
        today = date.today().isoformat()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, date, steps, heart_rate_avg, heart_rate_min,
                       heart_rate_max, heart_rate_samples, synced_at,
                       created_at, updated_at
                FROM daily_stats
                WHERE date = ?
            """, (today,))

            row = cursor.fetchone()
            if row:
                return self._row_to_daily_stats(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"Failed to get today stats: {e}")
            return None

    def get_sync_history(self, limit: int = 20) -> List[dict]:
        """
        Get sync history.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of sync log records.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, synced_at, success, steps_read, heart_rate_read,
                       battery_level, error_message, created_at
                FROM sync_log
                ORDER BY synced_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Failed to get sync history: {e}")
            return []

    def get_last_sync(self) -> Optional[dict]:
        """
        Get the most recent sync record.

        Returns:
            Last sync record or None.
        """
        history = self.get_sync_history(limit=1)
        return history[0] if history else None

    def delete_daily_stats(self, date_str: str) -> bool:
        """
        Delete daily stats for a specific date.

        Args:
            date_str: Date to delete (YYYY-MM-DD).

        Returns:
            True if deleted, False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM daily_stats WHERE date = ?",
                (date_str,)
            )
            conn.commit()

            return cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Failed to delete stats: {e}")
            return False

    def get_setting(self, key: str) -> Optional[str]:
        """
        Get a setting value.

        Args:
            key: Setting key.

        Returns:
            Setting value or None if not found.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

        except sqlite3.Error as e:
            logger.error(f"Failed to get setting '{key}': {e}")
            return None

    def set_setting(self, key: str, value: str) -> bool:
        """
        Set a setting value.

        Args:
            key: Setting key.
            value: Setting value.

        Returns:
            True if set successfully, False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()

            logger.debug(f"Setting '{key}' set to '{value}'")
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to set setting '{key}': {e}")
            return False

    def get_paired_device(self) -> Optional[dict]:
        """
        Get paired device info.

        Returns:
            Dict with 'address' and 'name' keys, or None if not paired.
        """
        address = self.get_setting('paired_device_address')
        name = self.get_setting('paired_device_name')

        if address:
            return {'address': address, 'name': name or 'PineTime'}
        return None

    def set_paired_device(self, address: str, name: str) -> bool:
        """
        Set paired device info.

        Args:
            address: Device MAC address.
            name: Device name.

        Returns:
            True if set successfully, False otherwise.
        """
        success = self.set_setting('paired_device_address', address)
        if success:
            success = self.set_setting('paired_device_name', name)
        return success

    def clear_paired_device(self) -> bool:
        """
        Clear paired device info (unpair).

        Returns:
            True if cleared successfully, False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM settings WHERE key IN (?, ?)",
                          ('paired_device_address', 'paired_device_name'))
            conn.commit()

            logger.info("Paired device cleared")
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to clear paired device: {e}")
            return False

    def has_paired_device(self) -> bool:
        """
        Check if a device is paired.

        Returns:
            True if paired, False otherwise.
        """
        return self.get_setting('paired_device_address') is not None

    def __enter__(self) -> "Database":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
