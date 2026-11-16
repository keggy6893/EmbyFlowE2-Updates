"""Strict tar.gz adapter for the proposed modular EmbyFlowE2 update.

DEVELOPMENT ONLY. This is not plugged into the receiver's installed updater.
The existing RC26.9 tar.gz path accepts only three fixed files (including PNGs).
For modular releases this adapter handles Python-only files, requiring a trusted
v2 manifest with per-file digests, and passes them to the existing crash-
recoverable installer. No arbitrary archive paths or symlinks are accepted.
"""
import hashlib
import io
import tarfile

from transactional_bundle import BundleError
from update_coordinator import MAX_PAYLOAD_BYTES, apply_release, parse_manifest

PREFIX = "EmbyFlowE2/"
MAX_ARCHIVE_BYTES = 35 * 1024 * 1024


def pack_archive(manifest, files):
    """Create deterministic development tarball for manifest-controlled files."""
    expected = parse_manifest(manifest)
    if set(files) != set(expected):
        raise BundleError("Archive files and manifest do not match")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name in sorted(expected):
            data = files[name]
            if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != expected[name]:
                raise BundleError("Bad archive input: " + name)
            info = tarfile.TarInfo(PREFIX + name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise BundleError("Archive too large")
    return result


def unpack_verified_archive(archive_bytes, manifest, archive_sha256=None):
    """Validate entire archive before changing the receiver's plugin directory.

    Authenticity is the caller's responsibility: manifest and optional archive
    hash must come from an independently trusted, pinned release descriptor.
    """
    expected = parse_manifest(manifest)
    if not isinstance(archive_bytes, bytes) or len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise BundleError("Invalid or oversized archive")
    if archive_sha256 is not None:
        if not isinstance(archive_sha256, str) or len(archive_sha256) != 64:
            raise BundleError("Invalid archive SHA256")
        if hashlib.sha256(archive_bytes).hexdigest() != archive_sha256.lower():
            raise BundleError("Archive SHA256 mismatch")
    files = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            for member in archive:
                # The development format contains only regular files; not even
                # directories, PAX headers, links, devices or extra metadata.
                if not member.isfile() or not member.name.startswith(PREFIX):
                    raise BundleError("Unexpected archive member")
                name = member.name[len(PREFIX):]
                if name not in expected or name in files:
                    raise BundleError("Unknown or repeated archive file: " + name)
                total += member.size
                if member.size < 0 or total > MAX_PAYLOAD_BYTES:
                    raise BundleError("Archive expands beyond permitted size")
                reader = archive.extractfile(member)
                if reader is None:
                    raise BundleError("Missing archive payload")
                data = reader.read(member.size + 1)
                if len(data) != member.size:
                    raise BundleError("Archive file length mismatch")
                if hashlib.sha256(data).hexdigest() != expected[name]:
                    raise BundleError("Archive file SHA256 mismatch: " + name)
                try:
                    compile(data, name, "exec", dont_inherit=True)
                except (SyntaxError, ValueError, TypeError) as exc:
                    raise BundleError("Invalid Python source: " + name) from exc
                files[name] = data
    except (OSError, EOFError, tarfile.TarError) as exc:
        raise BundleError("Malformed tar.gz archive") from exc
    if set(files) != set(expected):
        raise BundleError("Archive missing required files")
    return files


def install_modular_archive(root, archive_bytes, manifest, *, archive_sha256=None):
    """Transactionally apply a validated archive; see startup recovery requirements."""
    files = unpack_verified_archive(archive_bytes, manifest, archive_sha256)
    return apply_release(root, manifest, files)
