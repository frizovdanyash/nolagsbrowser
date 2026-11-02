import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from . import util


class ClearDataDialog(Gtk.Dialog):
    OPTIONS = [
        ("history", "История просмотров", True),
        ("cookies", "Cookie и данные сайтов", True),
        ("cache", "Кэш страниц", True),
        ("downloads", "Список загрузок", False),
        ("notes", "Заметки", False),
    ]

    def __init__(self, parent):
        super().__init__(title="Очистить данные", transient_for=parent)
        self.set_default_size(420, 300)
        self.add_buttons("Отмена", Gtk.ResponseType.CANCEL, "Очистить", Gtk.ResponseType.OK)
        self.switches = {}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(16)
        header = Gtk.Label(xalign=0)
        header.set_markup("<b>Что удалить?</b>")
        box.pack_start(header, False, False, 0)
        for key, label, default in self.OPTIONS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            switch = Gtk.Switch()
            switch.set_active(default)
            self.switches[key] = switch
            row.pack_end(switch, False, False, 0)
            box.pack_start(row, False, False, 0)
        note = Gtk.Label(label="Действие нельзя отменить.")
        note.get_style_context().add_class("nlb-dim")
        note.set_xalign(0)
        box.pack_start(Gtk.Separator(), False, False, 6)
        box.pack_start(note, False, False, 0)
        self.get_content_area().add(box)
        self.show_all()

    def options(self):
        return {key: switch.get_active() for key, switch in self.switches.items()}


class TaskManagerDialog(Gtk.Window):
    def __init__(self, window):
        super().__init__(title="Диспетчер вкладок — NoLags Browser")
        self.window = window
        self.set_transient_for(window)
        self.set_default_size(760, 460)
        self.set_icon_name("nolagsbrowser")
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "Диспетчер вкладок"
        header.props.subtitle = "Память и вкладки"
        self.set_titlebar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(12)
        self.summary = Gtk.Label(xalign=0)
        self.summary.set_markup("<b>Считаю…</b>")
        box.pack_start(self.summary, False, False, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.listbox)
        box.pack_start(scroller, True, True, 0)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        trim = Gtk.Button(label="Освободить память")
        trim.connect("clicked", lambda *_: self.window.trim_memory())
        buttons.pack_start(trim, False, False, 0)
        discard = Gtk.Button(label="Усыпить все фоновые")
        discard.connect("clicked", lambda *_: (self.window.discard_background_tabs(), self.refresh()))
        buttons.pack_start(discard, False, False, 0)
        close = Gtk.Button(label="Закрыть")
        close.connect("clicked", lambda *_: self.close())
        buttons.pack_end(close, False, False, 0)
        box.pack_start(buttons, False, False, 0)
        self.add(box)
        self.refresh()
        self._timer = None
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args):
        if self._timer:
            from gi.repository import GLib

            GLib.source_remove(self._timer)
            self._timer = None

    def refresh(self):
        from gi.repository import GLib

        for child in self.listbox.get_children():
            self.listbox.remove(child)
        total = util.webkit_memory_mb()
        own = util.self_memory_mb()
        self.summary.set_markup(
            f"<b>Всего ОЗУ браузера: {total:.0f} МБ</b>\n"
            f"<span size='small'>интерфейс {own:.0f} МБ · веб-процессы {max(0.0, total - own):.0f} МБ · вкладок {len(self.window.tabs)}</span>"
        )
        for index, tab in enumerate(self.window.tabs):
            row = Gtk.ListBoxRow()
            row.set_activatable(True)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_border_width(8)
            state = "спит" if tab.discarded else ("звук" if tab.view and tab.view.get_property("is-playing-audio") else "")
            title = Gtk.Label(label=tab.title or "Без названия", xalign=0)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(46)
            box.pack_start(title, True, True, 0)
            url = Gtk.Label(label=tab.url or "", xalign=0)
            url.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            url.get_style_context().add_class("nlb-dim")
            url.set_max_width_chars(36)
            box.pack_start(url, False, False, 0)
            if state:
                tag = Gtk.Label(label=state)
                tag.get_style_context().add_class("nlb-dim")
                box.pack_start(tag, False, False, 0)
            sleep = Gtk.Button(label="Усыпить")
            sleep.set_sensitive(not tab.discarded)
            sleep.connect("clicked", lambda _w, t=tab: self._discard(t))
            box.pack_end(sleep, False, False, 0)
            switch = Gtk.Button(label="Перейти")
            switch.connect("clicked", lambda _w, t=tab: self._select(t))
            box.pack_end(switch, False, False, 0)
            row.add(box)
            self.listbox.add(row)
        self.listbox.show_all()
        self._timer = GLib.timeout_add_seconds(3, self._tick)

    def _tick(self):
        self._timer = None
        total = util.webkit_memory_mb()
        self.summary.set_markup(
            f"<b>Всего ОЗУ браузера: {total:.0f} МБ</b>\n"
            f"<span size='small'>вкладок {len(self.window.tabs)}</span>"
        )
        return False

    def _discard(self, tab):
        if tab.discard():
            self.window.toast("Вкладка усыплена")
            self._timer = None
            self.refresh()

    def _select(self, tab):
        self.window.select_tab(tab)
        self.window.present()


class CommandPalette(Gtk.Window):
    COMMANDS = [
        ("Новая вкладка", "Ctrl+T", "tab_new"),
        ("Новое окно", "Ctrl+N", "window_new"),
        ("Приватное окно", "Ctrl+Shift+N", "window_private"),
        ("История", "Ctrl+H", "page_history"),
        ("Закладки", "Ctrl+Shift+O", "page_bookmarks"),
        ("Загрузки", "Ctrl+J", "page_downloads"),
        ("Заметки", "", "page_notes"),
        ("Настройки", "Ctrl+,", "settings"),
        ("Очистить данные", "Ctrl+Shift+Delete", "clear_data"),
        ("Освободить память", "", "trim"),
        ("Усыпить фоновые вкладки", "", "discard"),
        ("Диспетчер вкладок", "", "task_manager"),
        ("Исходный код страницы", "Ctrl+U", "view_source"),
        ("Инструменты разработчика", "F12", "devtools"),
        ("Скриншот страницы", "Ctrl+Shift+S", "screenshot"),
        ("Печать", "Ctrl+P", "print"),
        ("Режим чтения", "Ctrl+Shift+F", "reader"),
        ("Тёмная тема страниц", "", "style_dark"),
        ("Обычная тема страниц", "", "style_none"),
        ("Вернуть закрытую вкладку", "Ctrl+Shift+T", "reopen"),
        ("О браузере", "", "page_about"),
        ("Горячие клавиши", "", "shortcuts"),
    ]

    def __init__(self, window):
        super().__init__(title="Командная строка")
        self.window = window
        self.set_transient_for(window)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_default_size(560, 420)
        self.set_decorated(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Введите команду или адрес…")
        self.entry.connect("changed", lambda _e: self.refresh())
        self.entry.connect("key-press-event", self._on_key)
        box.pack_start(self.entry, False, False, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-activated", lambda _l, row: self.run(getattr(row, "command", "")))
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.listbox)
        box.pack_start(scroller, True, True, 0)
        self.add(box)
        self.refresh()

    def _on_key(self, _entry, event):
        from gi.repository import Gdk

        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            rows = self.listbox.get_children()
            if not rows:
                return True
            current = self.listbox.get_selected_row()
            index = 0 if current is None else rows.index(current)
            index = max(0, min(len(rows) - 1, index + (1 if event.keyval == Gdk.KEY_Down else -1)))
            self.listbox.select_row(rows[index])
            return True
        if event.keyval == Gdk.KEY_Return:
            row = self.listbox.get_selected_row() or (self.listbox.get_children() or [None])[0]
            if row is not None:
                self.run(getattr(row, "command", ""))
            return True
        return False

    def refresh(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        query = self.entry.get_text().strip().lower()
        if query and " " not in query and "." in query:
            row = Gtk.ListBoxRow()
            row.command = "url:" + query
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_border_width(8)
            box.pack_start(Gtk.Image.new_from_icon_name("applications-internet", Gtk.IconSize.BUTTON), False, False, 0)
            box.pack_start(Gtk.Label(label=f"Открыть {query}", xalign=0), True, True, 0)
            row.add(box)
            self.listbox.add(row)
        for label, accel, command in self.COMMANDS:
            if query and query not in label.lower():
                continue
            row = Gtk.ListBoxRow()
            row.command = command
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_border_width(8)
            text = Gtk.Label(label=label, xalign=0)
            box.pack_start(text, True, True, 0)
            if accel:
                key = Gtk.Label(label=accel)
                key.get_style_context().add_class("nlb-dim")
                box.pack_end(key, False, False, 0)
            row.add(box)
            self.listbox.add(row)
        self.listbox.show_all()
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])

    def run(self, command):
        window = self.window
        self.close()
        if command.startswith("url:"):
            if window.current_tab:
                window.current_tab.navigate(command[4:])
            return
        mapping = {
            "tab_new": lambda: window.create_tab(),
            "window_new": window.new_window,
            "window_private": window.new_private_window,
            "page_history": lambda: window.open_page("nolags://history"),
            "page_bookmarks": lambda: window.open_page("nolags://bookmarks"),
            "page_downloads": lambda: window.open_page("nolags://downloads"),
            "page_notes": lambda: window.open_page("nolags://notes"),
            "page_about": lambda: window.open_page("nolags://about"),
            "settings": window.open_settings,
            "clear_data": window.clear_data_dialog,
            "trim": window.trim_memory,
            "discard": window.discard_background_tabs,
            "task_manager": window.show_task_manager,
            "view_source": window.view_source,
            "devtools": window.devtools,
            "screenshot": window.screenshot,
            "print": window.print_page,
            "reader": lambda: window.current_tab and window.current_tab.toggle_reader(),
            "style_dark": lambda: window.set_site_style("dark"),
            "style_none": lambda: window.set_site_style("none"),
            "reopen": window.reopen_closed_tab,
            "shortcuts": window.show_shortcuts_page,
        }
        callback = mapping.get(command)
        if callback:
            callback()
