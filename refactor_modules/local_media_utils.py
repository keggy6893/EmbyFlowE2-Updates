"""Pure local-media display helpers extracted verbatim from RC26.9.

No Enigma2 dependencies. Only formatting; never modifies media files.
"""
import os


def embyflow_local_human_size(value):
    try:
        size = float(value or 0)
        units = ("B", "KB", "MB", "GB", "TB")
        unit_index = 0

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        if unit_index == 0:
            return "%d %s" % (int(size), units[unit_index])

        return "%.1f %s" % (size, units[unit_index])
    except Exception:
        return ""


def embyflow_local_clean_title(path):
    try:
        base = os.path.basename(str(path or ""))
        title = os.path.splitext(base)[0]
        return title.replace("_", " ").strip() or base
    except Exception:
        return str(path or "")
