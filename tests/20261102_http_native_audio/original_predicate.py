def _efua_vu_remote_audio_trial(player):
    try:
        info = getattr(player, 'playback_info', None) or {}
        item = getattr(player, 'item', None) or {}
        if info.get('local_file') or str(item.get('Id') or item.get('id') or '').startswith('local:'):
            return False
        ref = player.session.nav.getCurrentlyPlayingServiceReference()
        if ref is None or int(ref.type) != 4097:
            return False
        if not str(getattr(player, 'stream_url', '') or '').lower().startswith(('http://', 'https://')):
            return False
        machine = ''
        try:
            from Components.SystemInfo import BoxInfo
            machine = str(BoxInfo.getItem('machinebuild') or BoxInfo.getItem('model') or '').lower()
        except Exception:
            pass
        if not machine:
            try:
                from boxbranding import getMachineBuild
                machine = str(getMachineBuild() or '').lower()
            except Exception:
                pass
        if machine not in ('vuduo4kse', 'duo4kse'):
            return False
        return bool(_efa2_enabled(player) and not _efa3_audio_compat_codec(player))
    except Exception:
        return False
