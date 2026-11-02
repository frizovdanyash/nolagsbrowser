import functools
from pathlib import Path

from . import paths

ASSET_CACHE = {}


def _asset_dir():
    return paths.assets_dir() / "mascot"


def mascot_file(variant="hero"):
    names = {
        "hero": "mascot.png",
        "happy": "mascot_happy.png",
        "peek": "mascot_peek.png",
        "sleep": "mascot_sleep.png",
    }
    candidate = _asset_dir() / names.get(variant, "mascot.png")
    if candidate.is_file():
        return candidate
    fallback = _asset_dir() / "mascot.png"
    if fallback.is_file():
        return fallback
    return None


@functools.lru_cache(maxsize=32)
def mascot_pixbuf(size=128, variant="hero"):
    import gi

    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf

    path = mascot_file(variant)
    if not path:
        return None
    if size in ASSET_CACHE:
        return ASSET_CACHE[size]
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, -1, True)
    except Exception:
        return None
    ASSET_CACHE[size] = pixbuf
    return pixbuf


def draw_mascot(cr, size, x=0, y=0, variant="hero"):
    pixbuf = mascot_pixbuf(int(size), variant)
    if not pixbuf:
        return False
    from gi.repository import Gdk, GdkPixbuf

    surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
    cr.save()
    cr.set_source_surface(surface, x, y)
    cr.paint()
    cr.restore()
    return True


def mascot_data_uri(variant="hero", size=256):
    import base64

    pixbuf = mascot_pixbuf(size, variant)
    if not pixbuf:
        return ""
    ok, buf = pixbuf.save_to_bufferv("png", [], [])
    if not ok:
        return ""
    return "data:image/png;base64," + base64.b64encode(buf).decode("ascii")


def logo_uri(size=64):
    path = paths.icons_dir() / f"{size}x{size}" / "apps" / "nolagsbrowser.png"
    if not path.is_file():
        path = paths.icons_dir() / "scalable" / "apps" / "nolagsbrowser.svg"
    if not path.is_file():
        return ""
    import base64

    try:
        data = path.read_bytes()
    except OSError:
        return ""
    mime = "svg+xml" if path.suffix == ".svg" else "png"
    return f"data:image/{mime};base64," + base64.b64encode(data).decode("ascii")


PAW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">
<g fill="{color}">
<ellipse cx="32" cy="42" rx="16" ry="13"/>
<ellipse cx="13" cy="27" rx="7" ry="9"/>
<ellipse cx="25" cy="17" rx="7" ry="9.5"/>
<ellipse cx="39" cy="17" rx="7" ry="9.5"/>
<ellipse cx="51" cy="27" rx="7" ry="9"/>
</g></svg>"""


def paw_svg(size=24, color="#2fb7a4"):
    return PAW_SVG.format(size=size, color=color)
