import html
import json
import time

from . import APP_NAME, APP_VERSION, mascot, search, util
from .adblock import AdBlocker

BASE_CSS = """
:root {
  --accent: __ACCENT__;
  --bg: #f5f3ee;
  --bg2: #ffffff;
  --fg: #20232a;
  --dim: #6c7480;
  --line: rgba(32, 35, 42, .12);
  --shadow: 0 10px 30px rgba(30, 35, 45, .08);
  --radius: 16px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14171c;
    --bg2: #1c2027;
    --fg: #e9edf2;
    --dim: #9aa4b2;
    --line: rgba(233, 237, 242, .12);
    --shadow: 0 10px 30px rgba(0, 0, 0, .35);
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--fg);
  font-family: "Inter", "Noto Sans", "DejaVu Sans", system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
button {
  font: inherit; color: inherit; background: var(--bg2); border: 1px solid var(--line);
  border-radius: 10px; padding: 8px 14px; cursor: pointer; transition: .15s ease;
}
button:hover { border-color: var(--accent); color: var(--accent); }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
button.primary:hover { filter: brightness(1.08); color: #fff; }
button.ghost { background: transparent; }
input, textarea, select {
  font: inherit; color: inherit; background: var(--bg2);
  border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; outline: none;
}
input:focus, textarea:focus, select:focus { border-color: var(--accent); }
.wrap { max-width: 1080px; margin: 0 auto; padding: 28px 26px 60px; }
.top { display: flex; align-items: center; gap: 12px; margin-bottom: 26px; }
.logo { width: 38px; height: 38px; border-radius: 11px; }
.top h1 { font-size: 20px; margin: 0; letter-spacing: .2px; }
.top .spacer { flex: 1; }
.top nav { display: flex; gap: 6px; flex-wrap: wrap; }
.top nav a {
  color: var(--dim); padding: 7px 11px; border-radius: 9px; font-size: 13.5px;
}
.top nav a:hover, .top nav a.active { background: var(--bg2); color: var(--fg); text-decoration: none; }
.card {
  background: var(--bg2); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px; box-shadow: var(--shadow);
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.row { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--line); }
.row:last-child { border-bottom: none; }
.row .grow { flex: 1; min-width: 0; }
.row .title { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row .sub { color: var(--dim); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav {
  width: 30px; height: 30px; border-radius: 9px; flex: none; display: flex;
  align-items: center; justify-content: center; color: #fff; font-weight: 600; font-size: 12px;
}
.empty { color: var(--dim); text-align: center; padding: 26px 0; font-size: 13.5px; }
.pill { border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px; font-size: 13px; color: var(--dim); }
.section-title { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--dim); margin: 0 0 10px; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.toolbar input[type=search] { flex: 1; min-width: 180px; }
.tag { font-size: 11.5px; color: var(--dim); border: 1px solid var(--line); border-radius: 6px; padding: 1px 6px; }
footer { color: var(--dim); font-size: 12.5px; text-align: center; padding: 26px 0 10px; }
kbd {
  background: var(--bg2); border: 1px solid var(--line); border-bottom-width: 2px;
  border-radius: 6px; padding: 1px 7px; font-size: 12px; font-family: inherit;
}
"""

BRIDGE_JS = r"""
function nl(action, data) {
  try {
    var payload = Object.assign({ action: action }, data || {});
    window.webkit.messageHandlers.nl.postMessage(JSON.stringify(payload));
  } catch (err) {}
}
function nlFav(text) {
  var colors = ["#2fb7a4", "#e07a5f", "#6c8cd5", "#c77dff", "#f4a261", "#5aa9e6", "#8ac926", "#ff7096"];
  var total = 0;
  for (var i = 0; i < (text || "x").length; i++) total += text.charCodeAt(i);
  return colors[total % colors.length];
}
function nlInit() {
  var nodes = document.querySelectorAll(".fav[data-host]");
  for (var i = 0; i < nodes.length; i++) {
    var host = (nodes[i].getAttribute("data-host") || "?").replace(/^www\./, "");
    if (nodes[i].getAttribute("data-fixed")) continue;
    nodes[i].style.background = nlFav(host);
    nodes[i].textContent = host.slice(0, 2).toUpperCase();
  }
  var search = document.querySelector("input[data-autofocus]");
  if (search && document.hasFocus()) search.focus();
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", nlInit);
} else {
  nlInit();
}
setTimeout(nlInit, 250);
document.addEventListener("click", function (event) {
  var el = event.target.closest("[data-action]");
  if (!el) return;
  event.preventDefault();
  var action = el.getAttribute("data-action");
  var payload = {};
  try { payload = JSON.parse(el.getAttribute("data-payload") || "{}"); } catch (e) {}
  nl(action, payload);
});
document.addEventListener("keydown", function (event) {
  if (event.key === "/" && event.target.tagName !== "INPUT" && event.target.tagName !== "TEXTAREA") {
    var input = document.querySelector("input[data-autofocus]");
    if (input) { event.preventDefault(); input.focus(); }
  }
});
"""


def _json(data):
    try:
        return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    except (TypeError, ValueError):
        return "{}"


def _base(settings, title, extra_css=""):
    accent = settings.get("accent_color") or "#2fb7a4"
    css = BASE_CSS.replace("__ACCENT__", accent) + extra_css
    icon = mascot.logo_uri(64)
    return css, icon, accent, title


def _shell(settings, title, body, script="", extra_css="", nav_active=""):
    css, icon, accent, title = _base(settings, title, extra_css)
    nav_items = [
        ("nolags://newtab", "Новая вкладка", "newtab"),
        ("nolags://history", "История", "history"),
        ("nolags://bookmarks", "Закладки", "bookmarks"),
        ("nolags://downloads", "Загрузки", "downloads"),
        ("nolags://notes", "Заметки", "notes"),
        ("nolags://about", "О браузере", "about"),
    ]
    nav = "".join(
        f'<a href="{url}" class="{"active" if key == nav_active else ""}">{label}</a>'
        for url, label, key in nav_items
    )
    logo = f'<img class="logo" src="{icon}" alt="">' if icon else ""
    return (
        "<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
        "<div class=\"wrap\">"
        f"<div class=\"top\">{logo}<h1>{html.escape(title)}</h1>"
        f"<div class=\"spacer\"></div><nav>{nav}</nav></div>"
        f"{body}"
        "<footer>NoLags Browser · WebKitGTK</footer></div>"
        f"<script>{BRIDGE_JS}{script}</script></body></html>"
    )


NEWTAB_EXTRA_CSS = """
body.nt { overflow-x: hidden; }
.hero { display: flex; gap: 26px; align-items: center; margin: 12px 0 30px; flex-wrap: wrap; }
.hero .text { flex: 1; min-width: 260px; }
.hero h1 { font-size: 32px; margin: 0 0 6px; letter-spacing: -.4px; }
.hero .sub { color: var(--dim); margin: 0 0 20px; }
.hero .mascot { width: 190px; height: auto; filter: drop-shadow(0 18px 26px rgba(0,0,0,.16)); }
.searchbar { display: flex; gap: 8px; align-items: center; }
.searchbar input { flex: 1; padding: 14px 16px; font-size: 16px; border-radius: 14px; }
.searchbar button { padding: 13px 18px; border-radius: 14px; }
.engine { color: var(--dim); font-size: 12.5px; margin-top: 8px; }
.chips { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.chips button { padding: 6px 12px; font-size: 13px; border-radius: 999px; }
.sites { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 12px; }
.site {
  display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 14px 6px;
  border-radius: 14px; border: 1px solid transparent; cursor: pointer;
}
.site:hover { background: var(--bg2); border-color: var(--line); }
.site .fav { width: 40px; height: 40px; border-radius: 12px; font-size: 15px; }
.site span { font-size: 12.5px; color: var(--dim); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 18px; }
.actions button { display: flex; align-items: center; gap: 8px; justify-content: flex-start; }
.mem { font-size: 26px; font-weight: 600; letter-spacing: -.5px; }
.mem small { font-size: 13px; color: var(--dim); font-weight: 400; }
.bar { height: 8px; border-radius: 999px; background: var(--line); overflow: hidden; margin: 10px 0 4px; }
.bar > i { display: block; height: 100%; background: var(--accent); border-radius: 999px; transition: width .4s ease; }
.tip { color: var(--dim); font-size: 13px; }
.clock { color: var(--dim); font-variant-numeric: tabular-nums; }
.splash { display: none; }
.paw { width: 16px; height: 16px; vertical-align: -3px; }
"""

NEWTAB_HTML = """
<div class="hero">
  <div class="text">
    <h1>__GREETING__</h1>
    <p class="sub">__DATE__ · поиск: __ENGINE__</p>
    <form class="searchbar" id="sf">
      <input id="q" data-autofocus placeholder="Поиск или адрес…" autocomplete="off" spellcheck="false">
      <button class="primary" type="submit">Найти</button>
    </form>
    <div class="engine">Enter — искать, Shift+Enter — открыть адрес как есть</div>
    <div class="chips">__CHIPS__</div>
  </div>
  __MASCOT__
</div>
<div class="grid">
  <div class="card">
    <p class="section-title">Часто посещаемые</p>
    <div class="sites">__SITES__</div>
  </div>
  <div class="card">
    <p class="section-title">Недавно закрытые</p>
    __CLOSED__
  </div>
  <div class="card">
    <p class="section-title">Закладки</p>
    __BOOKMARKS__
  </div>
  <div class="card">
    <p class="section-title">Память</p>
    <div class="mem" id="memValue">— <small>МБ всего</small></div>
    <div class="bar"><i id="memBar" style="width:0%"></i></div>
    <div class="tip" id="memNote">Считаю потребление…</div>
    <div class="actions">
      <button data-action="trim_memory">Освободить память</button>
      <button data-action="task_manager">Диспетчер вкладок</button>
    </div>
  </div>
</div>
<div class="card" style="margin-top:16px">
  <p class="section-title">Быстрые действия</p>
  <div class="actions">
    <button data-action="open" data-payload='{"url":"nolags://history"}'>История</button>
    <button data-action="open" data-payload='{"url":"nolags://downloads"}'>Загрузки</button>
    <button data-action="open" data-payload='{"url":"nolags://notes"}'>Заметки</button>
    <button data-action="open" data-payload='{"url":"nolags://bookmarks"}'>Закладки</button>
    <button data-action="settings">Настройки</button>
    <button data-action="clear_cache">Очистить кэш</button>
    <button data-action="blocklist_hosts">Список блокировки</button>
    <button data-action="shortcuts">Горячие клавиши</button>
  </div>
</div>
<p class="tip" style="text-align:center;margin-top:22px">__TIP__</p>
"""

NEWTAB_JS = r"""
document.getElementById("sf").addEventListener("submit", function (event) {
  event.preventDefault();
  var value = document.getElementById("q").value.trim();
  if (!value) return;
  if (event.submitter && event.shiftKey) nl("navigate_raw", { text: value, force: true });
  else nl("navigate", { text: value });
});
document.getElementById("q").addEventListener("keydown", function (event) {
  if (event.key === "Enter" && event.shiftKey) {
    event.preventDefault();
    nl("navigate_raw", { text: this.value.trim(), force: true });
  }
});
window.nlSetMem = function (data) {
  var value = document.getElementById("memValue");
  var bar = document.getElementById("memBar");
  var note = document.getElementById("memNote");
  if (!value || !bar) return;
  value.innerHTML = (data.total || 0).toFixed(0) + " <small>МБ всего</small>";
  var percent = Math.min(100, ((data.total || 0) / (data.limit || 3800)) * 100);
  bar.style.width = percent.toFixed(1) + "%";
  bar.style.background = percent > 80 ? "#e07a5f" : "";
  note.textContent = data.tabs + " вкладок · интерфейс " + (data.own || 0).toFixed(0) +
    " МБ · веб-процессы " + (data.web || 0).toFixed(0) + " МБ";
};
setInterval(function () { nl("mem_stats"); }, 5000);
function tick() {
  var now = new Date();
  var clock = document.getElementById("clock");
  if (clock) clock.textContent = now.toLocaleTimeString("ru-RU");
}
tick(); setInterval(tick, 1000);
"""


def _greeting():
    hour = time.localtime().tm_hour
    if 5 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def _date_line():
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    now = time.localtime()
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    return f"{weekdays[now.tm_wday]}, {now.tm_mday} {months[now.tm_mon - 1]} {now.tm_year}"


TIPS = [
    "Средняя кнопка мыши на ссылке открывает её в фоновой вкладке.",
    "Ctrl+Shift+T возвращает только что закрытую вкладку.",
    "Двойной щелчок по пустому месту панели вкладок создаёт новую вкладку.",
    "Alt+1…9 переключает вкладки, Ctrl+9 открывает последнюю.",
    "Ctrl+Shift+Delete открывает очистку данных просмотра.",
    "F12 открывает инструменты разработчика, Ctrl+U — исходный код страницы.",
    "Колесо мыши с Ctrl масштабирует страницу, Ctrl+0 сбрасывает масштаб.",
    "Вкладка, висящая в фоне, может засыпать и освободить память.",
    "Ctrl+Shift+M быстро выключает звук у вкладки.",
    "Правая кнопка мыши с перетаскиванием влево — назад, вправо — вперёд.",
]


def page_newtab(settings, data):
    engine = search.engine_name(settings)
    sites = data.get("top_sites") or []
    if sites:
        sites_html = "".join(
            f'<div class="site" data-action="navigate" data-payload=\'{_json({"url": site["url"]})}\' title="{html.escape(site["url"])}">'
            f'<div class="fav" data-host="{html.escape(site.get("host") or "")}"></div>'
            f'<span>{html.escape(site.get("host") or "")}</span></div>'
            for site in sites
        )
    else:
        sites_html = '<p class="empty">Пока пусто — посетите пару сайтов, и они появятся здесь.</p>'
    closed = data.get("recently_closed") or []
    if closed:
        closed_html = "".join(
            f'<div class="row"><div class="fav" data-host="{html.escape(search.display_host(item.get("url", "")))}"></div>'
            f'<div class="grow"><div class="title">{html.escape(util.truncate(item.get("title") or item.get("url") or "", 60))}</div>'
            f'<div class="sub">{html.escape(search.pretty_url(item.get("url") or ""))}</div></div>'
            f'<button class="ghost" data-action="restore_tab" data-payload=\'{_json({"url": item.get("url"), "title": item.get("title")})}\'>Вернуть</button></div>'
            for item in closed[:6]
        )
    else:
        closed_html = '<p class="empty">Закрытые вкладки появятся здесь.</p>'
    bookmarks = data.get("bookmarks") or []
    if bookmarks:
        bookmarks_html = "".join(
            f'<div class="row" data-action="navigate" data-payload=\'{_json({"url": item["url"]})}\' style="cursor:pointer">'
            f'<div class="fav" data-host="{html.escape(search.display_host(item["url"]))}"></div>'
            f'<div class="grow"><div class="title">{html.escape(util.truncate(item.get("title") or item["url"], 60))}</div>'
            f'<div class="sub">{html.escape(search.pretty_url(item["url"]))}</div></div></div>'
            for item in bookmarks[:6]
        )
    else:
        bookmarks_html = '<p class="empty">Добавьте страницу в закладки звёздочкой в адресной строке.</p>'
    chips = "".join(
        f'<button data-action="navigate" data-payload=\'{_json({"url": item["url"]})}\'>{html.escape(item["label"])}</button>'
        for item in data.get("chips") or []
    )
    mascot_html = ""
    hero = mascot.mascot_data_uri("hero", 380)
    sleep = mascot.mascot_data_uri("sleep", 200)
    if hero:
        mascot_html = f'<img class="mascot" src="{hero}" alt="">'
    tip = TIPS[int(time.time() // 3600) % len(TIPS)]
    body = (
        NEWTAB_HTML.replace("__GREETING__", _greeting())
        .replace("__DATE__", _date_line())
        .replace("__ENGINE__", html.escape(engine))
        .replace("__CHIPS__", chips)
        .replace("__MASCOT__", mascot_html)
        .replace("__SITES__", sites_html)
        .replace("__CLOSED__", closed_html)
        .replace("__BOOKMARKS__", bookmarks_html)
        .replace("__TIP__", html.escape(tip))
    )
    page = _shell(settings, "Новая вкладка", body, NEWTAB_JS, NEWTAB_EXTRA_CSS, "newtab")
    page = page.replace("<body>", '<body class="nt">')
    page = page.replace("<h1>Новая вкладка</h1>", "<h1>NoLags</h1>")
    return page


def _fav(url):
    host = search.display_host(url) or url
    return f'<div class="fav" data-host="{html.escape(host)}"></div>'


def page_history(settings, data, query=""):
    groups = data.get("history") or {}
    rows = []
    for day, items in groups.items():
        rows.append(f'<p class="section-title" style="margin-top:18px">{html.escape(util.day_label(day))}</p>')
        for item in items:
            rows.append(
                f'<div class="row">{_fav(item["url"])}'
                f'<div class="grow" data-action="navigate" data-payload=\'{_json({"url": item["url"]})}\' style="cursor:pointer">'
                f'<div class="title">{html.escape(item.get("title") or item["url"])}</div>'
                f'<div class="sub">{html.escape(search.pretty_url(item["url"]))} · {int(item.get("visits") or 1)} визитов</div></div>'
                f'<button class="ghost" data-action="history_delete" data-payload=\'{_json({"url": item["url"]})}\' title="Удалить">✕</button></div>'
            )
    listing = "".join(rows) if rows else '<p class="empty">История пуста.</p>'
    body = f"""
<div class="toolbar">
  <input type="search" id="q" data-autofocus placeholder="Поиск по истории…" value="{html.escape(query)}">
  <button data-action="history_reload">Найти</button>
  <button class="ghost" data-action="history_export">Экспорт JSON</button>
  <button class="ghost" data-action="history_clear">Очистить всё</button>
</div>
<div class="card">{listing}</div>
"""
    script = """
document.getElementById("q").addEventListener("keydown", function (event) {
  if (event.key === "Enter") nl("history_search", { query: this.value });
});
"""
    return _shell(settings, "История", body, script, nav_active="history")


def page_bookmarks(settings, data):
    folders = data.get("folders") or {}
    blocks = []
    for folder, items in folders.items():
        title = folder or "Без папки"
        rows = "".join(
            f'<div class="row">{_fav(item["url"])}'
            f'<div class="grow" data-action="navigate" data-payload=\'{_json({"url": item["url"]})}\' style="cursor:pointer">'
            f'<div class="title">{html.escape(item.get("title") or item["url"])}</div>'
            f'<div class="sub">{html.escape(search.pretty_url(item["url"]))}</div></div>'
            f'<button class="ghost" data-action="bookmark_delete" data-payload=\'{_json({"url": item["url"]})}\' title="Удалить">✕</button></div>'
            for item in items
        )
        blocks.append(f'<p class="section-title" style="margin-top:18px">{html.escape(title)}</p>{rows}')
    listing = "".join(blocks) if blocks else '<p class="empty">Закладок пока нет.</p>'
    body = f"""
<div class="toolbar">
  <button class="primary" data-action="bookmark_current">Добавить текущую страницу</button>
  <button class="ghost" data-action="bookmarks_import">Импорт HTML</button>
  <button class="ghost" data-action="bookmarks_export">Экспорт HTML</button>
  <button class="ghost" data-action="bookmarks_export_json">Экспорт JSON</button>
</div>
<div class="card">{listing}</div>
"""
    return _shell(settings, "Закладки", body, nav_active="bookmarks")


def page_downloads(settings, data):
    items = data.get("downloads") or []
    rows = []
    for item in items:
        state = item.get("state") or "done"
        labels = {"started": "загружается", "done": "готово", "failed": "ошибка", "cancelled": "отменено"}
        rows.append(
            f'<div class="row"><div class="fav" data-host="{html.escape(item.get("filename") or "file")}">⬇</div>'
            f'<div class="grow"><div class="title">{html.escape(item.get("filename") or "Файл")}</div>'
            f'<div class="sub">{util.human_size(item.get("size") or 0)} · {labels.get(state, state)} · {util.human_time(item.get("created"))}</div></div>'
            f'<button class="ghost" data-action="download_open" data-payload=\'{_json({"path": item.get("path")})}\'>Открыть</button>'
            f'<button class="ghost" data-action="download_folder" data-payload=\'{_json({"path": item.get("path")})}\'>Папка</button></div>'
        )
    listing = "".join(rows) if rows else '<p class="empty">Загрузок нет.</p>'
    body = f"""
<div class="toolbar">
  <button class="ghost" data-action="downloads_folder">Открыть папку загрузок</button>
  <button class="ghost" data-action="downloads_clear">Очистить список</button>
</div>
<div class="card">{listing}</div>
"""
    return _shell(settings, "Загрузки", body, nav_active="downloads")


def page_notes(settings, data):
    notes = data.get("notes") or []
    rows = "".join(
        f'<div class="row"><div class="grow"><div class="title">{html.escape(util.truncate(item.get("title") or item.get("url") or "Заметка", 70))}</div>'
        f'<div class="sub" style="white-space:pre-wrap">{html.escape(item.get("body") or "")}</div>'
        f'<div class="sub">{util.human_time(item.get("created"))}</div></div>'
        f'<button class="ghost" data-action="note_delete" data-payload=\'{_json({"id": item.get("id")})}\'>✕</button></div>'
        for item in notes
    )
    listing = rows if rows else '<p class="empty">Заметок нет.</p>'
    body = f"""
<div class="card" style="margin-bottom:16px">
  <p class="section-title">Новая заметка</p>
  <textarea id="note" placeholder="Текст заметки…" style="width:100%;min-height:110px;resize:vertical"></textarea>
  <div class="toolbar" style="margin-top:10px;margin-bottom:0">
    <button class="primary" id="saveNote">Сохранить</button>
    <button class="ghost" data-action="note_from_page">Взять со страницы</button>
  </div>
</div>
<div class="card">{listing}</div>
"""
    script = """
document.getElementById("saveNote").addEventListener("click", function () {
  var area = document.getElementById("note");
  if (!area.value.trim()) return;
  nl("note_add", { body: area.value });
});
window.nlNoteFromPage = function (title, text) {
  var area = document.getElementById("note");
  if (!area) return;
  area.value = title + "\\n\\n" + text;
  area.focus();
};
"""
    return _shell(settings, "Заметки", body, script, nav_active="notes")


def page_about(settings, data):
    hero = mascot.mascot_data_uri("hero", 420) or mascot.mascot_data_uri("happy", 420)
    stats = data.get("stats") or {}
    blocker = data.get("blocker") or {}
    mascot_html = f'<img src="{hero}" style="width:250px;border-radius:20px" alt="">' if hero else ""
    body = f"""
<div class="card" style="display:flex;gap:26px;align-items:center;flex-wrap:wrap">
  {mascot_html}
  <div style="flex:1;min-width:260px">
    <h2 style="margin:0 0 4px">{APP_NAME}</h2>
    <p style="margin:0 0 12px;color:var(--dim)">Версия {APP_VERSION} · движок WebKitGTK {data.get("webkit") or ""}</p>
    <p style="margin:0 0 16px">Лёгкий браузер на GTK3 и WebKitGTK с ручным управлением памятью,
    встроенной блокировкой трекеров и минимальным интерфейсом.</p>
    <div class="toolbar" style="margin-bottom:0">
      <button class="primary" data-action="open" data-payload='{{"url":"https://github.com/frizovdanyash/nolagsbrowser"}}'>Репозиторий</button>
      <button class="ghost" data-action="shortcuts">Горячие клавиши</button>
      <button class="ghost" data-action="settings">Настройки</button>
    </div>
  </div>
</div>
<div class="grid" style="margin-top:16px">
  <div class="card"><p class="section-title">Профиль</p>
    <div class="row"><div class="grow">Записей в истории</div><b>{int(stats.get("history") or 0)}</b></div>
    <div class="row"><div class="grow">Закладок</div><b>{int(stats.get("bookmarks") or 0)}</b></div>
    <div class="row"><div class="grow">Загрузок</div><b>{int(stats.get("downloads") or 0)}</b></div>
    <div class="row"><div class="grow">Размер данных</div><b>{util.human_size(stats.get("db_size") or 0)}</b></div>
  </div>
  <div class="card"><p class="section-title">Блокировка</p>
    <div class="row"><div class="grow">Домены в списке</div><b>{int(blocker.get("count") or 0)}</b></div>
    <div class="row"><div class="grow">Сторонние cookie</div><b>{"блокируются" if settings.get("block_third_party_cookies") else "разрешены"}</b></div>
    <div class="row"><div class="grow">Защита от отслеживания</div><b>{"включена" if settings.get("itp") else "выключена"}</b></div>
    <div class="toolbar" style="margin:12px 0 0">
      <button class="ghost" data-action="blocklist_hosts">Hosts-файл</button>
      <button class="ghost" data-action="blocklist_update">Обновить список</button>
    </div>
  </div>
</div>
"""
    return _shell(settings, "О браузере", body, nav_active="about")


def page_shortcuts(settings, data):
    rows = [
        ("Ctrl+T", "Новая вкладка"), ("Ctrl+Shift+T", "Вернуть закрытую вкладку"),
        ("Ctrl+W", "Закрыть вкладку"), ("Ctrl+Shift+W", "Закрыть окно"),
        ("Ctrl+L / Alt+D / F6", "Адресная строка"), ("Ctrl+F", "Поиск на странице"),
        ("Ctrl+G / F3", "Следующее совпадение"), ("Ctrl+R / F5", "Обновить"),
        ("Ctrl+Shift+R", "Обновить без кэша"), ("Alt+← / Alt+→", "Назад / вперёд"),
        ("Alt+Home", "Домашняя страница"), ("Ctrl+Tab", "Следующая вкладка"),
        ("Ctrl+Shift+Tab", "Предыдущая вкладка"), ("Alt+1…9", "Выбор вкладки"),
        ("Ctrl+9", "Последняя вкладка"), ("Ctrl+D", "Добавить в закладки"),
        ("Ctrl+B", "Панель закладок"), ("Ctrl+H / Ctrl+Y", "История"),
        ("Ctrl+J", "Загрузки"), ("Ctrl+Shift+D", "Закладки в новую папку"),
        ("Ctrl+P", "Печать"), ("Ctrl+S", "Сохранить страницу"),
        ("Ctrl+Shift+S", "Скриншот страницы"), ("Ctrl+U", "Исходный код"),
        ("F12", "Инструменты разработчика"), ("Ctrl+Shift+Delete", "Очистка данных"),
        ("Ctrl+= / Ctrl+-", "Масштаб"), ("Ctrl+0", "Сброс масштаба"),
        ("F11", "Полный экран"), ("Ctrl+Shift+M", "Звук вкладки"),
        ("Ctrl+Shift+N", "Приватное окно"), ("Ctrl+N", "Новое окно"),
        ("Ctrl+Shift+P", "Командная строка"),
    ]
    table = "".join(
        f'<div class="row"><div class="grow">{html.escape(label)}</div><kbd>{html.escape(keys)}</kbd></div>'
        for keys, label in rows
    )
    body = f'<div class="card">{table}</div>'
    return _shell(settings, "Горячие клавиши", body, nav_active="")


def page_error(settings, data):
    sleep = mascot.mascot_data_uri("sleep", 260)
    image = f'<img src="{sleep}" style="width:200px;border-radius:18px" alt="">' if sleep else ""
    body = f"""
<div class="card" style="text-align:center;padding:36px 24px">
  {image}
  <h2 style="margin:16px 0 6px">Не удалось открыть страницу</h2>
  <p style="color:var(--dim);margin:0 0 6px">{html.escape(data.get("message") or "Неизвестная ошибка")}</p>
  <p style="color:var(--dim);margin:0 0 20px;word-break:break-all">{html.escape(data.get("url") or "")}</p>
  <div class="toolbar" style="justify-content:center;margin-bottom:0">
    <button class="primary" data-action="retry">Повторить</button>
    <button class="ghost" data-action="offline_check">Проверить соединение</button>
    <button class="ghost" data-action="open" data-payload='{{"url":"nolags://newtab"}}'>На главную</button>
  </div>
</div>
"""
    return _shell(settings, "Ошибка загрузки", body)


def page_command(settings, data):
    return page_newtab(settings, data)
