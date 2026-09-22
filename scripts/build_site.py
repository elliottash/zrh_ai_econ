"""Stage only public course assets and check homepage download links."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import shutil
root = Path(__file__).resolve().parents[1]
out = root / 'build'
if out.exists():
    shutil.rmtree(out)
out.mkdir()
for name in ('index.html', 'robots.txt', 'sitemap.xml', 'assets', 'slides', 'assignments', 'notebooks'):
    src = root / name
    if src.is_dir():
        shutil.copytree(src, out/name)
    else:
        shutil.copy2(src, out/name)
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key not in ('href','src') or not value or value.startswith(('#','https:','http:','mailto:')):
                continue
            path = unquote(urlsplit(value).path).lstrip('/')
            if path in ('chat','chat/'):
                continue
            assert (out/path).exists(), value
html = (out/'index.html').read_text()
assert 'Zurich Summer School in AI & Applied Economics' in html
assert 'Economics Lab' not in html
Links().feed(html)
print('Course built; homepage links and downloads verified.')
