"""Generate unpublished inline installer; preserve user's receiver plugin."""
import base64
import hashlib
from pathlib import Path
import sys
import zlib

HERE = Path(__file__).resolve().parent
destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd() / 'local-artifacts'
destination.mkdir(parents=True, exist_ok=True)
patch = (HERE / 'patch.py').read_text()
installer = (HERE / 'install.py').read_text().split("if __name__ == '__main__':")[0]
script = installer + '\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py", ' + repr(patch) + ')\n'
compile(script, 'install_pgs_local.py', 'exec')
payload = base64.b64encode(zlib.compress(script.encode(), 9)).decode()
# Verify every byte of the transported script before handing it off.
assert zlib.decompress(base64.b64decode(payload)).decode() == script
(destination / 'install_pgs_local.py').write_text(script)
(destination / 'pgs_local_payload.txt').write_text(payload)
remote = "echo " + payload + " | base64 -d | python3 -c 'import sys,zlib;exec(zlib.decompress(sys.stdin.buffer.read()))'"
command = 'ssh -o HostKeyAlias=vu8-slot -o CheckHostIP=no root@192.168.1.11 "' + remote + '"'
(destination / 'install_pgs_local_powershell.txt').write_text(command + '\n')
print('payload bytes:', len(payload))
print('installer SHA256:', hashlib.sha256(script.encode()).hexdigest())
