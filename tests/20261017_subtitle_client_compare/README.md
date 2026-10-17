# Read-only comparison of actual receiver subtitle requests

V4 receiver output showed four consecutive 15-second subtitle timeouts. The user confirms the same 4K film displays automatic subtitles in e2-emby-client. Request header parity did not resolve the issue. Selection diagnostics had already shown the correct German forced text stream selected and loading true.

This diagnostic installer wraps EmbyFlow's subtitle GET and e2-emby-client's `loadAndParseSubs`, preserving call arguments, return values and exceptions. It fingerprints the request's credential-free origin, item ID and MediaSource ID and records stream index, route and result timing in `/tmp/emby_subtitle_compare.jsonl`. Tokens, queries, URL userinfo, actual hosts, URLs and subtitle text are neither recorded nor hashed.

Both source files must be available and supported; all patches are compiled and originals backed up before either is replaced. Ambiguous e2 client discovery aborts. This modifies both plugins only for observation. Restore their printed `.vor-ut-vergleich-<timestamp>` backups and restart GUI to remove tracing.

Validation: full source compilation against build 2026101703 and the reference client, matching fingerprints with different secret query values, secret filtering, and unchanged wrapped arguments/return values. Receiver comparison remains pending. No automatic update change.

After GUI restart, reopen the same 4K film in EmbyFlow and wait 20 seconds, stop playback, then start the exact same version in e2-emby-client until subtitles are visible. Read the last 20 JSONL records. Different fingerprints establish differing request identities, not necessarily which one is wrong; matching identities require investigating transport/runtime differences next.
