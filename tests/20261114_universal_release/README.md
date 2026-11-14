# RC26.5 Universal NAS + Resume - isolierter Test

Dieser Testbranch enthält einen gemeinsamen EmbyFlowE2-Testbuild für mehrere Enigma2-Receiver, der den AutoFS/Direct-Play-Resolver des HD51-Standes mit der VU+-V6-Detailansicht kombiniert.

**Nicht allgemein freigegeben.** Der produktive Feed auf main wurde nicht verändert.

- Testbuild: `2026-RC26.5-UNIVERSAL-NAS-RESUME-TEST`, Build `2026111410`
- Download: `plugin.py` (SHA256 `c15ac3a028d4b30b2343667912b4bd24a9ac782c4729cfe9619671dbc1b18e79`)
- Isolierter Update-Feed: `update.json`
- Sicherungs-/Testinstaller: `install_test.sh`
- Erwartete Funktionen: geprüfte NAS-Dateizuordnung bei `.ts`, `.mkv`, `.mp4`, `.m2ts`; natives Abspielen wenn möglich; HTTP-Fallback; Detailansicht mit `Fortsetzen` und `Von vorn abspielen`.
- **Noch nicht behoben / nicht getestet:** Synchronisierung von `Weiterschauen`, vollständige Gerätekompatibilität, tatsächlicher Diensttyp und Audio-Wechsel nach Integration.

Zum **einmaligen Test auf einer ausgewählten Box** via Telnet:

```sh
wget -qO /tmp/ef_rc265_install.sh "https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/rcdev-universal-test-20261114/tests/20261114_universal_release/install_test.sh" && sh /tmp/ef_rc265_install.sh
```

Anschließend GUI neu starten (`init 4; sleep 3; init 3`) und zuerst Filmstart, Deutsch/Englisch-Tonwechsel, Fortsetzen sowie Von-vorn-Abspielen prüfen.

Rollback der Testinstallation:

```sh
P=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
cp "$P/plugin.py.before_rc265_universal" "$P/plugin.py" && init 4 && sleep 3 && init 3
```

Nicht über den produktiven RC-Feed verteilen, bevor die Regressionstests bestanden sind.
