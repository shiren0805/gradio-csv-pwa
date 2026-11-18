"""產生 PWA 所需圖示（需要 Pillow、numpy；安裝 gradio 時已一併安裝）
用法：python tools/make_icons.py
想換成自己的 Logo，直接用同名 PNG 覆蓋 pwa/icons/ 內的檔案即可。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "pwa" / "icons"
OUT.mkdir(parents=True, exist_ok=True)
S = 1024  # 以大圖繪製再縮小，邊緣較平滑


def gradient_bg() -> Image.Image:
    """靛藍 → 天藍 的對角漸層"""
    c1 = np.array([79, 70, 229], dtype=float)   # #4f46e5
    c2 = np.array([14, 165, 233], dtype=float)  # #0ea5e9
    y, x = np.mgrid[0:S, 0:S]
    t = ((x + y) / (2 * (S - 1)))[..., None]
    arr = (c1 * (1 - t) + c2 * t).astype("uint8")
    return Image.fromarray(arr, "RGB").convert("RGBA")


def draw_glyph(img: Image.Image) -> None:
    """白色長條圖圖示，全部落在中央 56% 安全區內（maskable 也不會被裁到）"""
    d = ImageDraw.Draw(img)
    bar_w, gap = int(0.12 * S), int(0.06 * S)
    heights = [0.18, 0.30, 0.44]
    base_y = int(0.74 * S)
    x = int(0.26 * S)
    for h in heights:
        d.rounded_rectangle(
            [x, base_y - int(h * S), x + bar_w, base_y],
            radius=int(0.03 * S),
            fill=(255, 255, 255, 255),
        )
        x += bar_w + gap
    # 基準線
    d.rounded_rectangle(
        [int(0.22 * S), base_y + int(0.03 * S), int(0.78 * S), base_y + int(0.05 * S)],
        radius=int(0.01 * S),
        fill=(255, 255, 255, 200),
    )


def rounded(img: Image.Image, radius_ratio: float = 0.22) -> Image.Image:
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * radius_ratio), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


base = gradient_bg()
draw_glyph(base)

rounded(base).resize((192, 192), Image.LANCZOS).save(OUT / "icon-192.png")
rounded(base).resize((512, 512), Image.LANCZOS).save(OUT / "icon-512.png")
base.resize((512, 512), Image.LANCZOS).save(OUT / "maskable-512.png")          # 滿版，供 maskable
base.convert("RGB").resize((180, 180), Image.LANCZOS).save(OUT / "apple-touch-icon.png")  # iOS 自行裁圓角
rounded(base).resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png")
print("icons ->", OUT)
