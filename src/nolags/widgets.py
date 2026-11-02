import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango, WebKit2

from . import mascot, search, util

ACCENT = "#2fb7a4"

FALLBACKS = {
    "view-reader-symbolic": ["x-office-document-symbolic", "text-editor-symbolic"],
    "emblem-downloads-symbolic": ["folder-download-symbolic", "document-save-symbolic"],
    "view-private-symbolic": ["dialog-password-symbolic", "security-high-symbolic"],
    "utilities-system-monitor-symbolic": ["applications-system-symbolic", "applications-utilities-symbolic"],
    "speedometer-symbolic": ["applications-system-symbolic", "media-record-symbolic"],
    "applications-internet": ["web-browser-symbolic", "network-server-symbolic"],
    "emblem-favorite-symbolic": ["starred-symbolic", "non-starred-symbolic"],
    "phone-symbolic": ["multimedia-player-symbolic", "input-keyboard-symbolic"],
    "weather-clear-night-symbolic": ["night-light-symbolic", "alarm-symbolic"],
    "applications-engineering-symbolic": ["applications-system-symbolic", "system-run-symbolic"],
    "camera-photo-symbolic": ["multimedia-player-symbolic", "media-record-symbolic"],
    "document-print-symbolic": ["printer-symbolic", "document-save-symbolic"],
    "utilities-terminal-symbolic": ["system-run-symbolic", "applications-system-symbolic"],
    "accessories-text-editor-symbolic": ["text-editor-symbolic", "document-edit-symbolic"],
    "applications-graphics-symbolic": ["applications-multimedia-symbolic", "preferences-other-symbolic"],
    "preferences-desktop-keyboard-symbolic": ["input-keyboard-symbolic", "preferences-other-symbolic"],
    "view-fullscreen-symbolic": ["window-restore-symbolic", "view-dual-symbolic"],
    "drive-harddisk-symbolic": ["drive-harddisk-symbolic", "computer-symbolic"],
    "audio-volume-medium-symbolic": ["audio-volume-high-symbolic", "audio-card-symbolic", "audio-volume-low-symbolic"],
    "audio-volume-muted-symbolic": ["audio-volume-low-symbolic", "audio-card-symbolic"],
    "phone-symbolic": ["phone", "smartphone", "preferences-devices-symbolic"],
    "weather-clear-night-symbolic": ["weather-clear-night", "night-light-symbolic", "alarm-symbolic"],
    "speedometer-symbolic": ["speedometer", "utilities-system-monitor-symbolic"],
    "view-private-symbolic": ["view-private", "security-high-symbolic", "emblem-readonly-symbolic"],
    "user-bookmarks-symbolic": ["user-bookmarks", "starred-symbolic"],
    "system-search-symbolic": ["system-search", "edit-find-symbolic"],
    "emblem-favorite-symbolic": ["emblem-favorite", "starred-symbolic"],
    "preferences-desktop-keyboard-symbolic": ["preferences-desktop-keyboard", "input-keyboard-symbolic"],
    "accessories-text-editor-symbolic": ["accessories-text-editor", "text-editor-symbolic", "document-edit-symbolic"],
    "utilities-terminal-symbolic": ["utilities-terminal", "terminal-symbolic", "utilities-system-monitor-symbolic"],
    "applications-engineering-symbolic": ["applications-engineering", "applications-development-symbolic", "applications-utilities-symbolic"],
    "document-print-symbolic": ["document-print", "printer-symbolic", "document-save-symbolic"],
    "camera-photo-symbolic": ["camera-photo", "camera-symbolic"],
    "edit-redo-symbolic": ["edit-redo", "go-forward-symbolic", "go-next-symbolic"],
    "zoom-original-symbolic": ["zoom-original", "zoom-in-symbolic"],
    "pan-start-symbolic": ["pan-start", "go-previous-symbolic"],
    "pan-end-symbolic": ["pan-end", "go-next-symbolic"],
    "applications-graphics-symbolic": ["applications-graphics", "applications-multimedia-symbolic"],
    "channel-secure-symbolic": ["channel-secure", "security-high-symbolic", "dialog-password-symbolic"],
    "text-x-generic-symbolic": ["text-x-generic", "text-plain-symbolic"],
    "help-about-symbolic": ["help-about", "help-browser-symbolic"],
    "view-list-symbolic": ["view-list", "view-list-symbolic", "format-justify-fill-symbolic"],
    "applications-internet": ["applications-internet", "web-browser-symbolic", "web-browser"],
    "document-open-recent-symbolic": ["document-open-recent", "document-open-recent-symbolic", "document-open-symbolic"],
    "drive-harddisk-symbolic": ["drive-harddisk", "drive-harddisk-symbolic"],
}
_RESOLVED = {}


def resolve(name):
    if not name:
        return "text-x-generic-symbolic"
    if name in _RESOLVED:
        return _RESOLVED[name]
    theme = None
    try:
        theme = Gtk.IconTheme.get_default()
    except Exception:
        theme = None
    chosen = None
    for candidate in [name] + FALLBACKS.get(name, []):
        try:
            if theme is not None and theme.has_icon(candidate):
                chosen = candidate
                break
        except Exception:
            continue
    if chosen is None:
        chosen = (FALLBACKS.get(name) or [name])[-1]
    _RESOLVED[name] = chosen
    return chosen


def svg_pixbuf(svg, size=24):
    try:
        loader = GdkPixbuf.PixbufLoader()
        loader.write(svg.encode("utf-8"))
        loader.close()
        pixbuf = loader.get_pixbuf()
        if pixbuf and pixbuf.get_width() != size:
            return pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf
    except Exception:
        return None


def icon_image(name, size=16):
    image = Gtk.Image.new_from_icon_name(resolve(name), Gtk.IconSize.BUTTON)
    image.set_pixel_size(size)
    return image


def icon_button(name, tooltip=None, size=16):
    button = Gtk.Button()
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.add(icon_image(name, size))
    if tooltip:
        button.set_tooltip_text(tooltip)
    return button


def paw_image(size=18, color=ACCENT):
    pixbuf = svg_pixbuf(mascot.paw_svg(64, color), size)
    if pixbuf:
        return Gtk.Image.new_from_pixbuf(pixbuf)
    return Gtk.Image.new_from_icon_name("applications-internet", Gtk.IconSize.BUTTON)


def menu_item(label, icon=None, callback=None, accel=None, dangerous=False):
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    row.set_border_width(8)
    if icon:
        image = Gtk.Image.new_from_icon_name(resolve(icon), Gtk.IconSize.MENU)
        image.set_pixel_size(16)
        row.pack_start(image, False, False, 0)
    text = Gtk.Label(label=label, xalign=0)
    if dangerous:
        text.get_style_context().add_class("nlb-danger")
    row.pack_start(text, True, True, 0)
    if accel:
        key = Gtk.Label(label=accel)
        key.get_style_context().add_class("nlb-dim")
        key.set_xalign(1)
        row.pack_end(key, False, False, 0)
    button = Gtk.Button()
    button.add(row)
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.get_style_context().add_class("nlb-menu-item")
    if callback:
        button.connect("clicked", lambda *_: callback())
    button.show_all()
    return button


class MenuPopover(Gtk.Popover):
    def __init__(self, relative_to):
        super().__init__(relative_to=relative_to)
        self.set_modal(True)
        self.set_position(Gtk.PositionType.BOTTOM)
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(140)
        self._width = 330
        self.pages = {}
        self._boxes = {}
        Gtk.Popover.add(self, self._stack)
        self._build_root()

    def _scrolled(self, content, name):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(self._width)
        scroller.set_max_content_height(560)
        scroller.set_propagate_natural_height(True)
        scroller.add(content)
        self.pages[name] = scroller
        self._boxes[name] = content
        self._stack.add_named(scroller, name)
        return scroller

    def page(self, name, title=None, parent=None):
        if name in self.pages:
            return self._boxes[name]
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_border_width(6)
        if parent is not None:
            back = Gtk.Button()
            back_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            back_row.pack_start(icon_image("pan-start-symbolic"), False, False, 0)
            back_row.pack_start(Gtk.Label(label=title or "", xalign=0), True, True, 0)
            back.add(back_row)
            back.set_relief(Gtk.ReliefStyle.NONE)
            back.get_style_context().add_class("nlb-menu-item")
            back.connect("clicked", lambda *_: self._stack.set_visible_child_name(parent))
            back.show_all()
            box.pack_start(back, False, False, 0)
            box.pack_start(Gtk.Separator(), False, False, 4)
        self._scrolled(box, name)
        return box

    def _build_root(self):
        box = self.page("root")
        self.root = box

    def show_page(self, name):
        self._stack.set_visible_child_name(name)

    def add_widget(self, widget, page="root"):
        self._boxes[page].pack_start(widget, False, False, 0)

    def add_nav(self, label, target, icon, page="root"):
        button = menu_item(label, icon, lambda: self.show_page(target))
        button.get_child().get_children()[-1].set_text(label)
        self.add_widget(button, page)
        arrow = Gtk.Image.new_from_icon_name(resolve("pan-end-symbolic"), Gtk.IconSize.MENU)
        arrow.set_pixel_size(12)
        button.get_child().pack_end(arrow, False, False, 0)
        arrow.show()
        return button

    def add_separator(self, page="root"):
        self.add_widget(Gtk.Separator(), page)

    def add_label(self, text, page="root"):
        label = Gtk.Label(label=text, xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.get_style_context().add_class("nlb-menu-header")
        label.set_margin_start(10)
        label.set_margin_top(8)
        label.set_margin_bottom(2)
        self.add_widget(label, page)

    def add_switch(self, label, active, callback, page="root", icon=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_border_width(8)
        row.set_margin_start(2)
        if icon:
            image = Gtk.Image.new_from_icon_name(resolve(icon), Gtk.IconSize.MENU)
            image.set_pixel_size(16)
            row.pack_start(image, False, False, 0)
        text = Gtk.Label(label=label, xalign=0)
        row.pack_start(text, True, True, 0)
        switch = Gtk.Switch()
        switch.set_active(bool(active))
        switch.connect("state-set", lambda _s, state: (callback(state), False)[1])
        row.pack_end(switch, False, False, 0)
        wrapper = Gtk.ListBoxRow()
        wrapper.add(row)
        wrapper.set_activatable(False)
        self.add_widget(wrapper, page)
        wrapper.show_all()
        return switch


class TabLabel(Gtk.Box):
    def __init__(self, window, tab, show_close=True):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_border_width(4)
        self.window = window
        self.tab = tab
        self.icon = Gtk.Image()
        self.icon.set_pixel_size(16)
        self.icon.set_from_icon_name(resolve("text-x-generic-symbolic"), Gtk.IconSize.BUTTON)
        self.pack_start(self.icon, False, False, 0)
        self.label = Gtk.Label(label="Новая вкладка")
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_max_width_chars(24)
        self.pack_start(self.label, True, True, 0)
        self.audio = Gtk.Image.new_from_icon_name(resolve("audio-volume-medium-symbolic"), Gtk.IconSize.BUTTON)
        self.audio.set_no_show_all(True)
        self.audio.set_pixel_size(14)
        self.audio.set_tooltip_text("Вкладка воспроизводит звук — нажмите, чтобы заглушить")
        self.audio.connect("button-press-event", self._on_audio_click)
        self.pack_start(self.audio, False, False, 0)
        self.spinner = Gtk.Spinner()
        self.spinner.set_no_show_all(True)
        self.spinner.set_visible(False)
        self.pack_start(self.spinner, False, False, 0)
        self.close = Gtk.Button()
        self.close.set_relief(Gtk.ReliefStyle.NONE)
        self.close.set_focus_on_click(False)
        self.close.add(icon_image("window-close-symbolic", 14))
        self.close.set_tooltip_text("Закрыть вкладку")
        self.close.get_style_context().add_class("nlb-tab-close")
        self.close.connect("clicked", lambda *_: window.close_tab(tab))
        self.pack_start(self.close, False, False, 0)
        if not show_close:
            self.close.set_visible(False)
        self.show_all()
        self.audio.set_visible(False)
        self.spinner.set_visible(False)

    def _on_audio_click(self, _widget, event):
        if event.button == 1:
            self.tab.toggle_mute()
            return True
        return False

    def set_title(self, title):
        self.label.set_text(title or "Без названия")
        self.set_tooltip_text(title or "")

    def set_favicon(self, pixbuf):
        if pixbuf:
            self.icon.set_from_pixbuf(pixbuf)
        else:
            self.icon.set_from_icon_name(resolve("text-x-generic-symbolic"), Gtk.IconSize.BUTTON)

    def set_loading(self, loading):
        if loading:
            self.icon.set_visible(False)
            self.spinner.set_visible(True)
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.set_visible(False)
            self.icon.set_visible(True)

    def set_audio(self, playing, muted=False):
        if playing or muted:
            self.audio.set_from_icon_name(
                resolve("audio-volume-muted-symbolic" if muted else "audio-volume-medium-symbolic"),
                Gtk.IconSize.BUTTON,
            )
            self.audio.set_visible(True)
        else:
            self.audio.set_visible(False)


class SuggestionPopover(Gtk.Popover):
    def __init__(self, entry, on_accept):
        super().__init__(relative_to=entry)
        self.set_modal(False)
        self.set_position(Gtk.PositionType.BOTTOM)
        self.entry = entry
        self.on_accept = on_accept
        self.listbox = Gtk.ListBox()
        self.listbox.set_activate_on_single_click(False)
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(560)
        scroller.set_max_content_height(340)
        scroller.set_propagate_natural_height(True)
        scroller.add(self.listbox)
        self.add(scroller)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.rows = []

    def _on_row_activated(self, _listbox, row):
        if getattr(row, "payload", None) is not None:
            self.hide()
            self.on_accept(row.payload)

    def set_rows(self, rows):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self.rows = []
        for payload, title, subtitle, icon_name, kind in rows:
            row = Gtk.ListBoxRow()
            row.payload = payload
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_border_width(6)
            if kind == "search":
                image = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.BUTTON)
            elif kind == "url":
                image = Gtk.Image.new_from_icon_name("applications-internet", Gtk.IconSize.BUTTON)
            else:
                image = Gtk.Image.new_from_icon_name(icon_name or "document-open-recent-symbolic", Gtk.IconSize.BUTTON)
            image.set_pixel_size(18)
            box.pack_start(image, False, False, 0)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            label = Gtk.Label(label=title, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            texts.pack_start(label, False, False, 0)
            if subtitle:
                sub = Gtk.Label(label=subtitle, xalign=0)
                sub.set_ellipsize(Pango.EllipsizeMode.END)
                sub.get_style_context().add_class("nlb-dim")
                texts.pack_start(sub, False, False, 0)
            box.pack_start(texts, True, True, 0)
            row.add(box)
            self.listbox.add(row)
            self.rows.append(row)
        self.listbox.show_all()

    def move_selection(self, delta):
        if not self.rows:
            return
        current = self.listbox.get_selected_row()
        index = 0 if current is None else self.rows.index(current)
        index = max(0, min(len(self.rows) - 1, index + delta))
        self.listbox.select_row(self.rows[index])

    def activate_current(self):
        row = self.listbox.get_selected_row()
        if row is None and self.rows:
            row = self.rows[0]
        if row is not None and getattr(row, "payload", None) is not None:
            self.hide()
            self.on_accept(row.payload)
            return True
        return False


class AddressBar(Gtk.Box):
    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.window = window
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Введите адрес или поисковый запрос")
        self.entry.set_has_frame(True)
        self.entry.set_width_chars(30)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "applications-internet-symbolic")
        self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, "Сведения о соединении")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "non-starred-symbolic")
        self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Добавить в закладки")
        self.entry.connect("activate", self._on_activate)
        self.entry.connect("changed", self._on_changed)
        self.entry.connect("focus-in-event", self._on_focus_in)
        self.entry.connect("focus-out-event", lambda *_: self._on_focus_out())
        self.entry.connect("key-press-event", self._on_key_press)
        self.entry.connect("icon-release", self._on_icon_release)
        self.entry.connect("button-press-event", self._on_button_press)
        self.entry.get_style_context().add_class("nlb-address")
        self.pack_start(self.entry, True, True, 0)
        self.popover = SuggestionPopover(self.entry, self._accept)
        self.entry.set_can_focus(True)
        self._internal_update = False
        self._last_typed = ""
        self._capture = False
        self._suggest_timeout = None

    def _current_tab(self):
        return self.window.current_tab

    def set_text(self, text, capture=False):
        self._internal_update = True
        self.entry.set_text(text or "")
        self.entry.set_position(-1)
        self._internal_update = False
        self._capture = capture

    def show_url(self, url):
        if self.entry.has_focus():
            return
        display = self.window.display_url(url)
        self.set_text(display)

    def update_security(self, url):
        if search.is_internal(url):
            self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "applications-internet-symbolic")
            self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, "Внутренняя страница NoLags")
        elif url.startswith("https://"):
            self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "channel-secure-symbolic")
            self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, "Соединение защищено (HTTPS)")
        elif url.startswith("http://"):
            self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "dialog-warning-symbolic")
            self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, "Соединение без шифрования (HTTP)")
        else:
            self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "applications-internet-symbolic")
            self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, "Введите адрес или запрос")

    def update_star(self, url):
        try:
            starred = self.window.storage.is_bookmarked(url)
        except Exception:
            starred = False
        self.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY,
            "starred-symbolic" if starred else "non-starred-symbolic",
        )
        self.entry.set_icon_tooltip_text(
            Gtk.EntryIconPosition.SECONDARY,
            "Убрать из закладок" if starred else "Добавить в закладки",
        )

    def focus(self, select_all=True):
        self.entry.grab_focus()
        if select_all:
            self.entry.select_region(0, -1)

    def _on_activate(self, _entry):
        text = self.entry.get_text().strip()
        if not text:
            return
        if self.popover.get_visible():
            row = self.popover.listbox.get_selected_row()
            if row is not None and getattr(row, "payload", None) is not None:
                payload = row.payload
                self.popover.hide()
                self._accept(payload)
                return
        self.popover.hide()
        tab = self._current_tab()
        if tab is None:
            return
        if search.is_internal(tab.url):
            tab.navigate(text, from_omnibox=True)
        else:
            self.window.open_from_page(tab, text)
        if self.window.settings.get("new_tab_focus_address"):
            tab.view.grab_focus()

    def _accept(self, payload):
        tab = self._current_tab()
        if tab is None:
            return
        self.popover.hide()
        if isinstance(payload, tuple) and payload[0] == "search":
            self.window.open_from_page(tab, payload[1], force_search=True)
        else:
            self.window.open_from_page(tab, payload)

    def _on_focus_in(self, _entry, _event):
        self._capture = True
        self.window.set_address_focus(True)
        tab = self._current_tab()
        if tab and tab.url:
            self.set_text(tab.url)
            self.entry.select_region(0, -1)
        self.entry.set_position(-1)
        return False

    def _on_focus_out(self):
        self.window.set_address_focus(False)
        tab = self._current_tab()
        if tab:
            self.show_url(tab.url)
        return False

    def _on_button_press(self, _entry, event):
        if event.button == 1 and not self.entry.has_focus():
            return False
        return False

    def _on_icon_release(self, _entry, position, _event):
        if position == Gtk.EntryIconPosition.SECONDARY:
            tab = self._current_tab()
            if tab:
                self.window.toggle_bookmark(tab.url, tab.title)
        elif position == Gtk.EntryIconPosition.PRIMARY:
            self.window.show_connection_info()
        return True

    def _on_key_press(self, _entry, event):
        key = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        if key in (Gdk.KEY_Down, Gdk.KEY_Up):
            if self.popover.get_visible() and self.popover.rows:
                self.popover.move_selection(1 if key == Gdk.KEY_Down else -1)
                return True
        if key == Gdk.KEY_Escape:
            if self.popover.get_visible():
                self.popover.hide()
                return True
            tab = self._current_tab()
            if tab:
                self.show_url(tab.url)
            self.window.content_area.grab_focus()
            return True
        if key == Gdk.KEY_Return and (state & Gdk.ModifierType.SHIFT_MASK):
            text = self.entry.get_text().strip()
            self.popover.hide()
            tab = self._current_tab()
            if tab and text:
                self.window.open_from_page(tab, text, force_search=True)
            return True
        return False

    def _on_changed(self, _entry):
        if self._internal_update:
            return
        text = self.entry.get_text().strip()
        if not text:
            self.popover.hide()
            return
        if self._suggest_timeout:
            GLib.source_remove(self._suggest_timeout)
        self._suggest_timeout = GLib.timeout_add(90, self._do_suggest, text)

    def _do_suggest(self, text):
        self._suggest_timeout = None
        if not text or not self.entry.has_focus():
            return False
        if not self.window.settings.get("suggestions_enabled"):
            return False
        rows = self.window.build_suggestions(text)
        if rows:
            self.popover.set_rows(rows)
            self.popover.show_all()
        else:
            self.popover.hide()
        return False

    def set_loading_progress(self, progress):
        ctx = self.entry.get_style_context()
        if 0.0 < progress < 1.0:
            ctx.add_class("nlb-loading")
        else:
            ctx.remove_class("nlb-loading")


class FindBar(Gtk.Revealer):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.set_transition_duration(120)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.set_border_width(6)
        bar.get_style_context().add_class("nlb-findbar")
        label = Gtk.Label(label="Найти:")
        bar.pack_start(label, False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Текст для поиска на странице")
        self.entry.connect("changed", self._on_changed)
        self.entry.connect("activate", lambda _e: self.find_next())
        self.entry.connect("key-press-event", self._on_key)
        bar.pack_start(self.entry, True, True, 0)
        self.counter = Gtk.Label(label="")
        self.counter.get_style_context().add_class("nlb-dim")
        bar.pack_start(self.counter, False, False, 0)
        previous = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        previous.set_tooltip_text("Предыдущее совпадение (Shift+Enter)")
        previous.connect("clicked", lambda *_: self.find_previous())
        bar.pack_start(previous, False, False, 0)
        next_button = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        next_button.set_tooltip_text("Следующее совпадение (Enter)")
        next_button.connect("clicked", lambda *_: self.find_next())
        bar.pack_start(next_button, False, False, 0)
        close = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        close.set_tooltip_text("Закрыть поиск (Esc)")
        close.connect("clicked", lambda *_: self.close())
        bar.pack_start(close, False, False, 0)
        self.add(bar)
        self.matches = 0

    def _on_key(self, _entry, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if event.keyval == Gdk.KEY_Return and (event.state & Gdk.ModifierType.SHIFT_MASK):
            self.find_previous()
            return True
        return False

    def open(self, text=None):
        self.set_reveal_child(True)
        tab = self.window.current_tab
        if text:
            self.entry.set_text(text)
        else:
            selection = self.window.get_selected_text()
            if selection and len(selection) < 120:
                self.entry.set_text(selection)
        self.entry.grab_focus()
        self.entry.select_region(0, -1)
        if self.entry.get_text():
            self._on_changed(self.entry)

    def close(self):
        self.set_reveal_child(False)
        tab = self.window.current_tab
        if tab:
            tab.view.grab_focus()

    def _controller(self):
        tab = self.window.current_tab
        return tab.view.get_find_controller() if tab else None

    def _on_changed(self, entry):
        controller = self._controller()
        if controller is None:
            return
        text = entry.get_text()
        if not text:
            controller.search_finish()
            self.counter.set_text("")
            return
        options = WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND
        controller.search(text, options, 200)

    def find_next(self):
        controller = self._controller()
        if controller:
            controller.search_next()

    def find_previous(self):
        controller = self._controller()
        if controller:
            controller.search_previous()

    def set_count(self, matches):
        self.matches = matches
        self.counter.set_text(f"{matches} совпадений" if matches else "не найдено")


class StatusBar(Gtk.Revealer):
    def __init__(self):
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(100)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.set_border_width(3)
        bar.get_style_context().add_class("nlb-statusbar")
        self.link_label = Gtk.Label(label="", xalign=0)
        self.link_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        bar.pack_start(self.link_label, True, True, 0)
        self.zoom_label = Gtk.Label(label="")
        self.zoom_label.get_style_context().add_class("nlb-dim")
        bar.pack_end(self.zoom_label, False, False, 0)
        self.mem_label = Gtk.Label(label="")
        self.mem_label.get_style_context().add_class("nlb-dim")
        bar.pack_end(self.mem_label, False, False, 0)
        self.add(bar)
        self.show_all()

    def set_link(self, text):
        self.link_label.set_text(text or "")

    def set_zoom(self, zoom):
        self.zoom_label.set_text("" if abs(zoom - 1.0) < 0.01 else f"Масштаб {int(round(zoom * 100))}%")

    def set_memory(self, text):
        self.mem_label.set_text(text or "")


class DownloadsWindow(Gtk.Window):
    def __init__(self, window):
        super().__init__(title="Загрузки — NoLags Browser", transient_for=window)
        self.window = window
        self.set_default_size(640, 420)
        self.set_icon_name("nolagsbrowser")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_border_width(8)
        clear = Gtk.Button(label="Очистить список")
        clear.connect("clicked", self._on_clear)
        toolbar.pack_start(clear, False, False, 0)
        folder = Gtk.Button(label="Открыть папку загрузок")
        folder.connect("clicked", lambda *_: util.open_folder(window.download_dir()))
        toolbar.pack_start(folder, False, False, 0)
        box.pack_start(toolbar, False, False, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.listbox)
        box.pack_start(scroller, True, True, 0)
        self.add(box)
        self.connect("key-press-event", self._on_key)
        self.reload()

    def _on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_clear(self):
        self.window.storage.clear_downloads()
        self.reload()

    def reload(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        rows = self.window.storage.downloads(300)
        if not rows:
            empty = Gtk.Label(label="Пока ничего не скачано.\nВсе загрузки появятся здесь.")
            empty.set_justify(Gtk.Justification.CENTER)
            empty.set_margin_top(60)
            empty.get_style_context().add_class("nlb-dim")
            self.listbox.add(empty)
        for row in rows:
            self.listbox.add(self._build_row(row))
        self.listbox.show_all()

    def _build_row(self, data):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(8)
        image = Gtk.Image.new_from_icon_name("emblem-downloads-symbolic", Gtk.IconSize.BUTTON)
        image.set_pixel_size(22)
        box.pack_start(image, False, False, 0)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label=data.get("filename") or "Файл", xalign=0)
        title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        texts.pack_start(title, False, False, 0)
        state = data.get("state") or "done"
        labels = {
            "started": "загружается",
            "done": "готово",
            "failed": "ошибка",
            "cancelled": "отменено",
        }
        sub = Gtk.Label(
            label=f"{util.human_size(data.get('size') or 0)} · {labels.get(state, state)} · {util.human_time(data.get('created'))}",
            xalign=0,
        )
        sub.get_style_context().add_class("nlb-dim")
        texts.pack_start(sub, False, False, 0)
        box.pack_start(texts, True, True, 0)
        path = data.get("path") or ""
        if path and state == "done":
            open_file = Gtk.Button(label="Открыть")
            open_file.connect("clicked", lambda *_: util.xdg_open(path))
            box.pack_end(open_file, False, False, 0)
            open_dir = Gtk.Button.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)
            open_dir.set_tooltip_text("Показать в папке")
            open_dir.connect("clicked", lambda *_: util.open_folder(path))
            box.pack_end(open_dir, False, False, 0)
        row.add(box)
        return row


class TabSearchPopover(Gtk.Popover):
    def __init__(self, window):
        super().__init__(relative_to=window.tab_overview_button)
        self.window = window
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_modal(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(8)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Найти вкладку…")
        self.entry.connect("changed", lambda _e: self._refresh())
        self.entry.connect("key-press-event", self._on_key)
        box.pack_start(self.entry, False, False, 0)
        self.listbox = Gtk.ListBox()
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(380)
        scroller.set_max_content_height(400)
        scroller.set_propagate_natural_height(True)
        scroller.add(self.listbox)
        box.pack_start(scroller, True, True, 0)
        self.add(box)
        self.listbox.connect("row-activated", self._on_activate)
        self.show_all()

    def open(self):
        self._refresh()
        self.show_all()
        self.entry.grab_focus()

    def _refresh(self):
        query = self.entry.get_text().strip().lower()
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        for tab in self.window.tabs:
            title = tab.title or "Без названия"
            if query and query not in title.lower() and query not in (tab.url or "").lower():
                continue
            row = Gtk.ListBoxRow()
            row.tab_ref = tab
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_border_width(6)
            image = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.BUTTON)
            box.pack_start(image, False, False, 0)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            label = Gtk.Label(label=title, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            texts.pack_start(label, False, False, 0)
            sub = Gtk.Label(label=search.pretty_url(tab.url), xalign=0)
            sub.set_ellipsize(Pango.EllipsizeMode.END)
            sub.get_style_context().add_class("nlb-dim")
            texts.pack_start(sub, False, False, 0)
            box.pack_start(texts, True, True, 0)
            row.add(box)
            self.listbox.add(row)
        self.listbox.show_all()

    def _on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            current = self.listbox.get_selected_row()
            rows = self.listbox.get_children()
            if not rows:
                return True
            index = 0 if current is None else rows.index(current)
            index = max(0, min(len(rows) - 1, index + (1 if event.keyval == Gdk.KEY_Down else -1)))
            self.listbox.select_row(rows[index])
            return True
        return False

    def _on_activate(self, _listbox, row):
        tab = getattr(row, "tab_ref", None)
        if tab:
            self.window.select_tab(tab)
            self.hide()
