"""The printed bulletin's cover picture (printed bulletin spec, "Data model";
PR 3 planning answers 2-6), with Pillow (installed with reportlab).

- prepare(data): an upload made ready to store (POST /bulletin-images). It
  must be at most 10 MB, a JPEG or a PNG (planning answer 5: no HEIC; an
  iPhone's Safari sends a JPEG; a phone's multi-picture JPEG, which Pillow
  calls "MPO", is a JPEG) and at most 50 million pixels (24 million for a
  PNG, which is decoded whole, and for a progressive JPEG, which keeps every
  coefficient in memory whatever the scale it is decoded at; a JPEG of more
  than MAX_SCANS scans is refused before it is decoded, since each scan is a
  pass over the whole picture). It is turned upright (its EXIF
  orientation), its colors converted to sRGB when it carries a color
  profile (an iPhone's Display P3), a transparent part laid on white,
  scaled down to at most 1600 px on its long side (never up), and stored as
  a JPEG with no camera data (no EXIF, XMP, comment or other metadata, so
  no location, time or name) of at most
  MAX_STORED_BYTES (a lower quality, then a smaller size, until it fits).
  A JPEG is decoded at a reduced scale when it is much larger (draft mode),
  and a large PNG is reduced before anything else is done to it, so the
  memory one upload takes stays bounded; one upload is prepared at a time in
  the process (one worker thread), and another waits its turn up to
  BUSY_WAIT_SECONDS, then is a 429 (BUSY_MESSAGE). A started picture has
  PREPARE_SECONDS of the worker (checked between the file's reads while it is
  decoded, and between the steps), and the request waits TOTAL_WAIT_SECONDS
  in all: past either, a 429 (TOO_SLOW_MESSAGE). Anything else is a 422
  naming the field "image".
- cover(picture, lines, size): the cover's box as both printed files show it
  (planning answers 2-4): the picture scaled to fill `size` and trimmed
  evenly at the edges (a centered crop), in color, with a dark see-through
  band across its bottom holding `lines` (the reading and the date) in
  white, centered, shrunk together to fit the width. A JPEG; the PDF and the
  Word version place the same picture, so they look the same.
Pure: no database, FastAPI or rendering library (the band's font is the
Times Bold outline that reportlab ships).
"""
from __future__ import annotations

import functools
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as Waited
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

import reportlab
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from domain_errors import InvalidInput, RateLimited

MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # planning answer: at most 10 MB in
MAX_PIXELS = 50_000_000                      # a JPEG: more than any phone camera's 48 MP
MAX_PNG_PIXELS = 24_000_000                  # a PNG (a screenshot or a graphic), decoded whole
# A progressive JPEG: libjpeg keeps every DCT coefficient (2 bytes a pixel a component) whatever the scale it
# decodes at, so it takes as much memory as a PNG of its size (build review I1: 300-400 MB at 50 MP).
MAX_PROGRESSIVE_PIXELS = MAX_PNG_PIXELS
# A JPEG's scans (SOS markers), at most: each is a pass over every block of the picture (build review C1: a
# file of a few hundred KB repeating one scan a thousand times took 30 s). Pillow's progressive JPEG has 10
# (6 grey, 18 CMYK), a phone's baseline JPEG 1 (2 with its EXIF thumbnail), a two-picture MPO about 20.
MAX_SCANS = 64
MAX_SIDE = 1600                              # the stored picture's long side, at most
MAX_STORED_BYTES = 600_000                   # the stored JPEG, at most (plan review C3)
CONTENT_TYPE = "image/jpeg"                  # what is stored and served
FORMATS = ("JPEG", "MPO", "PNG")             # planning answer 5; MPO: a phone's multi-picture JPEG
OPENERS = ("JPEG", "PNG")                    # the only parsers tried (Pillow opens an MPO with JPEG's)
# The stored JPEG's long side and quality, tried in turn until it is at most MAX_STORED_BYTES.
ENCODINGS = ((1600, 85), (1600, 75), (1400, 70), (1200, 65), (1000, 60), (800, 60))
BUSY_WAIT_SECONDS = 10.0                     # how long an upload waits for the one before it
BUSY_RETRY_SECONDS = 5
PREPARE_SECONDS = 10.0                       # a started picture's time on the worker, at most
TOTAL_WAIT_SECONDS = 20.0                    # an upload's whole wait for its picture, at most
READ_BLOCK = 4096                            # the decoder reads the file in blocks this size (the time check)

TOO_LARGE_MESSAGE = "The picture is larger than 10 MB. Choose a smaller one."
NOT_A_PICTURE_MESSAGE = "Choose a JPEG or PNG picture."
TOO_MANY_PIXELS_MESSAGE = "The picture has too many pixels. Choose a smaller one."
BUSY_MESSAGE = "Another picture is being prepared. Try again in a few seconds."
TOO_SLOW_MESSAGE = "The picture took too long to prepare. Choose a smaller one."

# The band: black at this opacity, its text white (planning answer 2).
BAND_OPACITY = 0.55
# Times Bold's outline, as reportlab ships it (the PDF's standard Times-Bold has no file of its own).
FONT_FILE = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "_eb_____.pfb")

# EXIF orientation (a phone stores a portrait photo sideways): the turn that makes it upright.
ORIENTATION = 0x0112
TURNS = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180, 4: Image.Transpose.FLIP_TOP_BOTTOM,
         5: Image.Transpose.TRANSPOSE, 6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
         8: Image.Transpose.ROTATE_90}

# Pillow's own guard against a picture that claims more pixels than its file holds: it refuses one
# past twice this as it opens it (a 422 here). The process opens no other large picture.
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
# One upload is decoded and prepared at a time in the process (plan review C2), always on this one thread:
# uploads arriving together queue here instead of adding up, and the memory a picture took is reused by
# the next (the C allocator keeps freed memory per thread, so twenty threads taking turns would each keep
# their own).
_WORKER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bulletin-image")


@dataclass(frozen=True)
class Prepared:
    content: bytes          # the JPEG to store
    width: int
    height: int


def _invalid(message: str) -> InvalidInput:
    return InvalidInput(message, field="image")


class _TooSlow(Exception):
    """The picture's time on the worker is up (PREPARE_SECONDS)."""


def _too_slow() -> RateLimited:
    return RateLimited(TOO_SLOW_MESSAGE, retry_after_seconds=BUSY_RETRY_SECONDS)


class _Timed(BytesIO):
    """The upload's bytes, read by the decoder block by block; a read past the deadline stops the decode
    (libjpeg cannot be interrupted, but it asks for the next block between scans)."""

    def __init__(self, data: bytes, deadline: float):
        super().__init__(data)
        self.deadline = deadline

    def read(self, size: int | None = -1) -> bytes:
        _check(self.deadline)
        return super().read(size)


def _check(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise _TooSlow


def _target(width: int, height: int) -> tuple[int, int]:
    """The size `thumbnail` gives: the long side at most MAX_SIDE, the ratio kept."""
    scale = min(1.0, MAX_SIDE / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def _smaller(img: Image.Image) -> Image.Image:
    """The decoded picture at most MAX_SIDE on its long side, in a mode Pillow scales well. A large one is
    first reduced by a whole factor (box averaging into a new, small picture: no second copy at full size)."""
    if img.mode.startswith("I;16") or img.mode == "I":
        img = img.point(lambda v: v * (1 / 256)).convert("L")       # 16-bit grey: keep its tones (not clipped)
    elif img.mode == "P":
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif img.mode not in ("RGB", "RGBA", "L", "LA", "CMYK"):
        bands = img.getbands()
        img = img.convert("RGBA" if "A" in bands else "L" if len(bands) == 1 else "RGB")
    factor = max(img.size) // MAX_SIDE
    if factor >= 2:
        img = img.reduce(factor)
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return img


def _rgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    """RGB in sRGB: a transparent part laid on white; a color profile converted (kept as is if unreadable)."""
    if "A" in img.getbands():
        flat = Image.new("RGB", img.size, "white")
        flat.paste(img.convert("RGB"), mask=img.getchannel("A"))
        img = flat
    if icc and img.mode in ("RGB", "CMYK"):
        try:
            return ImageCms.profileToProfile(img, ImageCms.ImageCmsProfile(BytesIO(icc)),
                                             ImageCms.createProfile("sRGB"), outputMode="RGB")
        except (ImageCms.PyCMSError, OSError, ValueError):
            pass
    return img if img.mode == "RGB" else img.convert("RGB")


def _encoded(picture: Image.Image) -> tuple[bytes, int, int]:
    """The JPEG to store: the first of ENCODINGS of at most MAX_STORED_BYTES (the last one otherwise)."""
    for side, quality in ENCODINGS:
        img = picture
        if max(picture.size) > side:
            img = picture.copy()
            img.thumbnail((side, side), Image.Resampling.LANCZOS)
        img.info.clear()                                            # no comment, EXIF, XMP or profile written
        out = BytesIO()
        img.save(out, "JPEG", quality=quality, optimize=True)
        if out.tell() <= MAX_STORED_BYTES:
            break
    return out.getvalue(), img.width, img.height


def _limit(img: Image.Image) -> int:
    """The most pixels taken for this picture: a PNG and a progressive JPEG are decoded whole."""
    if img.format == "PNG":
        return MAX_PNG_PIXELS
    return MAX_PROGRESSIVE_PIXELS if img.info.get("progressive") or img.info.get("progression") else MAX_PIXELS


def _prepared(data: bytes, seconds: float = PREPARE_SECONDS) -> Prepared:
    deadline = time.monotonic() + seconds
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)     # the check below says it
            img = Image.open(_Timed(data, deadline), formats=OPENERS)
        if img.format not in FORMATS:
            raise _invalid(NOT_A_PICTURE_MESSAGE)
        if img.width * img.height > _limit(img):
            raise _invalid(TOO_MANY_PIXELS_MESSAGE)
        icc = img.info.get("icc_profile")                           # read before anything drops `info`
        orientation = img.getexif().get(ORIENTATION, 1)
        if img.format != "PNG":
            img.draft("RGB", _target(img.width, img.height))       # decode at 1/2, 1/4 or 1/8 when it can
        img.decodermaxblock = READ_BLOCK
        img.load()
        _check(deadline)
        img = _smaller(img)                                         # the decoded original is let go here
        img = img.transpose(TURNS[orientation]) if orientation in TURNS else img     # upright
        picture = _rgb(img, icc)
        _check(deadline)
    except _TooSlow:
        raise _too_slow() from None
    except Image.DecompressionBombError:
        raise _invalid(TOO_MANY_PIXELS_MESSAGE) from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise _invalid(NOT_A_PICTURE_MESSAGE) from None
    content, width, height = _encoded(picture)
    return Prepared(content, width, height)


def _scans(data: bytes) -> int:
    """A JPEG's scans: its SOS markers (in the compressed data a 0xFF byte is always followed by 0x00 or a
    restart marker, so FF DA is a marker wherever it is; an EXIF thumbnail's scan counts too)."""
    return data.count(b"\xff\xda")


def prepare(data: bytes, *, wait: float = BUSY_WAIT_SECONDS, seconds: float = PREPARE_SECONDS,
            total: float = TOTAL_WAIT_SECONDS) -> Prepared:
    """The upload checked and made ready to store (see the module docstring)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise _invalid(TOO_LARGE_MESSAGE)
    if not data:
        raise _invalid(NOT_A_PICTURE_MESSAGE)
    if data[:2] == b"\xff\xd8" and _scans(data) > MAX_SCANS:
        raise _invalid(NOT_A_PICTURE_MESSAGE)
    started = time.monotonic()
    job = _WORKER.submit(_prepared, data, seconds)
    try:
        return job.result(timeout=wait)
    except Waited:
        if job.cancel():                                            # still waiting its turn: not started
            raise RateLimited(BUSY_MESSAGE, retry_after_seconds=BUSY_RETRY_SECONDS) from None
    try:
        return job.result(timeout=max(0.0, total - (time.monotonic() - started)))   # started: its own time
    except Waited:
        raise _too_slow() from None


@functools.lru_cache(maxsize=32)
def _font(size: int) -> ImageFont.FreeTypeFont:
    """The band's font at this pixel size (loaded once a size: fitted_sizes asks for each line and step)."""
    return ImageFont.truetype(FONT_FILE, size)


def fitted_sizes(draw: ImageDraw.ImageDraw, lines: Sequence[tuple[str, int]], width: int) -> list[int]:
    """The lines' pixel sizes, all shrunk by the same factor until every line fits `width` (so a long
    reading is never smaller than the date under it), at least 8 px."""
    scale = 1.0
    for text, px in lines:
        length = draw.textlength(text, font=_font(px))
        if length > width:
            scale = min(scale, width / length)
    sizes = [max(8, int(px * scale)) for _text, px in lines]
    while any(draw.textlength(text, font=_font(size)) > width for (text, _px), size in zip(lines, sizes)) \
            and max(sizes) > 8:
        sizes = [max(8, size - 1) for size in sizes]
    return sizes


def cover(picture: bytes, lines: Sequence[tuple[str, int]], size: tuple[int, int]) -> bytes:
    """The cover's box (see the module docstring). `lines` are (text, pixel size), top to bottom; blank ones
    are left out, and with none there is no band."""
    width, height = size
    with Image.open(BytesIO(picture)) as img:
        box = ImageOps.fit(img.convert("RGB"), size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    lines = [(text, px) for text, px in lines if text.strip()]
    if lines:
        draw = ImageDraw.Draw(box)
        margin = round(width * 0.05)
        fonts = [_font(px) for px in fitted_sizes(draw, lines, width - 2 * margin)]
        gap = round(min(px for _text, px in lines) * 0.45)
        heights = [font.getbbox(text)[3] - font.getbbox(text)[1] for (text, _px), font in zip(lines, fonts)]
        pad = round(min(px for _text, px in lines) * 0.6)
        band_top = height - (sum(heights) + gap * (len(lines) - 1) + 2 * pad)
        band = Image.new("RGBA", (width, height - band_top), (0, 0, 0, round(255 * BAND_OPACITY)))
        box = Image.alpha_composite(box.convert("RGBA"), Image.new("RGBA", size, (0, 0, 0, 0)))
        box.alpha_composite(band, (0, band_top))
        draw = ImageDraw.Draw(box)
        y = band_top + pad
        for (text, _px), font, h in zip(lines, fonts, heights):
            top = font.getbbox(text)[1]
            draw.text(((width - draw.textlength(text, font=font)) / 2, y - top), text, font=font,
                      fill=(255, 255, 255, 255))
            y += h + gap
        box = box.convert("RGB")
    box.info.clear()                                                # the stored picture's metadata stays out
    out = BytesIO()
    box.save(out, "JPEG", quality=90, optimize=True)
    return out.getvalue()
