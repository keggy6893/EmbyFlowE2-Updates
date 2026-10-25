# Local subtitle menu key-consumption correction V3

The receiver user clarified that playback stops on opening the local subtitle
menu, before any track is selected. OSD previously showed PAUSE. V1 and V2
returned session.openWithCallback's dialog object from _eflu_open.

The actual Enigma2 dispatch contract matters here:
- Components/ActionMap.py ActionMap.action passes a non-None action response
  through, otherwise it returns integer 1.
- lib/python/python.cpp ePython::call returns integer Python results, but maps
  non-integer Python results to integer 0 (unhandled).
- lib/actions/action.cpp snapshots the key's callback list, then invokes more
  callbacks while the previous result is zero. Parent callbacks can already be
  queued when a new dialog unbinds the parent's ActionMaps.
- The plugin's combined ActionMap binds both ColorActions.yellow and
  MediaPlayerActions.pause. Standard data/keymap.xml maps KEY_YELLOW on release
  to both of these actions in their respective contexts.

Thus the local menu can open and then let the queued Pause action run. This is
an application return-value bug; no decoder behavior needs to be inferred from
an advancing clock. The test reproduces this dispatch with a dialog object and
queued Pause handler. V3 calls openWithCallback and explicitly returns integer
1, preventing the Pause handler. It retains V2's standard subtitle parent.

No forced unpause, change to user pause state, seek, audio change, server call,
engine swap or broad ActionMap replacement is added. The remote subtitle
handler is unchanged. The return correction is inside the local menu only.

21 tests cover key dispatch plus native selection regressions. Installer tests
cover exact V1/V2 module replacement with byte-identical surrounding code,
backups, repeat no-op, rejected unknown edits and failed replace recovery.
The native dispatcher behavior was checked against OpenATV source; these are
not a substitute for the receiver retest. No full-release manifest is changed.
