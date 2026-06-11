"""Generate INT Zone Studio branding assets from the master logo."""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "branding" / "logo-source.png"
BRANDING = REPO / "docs" / "branding"
ICONS = REPO / "desktop" / "studio" / "src-tauri" / "icons"
PUBLIC = REPO / "desktop" / "studio" / "public"


def ensure_source() -> Image.Image:
    if not SOURCE.exists():
        fallback = Path(
            r"C:\Users\Administrator\.cursor\projects"
            r"\c-Users-Administrator-OneDrive-Desktop-Strtup\assets"
            r"\c__Users_Administrator_AppData_Roaming_Cursor_User_workspaceStorage"
            r"_de7f2ea08d052773a64a2c9489a9ee08_images_ChatGPT_Image_Jun_11__2026__"
            r"04_01_39_PM-07bbb74e-bd04-43b7-b2df-60063a1232d7.png"
        )
        if fallback.exists():
            BRANDING.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fallback, SOURCE)
        else:
            raise FileNotFoundError(
                "Place master logo at docs/branding/logo-source.png"
            )
    return Image.open(SOURCE).convert("RGBA")


def crop_icon_mark(img: Image.Image) -> Image.Image:
    """Square crop around the iNT mark (upper graphic)."""
    w, h = img.size
    top = int(h * 0.04)
    bottom = int(h * 0.52)
    region = img.crop((0, top, w, bottom))
    rw, rh = region.size
    side = min(rw, rh)
    left = (rw - side) // 2
    upper = (rh - side) // 2
    return region.crop((left, upper, left + side, upper + side))


def save_png(path: Path, image: Image.Image, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resized = image.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(path, format="PNG", optimize=True)


def save_ico(path: Path, image: Image.Image, sizes: tuple[int, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [image.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    frames[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )


def save_icns(path: Path, image: Image.Image) -> None:
    """Minimal ICNS (PNG-in-icns) for Tauri bundle metadata."""
    png_sizes = (16, 32, 64, 128, 256, 512, 1024)
    entries: list[tuple[bytes, int, int]] = []
    type_map = {
        16: b"icp4",
        32: b"icp5",
        64: b"icp6",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
        1024: b"ic10",
    }
    for size in png_sizes:
        frame = image.resize((size, size), Image.Resampling.LANCZOS)
        import io

        buf = io.BytesIO()
        frame.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        entries.append((type_map[size], size, data))

    body = bytearray()
    for ostype, _size, data in entries:
        chunk = ostype + struct.pack(">I", len(data) + 8) + data
        body.extend(chunk)

    header = struct.pack(">4sI", b"icns", 8 + len(body))
    path.write_bytes(header + body)


def main() -> None:
    master = ensure_source()
    BRANDING.mkdir(parents=True, exist_ok=True)
    master.save(BRANDING / "logo-full.png", optimize=True)
    master.save(BRANDING / "logo-banner.png", optimize=True)

    mark = crop_icon_mark(master)
    save_png(ICONS / "32x32.png", mark, 32)
    save_png(ICONS / "128x128.png", mark, 128)
    save_png(ICONS / "128x128@2x.png", mark, 256)
    save_png(ICONS / "icon.png", mark, 512)
    save_ico(ICONS / "icon.ico", mark, (16, 24, 32, 48, 64, 128, 256))
    save_icns(ICONS / "icon.icns", mark)

    save_png(PUBLIC / "logo.png", mark, 256)
    save_png(PUBLIC / "favicon.png", mark, 32)

    # GitHub social preview (1280x640)
    banner = Image.new("RGBA", (1280, 640), (8, 12, 20, 255))
    logo_w = 420
    logo_h = int(master.height * (logo_w / master.width))
    scaled = master.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    x = (1280 - logo_w) // 2
    y = (640 - logo_h) // 2 - 20
    banner.paste(scaled, (x, y), scaled)
    banner.save(BRANDING / "social-preview.png", optimize=True)

    print("Brand assets written:")
    print(f"  {BRANDING}")
    print(f"  {ICONS}")
    print(f"  {PUBLIC / 'logo.png'}")


if __name__ == "__main__":
    main()
