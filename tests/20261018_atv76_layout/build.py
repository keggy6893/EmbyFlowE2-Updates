from pathlib import Path
import hashlib

here=Path(__file__).resolve().parent
script=(here/'install.py').read_text()
script+='\ninstall("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py",%r)\n'%(here/'runtime.py').read_text()
data=script.encode('ascii','backslashreplace')
compile(data,'EmbyFlow_ATV76_Layout_INSTALL.py','exec')
out=Path('/workspace/local-artifacts/EmbyFlow_ATV76_Layout_INSTALL.py');out.write_bytes(data)
print(out,hashlib.sha256(data).hexdigest())
