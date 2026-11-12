# RC26.3 Octagon AutoFS V5

Tested on an Octagon SF8008 Supreme with OpenATV 8.0.1. Both logged Skyfall starts used Enigma2 service type 1. The tester reported immediate audio-track switching and later confirmed synchronized playback. One earlier switch caused temporary stuttering.

Apply the patch to the matching RC26.3 test base.

- Base plugin.py SHA-256: f238c634575d77468bb3db165aa964de660c13f85edc268dc5f31ddaf4b79cd1
- Patched plugin.py SHA-256: a7f4aba844d78cea700b8d43fd66113e7bd683ac41cd25ee2b7ad48e52872362

Check applicability with `git -c core.autocrlf=false apply --check octa-autofs-v5.patch`.
