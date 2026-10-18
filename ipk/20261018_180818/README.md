# EmbyFlowE2 clean IPK

Build 2026101804. Timestamp Europe/Berlin: 20261018_180818.

Contains plugin, blank legacy account defaults and packaged runtime resources. No receiver accounts, login INI, settings, cache, logs, downloads or bot credentials. The existing package treats emby_config.py as a conffile; installed settings are not reset. No automatic GUI restart.

Four helper modules are available only as bytecode from the verified VU basis. The pre-install guard requires Python ABI 2b0e0d0a and rejects a mismatch before installation. Architecture all does not imply compatibility with all Python versions. Receiver installation has not been tested.

Verified: original package/resource hashes, public release hash, exactly two resource-path changes, syntax, archive round-trip, empty account defaults and image integrity.
