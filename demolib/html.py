from html import escape

CSS = """
:root{color-scheme:light dark;--fg:#1b1d21;--muted:#5b6270;--bg:#fff;--alt:#f4f5f7;--line:#d9dce1;--accent:#0b5cd6;--err:#b42318;--ok:#067647}
@media (prefers-color-scheme:dark){:root{--fg:#e7e9ee;--muted:#9aa2b1;--bg:#111317;--alt:#1a1d23;--line:#2c313a;--accent:#6ea8ff;--err:#f97066;--ok:#47cd89}}
*{box-sizing:border-box}body{margin:0 auto;max-width:1200px;padding:12px 16px;font:14px/1.45 system-ui,sans-serif;color:var(--fg);background:var(--bg)}
h1{font-size:18px;margin:0 0 4px}h2{font-size:15px;margin:16px 0 6px}h3{font-size:14px;margin:8px 0 4px}
a{color:var(--accent)}a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.muted{color:var(--muted)}nav ul{display:flex;gap:12px;list-style:none;padding:0;margin:6px 0;flex-wrap:wrap}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}caption{text-align:left;font-weight:600;padding:4px 0}
th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}th{background:var(--alt);font-weight:600}
td.n,th.n{text-align:right}.wrap{overflow-x:auto}
.err{color:var(--err)}.ok{color:var(--ok)}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:2px 12px;margin:6px 0}dl.kv dt{color:var(--muted)}dl.kv dd{margin:0}
pre{white-space:pre-wrap;word-break:break-word;background:var(--alt);border:1px solid var(--line);padding:6px;margin:4px 0;max-height:420px;overflow:auto;font:12px/1.4 ui-monospace,monospace}
details{border:1px solid var(--line);border-radius:4px;padding:2px 8px;margin:4px 0}summary{cursor:pointer}
ol.timeline{list-style:none;padding:0;margin:0}ol.timeline>li{border-left:3px solid var(--line);padding:2px 0 2px 10px;margin:6px 0}
ol.timeline>li.user{border-color:var(--accent)}ol.timeline>li.assistant{border-color:var(--ok)}
"""


def esc(value):
    return escape("" if value is None else str(value), quote=True)


def page(title, body):
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def table(caption, headers, rows, numeric=()):
    head = "".join(f'<th scope="col"{" class=n" if i in numeric else ""}>{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows)
    return (f'<div class="wrap"><table><caption>{esc(caption)}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def fmt_cost(v):
    return f"${v:.4f}" if v else "–"


def fmt_num(v, digits=1):
    if v is None or v == "":
        return "–"
    if isinstance(v, int):
        return f"{v:,}"
    return f"{v:,.{digits}f}"
