$ErrorActionPreference = 'Stop'
$project = 'C:\Users\bumse\AndroidStudioProjects\EmbyFlowAndroid'
$destination = 'C:\Users\bumse\Downloads\TCL'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stage = Join-Path $destination "EmbyFlowAndroid_CommunityTest_$stamp"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$expected = @{
 'app\src\main\AndroidManifest.xml' = '0601c23939ebe72ee4566418077323732aef10c2816c0b8a4a642762b713ee41'
 'app\src\main\java\de\embyflow\androidtv\MainActivity.kt' = '19bdf46e8e94b0c15c4d489ce405284855861ea4fa1a1a603c38236a11d95ee2'
 'app\build.gradle.kts' = '08744b6fda00b118facb06b823c327206843a7a66bfcb2f2ee50d12a551c1d47'
 'app\src\main\res\xml\backup_rules.xml' = '6cf1a27e6807b1d24e41d3fbe7ddc1bfe1f42226027964f6eaf477d71b43b283'
 'app\src\main\res\xml\data_extraction_rules.xml' = 'cb1fc47ab4a984530ed60e0e6ee638929c3038290e7e7e0b4b03a3a30fbe7381'
}
foreach ($relative in $expected.Keys) {
 $file = Join-Path $project $relative
 if (!(Test-Path $file) -or (Get-FileHash $file -Algorithm SHA256).Hash -ne $expected[$relative]) {
  throw "Quellstand abweichend: $relative. Nichts geaendert."
 }
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null
# Current source ZIP remains the pre-change checkpoint. Work on a separate copy.
robocopy $project $stage /E /XD .gradle build .git .idea /R:1 /W:1 /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Projektkopie fehlgeschlagen.' }
function Replace-Once([string]$Text, [string]$Before, [string]$After) {
 if (($Text.Split(@($Before), [StringSplitOptions]::None).Count - 1) -ne 1) {
  throw 'Einbaustelle nicht eindeutig. Originalprojekt unveraendert.'
 }
 return $Text.Replace($Before, $After)
}
$main = Join-Path $stage 'app\src\main\java\de\embyflow\androidtv\MainActivity.kt'
$text = [IO.File]::ReadAllText($main).Replace("`r`n", "`n")
$before = @'
            if (hasServer && hasToken && hasUser) {
                fetchMedia("Movie")
            }
'@
$after = @'
            if (hasServer && hasToken && hasUser) {
                fetchMedia("Movie")
            } else {
                openEmbySettings()
            }
'@
$text = Replace-Once $text $before $after
$before = @'
                            screen.invalidate()
                        }

                    } catch (e: Exception) {
'@
$after = @'
                            screen.invalidate()
                            fetchMedia("Movie")
                        }

                    } catch (e: Exception) {
'@
$text = Replace-Once $text $before $after
[IO.File]::WriteAllText($main, $text, $utf8)
$manifest = Join-Path $stage 'app\src\main\AndroidManifest.xml'
$text = [IO.File]::ReadAllText($manifest)
$text = Replace-Once $text '<application android:allowBackup="true"' '<application android:allowBackup="false" android:usesCleartextTraffic="true"'
$text = Replace-Once $text "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"true`"" "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"false`""
[IO.File]::WriteAllText($manifest, $text, $utf8)
$gradle = Join-Path $stage 'app\build.gradle.kts'
$text = [IO.File]::ReadAllText($gradle)
$text = Replace-Once $text 'versionCode = 1' 'versionCode = 2026101601'
$text = Replace-Once $text 'versionName = "1.0"' 'versionName = "0.4.0-test1"'
[IO.File]::WriteAllText($gradle, $text, $utf8)
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\res\xml\backup_rules.xml'), '<full-backup-content><exclude domain="sharedpref" path="embyflow.xml" /></full-backup-content>', $utf8)
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\res\xml\data_extraction_rules.xml'), '<data-extraction-rules><cloud-backup><exclude domain="sharedpref" path="embyflow.xml" /></cloud-backup><device-transfer><exclude domain="sharedpref" path="embyflow.xml" /></device-transfer></data-extraction-rules>', $utf8)
if (!(Test-Path "$stage\gradlew.bat")) { throw 'Gradle-Wrapper fehlt.' }
$studioJava = 'C:\Program Files\Android\Android Studio\jbr'
if (Test-Path "$studioJava\bin\java.exe") { $env:JAVA_HOME = $studioJava }
$log = Join-Path $destination "EmbyFlowAndroid_Build_$stamp.log"
Push-Location $stage
try {
 & .\gradlew.bat --no-daemon :app:assembleDebug 2>&1 | Tee-Object -FilePath $log
 $buildExit = $LASTEXITCODE
} finally { Pop-Location }
if ($buildExit -ne 0) {
 explorer.exe "/select,`"$log`""
 throw "APK-Build fehlgeschlagen. Bitte die markierte Logdatei hier hochladen."
}
$built = Join-Path $stage 'app\build\outputs\apk\debug\app-debug.apk'
if (!(Test-Path $built)) { throw 'Keine APK gefunden.' }
$apk = Join-Path $destination "EmbyFlowAndroid_0.4.0-test1_$stamp.apk"
Copy-Item $built $apk
$hash = (Get-FileHash $apk -Algorithm SHA256).Hash
[IO.File]::WriteAllText("$apk.sha256", "$hash  $([IO.Path]::GetFileName($apk))`n", $utf8)
Write-Host "TEST-APK FERTIG: $apk" -ForegroundColor Green
Write-Host 'Noch nicht verteilt oder auf dem TCL installiert.'
explorer.exe "/select,`"$apk`""
