"""Build the direct-on-box auto installer, without publishing anything."""
from pathlib import Path
import base64
import zlib
import sys

HERE = Path(__file__).resolve().parent
patch = (HERE / 'auto.py').read_text()
installer = (HERE / 'install_auto.py').read_text().split("if __name__ == '__main__':")[0]
script = installer + '\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py", ' + repr(patch) + ')\n'
compile(script, 'install_pgs_auto.py', 'exec')
payload = base64.b64encode(zlib.compress(script.encode(), 9)).decode()
assert zlib.decompress(base64.b64decode(payload)).decode() == script
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd() / 'local-artifacts'
out.mkdir(parents=True, exist_ok=True)
(out / 'install_pgs_auto.py').write_text(script)
(out / 'pgs_auto_payload.txt').write_text(payload)
command = 'ssh -o HostKeyAlias=vu8-slot -o CheckHostIP=no root@192.168.1.11 "echo ' + payload + " | base64 -d | python3 -c 'import sys,zlib;exec(zlib.decompress(sys.stdin.buffer.read()))'\""
(out / 'install_pgs_auto_powershell.txt').write_text(command + '\n')
print(command)
