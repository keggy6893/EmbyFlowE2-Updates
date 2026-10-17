from pathlib import Path
import os,shutil,sys,time

OLD="""                result=interface.enableSubtitles(widget,entry)
                if result is False:raise RuntimeError('Native Untertitel abgelehnt')
"""
NEW="""                # Reset cached selection before attaching this subtitle window.
                interface.disableSubtitles(widget)
                result=interface.enableSubtitles(widget,entry)
                if result not in (None,0):raise RuntimeError('Native Untertitel abgelehnt')
"""

def patched(source):
    if '# EMBYFLOW_NATIVE_4K_FORCED_TEST_20261017' not in source:
        raise RuntimeError('Direkter 4K-Test fehlt. Nichts geaendert.')
    if source.count(OLD)!=1:
        raise RuntimeError('Einbaustelle abweichend oder bereits korrigiert. Nichts geaendert.')
    result=source.replace(OLD,NEW,1)
    compile(result,'plugin.py','exec');return result

def main():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(p.read_text());backup=p.with_name('plugin.py.vor-native-anbindung-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(p),str(backup));temp=p.with_name('plugin.py.native-repair.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(p),str(temp));os.replace(str(temp),str(p))
    print('4K-Untertitelfenster-Anbindung korrigiert. Sicherung:',backup)
    print('GUI neu starten und dieselbe fremdsprachige Szene pruefen.')

if __name__=='__main__':main()
