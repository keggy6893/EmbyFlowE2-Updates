# V3 receiver test: empty subtitle downloads

The user reported that installed build 2026101702 still left subtitles off. The receiver error explicitly said `Leere Untertiteldatei; Leere Untertiteldatei`. This is a failed download, not proof of a missing/unsupported subtitle track or a solved selection problem.

This separate test installer replaces only the subtitle GET helper and adds fallback URL candidates. Subtitle files use fresh guarded Requests sessions instead of the metadata pool/cache, with normal compression negotiation. One additional request is allowed after an empty HTTP 200 or disconnected connection. TLS certificate errors and HTTP authentication/rate-limit responses are not retried by the helper. Existing server pause enforcement remains active through the guarded Requests wrapper. The worker retains its SRT validation, 8 MiB check and generation cancellation.

If the old Items routes fail, the same item/source/stream is tried on the Videos routes already used by older text subtitle code in this repository. No fallback to a different/full subtitle track is performed. No video transcoding or PGS support is added. A server that supplies no subtitle content on any route will still fail visibly.

Six tests cover empty-then-success, bounded empty retries, TLS/auth/rate-limit handling, URL hostname preservation, full original worker/real HTTP download with empty legacy routes followed by a valid Videos SRT, and repeat installation refusal. Full plugin compilation and byte-identical backup were verified separately. These fixtures test handling of the observed error; they do not prove the receiver's server will respond identically. Receiver validation remains pending.

The installer requires V2, backs up plugin.py and replaces it atomically. Existing layout changes are preserved. Restart the GUI and reopen the film after installation. Diagnostic `/tmp/embyflow_ut_v3.jsonl` contains only time, attempt number, status, byte count and result kind; it excludes URLs, hostnames, IDs, subtitle text and credentials.

At the user's explicit request, the rcdev auto-update channel now supplies V3 as build 2026101703. Receiver validation remains pending; publication is not a claim that the reported server-side behavior is resolved.
