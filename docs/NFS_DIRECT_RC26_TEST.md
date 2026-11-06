# EmbyFlowE2 RC26 – konfigurierbare NFS-Direktwiedergabe (Entwicklungsstand)

**Status:** Quellcode-Teststand, kein fertiges IPK und kein freigegebenes Update.

## Hintergrund

Auf einer VU+ Duo 4K SE wurde bei einer NAS-TS-Datei die native Wiedergabe per Enigma2-Service-Typ 1 erfolgreich getestet. Die Wiedergabe einschließlich Audio-Umschaltung funktionierte. Der bisherige HTTP-Wiedergabeweg führte beim Tonspurwechsel zu Standbild und Tonausfall.

**Diese Beobachtung ist kein Nachweis für andere Receiver oder NAS-Mounts.**

## Sicherheitsregeln

- Keine private NAS-Adresse oder benutzerspezifischen Pfade im Quellcode.
- Kein Raten anhand gleicher Dateinamen.
- Direkte Wiedergabe nur bei eindeutigem Emby-Medienpfad und lesbarer Datei.
- Keine Änderung am Stream-Verhalten, wenn kein eindeutiges Mapping existiert.
- Nichts automatisch installieren; der reguläre Updatekanal bleibt unverändert.

## Konfiguration je Receiver

Eine receiverlokale JSON-Datei ist vorgesehen: `/etc/enigma2/embyflow_nfs_map.json`

Beispiel mit **Platzhaltern**, nicht direkt übernehmen:

```json
{
  "mappings": [
    {
      "server_prefix": "/SERVER/MEDIEN/",
      "local_prefix": "/media/NETZLAUFWERK/"
    }
  ]
}
```

Der Server-Präfix muss exakt dem `Path` aus dem ausgewählten Emby-`MediaSource` entsprechen. Der lokale Präfix muss auf einen tatsächlich eingebundenen NFS-Ordner zeigen.

## Noch erforderlich vor Freigabe

1. Build/Package aus geprüftem RC26-Quellstand erstellen.
2. Mehrere MediaSources, Pfad-Sicherheitsprüfung, fehlende Konfiguration und Fallback testen.
3. Anskars tatsächliche NFS-Freigabe und MediaSource-Pfade feststellen.
4. Auf Anskars GigaBlue testen, bevor eine IPK im Updatekanal veröffentlicht wird.

Die funktionsfähige, aber auf einen einzelnen Receiver abgestimmte Testversion ist **kein allgemeines Release**.
