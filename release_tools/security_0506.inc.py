# Securitycheck by Paul — private files and centrally sanitized logs.
def embyflow_sanitize_log_text(value):
    text = str(value)
    # Includes query strings, JSON, dictionary repr and header assignments.
    keys = r'(?:api[_-]?key|access[_-]?token|token|password|pw|x-emby-token|playsessionid|authorization)'
    text = re.sub(r'(?i)([\"\x27]?' + keys + r'[\"\x27]?\s*[:=]\s*)([\"\x27])[^\r\n]*?\2', lambda m: m.group(1) + m.group(2) + '***' + m.group(2), text)
    text = re.sub(r'(?i)(' + keys + r'\s*[:=]\s*)(?![\"\x27])[^&\s,;}]+', r'\1***', text)
    text = re.sub(r'(?i)(https?://)[^\s/@]+:[^\s/@]+@', r'\1***@', text)
    # Exact current secrets also cover otherwise unlabeled exception messages.
    cfg = globals().get('config')
    section = getattr(cfg, 'embyflow', None)
    for key in ('password', 'api_key'):
        secret = str(getattr(getattr(section, key, None), 'value', '') or '')
        if secret:
            text = text.replace(secret, '***')
    return text

class _EmbyFlowSafeLog:
    def __init__(self, handle):
        self.handle = handle
    def write(self, value):
        self.handle.write(embyflow_sanitize_log_text(value))
        return len(value)
    def writelines(self, values):
        for value in values:
            self.write(value)
    def __getattr__(self, name):
        return getattr(self.handle, name)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return self.handle.__exit__(*args)

def _embyflow_private_log(path, mode='a', *args, **kwargs):
    import stat
    directory = '/tmp/embyflow-private-logs'
    try:
        os.mkdir(directory, 0o700)
    except FileExistsError:
        pass
    info = os.lstat(directory)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise OSError('Unsicheres Logverzeichnis')
    os.chmod(directory, 0o700)
    target = os.path.join(directory, os.path.basename(str(path)))
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    flags |= os.O_APPEND if 'a' in mode else 0
    descriptor = os.open(target, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise OSError('Unsichere Logdatei')
        os.fchmod(descriptor, 0o600)
        if 'w' in mode:
            os.ftruncate(descriptor, 0)
        handle = io.open(descriptor, mode, *args, **kwargs)
        descriptor = None
        return _EmbyFlowSafeLog(handle)
    finally:
        if descriptor is not None:
            os.close(descriptor)
