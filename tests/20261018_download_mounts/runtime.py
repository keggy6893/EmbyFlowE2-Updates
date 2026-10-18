# EMBYFLOW_NUMBERED_DOWNLOAD_MOUNTS_V1
import os as _efmount_os
import re as _efmount_re


def _efmount_entries(writable=True):
    try:
        names = _efmount_os.listdir('/media')
        root_device = _efmount_os.stat('/').st_dev
    except OSError:
        return []
    names = [name for name in names if _efmount_re.fullmatch(r'(hdd|usb)[0-9]*', name)]
    names.sort(key=lambda name: (0 if name.startswith('hdd') else 1,
                                int(_efmount_re.search(r'[0-9]+$', name).group())
                                if _efmount_re.search(r'[0-9]+$', name) else -1))
    result, seen = [], set()
    for name in names:
        mount = '/media/' + name
        real = _efmount_os.path.realpath(mount)
        try:
            if real == '/' or not _efmount_os.path.ismount(real):
                continue
            device = _efmount_os.stat(real).st_dev
            if device == root_device or device in seen:
                continue
            if writable and (not _efmount_os.access(real, _efmount_os.W_OK)
                             or _efmount_os.statvfs(real).f_flag & _efmount_os.ST_RDONLY):
                continue
            seen.add(device)
            result.append((mount, real))
        except OSError:
            continue
    return result


def _efdl_targets():
    return _efmount_entries(True)


_efmount_choice_before = _efdl_choice_text


def _efdl_choice_text(entry):
    mount = str(entry[0])
    if _efmount_re.fullmatch(r'/media/(hdd|usb)[0-9]*', mount):
        # The mount name does not reliably identify physical HDD versus USB.
        return 'Speicher · ' + mount.rsplit('/', 1)[-1], mount, mount + '/movie/EmbyFlow'
    return _efmount_choice_before(entry)


def _eflib_roots():
    roots = []
    for mount, real in _efmount_entries(False):
        root = _efmount_os.path.join(real, 'movie', 'EmbyFlow')
        if _efmount_os.path.realpath(root) != root or not _efmount_os.path.isdir(root):
            continue
        roots.append((root, mount.rsplit('/', 1)[-1]))
    return roots
