# EMBYFLOW_COMPATIBLE_OFFLINE_DOWNLOAD_TEST_V1
import copy as _efcmp_copy
import os as _efcmp_os

_efcmp_source_before = EmbyFlowLocalDownloadScreen.source_chosen
_efcmp_target_before = EmbyFlowLocalDownloadScreen.target_chosen
_efcmp_transfer_before = EmbyFlowLocalDownloadScreen.transfer
_efcmp_poll_before = EmbyFlowLocalDownloadScreen.poll
_efcmp_text_before = _efdl_choice_text


def _efcmp_source(self, choice):
    if not choice or self.closed:
        return _efcmp_source_before(self, choice)
    source = choice[1]
    if not any(str(s.get('Codec') or '').lower() in ('av1', 'av01')
               for s in source.get('MediaStreams') or [] if s.get('Type') == 'Video'):
        return _efcmp_source_before(self, choice)
    def selected(answer):
        if not answer or self.closed:
            return
        if answer[1] == 'original':
            return _efcmp_source_before(self, choice)
        try:
            compatible = _efcmp_copy.deepcopy(source)
            ticks = int(source.get('RunTimeTicks') or self.item.get('RunTimeTicks') or 0)
            compatible.update(_efcmp_original_id=source['Id'], _efcmp_compatible=True,
                Id=str(source['Id'])[:40] + '-h264', Container='mp4',
                Size=_efcmp_engine.estimate(ticks), _efcmp_ticks=ticks)
            _efcmp_source_before(self, ('HDD-kompatibel H.264/AAC', compatible))
        except Exception:
            self['status'].setText('Kompatibler Download nicht vorbereitbar: Laufzeit oder Version fehlt.')
    self.session.openWithCallback(selected, _EFDLChoice, title='AV1 - Downloadformat',
        description='HDD-kompatibel: Emby erstellt eine vollstaendige MP4-Datei fuer deine Box.',
        access_status='Umwandlung benoetigt den Emby-Server; fertige Datei laeuft offline',
        list=[('HDD-kompatibel: H.264/AAC fuer Offline-Wiedergabe', 'compatible'),
              ('Originaldatei: AV1, auf dieser Box nicht offline abspielbar', 'original')])


def _efcmp_text(entry):
    if isinstance(entry[1], dict) and entry[1].get('_efcmp_compatible'):
        return 'HDD-kompatibel · H.264/AAC', 'Speicherbudget', 'Serverumwandlung · MP4 · maximal Full HD'
    return _efcmp_text_before(entry)


def _efcmp_target(self, choice):
    if not getattr(self, 'source', {}).get('_efcmp_compatible'):
        return _efcmp_target_before(self, choice)
    if not choice or self.closed:
        return self.close()
    try:
        root = choice[1]
        if root not in [real for label, real in _efdl_targets()]:
            raise ValueError('Datentraeger nicht mehr verfuegbar.')
        directory = _efcmp_os.path.join(root, 'movie', 'EmbyFlow')
        _efcmp_os.makedirs(directory, exist_ok=True)
        if (_efcmp_os.path.commonpath([root, _efcmp_os.path.realpath(directory)]) != root
                or _efcmp_os.stat(directory).st_dev != _efcmp_os.stat(root).st_dev):
            raise ValueError('Downloadordner liegt nicht auf dem gewaehlten Datentraeger.')
        _efdl_engine.check_space(directory, self.source['Size'])
        self.target = _efcmp_os.path.join(directory, _efdl_engine.filename(self.item.get('Name', 'Film'), self.item['Id'], self.source))
        summary = ('H.264/AAC · MP4 · maximal Full HD\n'
            'Vollstaendige Datei fuer Offline-Wiedergabe von HDD.\n'
            'Speicherbudget: %.2f GiB plus Reserve; Dateigroesse kann kleiner sein.\n'
            'Keine Untertitel. Ein Platz des Tageslimits wird verwendet.\nZiel: %s' %
            (self.source['Size'] / 2**30, directory))
        self.session.openWithCallback(lambda answer: self.confirmed(bool(answer and answer[1])),
            _EFDLChoice, title='Kompatibel herunterladen?', description=summary,
            access_status='Anbieterfreigabe und Umwandlung werden vor dem Start geprueft',
            confirmation=True, list=[('Abbrechen', False), ('Herunterladen', True)])
    except Exception:
        self.events.put(('error', 'Ziel nicht verfuegbar oder Speicherplatz nicht ausreichend.'))


def _efcmp_transfer(self):
    if not self.source.get('_efcmp_compatible'):
        return _efcmp_transfer_before(self)
    try:
        server, token = self.auth
        if not any(_efcmp_os.path.commonpath([root, _efcmp_os.path.realpath(self.target)]) == root
                   for label, root in _efdl_targets()):
            raise _efcmp_engine.CompatibilityError('Datentraeger nicht mehr verfuegbar.')
        path = _efcmp_engine.download(requests, server, token, self.user, self.item, self.source,
            self.target, self.cancel, lambda done, budget: setattr(self, 'progress', (done, budget)),
            _efdl_engine, AUTH_HEADER,
            permission=lambda: self.events.put(('permission', ('granted', 'Downloadfreigabe: Vor dem Start erneut bestaetigt'))))
        _efdl_library_save(path, self.item, self.data)
        self.events.put(('compatible_done', path))
    except _efdl_engine.DownloadCancelled:
        pass
    except (_efdl_engine.DownloadPermissionDenied, _efdl_engine.DownloadPermissionUnknown) as error:
        self.events.put(('error', str(error)))
    except _efcmp_engine.CompatibilityError as error:
        self.events.put(('error', str(error)))
    except Exception:
        self.events.put(('error', 'Kompatibler Download fehlgeschlagen. Teildatei wird entfernt.'))


def _efcmp_poll(self):
    if self.closed:
        return
    # Translate only this worker's completion event. Other events retain the
    # original GUI handler and quota/permission behavior.
    with self.events.mutex:
        event = self.events.queue[0] if self.events.queue else None
    if event and event[0] == 'compatible_done':
        self.events.get_nowait()
        self.progress = (0, 0)
        self['progress_bar'].setValue(100)
        self['footer'].setText('ROT / EXIT  Schliessen')
        self['status'].setText('Kompatibler Download abgeschlossen:\n%s\n\n'
            'H.264/AAC geprueft. Direkt von HDD offline abspielbar.\n'
            'Keine Untertitel. EXIT: Schliessen' % event[1])
        _efdl_update_quota(self)
        return
    _efcmp_poll_before(self)
    if getattr(self, 'source', {}).get('_efcmp_compatible') and not self.closed:
        done, budget = self.progress
        if budget:
            self['progress_bar'].setValue(min(99, int(done * 100 / budget)))
            self['status'].setText('Kompatible Offline-Datei wird erstellt ...\n'
                '%.2f GiB gespeichert · Budget %.2f GiB\n'
                'Die Prozentanzeige bezieht sich auf das Speicherbudget.\n'
                'Fertig erst nach Pruefung der vollstaendigen Datei.' % (done / 2**30, budget / 2**30))


EmbyFlowLocalDownloadScreen.source_chosen = _efcmp_source
EmbyFlowLocalDownloadScreen.target_chosen = _efcmp_target
EmbyFlowLocalDownloadScreen.transfer = _efcmp_transfer
EmbyFlowLocalDownloadScreen.poll = _efcmp_poll
_efdl_choice_text = _efcmp_text
