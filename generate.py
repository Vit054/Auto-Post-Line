"""Generate today's morning greeting image.

1. Pick the day + Thai lucky color theme.
2. Ask DeepSeek for a unique English greeting (falls back to a local pool).
3. Fetch a flower photo from Pollinations (falls back to a gradient).
4. Compose the greeting onto the image with Pillow.
5. Save images/<date>.jpg, append to history.json, prune old images.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import today

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
FONTS = ROOT / "assets" / "fonts"
HISTORY = ROOT / "history.json"
SIZE = 1080
KEEP_IMAGES = 14

FONT_SOURCES = {
    "GreatVibes-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/greatvibes/GreatVibes-Regular.ttf",
    "Poppins-SemiBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-SemiBold.ttf",
    "Poppins-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf",
}

FALLBACK_GREETINGS = [
    "Have a bright and beautiful {day}!",
    "Good morning! Make today truly wonderful.",
    "Wishing you a peaceful and happy {day}.",
    "Rise and shine — {day} is all yours!",
    "May your {day} bloom with joy and calm.",
    "Good morning! Sending you warm smiles today.",
    "A fresh {day}, a fresh start. Enjoy it!",
    "Hello {day}! Stay positive and stay strong.",
    "Sip your coffee and own this {day}.",
    "New morning, new blessings. Happy {day}!",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    FONTS.mkdir(parents=True, exist_ok=True)
    path = FONTS / name
    if not path.exists() and name in FONT_SOURCES:
        try:
            r = requests.get(FONT_SOURCES[name], timeout=30)
            r.raise_for_status()
            path.write_bytes(r.content)
        except Exception as e:  # noqa: BLE001
            print(f"font download failed ({name}): {e}")
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:  # noqa: BLE001
        for cand in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ):
            if os.path.exists(cand):
                return ImageFont.truetype(cand, size)
        return ImageFont.load_default()


def load_history() -> list[dict]:
    if HISTORY.exists():
        try:
            return json.loads(HISTORY.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            return []
    return []


def save_history(items: list[dict]) -> None:
    HISTORY.write_text(json.dumps(items[-90:], ensure_ascii=False, indent=2), "utf-8")


def prune_old(keep: int = KEEP_IMAGES) -> None:
    files = sorted(IMAGES.glob("*.jpg"))
    for f in files[:-keep]:
        try:
            f.unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
def deepseek_greeting(day: str, avoid: list[str]) -> str | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("DEEPSEEK_API_KEY not set; using fallback greeting.")
        return None
    avoid_txt = "\n".join(f"- {a}" for a in avoid[-25:]) or "(none yet)"
    prompt = (
        f"Write ONE short, warm good-morning greeting in English for {day}. "
        f"Rules: 6 to 14 words, friendly and uplifting, suitable to fit {day}, "
        f"no hashtags, no emoji, no surrounding quotation marks. "
        f"It MUST be clearly different from these past greetings:\n{avoid_txt}\n"
        f"Reply with the greeting text only."
    )
    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.3,
                "max_tokens": 60,
            },
            timeout=40,
        )
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"].strip()
        txt = txt.strip('"').strip().split("\n")[0].strip()
        return txt or None
    except Exception as e:  # noqa: BLE001
        print(f"deepseek failed: {e}")
        return None


def pollinations_image(theme: dict, seed: int) -> Image.Image | None:
    """Optional real AI photo. Anonymous tier is rate-gated (HTTP 402), so this
    only runs when POLLINATIONS_TOKEN is set; otherwise we use floral_art()."""
    token = os.environ.get("POLLINATIONS_TOKEN")
    if not token:
        return None
    prompt = (
        f"professional photograph of {theme['flowers']}, fresh morning dew, "
        f"soft natural sunlight, shallow depth of field, beautiful bokeh, "
        f"on a rustic light wooden table, bright and airy, high detail, no text"
    )
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(prompt)
        + f"?width={SIZE}&height={SIZE}&seed={seed}&nologo=true&model=flux&token={token}"
    )
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception as e:  # noqa: BLE001
            print(f"pollinations attempt {attempt + 1} failed: {e}")
    return None


def _draw_flower(base, cx, cy, r, petals, petal_rgb, center_rgb, rng):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    plen, pw = r, r * 0.55
    for k in range(petals):
        ang = 360 * k / petals + rng.uniform(-7, 7)
        side = int(plen * 2)
        tile = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.ellipse([side / 2 - pw / 2, 3, side / 2 + pw / 2, plen], fill=petal_rgb + (235,))
        tile = tile.rotate(-ang, center=(side / 2, side / 2), resample=Image.BICUBIC)
        layer.alpha_composite(tile, (int(cx - side / 2), int(cy - side / 2)))
    base.alpha_composite(layer)
    cr = r * 0.32
    ImageDraw.Draw(base).ellipse(
        [cx - cr, cy - cr, cx + cr, cy + cr], fill=center_rgb + (255,)
    )


def floral_art(theme: dict, seed: int) -> Image.Image:
    """Reliable, key-free stylized floral scene themed to the day's lucky color."""
    rng = random.Random(seed)
    color, accent = hex_rgb(theme["color"]), hex_rgb(theme["accent"])
    light = tuple(int(c + (255 - c) * 0.78) for c in accent)

    bg = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(bg)
    for y in range(SIZE):
        t = y / SIZE
        col = tuple(int(light[i] + (252 - light[i]) * t) for i in range(3))
        d.line([(0, y), (SIZE, y)], fill=col)
    base = bg.convert("RGBA")

    bok = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for _ in range(20):
        rr = rng.randint(50, 150)
        x, y = rng.randint(0, SIZE), rng.randint(0, int(SIZE * 0.72))
        bd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=accent + (rng.randint(18, 55),))
    base.alpha_composite(bok.filter(ImageFilter.GaussianBlur(10)))

    center_rgb = tuple(int(c * 0.7) for c in color)
    for _ in range(rng.randint(5, 7)):
        cx = rng.randint(130, SIZE - 130)
        cy = rng.randint(120, int(SIZE * 0.48))
        r = rng.randint(75, 135)
        petals = rng.choice([5, 6, 8])
        petal_rgb = accent if rng.random() < 0.5 else color
        _draw_flower(base, cx, cy, r, petals, petal_rgb, center_rgb, rng)
    return base.convert("RGB")


# --------------------------------------------------------------------------- #
# compose
# --------------------------------------------------------------------------- #
def _crop_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def _size(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


def _center(draw, y, text, font, fill, shadow=(0, 0, 0, 170)):
    w, _ = _size(draw, text, font)
    x = (SIZE - w) // 2
    draw.text((x + 3, y + 3), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if _size(draw, t, font)[0] <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def compose(img: Image.Image, day: str, greeting: str, theme: dict) -> Image.Image:
    img = _crop_square(img).resize((SIZE, SIZE)).convert("RGBA")

    # darken the lower half so text stays readable on any photo
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    start = int(SIZE * 0.42)
    for y in range(start, SIZE):
        a = int(190 * (y - start) / (SIZE - start))
        od.line([(0, y), (SIZE, y)], fill=(0, 0, 0, min(a, 190)))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    f_eye = load_font("Poppins-SemiBold.ttf", 38)
    f_day = load_font("GreatVibes-Regular.ttf", 168)
    f_body = load_font("Poppins-Regular.ttf", 46)

    accent = hex_rgb(theme["accent"])
    eyebrow = "G O O D   M O R N I N G"
    margin = 95
    lines = _wrap(draw, greeting, f_body, SIZE - 2 * margin)

    eye_h = _size(draw, eyebrow, f_eye)[1]
    day_h = _size(draw, day, f_day)[1]
    body_lh = _size(draw, "Ag", f_body)[1] + 16
    block = eye_h + 26 + day_h + 34 + len(lines) * body_lh
    y = SIZE - block - 86

    _center(draw, y, eyebrow, f_eye, accent + (255,))
    y += eye_h + 26
    _center(draw, y, day, f_day, (255, 255, 255, 255))
    y += day_h + 4
    # accent underline under the day
    uw = 150
    draw.line([((SIZE - uw) // 2, y + 14), ((SIZE + uw) // 2, y + 14)],
              fill=accent + (255,), width=5)
    y += 30
    for ln in lines:
        _center(draw, y, ln, f_body, (255, 255, 255, 255))
        y += body_lh

    return img


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    now, theme = today()
    date = now.strftime("%Y-%m-%d")
    day = theme["day"]
    seed = int(hashlib.sha256(date.encode()).hexdigest(), 16) % 1_000_000

    history = load_history()
    avoid = [h["text"] for h in history]

    greeting = deepseek_greeting(day, avoid)
    if not greeting:
        random.seed(seed)
        pool = [g.format(day=day) for g in FALLBACK_GREETINGS]
        fresh = [g for g in pool if g not in avoid] or pool
        greeting = random.choice(fresh)

    img = pollinations_image(theme, seed) or floral_art(theme, seed)
    final = compose(img, day, greeting, theme).convert("RGB")

    IMAGES.mkdir(exist_ok=True)
    out = IMAGES / f"{date}.jpg"
    q = 86
    final.save(out, "JPEG", quality=q, optimize=True)
    while out.stat().st_size > 1_000_000 and q > 50:
        q -= 8
        final.save(out, "JPEG", quality=q, optimize=True)

    history.append({"date": date, "day": day, "text": greeting})
    save_history(history)
    prune_old()

    print(f"Day      : {day}")
    print(f"Greeting : {greeting}")
    print(f"Saved    : {out} ({out.stat().st_size // 1024} KB)")

    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a", encoding="utf-8") as f:
            f.write(f"date={date}\n")
            f.write(f"image_path=images/{date}.jpg\n")


if __name__ == "__main__":
    main()
