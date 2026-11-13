#!/usr/bin/env python3
"""Write themes/ and skins/ from the shared palette.

themes/Kanagawa <Variant>.json is a Spotifast palette. skins/ holds recolors
of the Spotifast skins in the upstream/ submodule: the Winamp skin (.wsz) and
the two Windows Media Player skins (.wmz).

Usage: scripts/generate.py [--check] [path/to/palette.json]   (default: ../.github/palette.json)

--check writes nothing and exits 1 when a committed file is stale. It compares
archive contents, not bytes: the compressed bytes change with the zlib build.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SKINS = ROOT / "upstream" / "assets" / "skins"
VARIANTS = ["wave", "dragon", "lotus"]
LIGHT = {"lotus"}

# Spotifast palette key -> palette role.
COLORS = {
    "window": "ui.bg",
    "panel": "ui.bg_m1",
    "surface": "ui.bg_p1",
    "surface_hover": "ui.bg_p2",
    "surface_active": "ui.bg_visual",
    "outline": "ui.nontext",
    "text": "ui.fg",
    "secondary": "ui.fg_dim",
    "dim": "syn.comment",
    "accent": "syn.fun",
    "accent_hover": "syn.special1",
    "on_accent": "ui.bg",
    "danger": "diag.error",
    "warning": "diag.warning",
}
# Light variants: syn.comment is below 3:1 on Lotus backgrounds (kde/ makes the same
# choice), and on_accent text on syn.special1 is below 4.5:1, so hover goes darker.
LIGHT_COLORS = {"dim": "ui.float.fg_border", "accent_hover": "syn.statement"}

# Upstream skin colors (upstream/examples/default_skin.rs), by the
# same keys. accent_dark is the color of a lamp that is off.
UPSTREAM = {
    "window": "#0f1114",
    "panel": "#15181c",
    "surface": "#1d2127",
    "surface_hover": "#262b33",
    "surface_active": "#2f353f",
    "outline": "#2a3038",
    "text": "#f2f4f6",
    "secondary": "#a9b1bc",
    "dim": "#6e7784",
    "accent": "#1ed760",
    "on_accent": "#0a140e",
    "accent_dark": "#144a2a",
}
ACCENT_DARK = "ui.bg_search"
# gen.bmp separates its letters with this color. Spotifast reads it, so it stays.
KEEP = {(0x00, 0xC6, 0xFF)}

# Images in a .wmz that are masks, not pictures: never recolor them. A mask is a
# clippingImage or mappingImage, or a backgroundImage in a tag with a clippingColor.
MASK_ATTRS = re.compile(r'(?:clippingImage|mappingImage)="([^"]+)"'
                        r'|backgroundImage="([^"]+)"[^>]*clippingColor')
# .wms attributes that are visible colors.
COLOR_ATTR = re.compile(r'\b((?:foreground|background|item\w*)Color)="(#[0-9a-fA-F]{6})"')

# Grey ramp for the photographic skins, black to white, through the ink and wave
# blues. Light variants run it the other way: a light core, an ink ribbon. ui.bg is
# there twice, so the dark glass core stays flat and light under its text.
RAMP = ["ui.bg_m3", "ui.bg", "ui.bg_p1", "ui.bg_visual", "ui.bg_search", "ui.fg_dim", "ui.fg"]
RAMP_LIGHT = ["ui.bg", "ui.bg", "ui.bg_m1", "ui.bg_m3", "ui.bg_search", "ui.nontext", "ui.fg"]
# assets/great-wave.png: the crest of Hokusai's Great Wave on black, cut from the
# kanagawa-community/kde wallpaper "great-wave-crest". It goes into the
# glass core, as faint as the text on the core needs (MIN_CONTRAST).
WAVE = "great-wave.png"
WAVE_OPACITY = [o / 100 for o in range(45, 0, -5)]
MIN_CONTRAST = 4.5
BOX = re.compile(r'<(?:TEXT|PLAYLIST)\b[^>]*?left="(\d+)" top="(\d+)" width="(\d+)" height="(\d+)"')
# BOX positions are window positions only while the pages that hold them are at 0,0.
PAGE = re.compile(r'<SUBVIEW id="\w+Page" left="(\d+)" top="(\d+)"')

EPOCH = (1980, 1, 1, 0, 0, 0)


def roles(variant):
    """Map each role to its hex color."""
    return {role: c["hex"] for c in variant["colors"].values() for role in c["usage"]}


def rgb(hex_):
    return tuple(int(hex_[i : i + 2], 16) for i in (1, 3, 5))


def hexa(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def rnd(x):
    """Round half away from zero, as Rust's f32::round does."""
    return int(x + 0.5)


def mix(a, b, t):
    return tuple(rnd(x + (y - x) * t) for x, y in zip(a, b))


def shade(c, f):
    return tuple(rnd(v * f) for v in c)


def lift(c, f):
    return tuple(rnd(v + (255 - v) * f) for v in c)


def derived(base):
    """Every color the upstream skin draws, from its base colors, by name."""
    out = dict(base)
    acc, dark = base["accent"], base["accent_dark"]
    for c, name in ((acc, "accent"), (dark, "accent_dark")):
        out[f"{name}_shade"] = shade(c, 0.7)
        out[f"{name}_lift"] = lift(c, 0.25)
    for n in (18, 15):  # eqmain.bmp curve and viscolor.txt bands
        for k in range(n + 1):
            out[f"ramp{n}_{k}"] = mix(acc, dark, k / n)
    return out


def skin_table(r):
    """Upstream skin color -> Kanagawa color. Fails on an ambiguous source."""
    src = derived({k: rgb(v) for k, v in UPSTREAM.items()})
    base = {k: rgb(r[COLORS[k]]) for k in UPSTREAM if k != "accent_dark"}
    base["accent_dark"] = rgb(r[ACCENT_DARK])
    dst = derived(base)
    table = {c: c for c in KEEP}
    for name, c in src.items():
        if table.setdefault(c, dst[name]) != dst[name]:
            sys.exit(f"upstream color {hexa(c)} has two meanings")
    return table


def recolor_pixel(p, ramp, accent):
    """Photographic pixel: grey value onto a ramp of roles, green toward the accent."""
    r, g, b, a = p
    hi = max(r, g, b)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    green = max(g - max(r, b), 0) / 255  # absolute: faint tints in the glass stay grey
    n = len(ramp) - 1
    i = min(int(lum * n), n - 1)
    neutral = mix(ramp[i], ramp[i + 1], lum * n - i)
    lit = shade(accent, hi / 215) if hi <= 215 else lift(accent, (hi - 215) / 40)
    return (*mix(neutral, lit, min(green * 2, 1.0)), a)


def luminance(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = map(lin, c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def add_wave(core, boxes, text):
    """Lay the wave over the opaque part of the core, bottom left, covering it.

    Uses the strongest WAVE_OPACITY at which every text color keeps MIN_CONTRAST
    on every core pixel under a text box.
    """
    art = Image.open(ROOT / "assets" / WAVE).convert("RGB")
    alpha = core.getchannel("A")
    x0, y0, x1, y1 = alpha.getbbox()
    scale = max((x1 - x0) / art.width, (y1 - y0) / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    layer = Image.new("RGB", core.size)
    layer.paste(art, (x0, y1 - art.height))
    # The art is a cutout on black: black is not wave.
    shape = layer.convert("L").point(lambda v: 255 if v > 12 else 0)
    under = [(x, y) for l, t, w, h in boxes for y in range(t, t + h) for x in range(l, l + w)
             if 0 <= x < core.width and 0 <= y < core.height and alpha.getpixel((x, y)) == 255]
    for opacity in WAVE_OPACITY:
        mask = shape.point(lambda v: round(v * opacity))
        out = Image.composite(layer.convert("RGBA"), core, mask)
        out.putalpha(alpha)
        if all(contrast(out.getpixel(p), c) >= MIN_CONTRAST for c in text for p in under):
            return out
    sys.exit("the wave leaves no readable text even at the lowest opacity")


def zip_bytes(files):
    """A zip with sorted names and fixed times."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[name], compresslevel=9)
    return buf.getvalue()


def text_colors(text, table):
    """Rewrite r,g,b lines (viscolor.txt) and #RRGGBB values (pledit.txt) by the table."""

    def look(c):
        if c not in table:
            sys.exit(f"unknown upstream color {hexa(c)}")
        return table[c]

    text = re.sub(
        r"^(\d+),(\d+),(\d+)",
        lambda m: ",".join(map(str, look(tuple(map(int, m.groups()))))),
        text,
        flags=re.M,
    )
    return re.sub(r"#[0-9A-Fa-f]{6}", lambda m: hexa(look(rgb(m[0]))).upper(), text)


def wsz(table):
    out = {}
    with zipfile.ZipFile(SKINS / "spotifast.wsz") as z:
        for name in z.namelist():
            data = z.read(name)
            if name.lower().endswith(".bmp"):
                im = Image.open(io.BytesIO(data)).convert("RGB")
                unknown = set(im.get_flattened_data()) - table.keys()
                if unknown:
                    sys.exit(f"{name}: unknown colors {sorted(map(hexa, unknown))}")
                im.putdata([table[p] for p in im.get_flattened_data()])
                b = io.BytesIO()
                im.save(b, "BMP")
                data = b.getvalue()
            elif name.lower().endswith(".txt"):
                data = text_colors(data.decode(), table).encode()
            out[name] = data
    return zip_bytes(out)


def wmz(src, title, table, ramp, accent):
    out = {}
    with zipfile.ZipFile(src) as z:
        files = {n: z.read(n) for n in z.namelist()}
    wms_name = next(n for n in files if n.endswith(".wms"))
    wms = files[wms_name].decode()
    masks = {a or b for a, b in MASK_ATTRS.findall(wms)}

    # A .wms color that is not in the table (a glow, a pane background) gets the
    # same recolor as a picture pixel.
    def color(m):
        c = rgb(m[2])
        new = table[c] if c in table else recolor_pixel((*c, 255), ramp, accent)[:3]
        return f'{m[1]}="{hexa(new)}"'

    wms = COLOR_ATTR.sub(color, wms)
    wms = re.sub(r'<THEME title="[^"]*" author="[^"]*" copyright="[^"]*"',
                 f'<THEME title="{title}" author="Spotifast, recolored by Kanagawa Community" '
                 'copyright="Recolor of a Spotifast skin, MIT, Carmine Paolino"', wms)
    for name, data in files.items():
        if name == wms_name:
            data = wms.encode()
        elif name.endswith(".png") and name not in masks:
            im = Image.open(io.BytesIO(data)).convert("RGBA")
            im.putdata([recolor_pixel(p, ramp, accent) for p in im.get_flattened_data()])
            if name == "core.png":
                if any(m != ("0", "0") for m in PAGE.findall(wms)):
                    sys.exit(f"{src.name}: a page is not at 0,0; the text boxes need its offset")
                boxes = [tuple(map(int, m)) for m in BOX.findall(wms)]
                im = add_wave(im, boxes, [table[rgb(UPSTREAM[k])] for k in ("text", "secondary")])
            b = io.BytesIO()
            im.save(b, "PNG", compress_level=9)
            data = b.getvalue()
        elif name == "viscolor.txt":
            data = text_colors(data.decode(), table).encode()
        out[name] = data
    return zip_bytes(out)


def palette(r, light):
    colors = {k: r[v] for k, v in (COLORS | (LIGHT_COLORS if light else {})).items()}
    return json.dumps({"base": "light" if light else "dark", "colors": colors}, indent=2) + "\n"


def content(path, data):
    """What a file holds: decoded pixels for images, members for archives."""
    if path.suffix not in (".wsz", ".wmz"):
        return data
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            member = z.read(name)
            if name.lower().endswith((".png", ".bmp")):
                im = Image.open(io.BytesIO(member))
                member = (im.mode, im.size, im.tobytes())
            out[name] = member
    return out


def main():
    args = sys.argv[1:]
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    path = Path(args[0]) if args else ROOT.parent / ".github" / "palette.json"
    stale, written = [], set()
    variants = json.loads(path.read_text())["variants"]
    for v in VARIANTS:
        r = roles(variants[v])
        name = f"Kanagawa {v.capitalize()}"
        light = v in LIGHT
        table = skin_table(r)
        ramp = [rgb(r[e]) for e in (RAMP_LIGHT if light else RAMP)]
        accent = rgb(r[COLORS["accent"]])
        outputs = {
            ROOT / "themes" / f"{name}.json": palette(r, light).encode(),
            ROOT / "skins" / f"{name}.wsz": wsz(table),
            ROOT / "skins" / f"{name} Tall.wmz": wmz(
                SKINS / "spotifast-ribbon.wmz", f"{name} Tall", table, ramp, accent),
            ROOT / "skins" / f"{name} Wide.wmz": wmz(
                SKINS / "spotifast-wide.wmz", f"{name} Wide", table, ramp, accent),
        }
        for out, data in outputs.items():
            written.add(out)
            if check:
                if not out.exists() or content(out, out.read_bytes()) != content(out, data):
                    stale.append(out)
                continue
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(data)
            print(out.relative_to(ROOT))
    if check:  # files the generator no longer writes
        stale += sorted(p for d in ("themes", "skins") for p in (ROOT / d).glob("*") if p not in written)
    for out in stale:
        print(f"stale: {out.relative_to(ROOT)}")
    if stale:
        sys.exit(1)


if __name__ == "__main__":
    main()
