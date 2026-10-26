# EMBYFLOW_LOCAL_SOURCE_PICONS_V1_BEGIN
_ELSI_SHOW_BEFORE = EmbyFlowLocalSourcesScreenV16._show_icon
_ELSI_ASSETS = os.path.join(PLUGIN_PATH, 'assets', 'local_source_picons_20261026')


def _elsi_kind(source):
    source = source if isinstance(source, dict) else {}
    if source.get('id') == '__embyflow_all_media_v1__':
        return 'all'
    mode = str(source.get('mode') or 'mixed').casefold()
    if mode in ('movies', 'series', 'recordings', 'documentary'):
        return mode
    path = str(source.get('path') or '').casefold()
    if '/net/' in path or '/autofs/' in path:
        return 'network'
    return 'drive'


def _elsi_show_icon(screen, widget_name, source):
    try:
        path = os.path.join(_ELSI_ASSETS, _elsi_kind(source) + '.png')
        if not os.path.isfile(path):
            return _ELSI_SHOW_BEFORE(screen, widget_name, source)
        widget = screen[widget_name]
        instance = widget.instance
        if instance is None:
            return _ELSI_SHOW_BEFORE(screen, widget_name, source)
        if widget_name.startswith('card_icon'):
            slot = int(widget_name[len('card_icon'):])
            if 0 <= slot < 5:
                instance.move(EFP(249 + slot * 216, 354))
                instance.resize(EFS(112, 112))
        instance.setPixmapFromFile(path)
        instance.setScale(1)
        widget.show()
        instance.show()
    except Exception:
        return _ELSI_SHOW_BEFORE(screen, widget_name, source)


EmbyFlowLocalSourcesScreenV16._show_icon = _elsi_show_icon
# EMBYFLOW_LOCAL_SOURCE_PICONS_V1_END
