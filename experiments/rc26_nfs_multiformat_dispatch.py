# RC26 multiformat NFS direct-play design note
# Applies to the tested per-receiver NFS mapping implementation.
# Does NOT make mappings automatic.

NATIVE_TS_EXTENSIONS = (".ts", ".m2ts", ".mts", ".trp")
DIRECT_FILE_EXTENSIONS = NATIVE_TS_EXTENSIONS + (
    ".mkv", ".mp4", ".m4v", ".mov", ".avi",
    ".mpg", ".mpeg", ".vob", ".webm",
)

def local_media_service_type(extension, configured_stream_service_type):
    """Match RC26's existing local-file player dispatch."""
    return 1 if extension.lower() in NATIVE_TS_EXTENSIONS else configured_stream_service_type

# Apply to the NFS path resolver only after:
# 1. An Emby MediaSource Path matches a configured server prefix.
# 2. Its corresponding realpath stays inside the mapped mount root.
# 3. The file exists and can be read.
# 4. The selected MediaSource is unambiguous.
# Then use eServiceReference(service_type, 0, local_path).
# Keep HTTP/Transcoding handling unchanged when no mapping resolves.
