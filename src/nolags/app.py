import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2

from . import APP_ID, APP_NAME, APP_VERSION, paths
from .settings import Settings
from .window import MainWindow

CSS = """
@define-color nlb_accent #2fb7a4;
@define-color nlb_bg mix(@theme_bg_color, @theme_base_color, 0.5);

.nlb-toolbar {
    background: @theme_bg_color;
    border-bottom: 1px solid alpha(@theme_fg_color, 0.10);
}
.nlb-toolbar button {
    min-height: 26px;
    min-width: 26px;
    padding: 3px;
    border-radius: 8px;
    background: transparent;
    border: none;
    box-shadow: none;
}
.nlb-toolbar button:hover { background: alpha(@theme_fg_color, 0.09); }
.nlb-toolbar button:active { background: alpha(@theme_fg_color, 0.16); }
.nlb-address entry {
    border-radius: 12px;
    padding: 6px 10px;
    min-height: 22px;
}
.nlb-bookmarks {
    background: alpha(@theme_fg_color, 0.035);
    border-bottom: 1px solid alpha(@theme_fg_color, 0.08);
}
.nlb-bookmarks button {
    padding: 2px 6px;
    border-radius: 7px;
    background: transparent;
    border: none;
    box-shadow: none;
    font-size: 0.92em;
}
.nlb-bookmarks button:hover { background: alpha(@theme_fg_color, 0.10); }
.nlb-tabstrip { padding: 0 2px; }
.nlb-tab {
    min-height: 30px;
    min-width: 60px;
    max-width: 230px;
    padding: 0;
    border-radius: 9px;
    border: none;
    background: transparent;
    box-shadow: none;
    transition: background 120ms ease;
}
.nlb-tab:hover { background: alpha(@theme_fg_color, 0.08); }
.nlb-tab:checked {
    background: @theme_base_color;
    box-shadow: inset 0 0 0 1px alpha(@theme_fg_color, 0.10);
}
.nlb-tab label { font-size: 0.92em; }
.nlb-notebook > header { border: none; background: transparent; }
.nlb-tab-close {
    padding: 0;
    min-width: 18px;
    min-height: 18px;
    border-radius: 6px;
    background: transparent;
    border: none;
    box-shadow: none;
}
.nlb-tab-close:hover { background: alpha(@theme_fg_color, 0.14); }
.nlb-toast {
    background: alpha(@theme_fg_color, 0.88);
    color: @theme_bg_color;
    padding: 8px 16px;
    border-radius: 999px;
    font-size: 0.92em;
}
.nlb-statusbar {
    background: alpha(@theme_fg_color, 0.04);
    border-top: 1px solid alpha(@theme_fg_color, 0.08);
    font-size: 0.86em;
}
.nlb-findbar {
    background: @theme_bg_color;
    border-bottom: 1px solid alpha(@theme_fg_color, 0.10);
}
.nlb-findbar entry { border-radius: 9px; }
.nlb-dim { opacity: 0.62; font-size: 0.9em; }
.nlb-badge { font-size: 0.78em; opacity: 0.85; }
.nlb-menu-item {
    padding: 0;
    border-radius: 8px;
    border: none;
    background: transparent;
    box-shadow: none;
}
.nlb-menu-item:hover { background: alpha(@theme_fg_color, 0.09); }
.nlb-menu-header { font-size: 0.82em; opacity: 0.55; font-weight: 600; }
.nlb-danger { color: #c0392b; }
.nlb-headerbtn {
    padding: 2px;
    border-radius: 8px;
    background: transparent;
    border: none;
    box-shadow: none;
}
.nlb-headerbtn:hover { background: alpha(@theme_fg_color, 0.10); }
.nlb-settings-side {
    background: alpha(@theme_fg_color, 0.04);
    border-right: 1px solid alpha(@theme_fg_color, 0.08);
}
.nlb-settings-side row { border-radius: 9px; margin: 2px 6px; }
.nlb-settings-side row:selected { background: alpha(@nlb_accent, 0.22); }
.nlb-loading {
    background-image: linear-gradient(to right, alpha(@nlb_accent, 0.35), transparent);
}
entry.nlb-loading { border-color: alpha(@nlb_accent, 0.65); }
"""


def load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS.encode("utf-8"))
    except Exception:
        return
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


class NoLagsApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.settings = None
        self.windows = []
        self._initial_urls = []

    def do_startup(self):
        Gtk.Application.do_startup(self)
        paths.ensure_dirs()
        self.settings = Settings()
        load_css()
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", self.settings.get("ui_theme") == "dark")
        context = WebKit2.WebContext.get_default()
        try:
            context.set_cache_model(
                WebKit2.CacheModel.DOCUMENT_VIEWER
                if self.settings.get("low_memory_mode")
                else WebKit2.CacheModel.DOCUMENT_BROWSER
            )
        except Exception:
            pass
        try:
            context.connect("download-started", self._on_download_started)
        except Exception:
            pass
        try:
            manager = context.get_cookie_manager()
            policy = (
                WebKit2.CookieAcceptPolicy.NO_THIRD_PARTY
                if self.settings.get("block_third_party_cookies")
                else WebKit2.CookieAcceptPolicy.ALWAYS
            )
            manager.set_accept_policy(policy)
        except Exception:
            pass
        try:
            data_manager = context.get_website_data_manager()
            data_manager.set_itp_enabled(bool(self.settings.get("itp")))
            data_manager.set_favicons_enabled(True)
        except Exception:
            pass
        try:
            data_manager = context.get_website_data_manager()
            proxy = WebKit2.NetworkProxySettings.new(os.environ.get("http_proxy") or None, None)
            data_manager.set_network_proxy_settings(
                WebKit2.NetworkProxyMode.CUSTOM if os.environ.get("http_proxy") else WebKit2.NetworkProxyMode.DEFAULT,
                proxy if os.environ.get("http_proxy") else None,
            )
        except Exception:
            pass
        self._scheme_registered = False

    def _ensure_scheme(self, window):
        return None

    def _on_download_started(self, _context, download):
        for window in self.get_windows():
            if isinstance(window, MainWindow):
                window._on_download_started(_context, download)
                return

    def do_activate(self):
        window = self.get_active_window()
        if not isinstance(window, MainWindow):
            window = MainWindow(self, self.settings)
            self._ensure_scheme(window)
            self.add_window(window)
            self.windows.append(window)
        window.present()

    def do_open(self, files, _hint):
        urls = [file.get_uri() for file in files]

        def create():
            window = MainWindow(self, self.settings, urls=urls)
            self._ensure_scheme(window)
            self.add_window(window)
            self.windows.append(window)
            window.present()
            return False

        GLib.idle_add(create)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        urls = [arg for arg in args if not arg.startswith("-")]
        private = "--private" in args or "-p" in args
        self.activate()
        if urls:
            window = self.get_active_window()
            if isinstance(window, MainWindow):
                for url in urls:
                    window.create_tab(url)
        return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    if "--version" in argv:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    app = NoLagsApplication()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main())
