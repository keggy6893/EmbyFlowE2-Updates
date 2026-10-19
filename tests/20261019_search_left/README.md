# Receiver test: marine blue search, keyboard left

The existing `EmbyFlowDisneySearchScreen` is replaced with a six-column alphabetic keyboard on the left, three visible recent searches underneath, and four larger posters on the right. Background remains `#0C1827`; accent and focus are cyan. Characters, umlauts, numbers, space, deletion, history persistence, filters, async result validation and image cache remain available.

Navigation: up/down moves between keyboard rows; right at a row edge enters results. Left from the first result returns to typing. Down from the keyboard action row enters history; up returns. History scrolls through the existing eight entries. Right/left traverses all returned results, loading the next four-poster page as needed. Blue cycles type filters; yellow deletes a character or selected history item. OK opens the exact selected result.

`build.py` reproducibly creates `EmbyFlowE2_2026101901.py` from the published 2026101805 baseline and `install-search-left-test.py`. The installer replaces only the search class in the receiver's existing Python plugin; other local patches and account settings are retained. It saves a timestamped backup, syntax checks before replacement and restarts Enigma2 only after a successful install. It does not install packages. Current public update manifests are deliberately unchanged pending receiver rendering and navigation verification. The new artifact retains the baseline application version, since this is a local search test, not an update release.

Validation:

```
python3 tests/20261019_search_left/build.py
python3 -m unittest discover -s tests/20261019_search_left -p 'test_*.py' -v
```

The tests execute the real class with Enigma2 UI doubles: alphabet/action reachability, numeric keyboard relocation, history paging/load/delete, exact selection across all 18 results, stale query rejection, filter cycling, timer shutdown and scaled focus borders at HD. Installer tests check that AST changes are confined to the search class, installed backups preserve the old source and local appended patches, and a repeated install does nothing. They cannot validate an actual receiver's font rendering, poster decoding or remote keymap. Those remain receiver checks at 1920×1080 and 1280×720.
