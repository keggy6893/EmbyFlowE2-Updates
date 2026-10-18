from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
runtime = (HERE / 'runtime.py').read_text()
script = '''from pathlib import Path
import os, shutil, tempfile, time
'''
script += 'RUNTIME = %r\n' % runtime
script += '''
def patched(source):
    if '# EMBYFLOW_DOWNLOAD_AV1_LOCAL_TEST_V1' in source:return source
    for required in ('class EmbyFlowDownloadsScreen', 'def _embyflow_v22_norm(', 'def fetch_stream_info(', 'def _eflib_valid('):
        if required not in source:raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source + '\\n\\n' + RUNTIME
    compile(result,'plugin.py','exec')
    return result

def install(path):
    path=Path(path)
    if path.is_symlink():raise RuntimeError('Unerwarteter Pluginpfad.')
    source=path.read_text(encoding='utf-8');result=patched(source)
    if source==result:
        print('AV1-Downloadtest bereits installiert.',flush=True);return False
    backup=str(path)+'.vor-av1-download-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path,backup)
    descriptor,temporary=tempfile.mkstemp(prefix='plugin.py.av1-',dir=str(path.parent))
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as output:
            output.write(result);output.flush();os.fsync(output.fileno())
        shutil.copystat(path,temporary);os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    print('Lokaler AV1-Downloadtest installiert. Sicherung:',backup,flush=True)
    return True

if __name__=='__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'):
        print('GUI startet neu. Danach Downloads > Die Wuestenratten > OK.',flush=True)
        os.system('init 4');time.sleep(3);os.system('init 3')
'''
data=script.encode('ascii','backslashreplace')
compile(data,'EmbyFlow_AV1_Download_Test.py','exec')
destination=HERE.parents[1]/'install-download-av1-test.py'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(data)
print(destination,hashlib.sha256(data).hexdigest())
