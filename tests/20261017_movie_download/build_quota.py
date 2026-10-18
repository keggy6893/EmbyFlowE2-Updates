"""Generate a self-contained local quota installer and its transport payload."""
from pathlib import Path
import base64
import zlib

HERE = Path(__file__).resolve().parent
script = (HERE / 'install_quota.py').read_text().split("if __name__ == '__main__':")[0]
script += '\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py", ' + repr((HERE / 'engine.py').read_text()) + ')\n'
compile(script, 'install_download_limit5.py', 'exec')
payload = base64.b64encode(zlib.compress(script.encode(), 9)).decode()
assert zlib.decompress(base64.b64decode(payload)).decode() == script
out = Path('/workspace/local-artifacts')
(out / 'install_download_limit5.py').write_text(script)
command = 'ssh -o HostKeyAlias=vu8-slot -o CheckHostIP=no root@192.168.1.11 "echo ' + payload + " | base64 -d | python3 -c 'import sys,zlib;exec(zlib.decompress(sys.stdin.buffer.read()))'\""
(out / 'install_download_limit5_powershell.txt').write_text(command + '\n')
print('Payload characters:', len(payload))
