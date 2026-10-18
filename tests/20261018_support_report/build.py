from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
RUNTIME = (HERE / 'report.py').read_text() + '\n' + (HERE / 'ui.py').read_text()
MARKER = '# EMBYFLOW_SUPPORT_REPORT_V1'


def patched(source):
    if MARKER in source:
        return source
    for required in ('class EmbyFlowAdvancedSettingsNeon', 'def sx(', 'def sy(', 'def sf('):
        if required not in source:
            raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    source += '\n\n' + RUNTIME
    compile(source, 'plugin.py', 'exec')
    return source


def build():
    installer = '''from pathlib import Path
import os, shutil, tempfile, time
'''
    installer += 'RUNTIME = %r\nMARKER = %r\n' % (RUNTIME, MARKER)
    import inspect
    installer += '\n' + inspect.getsource(patched)
    installer += '''
def install(path):
    path = Path(path)
    if path.is_symlink():raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text(encoding='utf-8')
    result = patched(source)
    if result == source:
        print('Supportbericht bereits installiert.',flush=True)
        return False
    backup = str(path)+'.vor-support-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path,backup)
    descriptor, temporary = tempfile.mkstemp(prefix='plugin.py.support-',dir=str(path.parent))
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as output:
            output.write(result);output.flush();os.fsync(output.fileno())
        shutil.copystat(path,temporary);os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    print('Supportbericht installiert. Sicherung:',backup,flush=True)
    return True

if __name__ == '__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'):
        print('GUI startet neu. Erweiterte Einstellungen > BLAU Extras > Supportbericht erstellen.',flush=True)
        os.system('init 4');time.sleep(3);os.system('init 3')
'''
    data = installer.encode('ascii', errors='backslashreplace')
    compile(data, 'install-support-report.py', 'exec')
    (HERE.parents[1] / 'install-support-report.py').write_bytes(data)
    print('SHA256:', hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    build()
