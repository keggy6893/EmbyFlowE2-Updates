from pathlib import Path
import hashlib

here = Path(__file__).resolve().parent
script = (here / 'install_v2.py').read_text()
script += '\nRUNTIME = %r\n' % (here / 'runtime.py').read_text()
script += '''
if __name__ == '__main__':
    image = dict(line.strip().split('=', 1) for line in Path('/etc/image-version').read_text().splitlines() if '=' in line)
    if image.get('distro') != 'openatv' or not image.get('version', '').startswith('7.6'):
        raise SystemExit('Dieser Layout-Test ist fuer openATV 7.6. Nichts geaendert.')
    changed = install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', RUNTIME)
    if changed:
        print('GUI startet neu.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')
'''
data = script.encode('ascii', 'backslashreplace')
compile(data, 'install-gb76.py', 'exec')
target = here.parents[1] / 'install-gb76.py'
target.write_bytes(data)
print(target.name, hashlib.sha256(data).hexdigest())
