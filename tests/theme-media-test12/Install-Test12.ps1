param([string]$Box = '192.168.1.11')
$ErrorActionPreference = 'Stop'
$paket = Join-Path $PSScriptRoot 'EmbyFlowE2_ThemeMedia_Test12.zip'
if (-not (Test-Path -LiteralPath $paket)) { throw "Testpaket fehlt: $paket" }
$erwartet = 'cabb7fbf95885e419b8db335400f07603274d4226ae80e8a6f2d2e58441ff399'
if ((Get-FileHash -LiteralPath $paket -Algorithm SHA256).Hash.ToLowerInvariant() -ne $erwartet) {
    throw 'ZIP-Prüfsumme stimmt nicht. Installation gestoppt.'
}
& scp $paket "root@${Box}:/tmp/embyflow-theme-test12.zip"
if ($LASTEXITCODE -ne 0) { throw 'Upload fehlgeschlagen.' }
$installation = @'
set -eu
ordner=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
ziel="$ordner/plugin.py"
manager="$ordner/theme_media_manager.py"
zip=/tmp/embyflow-theme-test12.zip
test -f "$ziel" || { echo 'ABBRUCH: Plugin nicht vorhanden'; exit 2; }
alt=$(sha256sum "$ziel" | cut -d ' ' -f 1)
test "$alt" = '362a4131f5fad14991a670f086c16010fef550e6e6d3bb697a31a63f2944dab9' || {
  echo "ABBRUCH: Erwartet ist Test11; aktuell: $alt"
  exit 2
}
unzip -t "$zip" >/dev/null
unzip -p "$zip" EmbyFlowE2/plugin.py > /tmp/embyflow-test12-plugin.py
unzip -p "$zip" EmbyFlowE2/theme_media_manager.py > /tmp/embyflow-test12-manager.py
printf '%s  %s\n' \
  '9a8fca79605c75dab5e0fbb7bddec540b9a81042dd01ff4a8862af8343faafd3' /tmp/embyflow-test12-plugin.py \
  '2308c8efb793a66ffd2c71d5e6d508155a42959069ce68d786b63bccfe1966dc' /tmp/embyflow-test12-manager.py | sha256sum -c -
python3 -m py_compile /tmp/embyflow-test12-plugin.py /tmp/embyflow-test12-manager.py
sicherung="$ordner/plugin.py.before-theme-test12.bak"
test ! -e "$sicherung" || { echo "ABBRUCH: Sicherung existiert bereits: $sicherung"; exit 2; }
cp -p "$ziel" "$sicherung"
manager_alt=0
if test -e "$manager"; then
  test ! -e "$manager.before-theme-test12.bak" || { echo 'ABBRUCH: Manager-Sicherung existiert bereits'; exit 2; }
  cp -p "$manager" "$manager.before-theme-test12.bak"
  manager_alt=1
fi
fertig=0
rollback() {
  if test "$fertig" -eq 0; then
    cp -p "$sicherung" "$ziel"
    if test "$manager_alt" -eq 1; then
      cp -p "$manager.before-theme-test12.bak" "$manager"
    else
      rm -f "$manager"
    fi
    echo 'Installation fehlgeschlagen; Dateien wiederhergestellt.'
  fi
}
trap rollback EXIT
cp /tmp/embyflow-test12-manager.py "$manager"
cp /tmp/embyflow-test12-plugin.py "$ziel"
python3 -m py_compile "$manager" "$ziel"
test "$(sha256sum "$ziel" | cut -d ' ' -f 1)" = '9a8fca79605c75dab5e0fbb7bddec540b9a81042dd01ff4a8862af8343faafd3'
fertig=1
trap - EXIT
if python3 -c 'import yt_dlp' >/dev/null 2>&1; then
  echo 'yt-dlp vorhanden: ThemerrDB-Fallback kann getestet werden.'
else
  echo 'HINWEIS: yt-dlp fehlt; Emby-eigene Theme-Songs funktionieren weiterhin.'
fi
echo 'Test12 installiert; Plugin-Sicherung liegt dauerhaft neben plugin.py.'
'@
($installation -replace "`r", '') | & ssh "root@$Box" 'sh -s'
if ($LASTEXITCODE -ne 0) { throw 'Installation abgebrochen; Ausgabe oben prüfen. Kein Neustart ausgelöst.' }
Write-Host 'Installation geprüft. Box startet normal neu.'
& ssh "root@$Box" reboot
if ($LASTEXITCODE -ne 0) { Write-Warning 'SSH-Verbindung beim Neustart beendet. Bitte prüfen, ob die Box neu startet.' }
