# Compact download dialogs in the EmbyFlow navy/cyan palette.
import textwrap as _efdl_wrap
import re as _efdl_re

def _efdl_choice_text(entry):
    raw, data = str(entry[0]), entry[1]
    if isinstance(data, dict) and data.get('Size'):
        streams = data.get('MediaStreams') or []
        video = next((s for s in streams if isinstance(s,dict) and s.get('Type') == 'Video'), {})
        try:
            width = int(video.get('Width') or 0)
        except (TypeError, ValueError):
            width = 0
        if width >= 3840 or _efdl_re.search(r'2160p|\b4k\b', raw, _efdl_re.I):
            quality = '4K UHD'
        elif width >= 1920 or _efdl_re.search(r'1080p', raw, _efdl_re.I):
            quality = 'Full HD'
        elif width >= 1280 or _efdl_re.search(r'720p', raw, _efdl_re.I):
            quality = 'HD'
        else:
            quality = 'Originaldatei'
        codec = str(video.get('Codec') or '').upper()
        codec = {'H264': 'H.264', 'H265': 'HEVC'}.get(codec, codec)
        main = ' · '.join(s for s in (quality, codec, str(data.get('Container') or '').upper()) if s)
        return main, '%.2f GiB' % (int(data['Size']) / 2**30), raw
    if raw in ('/media/hdd', '/media/usb'):
        return ('Festplatte' if raw == '/media/hdd' else 'USB-Speicher'), raw, raw + '/movie/EmbyFlow'
    return raw, '', raw

class EmbyFlowDownloadChoice(Screen):
    def __init__(self, session, title, list, description='', confirmation=False, access_status='', storage=None):
        self.entries = tuple(list or ())
        self.storage = dict(storage or {})
        self.index = 0  # Confirmation starts on Abbrechen.
        self.page_size = 2 if confirmation else 3
        self.visible_rows = max(1, min(self.page_size, len(self.entries)))
        row_y = 514 if confirmation else 270
        detail_lines = max((len(_efdl_wrap.wrap(_efdl_choice_text(e)[2], 88)) for e in self.entries), default=1)
        detail_height = max(72, min(144, 24 * detail_lines + 8))
        detail_y = row_y + self.visible_rows * 108 + 38
        height = row_y + self.visible_rows * 108 + 72 if confirmation else detail_y + detail_height + 76
        nodes = []
        def label(name, x, y, w, h, size, fg='#E1E7ED', align='left'):
            nodes.append('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="%s" backgroundColor="#0B1522" transparent="1" valign="center" halign="%s" zPosition="3" />' % (name, sx(x), sy(y), sx(w), sy(h), sy(size), fg, align))
        def pixmap(name,x,y,w,h,z=1):
            nodes.append('<widget name="%s" position="%d,%d" size="%d,%d" zPosition="%d" alphatest="blend" />' % (name,sx(x),sy(y),sx(w),sy(h),z))
        pixmap('panel',0,0,1120,height,0)
        label('brand_emby',40,24,60,26,18,'#26DFF5')
        label('brand_flow',100,24,65,26,18,'#EC3EA9')
        label('brand_e2',170,24,45,26,18,'#99ACBD')
        label('section',840,24,240,26,16,'#8DA1B7','right')
        nodes.append('<eLabel position="%d,%d" size="%d,%d" backgroundColor="#294052" zPosition="1" />' % (sx(40),sy(66),sx(1040),sy(1)))
        label('heading',40,86,1040,46,32)
        label('description',40,142,1040,258 if confirmation else 34,20,'#98A9B9')
        label('quota',40,418 if confirmation else 188,1040,30,22,'#26DFF5')
        label('permission',40,462 if confirmation else 232,1040,26,18,'#79C5CE')
        for slot in range(self.visible_rows):
            y=row_y+slot*108
            pixmap('card%d'%slot,40,y,1040,96)
            label('row%d'%slot,144,y+12,660,34,25)
            label('info%d'%slot,800,y+22,214,45,25,'#D7E7EF','right')
            label('storage_meta%d'%slot,144,y+56,650,26,18,'#98A9B9')
            for badge in range(3):
                pixmap('badge_bg%d_%d'%(slot,badge),144+badge*106,y+56,94,26,2)
                label('badge%d_%d'%(slot,badge),144+badge*106,y+56,94,26,17,'#B9CFDF','center')
        if not confirmation:
            label('detail_caption',40,detail_y-25,1040,22,16,'#8196A9')
        label('details',40,detail_y if not confirmation else height-60,1040,detail_height if not confirmation else 1,20,'#98A9B9')
        nodes.append('<eLabel position="%d,%d" size="%d,%d" backgroundColor="#294052" zPosition="1" />' % (sx(40),sy(height-62),sx(1040),sy(1)))
        label('hint',40,height-44,1040,28,18,'#93AABD')
        self.skin = '<screen name="EmbyFlowDownloadChoice" position="center,center" size="%d,%d" flags="wfNoBorder" backgroundColor="#FF000000">%s</screen>' % (sx(1120),sy(height),''.join(nodes))
        Screen.__init__(self,session)
        self['panel']=Pixmap()
        self['brand_emby']=Label('EMBY')
        self['brand_flow']=Label('FLOW')
        self['brand_e2']=Label('E2')
        self['section']=Label('DOWNLOAD')
        self['heading']=Label(str(title))
        self['description']=Label('\n'.join(_efdl_wrap.fill(line,88) for line in str(description).splitlines()))
        self['permission']=Label(str(access_status))
        self['quota']=Label('')
        _efdl_update_quota(self)
        self['details']=Label('')
        if not confirmation:self['detail_caption']=Label('DATEI' if any(isinstance(e[1],dict) for e in self.entries) else 'SPEICHERORT')
        self['hint']=Label('')
        for slot in range(self.visible_rows):
            self['row%d'%slot]=Label('')
            self['info%d'%slot]=Label('')
            self['card%d'%slot]=Pixmap()
            self['storage_meta%d'%slot]=Label('')
            for badge in range(3):
                self['badge_bg%d_%d'%(slot,badge)]=Pixmap()
                self['badge%d_%d'%(slot,badge)]=Label('')
        self['actions']=ActionMap(['OkCancelActions','DirectionActions','ColorActions'],{'ok':self.accept,'cancel':self.cancel,'red':self.cancel,'up':lambda:self.move(-1),'down':lambda:self.move(1)},-2)
        self.onLayoutFinish.append(self.draw)
        self._quota_timer=eTimer()
        self._quota_timer.callback.append(self.refresh_quota)
        self.onClose.append(self._quota_timer.stop)
        self._quota_timer.start(1000,False)

    def refresh_quota(self):
        _efdl_update_quota(self)

    def draw(self):
        _efdl_style_apply(self['panel'],'panel')
        first=(self.index//self.page_size)*self.page_size
        for slot in range(self.visible_rows):
            index=first+slot
            widget, info, card=self['row%d'%slot],self['info%d'%slot],self['card%d'%slot]
            pieces=[widget,info,card,self['storage_meta%d'%slot]]+[self[name+'%d_%d'%(slot,b)] for b in range(3) for name in ('badge','badge_bg')]
            if index>=len(self.entries):
                for part in pieces:part.hide()
                continue
            main,right,raw=_efdl_choice_text(self.entries[index])
            data=self.entries[index][1]
            film=isinstance(data,dict) and bool(data.get('Size'))
            chunks=main.split(' · ') if film else [main]
            title=chunks[0]
            capacity = self.storage.get(data) if isinstance(data,str) else None
            meta = self['storage_meta%d'%slot]
            if capacity is not None:
                if capacity.get('known'):
                    right = ('%.1f GiB frei' % (capacity['free']/2**30)).replace('.',',')
                    meta.setText(('%.1f GiB gesamt' % (capacity['total']/2**30)).replace('.',',') + ('' if capacity['enough'] else ' · Zu wenig Speicher'))
                else:
                    right = 'Nicht ermittelbar'
                    meta.setText('Speicherprüfung fehlgeschlagen')
                meta.show()
            else:
                meta.hide()
            widget.setText(title if len(title)<=52 else title[:49]+'…')
            info.setText(right)
            widget.show();info.show();card.show()
            _efdl_style_apply(card,('selected' if index==self.index else 'normal')+('' if film else '_plain'))
            badges=[]
            if film:
                resolution={'4K UHD':'2160p','Full HD':'1080p','HD':'720p'}.get(chunks[0])
                badges=([resolution] if resolution else [])+chunks[1:]
            for badge in range(3):
                text=self['badge%d_%d'%(slot,badge)]
                background=self['badge_bg%d_%d'%(slot,badge)]
                if badge<len(badges):
                    text.setText(badges[badge]);text.show();background.show()
                    _efdl_style_apply(background,'badge')
                else:
                    text.hide();background.hide()
        if self.entries:
            details = _efdl_choice_text(self.entries[self.index])[2]
            selected_data = self.entries[self.index][1]
            capacity = self.storage.get(selected_data) if isinstance(selected_data,str) else None
            if capacity is not None:
                sizes = ('Film: %.2f GiB · Reserve: %.2f GiB' % (capacity['required']/2**30, capacity['reserve']/2**30)).replace('.',',')
                state = ('Genügend Speicher' if capacity['enough'] else 'Zu wenig Speicher') if capacity.get('known') else 'Speicher nicht prüfbar'
                details += '\n' + sizes + ' · ' + state
            self['details'].setText('\n'.join(_efdl_wrap.fill(line,88) for line in details.splitlines()))
        self['hint'].setText('%d / %d verfügbar       ↑ ↓  Auswahl       OK  Weiter       EXIT  Zurück' % (self.index+1 if self.entries else 0,len(self.entries)))

    def move(self,step):
        if self.entries:
            self.index=(self.index+step)%len(self.entries)
            self.draw()

    def accept(self):
        if not self.entries:
            return
        data = self.entries[self.index][1]
        capacity = self.storage.get(data) if isinstance(data,str) else None
        if capacity is not None and not capacity['enough']:
            self['hint'].setText('Zu wenig Speicher · Anderes Ziel wählen' if capacity.get('known') else 'Speicher nicht prüfbar · Zielauswahl erneut öffnen')
            return
        self.close(self.entries[self.index])

    def cancel(self):
        self.close(None)
