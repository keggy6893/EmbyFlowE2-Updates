from pathlib import Path
import hashlib

here = Path(__file__).resolve().parent
script = (here/'install.py').read_text()
script += '\nRUNTIME = %r\n' % (here/'runtime.py').read_text()
script += '''
if __name__ == '__main__':
    changed = install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', RUNTIME)
    if changed:
        print('GUI startet neu. Danach Film in EmbyFlow starten.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')
'''
data = script.encode('ascii','backslashreplace')
compile(data, 'install-lcd-time.py', 'exec')
destination = here.parents[1]/'install-lcd-time.py'
destination.write_bytes(data)
print(destination.name, hashlib.sha256(data).hexdigest())
