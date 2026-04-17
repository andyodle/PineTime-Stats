#!/usr/bin/env python3
"""
PineTime Step Tracking Dashboard

A desktop application for tracking steps and heart rate data
from the PineTime smartwatch running InfiniTime firmware.

Usage:
    python main.py

Requirements:
    - PineTime with InfiniTime firmware (v1.7+ recommended)
    - Bluetooth adapter with BLE support
    - Python 3.9+
"""

import sys
import os
import logging
import argparse
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ble.client import PineTimeBLEClient
from db.repository import Database
from ui.main_window import MainWindow
from ui.styles import apply_theme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PineTime Step Tracking Dashboard"
    )
    parser.add_argument(
        "-d", "--database",
        default="pinetime_stats.db",
        help="Path to SQLite database file (default: pinetime_stats.db)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dark",
        action="store_true",
        default=True,
        help="Use dark theme (default: True)"
    )
    parser.add_argument(
        "--light",
        action="store_true",
        help="Use light theme"
    )
    return parser.parse_args()


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    db_path = Path(args.database).absolute()
    logger.info(f"Database path: {db_path}")

    try:
        logger.info("Initializing database...")
        db = Database(str(db_path))
        db.initialize()

        logger.info("Creating BLE client...")
        ble_client = PineTimeBLEClient()

        logger.info("Starting application...")
        app = QApplication(sys.argv)
        app.setApplicationName("PineTime Dashboard")
        app.setOrganizationName("PineTime")

        is_dark = not args.light
        apply_theme(app, is_dark=is_dark)

        window = MainWindow(ble_client, db)
        window.show()

        exit_code = app.exec()

        logger.info("Shutting down...")
        db.close()

        return exit_code

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
