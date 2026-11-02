import json
import os
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango, WebKit2

from . import APP_NAME, APP_VERSION, USER_AGENT, dialogs, mascot, pages, search, util, widgets
from .adblock import USER_STYLES, AdBlocker, check_internet
from .settings import Settings
from .settings_ui import SettingsWindow
from .storage import Storage

CHIPS = [
    ("GitHub", "https://github.com"),
    ("YouTube", "https://youtube.com"),
    ("Wikipedia", "https://ru.wikipedia.org"),
    ("Habr", "https://habr.com"),
    ("Stack Overflow", "https://stackoverflow.com"),
    ("Reddit", "https://reddit.com"),
]


_SCHEME_CONTEXTS = set()


def _register_context_scheme(context, callback):
    key = id(context)
    if key in _SCHEME_CONTEXTS:
        return False
    try:
        context.register_uri_scheme("nolags", callback)
    except Exception:
        _SCHEME_CONTEXTS.add(key)
        return False
    _SCHEME_CONTEXTS.add(key)
    return True


class Tab:
    last_zoom = 1.0

    def __init__(self, window, url=None, pinned=False):
        self.window = window
        self.settings = window.settings
        self.pinned = pinned
        self.discarded = False
        self.reader = False
        self.zoom = Tab.last_zoom if self.settings.get("inherit_zoom") else float(self.settings.get("default_zoom") or 1.0)
        self.url = url or ""
        self.title = "Новая вкладка"
        self.last_active = time.time()
        self.secure = False
        self._style_sheet = None
        self._reader_sheet = None
        self.custom_style_sheet = None
        self.host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.view = None
        self.create_view()
        if url:
            self.load(url)

    def create_view(self):
        if self.window.private_context is not None:
            view = WebKit2.WebView.new_with_context(self.window.private_context)
        else:
            view = WebKit2.WebView()
        self.view = view
        self.apply_settings()
        view.set_zoom_level(self.zoom)
        self.wire()
        self.host.pack_start(view, True, True, 0)
        view.show()

    def apply_settings(self):
        settings = self.view.get_settings()
        get = self.settings.get
        settings.set_enable_javascript(bool(get("enable_javascript")))
        settings.set_auto_load_images(bool(get("load_images")))
        settings.set_enable_webgl(bool(get("enable_webgl")))
        settings.set_enable_smooth_scrolling(bool(get("smooth_scrolling")))
        settings.set_enable_developer_extras(True)
        settings.set_enable_media_stream(True)
        settings.set_enable_webaudio(True)
        settings.set_enable_mediasource(True)
        settings.set_enable_encrypted_media(True)
        settings.set_enable_site_specific_quirks(True)
        settings.set_enable_dns_prefetching(not bool(get("low_memory_mode")))
        settings.set_enable_page_cache(not bool(get("low_memory_mode")))
        settings.set_enable_offline_web_application_cache(False)
        settings.set_enable_html5_local_storage(True)
        settings.set_enable_html5_database(False)
        settings.set_enable_media(bool(get("load_images")) or True)
        settings.set_media_playback_requires_user_gesture(get("autoplay") != "allow")
        settings.set_media_playback_allows_inline(True)
        mode = str(get("accelerated_compositing") or "ondemand")
        policy_map = {
            "always": WebKit2.HardwareAccelerationPolicy.ALWAYS,
            "ondemand": WebKit2.HardwareAccelerationPolicy.ALWAYS,
        }
        if hasattr(WebKit2.HardwareAccelerationPolicy, "NEVER"):
            policy_map["never"] = WebKit2.HardwareAccelerationPolicy.NEVER
        policy = policy_map.get(mode, WebKit2.HardwareAccelerationPolicy.ALWAYS)
        try:
            settings.set_hardware_acceleration_policy(policy)
        except Exception:
            pass
        try:
            settings.set_enable_back_forward_navigation_gestures(True)
        except Exception:
            pass
        try:
            settings.set_javascript_can_access_clipboard(False)
            settings.set_javascript_can_open_windows_automatically(False)
        except Exception:
            pass
        ua_mode = str(get("user_agent_mode") or "chrome")
        if ua_mode == "custom" and get("custom_user_agent"):
            ua = str(get("custom_user_agent"))
        elif ua_mode == "firefox":
            ua = (
                "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
            )
        elif ua_mode == "auto":
            ua = None
        else:
            ua = USER_AGENT
        if ua:
            settings.set_user_agent(ua)
        if get("autoplay") == "mute":
            self.view.set_is_muted(True)
        self.apply_user_style()

    def apply_user_style(self):
        ucm = self.view.get_user_content_manager()
        if self._style_sheet is not None:
            try:
                ucm.remove_style_sheet(self._style_sheet)
            except Exception:
                pass
            self._style_sheet = None
        style = str(self.settings.get("site_style") or "none")
        css = USER_STYLES.get(style) or ""
        if css:
            sheet = WebKit2.UserStyleSheet.new(
                css,
                WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                WebKit2.UserStyleLevel.USER,
                None,
                None,
            )
            ucm.add_style_sheet(sheet)
            self._style_sheet = sheet
        custom = self.settings.get("custom_css") or ""
        if custom:
            sheet = WebKit2.UserStyleSheet.new(
                custom,
                WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                WebKit2.UserStyleLevel.USER,
                None,
                None,
            )
            ucm.add_style_sheet(sheet)

    def wire(self):
        view = self.view
        ucm = view.get_user_content_manager()
        try:
            ucm.register_script_message_handler("nl")
            ucm.connect("script-message-received::nl", self._on_js_message)
        except Exception:
            pass
        view.connect("load-changed", self._on_load_changed)
        view.connect("load-failed", self._on_load_failed)
        view.connect("notify::title", self._on_title)
        view.connect("notify::uri", self._on_uri)
        view.connect("notify::favicon", self._on_favicon)
        view.connect("notify::estimated-load-progress", self._on_progress)
        view.connect("notify::is-playing-audio", self._on_audio)
        view.connect("notify::is-muted", self._on_audio)
        view.connect("mouse-target-changed", self._on_mouse_target)
        view.connect("context-menu", self._on_context_menu)
        view.connect("create", self._on_create)
        view.connect("permission-request", self._on_permission)
        view.connect("web-process-terminated", self._on_process_terminated)
        view.connect("enter-fullscreen", self._on_enter_fullscreen)
        view.connect("leave-fullscreen", self._on_leave_fullscreen)
        view.connect("close", self._on_close_request)
        view.connect("print", self._on_print_request)
        view.connect("ready-to-show", self._on_ready_to_show)
        view.connect("scroll-event", self._on_scroll)
        view.connect("button-press-event", self._on_button_press)
        view.connect("button-release-event", self._on_button_release)
        try:
            view.connect("run-file-chooser", self._on_file_chooser)
        except Exception:
            pass
        find_controller = view.get_find_controller()
        find_controller.connect("found-text", self._on_found_text)
        find_controller.connect("failed-to-find-text", self._on_found_none)

    def _on_js_message(self, _ucm, value):
        try:
            if hasattr(value, "get_js_value"):
                value = value.get_js_value()
            raw = value.to_json(0)
        except Exception:
            return
        data = None
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (TypeError, ValueError):
                return
        if isinstance(data, dict):
            self.window.handle_page_message(self, data)

    def _on_found_text(self, _controller, count):
        self.window.find_bar.set_count(count)

    def _on_found_none(self, _controller):
        self.window.find_bar.set_count(0)

    def _on_ready_to_show(self, _view):
        if self.window.current_tab is self:
            self.view.grab_focus()

    def _on_scroll(self, _view, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.window.zoom_in()
                return True
            if event.direction == Gdk.ScrollDirection.DOWN:
                self.window.zoom_out()
                return True
        return False

    def _on_button_press(self, _view, event):
        if event.button == 2:
            self.window.gesture_start(event.x_root)
        return False

    def _on_button_release(self, _view, event):
        if event.button == 2:
            self.window.gesture_end(event.x_root)
        return False

    def _on_print_request(self, view, _print_op):
        self.window.print_page()
        return True

    def _on_close_request(self, _view):
        self.window.close_tab(self)
        return True

    def _on_enter_fullscreen(self, _view):
        self.window.set_fullscreen(True)

    def _on_leave_fullscreen(self, _view):
        self.window.set_fullscreen(False)

    def _on_file_chooser(self, _view, request):
        try:
            request.select_file(self.window, None)
            return True
        except Exception:
            return False

    def _on_process_terminated(self, _view, reason):
        if reason == WebKit2.WebProcessTerminationReason.CRASHED:
            if self.settings.get("restore_crashed_tabs") and self.url:
                self.window.toast("Вкладка упала — перезагружаю")
                GLib.timeout_add(400, lambda: (self.load(self.url), False)[1])
            else:
                self.window.toast("Веб-процесс завершился")
        return False

    def _on_permission(self, _view, request):
        try:
            request.deny()
        except Exception:
            pass
        return True

    def _on_create(self, _view, navigation_action):
        return self.window.create_popup_view(navigation_action)

    def _on_context_menu(self, _view, menu, event, hit):
        self.window.apply_context_extras(menu, hit)
        return False

    def _on_mouse_target(self, _view, hit, _modifiers):
        link = hit.get_link_uri() if hit else None
        title = hit.get_link_title() if hit else None
        media = hit.get_image_uri() if hit else None
        if link:
            self.window.status_bar.set_link(title or link)
            self.window.show_status(True)
        elif media:
            self.window.status_bar.set_link(media)
            self.window.show_status(True)
        else:
            self.window.status_bar.set_link("")
            if not self.settings.get("show_statusbar"):
                self.window.show_status(False)

    def _on_audio(self, view, _param):
        playing = bool(view.get_property("is-playing-audio"))
        muted = bool(view.get_is_muted())
        self.label.set_audio(playing, muted)
        if self.window.current_tab is self:
            self.window.mute_button.set_visible(playing or muted)

    def _on_progress(self, view, _param):
        if self.window.current_tab is self:
            self.window.address.update_security(view.get_uri() or "")
            self.window.address.set_loading_progress(view.get_estimated_load_progress())

    def _on_favicon(self, view, _param):
        surface = view.get_favicon()
        pixbuf = None
        if surface is not None:
            try:
                width = surface.get_width()
                height = surface.get_height()
                pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
                if pixbuf and (pixbuf.get_width() > 24 or pixbuf.get_height() > 24):
                    pixbuf = pixbuf.scale_simple(16, 16, GdkPixbuf.InterpType.BILINEAR)
            except Exception:
                pixbuf = None
        if not pixbuf:
            pixbuf = self.window.letter_icon(self.url)
        try:
            self.label.set_favicon(pixbuf)
        except Exception:
            pass

    def _on_uri(self, view, _param):
        uri = view.get_uri() or ""
        self.url = uri
        self.secure = uri.startswith("https://")
        if self.window.current_tab is self:
            self.window.address.show_url(uri)
            self.window.address.update_security(uri)
            self.window.address.update_star(uri)
        self.window.update_bookmark_star(uri)

    def _on_title(self, view, _param):
        title = view.get_title() or ""
        if not title or title in ("Новая вкладка", "NoLags"):
            title = search.pretty_url(view.get_uri() or "") or title or "Новая вкладка"
        self.title = title
        try:
            self.label.set_title(title)
        except Exception:
            pass
        if self.window.current_tab is self:
            self.window.refresh_window_title()

    def _on_load_changed(self, view, event):
        if event == WebKit2.LoadEvent.STARTED:
            self.label.set_loading(True)
            self.window.refresh_nav_buttons()
            self.window.memory_touched()
        elif event == WebKit2.LoadEvent.FINISHED:
            self.label.set_loading(False)
            self.label.set_loading(False)
            self.window.refresh_nav_buttons()
            self.window.address.set_loading_progress(1.0)
            self.window.memory_touched()
            uri = view.get_uri() or ""
            if uri.startswith(("http://", "https://")):
                self.window.storage.add_history(uri, self.title, search.display_host(uri))
            self.window.update_bookmark_star(uri)
            self.window.status_bar.set_zoom(view.get_zoom_level())
            self.window.on_tab_loaded(self)
        elif event == WebKit2.LoadEvent.COMMITTED:
            self.window.refresh_nav_buttons()

    def _on_load_failed(self, view, event, uri, error):
        if isinstance(error, GLib.Error):
            message = error.message
            code = error.code
        else:
            message = str(error)
            code = 0
        if code == WebKit2.NetworkError.CANCELLED or "cancelled" in message.lower():
            return False
        self.window.show_error_page(self, uri, message)
        return True

    def navigate(self, text, from_omnibox=False, force_search=False):
        if force_search:
            target = search.search_url(self.settings, text)
        else:
            target = search.normalize_input(text, self.settings)
        if target:
            self.load(target)

    def load(self, url):
        self.url = url
        self.window.memory_touched()
        if url.startswith("nolags://error") or url.startswith("nolags://shortcuts"):
            self.view.load_uri(url)
            return
        self.view.load_uri(url)

    def reload(self, ignore_cache=False):
        if self.discarded:
            self.revive()
            return
        if ignore_cache:
            self.view.reload_bypass_cache()
        else:
            self.view.reload()

    def stop(self):
        self.view.stop_loading()

    def go_back(self):
        if self.view.can_go_back():
            self.view.go_back()

    def go_forward(self):
        if self.view.can_go_forward():
            self.view.go_forward()

    def toggle_mute(self):
        muted = not self.view.get_is_muted()
        self.view.set_is_muted(muted)
        self.window.toast("Звук вкладки выключен" if muted else "Звук вкладки включён")

    def set_zoom(self, zoom):
        zoom = util.clamp(zoom, float(self.settings.get("minimum_zoom")), float(self.settings.get("maximum_zoom")))
        self.zoom = zoom
        Tab.last_zoom = zoom
        self.view.set_zoom_level(zoom)
        self.window.status_bar.set_zoom(zoom)
        self.window.toast(f"Масштаб {int(round(zoom * 100))}%")

    def toggle_reader(self):
        ucm = self.view.get_user_content_manager()
        if self.reader:
            if self._reader_sheet is not None:
                try:
                    ucm.remove_style_sheet(self._reader_sheet)
                except Exception:
                    pass
                self._reader_sheet = None
            self.reader = False
            self.window.toast("Режим чтения выключен")
            return
        css = __import__("nolags.adblock", fromlist=["READER_CSS"]).READER_CSS
        sheet = WebKit2.UserStyleSheet.new(
            css,
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserStyleLevel.USER,
            None,
            None,
        )
        ucm.add_style_sheet(sheet)
        self._reader_sheet = sheet
        self.reader = True
        self.window.toast("Режим чтения включён")

    def selected_text(self):
        try:
            result = self.view.run_javascript(
                "window.getSelection ? window.getSelection().toString() : ''", None, None
            )
            value = result.get_js_value()
            return value.to_string() or ""
        except Exception:
            return ""

    def discard(self):
        if self.discarded or not self.url or search.is_internal(self.url):
            return False
        if self.view.get_property("is-playing-audio"):
            return False
        self.saved_title = self.title
        try:
            self.view.stop_loading()
        except Exception:
            pass
        self.host.remove(self.view)
        self.view.destroy()
        self.view = None
        self.discarded = True
        self.label.set_loading(False)
        self.label.set_title((self.title or "Вкладка") + " · спит")
        self._build_placeholder()
        return True

    def _build_placeholder(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        pixbuf = mascot.mascot_pixbuf(140, "sleep")
        if pixbuf:
            box.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
        label = Gtk.Label()
        label.set_markup("<b>Вкладка спит</b>")
        box.pack_start(label, False, False, 0)
        hint = Gtk.Label(label="Память освобождена. Откройте вкладку, чтобы загрузить страницу заново.")
        hint.set_line_wrap(True)
        hint.set_max_width_chars(46)
        hint.set_justify(Gtk.Justification.CENTER)
        hint.get_style_context().add_class("nlb-dim")
        box.pack_start(hint, False, False, 0)
        button = Gtk.Button(label="Проснуться")
        button.get_style_context().add_class("suggested-action")
        button.connect("clicked", lambda *_: self.window.select_tab(self))
        button.set_halign(Gtk.Align.CENTER)
        box.pack_start(button, False, False, 0)
        self.placeholder = box
        box.show_all()
        self.host.pack_start(box, True, True, 0)

    def revive(self):
        if not self.discarded:
            return
        for child in self.host.get_children():
            self.host.remove(child)
        self.discarded = False
        url = self.url
        self.create_view()
        if url:
            self.view.load_uri(url)
        self.label.set_title(self.title)

    def destroy(self):
        try:
            if self.view is not None:
                self.view.stop_loading()
                self.host.remove(self.view)
                self.view.destroy()
        except Exception:
            pass
        self.view = None


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, settings=None, private=False, urls=None):
        super().__init__(application=app)
        self.set_title(APP_NAME)
        self.set_default_size(1200, 760)
        self.set_icon_name("nolagsbrowser")
        self.settings = settings or Settings()
        self.storage = Storage()
        self.blocker = AdBlocker(self.settings)
        self.private = private
        self.tabs = []
        self.closed_tabs = []
        self.popups = []
        self.private_context = None
        self.find_bar_ref = None
        self._gesture_x = None
        self._toast_timer = None
        self._mem_timer = None
        self._trim_timer = None
        self._site_zoom = self.storage.meta_get("site_zoom", {}) or {}
        if private:
            try:
                self.private_context = WebKit2.WebContext.new_ephemeral()
            except Exception:
                self.private_context = None
        self._register_schemes()
        self._build_ui()
        self._connect_context()
        self._install_accels()
        self._install_timers()
        self._restore_startup(urls)
        self.connect("delete-event", self._on_delete)
        self.connect("key-press-event", self._on_key_press)
        self.show_all()
        self.apply_ui_settings()
        GLib.idle_add(self._first_focus)

    def _first_focus(self):
        tab = self.current_tab
        if tab is None or tab.view is None:
            return False
        if self.settings.get("new_tab_focus_address") and search.is_internal(tab.url):
            try:
                tab.view.run_javascript("var s=document.getElementById('q'); if(s){s.focus();}", None, None)
            except Exception:
                pass
        else:
            tab.view.grab_focus()
        return False

    def _build_ui(self):
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title(APP_NAME)
        self.set_titlebar(self.header)

        self.new_tab_button = widgets.icon_button("list-add-symbolic")
        self.new_tab_button.set_tooltip_text("Новая вкладка (Ctrl+T)")
        self.new_tab_button.connect("clicked", lambda *_: self.create_tab())
        self.new_tab_button.get_style_context().add_class("nlb-headerbtn")
        self.header.pack_start(self.new_tab_button)

        self.tab_overview_button = widgets.icon_button("view-list-symbolic")
        self.tab_overview_button.set_tooltip_text("Список вкладок")
        self.tab_overview_button.get_style_context().add_class("nlb-headerbtn")
        self.header.pack_start(self.tab_overview_button)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.set_show_tabs(False)
        self.notebook.get_style_context().add_class("nlb-tabs")
        self.notebook.connect("switch-page", self._on_switch_page)

        self.tab_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_strip.get_style_context().add_class("nlb-tabstrip")
        self.tab_strip_align = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.tab_strip_align.pack_start(self.tab_strip, False, False, 0)
        self.tab_strip_scroller = Gtk.ScrolledWindow()
        self.tab_strip_scroller.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        self.tab_strip_scroller.set_propagate_natural_height(True)
        self.tab_strip_scroller.add(self.tab_strip_align)
        self.tab_strip_scroller.connect("button-press-event", self._on_strip_press)
        self.tab_strip_scroller.set_size_request(240, -1)
        self.header.set_custom_title(self.tab_strip_scroller)

        self.download_button = Gtk.Button()
        self.download_button.set_relief(Gtk.ReliefStyle.NONE)
        download_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        download_box.pack_start(widgets.icon_image("folder-download-symbolic"), False, False, 0)
        self.download_badge = Gtk.Label(label="")
        self.download_badge.get_style_context().add_class("nlb-badge")
        download_box.pack_start(self.download_badge, False, False, 0)
        self.download_button.add(download_box)
        self.download_button.set_tooltip_text("Загрузки (Ctrl+J)")
        self.download_button.connect("clicked", lambda *_: self.open_page("nolags://downloads"))
        self.header.pack_end(self.download_button)

        self.menu_button = Gtk.Button()
        self.menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self.menu_button.add(widgets.icon_image("open-menu-symbolic"))
        self.menu_button.set_tooltip_text("Меню браузера")
        self.menu_button.connect("clicked", self._open_menu)
        self.header.pack_end(self.menu_button)

        self.outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.outer)

        self.sidebar_revealer = Gtk.Revealer()
        self.sidebar_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.set_size_request(190, -1)
        self.sidebar_revealer.add(self.sidebar_box)

        self.toolbar_revealer = Gtk.Revealer()
        self.toolbar_revealer.set_reveal_child(True)
        self.toolbar_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.toolbar_revealer.set_transition_duration(120)
        self.toolbar = self._build_toolbar()
        self.toolbar_revealer.add(self.toolbar)
        self.outer.pack_start(self.toolbar_revealer, False, False, 0)

        self.bookmarks_revealer = Gtk.Revealer()
        self.bookmarks_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.bookmarks_revealer.set_transition_duration(120)
        self.bookmarks_bar = self._build_bookmarks_bar()
        self.bookmarks_revealer.add(self.bookmarks_bar)
        self.outer.pack_start(self.bookmarks_revealer, False, False, 0)

        self.find_bar = widgets.FindBar(self)
        self.outer.pack_start(self.find_bar, False, False, 0)

        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        content_box.pack_start(self.sidebar_revealer, False, False, 0)
        content_box.pack_start(self.notebook, True, True, 0)
        self.outer.pack_start(content_box, True, True, 0)

        self.status_bar = widgets.StatusBar()
        self.status_bar.set_reveal_child(bool(self.settings.get("show_statusbar")))
        self.outer.pack_start(self.status_bar, False, False, 0)

        self.toast_revealer = Gtk.Revealer()
        self.toast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.toast_revealer.set_halign(Gtk.Align.CENTER)
        self.toast_label = Gtk.Label(label="")
        self.toast_label.get_style_context().add_class("nlb-toast")
        self.toast_label.set_margin_bottom(18)
        self.toast_revealer.add(self.toast_label)
        overlay = Gtk.Overlay()
        self.outer.remove(content_box)
        overlay.add(content_box)
        overlay.add_overlay(self.toast_revealer)
        overlay.set_overlay_pass_through(self.toast_revealer, True)
        self.outer.pack_start(overlay, True, True, 0)
        self.content_area = content_box
        self.overlay = overlay

        self.tab_search = widgets.TabSearchPopover(self)
        self.tab_overview_button.connect("clicked", lambda *_: self.tab_search.open())

        self.menu = self._build_menu()
        self._build_menu_pages()
        self.menu_pages_ready = True
        self.loader_image = Gtk.Image()
        self.loader_image.set_pixel_size(16)

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar.set_border_width(4)
        bar.set_margin_start(4)
        bar.set_margin_end(4)
        bar.get_style_context().add_class("nlb-toolbar")

        self.back_button = widgets.icon_button("go-previous-symbolic")
        self.back_button.set_tooltip_text("Назад (Alt+←)")
        self.back_button.connect("clicked", lambda *_: self.current_tab and self.current_tab.go_back())
        self.forward_button = widgets.icon_button("go-next-symbolic")
        self.forward_button.set_tooltip_text("Вперёд (Alt+→)")
        self.forward_button.connect("clicked", lambda *_: self.current_tab and self.current_tab.go_forward())
        self.reload_button = Gtk.Button()
        self.reload_button.set_tooltip_text("Обновить (Ctrl+R)")
        self.reload_button.connect("clicked", self._on_reload_clicked)
        self.home_button = widgets.icon_button("go-home-symbolic")
        self.home_button.set_tooltip_text("Домашняя страница (Alt+Home)")
        self.home_button.connect("clicked", lambda *_: self.go_home())
        for button in (self.back_button, self.forward_button, self.reload_button, self.home_button):
            button.set_relief(Gtk.ReliefStyle.NONE)
            bar.pack_start(button, False, False, 0)

        self.address = widgets.AddressBar(self)
        bar.pack_start(self.address, True, True, 6)

        self.mute_button = widgets.icon_button("audio-volume-muted-symbolic")
        self.mute_button.set_tooltip_text("Выключить звук вкладки (Ctrl+Shift+M)")
        self.mute_button.set_relief(Gtk.ReliefStyle.NONE)
        self.mute_button.set_no_show_all(True)
        self.mute_button.set_visible(False)
        self.mute_button.connect("clicked", lambda *_: self.current_tab and self.current_tab.toggle_mute())
        bar.pack_start(self.mute_button, False, False, 0)

        self.reader_button = widgets.icon_button("view-reader-symbolic")
        if not self.reader_button.get_image():
            self.reader_button = widgets.icon_button("x-office-document-symbolic")
        self.reader_button.set_tooltip_text("Режим чтения (Ctrl+Shift+F)")
        self.reader_button.set_relief(Gtk.ReliefStyle.NONE)
        self.reader_button.connect("clicked", lambda *_: self.current_tab and self.current_tab.toggle_reader())
        bar.pack_start(self.reader_button, False, False, 0)

        self.bookmark_button = widgets.icon_button("non-starred-symbolic")
        self.bookmark_button.set_tooltip_text("Добавить в закладки (Ctrl+D)")
        self.bookmark_button.set_relief(Gtk.ReliefStyle.NONE)
        self.bookmark_button.connect("clicked", lambda *_: self.toggle_bookmark_current())
        bar.pack_start(self.bookmark_button, False, False, 0)
        return bar

    def _build_bookmarks_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar.set_border_width(3)
        bar.set_margin_start(4)
        bar.get_style_context().add_class("nlb-bookmarks")
        self.bookmarks_items = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        scroller.set_propagate_natural_height(True)
        scroller.add(self.bookmarks_items)
        bar.pack_start(scroller, True, True, 0)
        self.bookmarks_all_button = Gtk.Button(label="Все закладки")
        self.bookmarks_all_button.set_relief(Gtk.ReliefStyle.NONE)
        self.bookmarks_all_button.connect("clicked", lambda *_: self.open_page("nolags://bookmarks"))
        bar.pack_end(self.bookmarks_all_button, False, False, 0)
        return bar

    def _build_menu(self):
        menu = widgets.MenuPopover(self.menu_button)
        menu.connect("closed", lambda *_: menu.show_page("root"))
        root = menu.page("root")
        self._menu_new_tab = widgets.menu_item("Новая вкладка", "list-add-symbolic", lambda: self.create_tab(), "Ctrl+T")
        self._menu_new_window = widgets.menu_item("Новое окно", "window-new-symbolic", self.new_window, "Ctrl+N")
        self._menu_private = widgets.menu_item("Приватное окно", "view-private-symbolic", self.new_private_window, "Ctrl+Shift+N")
        for item in (self._menu_new_tab, self._menu_new_window, self._menu_private):
            menu.add_widget(item)
        menu.add_separator()
        menu.add_nav("История", "history", "document-open-recent-symbolic")
        menu.add_nav("Закладки", "bookmarks", "user-bookmarks-symbolic")
        menu.add_nav("Загрузки", "downloads", "folder-download-symbolic")
        menu.add_nav("Масштаб", "zoom", "zoom-in-symbolic")
        menu.add_nav("Вид страницы", "style", "applications-graphics-symbolic")
        menu.add_nav("Память и вкладки", "memory", "utilities-system-monitor-symbolic")
        menu.add_nav("Инструменты", "tools", "applications-engineering-symbolic")
        menu.add_separator()
        menu.add_widget(widgets.menu_item("Настройки", "preferences-system-symbolic", self.open_settings, "Ctrl+,"))
        menu.add_widget(widgets.menu_item("Горячие клавиши", "preferences-desktop-keyboard-symbolic", self.show_shortcuts_page, "Ctrl+Shift+/"))
        menu.add_widget(widgets.menu_item("Справка и о браузере", "help-about-symbolic", lambda: self.open_page("nolags://about")))
        menu.add_separator()
        menu.add_widget(widgets.menu_item("Выход", "application-exit-symbolic", self._quit, "Ctrl+Q"))

        history = menu.page("history", "История", "root")
        menu.add_widget(widgets.menu_item("Вся история", "document-open-recent-symbolic", lambda: self.open_page("nolags://history")), "history")
        menu.add_widget(widgets.menu_item("Вернуть закрытую вкладку", "edit-redo-symbolic", self.reopen_closed_tab, "Ctrl+Shift+T"), "history")
        menu.add_widget(widgets.menu_item("Очистить историю…", "user-trash-symbolic", self.clear_data_dialog), "history")

        settings_page = menu.page("sys", "Настройки", "root")
        menu.add_widget(widgets.menu_item("Настройки браузера", "preferences-system-symbolic", self.open_settings), "sys")
        menu.add_widget(widgets.menu_item("Очистить данные…", "user-trash-symbolic", self.clear_data_dialog, "Ctrl+Shift+Delete"), "sys")
        menu.add_widget(widgets.menu_item("Скачать hosts-файл", "document-save-symbolic", self.save_hosts_file), "sys")
        menu.add_widget(widgets.menu_item("Обновить список блокировки", "view-refresh-symbolic", self.update_blocklist), "sys")
        menu.add_widget(widgets.menu_item("Завершить работу", "application-exit-symbolic", self._quit), "sys")
        menu.add_widget(widgets.menu_item("Настройки", "preferences-system-symbolic", self.open_settings))
        return menu

    def _build_menu_pages(self):
        menu = self.menu
        bookmarks = menu.page("bookmarks", "Закладки", "root")
        menu.add_widget(widgets.menu_item("Все закладки", "user-bookmarks-symbolic", lambda: self.open_page("nolags://bookmarks")), "bookmarks")
        menu.add_widget(widgets.menu_item("Добавить текущую страницу", "starred-symbolic", self.toggle_bookmark_current, "Ctrl+D"), "bookmarks")
        menu.add_widget(widgets.menu_item("Добавить все вкладки", "document-save-symbolic", self.bookmark_all_tabs, "Ctrl+Shift+D"), "bookmarks")
        menu.add_widget(widgets.menu_item("Показать панель закладок", "view-list-symbolic", self.toggle_bookmarks_bar, "Ctrl+B"), "bookmarks")
        menu.add_widget(widgets.menu_item("Импорт из HTML…", "document-open-symbolic", self.import_bookmarks), "bookmarks")
        menu.add_widget(widgets.menu_item("Экспорт в HTML…", "document-save-as-symbolic", self.export_bookmarks_html), "bookmarks")

        downloads = menu.page("downloads", "Загрузки", "root")
        menu.add_widget(widgets.menu_item("Все загрузки", "folder-download-symbolic", lambda: self.open_page("nolags://downloads"), "Ctrl+J"), "downloads")
        menu.add_widget(widgets.menu_item("Открыть папку загрузок", "folder-symbolic", lambda: util.open_folder(self.download_dir())), "downloads")
        menu.add_widget(widgets.menu_item("Сохранить страницу…", "document-save-symbolic", self.save_page, "Ctrl+S"), "downloads")

        zoom = menu.page("zoom", "Масштаб", "root")
        menu.add_widget(widgets.menu_item("Увеличить", "zoom-in-symbolic", self.zoom_in, "Ctrl++"), "zoom")
        menu.add_widget(widgets.menu_item("Уменьшить", "zoom-out-symbolic", self.zoom_out, "Ctrl+-"), "zoom")
        menu.add_widget(widgets.menu_item("Сбросить (100%)", "zoom-original-symbolic", self.zoom_reset, "Ctrl+0"), "zoom")
        menu.add_separator("zoom")
        menu.add_widget(widgets.menu_item("Во весь экран", "view-fullscreen-symbolic", self.toggle_fullscreen, "F11"), "zoom")

        style = menu.page("style", "Вид страницы", "root")
        for key, label in (("none", "Как на сайте"), ("dark", "Тёмная тема страниц"), ("sepia", "Сепия"), ("gray", "Чёрно-белая")):
            menu.add_widget(widgets.menu_item(label, "applications-graphics-symbolic", lambda k=key: self.set_site_style(k)), "style")
        menu.add_separator("style")
        menu.add_widget(widgets.menu_item("Режим чтения", "x-office-document-symbolic", lambda: self.current_tab and self.current_tab.toggle_reader(), "Ctrl+Shift+F"), "style")
        menu.add_widget(widgets.menu_item("Мобильный User-Agent", "phone-symbolic", self.toggle_mobile_ua), "style")

        memory = menu.page("memory", "Память и вкладки", "root")
        menu.add_widget(widgets.menu_item("Освободить память", "user-trash-symbolic", self.trim_memory), "memory")
        menu.add_widget(widgets.menu_item("Усыпить неактивные вкладки", "weather-clear-night-symbolic", self.discard_background_tabs), "memory")
        menu.add_widget(widgets.menu_item("Диспетчер вкладок", "utilities-system-monitor-symbolic", self.show_task_manager), "memory")
        menu.add_separator("memory")
        menu.add_switch("Усыплять вкладки", bool(self.settings.get("auto_discard")), lambda state: self.settings.set("auto_discard", state), "memory", "weather-clear-night-symbolic")
        menu.add_switch("Режим низкого потребления", bool(self.settings.get("low_memory_mode")), self.set_low_memory, "memory", "speedometer-symbolic")
        menu.add_switch("Строка состояния", bool(self.settings.get("show_statusbar")), self.set_statusbar, "memory", "utilities-system-monitor-symbolic")

        tools = menu.page("tools", "Инструменты", "root")
        menu.add_widget(widgets.menu_item("Инструменты разработчика", "applications-engineering-symbolic", self.devtools, "F12"), "tools")
        menu.add_widget(widgets.menu_item("Исходный код страницы", "text-x-generic-symbolic", self.view_source, "Ctrl+U"), "tools")
        menu.add_widget(widgets.menu_item("Скриншот страницы", "camera-photo-symbolic", self.screenshot, "Ctrl+Shift+S"), "tools")
        menu.add_widget(widgets.menu_item("Печать", "document-print-symbolic", self.print_page, "Ctrl+P"), "tools")
        menu.add_widget(widgets.menu_item("Сохранить страницу", "document-save-symbolic", self.save_page, "Ctrl+S"), "tools")
        menu.add_widget(widgets.menu_item("Найти на странице", "edit-find-symbolic", lambda: self.find_bar.open(), "Ctrl+F"), "tools")
        menu.add_widget(widgets.menu_item("Командная строка", "utilities-terminal-symbolic", self.show_command_palette, "Ctrl+Shift+P"), "tools")
        menu.add_separator("tools")
        menu.add_widget(widgets.menu_item("Очистить кэш", "edit-clear-symbolic", self.clear_cache), "tools")
        menu.add_widget(widgets.menu_item("Заметка о странице", "accessories-text-editor-symbolic", self.add_note_from_page), "tools")

    def _connect_context(self):
        try:
            context = self.private_context if self.private_context is not None else WebKit2.WebContext.get_default()
            context.connect("download-started", self._on_download_started)
        except Exception:
            pass

    def _install_accels(self):
        self.accel_group = Gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        def bind(accel, callback):
            try:
                key, mods = Gtk.accelerator_parse(accel)
            except Exception:
                return
            if key == 0 and mods == 0:
                return
            self.accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE, lambda *_: (callback(), True)[1])

        bind("<Control>t", lambda: self.create_tab(focus=True))
        bind("<Control>n", self.new_window)
        bind("<Control><Shift>n", self.new_private_window)
        bind("<Control>w", self.close_current_tab)
        bind("<Control><Shift>w", self._quit)
        bind("<Control>q", self._quit)
        bind("<Control>l", lambda: self.address.focus())
        bind("<Alt>d", lambda: self.address.focus())
        bind("<Control>k", lambda: self.address.focus())
        bind("<Control>e", lambda: self.address.focus())
        bind("<Control>f", lambda: self.find_bar.open())
        bind("<Control>g", lambda: self.find_bar.find_next())
        bind("<F3", lambda: self.find_bar.find_next())
        bind("<Control><Shift>g", lambda: self.find_bar.find_previous())
        bind("<Control>r", lambda: self.current_tab and self.current_tab.reload())
        bind("<Control><Shift>r", lambda: self.current_tab and self.current_tab.reload(True))
        bind("<Control>F5", lambda: self.current_tab and self.current_tab.reload(True))
        bind("<Alt>Left", lambda: self.current_tab and self.current_tab.go_back())
        bind("<Alt>Right", lambda: self.current_tab and self.current_tab.go_forward())
        bind("<Alt>Home", self.go_home)
        bind("<Control>Tab", lambda: self.cycle_tab(1))
        bind("<Control><Shift>Tab", lambda: self.cycle_tab(-1))
        bind("<Control><Shift>t", self.reopen_closed_tab)
        bind("<Control>d", self.toggle_bookmark_current)
        bind("<Control><Shift>d", self.bookmark_all_tabs)
        bind("<Control>b", self.toggle_bookmarks_bar)
        bind("<Control>h", lambda: self.open_page("nolags://history"))
        bind("<Control>y", lambda: self.open_page("nolags://history"))
        bind("<Control>j", lambda: self.open_page("nolags://downloads"))
        bind("<Control>p", self.print_page)
        bind("<Control>s", self.save_page)
        bind("<Control><Shift>s", self.screenshot)
        bind("<Control>u", self.view_source)
        bind("<F12", self.devtools)
        bind("<Control><Shift>i", self.devtools)
        bind("<Control><Shift>Delete", self.clear_data_dialog)
        bind("<Control>equal", self.zoom_in)
        bind("<Control>plus", self.zoom_in)
        bind("<Control>minus", self.zoom_out)
        bind("<Control>0", self.zoom_reset)
        bind("<F11", self.toggle_fullscreen)
        bind("<Control><Shift>m", lambda: self.current_tab and self.current_tab.toggle_mute())
        bind("<Control><Shift>p", self.show_command_palette)
        bind("<Control><Shift>f", lambda: self.current_tab and self.current_tab.toggle_reader())
        bind("<Control>comma", self.open_settings)
        bind("<Control>m", lambda: self.iconify())
        bind("<F6", lambda: self.address.focus())
        bind("<Control><Shift>o", lambda: self.open_page("nolags://bookmarks"))
        bind("<Control><Shift>j", lambda: self.open_page("nolags://downloads"))
        bind("<Control>shift>l", lambda: self.address.focus())
        for index in range(1, 10):
            bind(f"<Alt>{index}", lambda i=index: self.select_tab_index(i - 1))
        bind("<Control>9", lambda: self.select_tab_index(len(self.tabs) - 1))

    def _install_timers(self):
        self._mem_timer = GLib.timeout_add_seconds(60, self._discard_tick)
        interval = int(self.settings.get("memory_trim_interval") or 0)
        self._restart_trim_timer(interval)

    def _restart_trim_timer(self, interval):
        if self._trim_timer:
            GLib.source_remove(self._trim_timer)
            self._trim_timer = None
        if interval and interval > 0:
            self._trim_timer = GLib.timeout_add_seconds(max(30, interval * 60), self._trim_tick)

    def _trim_tick(self):
        util.malloc_trim()
        self.update_memory_label()
        return True

    def _discard_tick(self):
        self.update_memory_label()
        if not self.settings.get("auto_discard"):
            return True
        delay = float(self.settings.get("tab_discard_delay") or 0)
        if delay <= 0:
            return True
        if not self.private and len(self.tabs) > 1:
            now = time.time()
            for tab in list(self.tabs):
                if tab is self.current_tab or tab.pinned or tab.discarded:
                    continue
                if now - tab.last_active > delay * 60:
                    if tab.discard():
                        self.toast("Вкладка усыплена для экономии памяти")
        return True

    def update_memory_label(self):
        if self.settings.get("show_statusbar"):
            total = util.webkit_memory_mb()
            self.status_bar.set_memory(f"ОЗУ {total:.0f} МБ · вкладок {len(self.tabs)}")
        else:
            self.status_bar.set_memory("")

    def memory_touched(self):
        pass

    def _on_delete(self, *_args):
        if self.settings.get("ask_quit_multiple") and len([t for t in self.tabs if not t.pinned]) > 1:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="Закрыть NoLags Browser?",
            )
            dialog.format_secondary_text(f"Открыто вкладок: {len(self.tabs)}. Сеанс можно будет восстановить при следующем запуске.")
            dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
            dialog.add_button("Закрыть браузер", Gtk.ResponseType.OK)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return True
        self._save_session()
        if self.settings.get("clear_on_exit"):
            self._clear_on_exit()
        try:
            for tab in list(self.tabs):
                tab.destroy()
        except Exception:
            pass
        try:
            self.storage.close()
        except Exception:
            pass
        if self.private:
            self.destroy()
        return False

    def _clear_on_exit(self):
        options = self.settings.get("clear_on_exit_options") or {}
        if options.get("history"):
            self.storage.clear_history()
        if options.get("downloads"):
            self.storage.clear_downloads()
        if options.get("cookies"):
            self.clear_cookies(quiet=True)
        if options.get("cache"):
            self.clear_cache(quiet=True)

    def _save_session(self):
        try:
            data = [
                {"url": tab.url, "title": tab.title, "pinned": tab.pinned}
                for tab in self.tabs
                if tab.url and not search.is_internal(tab.url)
            ]
            self.storage.save_tabs(data)
            self.storage.meta_set("active_tab", self.notebook.get_current_page())
            self.storage.meta_set("session_time", time.time())
        except Exception:
            pass

    def _restore_startup(self, urls):
        startup = self.settings.get("startup_mode")
        if urls:
            for index, url in enumerate(urls):
                self.create_tab(url, background=index > 0)
            return
        if self.private:
            self.create_tab(self.settings.get("home_page") or "nolags://newtab")
            return
        if startup == "restore" or (self.settings.get("restore_session") and startup != "newtab"):
            saved = self.storage.load_tabs()
            if saved:
                for index, item in enumerate(saved):
                    if item.get("url"):
                        self.create_tab(item["url"], background=index > 0, pinned=bool(item.get("pinned")))
                active = int(self.storage.meta_get("active_tab", 0) or 0)
                self.select_tab_index(active)
                return
        if startup == "home":
            self.create_tab(self.settings.get("home_page") or "nolags://newtab")
            return
        if startup == "urls":
            urls_list = self.settings.get("startup_urls") or []
            if urls_list:
                for index, url in enumerate(urls_list):
                    self.create_tab(url, background=index > 0)
                return
        self.create_tab("nolags://newtab")

    def _on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.find_bar.get_reveal_child():
                self.find_bar.close()
                return True
            if self.fullscreen_active:
                self.set_fullscreen(False)
                return True
        if event.keyval == Gdk.KEY_Escape:
            pass
        return False

    def _on_tab_button_toggled(self, button):
        tab = getattr(button, "tab_ref", None)
        if tab is None:
            return
        if button.get_active():
            self.select_tab(tab)
        elif len(self.tabs) > 1 and tab in self.tabs and self.current_tab is tab:
            button.set_active(True)

    def _on_tab_button_press(self, button, event):
        tab = getattr(button, "tab_ref", None)
        if tab is None:
            return False
        if event.button == 2:
            self.close_tab(tab)
            return True
        if event.button == 3:
            self._tab_context_menu(tab, event)
            return True
        return False

    def _on_strip_press(self, widget, event):
        if event.button == 1:
            alloc = widget.get_allocation()
            if event.x > alloc.width - 4:
                self.create_tab()
        elif event.button == 3:
            menu = Gtk.Menu()
            item = Gtk.MenuItem(label="Новая вкладка")
            item.connect("activate", lambda *_: self.create_tab())
            menu.append(item)
            item = Gtk.MenuItem(label="Список вкладок")
            item.connect("activate", lambda *_: self.tab_search.open())
            menu.append(item)
            menu.show_all()
            menu.popup_at_pointer(event)
        return False

    def _on_notebook_press(self, notebook, event):
        if event.button == 1:
            if self._clicked_empty_tab_area(notebook, event):
                if self.settings.get("tabs_as_list"):
                    self.create_tab()
                return False
        if event.button == 2:
            clicked = self._tab_at_event(notebook, event)
            if clicked is not None:
                self.close_tab(clicked)
                return True
        if event.button == 3:
            clicked = self._tab_at_event(notebook, event)
            if clicked is not None:
                self._tab_context_menu(clicked, event)
                return True
        return False

    def _clicked_empty_tab_area(self, notebook, event):
        try:
            alloc = notebook.get_allocation()
            if event.y > 0 and event.y < 40 and event.x > alloc.width - 60:
                return True
        except Exception:
            pass
        return False

    def _tab_at_event(self, notebook, event):
        for tab in self.tabs:
            label = getattr(tab, "label", None)
            if label is None:
                continue
            try:
                alloc = label.get_allocation()
                origin = label.translate_coordinates(notebook, 0, 0)
                if origin is None:
                    continue
                x, y = origin
                if x <= event.x <= x + alloc.width and y <= event.y <= y + alloc.height:
                    return tab
            except Exception:
                continue
        return None

    def _tab_context_menu(self, tab, event):
        menu = Gtk.Menu()
        items = [
            ("Обновить", lambda: tab.reload()),
            ("Заглушить звук", tab.toggle_mute),
            ("Задублировать вкладку", lambda: self.duplicate_tab(tab)),
            ("Скопировать адрес", lambda: util.copy_text(tab.url)),
            ("Вернуть закрытую вкладку", self.reopen_closed_tab),
            ("Усыпить вкладку", lambda: tab.discard() and self.toast("Вкладка усыплена")),
            ("Закрепить вкладку", lambda: self.toggle_pin(tab)),
            ("Закрыть другие вкладки", lambda: self.close_other_tabs(tab)),
            ("Закрыть вкладку", lambda: self.close_tab(tab)),
        ]
        for label, callback in items:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", lambda _w, cb=callback: cb())
            menu.append(item)
        menu.show_all()
        menu.popup_at_pointer(event)


    @property
    def current_tab(self):
        index = self.notebook.get_current_page()
        if 0 <= index < len(self.tabs):
            return self.tabs[index]
        return None

    def create_tab(self, url=None, background=False, pinned=False, focus=True, load_url=None):
        if self.settings.get("preload_new_tab") and self.tabs:
            pass
        target = url or load_url
        tab = Tab(self, None, pinned=pinned)
        tab.label = widgets.TabLabel(self, tab, show_close=bool(self.settings.get("close_button_on_tabs")))
        tab.button = Gtk.ToggleButton()
        tab.label.set_title(tab.title)
        tab.button.set_relief(Gtk.ReliefStyle.NONE)
        tab.button.get_style_context().add_class("nlb-tab")
        tab.button.add(tab.label)
        tab.button.set_tooltip_text("Новая вкладка")
        tab.button.tab_ref = tab
        tab.button.connect("toggled", self._on_tab_button_toggled)
        tab.button.connect("button-press-event", self._on_tab_button_press)
        self.tab_strip.pack_start(tab.button, False, False, 0)
        page_num = self.notebook.append_page(tab.host, None)
        self.tabs.append(tab)
        if pinned:
            tab.label.set_title("Закреплено")
        if target:
            tab.load(target)
        else:
            tab.load("nolags://newtab")
        if not background or len(self.tabs) == 1:
            self.select_tab(tab)
        self.notebook.show_all()
        if self.settings.get("close_button_on_tabs") is False:
            tab.label.close.hide()
        if focus and not background:
            self.memory_touched()
        self.update_tab_bar_visibility()
        self.refresh_nav_buttons()
        return tab

    def duplicate_tab(self, tab):
        new = self.create_tab(background=True)
        if tab.url:
            new.load(tab.url)

    def close_tab(self, tab, restore=True):
        if tab not in self.tabs:
            return
        if self.settings.get("confirm_close_tabs") and tab.url and not search.is_internal(tab.url):
            pass
        if restore and tab.url and not search.is_internal(tab.url):
            self.closed_tabs.insert(0, {"url": tab.url, "title": tab.title})
            self.closed_tabs = self.closed_tabs[:25]
        index = self.tabs.index(tab)
        self.tabs.remove(tab)
        if getattr(tab, "button", None) is not None:
            self.tab_strip.remove(tab.button)
            tab.button.destroy()
            tab.button = None
        page = self.notebook.page_num(tab.host)
        if page != -1:
            self.notebook.remove_page(page)
        tab.destroy()
        if not self.tabs:
            self.create_tab("nolags://newtab")
        elif index >= len(self.tabs):
            self.select_tab_index(len(self.tabs) - 1)
        self.update_tab_bar_visibility()

    def close_current_tab(self):
        tab = self.current_tab
        if tab:
            self.close_tab(tab)

    def close_other_tabs(self, keep):
        for tab in list(self.tabs):
            if tab is not keep:
                self.close_tab(tab)

    def toggle_pin(self, tab):
        tab.pinned = not tab.pinned
        self.toast("Вкладка закреплена" if tab.pinned else "Вкладка откреплена")

    def select_tab(self, tab):
        if tab not in self.tabs:
            return
        index = self.tabs.index(tab)
        self.notebook.set_current_page(index)
        if self.notebook.get_current_page() != index:
            self._schedule_reselect(tab)
            return
        tab.last_active = time.time()
        for other in [tab] + [item for item in self.tabs if item is not tab]:
            button = getattr(other, "button", None)
            if button is None:
                continue
            want = other is tab
            if button.get_active() == want:
                continue
            try:
                button.handler_block_by_func(self._on_tab_button_toggled)
            except (TypeError, ValueError):
                pass
            button.set_active(want)
            try:
                button.handler_unblock_by_func(self._on_tab_button_toggled)
            except (TypeError, ValueError):
                pass

    def _schedule_reselect(self, tab, attempt=0):
        if attempt >= 8 or tab not in self.tabs:
            return False
        GLib.timeout_add(35, self._reselect, tab, attempt)
        return False

    def _reselect(self, tab, attempt):
        if tab not in self.tabs:
            return False
        index = self.tabs.index(tab)
        if self.notebook.get_current_page() != index:
            self.notebook.set_current_page(index)
        if self.notebook.get_current_page() != index:
            self._schedule_reselect(tab, attempt + 1)
        return False

    def select_tab_index(self, index):
        if 0 <= index < len(self.tabs):
            self.select_tab(self.tabs[index])

    def cycle_tab(self, delta):
        if not self.tabs:
            return
        index = (self.notebook.get_current_page() + delta) % len(self.tabs)
        self.select_tab_index(index)

    def _on_switch_page(self, _notebook, _page, index):
        if not (0 <= index < len(self.tabs)):
            return
        tab = self.tabs[index]
        if tab.view is not None:
            self.mute_button.set_visible(bool(tab.view.get_property("is-playing-audio") or tab.view.get_is_muted()))
        else:
            self.mute_button.set_visible(False)
        if tab.discarded:
            tab.revive()
        tab.last_active = time.time()
        self.address.show_url(tab.url)
        self.address.update_security(tab.url)
        self.address.update_star(tab.url)
        self.refresh_window_title()
        self.refresh_nav_buttons()
        self.status_bar.set_zoom(tab.view.get_zoom_level() if tab.view else 1.0)
        self.update_bookmark_star(tab.url)
        self.mute_button.set_sensitive(tab.view is not None)
        if self.settings.get("new_tab_focus_address") and search.is_internal(tab.url):
            if self.settings.get("ui_theme"):
                pass
        if self.settings.get("show_statusbar"):
            self.update_memory_label()
        self.apply_site_zoom(tab)

    def apply_site_zoom(self, tab):
        if not tab or not tab.view or not tab.url:
            return
        host = search.display_host(tab.url)
        if host and host in self._site_zoom:
            zoom = float(self._site_zoom[host])
            if abs(zoom - tab.view.get_zoom_level()) > 0.001:
                tab.view.set_zoom_level(zoom)

    def _on_pages_changed(self, *_args):
        self.update_tab_bar_visibility()

    def update_tab_bar_visibility(self):
        self.notebook.set_show_tabs(False)
        self.refresh_nav_buttons()

    def reopen_closed_tab(self):
        if not self.closed_tabs:
            self.toast("Закрытых вкладок нет")
            return
        item = self.closed_tabs.pop(0)
        self.create_tab(item.get("url"))

    def refresh_nav_buttons(self):
        tab = self.current_tab
        alive = tab is not None and tab.view is not None
        self.back_button.set_sensitive(bool(alive and tab.view.can_go_back()))
        self.forward_button.set_sensitive(bool(alive and tab.view.can_go_forward()))
        self.reload_button.set_sensitive(alive)
        loading = alive and tab.view.is_loading()
        if loading:
            self.reload_button.set_image(widgets.icon_image("process-stop-symbolic"))
            try:
                self.reload_button.disconnect_by_func(self._on_reload_clicked)
            except Exception:
                pass
            self.reload_button.connect("clicked", self._on_stop_clicked)
        else:
            if self.settings.get("show_paw_loader"):
                pixbuf = widgets.svg_pixbuf(mascot.paw_svg(64, self.settings.get("accent_color") or "#2fb7a4"), 16)
                self.reload_button.set_image(Gtk.Image.new_from_pixbuf(pixbuf) if pixbuf else widgets.icon_image("view-refresh-symbolic"))
            else:
                self.reload_button.set_image(widgets.icon_image("view-refresh-symbolic"))
            try:
                self.reload_button.disconnect_by_func(self._on_stop_clicked)
            except Exception:
                pass
            self.reload_button.connect("clicked", self._on_reload_clicked)

    def _on_reload_clicked(self, *_args):
        if self.current_tab:
            self.current_tab.reload()

    def _on_stop_clicked(self, *_args):
        if self.current_tab:
            self.current_tab.stop()

    def refresh_window_title(self):
        tab = self.current_tab
        if tab and tab.title:
            self.set_title(f"{tab.title} — {APP_NAME}")
        else:
            self.set_title(APP_NAME)

    def update_bookmark_star(self, url):
        if not url:
            return
        starred = self.storage.is_bookmarked(url)
        self.bookmark_button.set_image(widgets.icon_image("starred-symbolic" if starred else "non-starred-symbolic"))
        self.address.update_star(url)

    def toggle_bookmark_current(self):
        tab = self.current_tab
        if tab and tab.url:
            self.toggle_bookmark(tab.url, tab.title)

    def toggle_bookmark(self, url, title):
        if not url:
            return
        if self.storage.is_bookmarked(url):
            self.storage.remove_bookmark(url)
            self.toast("Удалено из закладок")
        else:
            self.storage.add_bookmark(url, title or url)
            self.toast("Добавлено в закладки")
        self.update_bookmark_star(url)
        self.rebuild_bookmarks_bar()

    def bookmark_all_tabs(self):
        count = 0
        for tab in self.tabs:
            if tab.url and not search.is_internal(tab.url):
                self.storage.add_bookmark(tab.url, tab.title, "Сеанс")
                count += 1
        self.toast(f"Добавлено закладок: {count}")
        self.rebuild_bookmarks_bar()

    def rebuild_bookmarks_bar(self):
        for child in self.bookmarks_items.get_children():
            self.bookmarks_items.remove(child)
        rows = self.storage.bookmarks()[:40]
        visible = bool(rows) and bool(self.settings.get("show_bookmarks_bar"))
        for row in rows:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            icon = widgets.icon_image("emblem-favorite-symbolic")
            icon.set_pixel_size(13)
            box.pack_start(icon, False, False, 0)
            label = Gtk.Label(label=util.truncate(row.get("title") or row["url"], 26))
            box.pack_start(label, False, False, 0)
            button.add(box)
            button.set_tooltip_text(row["url"])
            button.connect("clicked", lambda _w, url=row["url"]: self.open_url(url))
            button.connect("button-press-event", lambda _w, event, url=row["url"]: self._bookmark_bar_middle(event, url))
            self.bookmarks_items.pack_start(button, False, False, 0)
        self.bookmarks_items.show_all()
        self.bookmarks_all_button.set_visible(bool(rows))
        self.bookmarks_revealer.set_reveal_child(visible)

    def _bookmark_bar_middle(self, event, url):
        if event.button == 2:
            self.create_tab(url, background=True)
            return True
        return False

    def toggle_bookmarks_bar(self):
        enabled = self.settings.toggle("show_bookmarks_bar")
        self.bookmarks_revealer.set_reveal_child(bool(enabled))
        self.toast("Панель закладок включена" if enabled else "Панель закладок скрыта")

    def set_statusbar(self, state):
        self.settings.set("show_statusbar", bool(state))
        self.update_memory_label()
        if not state:
            self.show_status(False)

    def show_status(self, state):
        self.status_bar.set_reveal_child(bool(state))

    def go_home(self):
        page = self.settings.get("home_page") or "nolags://newtab"
        if self.current_tab:
            self.current_tab.load(page)

    def open_url(self, url, background=False):
        tab = self.current_tab
        if tab is None or (search.is_internal(tab.url) and url.startswith("nolags://")):
            if tab is None:
                self.create_tab(url)
            elif url.startswith("nolags://"):
                tab.load(url)
            else:
                self.create_tab(url, background=background)
            return
        if background:
            self.create_tab(url, background=True)
            return
        tab.load(url)

    def open_page(self, url):
        tab = self.current_tab
        if tab is not None and search.is_internal(tab.url):
            tab.load(url)
            return
        self.create_tab(url)

    def display_url(self, url):
        if not url:
            return ""
        if self.settings.get("show_full_url"):
            return url
        if search.is_internal(url):
            return "NoLags"
        return search.pretty_url(url, bool(self.settings.get("trim_trailing_slash")))

    def set_address_focus(self, focused):
        if focused:
            self.show_status(False)

    def letter_icon(self, url):
        host = search.display_host(url) or "?"
        surface = None
        try:
            from gi.repository import cairo

            size = 16
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            ctx = cairo.Context(surface)
            color = util.color_for(host)
            ctx.set_source_rgb(
                int(color[1:3], 16) / 255.0,
                int(color[3:5], 16) / 255.0,
                int(color[5:7], 16) / 255.0,
            )
            ctx.paint()
            return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)
        except Exception:
            return None


    def build_suggestions(self, text):
        rows = []
        stripped = text.strip()
        engine = search.engine_name(self.settings)
        normalized = search.normalize_input(stripped, self.settings)
        if normalized and normalized != stripped:
            rows.append((normalized, stripped, "Открыть адрес", "applications-internet", "url"))
        else:
            rows.append((("search", search.search_url(self.settings, stripped)), f"Искать «{stripped}»", engine, "system-search-symbolic", "search"))
        if self.settings.get("suggestions_enabled"):
            limit = int(self.settings.get("suggestions_limit") or 8)
            if self.settings.get("bookmark_suggestions"):
                for item in self.storage.search_bookmarks(stripped, 3):
                    rows.append((item["url"], item.get("title") or item["url"], search.pretty_url(item["url"]), "user-bookmarks-symbolic", "bookmark"))
            if self.settings.get("history_suggestions"):
                for item in self.storage.history_host_suggestions(stripped, 4):
                    if any(row[0] == item["url"] for row in rows):
                        continue
                    rows.append((item["url"], item.get("title") or item["host"], item["host"], "document-open-recent-symbolic", "history"))
            for page_url, label, subtitle in (
                ("nolags://history", "История", "Страница NoLags"),
                ("nolags://bookmarks", "Закладки", "Страница NoLags"),
                ("nolags://settings", "Настройки", "Страница NoLags"),
            ):
                if stripped.lower() in label.lower():
                    rows.append((page_url, label, subtitle, "applications-internet", "url"))
            rows = rows[:limit]
        return rows


    def page_data(self):
        return {
            "top_sites": self.storage.top_sites(10),
            "recently_closed": self.closed_tabs[:6],
            "bookmarks": self.storage.bookmarks()[:6],
            "chips": [{"label": label, "url": url} for label, url in CHIPS],
        }

    def internal_html(self, uri):
        parsed = urlparse(uri)
        name = (parsed.netloc or parsed.path or "newtab").strip("/") or "newtab"
        query = ""
        if "?" in uri:
            query = unquote(uri.split("?", 1)[1])
        data = self.page_data()
        if name == "newtab":
            return pages.page_newtab(self.settings, data)
        if name == "history":
            groups = self.storage.history_by_day(30)
            return pages.page_history(self.settings, {"history": groups}, query)
        if name == "bookmarks":
            rows = self.storage.bookmarks()
            folders = {}
            for row in rows:
                folders.setdefault(row.get("folder") or "", []).append(row)
            return pages.page_bookmarks(self.settings, {"folders": folders})
        if name == "downloads":
            return pages.page_downloads(self.settings, {"downloads": self.storage.downloads()})
        if name == "notes":
            return pages.page_notes(self.settings, {"notes": self.storage.notes()})
        if name == "about":
            try:
                webkit_version = f"{WebKit2.get_major_version()}.{WebKit2.get_minor_version()}.{WebKit2.get_micro_version()}"
            except Exception:
                webkit_version = ""
            return pages.page_about(
                self.settings,
                {
                    "stats": self.storage.stats(),
                    "blocker": {"count": self.blocker.count()},
                    "webkit": webkit_version,
                },
            )
        if name == "shortcuts":
            return pages.page_shortcuts(self.settings, data)
        if name == "error":
            return pages.page_error(self.settings, {"message": query or "Страница недоступна", "url": ""})
        if name == "settings":
            GLib.idle_add(lambda: (self.open_settings(), False)[1])
            return pages.page_newtab(self.settings, data)
        return pages.page_newtab(self.settings, data)

    def _scheme_callback(self, request):
        uri = request.get_uri()
        if uri.startswith("nolags://error"):
            message = ""
            target = ""
            if "?" in uri:
                params = {}
                for pair in uri.split("?", 1)[1].split("&"):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key] = unquote(value)
                message = params.get("message", "")
                target = params.get("url", "")
            html = pages.page_error(self.settings, {"message": message, "url": target})
        else:
            html = self.internal_html(uri)
        payload = html.encode("utf-8")
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(payload))
        try:
            request.finish(stream, len(payload), "text/html")
        except Exception:
            try:
                request.finish_error(GLib.Error.new_literal(Gio.io_error_quark(), 0, "fail"))
            except Exception:
                pass

    def _register_schemes(self):
        contexts = [WebKit2.WebContext.get_default()]
        if self.private_context is not None:
            contexts.append(self.private_context)
        for context in contexts:
            if not _register_context_scheme(context, self._scheme_callback):
                continue

    def register_scheme(self, context):
        try:
            context.register_uri_scheme("nolags", self._scheme_callback)
        except Exception:
            pass

    def show_error_page(self, tab, uri, message):
        target = f"nolags://error?message={util.escape_html(message)}&url={util.escape_html(uri)}"
        try:
            tab.view.stop_loading()
        except Exception:
            pass
        tab.view.load_uri(target)

    def handle_page_message(self, tab, data):
        action = data.get("action")
        if action == "navigate":
            target = data.get("url") or data.get("text") or ""
            if target:
                self.open_from_page(tab, target)
        elif action == "navigate_raw":
            text = data.get("raw") or data.get("text") or ""
            if text:
                self.open_from_page(tab, text)
        elif action == "search":
            text = data.get("text") or data.get("query") or ""
            if text:
                self.open_from_page(tab, text, force_search=True)
        elif action == "open":
            url = data.get("url") or ""
            if url:
                tab.load(url)
        elif action == "settings":
            self.open_settings()
        elif action == "shortcuts":
            tab.load("nolags://shortcuts")
        elif action == "clear_cache":
            self.clear_cache()
        elif action == "trim_memory":
            self.trim_memory()
        elif action == "task_manager":
            self.show_task_manager()
        elif action == "mem_stats":
            self.send_memory_stats(tab)
        elif action == "blocklist_hosts":
            self.open_hosts_file(tab)
        elif action == "blocklist_update":
            self.update_blocklist()
        elif action == "history_search":
            self.search_history(data.get("query") or "")
        elif action == "history_delete":
            self.storage.remove_history(data.get("url") or "")
            tab.reload()
        elif action == "history_clear":
            self.storage.clear_history()
            tab.reload()
            self.toast("История очищена")
        elif action == "history_export":
            self.export_history()
        elif action == "bookmark_delete":
            self.storage.remove_bookmark(data.get("url") or "")
            tab.reload()
            self.rebuild_bookmarks_bar()
            self.update_bookmark_star(self.current_tab.url if self.current_tab else "")
        elif action == "bookmark_current":
            if self.current_tab and self.current_tab.url:
                self.storage.add_bookmark(self.current_tab.url, self.current_tab.title)
                self.toast("Добавлено в закладки")
                tab.reload()
                self.rebuild_bookmarks_bar()
        elif action == "bookmarks_import":
            self.import_bookmarks()
            tab.reload()
        elif action == "bookmarks_export":
            self.export_bookmarks_html()
        elif action == "bookmarks_export_json":
            self.export_bookmarks_json()
        elif action == "note_add":
            body = (data.get("body") or "").strip()
            if body:
                title = self.current_tab.title if self.current_tab else ""
                self.storage.add_note(self.current_tab.url if self.current_tab else "", title, body)
                self.toast("Заметка сохранена")
                tab.reload()
        elif action == "note_delete":
            self.storage.delete_note(data.get("id"))
            tab.reload()
        elif action == "note_from_page":
            text = ""
            title = ""
            if self.current_tab and self.current_tab.view:
                try:
                    result = self.current_tab.view.run_javascript(
                        "document.body ? document.body.innerText.slice(0, 4000) : ''", None, None
                    )
                    text = result.get_js_value().to_string() or ""
                    title = self.current_tab.title
                except Exception:
                    text = ""
            tab.view.run_javascript(
                f"window.nlNoteFromPage({json.dumps(title)}, {json.dumps(text)})", None, None
            )
        elif action == "download_open":
            util.xdg_open(data.get("path") or "")
        elif action == "download_folder":
            util.open_folder(data.get("path") or "")
        elif action == "downloads_folder":
            util.open_folder(self.download_dir())
        elif action == "downloads_clear":
            self.storage.clear_downloads()
            tab.reload()
        elif action == "restore_tab":
            url = data.get("url") or ""
            if url:
                self.create_tab(url)
        elif action == "retry":
            if self.current_tab:
                back = self.current_tab.url
                self.current_tab.navigate(self.settings.get("home_page") or "nolags://newtab")
                if back and not search.is_internal(back):
                    self.current_tab.load(back)
        elif action == "offline_check":
            online = check_internet()
            self.toast("Соединение есть" if online else "Интернета нет")
        elif action == "save_site_style":
            style = data.get("style") or "none"
            self.set_site_style(style)

    def open_from_page(self, tab, text, force_search=False):
        target = (text or "").strip()
        if not target:
            return
        if target.startswith(("nolags://", "about:", "view-source:", "file:")):
            tab.load(target)
            return
        if force_search:
            tab.load(search.search_url(self.settings, target))
            return
        if search.is_internal(tab.url):
            tab.navigate(target)
        else:
            self.create_tab(search.normalize_input(target, self.settings))

    def send_memory_stats(self, tab):
        if tab is None or tab.view is None:
            return
        total = util.webkit_memory_mb()
        own = util.self_memory_mb()
        payload = {
            "total": total,
            "own": own,
            "web": max(0.0, total - own),
            "tabs": len(self.tabs),
            "limit": 3800,
        }
        try:
            tab.view.run_javascript(f"window.nlSetMem && window.nlSetMem({json.dumps(payload)})", None, None)
        except Exception:
            pass

    def search_history(self, query):
        tab = self.current_tab
        if not tab:
            return
        if query:
            groups = {}
            for item in self.storage.history(query, 500):
                key = time.strftime("%Y-%m-%d", time.localtime(item["last_visit"]))
                groups.setdefault(key, []).append(item)
            html = pages.page_history(self.settings, {"history": groups}, query)
            payload = html.encode("utf-8")
            stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(payload))
            try:
                tab.view.load_bytes(GLib.Bytes.new(payload), "text/html", "UTF-8", "nolags://history")
            except Exception:
                tab.load("nolags://history")
        else:
            tab.load("nolags://history")


    def open_settings(self):
        if getattr(self, "_settings_window", None) is not None:
            self._settings_window.present()
            return
        self._settings_window = SettingsWindow(self, self.settings, self.on_setting_changed)
        self._settings_window.connect("destroy", lambda *_: setattr(self, "_settings_window", None))
        self._settings_window.show_all()

    def on_setting_changed(self, key, value):
        if key in (
            "restore_session", "auto_discard", "low_memory_mode", "tab_discard_delay",
            "enable_javascript", "load_images", "enable_webgl", "smooth_scrolling",
            "accelerated_compositing", "autoplay", "user_agent_mode", "custom_user_agent",
            "memory_trim_interval", "site_style", "custom_css",
        ):
            for tab in self.tabs:
                if tab.view is not None:
                    tab.apply_settings()
            if key == "memory_trim_interval":
                self._restart_trim_timer(int(value or 0))
        if key == "show_bookmarks_bar":
            self.bookmarks_revealer.set_reveal_child(bool(value))
        if key == "show_statusbar":
            self.update_memory_label()
            self.show_status(True)
        if key == "compact_mode":
            self.apply_ui_settings()

    def apply_ui_settings(self):
        compact = bool(self.settings.get("compact_mode"))
        spacing = 0 if compact else 2
        self.toolbar.set_spacing(spacing)
        has_bookmarks = bool(self.storage.bookmarks())
        self.bookmarks_revealer.set_reveal_child(bool(self.settings.get("show_bookmarks_bar")) and has_bookmarks)
        self.status_bar.set_reveal_child(bool(self.settings.get("show_statusbar")))
        self.update_memory_label()
        theme = str(self.settings.get("ui_theme") or "system")
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None and theme in ("light", "dark"):
            gtk_settings.set_property("gtk-application-prefer-dark-theme", theme == "dark")
        self.apply_tab_position(str(self.settings.get("tab_position") or "top"))

    def apply_tab_position(self, position):
        mapping = {
            "top": Gtk.PositionType.TOP,
            "bottom": Gtk.PositionType.BOTTOM,
            "left": Gtk.PositionType.LEFT,
            "right": Gtk.PositionType.RIGHT,
        }
        parent = self.tab_strip_scroller.get_parent()
        if parent is not None and parent is not self.header:
            parent.remove(self.tab_strip_scroller)
        if position in ("left", "right"):
            self.header.set_custom_title(None)
            self.tab_strip.set_orientation(Gtk.Orientation.VERTICAL)
            self.tab_strip_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
            self.tab_strip_scroller.set_size_request(200, -1)
            if self.tab_strip_scroller.get_parent() is not None:
                self.tab_strip_scroller.get_parent().remove(self.tab_strip_scroller)
            self.sidebar_box.pack_start(self.tab_strip_scroller, True, True, 0)
            self.sidebar_revealer.set_reveal_child(True)
            self.sidebar_revealer.set_transition_type(
                Gtk.RevealerTransitionType.SLIDE_RIGHT if position == "left" else Gtk.RevealerTransitionType.SLIDE_LEFT
            )
        else:
            if self.tab_strip_scroller.get_parent() is not None:
                self.tab_strip_scroller.get_parent().remove(self.tab_strip_scroller)
            self.sidebar_revealer.set_reveal_child(False)
            self.tab_strip.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.tab_strip_scroller.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
            self.tab_strip_scroller.set_size_request(240, -1)
            self.header.set_custom_title(self.tab_strip_scroller)
        self.tab_strip_scroller.show_all()

    def clear_cache(self, quiet=False):
        try:
            context = self.private_context if self.private_context is not None else WebKit2.WebContext.get_default()
            context.clear_cache()
        except Exception:
            pass
        for attr in ("cache", "web-cache", "code-cache"):
            path = Path(util.__file__).resolve().parent.parent
            break
        try:
            cache_dir = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "nolagsbrowser"
            for item in cache_dir.glob("**/*"):
                if item.is_file():
                    try:
                        item.unlink()
                    except OSError:
                        pass
        except OSError:
            pass
        self.toast("Кэш очищен")

    def clear_cookies(self, quiet=False):
        try:
            context = self.private_context if self.private_context is not None else WebKit2.WebContext.get_default()
            manager = context.get_cookie_manager()
            manager.delete_all_cookies()
        except Exception:
            pass
        if not quiet:
            self.toast("Cookie удалены")

    def trim_memory(self):
        util.malloc_trim()
        try:
            context = WebKit2.WebContext.get_default()
            context.clear_cache()
        except Exception:
            pass
        self.update_memory_label()
        tab = self.current_tab
        if tab:
            self.send_memory_stats(tab)
        self.toast("Память освобождена")

    def discard_background_tabs(self):
        count = 0
        for tab in self.tabs:
            if tab is not self.current_tab and tab.discard():
                count += 1
        self.toast(f"Усыплено вкладок: {count}")

    def set_low_memory(self, state):
        self.settings.set("low_memory_mode", bool(state))
        for tab in self.tabs:
            if tab.view is not None:
                tab.apply_settings()
        self.toast("Режим низкого потребления включён" if state else "Режим низкого потребления выключен")

    def set_site_style(self, style):
        self.settings.set("site_style", style)
        for tab in self.tabs:
            if tab.view is not None:
                tab.apply_user_style()
        self.toast("Оформление страниц обновлено")

    def toggle_mobile_ua(self):
        current = self.settings.get("user_agent_mode")
        new = "auto" if current == "custom" else "custom"
        if new == "custom":
            self.settings.set("custom_user_agent", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
        self.settings.set("user_agent_mode", new)
        for tab in self.tabs:
            if tab.view is not None:
                tab.apply_settings()
                tab.reload()
        self.toast("Мобильный User-Agent включён" if new == "custom" else "Обычный User-Agent")

    def print_page(self):
        tab = self.current_tab
        if not tab or tab.view is None:
            return
        try:
            operation = WebKit2.PrintOperation.new(tab.view)
            result = operation.run_dialog(self)
            if result == Gtk.PrintOperationResult.APPLY:
                pass
        except Exception:
            self.toast("Печать недоступна в этой системе")

    def save_page(self):
        tab = self.current_tab
        if not tab or not tab.url or tab.view is None:
            self.toast("Нечего сохранять")
            return
        dialog = Gtk.FileChooserDialog(
            title="Сохранить страницу",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_folder(str(self.download_dir()))
        name = re.sub(r"[^\w\- .]", "_", tab.title or "page")[:70].strip() or "page"
        dialog.set_current_name(f"{name}.mhtml")
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Веб-архив (MHTML)")
        file_filter.add_pattern("*.mhtml")
        dialog.add_filter(file_filter)
        if dialog.run() != Gtk.ResponseType.ACCEPT:
            dialog.destroy()
            return
        path = dialog.get_filename()
        dialog.destroy()
        if not path.endswith(".mhtml"):
            path += ".mhtml"
        target = Path(path)
        try:
            gfile = Gio.File.new_for_path(str(target))

            def on_saved(view, result, _data):
                try:
                    ok = view.save_to_file_finish(result)
                except Exception:
                    ok = False
                self.toast("Страница сохранена" if ok else "Не удалось сохранить страницу")

            tab.view.save_to_file(gfile, WebKit2.SaveMode.MHTML, None, on_saved, None)
        except Exception:
            self.toast("Не удалось сохранить страницу")

    def screenshot(self):
        tab = self.current_tab
        if not tab or tab.view is None:
            return
        dialog = Gtk.FileChooserDialog(
            title="Скриншот страницы",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_folder(str(self.download_dir()))
        dialog.set_current_name(f"screenshot-{time.strftime('%Y%m%d-%H%M%S')}.png")
        if dialog.run() != Gtk.ResponseType.ACCEPT:
            dialog.destroy()
            return
        path = dialog.get_filename()
        dialog.destroy()

        def on_snapshot(view, result, _data):
            try:
                surface = view.get_snapshot_finish(result)
            except Exception:
                self.toast("Не удалось сделать скриншот")
                return
            try:
                pixbuf = Gdk.pixbuf_get_from_surface(
                    surface, 0, 0, surface.get_width(), surface.get_height()
                )
                pixbuf.savev(str(path), "png", [], [])
                self.toast("Скриншот сохранён")
            except Exception:
                self.toast("Не удалось сохранить скриншот")

        tab.view.get_snapshot(WebKit2.SnapshotRegion.FULL_DOCUMENT, WebKit2.SnapshotOptions.NONE, None, on_snapshot, None)

    def view_source(self):
        tab = self.current_tab
        if tab and tab.url and not search.is_internal(tab.url):
            self.create_tab(f"view-source:{tab.url}")

    def devtools(self):
        tab = self.current_tab
        if not tab or tab.view is None:
            return
        try:
            inspector = tab.view.get_inspector()
            inspector.show()
        except Exception:
            self.toast("Инструменты разработчика недоступны")

    def zoom_in(self):
        tab = self.current_tab
        if tab:
            tab.set_zoom(tab.view.get_zoom_level() + 0.1)

    def zoom_out(self):
        tab = self.current_tab
        if tab:
            tab.set_zoom(tab.view.get_zoom_level() - 0.1)

    def zoom_reset(self):
        tab = self.current_tab
        if tab:
            tab.set_zoom(float(self.settings.get("default_zoom") or 1.0))

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.fullscreen_active)

    @property
    def fullscreen_active(self):
        return bool(getattr(self, "_fullscreen", False))

    def set_fullscreen(self, state):
        self._fullscreen = bool(state)
        if state:
            self.fullscreen()
            self.toolbar_revealer.set_reveal_child(False)
            self.bookmarks_revealer.set_reveal_child(False)
        else:
            self.unfullscreen()
            self.toolbar_revealer.set_reveal_child(True)
            self.bookmarks_revealer.set_reveal_child(bool(self.settings.get("show_bookmarks_bar")))

    def open_hosts_file(self, tab=None):
        path = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "nolagsbrowser" / "hosts.blocklist"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = ["127.0.0.1 localhost", ""]
            for domain in sorted(self.blocker.hosts):
                if "/" in domain or "." not in domain:
                    continue
                lines.append(f"0.0.0.0 {domain}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            self.toast("Не удалось записать файл")
            return
        target = tab or self.current_tab
        if target:
            target.load(path.as_uri())
        self.toast("Hosts-файл открыт в вкладке")

    def save_hosts_file(self):
        dialog = Gtk.FileChooserDialog(
            title="Сохранить hosts-файл",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_folder(str(self.download_dir()))
        dialog.set_current_name("nolags-hosts.txt")
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            dialog.destroy()
            lines = ["127.0.0.1 localhost", ""]
            lines += [f"0.0.0.0 {domain}" for domain in sorted(self.blocker.hosts) if "." in domain]
            try:
                Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
                self.toast("Файл сохранён")
            except OSError:
                self.toast("Не удалось сохранить файл")
        else:
            dialog.destroy()

    def update_blocklist(self):
        self.toast("Обновляю список блокировки…")

        def worker():
            ok, message = self.blocker.update_from_url(
                "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
            )
            GLib.idle_add(lambda: self.toast(f"Список обновлён: {message}" if ok else f"Не удалось: {message}"))
            return False

        import threading

        threading.Thread(target=worker, daemon=True).start()

    def export_history(self):
        dialog = Gtk.FileChooserDialog(title="Экспорт истории", transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_name("nolags-history.json")
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            dialog.destroy()
            count = self.storage.export_history(path)
            self.toast(f"Экспортировано записей: {count}")
        else:
            dialog.destroy()

    def export_bookmarks_html(self):
        dialog = Gtk.FileChooserDialog(title="Экспорт закладок", transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_name("nolags-bookmarks.html")
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            dialog.destroy()
            count = self.storage.export_bookmarks_html(path)
            self.toast(f"Экспортировано закладок: {count}")
        else:
            dialog.destroy()

    def export_bookmarks_json(self):
        dialog = Gtk.FileChooserDialog(title="Экспорт закладок JSON", transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_name("nolags-bookmarks.json")
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            dialog.destroy()
            count = self.storage.export_bookmarks_json(path)
            self.toast(f"Экспортировано закладок: {count}")
        else:
            dialog.destroy()

    def import_bookmarks(self):
        dialog = Gtk.FileChooserDialog(title="Импорт закладок", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Импортировать", Gtk.ResponseType.ACCEPT)
        filter_html = Gtk.FileFilter()
        filter_html.set_name("HTML-файлы закладок")
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")
        dialog.add_filter(filter_html)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            dialog.destroy()
            count = self.storage.import_bookmarks_html(path)
            self.toast(f"Импортировано закладок: {count}")
            self.rebuild_bookmarks_bar()
        else:
            dialog.destroy()

    def clear_data_dialog(self):
        dialog = dialogs.ClearDataDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            options = dialog.options()
            if options.get("history"):
                self.storage.clear_history()
            if options.get("downloads"):
                self.storage.clear_downloads()
            if options.get("cookies"):
                self.clear_cookies(quiet=True)
            if options.get("cache"):
                self.clear_cache(quiet=True)
            if options.get("notes"):
                self.storage.wipe(["notes"])
            self.toast("Данные очищены")
            tab = self.current_tab
            if tab and search.is_internal(tab.url):
                tab.reload()
        dialog.destroy()

    def show_task_manager(self):
        dialog = dialogs.TaskManagerDialog(self)
        dialog.show_all()

    def show_command_palette(self):
        dialog = dialogs.CommandPalette(self)
        dialog.show_all()

    def show_shortcuts_page(self):
        self.open_page("nolags://shortcuts")

    def show_connection_info(self):
        tab = self.current_tab
        if not tab:
            return
        url = tab.url or ""
        secure = url.startswith("https://")
        message = "Соединение защищено (HTTPS)" if secure else "Соединение без шифрования (HTTP)"
        if search.is_internal(url):
            message = "Внутренняя страница NoLags"
        self.toast(message)

    def add_note_from_page(self):
        tab = self.current_tab
        text = ""
        title = ""
        if tab and tab.view:
            try:
                result = tab.view.run_javascript("document.body ? document.body.innerText.slice(0, 4000) : ''", None, None)
                text = result.get_js_value().to_string() or ""
                title = tab.title
            except Exception:
                text = ""
        if not text:
            self.toast("Нечего сохранять")
            return
        self.storage.add_note(tab.url if tab else "", title, f"{title}\n\n{text[:2000]}")
        self.toast("Заметка сохранена")

    def get_selected_text(self):
        tab = self.current_tab
        if tab:
            return tab.selected_text()
        return ""

    def download_dir(self):
        configured = self.settings.get("download_dir")
        if configured:
            return Path(configured).expanduser()
        return paths_downloads()

    def create_popup_view(self, navigation_action):
        try:
            related = navigation_action.get_web_view() if hasattr(navigation_action, "get_web_view") else None
        except Exception:
            related = None
        if related is None:
            related = self.current_tab.view if self.current_tab else None
        if related is None:
            return None
        view = WebKit2.WebView.new_with_related_view(related)
        window = Gtk.Window(title="NoLags Browser")
        window.set_transient_for(self)
        window.set_default_size(900, 620)
        window.set_icon_name("nolagsbrowser")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "Окно сайта"
        window.set_titlebar(header)
        box.pack_start(view, True, True, 0)
        window.add(box)
        window.show_all()
        window.connect("destroy", lambda *_: self.popups.remove(window) if window in self.popups else None)
        self.popups.append(window)
        try:
            view.connect("close", lambda *_: (window.close(), True)[1])
            ucm = view.get_user_content_manager()
            ucm.connect("script-message-received::nl", lambda *_: None)
            view.connect("create", lambda v, action: self.create_popup_view(action))
        except Exception:
            pass
        return view

    def apply_context_extras(self, menu, hit):
        try:
            items = menu.get_items()
        except Exception:
            return
        actions = []
        for item in items:
            label = item.get_label() or ""
            text = label.lower()
            if "open link" in text or "открыть ссылку" in text:
                actions.append((item, "new_tab"))
            elif "copy link" in text or "копировать ссылку" in text:
                actions.append((item, "copy_link"))
            elif "open image" in text or "открыть изображение" in text:
                actions.append((item, "new_tab"))
        link = hit.get_link_uri() if hit else None
        image = hit.get_image_uri() if hit else None
        for item, kind in actions:
            if kind in ("new_tab",) and link:
                extra = Gtk.MenuItem(label="Открыть ссылку в новой вкладке")
                extra.connect("activate", lambda *_: self.create_tab(link, background=True))
                menu.insert(extra, 1)
            elif kind == "copy_link" and link:
                extra = Gtk.MenuItem(label="Копировать адрес ссылки")
                extra.connect("activate", lambda *_: util.copy_text(link))
                menu.insert(extra, 2)
        if image:
            extra = Gtk.MenuItem(label="Открыть изображение в новой вкладке")
            extra.connect("activate", lambda *_: self.create_tab(image, background=True))
            menu.append(extra)
        if link:
            extra = Gtk.MenuItem(label="Загрузить по ссылке")
            extra.connect("activate", lambda *_: self.download_link(link))
            menu.append(extra)
        menu.show_all()

    def download_link(self, url):
        try:
            context = WebKit2.WebContext.get_default()
            download = context.download_uri(url)
            if download is None:
                self.toast("Загрузка не началась")
                return
            destination = util.unique_path(self.download_dir(), unquote(Path(urlparse(url).path).name) or "download")
            download.set_destination(destination.as_uri())
            self.toast("Загрузка началась")
        except Exception:
            self.toast("Не удалось скачать файл")

    def gesture_start(self, x_root):
        if self.settings.get("mouse_gestures"):
            self._gesture_x = x_root

    def gesture_end(self, x_root):
        if not self.settings.get("mouse_gestures") or self._gesture_x is None:
            return
        delta = x_root - self._gesture_x
        self._gesture_x = None
        if abs(delta) < 60:
            return
        if delta < 0 and self.current_tab:
            self.current_tab.go_back()
        elif delta > 0 and self.current_tab:
            self.current_tab.go_forward()

    def _on_download_started(self, _context, download):
        destination = None
        try:
            response = download.get_response()
            name = None
            if response is not None:
                disposition = response.get_suggested_filename()
                name = disposition
            if not name:
                name = unquote(Path(urlparse(download.get_uri() or "").path).name) or "download"
            target_dir = self.download_dir()
            if self.settings.get("ask_download_dir"):
                target = self._ask_download_path(name)
                if not target:
                    download.cancel()
                    return
                destination = target
            else:
                destination = util.unique_path(target_dir, name)
        except Exception:
            destination = util.unique_path(self.download_dir(), "download")
        try:
            download.set_allow_overwrite(False)
            if destination is not None:
                download.set_destination(destination.as_uri())
        except Exception:
            pass
        path = str(destination) if destination else ""
        row_id = self.storage.add_download(download.get_uri() or "", Path(path).name if path else "", path, 0, "started")
        self._update_download_badge()
        self.toast(f"Загрузка: {Path(path).name if path else 'файл'}")

        def on_finished(dl):
            size = 0
            try:
                size = dl.get_received_data_length()
            except Exception:
                pass
            self.storage.update_download(row_id, "done", int(size))
            GLib.idle_add(self._update_download_badge)
            if self.settings.get("auto_open_downloads") and path:
                util.xdg_open(path)
            return False

        def on_failed(dl, error):
            self.storage.update_download(row_id, "failed")
            GLib.idle_add(self._update_download_badge)
            GLib.idle_add(lambda: self.toast("Загрузка не удалась"))
            return False

        try:
            download.connect("finished", on_finished)
            download.connect("failed", on_failed)
        except Exception:
            pass

    def _update_download_badge(self):
        rows = self.storage.downloads(50)
        active = [row for row in rows if row.get("state") == "started"]
        self.download_badge.set_text(str(len(active)) if active else "")
        return False

    def _ask_download_path(self, filename):
        dialog = Gtk.FileChooserDialog(
            title="Сохранить файл",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Сохранить", Gtk.ResponseType.ACCEPT)
        dialog.set_current_folder(str(self.download_dir()))
        dialog.set_current_name(filename)
        dialog.set_do_overwrite_confirmation(True)
        response = dialog.run()
        path = dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        dialog.destroy()
        if path:
            return Path(path)
        return None

    def toast(self, message, timeout=2.6):
        self.toast_label.set_text(message or "")
        self.toast_revealer.set_reveal_child(bool(message))
        if self._toast_timer:
            GLib.source_remove(self._toast_timer)
            self._toast_timer = None
        if message:
            self._toast_timer = GLib.timeout_add(int(timeout * 1000), self._hide_toast)
        return False

    def _hide_toast(self):
        self._toast_timer = None
        self.toast_revealer.set_reveal_child(False)
        return False

    def new_window(self):
        app = self.get_application()
        window = MainWindow(app, self.settings)
        window.present()
        return window

    def new_private_window(self):
        app = self.get_application()
        window = MainWindow(app, self.settings, private=True)
        window.present()
        return window

    def _open_menu(self, *_args):
        if not hasattr(self, "menu_pages_ready"):
            self._build_menu_pages()
            self.menu_pages_ready = True
        self.menu.set_relative_to(self.menu_button)
        if hasattr(self.menu, "page"):
            pass
        self.menu.show_all()
        self.menu.popup()

    def _quit(self):
        windows = self.get_application().get_windows()
        for window in windows:
            if window is self:
                window.close()
        self.get_application().quit()

    def on_tab_loaded(self, tab):
        if tab is self.current_tab:
            self.refresh_window_title()


def paths_downloads():
    from .paths import downloads_dir

    return downloads_dir()
