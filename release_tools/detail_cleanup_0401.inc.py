# EMBYFLOW_DETAIL_IMAGES_CLEANUP_TEST1
_efclean_states = {}

def _efclean_collect():
    for key, state in list(_efclean_states.items()):
        if not state['closed']:
            continue
        if _efimg3_active is not None and _efimg3_active.get('item_id') == state['item_id']:
            continue
        for path in state['paths']:
            if any(other is not state and not other['closed'] and path in other['paths']
                   for other in _efclean_states.values()):
                continue
            for filename in (path, path + '.tmp'):
                try:
                    os.unlink(filename)
                    _efimg3_log('Detailbild entfernt: ' + os.path.basename(filename))
                except OSError:
                    pass
        _efclean_states.pop(key, None)

def _efclean_write(screen, path, content):
    with _efimg3_lock:
        state = _efclean_states.get(id(screen))
        if state is None or state['closed']:
            return False
        if path not in state['allowed']:
            raise ValueError('Unerwarteter Detailbildpfad')
        state['paths'].add(path)
        with open(path + '.tmp', 'wb') as handle:
            handle.write(content)
        os.replace(path + '.tmp', path)
        return True

_efclean_init_before = EmbyFlowDetailScreen.__init__
def _efclean_init(self, session, data, *args, **kwargs):
    data = data or {}
    item_id = str(data.get('id') or data.get('Id') or '').strip()
    allowed = tuple('/tmp/embyflow_detail_%s_%s_%s.jpg' % (kind, os.getpid(), item_id)
                    for kind in ('poster', 'backdrop'))
    state = {'item_id': item_id, 'closed': False, 'paths': set(), 'allowed': allowed}
    key = id(self)
    with _efimg3_lock:
        _efclean_states[key] = state
    try:
        _efclean_init_before(self, session, data, *args, **kwargs)
    except Exception:
        with _efimg3_lock:
            state['closed'] = True
            _efclean_collect()
        raise
    def closed():
        with _efimg3_lock:
            state['closed'] = True
            _efclean_collect()
    self.onClose.append(closed)
EmbyFlowDetailScreen.__init__ = _efclean_init

_efclean_stop_before = EmbyFlowMoviePlayer.stop_player_poster_loader
def _efclean_stop(self, *args, **kwargs):
    try:
        return _efclean_stop_before(self, *args, **kwargs)
    finally:
        with _efimg3_lock:
            _efclean_collect()
EmbyFlowMoviePlayer.stop_player_poster_loader = _efclean_stop
