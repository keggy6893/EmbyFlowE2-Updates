# -*- coding: utf-8 -*-
from __future__ import print_function
import json, os
from datetime import datetime
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eTimer

HISTORY='/etc/enigma2/embyflow_search_history.json'
MINLEN=2
COLS=4
VISIBLE=12
KEYS=[['A','B','C','D','E','F'],['G','H','I','J','K','L'],['M','N','O','P','Q','R'],['S','T','U','V','W','X'],['Y','Z','0','1','2','3'],['4','5','6','7','8','9'],['Ä','Ö','Ü','ß','<-','SPACE']]
FLAT=[x for r in KEYS for x in r]

def skin():
 o=['<screen name="EmbyFlowDisneySearch" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#06131d">',
 '<widget name="brand" position="45,35" size="500,50" font="Regular;34" foregroundColor="#55c8e7" transparent="1" text="EmbyFlow  •  Suche" />',
 '<widget name="date" position="1420,35" size="300,40" font="Regular;20" foregroundColor="#91a2ad" transparent="1" halign="right" />',
 '<widget name="clock" position="1740,30" size="130,48" font="Regular;30" foregroundColor="#ffffff" transparent="1" halign="right" />',
 '<widget name="leftpanel" position="28,112" size="480,850" backgroundColor="#081923" />',
 '<widget name="title" position="48,130" size="410,40" font="Regular;29" foregroundColor="#ffffff" transparent="1" text="Suche" />',
 '<widget name="query" position="48,180" size="410,62" font="Regular;27" foregroundColor="#ffffff" backgroundColor="#102532" valign="center" />',
 '<widget name="status" position="48,250" size="410,32" font="Regular;18" foregroundColor="#91a2ad" transparent="1" />']
 x0,y0,w,h,gx,gy=48,305,60,55,7,10
 for i,k in enumerate(FLAT):
  r=i//6;c=i%6;x=x0+c*(w+gx);y=y0+r*(h+gy)
  o += ['<widget name="kf%d" position="%d,%d" size="%d,%d" backgroundColor="#35c9ee" />'%(i,x-3,y-3,w+6,h+6),
        '<widget name="k%d" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" backgroundColor="#102532" halign="center" valign="center" />'%(i,x,y,w,h,15 if k=='SPACE' else 22)]
 o += ['<widget name="results" position="536,112" size="1356,850" backgroundColor="#081923" />',
 '<widget name="rtitle" position="558,130" size="900,40" font="Regular;28" foregroundColor="#ffffff" transparent="1" />',
 '<widget name="count" position="1580,132" size="270,34" font="Regular;19" foregroundColor="#55c8e7" transparent="1" halign="right" />']
 for i in range(VISIBLE):
  r=i//COLS;c=i%COLS;x=565+c*315;y=205+r*220
  o += ['<widget name="rf%d" position="%d,%d" size="290,180" backgroundColor="#35c9ee" />'%(i,x-3,y-3),
        '<widget name="r%d" position="%d,%d" size="284,174" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#102532" valign="center" />'%(i,x,y),
        '<widget name="m%d" position="%d,%d" size="270,34" font="Regular;17" foregroundColor="#91a2ad" transparent="1" />'%(i,x+8,y+132)]
 o += ['<widget name="preview" position="28,982" size="1864,58" backgroundColor="#081923" />',
 '<widget name="hint" position="50,995" size="1800,30" font="Regular;18" foregroundColor="#aebcc5" transparent="1" text="Pfeile: Navigieren   OK: Zeichen / Details   ROT: Zurück   BLAU: Filter Alle / Filme / Serien" />','</screen>']
 return ''.join(o)

class EmbyFlowDisneySearchScreen(Screen):
 skinName='EmbyFlowDisneySearch'
 def __init__(self,session):
  self.skin=skin(); Screen.__init__(self,session); self.session=session
  self.query='';self.ki=0;self.focus='keyboard';self.results=[];self.ri=0;self.filter='all';self.gen=0
  for n,t in [('brand','EmbyFlow  •  Suche'),('title','Suche')]: self[n]=Label(t)
  self['date']=Label('');self['clock']=Label('');self['query']=Label('');self['status']=Label('2+ Zeichen für Ergebnisse');self['rtitle']=Label('Letzte Suchen');self['count']=Label('')
  for i,k in enumerate(FLAT): self['kf%d'%i]=Label('');self['k%d'%i]=Label('␠' if k=='SPACE' else k)
  for i in range(VISIBLE): self['rf%d'%i]=Label('');self['r%d'%i]=Label('');self['m%d'%i]=Label('')
  self['preview']=Label('');self['hint']=Label('')
  self['actions']=ActionMap(['OkCancelActions','DirectionActions','ColorActions','NumberActions'],{'ok':self.ok,'cancel':self.close,'red':self.close,'blue':self.cycle_filter,'left':self.left,'right':self.right,'up':self.up,'down':self.down,'0':lambda:self.add('0'),'1':lambda:self.add('1'),'2':lambda:self.add('2'),'3':lambda:self.add('3'),'4':lambda:self.add('4'),'5':lambda:self.add('5'),'6':lambda:self.add('6'),'7':lambda:self.add('7'),'8':lambda:self.add('8'),'9':lambda:self.add('9')},-1)
  self.timer=eTimer();self.timer.callback.append(self.search)
  self.onLayoutFinish.append(self.render)
 def render(self):
  now=datetime.now();self['date'].setText(now.strftime('%d.%m.%Y'));self['clock'].setText(now.strftime('%H:%M'));self['query'].setText(self.query or 'Suchbegriff eingeben …')
  for i in range(len(FLAT)): (self['kf%d'%i].show() if self.focus=='keyboard' and i==self.ki else self['kf%d'%i].hide())
  for i in range(VISIBLE):
   if i<len(self.results):
    it=self.results[i]; name=str(it.get('title') or it.get('Name') or ''); typ=str(it.get('Type') or it.get('type') or ''); year=str(it.get('ProductionYear') or it.get('year') or '')
    self['r%d'%i].setText('  '+name);self['m%d'%i].setText('Emby  •  %s%s'%(typ,('  •  '+year) if year else ''));self['r%d'%i].show();self['m%d'%i].show()
   else:self['r%d'%i].setText('');self['m%d'%i].setText('')
   (self['rf%d'%i].show() if self.focus=='results' and i==self.ri and i<len(self.results) else self['rf%d'%i].hide())
  self['count'].setText('%d Treffer'%len(self.results) if self.results else '')
 def trigger(self):
  try:self.timer.stop()
  except:pass
  self.render()
  if len(self.query.strip())<MINLEN:
   self.results=[];self['status'].setText('2+ Zeichen für Ergebnisse' if not self.query else 'Noch 1 Zeichen für Ergebnisse');self['rtitle'].setText('Ergebnisse');self.render();return
  self['status'].setText('Suche läuft …');self.timer.start(350,True)
 def search(self):
  try:
   from . import plugin as P
   types={'all':'Movie,Series','movies':'Movie','series':'Series'}[self.filter]
   self.results=P.emby_search_items(self.query.strip(),60,types) or []
   self.results=self.results[:VISIBLE];self.ri=0;self['rtitle'].setText('Ergebnisse für „%s“'%self.query.strip());self['status'].setText('%d Treffer'%len(self.results) if self.results else 'Keine Ergebnisse');
   if self.results:self.focus='results'
  except Exception as e:self.results=[];self['status'].setText('Suchfehler: %s'%str(e)[:80])
  self.render()
 def add(self,ch):self.query+=ch;self.trigger()
 def back(self):self.query=self.query[:-1];self.trigger()
 def ok(self):
  if self.focus=='keyboard':
   k=FLAT[self.ki]
   if k=='<-':self.back()
   elif k=='SPACE':self.add(' ')
   else:self.add(k)
  elif self.results:
   try:
    from . import plugin as P
    self.session.open(P.EmbyFlowDetailScreen,self.results[self.ri])
   except:pass
 def cycle_filter(self):
  self.filter={'all':'movies','movies':'series','series':'all'}[self.filter];self['status'].setText({'all':'Filter: Alle','movies':'Filter: Filme','series':'Filter: Serien'}[self.filter]);self.trigger()
 def left(self):
  if self.focus=='results':self.ri=max(0,self.ri-1)
  else:self.ki=max(0,self.ki-1)
  self.render()
 def right(self):
  if self.focus=='results':self.ri=min(max(0,len(self.results)-1),self.ri+1)
  else:self.ki=min(len(FLAT)-1,self.ki+1)
  self.render()
 def up(self):
  if self.focus=='results':
   if self.ri>=COLS:self.ri-=COLS
   else:self.focus='keyboard'
  else:self.ki=max(0,self.ki-6)
  self.render()
 def down(self):
  if self.focus=='keyboard':
   if self.ki+6<len(FLAT):self.ki+=6
   elif self.results:self.focus='results'
  elif self.ri+COLS<len(self.results):self.ri+=COLS
  self.render()
