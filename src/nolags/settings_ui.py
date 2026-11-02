import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from . import search, util
from .adblock import AdBlocker

CATEGORIES = [
    ("main", "Основные", "preferences-system-symbolic"),
    ("look", "Внешний вид", "applications-graphics-symbolic"),
    ("privacy", "Приватность", "security-high-symbolic"),
    ("memory", "Производительность", "utilities-system-monitor-symbolic"),
    ("data", "Данные и профиль", "drive-harddisk-symbolic"),
]

BOOL_ROWS = {
    "main": [
        ("restore_session", "Восстанавливать сеанс при запуске", "Открывать вкладки, которые были при закрытии"),
        ("new_tab_focus_address", "Фокус в адресной строке", "На новой вкладке сразу можно печатать запрос"),
        ("ask_quit_multiple", "Спрашивать при закрытии нескольких вкладок", "Защита от случайного закрытия окна"),
        ("confirm_close_tabs", "Подтверждать закрытие вкладок", "Спрашивать перед закрытием вкладки с введённым текстом"),
        ("close_button_on_tabs", "Кнопка закрытия на вкладках", "Показывать крестик на каждой вкладке"),
        ("show_bookmarks_bar", "Панель закладок", "Показывать строку закладок под адресной строкой"),
        ("show_statusbar", "Строка состояния", "Показывать адрес ссылки и потребление памяти"),
        ("show_tab_tooltips", "Подсказки на вкладках", "Показывать полное название страницы"),
        ("switch_to_new_tabs", "Переключаться на новую вкладку", "Открытая из ссылки вкладка становится активной"),
        ("middle_click_paste", "Вставка средней кнопкой", "Средняя кнопка в адресной строке вставляет буфер обмена"),
        ("mouse_gestures", "Жесты мышью", "Перетаскивание правой кнопкой: влево — назад, вправо — вперёд"),
        ("jump_to_start_on_reload", "Прокрутка в начало при обновлении", "Как в классических браузерах"),
        ("single_instance", "Одна копия браузера", "Новые запуски открывают вкладку в текущем окне"),
    ],
    "look": [
        ("compact_mode", "Компактный режим", "Уменьшенные кнопки и отступы — экономит место на экране"),
        ("stripe_toolbar", "Полосатая панель", "Мягкий фон панели инструментов"),
        ("show_paw_loader", "Лапка вместо спиннера", "Анимация загрузки в виде кошачьей лапки"),
        ("highlight_domains", "Выделять домен в адресе", "Подсвечивать основную часть адреса"),
        ("show_full_url", "Показывать полный адрес", "Не скрывать https:// и www."),
        ("trim_trailing_slash", "Убирать слеш в конце", "Короткий вид адреса"),
        ("show_frame_warning", "Предупреждение о встраивании", "Показывать, если сайт запрещает показ во фрейме"),
        ("tabs_as_list", "Вкладки списком", "Вертикальный список вкладок в боковой панели"),
    ],
    "privacy": [
        ("block_third_party_cookies", "Блокировать сторонние cookie", "Основной способ остановить межсайтовое отслеживание"),
        ("itp", "Защита от отслеживания (ITP)", "Ограничивает хранение данных трекерами"),
        ("block_popups", "Блокировать всплывающие окна", "Открывать pop-up только по клику"),
        ("dnt", "Заголовок Do Not Track", "Просить сайты не отслеживать"),
        ("clear_on_exit", "Очищать данные при выходе", "История, cookie, кэш по выбору"),
        ("load_ads_hosts", "Показывать заблокированное", "Отключить фильтрацию рекламных доменов"),
    ],
    "memory": [
        ("auto_discard", "Усыплять неактивные вкладки", "Освобождать память вкладок, которые давно не открывали"),
        ("low_memory_mode", "Режим низкого потребления", "Агрессивнее выгружать вкладки и чистить кэш"),
        ("hardware_acceleration", "Аппаратное ускорение", "Использовать GPU для отрисовки страниц"),
        ("enable_webgl", "WebGL", "Ускоренная 2D/3D-графика в браузере"),
        ("smooth_scrolling", "Плавная прокрутка", "Может нагружать слабый процессор"),
        ("load_images", "Загружать изображения", "Выключение сильно экономит трафик и память"),
        ("enable_javascript", "JavaScript", "Без него многие сайты перестанут работать"),
        ("preload_new_tab", "Предзагрузка новой вкладки", "Открывать новую вкладку быстрее за счёт памяти"),
        ("lazy_favicons", "Ленивые иконки сайтов", "Загружать favicon только для видимых вкладок"),
        ("restore_crashed_tabs", "Восстанавливать упавшие вкладки", "Перезагружать страницу после падения процесса"),
        ("suggestions_enabled", "Подсказки в адресной строке", "История, закладки и поиск"),
        ("history_suggestions", "Подсказки из истории", "Показывать часто посещаемые страницы"),
        ("bookmark_suggestions", "Подсказки из закладок", "Показывать сохранённые страницы"),
    ],
    "data": [
        ("ask_download_dir", "Спрашивать папку для загрузок", "Иначе файлы сохраняются в папку загрузок"),
        ("auto_open_downloads", "Открывать файлы после загрузки", "Запускать скачанный файл автоматически"),
        ("clear_on_exit_history", "Очищать историю при выходе", ""),
        ("clear_on_exit_cookies", "Удалять cookie при выходе", ""),
        ("clear_on_exit_cache", "Очищать кэш при выходе", ""),
    ],
}

CHOICE_ROWS = {
    "main": [
        ("startup_mode", "При запуске", [("newtab", "Новая вкладка"), ("home", "Домашняя страница"), ("restore", "Продолжить сеанс"), ("urls", "Набор страниц")]),
        ("search_engine", "Поисковая система", [(key, value[0]) for key, value in search.ENGINES.items()] + [("custom", "Своя система")]),
        ("tab_position", "Положение вкладок", [("top", "Сверху"), ("bottom", "Снизу"), ("left", "Слева"), ("right", "Справа")]),
        ("user_agent_mode", "User-Agent", [("chrome", "Chrome (совместимость)"), ("firefox", "Firefox"), ("auto", "Как у WebKit"), ("custom", "Свой")]),
        ("ui_theme", "Тема интерфейса", [("system", "Системная"), ("light", "Светлая"), ("dark", "Тёмная")]),
        ("toolbar_style", "Стиль кнопок", [("icons", "Только значки"), ("text", "Только текст"), ("both", "Значки и текст")]),
    ],
    "memory": [
        ("accelerated_compositing", "Аппаратный рендеринг", [("ondemand", "По требованию"), ("always", "Всегда"), ("never", "Никогда (экономия)")]),
        ("autoplay", "Автовоспроизведение", [("gesture", "Только по клику"), ("allow", "Разрешать звук"), ("mute", "Разрешать без звука"), ("deny", "Запрещать")]),
    ],
}

SPIN_ROWS = {
    "memory": [
        ("tab_discard_delay", "Усыплять вкладку через, мин", 0, 1440, 1),
        ("memory_trim_interval", "Чистить память каждые, мин", 0, 240, 1),
    ],
    "look": [
        ("tab_min_width", "Минимальная ширина вкладки", 30, 200, 5),
        ("tab_max_width", "Максимальная ширина вкладки", 80, 400, 5),
    ],
    "main": [
        ("suggestions_limit", "Строк в подсказках", 3, 20, 1),
    ],
}


class SettingsWindow(Gtk.Window):
    def __init__(self, parent, settings, on_change=None):
        super().__init__(title="Настройки — NoLags Browser")
        self.settings = settings
        self.on_change = on_change
        self.set_transient_for(parent)
        self.set_default_size(880, 620)
        self.set_icon_name("nolagsbrowser")
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.rows = {}

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "Настройки"
        header.props.subtitle = "NoLags Browser"
        self.set_titlebar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.pack_start(content, True, True, 0)

        self.sidebar = Gtk.ListBox()
        self.sidebar.set_size_request(200, -1)
        self.sidebar.get_style_context().add_class("nlb-settings-side")
        for key, label, icon in CATEGORIES:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_border_width(11)
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            image.set_pixel_size(16)
            box.pack_start(image, False, False, 0)
            box.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            row.add(box)
            row.category = key
            self.sidebar.add(row)
        self.sidebar.connect("row-selected", self._on_category)
        content.pack_start(self.sidebar, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        content.pack_start(self.stack, True, True, 0)

        for key, label, icon in CATEGORIES:
            self.stack.add_named(self._build_page(key), key)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom.set_border_width(10)
        reset = Gtk.Button(label="Сбросить настройки")
        reset.connect("clicked", self._on_reset)
        bottom.pack_start(reset, False, False, 0)
        shortcut = Gtk.Button(label="Горячие клавиши")
        shortcut.connect("clicked", lambda *_: parent.show_shortcuts_page())
        bottom.pack_start(shortcut, False, False, 0)
        spacer = Gtk.Box()
        bottom.pack_start(spacer, True, True, 0)
        close = Gtk.Button(label="Готово")
        close.get_style_context().add_class("suggested-action")
        close.connect("clicked", lambda *_: self.close())
        bottom.pack_end(close, False, False, 0)
        outer.pack_start(Gtk.Separator(), False, False, 0)
        outer.pack_start(bottom, False, False, 0)
        self.add(outer)
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))
        self.show_all()

    def _on_category(self, _listbox, row):
        if row is not None:
            self.stack.set_visible_child_name(row.category)

    def _section(self, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{title}</b>")
        label.set_margin_start(4)
        label.set_margin_top(14)
        label.set_margin_bottom(6)
        box.pack_start(label, False, False, 0)
        return box

    def _row(self, title, subtitle, control):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_border_width(8)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        label = Gtk.Label(label=title, xalign=0)
        texts.pack_start(label, False, False, 0)
        if subtitle:
            sub = Gtk.Label(label=subtitle, xalign=0)
            sub.set_ellipsize(Pango.EllipsizeMode.END)
            sub.get_style_context().add_class("nlb-dim")
            sub.set_line_wrap(True)
            texts.pack_start(sub, False, False, 0)
        row.pack_start(texts, True, True, 0)
        row.pack_end(control, False, False, 0)
        wrapper = Gtk.ListBoxRow()
        wrapper.set_activatable(False)
        wrapper.add(row)
        return wrapper

    def _switch(self, key, page, section_box):
        switch = Gtk.Switch()
        switch.set_active(bool(self.settings.get(key)))
        switch.connect("state-set", lambda _s, state: self._set(key, state))
        self.rows[key] = switch
        return switch

    def _set(self, key, value):
        if key.startswith("clear_on_exit_"):
            option = key[len("clear_on_exit_"):]
            options = dict(self.settings.get("clear_on_exit_options") or {})
            options[option] = value
            self.settings.set("clear_on_exit_options", options)
        else:
            self.settings.set(key, value)
        if self.on_change:
            self.on_change(key, value)
        return False

    def _build_page(self, category):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        inner.set_border_width(18)
        titles = {
            "main": "Запуск и взаимодействие",
            "look": "Внешний вид",
            "privacy": "Приватность и блокировка",
            "memory": "Память и производительность",
            "data": "Загрузки и данные профиля",
        }
        inner.pack_start(self._section(titles[category]), False, False, 0)
        for key, title, subtitle in BOOL_ROWS.get(category, []):
            current = self.settings.get(key)
            if key.startswith("clear_on_exit_"):
                current = (self.settings.get("clear_on_exit_options") or {}).get(key[len("clear_on_exit_"):], False)
            switch = Gtk.Switch()
            switch.set_active(bool(current))
            switch.connect("state-set", lambda _s, state, k=key: self._set(k, state))
            self.rows[key] = switch
            inner.pack_start(self._row(title, subtitle, switch), False, False, 0)
        for key, title, options in CHOICE_ROWS.get(category, []):
            combo = Gtk.ComboBoxText()
            current = self.settings.get(key)
            for value, label in options:
                combo.append(value, label)
            combo.set_active_id(str(current))
            combo.connect("changed", lambda c, k=key: self._set(k, c.get_active_id()))
            self.rows[key] = combo
            inner.pack_start(self._row(title, "", combo), False, False, 0)
        for key, title, low, high, step in SPIN_ROWS.get(category, []):
            spin = Gtk.SpinButton.new_with_range(low, high, step)
            spin.set_value(float(self.settings.get(key) or 0))
            spin.connect("value-changed", lambda s, k=key: self._set(k, int(s.get_value())))
            self.rows[key] = spin
            inner.pack_start(self._row(title, "", spin), False, False, 0)
        if category == "main":
            inner.pack_start(self._section("Адреса"), False, False, 0)
            home = Gtk.Entry()
            home.set_text(str(self.settings.get("home_page") or ""))
            home.set_width_chars(28)
            home.connect("changed", lambda e: self._set("home_page", e.get_text()))
            inner.pack_start(self._row("Домашняя страница", "Открывается по кнопке «Домой»", home), False, False, 0)
            custom = Gtk.Entry()
            custom.set_text(str(self.settings.get("custom_search") or ""))
            custom.set_placeholder_text("https://example.com/?q={q}")
            custom.set_width_chars(28)
            custom.connect("changed", lambda e: self._set("custom_search", e.get_text()))
            inner.pack_start(self._row("Своя поисковая система", "Шаблон с {q} вместо запроса", custom), False, False, 0)
            ua = Gtk.Entry()
            ua.set_text(str(self.settings.get("custom_user_agent") or ""))
            ua.set_width_chars(28)
            ua.connect("changed", lambda e: self._set("custom_user_agent", e.get_text()))
            inner.pack_start(self._row("Свой User-Agent", "Работает при выборе «Свой» выше", ua), False, False, 0)
        if category == "data":
            inner.pack_start(self._section("Обслуживание"), False, False, 0)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            actions.set_margin_top(8)
            for label, callback in (
                ("Очистить кэш", lambda *_: self._action("cache")),
                ("Очистить cookie", lambda *_: self._action("cookies")),
                ("Сжать базу", lambda *_: self._action("vacuum")),
                ("Папка профиля", lambda *_: self._action("folder")),
            ):
                button = Gtk.Button(label=label)
                button.connect("clicked", callback)
                actions.pack_start(button, False, False, 0)
            inner.pack_start(actions, False, False, 0)
            info = Gtk.Label(xalign=0)
            info.get_style_context().add_class("nlb-dim")
            info.set_margin_top(12)
            info.set_line_wrap(True)
            self.info_label = info
            inner.pack_start(info, False, False, 0)
        scroller.add(inner)
        frame.pack_start(scroller, True, True, 0)
        return frame

    def _action(self, what):
        window = self.get_transient_for()
        if window is None:
            return
        if what == "cache":
            window.clear_cache()
        elif what == "cookies":
            window.clear_cookies()
        elif what == "vacuum":
            window.storage.vacuum()
            window.toast("База данных сжата")
        elif what == "folder":
            util.xdg_open(window.storage.base)

    def _on_reset(self):
        from .settings import DEFAULTS

        for key, value in DEFAULTS.items():
            self.settings.set(key, value)
        self.close()
        parent = self.get_transient_for()
        if parent:
            parent.toast("Настройки сброшены")
            parent.rebuild_ui_from_settings()
