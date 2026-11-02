import os
import shutil
from pathlib import Path

APP_DIR_NAME = "nolagsbrowser"


def config_root() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR_NAME


def data_root() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_DIR_NAME


def cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / APP_DIR_NAME


def runtime_root() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return Path(base) / APP_DIR_NAME


def downloads_dir() -> Path:
    try:
        from gi.repository import GLib

        path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if path:
            return Path(path)
    except Exception:
        pass
    return Path.home() / "Downloads"


def assets_dir() -> Path:
    local = Path(__file__).resolve().parent.parent.parent / "assets"
    if local.is_dir():
        return local
    for candidate in (
        Path("/usr/share/nolagsbrowser/assets"),
        Path("/usr/local/share/nolagsbrowser/assets"),
    ):
        if candidate.is_dir():
            return candidate
    return local


def icons_dir() -> Path:
    project = assets_dir().parent / "data" / "icons"
    if project.is_dir():
        return project
    installed = Path("/usr/share/nolagsbrowser/icons")
    if installed.is_dir():
        return installed
    return Path("/usr/share/icons/hicolor")


def scripts_dir() -> Path:
    local = Path(__file__).resolve().parent.parent.parent / "scripts"
    if local.is_dir():
        return local
    for candidate in (Path("/usr/share/nolagsbrowser/scripts"), Path("/usr/share/nolagsbrowser/bin")):
        if candidate.is_dir():
            return candidate
    return local


def sqlite() -> str:
    return shutil.which("sqlite3") or ""


def ensure_dirs() -> None:
    for path in (config_root(), data_root(), cache_root(), runtime_root()):
        path.mkdir(parents=True, exist_ok=True)
