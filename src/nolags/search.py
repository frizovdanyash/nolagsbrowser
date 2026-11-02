import re
from urllib.parse import quote, urlparse

ENGINES = {
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q={q}&kae=d"),
    "google": ("Google", "https://www.google.com/search?q={q}"),
    "yandex": ("Yandex", "https://yandex.ru/search/?text={q}"),
    "bing": ("Bing", "https://www.bing.com/search?q={q}"),
    "brave": ("Brave", "https://search.brave.com/search?q={q}"),
    "startpage": ("Startpage", "https://www.startpage.com/sp/search?query={q}"),
    "wikipedia": ("Wikipedia", "https://ru.wikipedia.org/w/index.php?search={q}"),
}

SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:[/?#].*)?$"
)
LOCAL_RE = re.compile(r"^(?:localhost|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#].*)?$")
IPV6_RE = re.compile(r"^\[[0-9a-fA-F:]+\](?::\d+)?(?:[/?#].*)?$")
KNOWN_SCHEMES = {
    "http", "https", "file", "ftp", "about", "chrome", "nolags", "view-source",
    "mailto", "data", "javascript", "tel", "magnet", "ws", "wss", "blob",
}


def engine_for(settings):
    key = settings.get("search_engine") or "duckduckgo"
    if key == "custom":
        template = settings.get("custom_search") or ""
        name = settings.get("custom_search_name") or "Custom"
        if "{q}" not in template:
            template = template.rstrip("/") + "/?q={q}"
        return name, template
    return ENGINES.get(key, ENGINES["duckduckgo"])


def engine_name(settings):
    return engine_for(settings)[0]


def search_url(settings, query):
    template = engine_for(settings)[1]
    return template.replace("{q}", quote(query.strip(), safe=""))


def normalize_input(text, settings):
    value = (text or "").strip()
    if not value:
        return ""
    if value.startswith(("nolags:", "about:", "chrome:", "view-source:")):
        return value
    if SCHEME_RE.match(value):
        scheme = value.split(":", 1)[0].lower()
        if scheme in KNOWN_SCHEMES:
            return value
        if " " not in value and "." in value:
            return "https://" + value
    if " " not in value:
        if DOMAIN_RE.match(value) or LOCAL_RE.match(value) or IPV6_RE.match(value):
            return "https://" + value
        if value.startswith("/") or value.startswith("./") or value.startswith("../"):
            from pathlib import Path

            candidate = Path(value).expanduser()
            if candidate.exists():
                return candidate.resolve().as_uri()
    return search_url(settings, value)


def pretty_url(url, trim_slash=True):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if parsed.scheme in ("http", "https"):
        host = parsed.netloc
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path or ""
        if trim_slash and path.endswith("/") and len(path) > 1:
            path = path[:-1]
        rest = path
        if parsed.query:
            rest += "?" + parsed.query
        return host + rest
    if parsed.scheme == "file":
        return parsed.path
    if parsed.scheme == "nolags":
        return "NoLags"
    return url


def display_host(url):
    try:
        host = urlparse(url).netloc
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def is_internal(url):
    return url.startswith("nolags://") or url.startswith("about:nolags")


def host_matches(url, domain):
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    domain = domain.lower().strip(".")
    return host == domain or host.endswith("." + domain)
