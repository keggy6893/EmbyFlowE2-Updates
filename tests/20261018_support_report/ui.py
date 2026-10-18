# EMBYFLOW_SUPPORT_REPORT_V1
import xml.etree.ElementTree as _efsr_xml


def _efsr_flag(name):
    try:
        value = getattr(config.embyflow, name).value
        return value if type(value) is bool else None
    except Exception:
        return None


def _efsr_create(self):
    try:
        flags = {'Debug': _efsr_flag('debug'),
                 'Downloads': _efsr_flag('movie_download_enabled'),
                 'Trailer': _efsr_flag('trailers_enabled'),
                 'LCD-Zeitfix': '_eflcd_bridge' in globals()}
        report = _efsr_collect(PLUGIN_VERSION, PLUGIN_UPDATE_BUILD, flags)
        path = '/etc/enigma2/embyflow_support.txt'
        _efsr_write(path, report)
    except Exception:
        self.session.open(MessageBox, 'Supportbericht konnte nicht gespeichert werden.', type=MessageBox.TYPE_ERROR)
        return
    self.session.open(MessageBox,
        'Supportbericht erstellt.\n\n'
        'Per FTP herunterladen:\n' + path + '\n\n'
        'Enthaelt Box, Image, Pluginversion und Fehlerarten.\n'
        'Keine Rohlogs oder Zugangsdaten.\n'
        'Es wurde nichts versendet.', type=MessageBox.TYPE_INFO)


_efsr_music_before = EmbyFlowAdvancedSettingsNeon.show_help


def _efsr_extras(self):
    def selected(choice):
        if not choice:
            return
        if choice[1] == 'support':
            _efsr_create(self)
        elif choice[1] == 'music':
            _efsr_music_before(self)
    self.session.openWithCallback(selected, ChoiceBox,
        title='EmbyFlow - Extras',
        list=[('Musik', 'music'), ('Supportbericht erstellen', 'support')])


_efsr_skin = _efsr_xml.fromstring(EmbyFlowAdvancedSettingsNeon.skin)
for _efsr_node in _efsr_skin.iter('eLabel'):
    if _efsr_node.get('text') == 'MUSIK':
        _efsr_node.set('text', 'EXTRAS')
EmbyFlowAdvancedSettingsNeon.skin = _efsr_xml.tostring(_efsr_skin, encoding='unicode')
EmbyFlowAdvancedSettingsNeon.show_help = _efsr_extras
