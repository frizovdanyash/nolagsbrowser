import copy
import json
import os
from pathlib import Path

from . import paths

DEFAULTS = {
    "home_page": "nolags://newtab",
    "startup_mode": "newtab",
    "startup_urls": [],
    "search_engine": "duckduckgo",
    "custom_search": "",
    "custom_search_name": "Custom",
    "restore_session": True,
    "ask_quit_multiple": True,
    "confirm_close_tabs": False,
    "close_button_on_tabs": True,
    "tab_position": "top",
    "tab_min_width": 60,
    "tab_max_width": 220,
    "show_bookmarks_bar": True,
    "show_statusbar": False,
    "show_tab_tooltips": True,
    "tabs_as_list": False,
    "new_tab_focus_address": True,
    "open_new_tabs_in_background": False,
    "switch_to_new_tabs": True,
    "inherit_zoom": True,
    "default_zoom": 1.0,
    "minimum_zoom": 0.25,
    "maximum_zoom": 5.0,
    "load_images": True,
    "enable_javascript": True,
    "enable_webgl": True,
    "accelerated_compositing": "ondemand",
    "smooth_scrolling": True,
    "autoplay": "gesture",
    "user_agent_mode": "chrome",
    "custom_user_agent": "",
    "dnt": True,
    "block_third_party_cookies": True,
    "itp": True,
    "block_popups": True,
    "load_ads_hosts": False,
    "hardware_acceleration": True,
    "tab_discard_delay": 180,
    "auto_discard": True,
    "low_memory_mode": True,
    "memory_trim_interval": 25,
    "preload_new_tab": False,
    "lazy_favicons": True,
    "restore_crashed_tabs": True,
    "suggestions_enabled": True,
    "history_suggestions": True,
    "bookmark_suggestions": True,
    "suggestions_limit": 8,
    "download_dir": "",
    "ask_download_dir": False,
    "auto_open_downloads": False,
    "clear_on_exit": False,
    "clear_on_exit_options": {
        "history": False,
        "cookies": False,
        "cache": True,
        "downloads": False,
    },
    "ui_theme": "system",
    "compact_mode": False,
    "stripe_toolbar": True,
    "toolbar_style": "icons",
    "show_paw_loader": True,
    "show_frame_warning": True,
    "highlight_domains": True,
    "show_full_url": False,
    "trim_trailing_slash": True,
    "ctrl_tab_cycles": True,
    "keyboard_shortcuts": True,
    "mouse_gestures": False,
    "middle_click_paste": True,
    "jump_to_start_on_reload": True,
    "single_instance": True,
    "accent_color": "#2fb7a4",
}


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else paths.config_root() / "settings.json"
        self._data = copy.deepcopy(DEFAULTS)
        self._callbacks = []
        self.load()

    def load(self):
        if self.path.is_file():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for key, value in raw.items():
                        if key in self._data:
                            self._data[key] = value
                        else:
                            self._data[key] = value
            except (OSError, ValueError):
                pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self.save()
        for callback in list(self._callbacks):
            try:
                callback(key, value)
            except Exception:
                pass

    def update(self, values):
        for key, value in values.items():
            self.set(key, value)

    def toggle(self, key):
        self.set(key, not bool(self.get(key)))
        return bool(self.get(key))

    def on_change(self, callback):
        self._callbacks.append(callback)

    def as_dict(self):
        return copy.deepcopy(self._data)
