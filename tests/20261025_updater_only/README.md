# One-time installed updater repair without py_compile (updater only)

Published builds 2026102301 and 2026102402 already validate source with the
built-in compile(). However an installed older updater can fail at its own
`import py_compile` before installing the fixed update. This standalone tool
bootstraps that old updater without replacing the rest of the installed plugin
or installing optional Python packages. It is not a general plugin update.

Only `_embyflow_update_install_plugin` is inspected. The one module import is
replaced with a nested built-in source-check helper. All five doraise=True
syntax checks remain at their original staging/install/rollback locations, with
identical path arguments and propagated exceptions. SHA256, download rules,
backups and rollback are untouched. The tool rejects unknown structures and
argument changes. Known previously repaired public/local forms are no-ops.
It uses re rather than depending on the optional ast package on the receiver.

Before changing a receiver it obtains the download lock, checks symlink/file
status, source syntax, free space and unchanged bytes, creates an exclusive
backup, writes/fsyncs a same-directory staging file, stops the GUI, rechecks
source and atomically replaces. Finally it cleans staging and restarts the GUI.
No plugin source is executed by the syntax checker. No .pyc is manually made.

Seven tests validate the Sept19 and Oct18 old updater fixtures, syntax failure,
no execution of checked source, missing-file errors, unknown structures and
idempotence/public/local repaired forms. Outside-updater AST is preserved.
Installer tests in temporary files exercise the complete Sept19 fixture,
backup contents, repeat no-op and failed replacement with init mocked.
This is not a confirmed receiver installation until the user supplies output.

Run the pinned standalone script in the affected receiver's SSH/Telnet shell.
The tool contains no receiver IP and can also be transported via SSH from
PowerShell. Never assume an installed extension directory is a Git checkout.
Repair does not change the plugin version identity or install the full public
payload; in particular private local features remain as they were.
