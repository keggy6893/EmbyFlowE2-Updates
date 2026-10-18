"""Regenerate the self-contained installer published on the test branch."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'test_installer_template.py').read_text()
source += '\n\nNATIVE_PATCH = ' + repr((HERE / 'patch.py').read_text())
source += '\nAUTO_PATCH = ' + repr((HERE / 'auto.py').read_text())
source += "\n\nif __name__ == '__main__':\n    install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', NATIVE_PATCH, AUTO_PATCH)\n"
compile(source, 'install_test.py', 'exec')
destination = HERE / 'install_test.py'
destination.write_text(source)
print(destination)
