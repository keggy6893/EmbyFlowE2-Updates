from pathlib import Path
import re

src = Path('plugin_RCDEV13_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py')
text = src.read_text(encoding='utf-8')
pat = re.compile(r'(?<!\d)(?:192\.168\.|10\.\d{1,3}\.|172\.(?:1[6-9]|2\d|3[01])\.)(?:\d{1,3}\.)?\d{1,3}(?!\d)')
count = 0
for n, line in enumerate(text.splitlines(), 1):
    if pat.search(line):
        count += 1
        safe = pat.sub('<PRIVATE_IP>', line)
        print(f'REDACTED_PRIVATE_IP_CONTEXT line={n}: {safe[:500]}')
print(f'REDACTED_PRIVATE_IP_COUNT={count}')
