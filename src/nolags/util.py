import ctypes
import ctypes.util
import mimetypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def human_size(size):
    try:
        size = float(size)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


def human_time(ts):
    try:
        return time.strftime("%d.%m.%Y %H:%M", time.localtime(float(ts)))
    except (TypeError, ValueError, OSError):
        return ""


def day_label(day):
    today = time.strftime("%Y-%m-%d")
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    if day == today:
        return "Сегодня"
    if day == yesterday:
        return "Вчера"
    try:
        return time.strftime("%d %B %Y", time.strptime(day, "%Y-%m-%d"))
    except ValueError:
        return day


def unique_path(directory, filename):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 1
    while True:
        candidate = directory / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def guess_mime(path):
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def xdg_open(target):
    try:
        subprocess.Popen(["xdg-open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def open_folder(path):
    target = Path(path)
    if target.is_file():
        target = target.parent
    if target.exists():
        return xdg_open(target)
    return False


def copy_text(text):
    try:
        from gi.repository import Gdk, Gtk

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text or "", -1)
        clipboard.store()
        return True
    except Exception:
        return False


def get_clipboard_text():
    try:
        from gi.repository import Gdk, Gtk

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = clipboard.wait_for_text()
        return text or ""
    except Exception:
        return ""


def malloc_trim():
    ok = False
    try:
        libc_name = ctypes.util.find_library("c") or "libc.so.6"
        libc = ctypes.CDLL(libc_name)
        libc.malloc_trim(0)
        ok = True
    except Exception:
        ok = False
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.mallopt(-8, 1)
    except Exception:
        pass
    return ok


def rss_kb(pid="self"):
    try:
        with open(f"/proc/{pid}/status", "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def webkit_memory_mb():
    total = 0
    own = rss_kb()
    total += own
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as handle:
                    cmdline = handle.read().replace(b"\x00", b" ").lower()
            except OSError:
                continue
            if b"webkits" in cmdline or b"webkitwebprocess" in cmdline:
                total += rss_kb(entry)
    except OSError:
        pass
    return total / 1024.0


def self_memory_mb():
    return rss_kb() / 1024.0


def cpu_count():
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def clamp(value, low, high):
    return max(low, min(high, value))


def escape_html(text):
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def initials(text):
    parts = [part for part in (text or "?").replace(".", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def color_for(text):
    palette = [
        "#2fb7a4", "#e07a5f", "#6c8cd5", "#c77dff", "#f4a261",
        "#5aa9e6", "#8ac926", "#ff7096", "#00b4d8", "#b5838d",
    ]
    total = sum(ord(char) for char in (text or "x"))
    return palette[total % len(palette)]


def truncate(text, limit=80):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def is_running_tty():
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def has_command(name):
    return shutil.which(name) is not None
