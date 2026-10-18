"""Standalone local installer; no network download and no publication."""
from pathlib import Path
import base64
import zlib

HERE = Path(__file__).resolve().parent
script = (HERE / 'install_library.py').read_text()
script += '\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py", %r)\n' % (HERE / 'library.py').read_text()
compile(script, 'install_download_library.py', 'exec')
out = Path('/workspace/local-artifacts')
out.mkdir(exist_ok=True)
(out / 'install_download_library.py').write_text(script)
payload = base64.b64encode(zlib.compress(script.encode(), 9)).decode()
command = 'ssh -o HostKeyAlias=vu8-slot -o CheckHostIP=no root@192.168.1.11 "echo ' + payload + " | base64 -d | python3 -c 'import sys,zlib;exec(zlib.decompress(sys.stdin.buffer.read()))' && init 4 && sleep 3 && init 3\""
(out / 'install_download_library_powershell.txt').write_text(command + '\n')
print('Installer command characters:', len(command))
