# EMBYFLOW_CURRENT_IMAGES_LOCALTEST_V3
import threading as _efimg3_threading
import shutil as _efimg3_shutil
_efimg3_lock = _efimg3_threading.RLock()
_efimg3_states = {}
_efimg3_active = None
_efimg3_dir = '/tmp/EmbyFlow'

def _efimg3_log(message):
    try:
        with open('/tmp/embyflow_images.log', 'a') as handle:
            handle.write(time.strftime('%H:%M:%S') + ' | TEST3 ' + message + '\n')
    except Exception:
        pass

def _efimg3_clear():
    for name in ('Poster.jpg', 'Backdrop.jpg', 'Poster.jpg.new', 'Backdrop.jpg.new'):
        try:
            os.unlink(os.path.join(_efimg3_dir, name))
        except OSError:
            pass

def _efimg3_copy(state, path, name):
    global _efimg3_active
    if not os.path.isfile(path):
        return False
    try:
        if os.path.getsize(path) > 16 * 1024 * 1024:
            return False
        with open(path, 'rb') as handle:
            if handle.read(2) != b'\xff\xd8':
                return False
        with _efimg3_lock:
            if _efimg3_active is not state or state['cancel'].is_set():
                return False
            destination = os.path.join(_efimg3_dir, name)
            _efimg3_shutil.copyfile(path, destination + '.new')
            os.replace(destination + '.new', destination)
            _efimg3_log(name + ' bereitgestellt')
        return True
    except Exception as error:
        _efimg3_log(name + ': ' + str(error))
        return False

def _efimg3_worker(state, sources):
    pending = dict(sources)
    for attempt in range(60):
        if state['cancel'].is_set():
            return
        for name, paths in list(pending.items()):
            for path in paths:
                if _efimg3_copy(state, path, name):
                    pending.pop(name, None)
                    break
        if not pending:
            return
        if state['cancel'].wait(0.5):
            return
    _efimg3_log('Kein vorhandenes JPEG: ' + ', '.join(sorted(pending)))

_efimg3_load_before = EmbyFlowMoviePlayer.load_player_poster_async
_efimg3_stop_before = EmbyFlowMoviePlayer.stop_player_poster_loader

def _efimg3_load(self, *args, **kwargs):
    global _efimg3_active
    result = _efimg3_load_before(self, *args, **kwargs)
    try:
        item_id = str(getattr(self, 'item_id', '') or '')
        source_id = str(self.player_poster_source_id() or item_id)
        # Only immutable paths and cancellation state go to the worker.
        if not item_id or not source_id:
            return result
        if any('/' in value or '\\' in value or '..' in value for value in (item_id, source_id)):
            return result
        sources = {'Poster.jpg': [str(getattr(self, 'player_poster_ready_path', '') or ''),
                     CACHE_DIR + '/player/' + source_id + '_primary_v1.jpg',
                     '/tmp/embyflow_detail_poster_%s_%s.jpg' % (os.getpid(), item_id)],
                   'Backdrop.jpg': ['/tmp/embyflow_detail_backdrop_%s_%s.jpg' % (os.getpid(), item_id)]}
        for image_id in dict.fromkeys((item_id, source_id)):
            for prefix in ('grid', 'step1'):
                sources['Backdrop.jpg'].append('%s/grid_backdrops/%s_%s_%sx%s.jpg' %
                    (CACHE_DIR, prefix, image_id, int(SCREEN_W or 1920), int(SCREEN_H or 1080)))
        state = {'cancel': _efimg3_threading.Event()}
        with _efimg3_lock:
            if _efimg3_active is not None:
                _efimg3_active['cancel'].set()
            os.makedirs(_efimg3_dir, exist_ok=True)
            _efimg3_clear()
            _efimg3_states[id(self)] = state
            _efimg3_active = state
        thread = _efimg3_threading.Thread(target=_efimg3_worker, args=(state, sources), name='EmbyFlowCurrentImages3')
        thread.daemon = True
        thread.start()
        _efimg3_log('Export gestartet')
    except Exception as error:
        _efimg3_log('Export nicht gestartet: ' + str(error))
    return result

def _efimg3_stop(self, *args, **kwargs):
    global _efimg3_active
    try:
        with _efimg3_lock:
            state = _efimg3_states.pop(id(self), None)
            if state is not None:
                state['cancel'].set()
                if _efimg3_active is state:
                    _efimg3_active = None
                    _efimg3_clear()
                    _efimg3_log('Wiedergabe beendet: Bilder entfernt')
    except Exception as error:
        _efimg3_log('Aufraeumen: ' + str(error))
    return _efimg3_stop_before(self, *args, **kwargs)

EmbyFlowMoviePlayer.load_player_poster_async = _efimg3_load
EmbyFlowMoviePlayer.stop_player_poster_loader = _efimg3_stop
_efimg3_clear()
