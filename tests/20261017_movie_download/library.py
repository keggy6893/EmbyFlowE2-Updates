# EMBYFLOW_DOWNLOAD_LIBRARY_LOCAL_V11
# Offline library. No provider calls, download reservations or deletion actions.
import os as _eflib_os
import stat as _eflib_stat
import json as _eflib_json
import threading as _eflib_threading
import queue as _eflib_queue
import re as _eflib_re

_EFLIB_MOUNTS = ('/media/hdd', '/media/usb')
_EFLIB_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.ts', '.m2ts', '.mov', '.webm')


def _eflib_roots():
    roots = []
    seen = set()
    for mount in _EFLIB_MOUNTS:
        real = _eflib_os.path.realpath(mount)
        if real == '/' or real in seen or not _eflib_os.path.ismount(real):
            continue
        root = _eflib_os.path.join(real, 'movie', 'EmbyFlow')
        if _eflib_os.path.realpath(root) != root or not _eflib_os.path.isdir(root):
            continue
        seen.add(real)
        roots.append((root, 'HDD' if mount.endswith('/hdd') else 'USB'))
    return roots


def _eflib_text(value):
    return ' '.join(str(value or '').split())[:240]


def _eflib_metadata(path):
    try:
        fd = _eflib_os.open(path + '.embyflow.json', _eflib_os.O_RDONLY | _eflib_os.O_NOFOLLOW | _eflib_os.O_NONBLOCK)
        with _eflib_os.fdopen(fd, 'r') as handle:
            info = _eflib_os.fstat(handle.fileno())
            if not _eflib_stat.S_ISREG(info.st_mode) or info.st_size > 8192:
                return {}
            value = _eflib_json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def _efdl_library_save(path, item, data):
    # Optional descriptive sidecar. Never turn a finished transfer into failure.
    import tempfile
    temporary = None
    try:
        metadata = {key: item[key] for key in ('Name', 'Type', 'SeriesName', 'ParentIndexNumber', 'IndexNumber') if key in item}
        metadata['Name'] = _eflib_text(metadata.get('Name') or data.get('title') or data.get('Name'))
        directory = _eflib_os.path.dirname(path)
        fd, temporary = tempfile.mkstemp(prefix='.embyflow-meta-', dir=directory)
        with _eflib_os.fdopen(fd, 'w') as handle:
            _eflib_json.dump(metadata, handle, ensure_ascii=True)
            handle.flush()
            _eflib_os.fsync(handle.fileno())
        _eflib_os.replace(temporary, path + '.embyflow.json')
    except Exception:
        pass
    finally:
        if temporary and _eflib_os.path.exists(temporary):
            _eflib_os.unlink(temporary)


def _eflib_scan():
    entries, errors = [], []
    for root, storage in _eflib_roots():
        try:
            with _eflib_os.scandir(root) as iterator:
                for entry in iterator:
                    if entry.name.startswith('.') or _eflib_os.path.splitext(entry.name)[1].lower() not in _EFLIB_EXTENSIONS:
                        continue
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if not _eflib_stat.S_ISREG(info.st_mode) or info.st_size <= 0:
                            continue
                        metadata = _eflib_metadata(entry.path)
                        stem = _eflib_os.path.splitext(entry.name)[0]
                        # Existing downloader appends item ID and media source ID.
                        fallback = _eflib_re.sub(r'_(?:[0-9]+|[a-fA-F0-9]{32})_(?:[a-fA-F0-9-]{32,48}|[0-9]+)$', '', stem)
                        title = _eflib_text(metadata.get('Name') or fallback)
                        if metadata.get('Type') == 'Episode':
                            number = ''
                            try:
                                number = 'S%02dE%02d' % (int(metadata['ParentIndexNumber']), int(metadata['IndexNumber']))
                            except (KeyError, TypeError, ValueError):
                                pass
                            title = ' · '.join(filter(None, (_eflib_text(metadata.get('SeriesName')), number, title)))
                        entries.append(dict(path=entry.path, root=root, storage=storage, title=title,
                                            size=info.st_size, mtime=info.st_mtime, metadata=metadata))
                    except OSError:
                        continue
        except OSError:
            errors.append(storage + ': Ordner nicht lesbar')
    entries.sort(key=lambda entry: (-entry['mtime'], entry['title'].casefold(), entry['path']))
    return entries, errors


def _eflib_valid(entry):
    path = entry['path']
    return (any(root == entry['root'] for root, storage in _eflib_roots())
            and _eflib_os.path.dirname(path) == entry['root']
            and _eflib_os.path.realpath(path) == path
            and _eflib_os.path.isfile(path)
            and _eflib_os.stat(path).st_size == entry['size'])


class EmbyFlowDownloadsScreen(Screen):
    ROWS = 5

    def __init__(self, session):
        nodes = []
        def label(name, x, y, w, h, font=24, color='#DCE5EC', align='left'):
            nodes.append('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="%s" backgroundColor="#0B1522" transparent="1" halign="%s" valign="center" zPosition="3" />' % (name, sx(x), sy(y), sx(w), sy(h), sy(font), color, align))
        def picture(name, x, y, w, h):
            nodes.append('<widget name="%s" position="%d,%d" size="%d,%d" alphatest="blend" zPosition="1" />' % (name, sx(x), sy(y), sx(w), sy(h)))
        picture('panel', 0, 0, 1420, 880)
        label('brand', 40, 24, 800, 32, 23, '#26DFF5')
        label('count', 1070, 24, 310, 32, 22, '#98A9B9', 'right')
        label('heading', 40, 76, 1340, 52, 36)
        label('status', 40, 132, 1340, 60, 22, '#98A9B9')
        for slot in range(self.ROWS):
            y = 210 + slot * 108
            picture('card%d' % slot, 40, y, 1340, 96)
            label('title%d' % slot, 64, y + 6, 1120, 40, 27)
            label('meta%d' % slot, 64, y + 49, 1120, 32, 21, '#98A9B9')
            label('storage%d' % slot, 1150, y + 23, 130, 42, 23, '#98A9B9', 'right')
        label('path', 40, 766, 1340, 42, 20, '#98A9B9')
        label('hint', 40, 824, 1340, 32, 22, '#98A9B9')
        self.skin = '<screen name="EmbyFlowDownloadsScreen" position="center,center" size="%d,%d" flags="wfNoBorder" backgroundColor="#FF000000">%s</screen>' % (sx(1420), sy(880), ''.join(nodes))
        Screen.__init__(self, session)
        self['panel'] = Pixmap()
        for name, text in (('brand', 'EMBYFLOW E2'), ('count', ''), ('heading', 'Downloads'), ('status', ''), ('path', ''), ('hint', 'OK  Abspielen    ↑↓  Auswahl    BLAU  Aktualisieren    EXIT  Zurück')):
            self[name] = Label(text)
        for slot in range(self.ROWS):
            self['card%d' % slot] = Pixmap()
            for prefix in ('title', 'meta', 'storage'):
                self[prefix + str(slot)] = Label('')
        self.entries, self.index, self.loading, self.closed = [], 0, False, False
        self.results = _eflib_queue.Queue()
        self.timer = eTimer()
        self.timer.callback.append(self.poll)
        self['actions'] = ActionMap(['OkCancelActions', 'DirectionActions', 'ColorActions'],
                                   {'ok': self.play, 'cancel': self.close, 'red': self.close,
                                    'blue': self.reload, 'up': self.up, 'down': self.down}, -2)
        self.onLayoutFinish.append(self.layout)
        self.onClose.append(self.cleanup)

    def layout(self):
        _efdl_style_apply(self['panel'], 'panel')
        self.reload()

    def cleanup(self):
        self.closed = True
        self.timer.stop()

    def reload(self):
        if self.loading or self.closed:
            return
        self.loading = True
        self['status'].setText('HDD und USB werden durchsucht …')
        self.timer.start(200, False)
        _eflib_threading.Thread(target=self.scan_worker, daemon=True).start()

    def scan_worker(self):
        try:
            result = _eflib_scan()
        except Exception:
            result = ([], ['Downloadordner konnte nicht gelesen werden.'])
        if not self.closed:
            self.results.put(result)

    def poll(self):
        if self.closed:
            return
        try:
            entries, errors = self.results.get_nowait()
        except _eflib_queue.Empty:
            return
        old = self.entries[self.index]['path'] if self.entries else None
        self.entries, self.loading = entries, False
        self.index = next((i for i, entry in enumerate(entries) if entry['path'] == old), 0)
        self.timer.stop()
        self['status'].setText(' · '.join(errors) if errors else ('Filme und Folgen · lokal auf HDD und USB' if entries else 'Keine fertigen Downloads gefunden.\nSpeicherorte: /media/hdd/movie/EmbyFlow und /media/usb/movie/EmbyFlow'))
        self.draw()

    def draw(self):
        start = self.index // self.ROWS * self.ROWS
        self['count'].setText('%d / %d Dateien' % (self.index + 1 if self.entries else 0, len(self.entries)))
        for slot in range(self.ROWS):
            position = start + slot
            names = ['card%d' % slot, 'title%d' % slot, 'meta%d' % slot, 'storage%d' % slot]
            if position >= len(self.entries):
                for name in names:
                    self[name].hide()
                continue
            entry = self.entries[position]
            for name in names:
                self[name].show()
            _efdl_style_apply(self[names[0]], 'selected_plain' if position == self.index else 'normal_plain')
            self[names[1]].setText(entry['title'])
            kind = {'Episode': 'Folge', 'Movie': 'Film'}.get(entry['metadata'].get('Type'), 'Video')
            size = ('%.2f GiB' % (entry['size'] / 2**30)).replace('.', ',')
            self[names[2]].setText('%s · %s · %s' % (kind, _eflib_os.path.splitext(entry['path'])[1][1:].upper(), size))
            self[names[3]].setText(entry['storage'])
        self['path'].setText(self.entries[self.index]['path'] if self.entries else '')

    def up(self):
        if self.entries:
            self.index = max(0, self.index - 1)
            self.draw()

    def down(self):
        if self.entries:
            self.index = min(len(self.entries) - 1, self.index + 1)
            self.draw()

    def play(self):
        if self.loading or not self.entries:
            return
        entry = self.entries[self.index]
        try:
            if not _eflib_valid(entry):
                raise ValueError('Datei oder Datenträger nicht mehr verfügbar. BLAU: Aktualisieren')
            path, title = entry['path'], entry['title']
            probe = _embyflow_v21b_probe_local_file(path) or {}
            local_id = 'local:' + path
            metadata = entry['metadata']
            source = dict(Id=local_id, Path=path, MediaStreams=probe.get('media_streams') or [], DefaultSubtitleStreamIndex=-1)
            if probe.get('default_audio_index') is not None:
                source['DefaultAudioStreamIndex'] = probe['default_audio_index']
            item = dict(Id=local_id, id=local_id, Name=title, title=title,
                        Type=metadata.get('Type') or 'Movie', type=metadata.get('Type') or 'Movie',
                        Path=path, MediaSources=[source])
            position, runtime = get_embyflow_local_resume(local_id)
            item['RunTimeTicks'] = int(probe.get('runtime_ticks') or runtime or 0)
            if position > 0:
                item['PlaybackPositionTicks'] = int(position)
                item['UserData'] = dict(PlaybackPositionTicks=int(position))
            info = dict(url=path, item=item, local_file=True, local_probe=probe,
                        local_service_type=4097, local_extension=_eflib_os.path.splitext(path)[1].lower(),
                        play_session_id='local-' + str(uuid4()))
            reference = eServiceReference(4097, 0, path)
            reference.setName(title)
            _open_embyflow_player_now(self.session, reference, title, path, info)
        except Exception as error:
            self['status'].setText(str(error) if isinstance(error, ValueError) else 'Lokale Wiedergabe konnte nicht gestartet werden.')


_EFLIB_NAV_BUILD = EmbyFlowE2Screen._direct_nav_build_entries_ref12
_EFLIB_NAV_ACTIVATE = EmbyFlowE2Screen._direct_nav_activate_ref12
_EFLIB_SIDE_BUILD = EmbyFlowE2Screen._sidebar_main_rows_v24
_EFLIB_SIDE_ACTIVATE = EmbyFlowE2Screen._sidebar_activate_main_v24
_EFLIB_HOME_INIT = EmbyFlowE2Screen.__init__


def _eflib_enabled():
    return bool(config.embyflow.movie_download_enabled.value)


def _eflib_nav_entries(entries):
    entries = [entry for entry in entries if entry[1].get('_direct_action_ref12') != 'downloads']
    if not _eflib_enabled():
        return entries
    index = next((i + 1 for i, entry in enumerate(entries) if entry[1].get('_direct_action_ref12') == 'updates'), len(entries))
    entries.insert(index, ('Downloads', {'_direct_action_ref12': 'downloads'}))
    return entries


def _eflib_nav_build(self):
    return _eflib_nav_entries(_EFLIB_NAV_BUILD(self))


def _eflib_nav_activate(self):
    index = self.direct_nav_cursor_ref12
    entries = self.direct_nav_entries_ref12
    if 0 <= index < len(entries) and entries[index][1].get('_direct_action_ref12') == 'downloads':
        if _eflib_enabled():
            return self.session.open(EmbyFlowDownloadsScreen)
        return
    return _EFLIB_NAV_ACTIVATE(self)


def _eflib_side_build(self):
    entries = list(_EFLIB_SIDE_BUILD(self))
    if _eflib_enabled():
        index = next((i + 1 for i, entry in enumerate(entries) if entry[1].get('_sidebar_name') == 'side_updates'), len(entries))
        entries.insert(index, ('Downloads', {'_sidebar_kind': 'main', '_sidebar_name': 'side_downloads'}))
    return entries


def _eflib_side_activate(self, name):
    if name == 'side_downloads':
        if _eflib_enabled():
            return self.session.open(EmbyFlowDownloadsScreen)
        return
    return _EFLIB_SIDE_ACTIVATE(self, name)


def _eflib_setting_refresh(self):
    old = getattr(self, 'direct_nav_entries_ref12', None)
    if old is None:
        return
    new = _eflib_nav_entries(old)
    if new == old:
        return
    cursor = int(getattr(self, 'direct_nav_cursor_ref12', 0))
    current = old[cursor] if 0 <= cursor < len(old) else None
    self.direct_nav_entries_ref12 = new
    self.direct_nav_cursor_ref12 = next((i for i, entry in enumerate(new) if entry == current), 0)
    self._direct_nav_refresh_ref12()


def _eflib_home_init(self, *args, **kwargs):
    _EFLIB_HOME_INIT(self, *args, **kwargs)
    self.onShow.append(self.downloads_setting_refresh)


EmbyFlowE2Screen._direct_nav_build_entries_ref12 = _eflib_nav_build
EmbyFlowE2Screen._direct_nav_activate_ref12 = _eflib_nav_activate
EmbyFlowE2Screen._sidebar_main_rows_v24 = _eflib_side_build
EmbyFlowE2Screen._sidebar_activate_main_v24 = _eflib_side_activate
EmbyFlowE2Screen.downloads_setting_refresh = _eflib_setting_refresh
EmbyFlowE2Screen.__init__ = _eflib_home_init

# The async /Views refresh and expanding Films/Series rebuild via this global.
# Keep Downloads present across both paths, not just the first Home render.
if '_embyflow_nav_groups_v30_transform' in globals():
    _EFLIB_NAV_TRANSFORM = _embyflow_nav_groups_v30_transform

    def _eflib_nav_transform(entries):
        return _eflib_nav_entries(_EFLIB_NAV_TRANSFORM(entries))

    _embyflow_nav_groups_v30_transform = _eflib_nav_transform
