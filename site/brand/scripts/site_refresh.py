#!/usr/bin/env python3
"""Assemble the site-refresh explorations: five home-page mockups and an index.

Each page in explorations/site-refresh/src/ is written by hand. This script fills in
the parts every page shares (the logo, the pointer, the icon, and the bar that switches
between explorations) and writes the finished pages one folder up.
"""
import pathlib

HERE = pathlib.Path(__file__).parent.parent / "explorations" / "site-refresh"
SRC = HERE / "src"

GROUND, INK = "#FF6B3D", "#1A0F0A"  # palette A, the logo's own colors

TILES = (
    '<path fill-rule="evenodd" d="M64 66H128A22 22 0 0 1 150 88V152A22 22 0 0 1 128 174H64A22 22 0 0 1 42 152V88A22 22 0 0 1 64 66ZM76.16 88Q76.16 85 79.16 85L94.16 85Q97.16 85 97.16 88L97.16 134Q97.16 137 100.16 137L120.16 137Q123.16 137 123.16 140L123.16 152Q123.16 155 120.16 155L79.16 155Q76.16 155 76.16 152Z"/>'
    '<path fill-rule="evenodd" d="M208 66H272A22 22 0 0 1 294 88V152A22 22 0 0 1 272 174H208A22 22 0 0 1 186 152V88A22 22 0 0 1 208 66ZM216 88Q216 85 219 85L261 85Q264 85 264 88L264 100Q264 103 261 103L253.5 103Q250.5 103 250.5 106L250.5 134Q250.5 137 253.5 137L261 137Q264 137 264 140L264 152Q264 155 261 155L219 155Q216 155 216 152L216 140Q216 137 219 137L226.5 137Q229.5 137 229.5 134L229.5 106Q229.5 103 226.5 103L219 103Q216 103 216 100Z"/>'
    '<path fill-rule="evenodd" d="M352 66H416A22 22 0 0 1 438 88V152A22 22 0 0 1 416 174H352A22 22 0 0 1 330 152V88A22 22 0 0 1 352 66ZM358.67 85H381.67A34 35 0 0 1 381.67 155H358.67Q355.67 155 355.67 152V88Q355.67 85 358.67 85ZM378.67 103H381.67A12 17 0 0 1 381.67 137H378.67Q376.67 137 376.67 135V105Q376.67 103 378.67 103Z"/>'
    '<path d="M154 115.5Q154 113.5 156 113.5L164 113.5Q166 113.5 166 111.5L166 106Q166 104 167.41 105.41L180.59 118.59Q182 120 180.59 121.41L167.41 134.59Q166 136 166 134L166 128.5Q166 126.5 164 126.5L156 126.5Q154 126.5 154 124.5Z"/>'
    '<path d="M298 115.5Q298 113.5 300 113.5L308 113.5Q310 113.5 310 111.5L310 106Q310 104 311.41 105.41L324.59 118.59Q326 120 324.59 121.41L311.41 134.59Q310 136 310 134L310 128.5Q310 126.5 308 126.5L300 126.5Q298 126.5 298 124.5Z"/>'
)

POINTER = "M154 115.5Q154 113.5 156 113.5L164 113.5Q166 113.5 166 111.5L166 106Q166 104 167.41 105.41L180.59 118.59Q182 120 180.59 121.41L167.41 134.59Q166 136 166 134L166 128.5Q166 126.5 164 126.5L156 126.5Q154 126.5 154 124.5Z"

# The wordmark on its own orange ground, cropped to a rounded badge.
WORDMARK_BADGE = (
    '<svg class="wordmark" viewBox="18 42 444 156" role="img" aria-label="LID">'
    f'<rect x="18" y="42" width="444" height="156" rx="34" fill="{GROUND}"/>'
    f'<g fill="{INK}">{TILES}</g></svg>'
)

# The wordmark with no ground, cropped to the tiles, drawn in currentColor.
WORDMARK_BARE = (
    '<svg class="wordmark" viewBox="42 66 396 108" role="img" aria-label="LID">'
    f'<g fill="currentColor">{TILES}</g></svg>'
)

# The wordmark tiles in palette A ink, cropped to the tiles, for a ground the page paints.
WORDMARK_INK = (
    '<svg class="wordmark" viewBox="42 66 396 108" role="img" aria-label="LID">'
    f'<g fill="{INK}">{TILES}</g></svg>'
)


def icon(uid):
    return (
        f'<svg class="icon" viewBox="0 0 64 64" role="img" aria-label="LID">'
        f'<defs><clipPath id="{uid}"><rect width="64" height="24.5"/><rect y="31.5" width="64" height="32.5"/></clipPath></defs>'
        f'<rect width="64" height="64" rx="14" fill="{GROUND}"/>'
        f'<path d="M10 14Q10 12 12 12L21 12Q23 12 23 14L23 39Q23 41 25 41L36 41Q38 41 38 43L38 50Q38 52 36 52L12 52Q10 52 10 50Z" fill="{INK}" clip-path="url(#{uid})"/>'
        f'<path d="M23 24.5H45V31.5H23Z" fill="{INK}"/>'
        f'<path d="M44 18.5Q44 17 45.06 18.06L53.94 26.94Q55 28 53.94 29.06L45.06 37.94Q44 39 44 37.5Z" fill="{INK}"/>'
        "</svg>"
    )


# The logo's pointer as a CSS mask, so any element can draw it in any color.
PTR_MASK = (
    "--ptr-mask: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='154 104 28 32'%3E%3Cpath d='" + POINTER + "'/%3E%3C/svg%3E\");"
)

PAGES = [
    ("linked-list.html", "A", "Linked list"),
    ("plain-text.html", "B", "Plain text"),
    ("stickers.html", "C", "Stickers"),
    ("poster.html", "D", "Poster"),
    ("rail.html", "E", "Rail"),
]

SWITCHER = (
    '<nav class="xsw" aria-label="Site explorations">'
    '<a href="index.html">All</a>'
    + "".join(f'<a href="{f}"><b>{k}</b><span> {name}</span></a>' for f, k, name in PAGES)
    + '<button type="button" id="xsw-theme" aria-label="Color theme">Auto</button>'
    "</nav>"
    "<style>"
    ".xsw{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(12px + env(safe-area-inset-bottom,0px));"
    "z-index:100;display:flex;gap:2px;padding:4px;background:rgba(26,15,10,.94);border-radius:999px;"
    "font:500 13px/1 ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;letter-spacing:0;"
    "box-shadow:0 6px 24px rgba(0,0,0,.28);max-width:calc(100vw - 24px)}"
    ".xsw a,.xsw button{color:#F4EDE8;text-decoration:none;padding:8px 11px;border-radius:999px;border:0;"
    "background:none;font:inherit;cursor:pointer;white-space:nowrap}"
    ".xsw b{font-weight:700}"
    ".xsw a:hover,.xsw button:hover{background:rgba(255,255,255,.12)}"
    ".xsw a[aria-current=page]{background:#FF6B3D;color:#1A0F0A}"
    ".xsw a:focus-visible,.xsw button:focus-visible{outline:2px solid #FF6B3D;outline-offset:2px}"
    "@media (max-width:700px){.xsw span{display:none}}"
    "</style>"
    "<script>(function(){"
    "var here=location.pathname.split('/').pop()||'index.html';"
    "document.querySelectorAll('.xsw a').forEach(function(a){if(a.getAttribute('href')===here)a.setAttribute('aria-current','page')});"
    "var root=document.documentElement,orig=root.getAttribute('data-theme'),btn=document.getElementById('xsw-theme');"
    "var modes=['auto','light','dark'],m='auto';try{m=localStorage.getItem('lid-site-theme')||'auto'}catch(e){}"
    "function apply(){if(m==='auto'){if(orig)root.setAttribute('data-theme',orig);else root.removeAttribute('data-theme')}"
    "else root.setAttribute('data-theme',m);btn.textContent=m==='auto'?'Auto':m==='light'?'Light':'Dark';"
    "btn.setAttribute('aria-label','Color theme: '+btn.textContent)}"
    "btn.addEventListener('click',function(){m=modes[(modes.indexOf(m)+1)%3];try{localStorage.setItem('lid-site-theme',m)}catch(e){}apply()});"
    "apply()})();</script>"
)

POINTER_SYMBOL = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
    f'<symbol id="ptr" viewBox="154 104 28 32"><path d="{POINTER}"/></symbol></svg>'
)


def build():
    for path in sorted(SRC.glob("*.html")):
        text = path.read_text()
        text = (
            text.replace("{{WORDMARK_BADGE}}", WORDMARK_BADGE)
            .replace("{{WORDMARK_BARE}}", WORDMARK_BARE)
            .replace("{{WORDMARK_INK}}", WORDMARK_INK)
            .replace("{{PTR_MASK}}", PTR_MASK)
            .replace("{{POINTER_SYMBOL}}", POINTER_SYMBOL)
            .replace("{{SWITCHER}}", SWITCHER)
        )
        n = 0
        while "{{ICON}}" in text:
            n += 1
            text = text.replace("{{ICON}}", icon(f"{path.stem}-icon-{n}"), 1)
        assert "{{" not in text, f"unfilled placeholder in {path.name}"
        (HERE / path.name).write_text(text)
        print(f"wrote {path.name}")


if __name__ == "__main__":
    build()
