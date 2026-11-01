# EMBYFLOW_LOCAL_TEST_NAV_V1_BEGIN
_EFLOCAL_NAV = EmbyFlowE2Screen._direct_nav_build_entries_ref12
_EFLOCAL_ACTIVATE = EmbyFlowE2Screen._direct_nav_activate_ref12
_EFLOCAL_ASYNC_NAV = _embyflow_nav_groups_v30_transform


def _eflocal_entries(entries):
    rows = list(entries or [])
    if not any(isinstance(row[1], dict) and row[1].get('_direct_action_ref12') == 'local_usb' for row in rows):
        index = next((i for i, row in enumerate(rows) if isinstance(row[1], dict) and row[1].get('_direct_action_ref12') == 'settings'), len(rows))
        rows.insert(index, ('Emby Local', {'_direct_action_ref12': 'local_usb'}))
    return rows


def _eflocal_nav(screen):
    return _eflocal_entries(_EFLOCAL_NAV(screen))


def _eflocal_activate(screen):
    rows = screen.direct_nav_entries_ref12
    index = screen.direct_nav_cursor_ref12
    if 0 <= index < len(rows) and rows[index][1].get('_direct_action_ref12') == 'local_usb':
        return screen.open_local_media_menu()
    return _EFLOCAL_ACTIVATE(screen)


def _eflocal_async_nav(entries):
    return _eflocal_entries(_EFLOCAL_ASYNC_NAV(entries))


EmbyFlowE2Screen._direct_nav_build_entries_ref12 = _eflocal_nav
EmbyFlowE2Screen._direct_nav_activate_ref12 = _eflocal_activate
_embyflow_nav_groups_v30_transform = _eflocal_async_nav
# EMBYFLOW_LOCAL_TEST_NAV_V1_END
