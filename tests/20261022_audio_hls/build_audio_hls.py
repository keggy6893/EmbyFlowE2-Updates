import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = 2026102201
VERSION = '2026-RCDEV-TEST-20261022-AUDIO-HLS'
CHANGES = [
    'Tonspur-Test fuer Dreambox One und Gigablue Quad Pro: Nach Sprachwechsel HLS/TS mit AAC-Stereo statt MKV mit unveraendertem Originalton. Player bleibt Enigma2/4097; Video-Streamkopie wird angefordert.',
    'Gewaehlte Sprache, Filmposition und Wiedergabesitzung bleiben zugeordnet. Die Tonspurliste behaelt die Sprachen der Originaldatei.',
    'Gezielter Versuch gegen Bild-/Tonausfall nach etwa 30 Sekunden. Kein bestaetigter Hardwarefix. Fuer diesen Test ist serverseitige Audio-Umwandlung erforderlich; Mehrkanalton wird auf Stereo reduziert.',
    'Lokale USB-/NAS-Dateipfade und andere Receiver behalten den bisherigen Wiedergabeweg. Genre-Abstand, HD-Layout und LCD-Zeitkorrektur aus 2026102105 bleiben enthalten.',
]

HELPER = '''
# EMBYFLOW_RECEIVER_AUDIO_HLS_V1
def _efa3_audio_compat_codec(player):
    """Narrow receiver trial; never send a local file through the server."""
    info = getattr(player, 'playback_info', None) or {}
    item = getattr(player, 'item', None) or {}
    if info.get('local_file') or str(item.get('Id') or item.get('id') or '').startswith('local:'):
        return ''
    if not str(getattr(player, 'stream_url', '') or '').lower().startswith(('http://', 'https://')):
        return ''
    machine = ''
    try:
        from Components.SystemInfo import BoxInfo
        machine = str(BoxInfo.getItem('machinebuild') or BoxInfo.getItem('model') or '').lower()
    except Exception:
        pass
    if not machine:
        try:
            from boxbranding import getMachineBuild
            machine = str(getMachineBuild() or '').lower()
        except Exception:
            pass
    if machine not in ('dreamone', 'dmone', 'gbquad4kpro'):
        return ''
    try:
        videos = player.embyflow_media_streams_by_type('Video') or []
        codec = str(videos[0].get('Codec') or '').lower() if videos else ''
        return {'h264': 'h264', 'avc': 'h264', 'hevc': 'hevc', 'h265': 'hevc'}.get(codec, '')
    except Exception:
        return ''


'''


def replace_once(source, old, new):
    if source.count(old) != 1:
        # The legacy subtitle restart has the same URL fragment. Only change
        # the dedicated audio restart, which is defined near the module end.
        start = source.index('def _efa2_restart_4097(')
        if source[start:].count(old) == 1:
            return source[:start] + source[start:].replace(old, new, 1)
        raise ValueError('Unexpected source at: ' + old[:80])
    return source.replace(old, new, 1)


def build(source):
    source = replace_once(source, 'def _efa2_restart_4097(', HELPER + 'def _efa2_restart_4097(')
    source = replace_once(source, '''        if active_subtitle is None:
            params.extend([
                ("VideoCodec", "copy"),
                ("AudioCodec", "copy"),
            ])
            endpoint = "stream.mkv"
''', '''        compat_codec = _efa3_audio_compat_codec(self) if active_subtitle is None else ''
        if compat_codec:
            params.extend([
                ("VideoCodec", compat_codec),
                ("AudioCodec", "aac"),
                ("AudioBitRate", "192000"),
                ("AudioSampleRate", "48000"),
                ("AudioChannels", "2"),
                ("MaxAudioChannels", "2"),
                ("AllowVideoStreamCopy", "true"),
                ("AllowAudioStreamCopy", "false"),
                ("EnableAutoStreamCopy", "true"),
                ("Container", "ts"),
                ("SegmentContainer", "ts"),
                ("MinSegments", "1"),
                ("BreakOnNonKeyFrames", "false"),
                ("CopyTimestamps", "false"),
            ])
            endpoint = "master.m3u8"
        elif active_subtitle is None:
            params.extend([
                ("VideoCodec", "copy"),
                ("AudioCodec", "copy"),
            ])
            endpoint = "stream.mkv"
''')
    source = replace_once(source, '''        self.embyflow_playback_mode = 'directstream'
        self.playback_info.update(url=new_url, play_session_id=new_session_id,
                                  playback_mode='directstream', service_type=4097)
''', '''        self._efa3_audio_compat_session = new_session_id if compat_codec else None
        self.embyflow_playback_mode = 'audio-compat-transcoding' if compat_codec else 'directstream'
        self.playback_info.update(url=new_url, play_session_id=new_session_id,
                                  playback_mode=self.embyflow_playback_mode, service_type=4097,
                                  audio_compat_hls=bool(compat_codec))
''')
    source = replace_once(source, """        payload['PlayMethod'] = 'DirectStream'
        payload['AudioStreamIndex'] = player.item.get('embyflow_selected_audio_index')
""", """        payload['PlayMethod'] = ('Transcode' if getattr(player, '_efa3_audio_compat_session', None)
                                 == player.play_session_id else 'DirectStream')
        payload['AudioStreamIndex'] = player.item.get('embyflow_selected_audio_index')
""")
    source = replace_once(source, """        player.embyflow_active_audio_override = dict(matches[0])
""", """        player.embyflow_active_audio_override = dict(matches[0])
        if getattr(player, '_efa3_audio_compat_session', None) == player.play_session_id:
            player.embyflow_active_audio_override.update(Codec='aac', Channels=2)
""")
    source = replace_once(source, """        player['state_label'].setText('Tonspur wird serverseitig gestartet: %s' % payload.get('label', 'Tonspur'))
""", """        detail = ('AAC-Stereo / HLS' if player.playback_info.get('audio_compat_hls') else 'Server')
        player['state_label'].setText('Tonspur wird gestartet (%s): %s' % (detail, payload.get('label', 'Tonspur')))
""")
    for old, new in [
        ('PLUGIN_VERSION = "2026-RCDEV-TEST-20261021-GENRE-SPACING"', 'PLUGIN_VERSION = ' + repr(VERSION)),
        ('PLUGIN_BUILD_DATE = "21.10.2026"', 'PLUGIN_BUILD_DATE = "22.10.2026"'),
        ('PLUGIN_UPDATE_BUILD = 2026102105', 'PLUGIN_UPDATE_BUILD = ' + str(BUILD)),
    ]:
        source = replace_once(source, old, new)
    tree = ast.parse(source)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'PLUGIN_UPDATE_CHANGELOG' for t in n.targets))
    lines = source.splitlines(keepends=True)
    lines[assignment.lineno - 1:assignment.end_lineno] = [
        'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGES)) + '\n']
    source = ''.join(lines)
    ast.parse(source, feature_version=(3, 8))
    compile(source, 'plugin.py', 'exec')
    return source


if __name__ == '__main__':
    baseline = next(p for p in (ROOT / 'EmbyFlowE2_2026102105.py',
                               ROOT.parent.parent / 'EmbyFlowE2_2026102105.py') if p.is_file())
    source = baseline.read_text(encoding='utf-8')
    target = ROOT / ('EmbyFlowE2_%d.py' % BUILD)
    target.write_text(build(source), encoding='utf-8', newline='\n')
    print(json.dumps(dict(file=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
