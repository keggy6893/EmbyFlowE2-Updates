import ast, hashlib, json, pathlib, sys
BASE_SHA = '0ea10a000c9ff5427fda1bfe1fc4107d29f252947b87e380fb9b321502309064'
OUTPUT = 'EmbyFlowE2_ThemeStream_20261001_0101.py'
def build(data):
    if hashlib.sha256(data).hexdigest() != BASE_SHA:
        raise ValueError('Unexpected base payload')
    text = data.decode('utf-8')
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1: raise ValueError('Nonunique patch anchor: ' + old[:100])
        text = text.replace(old, new, 1)
    replace('PLUGIN_VERSION = "2026-RCDEV-THEMEVOLUME-20260930"', 'PLUGIN_VERSION = "2026-RCDEV-THEMESTREAM-20261001"')
    replace('PLUGIN_UPDATE_BUILD = 2026093003', 'PLUGIN_UPDATE_BUILD = 2026100101')
    old = '''            stream_url = "%s/Audio/%s/stream%s?Static=true&api_key=%s" % (
                server.rstrip("/"), theme_id, extension, token,
            )'''
    new = '''            from urllib.parse import urlencode
            stream_url = "%s/Videos/%s/stream?%s" % (
                server.rstrip("/"), theme_id,
                urlencode({"userId": user_id, "api_key": token, "static": "True",
                           "DeviceId": "embyflowe2-theme"}),
            )'''
    replace(old, new)
    replace('''            "PLAY item=%s theme=%s container=%s"
            % (selected_id, theme_id, container or "unknown")''', '''            "PLAY item=%s theme=%s container=%s service=%s route=%s volume_limit=%s"
            % (selected_id, theme_id, container or "unknown", STREAM_SERVICE_TYPE,
               "Videos/static" if theme_id else "Themerr",
               config.embyflow.theme_volume.value)''')
    # No URL is logged: authentication parameters must remain private.
    ast.parse(text)
    return text.encode('utf-8')
if __name__ == '__main__':
    source, output = map(pathlib.Path, sys.argv[1:])
    data = build(source.read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    (output / OUTPUT).write_bytes(data)
    manifest = dict(version='2026-RCDEV-THEMESTREAM-20261001', build=2026100101,
        channel='rcdev', target='plugin.py', artifact_type='plugin_py',
        download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/' + OUTPUT,
        sha256=hashlib.sha256(data).hexdigest(),
        changelog=['TEST: Hintergrundmusik über Videos/static wie im Murxer-Vergleichslog',
                   'Theme-Log ergänzt um Service, Streamroute und Lautstärkegrenze',
                   'Lautstärkeobergrenze und 10 FTP-Accounts weiterhin enthalten'])
    (output / 'update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(manifest['sha256'])
