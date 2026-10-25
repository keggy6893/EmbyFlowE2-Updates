# Nachtraeglicher EMC-Quellcodevergleich, 25.10.2026

Dieser Vergleich wurde **erst nach Veroeffentlichung von 2026102502** gemacht.
Er ersetzt keinen direkten Wiedergabe-/Anzeigenvergleich auf einem Receiver.
Die bisherigen 80 lokalen Tests sind kein solcher Hardwarevergleich.

## Referenzen

EMC-Quellstand `23dc058965d4743b1d884a6dae63054c047ef2d4`:

- [InfoBarSupport.py](https://github.com/oe-mirrors/EnhancedMovieCenter/blob/23dc058965d4743b1d884a6dae63054c047ef2d4/src/InfoBarSupport.py):
  `InfoBarSupport` erbt und initialisiert Enigma2 `InfoBarAudioSelection`.
- [EMCMediaCenter.py](https://github.com/oe-mirrors/EnhancedMovieCenter/blob/23dc058965d4743b1d884a6dae63054c047ef2d4/src/EMCMediaCenter.py):
  `setAudioTrack()` liest `getTrackInfo(i).getLanguage()` und
  `getCurrentTrack()`. Das ist die automatische Spurwahl, nicht der Nachweis
  einer identischen Infobar-Anzeige.
- `__osdAudioInfoAvail()` liest fuer den speziellen Audio-OSD-Pfad ein
  `sUser + 6`-Informationstupel und setzt `audioLabel`. Auch dieser Pfad darf
  nicht mit unserer Infobar oder allen Skin-Konvertern gleichgesetzt werden.

OpenATV Enigma2-Quellstand `be4ff6f5136ffecc43f7f24582d630707fb947e5`:

- [InfoBarGenerics.py](https://github.com/openatv/enigma2/blob/be4ff6f5136ffecc43f7f24582d630707fb947e5/lib/python/Screens/InfoBarGenerics.py):
  `InfoBarAudioSelection.audioSelection()` oeffnet `Screens.AudioSelection`.
- [AudioSelection.py](https://github.com/openatv/enigma2/blob/be4ff6f5136ffecc43f7f24582d630707fb947e5/lib/python/Screens/AudioSelection.py):
  `fillList()` liest den ausgewaehlten Index mit `getCurrentTrack()` und die
  Sprache jeder Spur mit `getTrackInfo(x).getLanguage()`. Ein
  `evUpdatedInfo`-Handler aktualisiert die Auswahlliste.

## Vergleich mit EmbyFlow 2026102502

Der neue EmbyFlow-Zusatz verwendet dieselbe native Track-Informationsschnittstelle
fuer die Sprachkennung. EmbyFlows bisherige Infobar speicherte ihren Text; der
Zusatz aktualisiert sie beim Oeffnen und ueber ihren bestehenden sichtbaren
Updatezyklus. Er uebernimmt nicht den kompletten Enigma2-Audioauswahldialog und
veraendert weder Spurwahl noch Playback.

Unterschiede bleiben: EmbyFlow hat eine eigene Infobar und eigene Metadaten.
Bei unbekannter nativer Sprachkennung bleibt die Metadaten-Anzeige erhalten.
Damit ist nicht nachgewiesen, dass jeder Receiver/Skin dieselbe Sprache wie
EMC zeigt. Der genaue auf Anskars Box installierte EMC-/Enigma2-Stand ist hier
nicht festgestellt. Direkter Vergleich auf SF8008 Supreme/DreamOne steht aus.

**Ergebnis:** Quellcodevergleich der verwendeten Schnittstellen erfolgt.
EMC-Hardwarevergleich und Bestaetigung von Anskars Anzeigefehler stehen aus.
