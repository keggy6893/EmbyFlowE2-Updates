from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_Anbieterlinks_20261005_0501.py').read_text()
s=s.replace('PLUGIN_VERSION = "2026-RCDEV-ANBIETERLINKS-20261005"','PLUGIN_VERSION = "2026-RCDEV-SERVERGUARD404-20261005"',1)
anchor='from datetime import datetime, timedelta\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n'+(root/'release_tools/server_guard_0503.inc.py').read_text()+'\n',1)
assert s.count('server, token, user_id = get_emby_auth(force=True)')==1
s=s.replace('server, token, user_id = get_emby_auth(force=True)','server, token, user_id = get_emby_auth()',1)
s=s.replace('with _V18Pool(max_workers=48) as pool:','with _V18Pool(max_workers=8) as pool:',1)
start=s.index('            for url in self._candidate_urls("/Users/AuthenticateByName"):')
end=s.index('            if not data:',start)
s=s[:start]+'''            # One credential submission per click to the configured address.
            url = self.server + "/Users/AuthenticateByName"
            response = embyflow_http_post(
                url,
                headers={"X-Emby-Authorization": AUTH_HEADER},
                json={"Username": self.username, "Pw": self.password},
                timeout=10, verify=True,
            )
            if int(getattr(response, "status_code", 0)) == 200:
                data = response.json() or {}
            else:
                last_error = "HTTP %s" % getattr(response, "status_code", "?")
'''+s[end:]
# Theme lookup also accesses Emby; do not leave a urllib bypass.
start=s.index('def _json(url, token=None, timeout=8):')
end=s.index('\n\nclass ThemeMediaManager',start)
s=s[:start]+'''def _json(url, token=None, timeout=8):
    headers = {'User-Agent': 'EmbyFlowE2/1.0'}
    if token:
        headers['X-Emby-Token'] = token
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 2 * 1024 * 1024:
                    raise ValueError('Theme lookup response too large')
            return json.loads(data.decode('utf-8'))
    except Exception:
        # Never log authenticated URLs or tokens.
        return None
'''+s[end:]
s+='\n'+(root/'release_tools/server_guard_ui_0502.inc.py').read_text()
compile(s,'plugin.py','exec')
p=root/'EmbyFlowE2_ServerGuard_20261005_0503.py';p.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-SERVERGUARD404-20261005',build=2026100503,
 download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+p.name,
 sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changelog=[
 '404/5xx/Redirect/Transportfehler zaehlen nicht als Login-Fehlversuch; Backoff nur bei 401/403/429 oder 200 ohne gueltiges Token',
 'HTTP 403/429: mindestens 5 Minuten Host-Pause, Retry-After beachten, Bildschirmmeldung',
 'Login: Lock und Backoff 60/120/240/480/900 Sekunden; ein Passwortversuch pro Klick ohne URL-Fallback oder Redirect',
 'Startup nutzt den Token-Cache; NAS-Suche weiterhin nur per Klick, jetzt maximal 8 Threads',
 'Neuheiten und Anbieterlinks aus 0501 enthalten; lokal mit simulierten Antworten getestet, kein Test auf Bennies Server'])
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Prepared build',m['build'],m['sha256'])
