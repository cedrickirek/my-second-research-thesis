# Vendored annotation assets (offline rendering)

Self-contained copies of the JS/CSS the annotation HTML needs, so a generated
file renders math **with no internet** (the CDN version goes blank on a phone
that is offline, on flaky data, or whose mail/files preview blocks external
resources). `annotation_html.render_html(offline=True)` inlines these.

| File | Source | Version |
|---|---|---|
| `katex.min.js` | https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js | KaTeX 0.16.9 |
| `katex.offline.css` | built from `katex@0.16.9/dist/katex.min.css` | KaTeX 0.16.9 |
| `marked.min.js` | https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js | marked 12.0.2 |

`katex.offline.css` is the upstream `katex.min.css` with the 20 WOFF2 fonts
embedded as `data:` base64 URIs and the now-redundant WOFF/TTF `src` alternates
stripped (browsers use the inlined WOFF2). Rebuild:

```python
import re, base64, urllib.request
css = open("katex.min.css", encoding="utf-8").read()
for name in sorted(set(re.findall(r"fonts/(KaTeX_[A-Za-z0-9_-]+)\.woff2", css))):
    data = urllib.request.urlopen(
        f"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/fonts/{name}.woff2"
    ).read()
    css = css.replace(f"url(fonts/{name}.woff2)",
                      "url(data:font/woff2;base64," + base64.b64encode(data).decode() + ")")
css = re.sub(r',url\(fonts/KaTeX_[A-Za-z0-9_-]+\.woff\) format\("woff"\)', "", css)
css = re.sub(r',url\(fonts/KaTeX_[A-Za-z0-9_-]+\.ttf\) format\("truetype"\)', "", css)
open("katex.offline.css", "w", encoding="utf-8").write(css)
```