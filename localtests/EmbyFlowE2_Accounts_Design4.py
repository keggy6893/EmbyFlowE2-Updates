# -*- coding: utf-8 -*-
from pathlib import Path
import datetime
import shutil
import py_compile
import os
path = Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
old = '    skin = scale_skin(\'\'\'\n    <screen name="EmbyFlowFtpAccountsScreen" position="center,center" size="1180,690" flags="wfNoBorder" backgroundColor="#07121e" title="EmbyFlow Accounts">\n      <eLabel position="0,0" size="1180,4" backgroundColor="#00bce8" />\n      <eLabel position="44,30" size="1092,48" text="EmbyFlow E2 - Account auswaehlen" font="Regular;34" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <widget name="status" position="44,98" size="1092,36" font="Regular;23" foregroundColor="#00bce8" backgroundColor="#07121e" />\n      <widget name="accounts" position="44,152" size="520,370" font="Regular;25" itemHeight="36" scrollbarMode="showOnDemand" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColor="#07121e" backgroundColorSelected="#006bc7" />\n      <widget name="details" position="610,156" size="526,270" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <widget name="hint" position="610,434" size="526,100" font="Regular;21" foregroundColor="#b7c3cf" backgroundColor="#07121e" />\n      <eLabel position="180,550" size="820,64" text="OK: ACCOUNT UEBERNEHMEN UND STARTEN" font="Regular;25" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#006bc7" />\n      <eLabel position="44,632" size="580,30" text="Rot / EXIT: Ohne Wechsel weiter" font="Regular;21" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <eLabel position="720,632" size="410,30" text="Blau: Datei neu pruefen" font="Regular;21" foregroundColor="#ffffff" backgroundColor="#07121e" />\n    </screen>\'\'\')\n'
new = '    skin = scale_skin(\'\'\'\n    <screen name="EmbyFlowFtpAccountsScreen" position="center,center" size="1440,900" flags="wfNoBorder" backgroundColor="#07121e" title="EmbyFlow Accounts">\n      <eLabel position="0,0" size="1440,5" backgroundColor="#00bce8" />\n      <eLabel position="48,30" size="1344,58" text="EmbyFlow E2 · Account auswählen" font="Regular;40" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <widget name="status" position="48,98" size="1344,40" font="Regular;28" foregroundColor="#58dbff" backgroundColor="#07121e" />\n      <eLabel position="48,155" size="640,40" text="DEINE ACCOUNTS" font="Regular;26" foregroundColor="#b7c3cf" backgroundColor="#07121e" />\n      <eLabel position="750,155" size="642,40" text="ZUGANGSDATEN" font="Regular;26" foregroundColor="#b7c3cf" backgroundColor="#07121e" />\n      <eLabel position="716,155" size="2,552" backgroundColor="#29465c" />\n      <widget name="accounts" position="48,210" size="640,500" font="Regular;32" itemHeight="50" scrollbarMode="showOnDemand" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColor="#07121e" backgroundColorSelected="#006bc7" />\n      <widget name="details" position="750,210" size="642,370" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <widget name="hint" position="750,592" size="642,116" font="Regular;26" foregroundColor="#cbd8e4" backgroundColor="#07121e" />\n      <eLabel position="48,750" size="1344,72" text="OK  ·  Account übernehmen und starten" font="Regular;32" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#006bc7" />\n      <eLabel position="48,847" size="22,22" backgroundColor="#ef2246" />\n      <eLabel position="84,839" size="740,40" text="ROT / EXIT  ·  Ohne Wechsel weiter" font="Regular;27" foregroundColor="#ffffff" backgroundColor="#07121e" />\n      <eLabel position="960,847" size="22,22" backgroundColor="#006bc7" />\n      <eLabel position="996,839" size="396,40" text="BLAU  ·  Neu einlesen" font="Regular;27" foregroundColor="#ffffff" backgroundColor="#07121e" />\n    </screen>\'\'\')\n'
source = path.read_text(encoding='utf-8')
if new in source:
    print('Design bereits installiert.')
    raise SystemExit(0)
if source.count(old) != 1:
    raise SystemExit('Abbruch: Erwarteter FTP-Test3 nicht gefunden. Nichts verändert.')
updated = source.replace(old, new)
compile(updated, str(path), 'exec')
backup = str(path) + '.design-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(str(path), backup)
tmp = Path(str(path) + '.design-new')
try:
    tmp.write_text(updated, encoding='utf-8')
    shutil.copymode(str(path), str(tmp))
    py_compile.compile(str(tmp), doraise=True)
    os.replace(str(tmp), str(path))
finally:
    if tmp.exists():
        tmp.unlink()
print('FERTIG: Größere Schrift und neues Account-Design installiert. Zugangsdaten unverändert.')
