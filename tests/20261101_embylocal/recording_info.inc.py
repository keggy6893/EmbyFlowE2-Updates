# EMBYFLOW_LOCAL_RECORDING_INFO_V1_BEGIN
import re as _elfm_re
import time as _elfm_time
_ELFM_INIT_BEFORE = EmbyFlowLocalMediaScreen.__init__
_ELFM_REFRESH_BEFORE = EmbyFlowLocalMediaScreen.refresh


def _elfm_read(path):
    try:
        with open(path, 'rb') as handle:
            raw = handle.read(65536)
        try:
            return raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            return raw.decode('latin-1')
    except OSError:
        return ''


def _elfm_native(path):
    data = {}
    try:
        # Same local service-information entry point used by EMC ServiceEvent.
        # No playback and no duration probing of the TS stream is requested.
        from enigma import eServiceCenter, eServiceReference
        ref = eServiceReference(1, 0, path)
        info = eServiceCenter.getInstance().info(ref)
        event = info and info.getEvent(ref)
        if event:
            for key, method in (('title', 'getEventName'), ('short', 'getShortDescription'),
                                ('long', 'getExtendedDescription'), ('begin', 'getBeginTime'),
                                ('epg_seconds', 'getDuration')):
                try:
                    data[key] = getattr(event, method)()
                except Exception:
                    pass
    except Exception:
        pass
    return data


def _elfm_signature(path):
    stem = os.path.splitext(path)[0]
    signature = []
    for name in (path+'.meta', path+'.eit', stem+'.eit', path+'.txt', stem+'.txt'):
        try:
            stat = os.stat(name)
            signature.append((stat.st_mtime_ns, stat.st_size))
        except OSError:
            signature.append(None)
    return tuple(signature)


def _elfm_data(screen, entry):
    path = str(entry.get('path') or '')
    original = str(entry.get('name') or '')
    stem = os.path.splitext(os.path.basename(path or original))[0]
    data = dict(title=stem or original, overview='', channel='', date='', runtime='',
                technical=str(entry.get('meta') or ''), path=path)
    if entry.get('kind') != 'file' or not screen.safe_within_root(path):
        data['title'] = original
        return data
    signature = _elfm_signature(path)
    cache = getattr(screen, '_elfm_cache', {})
    cached = cache.get(path)
    if cached and cached[0] == signature:
        return cached[1]
    parts = _elfm_re.match(r'^(\d{8})\s+(\d{4})\s*-\s*(.+?)\s*-\s*(.+)$', stem)
    if parts:
        day, clock, channel, title = parts.groups()
        try:
            fields = (int(day[:4]), int(day[4:6]), int(day[6:]), int(clock[:2]), int(clock[2:]))
            stamp = _elfm_time.localtime(_elfm_time.mktime(fields+(0,0,0,-1)))
            if tuple(stamp[:5]) == fields:
                data['date'] = _elfm_time.strftime('%d.%m.%Y · %H:%M', stamp)
        except (ValueError, OverflowError, OSError):
            pass
        data.update(title=title.replace('_', ' '), channel=channel)
    meta = _elfm_read(path+'.meta').splitlines()
    native = _elfm_native(path) if path.lower().endswith('.ts') else {}
    try:
        eit = embyflow_local_v7_read_eit(path) or {}
    except Exception:
        eit = {}
    data['title'] = str(native.get('title') or eit.get('event_name') or
                        (meta[1].strip() if len(meta)>1 else '') or data['title']).strip()
    chosen = data['title'].replace('\x86', '').replace('\x87', '')
    if chosen.lower().endswith('.ts'):
        chosen = chosen[:-3]
    prefixed = _elfm_re.match(r'^\d{8}\s+\d{4}\s*-\s*.+?\s*-\s*(.+)$', chosen)
    data['title'] = (prefixed.group(1) if prefixed else chosen).replace('_', ' ')
    short = str(native.get('short') or eit.get('short_text') or
                (meta[2].strip() if len(meta)>2 else '') or '').strip()
    long_text = str(native.get('long') or eit.get('extended_text') or '').strip()
    if not long_text:
        long_text = (_elfm_read(path+'.txt') or _elfm_read(os.path.splitext(path)[0]+'.txt')).strip()
    if not long_text:
        meta_description = meta[2].strip() if len(meta)>2 else ''
        if meta_description and meta_description not in (short, data['title']):
            long_text = meta_description
        try:
            saved = _els_read_cache()
            if not long_text and saved.get('path') == path:
                long_text = str(saved.get('overview') or '')
        except Exception:
            pass
    paragraphs = []
    if short and short.casefold() != data['title'].casefold() and short not in long_text:
        paragraphs.append(short)
    if long_text:
        paragraphs.append(long_text)
    if not paragraphs:
        try:
            saved = _els_read_cache()
            if saved.get('path') == path and saved.get('overview'):
                paragraphs.append(str(saved['overview']))
        except Exception:
            pass
    data['overview'] = '\n\n'.join(paragraphs)[:16384]
    try:
        if not data['date']:
            begin = native.get('begin') or (meta[3] if len(meta)>3 else 0)
            if int(begin or 0)>0:
                data['date'] = _elfm_time.strftime('%d.%m.%Y · %H:%M', _elfm_time.localtime(int(begin)))
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    # Enigma2 .ts.meta line 6 is a length in 90-kHz PTS; line 7 is size,
    # not a channel name. An EIT duration describes the broadcast event.
    try:
        measured = int(meta[5] or 0)//90000 if len(meta)>5 else 0
    except (ValueError, TypeError):
        measured = 0
    try:
        epg = int(native.get('epg_seconds') or eit.get('runtime_seconds') or 0)
        if measured>0:
            data['runtime'] = '%d Min.' % max(1, measured//60)
        elif epg>0:
            data['runtime'] = 'EPG: %d Min.' % max(1, epg//60)
    except (ValueError, TypeError):
        pass
    if len(cache)>=128:
        cache = {}
    cache[path] = (signature, data)
    screen._elfm_cache = cache
    return data


def _elfm_init(screen, *args, **kwargs):
    _ELFM_INIT_BEFORE(screen, *args, **kwargs)
    screen._elfm_cache = {}
    screen['selection_overview'] = Label('')
    screen['recording_info_actions'] = ActionMap(['InfobarEPGActions'],
        {'showEventInfo': screen._elfm_info}, -30)


def _elfm_refresh(screen):
    _ELFM_REFRESH_BEFORE(screen)
    if getattr(screen, '_elfm_source', None) is not screen.entries:
        screen._elfm_source = screen.entries
        screen._elfm_cache = {}
    entries = _elfg_entries(screen)
    for slot in range(9):
        position = screen.offset+slot
        if position<len(entries) and entries[position].get('kind') == 'file':
            data = _elfm_data(screen, entries[position])
            screen['row%d' % slot].setText(data['title'])
            screen['meta%d' % slot].setText('\n'.join(x for x in
                (data['channel'] or data['technical'], data['date']) if x))
    entry = screen.selected_entry()
    if not entry:
        screen['selection_overview'].setText('')
        return
    data = _elfm_data(screen, entry)
    screen['selection_name'].setText(_elfg_wrap(data['title'], 30))
    screen['selection_meta'].setText('\n'.join(x for x in
        (data['channel'], data['date'], data['technical'], data['runtime']) if x))
    screen['selection_overview'].setText(data['overview'] or
        ('Keine Inhaltsangabe lokal gespeichert.' if entry.get('kind') == 'file' else 'Ordner mit OK öffnen.'))


class EmbyFlowLocalRecordingInfo(Screen):
    skin = scale_skin('''<screen name="EmbyFlowLocalRecordingInfo" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#0C1827">
    <eLabel position="0,0" size="1920,1080" backgroundColor="#0C1827" zPosition="0" />
    <widget name="info_title" position="90,60" size="1740,110" font="Bold;38" foregroundColor="#F4F7FB" transparent="1" zPosition="3" />
    <widget name="body" position="90,200" size="1740,730" font="Regular;28" foregroundColor="#DCE5EE" transparent="1" zPosition="3" />
    <eLabel text="ROT / EXIT Zurück     ↑↓ Inhaltsangabe blättern" position="90,990" size="1700,40" font="Regular;24" foregroundColor="#55B8E2" transparent="1" zPosition="3" />
    </screen>''')
    def __init__(self, session, data):
        Screen.__init__(self, session)
        self['info_title'] = Label(data['title'])
        body = '\n'.join(x for x in (data['channel'], data['date'], data['technical'], data['runtime']) if x)
        body += '\n\n' + (data['overview'] or 'Keine Inhaltsangabe lokal gespeichert.')
        self['body'] = ScrollLabel(body) if ScrollLabel else Label(body)
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'], {
            'cancel': self.close, 'red': self.close, 'ok': self.close,
            'up': self.page_up, 'left': self.page_up, 'down': self.page_down, 'right': self.page_down}, -1)
        self.onLayoutFinish.append(lambda: self['body'].setText(body))
    def page_up(self):
        if ScrollLabel:
            self['body'].pageUp()
    def page_down(self):
        if ScrollLabel:
            self['body'].pageDown()


def _elfm_info(screen):
    entry = screen.selected_entry()
    if entry:
        return screen.session.open(EmbyFlowLocalRecordingInfo, _elfm_data(screen, entry))


_ELFM_SKIN = _ELFG_SKIN
for _elfm_name in ('title', 'path', 'summary', 'status', 'page', 'filter_hint'):
    _ELFM_SKIN = _ELFM_SKIN.replace('name="'+_elfm_name+'" ', 'name="'+_elfm_name+'" zPosition="3" ', 1)
_ELFM_SKIN = _ELFM_SKIN.replace('size="510,550"', 'size="510,675"')
_ELFM_SKIN = _ELFM_SKIN.replace('size="255,32" font="Regular;20"', 'size="255,46" font="Regular;18"')
_ELFM_SKIN = _ELFM_SKIN.replace('name="selection_meta" position="1470,365" size="320,70" font="Regular;23"',
    'name="selection_meta" position="1470,335" size="320,112" font="Regular;20"')
_ELFM_SKIN = _ELFM_SKIN.replace('name="selection_path" position="1350,585" size="440,170" font="Regular;22"',
    'name="selection_path" position="1350,812" size="440,90" font="Regular;19"')
_ELFM_SKIN = _ELFM_SKIN.replace('text="OK Auswählen"', 'text="INFO Inhalt"')
_ELFM_SKIN = _ELFM_SKIN.replace('</screen>', '<widget name="selection_overview" position="1350,572" size="440,220" font="Regular;22" foregroundColor="#DCE5EE" transparent="1" zPosition="3" /></screen>')
EmbyFlowLocalMediaScreen.skin = scale_skin(_ELFM_SKIN)
EmbyFlowLocalMediaScreen.__init__ = _elfm_init
EmbyFlowLocalMediaScreen.refresh = _elfm_refresh
EmbyFlowLocalMediaScreen._elfm_info = _elfm_info
# EMBYFLOW_LOCAL_RECORDING_INFO_V1_END
