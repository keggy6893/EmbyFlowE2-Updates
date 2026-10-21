from pathlib import Path
import ast
import hashlib
import re

HERE = Path(__file__).resolve().parent
BASE_HASH = '7f88c2a44457d7aed3c7d7ec11bab19c96f550778171e94b14a57a6ba57408ff'


def baseline():
    path = HERE / 'EmbyFlowE2_2026102103.py'
    if not path.exists():
        path = HERE.parents[1] / path.name
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASE_HASH:
        raise RuntimeError('Published receiver baseline mismatch')
    return data.decode('utf-8')


def fix_source(source):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_efa2_restart_4097')
    body = ast.get_source_segment(source, node)
    old = '''        playing_payload = self.emby_report_payload(target_ticks)
        playing_payload["AudioStreamIndex"] = audio_index
        playing_payload["PlayMethod"] = 'DirectStream'
        progress_payload = dict(playing_payload or {})
        progress_payload["EventName"] = "TimeUpdate"
'''
    if body.count(old) != 1:
        raise RuntimeError('Expected private report snapshot not found')
    body = body.replace(old, '', 1)
    start = body.index('        # One Playing + one Progress, asynchronously and guarded.')
    end = body.index('        main_ms = ', start)
    body = body[:start] + '''        # Use the same session registry as periodic Progress reports.
        # A separate POST worker leaves that registry unaware of Playing and
        # causes the first periodic Progress to announce this session again.
        self.item['embyflow_selected_audio_index'] = audio_index
        self._efa2_server_session = new_session_id
        self.send_emby_playback_report('Playing', target_ticks)
        self.send_emby_playback_report('Progress', target_ticks)

''' + body[end:]
    lines = source.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [body + '\n']
    return ''.join(lines)


def build():
    source = fix_source(baseline())
    source = source.replace('PLUGIN_UPDATE_BUILD = 2026102103', 'PLUGIN_UPDATE_BUILD = 2026102104', 1)
    source = source.replace('2026-RCDEV-TEST-20261021-DETAIL-HD-AUDIO-4097', '2026-RCDEV-TEST-20261021-AUDIO-SESSION-4097', 1)
    changelog = 'Tonspur-Test 4097: Start- und Fortschrittsmeldungen verwenden dieselbe Sitzungsverwaltung. Verhindert eine im lokalen Regressionstest nachgewiesene doppelte Startmeldung nach dem Tonwechsel.|Ob dies das dauerhafte Haengen von Bild und Ton nach etwa 30 Sekunden behebt, ist auf Hardware noch zu pruefen.|HD-Detailansicht und LCD-Zeitfix bleiben enthalten. UT-Test weiter offen.'
    source = re.sub(r'^PLUGIN_UPDATE_CHANGELOG = .*$', 'PLUGIN_UPDATE_CHANGELOG = ' + repr(changelog), source, count=1, flags=re.M)
    ast.parse(source, feature_version=(3, 8))
    compile(source, 'receiver_session', 'exec')
    artifact = HERE / 'EmbyFlowE2_2026102104.py'
    artifact.write_bytes(source.encode('utf-8'))
    data = artifact.read_bytes()
    print(artifact.name, hashlib.sha256(data).hexdigest())
    print('git_blob', hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest())


if __name__ == '__main__': build()
