import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import engine


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.json'
        self.quota_path = patch.object(engine, 'QUOTA_PATH', str(self.path))
        self.quota_path.start(); self.addCleanup(self.quota_path.stop)
        self.day = patch.object(engine.time, 'strftime', return_value='2026-10-18')
        self.day.start(); self.addCleanup(self.day.stop)

    def consume(self, completed=True):
        quota = engine.DailyQuota()
        quota.reserve()
        quota.close(completed)

    def test_shared_five_persistent_slots_sixth_rejected(self):
        for _ in range(5): self.consume()
        with self.assertRaisesRegex(ValueError, 'Tageslimit erreicht'): self.consume()
        record = json.loads(self.path.read_text())
        self.assertEqual(record['days'], {'2026-10-18': 5})
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_failed_or_cancelled_transfer_refunds_slot(self):
        for _ in range(8): self.consume(False)
        for _ in range(5): self.consume()
        with self.assertRaises(ValueError): self.consume()

    def test_new_calendar_day_has_five_new_slots(self):
        for _ in range(5): self.consume()
        with patch.object(engine.time, 'strftime', return_value='2026-10-19'):
            for _ in range(5): self.consume()
            with self.assertRaises(ValueError): self.consume()
        with self.assertRaises(ValueError): self.consume()

    def test_clock_rollback_does_not_reset_previous_day(self):
        for _ in range(5): self.consume()
        with patch.object(engine.time, 'strftime', return_value='2026-10-19'): self.consume()
        with self.assertRaises(ValueError): self.consume()

    def test_running_reservation_blocks_other_process_lease(self):
        quota = engine.DailyQuota(); quota.reserve()
        try:
            with self.assertRaisesRegex(ValueError, 'bereits'): self.consume()
        finally:
            quota.close(False)
        self.consume()

    def test_cross_midnight_failure_refunds_original_day_only(self):
        quota = engine.DailyQuota(); quota.reserve()
        with patch.object(engine.time, 'strftime', return_value='2026-10-19'):
            quota.close(False)
            self.consume()
        self.assertEqual(json.loads(self.path.read_text())['days'], {'2026-10-18': 0, '2026-10-19': 1})

    def test_invalid_counter_fails_closed(self):
        for value in ('broken', '{"version":1,"days":{"2026-10-18":-1}}',
                      '{"version":1,"days":{"2026-10-18":true}}'):
            self.path.write_text(value)
            with self.assertRaises(ValueError): self.consume()

    def test_unavailable_state_directory_does_not_disable_limit(self):
        with patch.object(engine, 'QUOTA_PATH', str(self.path / 'missing' / 'quota.json')):
            with self.assertRaisesRegex(ValueError, 'sicher geprueft'): self.consume()

    def test_status_shows_zero_two_five_and_new_day_without_writing(self):
        self.assertEqual(engine.quota_status(), {'used': 0, 'remaining': 5, 'limit': 5})
        self.assertFalse(self.path.exists())
        self.consume(); self.consume()
        saved = self.path.read_bytes()
        self.assertEqual(engine.quota_status(), {'used': 2, 'remaining': 3, 'limit': 5})
        self.assertEqual(self.path.read_bytes(), saved)
        for _ in range(3): self.consume()
        self.assertEqual(engine.quota_status()['remaining'], 0)
        with patch.object(engine.time, 'strftime', return_value='2026-10-19'):
            self.assertEqual(engine.quota_status()['used'], 0)

    def test_status_during_transfer_is_nonblocking_and_updates_after_refund(self):
        quota = engine.DailyQuota(); quota.reserve()
        try:
            self.assertEqual(engine.quota_status()['used'], 1)
        finally:
            quota.close(False)
        self.assertEqual(engine.quota_status()['used'], 0)

    def test_bad_status_is_unknown_not_five_available(self):
        self.path.write_text('broken')
        self.assertIsNone(engine.quota_status())
