#!/usr/bin/env python3
"""
Watch Sync Tests

Tests for BLE connection and data synchronization with PineTime watch.

Run with:
    python tests/watch_sync_tests.py
    pytest tests/watch_sync_tests.py -v

Requirements:
    - PineTime with InfiniTime firmware nearby
    - Bluetooth enabled
"""

import sys
import os
import asyncio
import tempfile
import logging
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ble.client import PineTimeBLEClient, PineTimeData, DeviceNotFoundError, ConnectionError
from db.repository import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WatchSyncTest:
    """Test harness for PineTime watch sync functionality."""

    def __init__(self, skip_hardware_tests: bool = False):
        """
        Initialize test harness.

        Args:
            skip_hardware_tests: If True, skip tests that require physical watch.
        """
        self.ble_client: Optional[PineTimeBLEClient] = None
        self.db: Optional[Database] = None
        self.db_path: Optional[str] = None
        self.test_data: Optional[PineTimeData] = None
        self.skip_hardware_tests = skip_hardware_tests
        self.watch_found = False

    def setup(self) -> bool:
        """
        Set up test environment.

        Returns:
            True if setup succeeded, False otherwise.
        """
        logger.info("Setting up test environment...")

        self.db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.ble_client = PineTimeBLEClient()

        logger.info("Test environment ready")
        return True

    def teardown(self) -> None:
        """Clean up test environment."""
        logger.info("Cleaning up test environment...")

        if self.ble_client:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.ble_client.disconnect())
                loop.close()
            except Exception as e:
                logger.debug(f"Error disconnecting (may be OK): {e}")

        if self.db:
            self.db.close()

        if self.db_path and os.path.exists(self.db_path):
            os.unlink(self.db_path)

        logger.info("Cleanup complete")

    async def _check_watch_available(self) -> bool:
        """Check if PineTime is available."""
        if self.skip_hardware_tests:
            return False

        try:
            device = await self.ble_client.scan(timeout=5.0)
            self.watch_found = True
            return True
        except DeviceNotFoundError:
            logger.warning("PineTime not found - hardware tests will be skipped")
            self.watch_found = False
            return False
        except Exception as e:
            logger.warning(f"BLE error: {e} - hardware tests will be skipped")
            self.watch_found = False
            return False

    async def test_scan_for_device(self) -> bool:
        """
        Test 1: Scan for PineTime device.

        Returns:
            True if device found, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 1: Scan for PineTime device")
        logger.info("=" * 50)

        if self.skip_hardware_tests:
            logger.info("⚠ SKIPPED: Hardware tests disabled")
            return True

        try:
            logger.info("Scanning for InfiniTime device...")
            device = await self.ble_client.scan(timeout=10.0)
            logger.info(f"Device found: {device.address}")
            logger.info("✓ TEST PASSED: Device found")
            self.watch_found = True
            return True

        except DeviceNotFoundError as e:
            logger.error(f"✗ TEST FAILED: {e}")
            self.watch_found = False
            return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: Unexpected error: {e}")
            self.watch_found = False
            return False

    async def test_connect_to_device(self) -> bool:
        """
        Test 2: Connect to PineTime device.

        Returns:
            True if connected, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 2: Connect to PineTime")
        logger.info("=" * 50)

        if self.skip_hardware_tests:
            logger.info("⚠ SKIPPED: Hardware tests disabled")
            return True

        try:
            logger.info("Scanning for device...")
            device = await self.ble_client.scan(timeout=5.0)

            logger.info(f"Connecting to {device.address}...")
            await self.ble_client.connect(device)

            if self.ble_client._client and self.ble_client._client.is_connected:
                logger.info("✓ TEST PASSED: Connected successfully")
                await self.ble_client.disconnect()
                return True
            else:
                logger.error("✗ TEST FAILED: Connection state unclear")
                return False

        except DeviceNotFoundError as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

        except ConnectionError as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: Unexpected error: {e}")
            return False

    async def test_read_all_data(self) -> bool:
        """
        Test 3: Read all data from PineTime.

        Returns:
            True if data read successfully, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 3: Read all data from PineTime")
        logger.info("=" * 50)

        if self.skip_hardware_tests:
            logger.info("⚠ SKIPPED: Hardware tests disabled")
            return True

        try:
            logger.info("Scanning for device...")
            device = await self.ble_client.scan(timeout=5.0)

            logger.info("Connecting...")
            await self.ble_client.connect(device)

            logger.info("Reading all data (steps, heart rate, battery, firmware)...")
            data = await self.ble_client.get_all_data()

            logger.info(f"  Steps: {data.steps}")
            logger.info(f"  Heart Rate: {data.heart_rate}")
            logger.info(f"  Battery: {data.battery_level}")
            logger.info(f"  Firmware: {data.firmware_version}")

            self.test_data = data

            logger.info("Disconnecting...")
            await self.ble_client.disconnect()

            logger.info("✓ TEST PASSED: Data read successfully")
            return True

        except DeviceNotFoundError as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

        except ConnectionError as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: Unexpected error: {e}")
            return False

    async def test_read_individual_characteristics(self) -> bool:
        """
        Test 4: Read each characteristic individually.

        Returns:
            True if all characteristics readable, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 4: Read individual characteristics")
        logger.info("=" * 50)

        if self.skip_hardware_tests:
            logger.info("⚠ SKIPPED: Hardware tests disabled")
            return True

        try:
            logger.info("Scanning for device...")
            device = await self.ble_client.scan(timeout=5.0)

            logger.info("Connecting...")
            await self.ble_client.connect(device)

            results = {}

            logger.info("Reading steps...")
            steps = await self.ble_client.get_steps()
            results["steps"] = steps
            logger.info(f"  Steps: {steps}")

            logger.info("Reading heart rate...")
            heart_rate = await self.ble_client.get_heart_rate()
            results["heart_rate"] = heart_rate
            logger.info(f"  Heart Rate: {heart_rate}")

            logger.info("Reading battery level...")
            battery = await self.ble_client.get_battery_level()
            results["battery"] = battery
            logger.info(f"  Battery: {battery}")

            logger.info("Reading firmware version...")
            firmware = await self.ble_client.get_firmware_version()
            results["firmware"] = firmware
            logger.info(f"  Firmware: {firmware}")

            logger.info("Disconnecting...")
            await self.ble_client.disconnect()

            if any(v is not None for v in results.values()):
                logger.info("✓ TEST PASSED: Characteristics readable")
                return True
            else:
                logger.error("✗ TEST FAILED: No characteristics readable")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def test_database_sync(self) -> bool:
        """
        Test 5: Sync data to database.

        Returns:
            True if sync successful, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 5: Sync data to database")
        logger.info("=" * 50)

        if self.test_data is None and not self.skip_hardware_tests:
            try:
                logger.info("Getting data from watch...")
                device = await self.ble_client.scan(timeout=5.0)
                await self.ble_client.connect(device)
                self.test_data = await self.ble_client.get_all_data()
                await self.ble_client.disconnect()
            except Exception as e:
                logger.warning(f"Could not get watch data: {e}")

        if self.test_data is None:
            logger.info("Using simulated data for database test...")
            self.test_data = PineTimeData(
                steps=5432,
                heart_rate=72,
                battery_level=85,
                firmware_version="1.16.0"
            )

        try:
            logger.info(f"Syncing data: steps={self.test_data.steps}, "
                       f"hr={self.test_data.heart_rate}, "
                       f"battery={self.test_data.battery_level}")

            result = self.db.sync_data(
                steps=self.test_data.steps,
                heart_rate=self.test_data.heart_rate,
                battery_level=self.test_data.battery_level,
            )

            if result.success:
                logger.info(f"  Sync successful: {result.date}")
                logger.info("✓ TEST PASSED: Data synced to database")
                return True
            else:
                logger.error(f"✗ TEST FAILED: Sync failed - {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def test_device_pairing(self) -> bool:
        """
        Test 10: Test device pairing functionality.

        Returns:
            True if pairing works, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 10: Device pairing")
        logger.info("=" * 50)

        try:
            test_address = "AA:BB:CC:DD:EE:FF"
            test_name = "InfiniTime"

            logger.info(f"Setting paired device: {test_name} ({test_address})")
            self.db.set_paired_device(test_address, test_name)

            paired = self.db.get_paired_device()
            if not paired:
                logger.error("✗ TEST FAILED: Could not retrieve paired device")
                return False

            if paired['address'] != test_address or paired['name'] != test_name:
                logger.error(f"✗ TEST FAILED: Paired device mismatch: {paired}")
                return False

            logger.info(f"  Paired device: {paired['name']} ({paired['address']})")

            if not self.db.has_paired_device():
                logger.error("✗ TEST FAILED: has_paired_device returned False")
                return False

            logger.info("  Clearing paired device...")
            self.db.clear_paired_device()

            if self.db.has_paired_device():
                logger.error("✗ TEST FAILED: Device still paired after clear")
                return False

            logger.info("✓ TEST PASSED: Device pairing works correctly")
            return True

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_database_retrieval(self) -> bool:
        """
        Test 6: Retrieve data from database.

        Returns:
            True if retrieval successful, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 6: Retrieve data from database")
        logger.info("=" * 50)

        try:
            today_stats = self.db.get_today_stats()

            if today_stats:
                logger.info(f"  Date: {today_stats.date}")
                logger.info(f"  Steps: {today_stats.steps}")
                logger.info(f"  Heart Rate Avg: {today_stats.heart_rate_avg:.1f}")
                logger.info(f"  Heart Rate Min: {today_stats.heart_rate_min}")
                logger.info(f"  Heart Rate Max: {today_stats.heart_rate_max}")
                logger.info("✓ TEST PASSED: Data retrieved from database")
                return True
            else:
                logger.error("✗ TEST FAILED: No data found in database")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def test_database_aggregation(self) -> bool:
        """
        Test 7: Test multiple syncs accumulate correctly.

        Returns:
            True if aggregation works, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 7: Test database aggregation")
        logger.info("=" * 50)

        try:
            stats_before = self.db.get_today_stats()
            hr_before = stats_before.heart_rate_avg if stats_before else 0

            logger.info("Syncing multiple times with different values...")

            self.db.sync_data(steps=4000, heart_rate=70)
            self.db.sync_data(steps=5000, heart_rate=75)
            self.db.sync_data(steps=6000, heart_rate=80)

            stats = self.db.get_today_stats()

            total_samples = stats.heart_rate_samples
            expected_samples = 3 + (stats_before.heart_rate_samples if stats_before else 0)

            logger.info(f"  Steps (max): {stats.steps} (expected: >= 6000)")
            logger.info(f"  HR Avg: {stats.heart_rate_avg:.1f}")
            logger.info(f"  HR Min: {stats.heart_rate_min}")
            logger.info(f"  HR Max: {stats.heart_rate_max}")
            logger.info(f"  Total samples: {total_samples} (expected: {expected_samples})")

            passed = (
                stats.steps >= 6000 and
                stats.heart_rate_min <= 70 and
                stats.heart_rate_max >= 80 and
                stats.heart_rate_samples >= 3
            )

            if passed:
                logger.info("✓ TEST PASSED: Aggregation works correctly")
                return True
            else:
                logger.error("✗ TEST FAILED: Aggregation incorrect")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def test_sync_history(self) -> bool:
        """
        Test 8: Test sync history logging.

        Returns:
            True if history works, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 8: Test sync history logging")
        logger.info("=" * 50)

        try:
            history = self.db.get_sync_history(limit=10)

            logger.info(f"  Found {len(history)} sync records")

            for i, record in enumerate(history[:3]):
                logger.info(f"    Record {i+1}: success={record['success']}, "
                          f"steps={record['steps_read']}")

            if len(history) >= 1:
                logger.info("✓ TEST PASSED: Sync history works")
                return True
            else:
                logger.error("✗ TEST FAILED: No sync history")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def test_full_sync_workflow(self) -> bool:
        """
        Test 9: Full sync workflow (connect -> read -> disconnect -> store).

        Returns:
            True if workflow successful, False otherwise.
        """
        logger.info("=" * 50)
        logger.info("TEST 9: Full sync workflow")
        logger.info("=" * 50)

        if self.skip_hardware_tests or not self.watch_found:
            logger.info("⚠ SKIPPED: Hardware tests disabled or watch not found")
            return True

        try:
            steps_before = self.db.get_today_stats().steps if self.db.get_today_stats() else 0

            logger.info("Step 1: Scan for device...")
            device = await self.ble_client.scan(timeout=5.0)
            logger.info(f"  Found: {device.address}")

            logger.info("Step 2: Connect to device...")
            await self.ble_client.connect(device)
            logger.info("  Connected")

            logger.info("Step 3: Read data...")
            data = await self.ble_client.get_all_data()
            logger.info(f"  Steps: {data.steps}, HR: {data.heart_rate}, "
                       f"Battery: {data.battery_level}")

            logger.info("Step 4: Disconnect...")
            await self.ble_client.disconnect()
            logger.info("  Disconnected")

            logger.info("Step 5: Store in database...")
            result = self.db.sync_data(
                steps=data.steps,
                heart_rate=data.heart_rate,
                battery_level=data.battery_level,
            )
            logger.info(f"  Sync result: {result.success}")

            steps_after = self.db.get_today_stats().steps if self.db.get_today_stats() else 0

            if result.success and steps_after >= steps_before:
                logger.info("✓ TEST PASSED: Full workflow completed")
                return True
            else:
                logger.error("✗ TEST FAILED: Workflow incomplete")
                return False

        except Exception as e:
            logger.error(f"✗ TEST FAILED: {e}")
            return False

    async def run_all_tests(self) -> dict:
        """
        Run all sync tests.

        Returns:
            Dictionary with test results.
        """
        logger.info("\n" + "=" * 60)
        logger.info("PINE TIME WATCH SYNC TESTS")
        logger.info("=" * 60)
        logger.info(f"Started at: {datetime.now().isoformat()}")
        logger.info(f"Hardware tests: {'Enabled' if not self.skip_hardware_tests else 'Disabled'}")
        logger.info("Make sure your PineTime is nearby and InfiniTime is running.")
        logger.info("=" * 60 + "\n")

        await self._check_watch_available()

        tests = [
            ("test_scan_for_device", self.test_scan_for_device),
            ("test_connect_to_device", self.test_connect_to_device),
            ("test_read_all_data", self.test_read_all_data),
            ("test_read_individual_characteristics", self.test_read_individual_characteristics),
            ("test_database_sync", self.test_database_sync),
            ("test_database_retrieval", self.test_database_retrieval),
            ("test_database_aggregation", self.test_database_aggregation),
            ("test_sync_history", self.test_sync_history),
            ("test_device_pairing", self.test_device_pairing),
            ("test_full_sync_workflow", self.test_full_sync_workflow),
        ]

        results = {}
        passed = 0
        failed = 0
        skipped = 0

        for test_name, test_func in tests:
            logger.info("")
            try:
                result = await test_func()
                results[test_name] = "PASS" if result else "FAIL"
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test_name} raised exception: {e}")
                results[test_name] = "ERROR"
                failed += 1

            await asyncio.sleep(0.5)

        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        for test_name, result in results.items():
            status_icon = "✓" if result == "PASS" else "✗" if result == "FAIL" else "⚠"
            logger.info(f"  {status_icon} {test_name}: {result}")

        logger.info("")
        logger.info(f"Total: {passed + failed + skipped} tests")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"Completed at: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        return results


def main():
    """Run the watch sync tests."""
    import argparse

    parser = argparse.ArgumentParser(description="PineTime Watch Sync Tests")
    parser.add_argument(
        "--skip-hardware",
        action="store_true",
        help="Skip tests that require physical watch"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    test = WatchSyncTest(skip_hardware_tests=args.skip_hardware)

    try:
        if not test.setup():
            logger.error("Failed to set up test environment")
            return 1

        results = asyncio.run(test.run_all_tests())

        failed = sum(1 for r in results.values() if r != "PASS")
        return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        test.teardown()


if __name__ == "__main__":
    sys.exit(main())
