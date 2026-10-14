# EmbyFlowAndroid – Detail-Test 14.10.2026

Basis: hochgeladene Quellsicherung EmbyFlowAndroid_Stand_20261014_231754.zip.
VU-Referenz: keggy6893/EmbyFlowE2-Updates, Commit 6a54001fffd0656f8e73e9c0d3671ac0f222b363, checkpoints/20261014_091749.

## Änderungen
- Kino-Detailansicht: Fanart und Originalverlauf; Titel/Inhalt links, Poster und vertikale Tasten rechts.
- Plaketten: Bewertung, Jahr, FSK, Laufzeit, verfügbare Bild-/Ton-/UT-Metadaten und voraussichtliche Endzeit.
- Serien: eigener vertikaler Verlauf; Staffelzahl aus dem Server; Staffeln/Folgen als marineblaue Listen, keine Staffelposterreihe.
- Episoden: Abspielen oder Fortsetzen sowie Zurück, ohne Trailer-Schaltfläche.
- Favoriten: Titel/Jahr/Typ gruppieren, unbekannte Jahre nicht gruppieren; Qualitätsdialog ohne interne IDs, Metadaten asynchron. Gruppierung ist eine Heuristik. Mehrere MediaSources eines Eintrags werden weiterhin als ein Eintrag behandelt, angezeigt wird dessen höchste gemeldete Auflösung.
- Zweizeilige Titel im Kategorien-/Favoritenraster. Keine Änderung am Zuschnitt der Weiterschauen-Poster.
- Alle sechs VU-Grafiken unter app/src/main/assets/embyflow. Originale aus dem angegebenen EmbyFlowE2-Repository; Urheberrechte verbleiben bei ihren Rechteinhabern.
- MENU auf der Detailseite: Trailer ein/aus (bisheriges Android-Verhalten standardmäßig ein), Hintergrund Fanart / Emby-Theme-Musik / Emby-Theme-Video. Hintergrundmedien standardmäßig aus. Lautstärke 25 Prozent. Fehlende Medien belassen Fanart. Kein lokaler Bond-Test. Hintergrundmedien stoppen beim Verlassen der Seite.
- Bestehender Trailer-V9-Abgleich, EmbyPlayerActivity und ResumeGridRenderer byteidentisch erhalten.

## Bedienung
Detail: ▲/▼ oder ◀/▶ Taste wählen, OK öffnen, CH+/CH− Inhalt blättern, MENU Einstellungen, Zurück schließen.
Staffelliste: ↑/↓ wählen, OK Folgen; Zurück zur Staffelliste bzw. Detailseite.
Qualität: ↑/↓ wählen, OK gewählte Medien-ID öffnen, Zurück abbrechen.

## Prüfung und Grenzen
- Geänderte Kotlin-Oberflächen samt unverändertem Main-/Trailer-/Resume-Code gegen Android API 35 kompiliert, JVM-Ziel 11. EmbyPlayerActivity wurde für diese isolierte Kompilierung durch einen reinen Activity-Typ ersetzt; der echte Player bleibt unverändert.
- 14 ausführbare Metadatenprüfungen: Gruppierung, Remakes, fehlende Jahre, Episoden, doppelte IDs, tatsächliche/cropped Auflösungen und fehlende Daten.
- Vollständiger Gradle-Build/APK und Laufzeittest am TCL hier nicht durchgeführt. Installer baut zuerst eine separate Testkopie mit dem vorhandenen Windows-SDK/Gradle.
- Server-Themes, Staffellisten, Favoritendialog und neue Darstellung müssen am realen Emby-Server/TCL getestet werden. Trailer werden weiterhin manuell gestartet; keine automatische Trailer-Wiedergabe ergänzt.
- Vollständige Quell-/Konfigurationssicherung ohne Build-Caches vor jeder Installation, bestehender Quellstand wird anhand der SHA256-Werte geprüft.
- Kein APK-Signierschlüssel, keine Server-Zugangsdaten im Updatepaket.

Paket SHA256: 995767c9a87b5862591c33060369dee10f8e9710a439a8904737975a2d0c28ff

Dieses Paket ist nur für EmbyFlowAndroid; der VU-Updatekanal wird nicht verändert.
