# EMBYFLOW_THEME_VOLUME_V1
# Shared ownership across grid music, local theme videos and Emby details.
config.embyflow.theme_volume = ConfigSelection(
    default="20", choices=[(str(n), "%d %%" % n) for n in range(0, 101, 5)])

_EMBYFLOW_THEME_VOLUME_STATE = None


def _embyflow_theme_volume_limit():
    try:
        return max(0, min(100, int(config.embyflow.theme_volume.value)))
    except (ValueError, TypeError):
        return 20


def _embyflow_theme_volume_release(screen):
    global _EMBYFLOW_THEME_VOLUME_STATE
    state = _EMBYFLOW_THEME_VOLUME_STATE
    if state is None or state["owner"] is not screen:
        return
    _EMBYFLOW_THEME_VOLUME_STATE = None
    try:
        state["timer"].stop()
    finally:
        state["control"].setVolume(state["left"], state["right"])


def _embyflow_theme_volume_play(screen, reference):
    global _EMBYFLOW_THEME_VOLUME_STATE
    from enigma import eDVBVolumecontrol
    control = eDVBVolumecontrol.getInstance()
    old = _EMBYFLOW_THEME_VOLUME_STATE
    # Preserve the normal volume only once, even if another theme takes over.
    left = old["left"] if old is not None else control.getVolume()
    right = old["right"] if old is not None else left
    if old is not None:
        old["timer"].stop()
    timer = eTimer()
    state = dict(owner=screen, ref=reference.toString(), control=control,
                 left=left, right=right, timer=timer)
    _EMBYFLOW_THEME_VOLUME_STATE = state

    def cap_volume():
        if _EMBYFLOW_THEME_VOLUME_STATE is not state:
            return
        current = screen.session.nav.getCurrentlyPlayingServiceReference()
        if current is None or current.toString() != state["ref"]:
            _embyflow_theme_volume_release(screen)
            return
        # Never increase a manually lowered volume. A service-specific volume
        # plugin may raise it after playService; cap that while we own the theme.
        limit = _embyflow_theme_volume_limit()
        current_volume = control.getVolume()
        if current_volume > limit:
            control.setVolume(limit, limit)
        timer.start(200, True)

    try:
        timer.callback.append(cap_volume)
    except AttributeError:
        state["connection"] = timer.timeout.connect(cap_volume)
    try:
        level = min(control.getVolume(), _embyflow_theme_volume_limit())
        control.setVolume(level, level)
        result = screen.session.nav.playService(reference)
        if type(result) is int and result != 0:
            raise RuntimeError("Theme service could not start")
        cap_volume()
        return result
    except Exception:
        _embyflow_theme_volume_release(screen)
        raise


class EmbyFlowThemeVolumeScreen(Screen):
    skin = scale_skin("""
    <screen name="EmbyFlowThemeVolumeScreen" position="center,center" size="1100,540"
        flags="wfNoBorder" backgroundColor="#07111F">
        <eLabel position="0,0" size="1100,4" backgroundColor="#26E6FF" />
        <eLabel text="Hintergrundmusik" position="50,35" size="1000,60"
            font="Regular;40" foregroundColor="#26E6FF" transparent="1" />
        <widget name="value" position="50,125" size="1000,110" font="Regular;76"
            foregroundColor="#FFFFFF" transparent="1" halign="center" />
        <widget name="help" position="50,260" size="1000,150" font="Regular;28"
            foregroundColor="#FFFFFF" transparent="1" halign="center" />
        <eLabel text="ROT / EXIT: Abbrechen" position="50,450" size="470,45"
            font="Regular;28" foregroundColor="#FFFFFF" transparent="1" />
        <eLabel text="GRÜN / OK: Speichern" position="560,450" size="490,45"
            font="Regular;28" foregroundColor="#42E66B" transparent="1" halign="right" />
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.level = _embyflow_theme_volume_limit()
        self["value"] = Label("")
        self["help"] = Label("LINKS / RECHTS: in 5-%-Schritten ändern\n"
                             "Obergrenze für Musik und ThemeVideos.\n"
                             "0 % = stumm. Film und TV behalten ihre Lautstärke.")
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {"left": lambda: self.change(-5), "right": lambda: self.change(5),
             "ok": self.save_level, "green": self.save_level,
             "cancel": self.close, "red": self.close}, -1)
        self.change(0)

    def change(self, amount):
        self.level = max(0, min(100, self.level + amount))
        self["value"].setText("%d %%" % self.level)

    def save_level(self):
        setting = config.embyflow.theme_volume
        before = setting.value
        try:
            setting.value = str(self.level)
            setting.save()
            configfile.save()
        except Exception:
            setting.value = before
            setting.save()
            self["help"].setText("Speichern fehlgeschlagen. Bitte erneut versuchen.")
            return
        self.close(True)


def _embyflow_open_theme_volume(self):
    self.session.open(EmbyFlowThemeVolumeScreen)


# Blue opens the clearly labelled music control in advanced settings.
EmbyFlowAdvancedSettingsNeon.skin = EmbyFlowAdvancedSettingsNeon.skin.replace(
    'text="HILFE"', 'text="MUSIK"')
EmbyFlowAdvancedSettingsNeon.show_help = _embyflow_open_theme_volume
