#!/usr/bin/env python3
"""
Generate the PWA icon set for HostPro OS.

By default this draws the white "hp" monogram on black. If you already have a
clean logo PNG (there is one inside hostpro-os-app.zip), pass it and it will be
centred on the black field instead, which will look better than the drawn text:

    python3 make-icons.py                  # draw the monogram
    python3 make-icons.py path/to/logo.png # use an existing logo

Writes into public/icons/.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "icons")
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)

# any-purpose icons can fill the square; maskable icons must keep their content
# inside the middle 80% or Android will crop the monogram when it applies a
# circle or squircle mask.
SIZES = [
    ("icon-180.png", 180, 0.62),   # apple-touch-icon
    ("icon-192.png", 192, 0.62),
    ("icon-512.png", 512, 0.62),
    ("icon-maskable-512.png", 512, 0.44),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def load_font(px):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def draw_monogram(size, content_ratio):
    img = Image.new("RGBA", (size, size), BLACK)
    draw = ImageDraw.Draw(img)
    font = load_font(int(size * content_ratio))
    text = "hp"
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(
        ((size - w) / 2 - box[0], (size - h) / 2 - box[1]),
        text,
        font=font,
        fill=WHITE,
    )
    return img


def place_logo(logo, size, content_ratio):
    img = Image.new("RGBA", (size, size), BLACK)
    target = int(size * content_ratio * 1.35)
    scaled = logo.copy()
    scaled.thumbnail((target, target), Image.LANCZOS)
    img.paste(
        scaled,
        ((size - scaled.width) // 2, (size - scaled.height) // 2),
        scaled if scaled.mode == "RGBA" else None,
    )
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    logo = None
    if len(sys.argv) > 1:
        logo = Image.open(sys.argv[1]).convert("RGBA")
        print("Using logo:", sys.argv[1])
    else:
        print("Drawing the hp monogram (pass a logo path to use a real logo).")

    for name, size, ratio in SIZES:
        img = place_logo(logo, size, ratio) if logo else draw_monogram(size, ratio)
        path = os.path.join(OUT, name)
        img.convert("RGB").save(path, "PNG", optimize=True)
        print("  wrote", name, f"{size}x{size}")


if __name__ == "__main__":
    main()
