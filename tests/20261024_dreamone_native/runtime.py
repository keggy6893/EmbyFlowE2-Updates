# EMBYFLOW_DREAMONE_NATIVE_AUDIO_V1_BEGIN
_DF_OPEN_BEFORE=EmbyFlowMoviePlayer.open_audio_selection
_DF_SELECT_BEFORE=EmbyFlowMoviePlayer.audio_selection_finished
_DF_START_BEFORE=EmbyFlowMoviePlayer.set_preferred_audio_track
_DF_SHOW_BEFORE=EmbyFlowMoviePlayer.show_overlay
_DF_STREAMS_BEFORE=EmbyFlowMoviePlayer.embyflow_media_streams_by_type
_DF_APPLY_BEFORE=EmbyFlowMoviePlayer.embyflow_apply_confirmed_audio_track

def _df_is(player):
    try:
        from Components.SystemInfo import BoxInfo
        machine=str(BoxInfo.getItem('machinebuild') or BoxInfo.getItem('model') or '').lower()
    except Exception:machine=''
    if not machine:
        try:
            from boxbranding import getMachineBuild
            machine=str(getMachineBuild() or '').lower()
        except Exception:pass
    if machine not in ('dreamone','dmone'):return False
    try:
        ref=player.session.nav.getCurrentlyPlayingServiceReference()
        return ref is not None and int(ref.type)==4097
    except Exception:return False

def _df_source(player):
    wanted=str(getattr(player,'media_source_id','') or '')
    for item in (getattr(player,'item',None) or {},(getattr(player,'playback_info',None) or {}).get('item') or {}):
        sources=item.get('MediaSources') or item.get('media_sources') or []
        if wanted:
            source=next((s for s in sources if str(s.get('Id') or s.get('id') or '')==wanted),None)
            if source is not None:return source
        elif len(sources)==1:return sources[0]
    return {}

def _df_streams(player,kind):
    if not _df_is(player):return _DF_STREAMS_BEFORE(player,kind)
    return [s for s in (_df_source(player).get('MediaStreams') or [])
            if str(s.get('Type') or '').lower()==str(kind).lower()]

def _df_apply(player,index):
    if not _df_is(player):return _DF_APPLY_BEFORE(player,index)
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

def _df_open(player):
    if not _df_is(player):return _DF_OPEN_BEFORE(player)
    # Use the original, confirmed native selector. Never open an HLS/remux
    # session merely to select a track already exposed by the decoder.
    return _EFA2_OPEN(player)

def _df_select(player,result):
    if not _df_is(player):return _DF_SELECT_BEFORE(player,result)
    payload=player.embyflow_extract_audio_payload(result)
    if not payload:return
    if 'e2_index' not in payload:
        player.session.open(MessageBox,'Tonspurmenue bitte schliessen und erneut oeffnen.',MessageBox.TYPE_INFO,timeout=5)
        return
    return _EFA2_SELECT(player,result)

def _df_show(player,*args,**kwargs):
    result=_DF_SHOW_BEFORE(player,*args,**kwargs)
    if _df_is(player):
        try:player['technical_badges'].setText(player.tester_osd_build_badges())
        except Exception:pass
    return result

def _dfas_log(event,**fields):
    try:
        import json,time,os
        path='/tmp/embyflow-dreamone-audio.log'
        if os.path.exists(path) and os.path.getsize(path)>32768:
            with open(path,'w'):pass
        fields.update(event=event,time=time.strftime('%H:%M:%S'))
        with open(path,'a') as out:out.write(json.dumps(fields)+'\n')
    except Exception:pass

def _dfas_source(player):
    return _df_source(player)

def _dfas_retry(self,reason):
    count=int(getattr(self,'_dfas_tries',0))+1
    self._dfas_tries=count
    if count<8:
        self.audio_timer.start(1000,True)
    else:_dfas_log('not-selected',reason=reason,tries=count)

def _dfas_start(self):
    if getattr(self,'closed',False) or getattr(self,'embyflow_manual_audio_selected',False):return
    if int(getattr(self,'_dfas_tries',0))>=8:return
    try:
        source=_dfas_source(self)
        streams=[s for s in (source.get('MediaStreams') or source.get('media_streams') or [])
                 if str(s.get('Type') or s.get('type') or '').lower()=='audio']
        service=self.session.nav.getCurrentService()
        tracks=service and service.audioTracks()
        count=int(tracks.getNumberOfTracks()) if tracks else 0
        if not count:return _dfas_retry(self,'tracks-not-ready')
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
            if chosen is None:return _dfas_retry(self,'german-not-exposed')
        else:
            # No advertised German track: retain the current service choice.
            return _dfas_log('no-german-track',native_tracks=count)
        requested=int(chosen['e2_index'])
        if int(tracks.getCurrentTrack())!=requested:tracks.selectTrack(requested)
        if int(tracks.getCurrentTrack())!=requested:return _dfas_retry(self,'selection-not-confirmed')
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
        _dfas_log('selected-german',native_track=requested,native_tracks=count,
                  stream_index=(matched or {}).get('Index'))
    except Exception as error:
        _dfas_retry(self,type(error).__name__)

def _df_start(player):
    if _df_is(player):return _dfas_start(player)
    return _DF_START_BEFORE(player)

EmbyFlowMoviePlayer.set_preferred_audio_track=_df_start
EmbyFlowMoviePlayer.embyflow_media_streams_by_type=_df_streams
EmbyFlowMoviePlayer.embyflow_apply_confirmed_audio_track=_df_apply
EmbyFlowMoviePlayer.open_audio_selection=_df_open
EmbyFlowMoviePlayer.audio_selection_finished=_df_select
EmbyFlowMoviePlayer.show_overlay=_df_show
# EMBYFLOW_DREAMONE_NATIVE_AUDIO_V1_END
