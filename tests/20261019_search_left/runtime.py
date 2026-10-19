# EMBYFLOW_SEARCH_LEFT_GRID_V1
class EmbyFlowDisneySearchScreen(Screen):
    KEYS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["Ä", "Ö", "Ü", "ß", "123", "SPACE", "DEL"]
    NUMBER_KEYS = list("0123456789") + ["ABC", "SPACE", "DEL"]
    FILTERS = [("Alle", "Movie,Series"), ("Filme", "Movie"), ("Serien", "Series")]
    KEY_COLUMNS = 6
    HISTORY_ROWS = 3
    POSTER_SLOTS = 4
    POSTER_WIDTH, POSTER_HEIGHT = 264, 376
    _skin = ['<screen name="EmbyFlowDisneySearchScreen" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#0C1827">\n      <eLabel text="EmbyFlow" position="40,24" size="350,44" font="Regular;32" foregroundColor="#DCE5EE" backgroundColor="#0C1827" transparent="1" />\n      <eLabel text="Suche" position="40,70" size="250,40" font="Bold;27" foregroundColor="#38C7F4" backgroundColor="#0C1827" transparent="1" />\n      <eLabel position="38,124" size="520,760" backgroundColor="#0C1827" cornerRadius="16" widgetBorderWidth="1" widgetBorderColor="#263B4A" />\n      <eLabel position="588,124" size="1290,760" backgroundColor="#0C1827" cornerRadius="16" widgetBorderWidth="1" widgetBorderColor="#263B4A" />\n      <widget name="query" position="62,150" size="472,64" font="Bold;30" foregroundColor="#FFFFFF" backgroundColor="#102432" valign="center" cornerRadius="11" widgetBorderWidth="2" widgetBorderColor="#2A566C" />\n      <widget name="hint" position="62,226" size="472,28" font="Regular;21" foregroundColor="#A5B5C3" transparent="1" />\n      <eLabel text="Letzte Suchen" position="62,682" size="472,38" font="Bold;27" foregroundColor="#F1F5F8" transparent="1" />\n      <widget name="history" position="62,730" size="472,132" font="Regular;25" foregroundColor="#DCE5EE" transparent="1" />\n      <widget name="focus_top" position="-500,-500" size="1,1" zPosition="20" backgroundColor="#38C7F4" />\n      <widget name="focus_bottom" position="-500,-500" size="1,1" zPosition="20" backgroundColor="#38C7F4" />\n      <widget name="focus_left" position="-500,-500" size="1,1" zPosition="20" backgroundColor="#38C7F4" />\n      <widget name="focus_right" position="-500,-500" size="1,1" zPosition="20" backgroundColor="#38C7F4" />']
    _key_geo = []
    for _i in range(len(KEYS)):
        if _i < 30:
            _x, _y, _w, _h = 62 + (_i % 6) * 80, 264 + (_i // 6) * 66, 72, 58
        else:
            _x, _y, _w, _h = 62 + (_i - 30) * 160, 606, 152, 58
        _key_geo.append((_x, _y, _w, _h))
        _skin.append('<widget name="k%d" position="%d,%d" size="%d,%d" zPosition="10" font="Bold;28" foregroundColor="#F1F5F8" backgroundColor="#102432" halign="center" valign="center" cornerRadius="8" />' % (_i, _x, _y, _w, _h))
    _skin.append('<widget name="filter" position="622,150" size="1210,40" font="Regular;27" foregroundColor="#45D4FA" transparent="1" />\n      <widget name="status" position="622,204" size="1210,38" font="Regular;24" foregroundColor="#A5B5C3" transparent="1" />')
    _poster_geo = []
    for _i in range(POSTER_SLOTS):
        _x = 622 + _i * 310
        _poster_geo.append((_x, 270, POSTER_WIDTH, POSTER_HEIGHT))
        _skin.append('<widget name="p%d" position="%d,270" size="264,376" zPosition="5" alphatest="on" />' % (_i, _x))
        _skin.append('<widget name="t%d" position="%d,662" size="264,90" zPosition="6" font="Bold;25" foregroundColor="#F1F5F8" transparent="1" valign="top" />' % (_i, _x))
        _skin.append('<widget name="m%d" position="%d,766" size="264,62" zPosition="6" font="Regular;21" foregroundColor="#A5B5C3" transparent="1" valign="top" />' % (_i, _x))
    _skin.append('<eLabel text="ROT  Zurück" position="40,918" size="250,40" font="Regular;23" foregroundColor="#D97E7E" transparent="1" />\n      <eLabel text="GELB  Löschen" position="350,918" size="300,40" font="Regular;23" foregroundColor="#D7BE62" transparent="1" />\n      <eLabel text="BLAU  Alle / Filme / Serien" position="700,918" size="460,40" font="Regular;23" foregroundColor="#62A9E6" transparent="1" />\n      <eLabel text="→ Treffer   ↓ Verlauf   OK Auswählen" position="1200,918" size="670,40" font="Regular;23" foregroundColor="#A5B5C3" transparent="1" halign="right" />\n    </screen>')
    skin = scale_skin("".join(_skin))

    def __init__(self, session):
        Screen.__init__(self, session)
        self.query_text = ""; self.key_index = 0; self.result_index = 0
        self.number_keyboard = False
        self.focus_mode = "keys"; self.filter_index = 0; self.results = []
        self.search_generation = 0; self.search_ready = None; self.closed_search = False
        self.history_items = self._load_history()
        self["query"] = Label(""); self["hint"] = Label("Treffer automatisch ab 2 Zeichen")
        self["filter"] = Label(""); self["status"] = Label(""); self["history"] = Label("")
        for name in ("focus_top","focus_bottom","focus_left","focus_right"): self[name] = Label("")
        for i, key in enumerate(self.KEYS): self["k%d" % i] = Label(self._key_label(key))
        for i in range(self.POSTER_SLOTS): self["p%d" % i] = Pixmap(); self["t%d" % i] = Label(""); self["m%d" % i] = Label("")
        self.poll_timer = eTimer()
        try: self.poll_timer.callback.append(self._poll)
        except Exception:
            try: self.poll_timer.timeout.connect(self._poll)
            except Exception: pass
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "WizardActions", "ColorActions"], {
            "cancel": self.close_screen, "red": self.close_screen, "ok": self.ok,
            "left": self.left, "right": self.right, "up": self.up, "down": self.down,
            "yellow": self.backspace, "blue": self.cycle_filter, "green": self.ok,
        }, -10)
        self.onLayoutFinish.append(self._start); self.onClose.append(self._on_close)

    def _start(self):
        self._set_keyboard(); self._render_keys(); self._render_filter(); self._render_history(); self._update_focus()
        try: self.poll_timer.start(180, False)
        except Exception: pass
    def _on_close(self):
        self.closed_search = True
        try: self.poll_timer.stop()
        except Exception: pass
    def close_screen(self): self.close()
    def _load_history(self):
        try:
            if not os.path.exists(SEARCH_HISTORY_FILE): return []
            with open(SEARCH_HISTORY_FILE, "r") as f: data = json.loads(f.read() or "[]")
            return [x for x in data if isinstance(x, dict) and str(x.get("term") or "").strip()][:8]
        except Exception: return []
    def _save_history(self, term):
        term = str(term or "").strip()
        if len(term) < 2: return
        try:
            data = self._load_history(); data = [x for x in data if str(x.get("term") or "").strip().lower() != term.lower()]
            data.insert(0, {"term": term, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())})
            with open(SEARCH_HISTORY_FILE, "w") as f: f.write(json.dumps(data[:20]))
            self.history_items = data[:8]
        except Exception: pass
    def _render_keys(self): self["query"].setText("   " + (self.query_text if self.query_text else "Suchbegriff"))
    def _render_filter(self): self["filter"].setText("     ".join((("● " if i == self.filter_index else "  ") + name) for i,(name,_types) in enumerate(self.FILTERS)))
    def _history_time(self, item):
        raw = str(item.get("timestamp") or "").strip()
        if not raw: return ""
        try:
            tm = time.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
            return ("Heute, " + time.strftime("%H:%M", tm)) if raw[:10] == time.strftime("%Y-%m-%d", time.localtime()) else time.strftime("%d.%m.%Y", tm)
        except Exception: return ""
    def _history_start(self):
        if self.focus_mode == "history":
            return (self.result_index // self.HISTORY_ROWS) * self.HISTORY_ROWS
        return 0

    def _render_history(self):
        if not self.history_items:
            self["history"].setText("Noch keine letzten Suchen")
            return
        start = self._history_start()
        lines = []
        for i, item in enumerate(self.history_items[start:start + self.HISTORY_ROWS], start):
            mark = "› " if self.focus_mode == "history" and i == self.result_index else "  "
            term = str(item.get("term") or "")
            lines.append(mark + (term[:26] + "…" if len(term) > 27 else term))
        self["history"].setText("\n".join(lines))
    def _hide_focus(self):
        for name in ("focus_top","focus_bottom","focus_left","focus_right"):
            try: self[name].instance.move(ePoint(-500,-500))
            except Exception: pass
    def _draw_focus(self, x, y, w, h):
        # The skin is scaled at load time; runtime borders must use the same scale.
        b = max(2, sx(3))
        x, y, w, h = sx(x), sy(y), sx(w), sy(h)
        try:
            self["focus_top"].instance.move(ePoint(x, y)); self["focus_top"].instance.resize(eSize(w, b))
            self["focus_bottom"].instance.move(ePoint(x, y+h-b)); self["focus_bottom"].instance.resize(eSize(w, b))
            self["focus_left"].instance.move(ePoint(x, y)); self["focus_left"].instance.resize(eSize(b, h))
            self["focus_right"].instance.move(ePoint(x+w-b, y)); self["focus_right"].instance.resize(eSize(b, h))
        except Exception:
            pass
    def _update_focus(self):
        self._hide_focus()
        if self.focus_mode == "keys":
            x, y, w, h = self._key_geo[self.key_index]
            self._draw_focus(x-3, y-3, w+6, h+6)
        elif self.focus_mode == "results" and self.results:
            x, y, w, h = self._poster_geo[self.result_index % self.POSTER_SLOTS]
            self._draw_focus(x-5, y-5, w+10, h+10)
        self._render_history()

    @staticmethod
    def _key_label(key):
        return {"SPACE": "Leer", "DEL": "Löschen"}.get(key, key)

    def _active_keys(self):
        return self.NUMBER_KEYS if self.number_keyboard else self.KEYS

    def _key_rows(self):
        # Action keys remain a separate row on both keyboard pages.
        count = len(self._active_keys()) - 3
        return [list(range(i, min(i + self.KEY_COLUMNS, count)))
                for i in range(0, count, self.KEY_COLUMNS)] + [list(range(count, count + 3))]

    def _set_keyboard(self):
        keys = self._active_keys()
        rows = self._key_rows()
        self._key_geo = []
        for r, row in enumerate(rows):
            action = r == len(rows) - 1
            for col, i in enumerate(row):
                geo = (62 + col * (160 if action else 80),
                       606 if action else 264 + r * 66,
                       152 if action else 72, 58)
                self._key_geo.append(geo)
                label = self["k%d" % i]
                label.setText(self._key_label(keys[i]))
                label.show()
                try:
                    x, y, w, h = geo
                    label.instance.move(ePoint(sx(x), sy(y)))
                    label.instance.resize(eSize(sx(w), sy(h)))
                except Exception:
                    pass
        for i in range(len(keys), len(self.KEYS)):
            self["k%d" % i].setText("")
            self["k%d" % i].hide()

    def _key_row(self):
        rows = self._key_rows()
        row = next(i for i, entries in enumerate(rows) if self.key_index in entries)
        return rows, row, rows[row].index(self.key_index)

    def _enter_results(self):
        if self.results:
            self.focus_mode = "results"
            self.result_index = 0
            self._render_results()

    def _result_page(self):
        return (self.result_index // self.POSTER_SLOTS) * self.POSTER_SLOTS if self.focus_mode == "results" else 0
    def left(self):
        if self.focus_mode == "keys":
            rows, r, col = self._key_row()
            self.key_index = rows[r][max(0, col - 1)]
        elif self.focus_mode == "results":
            if self.result_index > 0:
                self.result_index -= 1
            else:
                self.focus_mode = "keys"
            self._render_results()
        elif self.focus_mode == "history":
            self.focus_mode = "keys"
        self._update_focus()
    def right(self):
        if self.focus_mode == "keys":
            rows, r, col = self._key_row()
            if col + 1 < len(rows[r]):
                self.key_index = rows[r][col + 1]
            else:
                self._enter_results()
        elif self.focus_mode == "results" and self.results:
            self.result_index = min(self.result_index + 1, len(self.results) - 1)
            self._render_results()
        elif self.focus_mode == "history":
            self._enter_results()
        self._update_focus()
    def down(self):
        if self.focus_mode == "keys":
            rows, r, col = self._key_row()
            if r + 1 < len(rows):
                x = self._key_geo[self.key_index][0] + self._key_geo[self.key_index][2] / 2
                self.key_index = min(rows[r+1], key=lambda i: abs(self._key_geo[i][0] + self._key_geo[i][2] / 2 - x))
            elif self.history_items:
                self.focus_mode = "history"
                self.result_index = 0
        elif self.focus_mode == "history" and self.history_items:
            self.result_index = min(self.result_index + 1, len(self.history_items) - 1)
        self._update_focus()
    def up(self):
        if self.focus_mode == "keys":
            rows, r, col = self._key_row()
            if r > 0:
                x = self._key_geo[self.key_index][0] + self._key_geo[self.key_index][2] / 2
                self.key_index = min(rows[r-1], key=lambda i: abs(self._key_geo[i][0] + self._key_geo[i][2] / 2 - x))
        elif self.focus_mode == "results":
            self.focus_mode = "keys"
            self._render_results()
        elif self.focus_mode == "history":
            if self.result_index > 0:
                self.result_index -= 1
            else:
                self.focus_mode = "keys"
        self._update_focus()
    def ok(self):
        if self.focus_mode == "results" and self.results:
            item = self.results[min(self.result_index, len(self.results)-1)]
            self._save_history(self.query_text)
            self.session.open(EmbyFlowDetailScreen, item)
            return
        if self.focus_mode == "history" and self.history_items:
            self.query_text = str(self.history_items[self.result_index].get("term") or "")
            self.focus_mode = "keys"
            self.result_index = 0
            self._render_keys(); self._request_search(); self._update_focus()
            return
        key = self._active_keys()[self.key_index]
        if key == "DEL":
            self.backspace()
            return
        if key in ("123", "ABC"):
            self.number_keyboard = not self.number_keyboard
            self.key_index = 0
            self._set_keyboard(); self._update_focus()
            return
        self.query_text += " " if key == "SPACE" else key
        self._render_keys(); self._request_search()
    def backspace(self):
        if self.focus_mode == "history" and self.history_items:
            term=str(self.history_items[min(self.result_index,len(self.history_items)-1)].get("term") or "")
            try:
                data=[x for x in self._load_history() if str(x.get("term") or "").strip().lower()!=term.lower()]
                with open(SEARCH_HISTORY_FILE,"w") as f: f.write(json.dumps(data))
            except Exception: pass
            self.history_items=self._load_history(); self.result_index=0
            if not self.history_items: self.focus_mode="keys"
            self._render_history(); self._update_focus(); return
        if self.query_text: self.query_text=self.query_text[:-1]; self._render_keys(); self._request_search()
    def cycle_filter(self): self.filter_index=(self.filter_index+1)%len(self.FILTERS); self._render_filter(); self._request_search()
    def _request_search(self):
        term=self.query_text.strip(); self.search_generation += 1; generation=self.search_generation
        self.results=[]; self.result_index=0; self.search_ready=None; self._clear_posters()
        if self.focus_mode == "results": self.focus_mode="keys"
        self._update_focus()
        if len(term) < 2:
            self.results=[]; self.search_ready=None; self["status"].setText(""); self._clear_posters(); self._render_history(); self._update_focus(); return
        self["status"].setText("Suche nach '%s' ..." % term); include_types=self.FILTERS[self.filter_index][1]
        def worker():
            try: data=emby_search_items(term, 18, include_types)
            except Exception: data=[]
            self.search_ready=(generation,term,data)
        try:
            import threading; t=threading.Thread(target=worker, name="EmbyFlowDisneySearch"); t.daemon=True; t.start()
        except Exception: worker()
    def _poll(self):
        ready=self.search_ready
        if ready:
            self.search_ready=None; generation,term,data=ready
            if generation == self.search_generation and term == self.query_text.strip() and not self.closed_search:
                self.results=list(data or []); self.result_index=0
                if self.focus_mode == "history": self.focus_mode="keys"
                self["status"].setText(("%d Treffer" % len(self.results)) if self.results else "Keine Treffer"); self._render_results()
        if self.results: self._load_ready_posters()
    def _clear_posters(self):
        for i in range(self.POSTER_SLOTS):
            self["t%d"%i].setText(""); self["m%d"%i].setText("")
            try: self["p%d"%i].instance.setPixmap(None); self["p%d"%i].hide()
            except Exception: pass
    def _search_quality_label(self, item):
        # SEARCH_QUALITY_BADGE_FIX5: distinguish separate Emby versions
        # (for example a 1080p and a 4K copy) from the real MediaSources data.
        best_w = 0
        best_h = 0
        try:
            for source in (item.get("media_sources") or item.get("MediaSources") or []):
                for stream in (source.get("MediaStreams") or []):
                    if str(stream.get("Type") or "").lower() != "video":
                        continue
                    try: best_w = max(best_w, int(stream.get("Width") or 0))
                    except Exception: pass
                    try: best_h = max(best_h, int(stream.get("Height") or 0))
                    except Exception: pass
        except Exception:
            pass
        if best_w >= 3000 or best_h >= 2000:
            return "4K"
        if best_w >= 1900 or best_h >= 1000:
            return "1080p"
        if best_w >= 1200 or best_h >= 700:
            return "720p"
        if best_w or best_h:
            return "%dp" % best_h if best_h else "SD"
        return ""

    def _render_results(self):
        self._clear_posters()
        start = self._result_page()
        visible = self.results[start:start + self.POSTER_SLOTS]
        if self.results:
            self["status"].setText("%d Treffer  ·  %d–%d" % (len(self.results), start+1, start+len(visible)))
        try:
            EMBYFLOW_POSTER_CACHE_MANAGER.prioritize(visible, False)
            EMBYFLOW_POSTER_CACHE_MANAGER.enqueue(visible, False, priority=3)
        except Exception:
            pass
        for i, item in enumerate(visible):
            title = str(item.get("title") or "")
            quality = self._search_quality_label(item)
            self["t%d" % i].setText(title + ("  ·  " + quality if quality else ""))
            self["m%d" % i].setText(str(item.get("meta") or ""))
        self._load_ready_posters(); self._update_focus()
    def _load_ready_posters(self):
        start = self._result_page()
        for i, item in enumerate(self.results[start:start + self.POSTER_SLOTS]):
            path = _grid_cache_path(item, False)
            if _grid_cache_valid(path):
                try:
                    self["p%d" % i].show()
                    embyflow_decode_image_to_widget(self, "p%d" % i, path,
                        self.POSTER_WIDTH, self.POSTER_HEIGHT,
                        token="search-left-%d-%s" % (i, _grid_cache_item_id(item)))
                except Exception:
                    pass
