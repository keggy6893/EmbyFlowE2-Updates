# EmbyFlowE2-Updates
Update repository for EmbyFlow E2

## Build 2026100801

Die Neuheitenübersicht zeigt sechs Spalten und zwölf Poster pro Seite. Die rechte Vorschau mit Bild und Beschreibung entfällt; die vollständige Detailseite öffnet sich mit OK. Unter den Postern stehen Jahr und Titelart: Film, Serie, Doku oder Doku-Serie. Die Doku-Zuordnung verwendet die Genres des Emby-Servers. Titel nutzen zwei Zeilen mit einer Kürzung bei längeren Namen; ein zusätzlicher automatischer Zeilenumbruch ist deaktiviert.

Die dunklen Hintergrundflächen sind auf Marineblau `#0C1827` vereinheitlicht. Auf der Detailseite bleibt die Fläche deckend, auch wenn ein Hintergrundbild oder Video geladen wird.

### Trailer

Trailer bleiben optional und standardmäßig ausgeschaltet. Aktivierung unter **Erweiterte Einstellungen → Wiedergabe & Diagnose → Trailer aktivieren (Erprobung)**; mit Grün speichern. Der Resolver nutzt das Systempaket yt-dlp ab Version 2026.08.19. Die Reihenfolge bleibt: Emby-Anbieterlinks, KinoCheck, gefilterte YouTube-Ersatzsuche. KinoCheck berücksichtigt Trailer und danach Teaser; die YouTube-Suche prüft Titel, Filmjahr und Länge. Quellen und Ablehnungsgründe erscheinen im Trailer-Log.

Auf der VU+ Duo 4K SE scheiterte ein gültiger YouTube-Trailer durch den zuvor eingestellten AdGuard-Familien-DNS. Nach Umstellung auf DNS ohne erzwungenen YouTube-Restricted-Mode bestätigte der Benutzer Bild und Ton. Das ist eine Netzwerk-Einstellung und kein Teil des Plugin-Updates. Der Benutzer berichtet, dass etwa 95 Prozent seiner Trailer-Tests funktionieren; dies ist keine allgemeine Erfolgsquote. Eine Startzeit von vier Sekunden wird nicht zugesichert.

### Prüfung

Python-Syntax, Skin-XML, 6×2-Layout, Navigation und Titelart-Zuordnung wurden lokal mit simulierten Enigma2-Komponenten geprüft. Der Benutzer bestätigte Marineblau, die Posterübersicht und den Schriftfix auf seiner Box. Andere Receiver und sämtliche Wiedergabeszenarien sind damit nicht geprüft.

Die hochgeladene Box-PY vom 8. Oktober und die anschließend bestätigten Änderungen bilden die Grundlage dieses Builds. Bestehende Sicherheitskorrekturen bleiben enthalten.
