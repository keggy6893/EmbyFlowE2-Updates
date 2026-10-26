# EMBYFLOW_LOCAL_FOLDER_GRID_V1_BEGIN
_ELFG_INIT_BEFORE = EmbyFlowLocalMediaScreen.__init__
_ELFG_ASSETS = os.path.join(PLUGIN_PATH, 'assets', 'local_folder_grid_20261026')


def _elfg_priority(entry):
    if entry.get('kind') != 'dir':
        return 20
    name = str(entry.get('name') or '').casefold()
    groups = (('filme', 'movies', 'videos'), ('serien', 'series', 'tv shows'),
              ('aufnahmen', 'recordings', 'movie'), ('dokumentationen', 'dokus', 'docs'),
              ('konzerte', 'musik', 'music'), ('kinder', 'kids'))
    return next((i for i, names in enumerate(groups) if name in names), 10)


def _elfg_entries(screen):
    source = screen.entries
    show_all = bool(getattr(screen, '_elfg_show_all', False))
    if (getattr(screen, '_elfg_cache_source', None) is source and
            getattr(screen, '_elfg_cache_all', None) == show_all):
        return screen._elfg_cache_view
    entries = sorted(list(source or []),
                     key=lambda e: (_elfg_priority(e), str(e.get('name') or '').casefold()))
    if not show_all:
        media = [e for e in entries if _elfg_priority(e) < 10 or e.get('kind') == 'file']
        if any(e.get('kind') == 'dir' and _elfg_priority(e) < 10 for e in entries):
            entries = media
    screen._elfg_cache_source = source
    screen._elfg_cache_all = show_all
    screen._elfg_cache_view = entries
    return entries


def _elfg_wrap(text, width=34):
    # Break long paths/names without another optional Python package.
    value = str(text or '')
    return '\n'.join(value[i:i+width] for i in range(0, len(value), width))


def _elfg_icon(screen, name, kind):
    try:
        widget = screen[name]
        path = os.path.join(_ELFG_ASSETS, 'folder.png' if kind == 'dir' else 'video.png')
        widget.instance.setPixmapFromFile(path)
        widget.instance.setScale(1)
        widget.show()
    except Exception:
        pass


def _elfg_init(screen, *args, **kwargs):
    _ELFG_INIT_BEFORE(screen, *args, **kwargs)
    screen._elfg_show_all = False
    screen._elfg_path = screen.current_path
    for name in ('summary', 'selection_name', 'selection_meta', 'selection_path', 'filter_hint', 'page'):
        screen[name] = Label('')
    screen['selection_icon'] = Pixmap()
    for slot in range(9):
        screen['tile_bg%d' % slot] = Label(' ')
        screen['tile_icon%d' % slot] = Pixmap()
    screen['actions'] = ActionMap(['OkCancelActions', 'DirectionActions', 'ColorActions'], {
        'ok': screen.open_selected, 'green': screen.open_selected,
        'cancel': screen.go_back, 'red': screen.go_back,
        'blue': screen.start_scan, 'yellow': screen._elfg_toggle,
        'left': screen._elfg_left, 'right': screen._elfg_right,
        'up': screen.move_up, 'down': screen.move_down,
    }, -1)


def _elfg_selected(screen):
    entries = _elfg_entries(screen)
    if not entries:
        return None
    screen.selected_index = max(0, min(screen.selected_index, len(entries)-1))
    return entries[screen.selected_index]


def _elfg_refresh(screen):
    if getattr(screen, '_elfg_path', None) != screen.current_path:
        screen._elfg_path = screen.current_path
        screen._elfg_show_all = False
        screen.selected_index = 0
    entries = _elfg_entries(screen)
    count = len(entries)
    screen.selected_index = max(0, min(screen.selected_index, max(0, count-1)))
    screen.offset = screen.selected_index // 9 * 9
    screen['title'].setText(screen.title_text)
    screen['path'].setText(screen.current_path)
    folders = sum(e.get('kind') == 'dir' for e in entries)
    screen['summary'].setText('%d Ordner · %d Videos' % (folders, count-folders))
    hidden = max(0, len(screen.entries)-count)
    screen['filter_hint'].setText('Gelb: Medienansicht' if screen._elfg_show_all else
                                  ('Gelb: Alle Ordner (%d weitere)' % hidden if hidden else 'Gelb: Alle Ordner'))
    screen['page'].setText('%d / %d' % (screen.selected_index//9+1, max(1, (count+8)//9)))
    for slot in range(9):
        index = screen.offset + slot
        names = ('tile_bg%d' % slot, 'tile_icon%d' % slot, 'row%d' % slot, 'meta%d' % slot)
        if index >= count:
            for name in names:
                screen[name].hide()
            continue
        entry = entries[index]
        for name in names:
            screen[name].show()
        screen['row%d' % slot].setText(str(entry.get('name') or ''))
        screen['meta%d' % slot].setText(str(entry.get('meta') or ''))
        _elfg_icon(screen, 'tile_icon%d' % slot, entry.get('kind'))
    entry = _elfg_selected(screen)
    if entry:
        screen['selection_name'].setText(_elfg_wrap(entry.get('name'), 30))
        screen['selection_meta'].setText(str(entry.get('meta') or ''))
        screen['selection_path'].setText(_elfg_wrap(entry.get('path'), 36))
        _elfg_icon(screen, 'selection_icon', entry.get('kind'))
        slot = screen.selected_index % 9
        try:
            screen['focus_bg'].instance.move(EFP(90 + slot % 3 * 395, 250 + slot // 3 * 190))
            screen['focus_bg'].instance.resize(EFS(375, 170))
            screen['focus_bg'].show()
        except Exception:
            pass
    else:
        for name in ('selection_name', 'selection_meta', 'selection_path'):
            screen[name].setText('')
        screen['selection_icon'].hide()
        screen['focus_bg'].hide()


def _elfg_move(screen, delta):
    if getattr(screen, 'scan_loading', False):
        return
    entries = _elfg_entries(screen)
    if entries:
        target = screen.selected_index + delta
        if abs(delta) == 3 and not 0 <= target < len(entries):
            return
        screen.selected_index = max(0, min(target, len(entries)-1))
        screen.refresh()


def _elfg_toggle(screen):
    screen._elfg_show_all = not screen._elfg_show_all
    screen.selected_index = 0
    screen.refresh()


def _elfg_up(screen):
    _elfg_move(screen, -3)


def _elfg_down(screen):
    _elfg_move(screen, 3)


def _elfg_left(screen):
    _elfg_move(screen, -1)


def _elfg_right(screen):
    _elfg_move(screen, 1)


def _elfg_page_up(screen):
    _elfg_move(screen, -9)


def _elfg_page_down(screen):
    _elfg_move(screen, 9)


EmbyFlowLocalMediaScreen.skin = scale_skin(_ELFG_SKIN)
EmbyFlowLocalMediaScreen.VISIBLE_ROWS = 9
EmbyFlowLocalMediaScreen.__init__ = _elfg_init
EmbyFlowLocalMediaScreen.selected_entry = _elfg_selected
EmbyFlowLocalMediaScreen.refresh = _elfg_refresh
EmbyFlowLocalMediaScreen.move_up = _elfg_up
EmbyFlowLocalMediaScreen.move_down = _elfg_down
EmbyFlowLocalMediaScreen.page_up = _elfg_page_up
EmbyFlowLocalMediaScreen.page_down = _elfg_page_down
EmbyFlowLocalMediaScreen._elfg_left = _elfg_left
EmbyFlowLocalMediaScreen._elfg_right = _elfg_right
EmbyFlowLocalMediaScreen._elfg_toggle = _elfg_toggle
# EMBYFLOW_LOCAL_FOLDER_GRID_V1_END
