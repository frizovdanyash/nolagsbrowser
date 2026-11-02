#!/usr/bin/env python3
import base64
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MASCOT = ASSETS / "mascot"
ICONS = ASSETS / "icons"
BRAND = ASSETS / "brand"
SOURCE = MASCOT / "mascot_source.png"

SIZES = [16, 22, 24, 32, 48, 64, 96, 128, 192, 256, 512]

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#e9f7f3"/>
    </linearGradient>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2fb7a4"/>
      <stop offset="1" stop-color="#1d8d80"/>
    </linearGradient>
    <clipPath id="clip">
      <rect x="24" y="24" width="464" height="464" rx="112"/>
    </clipPath>
  </defs>
  <rect x="24" y="24" width="464" height="464" rx="112" fill="url(#bg)"/>
  <g clip-path="url(#clip)">
    <image x="56" y="30" width="400" height="480" preserveAspectRatio="xMidYMin meet" xlink:href="data:image/png;base64,__HEAD__"/>
  </g>
  <rect x="24" y="24" width="464" height="464" rx="112" fill="none" stroke="url(#ring)" stroke-width="14"/>
</svg>
"""

BANNER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1280 400" width="1280" height="400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101a20"/>
      <stop offset="0.55" stop-color="#16242b"/>
      <stop offset="1" stop-color="#0f2b2a"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.78" cy="0.35" r="0.6">
      <stop offset="0" stop-color="#2fb7a4" stop-opacity="0.42"/>
      <stop offset="1" stop-color="#2fb7a4" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="round"><rect x="896" y="28" width="328" height="344" rx="82"/></clipPath>
  </defs>
  <rect width="1280" height="400" fill="url(#bg)"/>
  <rect width="1280" height="400" fill="url(#glow)"/>
  <g clip-path="url(#round)">
    <rect x="896" y="28" width="328" height="344" fill="#f4f1ea"/>
    <image x="912" y="22" width="296" height="356" preserveAspectRatio="xMidYMin meet" xlink:href="data:image/png;base64,__HEAD__"/>
  </g>
  <rect x="896" y="28" width="328" height="344" rx="82" fill="none" stroke="#2fb7a4" stroke-width="9"/>
  <g font-family="DejaVu Sans, Inter, sans-serif">
    <text x="80" y="150" font-size="64" font-weight="bold" fill="#f6f8f7" letter-spacing="0.5">NoLags Browser</text>
    <text x="84" y="200" font-size="25" fill="#8fd8cc">лёгкий браузер на WebKitGTK для Debian и не только</text>
    <g font-size="21" fill="#c9d6d8">
      <rect x="84" y="232" width="176" height="42" rx="21" fill="#1c3038"/>
      <text x="108" y="260">низкое ОЗУ</text>
      <rect x="272" y="232" width="190" height="42" rx="21" fill="#1c3038"/>
      <text x="296" y="260">сон вкладок</text>
      <rect x="474" y="232" width="242" height="42" rx="21" fill="#1c3038"/>
      <text x="498" y="260">блокировка трекеров</text>
    </g>
    <text x="84" y="330" font-size="21" fill="#6f8a8f">github.com/frizovdanyash/nolagsbrowser</text>
  </g>
</svg>
"""


def run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print("FAILED:", " ".join(str(part) for part in cmd))
        print(result.stderr.strip()[:800])
        sys.exit(1)
    return result


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def main():
    if not SOURCE.is_file():
        print("missing mascot source")
        return 1
    if not shutil.which("convert"):
        print("imagemagick required")
        return 1
    MASCOT.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    BRAND.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/nolags-assets")
    work.mkdir(parents=True, exist_ok=True)

    run(["convert", str(SOURCE), "-resize", "1024x1024", "-bordercolor", "#f4f1ea", "-border", "1", "-fuzz", "7%", "-trim", "+repage", str(work / "trimmed.png")])
    trimmed = work / "trimmed.png"
    run(["convert", str(trimmed), "-resize", "900x900", str(MASCOT / "mascot.png")])

    width = int(run(["identify", "-format", "%w", str(trimmed)]).stdout.strip())
    height = int(run(["identify", "-format", "%h", str(trimmed)]).stdout.strip())
    head_w = int(width * 0.58)
    head_h = int(height * 0.56)
    head_x = int((width - head_w) / 2)
    run(["convert", str(trimmed), "-crop", f"{head_w}x{head_h}+{head_x}+0", "+repage", str(work / "head.png")])
    head = work / "head.png"
    run(["convert", str(head), "-resize", "600x600", str(work / "head_big.png")])
    head_big = work / "head_big.png"

    run(["convert", str(head_big), "-background", "none", "-resize", "520x520", str(MASCOT / "mascot_peek.png")])
    run([
        "convert", str(head_big), "-modulate", "104,112", "-background", "none",
        "-resize", "520x520", str(MASCOT / "mascot_happy.png"),
    ])
    run([
        "convert", str(head_big), "-colorspace", "Gray", "-modulate", "92,60", "-background", "none",
        "-resize", "520x520", "-fill", "#2fb7a4", "-font", "DejaVu-Sans-Bold", "-pointsize", "150",
        "-annotate", "+190+120", "z", "-pointsize", "110", "-annotate", "+280+60", "z",
        str(MASCOT / "mascot_sleep.png"),
    ])

    svg = ICON_SVG.replace("__HEAD__", b64(head_big))
    (ICONS / "nolagsbrowser.svg").write_text(svg, encoding="utf-8")
    run(["rsvg-convert", "-w", "1024", "-h", "1024", str(ICONS / "nolagsbrowser.svg"), "-o", str(work / "icon1024.png")])
    for size in SIZES:
        target = ROOT / "data" / "icons" / f"{size}x{size}" / "apps"
        target.mkdir(parents=True, exist_ok=True)
        run(["convert", str(work / "icon1024.png"), "-resize", f"{size}x{size}", str(target / "nolagsbrowser.png")])
    scalable = ROOT / "data" / "icons" / "scalable" / "apps"
    scalable.mkdir(parents=True, exist_ok=True)
    shutil.copy(ICONS / "nolagsbrowser.svg", scalable / "nolagsbrowser.svg")
    run(["convert", str(work / "icon1024.png"), "-resize", "256x256", str(ASSETS / "icon.png")])
    run(["convert", str(work / "icon1024.png"), "-resize", "512x512", str(BRAND / "icon-512.png")])

    banner = BANNER_SVG.replace("__HEAD__", b64(head_big))
    (BRAND / "banner.svg").write_text(banner, encoding="utf-8")
    run(["rsvg-convert", "-w", "1280", "-h", "400", str(BRAND / "banner.svg"), "-o", str(BRAND / "banner.png")])

    print("assets done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
