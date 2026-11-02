#!/usr/bin/env python3
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

TOLERANCE = 22
FEATHER = 1.2


def edge_regions(img, tolerance):
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    h, w, _ = arr.shape
    flat = arr.reshape(-1, 3)
    corners = np.array([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]], dtype=np.int16)
    base = np.median(corners, axis=0).astype(np.int16)
    for _ in range(3):
        distance = np.abs(flat - base).max(axis=1)
        close = flat[distance <= tolerance]
        if len(close) == 0:
            break
        base = close.mean(axis=0).astype(np.int16)
    distance = np.abs(flat - base).max(axis=1).reshape(h, w)
    similar = distance <= tolerance
    mask = np.zeros((h, w), dtype=bool)
    mask[0, :] = similar[0, :]
    mask[-1, :] = similar[-1, :]
    mask[:, 0] |= similar[:, 0]
    mask[:, -1] |= similar[:, -1]
    grown = True
    while grown:
        grown = False
        for shift, axis, sl in (
            (1, 0, (slice(1, None), slice(None))),
            (-1, 0, (slice(None, -1), slice(None))),
            (1, 1, (slice(None), slice(1, None))),
            (-1, 1, (slice(None), slice(None, -1))),
        ):
            shifted = np.roll(mask, shift, axis=axis)
            candidate = shifted & similar
            target = mask[sl[0], sl[1]]
            cand = candidate[sl[0], sl[1]]
            new = cand & ~target
            if new.any():
                target |= new
                mask[sl[0], sl[1]] = target
                grown = True
    return mask


def near_background(img, tolerance):
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    corners = np.array(
        [
            arr[0, 0],
            arr[0, -1],
            arr[-1, 0],
            arr[-1, -1],
        ]
    )
    base = np.median(corners, axis=0).astype(np.int16)
    distance = np.abs(arr - base).max(axis=2)
    return distance <= tolerance


def refine_edges(img, alpha):
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape
    alpha = alpha.copy()
    inside = alpha > 0.5
    band = np.zeros((h, w), dtype=bool)
    edge = inside & ~np.roll(inside, 2, axis=0)
    edge |= inside & ~np.roll(inside, -2, axis=0)
    edge |= inside & ~np.roll(inside, 2, axis=1)
    edge |= inside & ~np.roll(inside, -2, axis=1)
    edge |= inside & ~np.roll(inside, 1, axis=0)
    edge |= inside & ~np.roll(inside, -1, axis=0)
    edge |= inside & ~np.roll(inside, 1, axis=1)
    edge |= inside & ~np.roll(inside, -1, axis=1)
    band = edge
    dark = arr.max(axis=2) < 110
    alpha[band & dark] = 0.0
    return alpha


def main():
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    img = Image.open(source).convert("RGB")
    w, h = img.size

    background = edge_regions(img, TOLERANCE)
    alpha = np.where(background, 0.0, 1.0)

    alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), mode="L")
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(3))
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(FEATHER))
    alpha = np.asarray(alpha_img).astype(np.float32) / 255.0
    alpha = refine_edges(img, alpha)

    arr = np.asarray(img).astype(np.float32)
    out = np.dstack([arr, alpha * 255.0]).astype(np.uint8)
    result = Image.fromarray(out, mode="RGBA")

    bbox = result.getbbox()
    if bbox:
        result = result.crop((max(0, bbox[0] - 4), max(0, bbox[1] - 4), min(w, bbox[2] + 4), min(h, bbox[3] + 4)))

    result.save(target, "PNG", optimize=True)
    print(f"{target} {result.size[0]}x{result.size[1]}")


if __name__ == "__main__":
    main()
