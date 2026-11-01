from __future__ import annotations

import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from argus_netmon.state import LinkState

# Distinct solid colors for tray (64x64)
COLORS = {
    LinkState.UNKNOWN: (128, 128, 128, 255),
    LinkState.NO_LAN: (180, 40, 40, 255),
    LinkState.DOWN: (220, 80, 20, 255),
    LinkState.WHITELIST: (220, 160, 20, 255),
    LinkState.RU_ZONE: (200, 120, 40, 255),
    LinkState.OK: (40, 160, 70, 255),
    LinkState.DEGRADED: (40, 120, 200, 255),
}

# Short marks drawn on the icon — Xorg tray has no hover tooltip.
BADGES = {
    LinkState.UNKNOWN: "?",
    LinkState.NO_LAN: "LAN",
    LinkState.DOWN: "DN",
    LinkState.WHITELIST: "WL",
    LinkState.RU_ZONE: "RU",
    LinkState.OK: "OK",
    LinkState.DEGRADED: "3G",
}


@lru_cache(maxsize=4)
def _font(px: int) -> ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def make_icon(state: LinkState, size: int = 64) -> Image.Image:
    color = COLORS.get(state, COLORS[LinkState.UNKNOWN])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 10
    draw.ellipse(
        [margin, margin, size - margin - 1, size - margin - 1],
        fill=color,
    )

    badge = BADGES.get(state, "?")
    font = _font(max(14, size // (2 if len(badge) <= 2 else 3)))
    bbox = draw.textbbox((0, 0), badge, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    # outline for contrast
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        draw.text((x + dx, y + dy), badge, font=font, fill=(0, 0, 0, 200))
    draw.text((x, y), badge, font=font, fill=(255, 255, 255, 255))
    return img
