"""Invented test pictures for the cover picture tests (printed bulletin PR 3): made here with Pillow,
never a real photo."""
import struct
from io import BytesIO

from PIL import Image, ImageCms

RED, GREEN, BLUE = (220, 30, 30), (30, 160, 60), (30, 60, 220)


def picture(size=(400, 300), fmt="JPEG", color=GREEN, mode="RGB", **save) -> bytes:
    """A plain picture of one color."""
    out = BytesIO()
    Image.new(mode, size, color).save(out, fmt, **save)
    return out.getvalue()


def stripes(size, colors, *, horizontal=True, fmt="JPEG", **save) -> bytes:
    """Equal stripes of `colors`, top to bottom (or left to right when not horizontal)."""
    img = Image.new("RGB", size)
    n = len(colors)
    for i, color in enumerate(colors):
        if horizontal:
            img.paste(color, (0, size[1] * i // n, size[0], size[1] * (i + 1) // n))
        else:
            img.paste(color, (size[0] * i // n, 0, size[0] * (i + 1) // n, size[1]))
    out = BytesIO()
    img.save(out, fmt, **save)
    return out.getvalue()


def opened(data: bytes) -> Image.Image:
    img = Image.open(BytesIO(data))
    img.load()
    return img


def near(pixel, color, tolerance=40) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


def swapped_profile() -> bytes:
    """An invented color profile: sRGB with its red and blue primaries swapped, so a conversion to sRGB
    shows (a green of (30, 160, 60) becomes about (60, 160, 30))."""
    data = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    count = struct.unpack(">I", data[128:132])[0]
    at = {bytes(data[132 + 12 * i:136 + 12 * i]): 132 + 12 * i for i in range(count)}
    red, blue = at[b"rXYZ"], at[b"bXYZ"]
    data[red + 4:red + 12], data[blue + 4:blue + 12] = data[blue + 4:blue + 12], data[red + 4:red + 12]
    return bytes(data)


def repeated_scan(data: bytes, times: int) -> bytes:
    """A progressive JPEG with its last scan (and the Huffman table before it) repeated `times` more times:
    libjpeg decodes every repeat over the whole picture (the build review's C1)."""
    end = data.rindex(b"\xff\xd9")
    scan = data.rindex(b"\xff\xda", 0, end)
    table = data.rfind(b"\xff\xc4", 0, scan)
    start = table if table > data.rfind(b"\xff\xda", 0, scan) else scan
    return data[:end] + data[start:end] * times + data[end:]
