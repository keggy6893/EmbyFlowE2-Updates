import importlib.util
from pathlib import Path
import signal
import subprocess
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('theme_probe',ROOT/'test-themes.py')
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_success_reports_last_phase_and_resolver_without_urls(self):
        child=Mock(pid=123,returncode=0)
        child.communicate.return_value=('\n'.join([
            '{"phase":"resolver_ready","resolver":"2026.08.19","node_available":true}',
            '{"phase":"audio_connection"}',
            '{"stream_reachable":true,"status":206,"codec":"mp4a.40.2"}']), 'unused')
        with patch.object(probe.subprocess,'Popen',return_value=child) as create:
            result=probe.run_resolver('https://www.youtube.com/watch?v=example')
        self.assertTrue(result['stream_reachable'])
        self.assertEqual(result['last_phase'],'audio_connection')
        self.assertEqual(result['resolver'],'2026.08.19')
        self.assertTrue(result['node_available'])
        self.assertTrue(create.call_args.kwargs['start_new_session'])

    def test_deadline_kills_process_group_and_preserves_phase(self):
        child=Mock(pid=123,returncode=-9)
        child.communicate.side_effect=[subprocess.TimeoutExpired('resolver',55),
            ('{"phase":"resolver_ready","resolver":"2026.08.19","node_available":true}\n{"phase":"youtube_javascript"}', 'signed URL deliberately not exposed')]
        with patch.object(probe.subprocess,'Popen',return_value=child),patch.object(probe.os,'killpg') as kill:
            result=probe.run_resolver('https://www.youtube.com/watch?v=example')
        kill.assert_called_once_with(123,signal.SIGKILL)
        self.assertEqual(result['reason'],'resolver_deadline')
        self.assertEqual(result['last_phase'],'youtube_javascript')
        self.assertEqual(result['resolver'],'2026.08.19')
        self.assertNotIn('signed',str(result))

    def test_crash_does_not_report_stream_success(self):
        child=Mock(pid=123,returncode=1)
        child.communicate.return_value=('{"stream_reachable":true}', 'crash')
        with patch.object(probe.subprocess,'Popen',return_value=child):
            result=probe.run_resolver('https://www.youtube.com/watch?v=example')
        self.assertFalse(result['stream_reachable'])
        self.assertEqual(result['reason'],'resolver_process_error')

    def test_non_json_child_output_is_not_forwarded(self):
        child=Mock(pid=123,returncode=0)
        child.communicate.return_value=('https://example.invalid/signed?token=secret','raw errors')
        with patch.object(probe.subprocess,'Popen',return_value=child):
            result=probe.run_resolver('https://www.youtube.com/watch?v=example')
        self.assertEqual(result['reason'],'resolver_process_error')
        self.assertNotIn('secret',str(result))
