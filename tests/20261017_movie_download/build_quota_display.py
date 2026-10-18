"""One-file direct installer; neither downloads nor publishes user code."""
from pathlib import Path
import ast
import base64
import zlib

HERE = Path(__file__).resolve().parent
engine = (HERE / 'engine.py').read_text()
status = next(ast.get_source_segment(engine, node) for node in ast.parse(engine).body
              if isinstance(node, ast.FunctionDef) and node.name == 'quota_status')
script = (HERE / 'install_quota.py').read_text().split("if __name__ == '__main__':")[0]
script += '\nquota_patch = patched\n'
script += (HERE / 'install_quota_display.py').read_text().replace('from install_quota import patched as quota_patch\n', '', 1)
script += '\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py", %r, %r, %r)\n' % (engine, status, (HERE / 'quota_display.py').read_text())
compile(script, 'install_download_counter.py', 'exec')
out = Path('/workspace/local-artifacts')
(out / 'install_download_counter.py').write_text(script)
payload = base64.b64encode(zlib.compress(script.encode(), 9)).decode()
assert zlib.decompress(base64.b64decode(payload)).decode() == script
command = 'ssh -o HostKeyAlias=vu8-slot -o CheckHostIP=no root@192.168.1.11 "echo ' + payload + " | base64 -d | python3 -c 'import sys,zlib;exec(zlib.decompress(sys.stdin.buffer.read()))'\""
(out / 'install_download_counter_powershell.txt').write_text(command + '\n')
print('Payload characters:', len(payload))
