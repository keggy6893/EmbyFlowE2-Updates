# Windows PowerShell 5.1. Encoding runs on the PC; no Emby API is used.
param(
    [string]$Box = '192.168.1.11',
    [string]$WorkDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'EmbyFlow-Offline'),
    [string]$FfmpegDirectory = ''
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $OutputEncoding
$sshOptions = @('-o', 'HostKeyAlias=vu8-slot', '-o', 'CheckHostIP=no')
$boxLogin = 'root@' + $Box

function Invoke-BoxPython([string]$Code) {
    $result = @($Code | & ssh @sshOptions $boxLogin 'python3 -')
    if ($LASTEXITCODE -ne 0) { throw 'Box-Abfrage fehlgeschlagen. Original bleibt erhalten.' }
    return (($result -join "`n") | ConvertFrom-Json)
}

function Remote-ScpPath([string]$Path) {
    # scp -O uses the remote shell: quote paths containing spaces/umlauts.
    if ($Path.Contains("'") -or $Path.Contains("`n") -or $Path.Contains("`r")) {
        throw 'Dateiname kann nicht sicher uebertragen werden.'
    }
    return $boxLogin + ":'" + $Path + "'"
}

try {
    foreach ($program in @('ssh', 'scp')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
            throw ($program + ' fehlt. Windows OpenSSH-Client wird benoetigt.')
        }
    }
    # Older Windows OpenSSH already uses the legacy SCP protocol and has no -O.
    $scpCheck = New-Object System.Diagnostics.ProcessStartInfo
    $scpCheck.FileName = (Get-Command scp).Source
    $scpCheck.Arguments = '-O'
    $scpCheck.UseShellExecute = $false
    $scpCheck.RedirectStandardError = $true
    $scpCheck.RedirectStandardOutput = $true
    $scpProcess = [Diagnostics.Process]::Start($scpCheck)
    $scpHelp = $scpProcess.StandardError.ReadToEnd() + $scpProcess.StandardOutput.ReadToEnd()
    $scpProcess.WaitForExit()
    $scpProcess.Dispose()
    $scpMode = @('-O')
    if ($scpHelp -match '(?i)(unknown|illegal|invalid) option') { $scpMode = @() }
    New-Item -ItemType Directory -Force -Path $WorkDirectory | Out-Null
    $WorkDirectory = (Resolve-Path -LiteralPath $WorkDirectory).Path
    Write-Host '1/5 Originaldatei auf der Box suchen. Box-Passwort eingeben.'
    $discover = @'
import base64, glob, json, os, shutil
paths = []
for path in glob.glob('/media/*/movie/EmbyFlow/*_1731728_*.mkv'):
    root = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    if os.path.ismount(os.path.realpath(root)) and os.path.isfile(path) and not os.path.islink(path):
        real = os.path.realpath(path)
        if real not in paths:
            paths.append(real)
if len(paths) != 1:
    raise SystemExit('Original nicht eindeutig gefunden: %d Dateien. Nichts geaendert.' % len(paths))
path = paths[0]
destination = os.path.splitext(path)[0] + '_H264_AAC.mp4'
if os.path.lexists(destination):
    raise SystemExit('H264/AAC-Datei ist bereits auf der HDD vorhanden. Nichts ersetzt.')
print(json.dumps({'path64':base64.b64encode(path.encode()).decode(), 'size':os.path.getsize(path),
    'free':shutil.disk_usage(os.path.dirname(path)).free}))
'@
    $source = Invoke-BoxPython $discover
    $remoteSource = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($source.path64))
    $remoteTarget = $remoteSource.Substring(0, $remoteSource.Length - 4) + '_H264_AAC.mp4'
    # 90 minutes at <=6.2 Mbit/s plus margin; checked again after probing.
    $reserve = 512MB
    $outputBudget = 6GB
    $drive = New-Object System.IO.DriveInfo -ArgumentList ([IO.Path]::GetPathRoot($WorkDirectory))
    if ($drive.AvailableFreeSpace -lt ([long]$source.size + $outputBudget + $reserve)) {
        throw 'Am PC wird Platz fuer Original plus 6 GiB und Reserve benoetigt.'
    }
    if ([long]$source.free -lt ($outputBudget + $reserve)) {
        throw 'Auf der Box-HDD fehlen 6 GiB freier Platz plus Reserve.'
    }

    Write-Host '2/5 FFmpeg fuer den PC vorbereiten.'
    if (-not $FfmpegDirectory) {
        $FfmpegDirectory = Join-Path $WorkDirectory 'ffmpeg-9.0.2-essentials_build\bin'
        if (-not (Test-Path -LiteralPath (Join-Path $FfmpegDirectory 'ffmpeg.exe'))) {
            $zip = Join-Path $WorkDirectory 'ffmpeg-9.0.2.zip'
            $expected = '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'
            $uri = 'https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip'
            Write-Host 'Einmaliger Download: etwa 115 MB. Pruefsumme wird kontrolliert.'
            Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $zip
            if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
                throw 'FFmpeg-Pruefsumme stimmt nicht. Keine Ausfuehrung.'
            }
            Expand-Archive -LiteralPath $zip -DestinationPath $WorkDirectory -Force
        }
    }
    $ffmpeg = Join-Path $FfmpegDirectory 'ffmpeg.exe'
    $ffprobe = Join-Path $FfmpegDirectory 'ffprobe.exe'
    if (-not (Test-Path -LiteralPath $ffmpeg) -or -not (Test-Path -LiteralPath $ffprobe)) {
        throw 'FFmpeg/ffprobe nicht gefunden.'
    }
    $inputFile = Join-Path $WorkDirectory 'Wuestenratten-original.mkv'
    $outputFile = Join-Path $WorkDirectory 'Wuestenratten-H264-AAC.mp4'
    if (Test-Path -LiteralPath $outputFile) {
        throw ('PC-Zieldatei existiert bereits: ' + $outputFile + '. Nichts ersetzt.')
    }
    if (Test-Path -LiteralPath $inputFile) {
        throw ('PC-Original existiert bereits: ' + $inputFile + '. Nichts ersetzt.')
    }

    Write-Host '3/5 Original von HDD auf PC kopieren. Box-Passwort eingeben.'
    $scpSource = Remote-ScpPath $remoteSource
    & scp @scpMode @sshOptions $scpSource $inputFile
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $inputFile) -or
        (Get-Item -LiteralPath $inputFile).Length -ne [long]$source.size) {
        throw 'Kopie unvollstaendig. Die Originaldatei auf der Box bleibt erhalten.'
    }
    $inputProbeText = & $ffprobe '-v' 'error' '-show_entries' 'format=duration:stream=index,codec_type:stream_tags=language:stream_disposition=default' '-of' 'json' $inputFile
    if ($LASTEXITCODE -ne 0) { throw 'PC-Kopie konnte nicht gelesen werden.' }
    $inputProbe = ($inputProbeText -join "`n") | ConvertFrom-Json
    $seconds = [double]::Parse([string]$inputProbe.format.duration, [Globalization.CultureInfo]::InvariantCulture)
    if ($seconds -lt 1 -or $seconds -gt 5400) { throw 'Unerwartete Filmlaenge. Keine Umwandlung gestartet.' }
    $audioTracks = @($inputProbe.streams | Where-Object { $_.codec_type -eq 'audio' })
    if (-not $audioTracks.Count) { throw 'Keine Tonspur gefunden. Keine Umwandlung gestartet.' }
    $audioTrack = @($audioTracks | Where-Object { $_.tags.language -match '^(de|deu|ger)$' } | Select-Object -First 1)
    if (-not $audioTrack.Count) {
        $audioTrack = @($audioTracks | Where-Object { $_.disposition.default -eq 1 } | Select-Object -First 1)
    }
    if (-not $audioTrack.Count) { $audioTrack = @($audioTracks[0]) }
    $audioMap = '0:' + $audioTrack[0].index

    Write-Host '4/5 Umwandlung am PC. Laufende Zeit und speed= zeigen den Fortschritt.'
    Write-Host 'Das kann je nach PC laenger dauern. PC und Fenster eingeschaltet lassen.'
    $partial = Join-Path $WorkDirectory ('Wuestenratten-' + [Guid]::NewGuid().ToString('N') + '.part.mp4')
    & $ffmpeg '-hide_banner' '-nostdin' '-n' '-xerror' '-i' $inputFile '-map' '0:v:0' '-map' $audioMap `
        '-vf' 'scale=w=min(1920\,iw):h=min(1080\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2' `
        '-c:v' 'libx264' '-preset' 'veryfast' '-crf' '21' '-maxrate' '6M' '-bufsize' '12M' `
        '-pix_fmt' 'yuv420p' '-c:a' 'aac' '-b:a' '192k' '-ac' '2' '-sn' '-dn' '-movflags' '+faststart' $partial
    if ($LASTEXITCODE -ne 0) { throw 'PC-Umwandlung fehlgeschlagen. Originale bleiben erhalten.' }
    $probeText = & $ffprobe '-v' 'error' '-show_entries' 'format=duration:stream=codec_type,codec_name,pix_fmt,channels' '-of' 'json' $partial
    if ($LASTEXITCODE -ne 0) { throw 'MP4-Dateipruefung fehlgeschlagen.' }
    $probe = ($probeText -join "`n") | ConvertFrom-Json
    $video = @($probe.streams | Where-Object { $_.codec_type -eq 'video' })
    $audio = @($probe.streams | Where-Object { $_.codec_type -eq 'audio' })
    $duration = [double]::Parse([string]$probe.format.duration, [Globalization.CultureInfo]::InvariantCulture)
    if ($video.Count -ne 1 -or $video[0].codec_name -ne 'h264' -or $video[0].pix_fmt -ne 'yuv420p' -or
        $audio.Count -ne 1 -or $audio[0].codec_name -ne 'aac' -or $audio[0].channels -ne 2 -or
        [Math]::Abs($duration - $seconds) -gt 3 -or (Get-Item -LiteralPath $partial).Length -gt $outputBudget) {
        throw 'Ausgabe entspricht nicht H.264/AAC oder hat eine abweichende Laenge. Keine Rueckkopie.'
    }
    Move-Item -LiteralPath $partial -Destination $outputFile

    Write-Host '5/5 Fertige MP4 auf HDD kopieren. Box-Passwort eingeben.'
    $remotePartial = $remoteTarget + '.' + [Guid]::NewGuid().ToString('N') + '.part'
    $scpTarget = Remote-ScpPath $remotePartial
    & scp @scpMode @sshOptions $outputFile $scpTarget
    if ($LASTEXITCODE -ne 0) { throw ('Rueckkopie fehlgeschlagen. Fertige MP4 liegt am PC: ' + $outputFile) }
    $fileHash = (Get-FileHash -LiteralPath $outputFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $record = @{ partial64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remotePartial));
        target64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteTarget)); sha256=$fileHash } | ConvertTo-Json -Compress
    $record64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($record))
    $publish = "record64 = '$record64'`n" + @'
import base64, hashlib, json, os
record = json.loads(base64.b64decode(record64))
partial = base64.b64decode(record['partial64']).decode()
target = base64.b64decode(record['target64']).decode()
try:
    digest = hashlib.sha256()
    with open(partial, 'rb') as source:
        for block in iter(lambda:source.read(1024*1024), b''):
            digest.update(block)
    if digest.hexdigest() != record['sha256']:
        raise ValueError('Rueckkopie beschaedigt. Fertige PC-Datei bleibt erhalten.')
    os.link(partial, target)
finally:
    if os.path.exists(partial):
        os.unlink(partial)
print(json.dumps({'ok':True}))
'@
    $published = Invoke-BoxPython $publish
    if (-not $published.ok) { throw 'Veroeffentlichung der HDD-Datei fehlgeschlagen.' }
    Write-Host ''
    Write-Host 'FERTIG: Neue H264_AAC.mp4 liegt auf der Box-HDD.' -ForegroundColor Green
    Write-Host 'Im normalen Mediaplayer die Datei mit H264_AAC im Namen starten.'
    Write-Host ('PC-Dateien bleiben erhalten: ' + $WorkDirectory)
    Write-Host 'Der Emby-Server wurde nicht verwendet.'
} catch {
    Write-Host ('STOPP: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Die urspruengliche Filmdatei auf der Box wurde nicht veraendert.'
    exit 1
}
