# Copy-only recovery. Never starts an encoder or calls Emby.
param(
    [string]$Box = '192.168.1.11',
    [string]$WorkDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'EmbyFlow-Offline')
)
$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $OutputEncoding
$sshOptions = @('-o','HostKeyAlias=vu8-slot','-o','CheckHostIP=no','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3')
$boxLogin = 'root@' + $Box

function Invoke-Box([string]$Code) {
    $result = @($Code | & ssh @sshOptions $boxLogin 'python3 -')
    if ($LASTEXITCODE -ne 0) { throw 'Box nicht erreichbar oder HDD-Pruefung fehlgeschlagen. PC-Datei bleibt erhalten.' }
    return (($result -join "`n") | ConvertFrom-Json)
}

try {
    $movie = Join-Path $WorkDirectory 'Wuestenratten-H264-AAC.mp4'
    if (-not (Test-Path -LiteralPath $movie -PathType Leaf)) { throw ('Fertige PC-Datei fehlt: ' + $movie) }
    $size = (Get-Item -LiteralPath $movie).Length
    if ($size -le 0) { throw 'PC-Datei ist leer.' }
    Write-Host 'Fertige MP4 am PC pruefen. Keine neue Umwandlung.'
    $hash = (Get-FileHash -LiteralPath $movie -Algorithm SHA256).Hash.ToLowerInvariant()
    $remote = "expected = '$hash'`nsize = $size`n" + @'
import base64, glob, hashlib, json, os, shutil
def digest(path):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()
paths = set()
for path in glob.glob('/media/*/movie/EmbyFlow/*_1731728_*.mkv'):
    mount = os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(path))))
    if os.path.ismount(mount) and os.path.isfile(path) and not os.path.islink(path):
        paths.add(os.path.realpath(path))
if len(paths) != 1:
    raise SystemExit('Original-HDD nicht eindeutig gefunden. Keine Datei geaendert.')
original = paths.pop()
target = os.path.splitext(original)[0] + '_H264_AAC.mp4'
complete = False
if os.path.lexists(target):
    if os.path.islink(target) or not os.path.isfile(target) or digest(target) != expected:
        raise SystemExit('Andere fertige Zieldatei existiert. Nichts ersetzt.')
    complete = True
stage = os.path.join(os.path.dirname(original), '.embyflow-pc-' + expected + '.part')
if os.path.lexists(stage) and (os.path.islink(stage) or not os.path.isfile(stage)):
    raise SystemExit('Unerwartete temporaere Zieldatei. Nichts ersetzt.')
if not complete and shutil.disk_usage(os.path.dirname(original)).free < size + 512*1024*1024:
    raise SystemExit('Zu wenig freier HDD-Speicher fuer die Rueckkopie.')
print(json.dumps({'complete':complete, 'stage64':base64.b64encode(stage.encode()).decode(),
    'target64':base64.b64encode(target.encode()).decode()}))
'@
    Write-Host 'HDD-Ziel auf der Box pruefen. Box-Passwort eingeben.'
    $target = Invoke-Box $remote
    if (-not $target.complete) {
        $stage = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($target.stage64))
        if ($stage -notmatch '^/media/[A-Za-z0-9_/-]+/\.embyflow-pc-[a-f0-9]{64}\.part$') {
            throw 'Unerwarteter temporaerer HDD-Pfad.'
        }
        Write-Host 'Nur fertige MP4 zurueckkopieren. Box-Passwort eingeben.'
        # ASCII staging name avoids the legacy-SCP UTF-8 filename issue.
        & scp '-O' @sshOptions $movie ($boxLogin + ':' + $stage)
        if ($LASTEXITCODE -ne 0) {
            throw 'Verbindung bei Rueckkopie unterbrochen. Diesen Kopierbefehl erneut ausfuehren; keine neue Umwandlung noetig.'
        }
        $record = @{ expected=$hash; size=$size; stage64=$target.stage64; target64=$target.target64 } | ConvertTo-Json -Compress
        $record64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($record))
        $publish = "record64 = '$record64'`n" + @'
import base64, hashlib, json, os
record = json.loads(base64.b64decode(record64))
stage = base64.b64decode(record['stage64']).decode()
target = base64.b64decode(record['target64']).decode()
result = hashlib.sha256()
with open(stage, 'rb') as stream:
    if os.fstat(stream.fileno()).st_size != record['size']:
        raise SystemExit('Rueckkopie unvollstaendig. Fertige PC-Datei bleibt erhalten.')
    for block in iter(lambda:stream.read(1024*1024), b''):
        result.update(block)
if result.hexdigest() != record['expected']:
    raise SystemExit('Rueckkopie-Pruefsumme falsch. Keine fertige Datei freigegeben.')
os.link(stage, target)
os.unlink(stage)
print(json.dumps({'ok':True}))
'@
        Write-Host 'HDD-Kopie per SHA256 pruefen. Box-Passwort eingeben; danach kurz warten.'
        $published = Invoke-Box $publish
        if (-not $published.ok) { throw 'HDD-Datei konnte nicht freigegeben werden.' }
    }
    Write-Host 'FERTIG: H264_AAC.mp4 ist vollstaendig auf der Receiver-HDD.' -ForegroundColor Green
    Write-Host 'Jetzt im normalen Mediaplayer starten. PC-Kopie und AV1-Original bleiben erhalten.'
} catch {
    Write-Host ('STOPP: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
