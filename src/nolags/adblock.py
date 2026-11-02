import json
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

from . import paths

TRACKER_HOSTS = [
    "google-analytics.com", "googletagmanager.com", "googletagservices.com",
    "doubleclick.net", "googleadservices.com", "adservice.google.com",
    "facebook.net", "connect.facebook.net", "pixel.facebook.com",
    "scorecardresearch.com", "quantserve.com", "quantcount.com",
    "hotjar.com", "fullstory.com", "mouseflow.com", "luckyorange.com",
    "criteo.com", "criteo.net", "taboola.com", "outbrain.com",
    "adnxs.com", "adsrvr.org", "rubiconproject.com", "pubmatic.com",
    "openx.net", "casalemedia.com", "smartadserver.com", "yieldmo.com",
    "moatads.com", "serving-sys.com", "2mdn.net", "adform.net",
    "amazon-adsystem.com", "media.net", "zedo.com", "exelator.com",
    "bluekai.com", "demdex.net", "krxd.net", "agkn.com", "rlcdn.com",
    "mathtag.com", "adsrvr.com", "bidswitch.net", "sharethrough.com",
    "teads.tv", "spotxchange.com", "yieldlab.net", "lijit.com",
    "3lift.com", "33across.com", "triplelift.com", "indexww.com",
    "tapad.com", "adsymptotic.com", "crwdcntrl.net", "narrative.io",
    "branch.io", "appsflyer.com", "adjust.com", "kochava.com",
    "newrelic.com", "nr-data.net", "sentry-cdn.com", "bugsnag.com",
    "mixpanel.com", "amplitude.com", "segment.io", "segment.com",
    "heap.io", "keen.io", "statcounter.com", "histats.com",
    "liveinternet.ru", "mc.yandex.ru", "top-fwz1.mail.ru", "ad.mail.ru",
    "an.yandex.ru", "adriver.ru", "adfox.ru", "banners.adfox.ru",
    "vk.com/rtrg", "top100.rambler.ru", "counter.rambler.ru",
    "contextweb.com", "sovrn.com", "gumgum.com", "districtm.io",
    "adroll.com", "perfectaudience.com", "retargeter.com",
    "bing.com/bat.js", "clarity.ms", "yandex-team.ru",
]

COSMETIC_CSS = """
marquee { animation: none !important; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(120,130,140,.45); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(120,130,140,.7); }
img[width="1"][height="1"], img[width="0"][height="0"] { display: none !important; }
"""

READER_CSS = """
body { background: #faf9f4 !important; color: #23262b !important; }
article, main, [role="main"] { max-width: 46rem !important; margin: 0 auto !important;
  font-family: Georgia, 'Noto Serif', serif !important; font-size: 19px !important;
  line-height: 1.7 !important; }
h1, h2, h3 { line-height: 1.25 !important; }
img { max-width: 100% !important; height: auto !important; }
aside, nav, footer, header, .advert, .ads, .sidebar, .newsletter, .cookie-banner { display: none !important; }
"""

DARK_CSS = """
html { filter: invert(1) hue-rotate(180deg) !important; background: #111 !important; }
img, video, picture, canvas, svg, iframe { filter: invert(1) hue-rotate(180deg) !important; }
"""

SEPIA_CSS = """
html { filter: sepia(.32) saturate(.9) !important; background: #f4ecd8 !important; }
"""

GRAY_CSS = """
html { filter: grayscale(1) !important; }
"""

USER_STYLES = {
    "none": "",
    "dark": DARK_CSS,
    "sepia": SEPIA_CSS,
    "gray": GRAY_CSS,
}


class AdBlocker:
    def __init__(self, settings=None):
        self.settings = settings
        self.hosts_file = paths.data_root() / "blocklist.txt"
        self.hosts = set()
        self.load()

    def load(self):
        self.hosts = set()
        for domain in TRACKER_HOSTS:
            domain = domain.split("/")[0].strip().lower()
            if domain:
                self.hosts.add(domain)
        if self.hosts_file.is_file():
            try:
                for line in self.hosts_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip().lower()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    domain = parts[-1]
                    if domain in ("localhost", "localhost.localdomain", "0.0.0.0"):
                        continue
                    domain = domain.lstrip(".")
                    if domain and "." in domain:
                        self.hosts.add(domain)
            except OSError:
                pass

    def count(self):
        return len(self.hosts)

    def is_request_third_party(self, source_url, target_url):
        try:
            from urllib.parse import urlparse

            source_host = (urlparse(source_url).hostname or "").lower()
            target_host = (urlparse(target_url).hostname or "").lower()
        except ValueError:
            return False
        if not source_host or not target_host:
            return False
        if source_host == target_host:
            return False
        return not self.is_tracker(source_host) and self.is_tracker(target_host)

    def is_tracker(self, host):
        host = (host or "").lower().strip(".")
        if not host:
            return False
        parts = host.split(".")
        for index in range(len(parts) - 1):
            candidate = ".".join(parts[index:])
            if candidate in self.hosts:
                return True
        return False

    def blocklist_for_webkit(self, limit=4000):
        entries = sorted(self.hosts)[:limit]
        return entries

    def update_from_url(self, url):
        target = paths.data_root() / "blocklist.download"
        script = paths.scripts_dir() / "update-blocklist.sh"
        if script.is_file():
            try:
                proc = subprocess.run(
                    [str(script)],
                    capture_output=True,
                    timeout=180,
                    text=True,
                    env={**os.environ, "BLOCKLIST_URL": url, "BLOCKLIST_OUT": str(self.hosts_file)},
                )
                if proc.returncode == 0 and self.hosts_file.is_file():
                    self.load()
                    return True, proc.stdout.strip()
                return False, proc.stderr.strip()
            except (OSError, subprocess.SubprocessError) as exc:
                return False, str(exc)
        return self._download_hosts(url)

    def _download_hosts(self, url):
        out = paths.data_root() / "blocklist.download"
        try:
            proc = subprocess.run(
                ["python3", "-c", "import sys,urllib.request;urllib.request.urlretrieve(sys.argv[1],sys.argv[2])", url, str(out)],
                capture_output=True,
                timeout=180,
            )
            if proc.returncode == 0 and out.is_file():
                shutil.move(str(out), str(self.hosts_file))
                self.load()
                return True, f"{self.count()} domains"
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)
        return False, "download failed"


def check_internet(timeout=2.0):
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=timeout).close()
        return True
    except OSError:
        pass
    try:
        socket.gethostbyname("duckduckgo.com")
        return True
    except OSError:
        return False


def generate_hosts():
    blocker = AdBlocker()
    lines = ["# NoLags Browser ad block host list", "127.0.0.1 localhost"]
    for domain in sorted(blocker.hosts):
        if "/" in domain:
            continue
        lines.append(f"0.0.0.0 {domain}")
    return "\n".join(lines) + "\n"


def json_dump_safe(data):
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"
