from pathlib import Path
import ast
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = (HERE / 'runtime.py').read_text()
ARTIFACT = 'EmbyFlowE2_2026101901.py'
MARKER = 'EMBYFLOW_SEARCH_LEFT_GRID_V1'

INSTALLER = '''from pathlib import Path
import ast
import os
import shutil
import tempfile
import time

RUNTIME = %r
MARKER = %r


def patched(source):
    tree = ast.parse(source)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'EmbyFlowDisneySearchScreen']
    if len(classes) != 1:
        raise RuntimeError('Suchansicht nicht eindeutig gefunden. Nichts geaendert.')
    node = classes[0]
    lines = source.splitlines(True)
    current = ''.join(lines[node.lineno-1:node.end_lineno])
    if 'KEY_COLUMNS = 6' in current and 'def _set_keyboard(' in current:
        return source
    for name in ('_request_search', '_search_quality_label', '_load_history'):
        if not any(isinstance(item, ast.FunctionDef) and item.name == name for item in node.body):
            raise RuntimeError('Suchansicht weicht ab. Nichts geaendert.')
    result = ''.join(lines[:node.lineno-1]) + RUNTIME + '\\n' + ''.join(lines[node.end_lineno:])
    compile(result, 'plugin.py', 'exec')
    return result


def install(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('Pluginpfad nicht gefunden oder unerwartet.')
    source = path.read_text(encoding='utf-8')
    result = patched(source)
    if result == source:
        print('Neue Suchansicht bereits installiert.', flush=True)
        return False
    backup = str(path) + '.vor-suche-links-' + time.strftime('%%Y%%m%%d-%%H%%M%%S') + '-' + str(os.getpid())
    with open(backup, 'x', encoding='utf-8') as output:
        output.write(source); output.flush(); os.fsync(output.fileno())
    shutil.copystat(path, backup)
    descriptor, temporary = tempfile.mkstemp(prefix='plugin.py.suche-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(result); output.flush(); os.fsync(output.fileno())
        shutil.copystat(path, temporary)
        if path.read_text(encoding='utf-8') != source:
            raise RuntimeError('Plugin wurde inzwischen geaendert. Bitte erneut versuchen.')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Marineblaue Suche installiert. Sicherung: ' + backup, flush=True)
    return True


if __name__ == '__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'):
        print('GUI startet neu. Danach EmbyFlow > Suche oeffnen.', flush=True)
        os.system('init 4'); time.sleep(3); os.system('init 3')
''' % (RUNTIME, MARKER)


def main():
    namespace = {'__name__': 'builder'}
    exec(INSTALLER, namespace)
    original = (ROOT / 'EmbyFlowE2_2026101805.py').read_text()
    payload = namespace['patched'](original)
    (ROOT / ARTIFACT).write_text(payload)
    helper = ROOT / 'install-search-left-test.py'
    helper.write_bytes(INSTALLER.encode('ascii', 'backslashreplace'))
    print(helper.name, hashlib.sha256(helper.read_bytes()).hexdigest())
    print(ARTIFACT, hashlib.sha256(payload.encode()).hexdigest())


if __name__ == '__main__':
    main()
