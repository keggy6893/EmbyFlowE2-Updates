from pathlib import Path
import hashlib
import re
import tarfile
import tempfile

SRC = Path('plugin_RCDEV13_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py')
EXPECTED_PLUGIN_SHA = 'af7d1f09d071f4bf3f48a2476ece04ec6dd7ca3a3f4553cd9dbb4c3fc8d0dbe5'
OUT = Path('enigma2-plugin-extensions-embyflowe2_2026.09.13.rcdev13-navv30-discoverfix1-navread1-arrowvis2-publicclean1_all.ipk')

PLUGIN_REL = Path('usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
INIT_REL = Path('usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/__init__.py')
KEYMAP_REL = Path('usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/keymap.xml')
EXPECTED_PAYLOAD = sorted(map(str, (PLUGIN_REL, INIT_REL, KEYMAP_REL)))

KEYMAP = '''<keymap>\n    <map context="EmbyFlowE2Actions">\n        <key id="KEY_RED" mapto="red" flags="m" />\n        <key id="KEY_GREEN" mapto="green" flags="m" />\n        <key id="KEY_YELLOW" mapto="yellow" flags="m" />\n        <key id="KEY_BLUE" mapto="blue" flags="m" />\n        <key id="KEY_BACK" mapto="cancel" flags="m" />\n        <key id="KEY_EXIT" mapto="cancel" flags="m" />\n    </map>\n</keymap>\n'''

CONTROL = '''Package: enigma2-plugin-extensions-embyflowe2\nVersion: 2026.09.13.rcdev13-navv30-discoverfix1-navread1-arrowvis2-publicclean1\nDescription: EmbyFlowE2 for Enigma2 (RCDEV13 NAVV30 DISCOVERFIX1 NAVREAD1 ARROWVIS2 PUBLICCLEAN1)\nArchitecture: all\nSection: extra\nPriority: optional\nMaintainer: EmbyFlowE2\n'''


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def add_tree_to_targz(root: Path, output: Path):
    with tarfile.open(output, 'w:gz', format=tarfile.GNU_FORMAT) as tf:
        for p in sorted(root.rglob('*')):
            arc = str(p.relative_to(root))
            info = tf.gettarinfo(str(p), arcname=arc)
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            if p.is_file():
                with p.open('rb') as fh:
                    tf.addfile(info, fh)
            else:
                tf.addfile(info)


def write_ar(path: Path, members):
    with path.open('wb') as fh:
        fh.write(b'!<arch>\n')
        for name, data in members:
            ar_name = (name + '/').encode('ascii')
            if len(ar_name) > 16:
                raise SystemExit('AR member name too long: ' + name)
            header = (
                ar_name.ljust(16, b' ') +
                b'0'.ljust(12, b' ') +
                b'0'.ljust(6, b' ') +
                b'0'.ljust(6, b' ') +
                b'100644'.ljust(8, b' ') +
                str(len(data)).encode('ascii').ljust(10, b' ') +
                b'`\n'
            )
            if len(header) != 60:
                raise SystemExit('Invalid AR header length')
            fh.write(header)
            fh.write(data)
            if len(data) % 2:
                fh.write(b'\n')


def read_ar_members(path: Path):
    data = path.read_bytes()
    if not data.startswith(b'!<arch>\n'):
        raise SystemExit('Invalid IPK/ar magic')
    pos = 8
    names = []
    while pos < len(data):
        header = data[pos:pos+60]
        if len(header) != 60 or header[58:60] != b'`\n':
            raise SystemExit('Invalid AR member header')
        name = header[:16].decode('ascii').strip().rstrip('/')
        size = int(header[48:58].decode('ascii').strip())
        names.append(name)
        pos += 60 + size + (size % 2)
    return names


if not SRC.is_file():
    raise SystemExit('Public 1304 plugin missing')
plugin = SRC.read_bytes()
if sha256_bytes(plugin) != EXPECTED_PLUGIN_SHA:
    raise SystemExit('Public 1304 plugin SHA256 mismatch')
text = plugin.decode('utf-8')
compile(text, str(SRC), 'exec')

for required in (
    'PLUGIN_UPDATE_BUILD = 2026091304',
    '2026-RCDEV13-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-NAVREAD1-ARROWVIS2-PUBLICCLEAN1',
    '# EMBYFLOW_HOME_DISCOVERFIX1_START',
    '# EMBYFLOW_NAV_GROUPS_V30_START',
):
    if required not in text:
        raise SystemExit('Required public marker missing: ' + required)

for forbidden in ('UTFIX16', 'UTFIX20', 'PGS_HLS_RETRY_PROXY', 'TRANSCODE_RECOVERY'):
    if forbidden in text:
        raise SystemExit('Experimental marker present: ' + forbidden)

# Privacy gate: no saved/private LAN addresses may be embedded. The public UI
# intentionally contains one generic documentation/example address three times.
# Permit only that one repeated example and only inside nearby help/example text.
private_ip = re.compile(r'(?<!\d)(?:192\.168\.|10\.\d{1,3}\.|172\.(?:1[6-9]|2\d|3[01])\.)(?:\d{1,3}\.)?\d{1,3}(?!\d)')
hits = list(private_ip.finditer(text))
if hits:
    values = {m.group(0) for m in hits}
    if len(hits) != 3 or len(values) != 1:
        raise SystemExit('Unexpected embedded private IPv4 address set; refusing package')
    help_words = ('Beispiel', 'IP-Adresse', 'diskstation.local', 'Serveradresse', 'Adresse')
    for m in hits:
        context = text[max(0, m.start()-700): min(len(text), m.end()+700)]
        if not any(word in context for word in help_words):
            raise SystemExit('Private IPv4 outside documented example/help context; refusing package')
    print('PRIVACY_CHECK_OK generic_help_example_count=3')

with tempfile.TemporaryDirectory(prefix='embyflowe2-ipk-') as td:
    td = Path(td)
    root = td / 'root'
    control_dir = td / 'control'
    for rel in (PLUGIN_REL, INIT_REL, KEYMAP_REL):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
    control_dir.mkdir(parents=True, exist_ok=True)

    (root / PLUGIN_REL).write_bytes(plugin)
    (root / INIT_REL).write_bytes(b'')
    (root / KEYMAP_REL).write_text(KEYMAP, encoding='utf-8')
    (control_dir / 'control').write_text(CONTROL, encoding='utf-8')

    payload = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
    if payload != EXPECTED_PAYLOAD:
        raise SystemExit('Unexpected IPK payload: ' + repr(payload))
    if any('/etc/enigma2/' in '/' + p or '/tmp/' in '/' + p or p.endswith('.log') for p in payload):
        raise SystemExit('Runtime state/log path found in payload')
    if sha256_bytes((root / PLUGIN_REL).read_bytes()) != EXPECTED_PLUGIN_SHA:
        raise SystemExit('plugin.py changed while packaging')

    control_tgz = td / 'control.tar.gz'
    data_tgz = td / 'data.tar.gz'
    add_tree_to_targz(control_dir, control_tgz)
    add_tree_to_targz(root, data_tgz)

    write_ar(OUT, [
        ('debian-binary', b'2.0\n'),
        ('control.tar.gz', control_tgz.read_bytes()),
        ('data.tar.gz', data_tgz.read_bytes()),
    ])

if read_ar_members(OUT) != ['debian-binary', 'control.tar.gz', 'data.tar.gz']:
    raise SystemExit('Unexpected IPK ar members')

ipk_sha = sha256_bytes(OUT.read_bytes())
Path(str(OUT) + '.sha256').write_text(f'{ipk_sha}  {OUT.name}\n', encoding='ascii')
print('CLEAN_IPK_OK')
print('plugin_sha256=' + EXPECTED_PLUGIN_SHA)
print('ipk_sha256=' + ipk_sha)
print('payload=' + ','.join(EXPECTED_PAYLOAD))
print('output=' + OUT.name)
