
# EMBYFLOW_UNIVERSAL_DIRECT_AUDIO_V1_20261028
_EFUA_START = EmbyFlowMoviePlayer.set_preferred_audio_track
_EFUA_OPEN = EmbyFlowMoviePlayer.open_audio_selection
_EFUA_SELECT = EmbyFlowMoviePlayer.audio_selection_finished
_EFUA_STREAMS = EmbyFlowMoviePlayer.embyflow_media_streams_by_type
_EFUA_APPLY = EmbyFlowMoviePlayer.embyflow_apply_confirmed_audio_track

def _efua_log(event, **fields):
    try:
        import json, time
        fields.update(event=event, time=time.strftime('%H:%M:%S'))
        with open('/tmp/embyflow-audio-universal.log', 'a') as out:
            out.write(json.dumps(fields) + '\n')
    except Exception:
        pass

def _efua_native(player):
    try:
        ref = player.session.nav.getCurrentlyPlayingServiceReference()
        if ref is None or int(ref.type) not in (1, 4097):
            return False
        sid = getattr(player, 'play_session_id', None)
        if sid and (getattr(player, '_efa2_server_session', None) == sid or
                    getattr(player, '_efa3_audio_compat_session', None) == sid):
            return False
        return bool((getattr(player, 'playback_info', None) or {}).get('local_file')
                    or _embyflow_rcdev7_static_direct(player))
    except Exception:
        return False

def _efua_start(player):
    if not _efua_native(player):
        return _EFUA_START(player)
    key = (getattr(player, 'play_session_id', None),
           str(player.session.nav.getCurrentlyPlayingServiceReference()))
    if getattr(player, '_efua_start_key', None) != key:
        player._efua_start_key = key
        player._dfas_tries = 0
    # Existing language/codec matcher verifies the native track selection.
    # It also respects manual choices and retries while tracks are loading.
    return _efua_match(player)

def _efua_streams(player, kind):
    if not _efua_native(player):
        return _EFUA_STREAMS(player, kind)
    source = _df_source(player)
    if source:
        return [s for s in (source.get('MediaStreams') or [])
                if str(s.get('Type') or '').lower() == str(kind).lower()]
    return _EFUA_STREAMS(player, kind)

def _efua_open(player):
    try:
        native = _efua_native(player)
        _efua_log('audio_menu', native=native,
                  pending=bool(getattr(player, '_efa2_pending', False)))
        if native:
            return _EFA2_OPEN(player)
        if getattr(player, '_efa2_pending', False):
            return player.session.open(MessageBox,
                'Ein Tonwechsel laeuft noch. Bitte kurz warten.',
                MessageBox.TYPE_INFO, timeout=5)
        return _EFUA_OPEN(player)
    except Exception as error:
        _efua_log('audio_menu_error', error=type(error).__name__)
        return player.session.open(MessageBox,
            'Tonspurauswahl nicht verfuegbar: %s' % str(error),
            MessageBox.TYPE_ERROR, timeout=8)

def _efua_select(player, result):
    payload = player.embyflow_extract_audio_payload(result)
    if payload and 'e2_index' in payload and _efua_native(player):
        return _EFA2_SELECT(player, result)
    return _EFUA_SELECT(player, result)

def _efua_retry(self,reason):
    count=int(getattr(self,'_dfas_tries',0))+1
    self._dfas_tries=count
    if count<8:
        self.audio_timer.start(1000,True)
    else:_efua_log('not-selected',reason=reason,tries=count)

def _efua_match(self):
    if getattr(self,'closed',False) or getattr(self,'embyflow_manual_audio_selected',False):return
    if int(getattr(self,'_dfas_tries',0))>=8:return
    try:
        source=_df_source(self)
        streams=[s for s in (source.get('MediaStreams') or source.get('media_streams') or [])
                 if str(s.get('Type') or s.get('type') or '').lower()=='audio']
        service=self.session.nav.getCurrentService()
        tracks=service and service.audioTracks()
        count=int(tracks.getNumberOfTracks()) if tracks else 0
        if not count:return _efua_retry(self,'tracks-not-ready')
        descriptors=[self.embyflow_audio_track_descriptor(tracks,i) for i in range(count)]
        def lang(stream):
            # Respect an explicit language over ambiguous text in the title.
            return self.embyflow_audio_language_key(stream.get('Language') or stream.get('DisplayLanguage') or
                stream.get('DisplayTitle') or stream.get('Title'))
        german=[s for s in streams if lang(s)=='de' and not audio_stream_is_unwanted(s)]
        desired=max(german,key=lambda s:audio_stream_score(s,source.get('DefaultAudioStreamIndex'))) if german else None
        native=[d for d in descriptors if d.get('language_key')=='de' and
                not audio_stream_is_unwanted({'Title':d.get('description','')})]
        chosen=None;matched=None
        if native:
            # Prefer the requested German codec when there are multiple German tracks.
            codec=self.embyflow_audio_codec_key(desired.get('Codec')) if desired else ''
            chosen=next((d for d in native if codec and d.get('codec_key')==codec),native[0])
            candidates=[s for s in german if not chosen.get('codec_key') or
                        self.embyflow_audio_codec_key(s.get('Codec'))==chosen.get('codec_key')]
            if len(candidates)==1:matched=candidates[0]
            elif len(streams)==count:
                ordinal=streams[int(chosen['e2_index'])]
                if lang(ordinal)=='de':matched=ordinal
        elif desired is not None:
            # Ordinal fallback only for full, unlabelled native track lists.
            # Never map a German stream index onto an explicitly English track.
            if len(streams)==count:
                position=next(i for i,s in enumerate(streams) if s is desired)
                candidate=descriptors[position]
                codec=self.embyflow_audio_codec_key(desired.get('Codec'))
                if (not candidate.get('language_key') and
                    (not candidate.get('codec_key') or not codec or candidate['codec_key']==codec)):
                    chosen=candidate;matched=desired
            if chosen is None:return _efua_retry(self,'german-not-exposed')
        else:
            # No advertised German track: retain the current service choice.
            return _efua_log('no-german-track',native_tracks=count)
        requested=int(chosen['e2_index'])
        if int(tracks.getCurrentTrack())!=requested:tracks.selectTrack(requested)
        if int(tracks.getCurrentTrack())!=requested:return _efua_retry(self,'selection-not-confirmed')
        self.audio_timer.stop()
        if matched is not None:
            index=matched.get('Index')
            if index is not None:
                self.item['embyflow_selected_audio_index']=index
                source['DefaultAudioStreamIndex']=index
            self.embyflow_active_audio_override=dict(matched)
        else:
            self.embyflow_active_audio_override={'Type':'Audio','Language':'deu',
                'Codec':chosen.get('codec_key',''),'DisplayTitle':chosen.get('description','')}
        self.overlay_language='Deutsch'
        self.overlay_audio_format=chosen.get('description') or (matched or {}).get('DisplayTitle','')
        # The badge label is cached when the player is created: refresh it only
        # after native selection has been confirmed and its metadata updated.
        try:self['technical_badges'].setText(self.tester_osd_build_badges())
        except Exception:pass
        _efua_log('selected-german',native_track=requested,native_tracks=count,
                  stream_index=(matched or {}).get('Index'))
    except Exception as error:
        _efua_retry(self,type(error).__name__)

def _efua_apply(player,index):
    if not _efua_native(player):return _EFUA_APPLY(player,index)
    # The original confirmation routine refreshes the badges and language.
    # Its first-source metadata write must not alter another film version.
    sources=player.item.get('MediaSources') or player.item.get('media_sources') or []
    sentinel=object();first=sources[0] if sources else None
    old=first.get('DefaultAudioStreamIndex',sentinel) if first is not None else sentinel
    try:result=_DF_APPLY_BEFORE(player,index)
    finally:
        if first is not None:
            if old is sentinel:first.pop('DefaultAudioStreamIndex',None)
            else:first['DefaultAudioStreamIndex']=old
    selected=result[2]
    source=_df_source(player)
    if selected is not None and source:source['DefaultAudioStreamIndex']=selected
    return result

EmbyFlowMoviePlayer.set_preferred_audio_track = _efua_start
EmbyFlowMoviePlayer.open_audio_selection = _efua_open
EmbyFlowMoviePlayer.audio_selection_finished = _efua_select
EmbyFlowMoviePlayer.embyflow_media_streams_by_type = _efua_streams
EmbyFlowMoviePlayer.embyflow_apply_confirmed_audio_track = _efua_apply
# EMBYFLOW_UNIVERSAL_DIRECT_AUDIO_V1_20261028_END
