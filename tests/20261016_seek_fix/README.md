# E2 seek hotfix 2026101602

The burst commit called the legacy relative-seek implementation after the safe chapter/restart path returned False. This bypassed that path's rejection and could issue another native seek or legacy service restart. The fallback has been removed. Unsupported seeking displays an overlay message and leaves the existing service running.

The burst timer retains pending input while a previous jump settles for three seconds. Native seekTo checks isCurrentlySeekable when available. No changes to EOF failure counting, HTTP server guards, static-stream policy, or authentication.

Validation: full Python compilation and five isolated regression tests covering coalescing, rejected-seek fallback, settling, target clamping, and unseekable backend rejection. No receiver validation yet. This fixes an unsafe fallback, not every backend's container-seeking limitations.
