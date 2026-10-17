# V4 request parity test for affected 4K playback

Receiver diagnostics established: source found, German forced SubRip stream index 3 selected, manual selection false, loading became true and remained true after nine seconds. No completed V3 download record was found. The user confirms the exact same 4K film has working automatic subtitles in e2-emby-client.

Reference comparison: e2-emby-client `EmbyPlayer.loadAndParseSubs` uses a plain Requests GET with API key in the URL and timeout 15, without the additional Emby Authorization/Token headers or forced Connection: close. V4 tests that request profile using the existing query API-key parameter and the existing guarded Requests wrapper. It removes custom subtitle request headers, uses connect/read timeouts of 5/15 seconds, preserves TLS verification and records request start, response, timeout and connection error without URLs or credentials. A read timeout is not repeated on the same route. Existing V3 empty/disconnect retries and fallback paths remain. Existing subtitle selection/rendering is unchanged.

This is a controlled receiver test, not proof the request headers caused the server behavior. A 15-second read timeout bounds inactivity per read, not total download duration. Multiple candidate paths can still take longer than 15 seconds overall. No PGS support or claim of all-film compatibility is added.

Eight local tests cover minimal authenticated request options, empty retries, TLS/auth/rate-limit handling, timeout/start diagnostics, missing API key rejection, host-preserving route generation, real HTTP fallback/download with the original player worker, and repeat refusal. Full-plugin compilation and exact backup were verified. The HTTP fixture intentionally distinguishes the request profiles; it is not a reproduction of the user's private server.

Requires V3/build 2026101703. Backs up and atomically patches plugin.py; existing runtime tracing and layout remain. Restart GUI and reopen the exact 4K film without manual subtitle selection. Inspect `/tmp/embyflow_ut_v3.jsonl` if it still fails. Auto-update remains on V3 pending receiver results.
