using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

namespace NoLagsBrowser
{
    internal static class StartPage
    {
        private static string _mascot;
        private static string _sleep;

        private static string Resource(string name)
        {
            try
            {
                using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("NoLagsBrowser.Resources." + name);
                if (stream == null)
                    return "";
                using var memory = new MemoryStream();
                stream.CopyTo(memory);
                return "data:image/png;base64," + Convert.ToBase64String(memory.ToArray());
            }
            catch
            {
                return "";
            }
        }

        public static string Mascot => _mascot ??= Resource("mascot.png");
        public static string Sleep => _sleep ??= Resource("mascot_sleep.png");

        public static string Build(Storage storage)
        {
            var settings = storage.Settings;
            var sites = storage.TopSites(10).ToList();
            var bookmarks = storage.Bookmarks.Take(6).ToList();
            var builder = new StringBuilder();
            builder.AppendLine("<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\">");
            builder.AppendLine("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
            builder.Append("<title>Новая вкладка</title><style>");
            builder.Append(@"
:root{--bg:#f5f3ee;--bg2:#fff;--fg:#20232a;--dim:#6c7480;--line:rgba(32,35,42,.12);--accent:#2fb7a4}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--bg2:#1c2027;--fg:#e9edf2;--dim:#9aa4b2;--line:rgba(233,237,242,.12)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:'Segoe UI',system-ui,sans-serif;font-size:15px}
.wrap{max-width:1080px;margin:0 auto;padding:26px}
.hero{display:flex;gap:26px;align-items:center;margin:8px 0 26px;flex-wrap:wrap}
.hero h1{font-size:32px;margin:0 0 6px;letter-spacing:-.4px}
.sub{color:var(--dim);margin:0 0 18px}
.mascot{width:180px;border-radius:18px}
form{display:flex;gap:8px}
input[type=text]{flex:1;padding:14px 16px;font-size:16px;border-radius:14px;border:1px solid var(--line);background:var(--bg2);color:var(--fg);outline:none}
input[type=text]:focus{border-color:var(--accent)}
button{font:inherit;color:inherit;background:var(--bg2);border:1px solid var(--line);border-radius:14px;padding:12px 18px;cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.chips button{padding:6px 12px;border-radius:999px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:16px;padding:16px}
.ttl{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:0 0 10px}
.sites{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:10px}
.site{display:flex;flex-direction:column;align-items:center;gap:6px;padding:10px;border-radius:14px;cursor:pointer}
.site:hover{background:var(--bg)}
.fav{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:14px}
.site span{font-size:12px;color:var(--dim);max-width:96px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);cursor:pointer}
.row:last-child{border-bottom:none}
.row .t{flex:1;min-width:0}
.row .t div:first-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .t div:last-child{font-size:12px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px}
.actions button{text-align:left;padding:10px 14px;border-radius:12px}
.empty{color:var(--dim);font-size:13px;text-align:center;padding:18px 0}
footer{text-align:center;color:var(--dim);font-size:12px;padding:22px 0}
");
            builder.Append("</style></head><body><div class=\"wrap\"><div class=\"hero\"><div style=\"flex:1;min-width:260px\">");
            builder.Append($"<h1>{Greeting()}</h1><p class=\"sub\">{DateTime.Now:d MMMM yyyy} · поиск: {UrlTools.EngineName(settings)}</p>");
            builder.Append("<form id=\"sf\"><input type=\"text\" id=\"q\" placeholder=\"Поиск или адрес…\" autocomplete=\"off\" spellcheck=\"false\"><button class=\"primary\" type=\"submit\">Найти</button></form>");
            builder.Append("<div class=\"chips\">");
            foreach (var (label, url) in new[]
            {
                ("GitHub", "https://github.com"), ("YouTube", "https://youtube.com"),
                ("Википедия", "https://ru.wikipedia.org"), ("Хабр", "https://habr.com"),
                ("Stack Overflow", "https://stackoverflow.com"), ("Reddit", "https://reddit.com")
            })
                builder.Append($"<button type=\"button\" onclick=\"nl.navigate('{url}')\">{label}</button>");
            builder.Append("</div></div>");
            if (!string.IsNullOrEmpty(Mascot))
                builder.Append($"<img class=\"mascot\" src=\"{Mascot}\" alt=\"\">");
            builder.Append("</div><div class=\"grid\">");

            builder.Append("<div class=\"card\"><p class=\"ttl\">Часто посещаемые</p><div class=\"sites\">");
            if (sites.Count == 0)
                builder.Append("<p class=\"empty\">Пока пусто — посетите пару сайтов.</p>");
            foreach (var site in sites)
                builder.Append($"<div class=\"site\" onclick=\"nl.navigate('{Escape(site.Url)}')\"><div class=\"fav\" style=\"background:{ColorFor(site.Host)}\">{Escape(Initials(site.Host))}</div><span>{Escape(site.Host)}</span></div>");
            builder.Append("</div></div>");

            builder.Append("<div class=\"card\"><p class=\"ttl\">Закладки</p>");
            if (bookmarks.Count == 0)
                builder.Append("<p class=\"empty\">Добавьте страницу звёздочкой в адресной строке.</p>");
            foreach (var item in bookmarks)
                builder.Append($"<div class=\"row\" onclick=\"nl.navigate('{Escape(item.Url)}')\"><div class=\"fav\" style=\"background:{ColorFor(UrlTools.Host(item.Url))}\">{Escape(Initials(UrlTools.Host(item.Url)))}</div><div class=\"t\"><div>{Escape(Cut(item.Title ?? item.Url, 60))}</div><div>{Escape(UrlTools.Pretty(item.Url))}</div></div></div>");
            builder.Append("</div>");

            builder.Append("<div class=\"card\"><p class=\"ttl\">Память и действия</p><div style=\"font-size:24px;font-weight:600\" id=\"mem\">— МБ</div>");
            builder.Append("<div style=\"color:var(--dim);font-size:13px\" id=\"memNote\">Считаю потребление…</div><div class=\"actions\">");
            builder.Append("<button onclick=\"nl.action('trim')\">Освободить память</button>");
            builder.Append("<button onclick=\"nl.action('history')\">История</button>");
            builder.Append("<button onclick=\"nl.action('bookmarks')\">Закладки</button>");
            builder.Append("<button onclick=\"nl.action('downloads')\">Загрузки</button>");
            builder.Append("<button onclick=\"nl.action('sleep')\">Усыпить фоновые вкладки</button>");
            builder.Append("<button onclick=\"nl.action('settings')\">Настройки</button>");
            builder.Append("</div></div>");

            builder.Append("</div><footer>NoLags Browser · WebView2</footer></div>");
            builder.Append(@"
<script>
document.getElementById('sf').addEventListener('submit', function (e) {
  e.preventDefault();
  var value = document.getElementById('q').value.trim();
  if (!value) return;
  if (e.shiftKey) nl.raw(value); else nl.navigate(value);
});
document.getElementById('q').addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && e.shiftKey) { e.preventDefault(); nl.raw(this.value.trim()); }
});
window.nlMem = function (mb, tabs) {
  var m = document.getElementById('mem');
  var note = document.getElementById('memNote');
  if (m) m.textContent = mb + ' МБ';
  if (note) note.textContent = tabs + ' вкладок · включая веб-процессы';
};
setInterval(function () { nl.action('mem'); }, 6000);
</script>");
            builder.Append("</body></html>");
            return builder.ToString();
        }

        private static string Greeting()
        {
            int hour = DateTime.Now.Hour;
            if (hour >= 5 && hour < 12)
                return "Доброе утро";
            if (hour >= 12 && hour < 18)
                return "Добрый день";
            if (hour >= 18 && hour < 23)
                return "Добрый вечер";
            return "Доброй ночи";
        }

        private static string Escape(string text) =>
            (text ?? "").Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;").Replace("'", "\\'");

        private static string Cut(string text, int limit) =>
            string.IsNullOrEmpty(text) || text.Length <= limit ? text : text.Substring(0, limit - 1) + "…";

        private static string Initials(string host)
        {
            host = (host ?? "?").Replace("www.", "");
            return host.Length >= 2 ? host.Substring(0, 2).ToUpperInvariant() : host.ToUpperInvariant();
        }

        private static string ColorFor(string host)
        {
            string[] palette = { "#2fb7a4", "#e07a5f", "#6c8cd5", "#c77dff", "#f4a261", "#5aa9e6", "#8ac926", "#ff7096" };
            int total = 0;
            foreach (char character in host ?? "x")
                total += character;
            return palette[Math.Abs(total) % palette.Length];
        }
    }
}
