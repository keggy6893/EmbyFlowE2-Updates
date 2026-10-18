"""Build an additive receiver test installer; never change the update manifest."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
engine = (HERE / 'engine.py').read_text()
ui = (HERE / 'ui.py').read_text()
runtime = ('import types as _efcmp_types\n'
           '_efcmp_engine = _efcmp_types.ModuleType("embyflow_compatible_download")\n'
           'exec(compile(%r, "compatible_download_engine.py", "exec"), _efcmp_engine.__dict__)\n' % engine) + ui
script = '''from pathlib import Path
import os, shutil, tempfile, time
'''
script += 'RUNTIME = %r\n' % runtime
script += '''
def patched(source):
    if '# EMBYFLOW_COMPATIBLE_OFFLINE_DOWNLOAD_TEST_V1' in source:
        return source
    for required in ('class EmbyFlowLocalDownloadScreen', 'class EmbyFlowDownloadsScreen',
                     'def _efdl_choice_text(', 'def _efdl_library_save(', 'class DailyQuota:'):
        if required not in source:
            raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source + '\\n\\n' + RUNTIME
    compile(result, 'plugin.py', 'exec')
    return result

def install(path):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text(encoding='utf-8')
    result = patched(source)
    if result == source:
        print('Kompatibler Downloadtest bereits installiert.', flush=True)
        return False
    backup = str(path) + '.vor-kompatibel-download-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    descriptor, temporary = tempfile.mkstemp(prefix='plugin.py.compat-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(result)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(path, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Lokaler kompatibler Downloadtest installiert. Sicherung:', backup, flush=True)
    return True

if __name__ == '__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'):
        print('GUI startet neu. Film > Herunterladen > HDD-kompatibel waehlen.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')
'''
data = script.encode('ascii', 'backslashreplace')
compile(data, 'install-compatible-download-test.py', 'exec')
destination = HERE.parents[1] / 'install-compatible-download-test.py'
destination.write_bytes(data)
print(destination.name, hashlib.sha256(data).hexdigest())
