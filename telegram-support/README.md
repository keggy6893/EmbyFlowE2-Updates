# Telegram support setup: stage 1

Paste `setup-worker.mjs` into the Cloudflare dashboard Worker editor and deploy.
Requires the secret `TELEGRAM_BOT_TOKEN` entered directly in Cloudflare. No token
belongs in this repository. Open the Worker using Visit in its own browser tab.
Send `/support@EmbyFlowSupport6893Bot` in the intended group. The setup form asks
for the bot token in a password field as administrator authentication, compares it
with the Worker secret, and calls getUpdates. Group titles/IDs are returned only
after authentication. Raw updates, personal messages and errors are not returned.
Tokens are not put in URLs or emitted to console. getUpdates is read-only and
uses no offset; this stage does not set a webhook or send Telegram messages.

Group discovery requires a recent update visible to this bot. Existing webhooks
can prevent getUpdates; do not silently delete them. Re-send the bot command if
no relevant updates are found. Missing configuration fails closed.

This is ONLY setup discovery, not the report relay. Automatic client reporting,
explicit opt-in, bounded structured report payloads, duplicate suppression,
rate limiting and authenticated receiver enrollment still need implementation
before enabling reports. The bot token will remain in the Worker.

Run `node --test telegram-support/setup-worker.test.mjs`.
