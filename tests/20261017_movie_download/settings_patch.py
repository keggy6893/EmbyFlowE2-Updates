"""Add one scrolling setting to column two of the existing settings screen."""
def patch_settings(source):
    start = source.index('# EMBYFLOW_BUFFER_SCROLL_SETTINGS_V3')
    end = source.index('# Runtime status comes directly', start)
    block = source[start:end]
    replacements = [
        ('_efbs_focuses = (2, 3, 4, 7, 8, 9, 10, 11)', '_efbs_focuses = (2, 3, 4, 7, 8, 9, 10, 11, 12)'),
        ("'Stabilitätsmodus', '15-Sekunden-Puffertest')", "'Stabilitätsmodus', '15-Sekunden-Puffertest', 'Film-Download (lokaler Test)')"),
        ('    self._efbs_offset = 0', '    self._efbs_offset = 0\n    self._efdl_enabled = bool(config.embyflow.movie_download_enabled.value)'),
        ('1–6 / 8', '1–6 / 9'),
        ('min(2, max(index - 5, min(self._efbs_offset, index)))', 'min(len(_efbs_focuses) - 6, max(index - 5, min(self._efbs_offset, index)))'),
        ("    for name in _efbs_fields + ('middle_help',):", "    values.append(('> ' if self.focus == 12 else '') + ('AN' if self._efdl_enabled else 'AUS') + (' <' if self.focus == 12 else ''))\n    for name in _efbs_fields + ('middle_help',):"),
        ("'%s  %d–%d / 8  %s'", "'%s  %d–%d / 9  %s'"),
        ('self._efbs_offset < 2', 'self._efbs_offset < len(_efbs_focuses) - 6'),
        ("    if self.focus == 10:\n        self['left_help']", "    if self.focus == 12:\n        self['left_help'].setText('Film-Download im Detailmenü anbieten. Ziel HDD/USB, Größe vor Start bestätigen. Standard AUS. Mit Grün speichern.')\n    elif self.focus == 10:\n        self['left_help']"),
        ('order = (0, 6, 1, 2, 3, 4, 7, 8, 9, 10, 11, 5)', 'order = (0, 6, 1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 5)'),
        ('def _efbs_toggle(self):\n    if self.focus == 10:', 'def _efbs_toggle(self):\n    if self.focus == 12:\n        self._efdl_enabled = not self._efdl_enabled\n        self.refresh_all()\n    elif self.focus == 10:'),
        ('        _efb_test_next = self._efbs_test', '        _efb_test_next = self._efbs_test\n        config.embyflow.movie_download_enabled.value = bool(self._efdl_enabled)\n        config.embyflow.movie_download_enabled.save()\n        configfile.save()'),
    ]
    for old, new in replacements:
        if block.count(old) != 1:
            raise ValueError('Einstellungsstelle nicht eindeutig: ' + old)
        block = block.replace(old, new, 1)
    if block.count('self.focus in (10, 11)') != 3:
        raise ValueError('Einstellungsaktionen nicht eindeutig.')
    block = block.replace('self.focus in (10, 11)', 'self.focus in (10, 11, 12)')
    return source[:start] + block + source[end:]
