using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace NoLagsBrowser
{
    public static class UrlTools
    {
        public static readonly Dictionary<string, (string Name, string Template)> Engines = new Dictionary<string, (string, string)>
        {
            { "duckduckgo", ("DuckDuckGo", "https://duckduckgo.com/?q={q}") },
            { "google", ("Google", "https://www.google.com/search?q={q}") },
            { "yandex", ("Яндекс", "https://yandex.ru/search/?text={q}") },
            { "bing", ("Bing", "https://www.bing.com/search?q={q}") },
            { "brave", ("Brave", "https://search.brave.com/search?q={q}") },
            { "startpage", ("Startpage", "https://www.startpage.com/sp/search?query={q}") },
            { "wikipedia", ("Википедия", "https://ru.wikipedia.org/w/index.php?search={q}") }
        };

        private static readonly Regex SchemeRe = new Regex(@"^[a-zA-Z][a-zA-Z0-9+.\-]*:", RegexOptions.Compiled);
        private static readonly Regex DomainRe = new Regex(
            @"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:[/?#].*)?$",
            RegexOptions.Compiled);
        private static readonly Regex LocalRe = new Regex(
            @"^(?:localhost|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#].*)?$", RegexOptions.Compiled);

        public static string EngineName(SettingsData settings)
        {
            if (settings.SearchEngine == "custom" && !string.IsNullOrWhiteSpace(settings.CustomSearch))
                return "своя система";
            return Engines.TryGetValue(settings.SearchEngine ?? "duckduckgo", out var engine) ? engine.Name : "DuckDuckGo";
        }

        public static string SearchUrl(SettingsData settings, string query)
        {
            string template;
            if (settings.SearchEngine == "custom" && !string.IsNullOrWhiteSpace(settings.CustomSearch))
                template = settings.CustomSearch.Contains("{q}") ? settings.CustomSearch : settings.CustomSearch.TrimEnd('/') + "/?q={q}";
            else
                template = Engines.TryGetValue(settings.SearchEngine ?? "duckduckgo", out var engine)
                    ? engine.Template
                    : "https://duckduckgo.com/?q={q}";
            return template.Replace("{q}", Uri.EscapeDataString(query.Trim()));
        }

        public static string Normalize(string text, SettingsData settings, bool forceSearch = false)
        {
            string value = (text ?? "").Trim();
            if (value.Length == 0)
                return "";
            if (forceSearch)
                return SearchUrl(settings, value);
            if (value.StartsWith("nolags://", StringComparison.OrdinalIgnoreCase) ||
                value.StartsWith("about:", StringComparison.OrdinalIgnoreCase) ||
                value.StartsWith("view-source:", StringComparison.OrdinalIgnoreCase))
                return value;
            if (SchemeRe.IsMatch(value))
            {
                string scheme = value.Substring(0, value.IndexOf(':')).ToLowerInvariant();
                if (scheme == "http" || scheme == "https" || scheme == "file" || scheme == "ftp" ||
                    scheme == "mailto" || scheme == "data" || scheme == "blob" || scheme == "view-source")
                    return value;
                if (!value.Contains(" ") && value.Contains("."))
                    return "https://" + value;
            }
            if (!value.Contains(" ") && (DomainRe.IsMatch(value) || LocalRe.IsMatch(value)))
                return "https://" + value;
            return SearchUrl(settings, value);
        }

        public static string Host(string url)
        {
            try
            {
                var uri = new Uri(url, UriKind.Absolute);
                return uri.Host.StartsWith("www.", StringComparison.OrdinalIgnoreCase) ? uri.Host.Substring(4) : uri.Host;
            }
            catch
            {
                return "";
            }
        }

        public static string Pretty(string url)
        {
            if (string.IsNullOrWhiteSpace(url))
                return "";
            if (url.StartsWith("nolags://"))
                return "NoLags";
            try
            {
                var uri = new Uri(url, UriKind.Absolute);
                if (uri.Scheme == "http" || uri.Scheme == "https")
                {
                    string host = uri.Host.StartsWith("www.", StringComparison.OrdinalIgnoreCase) ? uri.Host.Substring(4) : uri.Host;
                    string path = uri.AbsolutePath == "/" ? "" : uri.AbsolutePath;
                    return host + path + (string.IsNullOrEmpty(uri.Query) ? "" : uri.Query);
                }
                if (uri.Scheme == "file")
                    return uri.LocalPath;
            }
            catch
            {
            }
            return url;
        }

        public static bool IsInternal(string url) =>
            !string.IsNullOrEmpty(url) && (url.StartsWith("nolags://") || url.StartsWith("about:nolags"));
    }
}
