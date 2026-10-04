"""The cover picture (printed bulletin spec, "Data model"; PR 3 planning
answers 2-5; bulletin_image.py): an upload checked, turned upright, scaled
and stored as JPEG; the cover's box made from it. Invented pictures only
(tests/picture_helpers.py)."""
import random
import subprocess
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageCms, ImageDraw

import bulletin_image as bi
from domain_errors import InvalidInput, RateLimited
from tests.picture_helpers import (BLUE, GREEN, RED, near, opened, picture, repeated_scan, stripes,
                                  swapped_profile)


def test_a_large_photo_is_stored_as_a_jpeg_at_most_1600_px_on_its_long_side():
    stored = bi.prepare(stripes((4000, 3000), [RED, GREEN, BLUE]))
    img = opened(stored.content)
    assert (img.format, img.size, (stored.width, stored.height)) == ("JPEG", (1600, 1200), (1600, 1200))
    assert near(img.getpixel((800, 100)), RED) and near(img.getpixel((800, 1100)), BLUE)
    assert bi.CONTENT_TYPE == "image/jpeg"


def test_a_photo_is_turned_upright():
    """A phone stores a portrait photo sideways with an EXIF orientation (6: turn it a quarter clockwise)."""
    exif = Image.Exif()
    exif[0x0112] = 6
    stored = bi.prepare(stripes((400, 200), [RED, BLUE], horizontal=False, exif=exif.tobytes()))
    img = opened(stored.content)
    assert img.size == (200, 400)                                   # now a portrait
    assert near(img.getpixel((100, 50)), RED) and near(img.getpixel((100, 350)), BLUE)


def test_a_small_png_keeps_its_size_and_a_transparent_part_turns_white():
    png = BytesIO()
    img = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    img.paste((30, 160, 60, 255), (0, 0, 150, 200))
    img.save(png, "PNG")
    stored = bi.prepare(png.getvalue())
    out = opened(stored.content)
    assert (out.format, out.mode, out.size) == ("JPEG", "RGB", (300, 200))   # never enlarged
    assert near(out.getpixel((50, 100)), GREEN) and near(out.getpixel((250, 100)), (255, 255, 255))


def test_the_stored_picture_keeps_no_camera_data():
    """No EXIF (a phone's location and time) and no color profile: the colors are converted to sRGB."""
    exif = Image.Exif()
    exif[0x0110] = "Example Phone"
    exif[0x8825] = {1: "N", 2: (40.0, 0.0, 0.0)}
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    stored = bi.prepare(picture((800, 600), exif=exif.tobytes(), icc_profile=icc))
    img = opened(stored.content)
    assert "exif" not in img.info and "icc_profile" not in img.info
    assert near(img.getpixel((400, 300)), GREEN)


@pytest.mark.parametrize("data, message", [
    (picture(fmt="GIF", mode="P", color=1), bi.NOT_A_PICTURE_MESSAGE),
    (picture(fmt="BMP"), bi.NOT_A_PICTURE_MESSAGE),
    (b"%PDF-1.4 not a picture", bi.NOT_A_PICTURE_MESSAGE),
    (picture()[:600], bi.NOT_A_PICTURE_MESSAGE),                              # cut short
    (b"", bi.NOT_A_PICTURE_MESSAGE),
    (picture((8000, 7000), fmt="JPEG", mode="L", color=128), bi.TOO_MANY_PIXELS_MESSAGE),               # 56 MP
    (picture((5000, 5000), fmt="PNG", mode="1", color=1), bi.TOO_MANY_PIXELS_MESSAGE),        # a 25 MP PNG
    (picture((11000, 10000), fmt="PNG", mode="1", color=1), bi.TOO_MANY_PIXELS_MESSAGE),      # Pillow's own guard
    (b"\xff" * (10 * 1024 * 1024 + 1), bi.TOO_LARGE_MESSAGE),
])
def test_only_a_jpeg_or_png_of_at_most_10_mb_and_50_million_pixels_is_taken(data, message):
    with pytest.raises(InvalidInput) as raised:
        bi.prepare(data)
    assert (raised.value.message, raised.value.field, raised.value.status) == (message, "image", 422)


def test_the_cover_fills_the_box_with_a_centered_crop_and_a_dark_band():
    """Planning answers 2-4: a tall picture in a wide box keeps its middle (the top and bottom are trimmed
    evenly); the reading and the date are white on a dark see-through band across the bottom; color stays."""
    tall = bi.prepare(stripes((600, 1200), [RED, GREEN, GREEN, GREEN, BLUE])).content
    box = opened(bi.cover(tall, [("Matthew 21:23-32", 75), ("October 11, 2026", 58)], (1550, 1250)))
    assert (box.format, box.mode, box.size) == ("JPEG", "RGB", (1550, 1250))
    assert near(box.getpixel((5, 5)), GREEN) and near(box.getpixel((775, 600)), GREEN)   # no red: trimmed
    band = [box.getpixel((x, 1240)) for x in (5, 1545)]
    assert all(near(pixel, tuple(round(c * (1 - bi.BAND_OPACITY)) for c in GREEN), 25) for pixel in band)
    row = [box.getpixel((x, y)) for y in range(1050, 1250, 4) for x in range(300, 1250, 4)]
    assert any(min(pixel) > 230 for pixel in row)                                           # white letters
    plain = opened(bi.cover(tall, [("", 75)], (1550, 1250)))
    assert near(plain.getpixel((5, 1240)), GREEN)                                           # nothing to say: no band


def test_a_long_reading_is_shrunk_to_fit_the_band():
    long = "1 Corinthians 15:1-11, 12-20, 35-38, 42-50 or Psalm 23 or Psalm 100"
    box = opened(bi.cover(picture((1600, 1200)), [(long, 75), ("October 11, 2026", 58)], (1550, 1250)))
    edges = [box.getpixel((x, y)) for y in range(1000, 1250, 2) for x in (2, 1547)]
    assert not any(min(pixel) > 230 for pixel in edges)                                     # no letter at the edge


# --- plan review fixes (2026-10-03): phone JPEGs, memory, stored size, odd PNGs, the band ---

def test_a_phone_s_multi_picture_jpeg_is_taken_as_a_jpeg():
    """An iPhone HDR or a Samsung portrait photo carries a second picture (Pillow reads it as "MPO")."""
    exif = Image.Exif()
    exif[0x0112] = 6
    out = BytesIO()
    Image.new("RGB", (4032, 3024), GREEN).save(out, "MPO", save_all=True, exif=exif.tobytes(),
                                               append_images=[Image.new("RGB", (1008, 756), RED)])
    assert Image.open(BytesIO(out.getvalue())).format == "MPO"
    stored = bi.prepare(out.getvalue())
    img = opened(stored.content)
    assert (img.format, img.size) == ("JPEG", (1200, 1600))                           # upright, the first picture
    assert near(img.getpixel((600, 800)), GREEN)


def test_a_16_bit_grey_png_keeps_its_tones():
    out = BytesIO()
    Image.new("I;16", (300, 200), 32768).save(out, "PNG")                              # mid-grey, 16 bits
    assert near(opened(bi.prepare(out.getvalue()).content).getpixel((150, 100)), (128, 128, 128), 3)


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
def test_a_color_profile_is_converted_to_srgb_with_or_without_transparency(mode):
    out = BytesIO()
    Image.new(mode, (300, 200), GREEN + (255,) * (mode == "RGBA")).save(out, "PNG", icc_profile=swapped_profile())
    assert near(opened(bi.prepare(out.getvalue()).content).getpixel((150, 100)), (60, 160, 30), 6)


def test_a_busy_picture_is_stored_in_at_most_600_kb():
    """Noise is the worst case for JPEG: a lower quality, then a smaller size, until it fits."""
    noise = Image.frombytes("RGB", (1600, 1600), random.Random(7).randbytes(1600 * 1600 * 3))
    png = BytesIO()
    noise.save(png, "PNG")
    stored = bi.prepare(png.getvalue())
    img = opened(stored.content)
    assert len(stored.content) <= bi.MAX_STORED_BYTES == 600_000
    assert img.format == "JPEG" and img.size == (stored.width, stored.height) and 800 <= stored.width < 1600
    assert len(bi.prepare(stripes((4000, 3000), [RED, GREEN, BLUE])).content) < 100_000      # a plain one: as is


def test_an_upload_waits_its_turn_then_is_told_to_try_again():
    """One picture is prepared at a time; one that cannot start within the wait is a 429."""
    release = threading.Event()
    busy = bi._WORKER.submit(release.wait, 10)
    try:
        with pytest.raises(RateLimited) as raised:
            bi.prepare(picture(), wait=0.05)
        assert (raised.value.message, raised.value.retry_after_seconds) == (bi.BUSY_MESSAGE, 5)
    finally:
        release.set()
        busy.result()
    assert bi.prepare(picture()).width == 400


MEMORY_PROBE = """
import resource, sys
from concurrent.futures import ThreadPoolExecutor
import bulletin_image as bi
data = open(sys.argv[1], "rb").read()
bi.prepare(open(sys.argv[2], "rb").read())                                  # warm up
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
with ThreadPoolExecutor(4) as pool:
    sizes = [p.width for p in pool.map(lambda _: bi.prepare(data), range(4))]
print(sizes, (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) // 1024)
"""


def test_four_large_pngs_at_once_take_the_memory_of_one(tmp_path):
    """The worst PNG taken (24 million pixels, a palette with transparency, a 3 KB file) needs about 220 MB
    to prepare; four arriving together are prepared one after another on one thread, so they need no more
    (a subprocess, so the peak is this upload's own)."""
    big = tmp_path / "big.png"
    Image.new("P", (4898, 4898), 0).save(big, transparency=0)
    small = tmp_path / "small.jpg"
    small.write_bytes(picture())
    backend = Path(bi.__file__).resolve().parent
    run = subprocess.run([sys.executable, "-c", MEMORY_PROBE, str(big), str(small)], cwd=backend,
                         capture_output=True, text=True, check=True)
    sizes, megabytes = run.stdout.rsplit(" ", 1)
    assert sizes == "[1600, 1600, 1600, 1600]"
    assert int(megabytes) < 300, run.stdout


def test_a_long_reading_and_the_date_shrink_together():
    """A reading too long for the band is made smaller, and the date with it, so it never prints smaller
    than the date under it."""
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    long = "1 Corinthians 15:1-11, 12-20, 35-38, 42-50 or Psalm 23 or Psalm 100"
    reading, date = bi.fitted_sizes(draw, [(long, 75), ("October 11, 2026", 58)], 1395)
    assert reading < 75 and reading >= date and abs(reading / date - 75 / 58) < 0.1
    assert draw.textlength(long, font=bi._font(reading)) <= 1395
    assert bi.fitted_sizes(draw, [("Matthew 22:1-14", 75), ("October 11, 2026", 58)], 1395) == [75, 58]


# --- build review fixes (2026-10-04, PR 3a) ---

def _markers(data: bytes) -> list[int]:
    """A JPEG's segment markers up to its first scan (APP1 is EXIF or XMP, COM a comment)."""
    found, at = [], 2
    while data[at + 1] != 0xDA:
        found.append(data[at + 1])
        at += 2 + int.from_bytes(data[at + 2:at + 4], "big")
    return found


def test_a_jpeg_with_too_many_scans_is_refused_before_it_is_decoded(monkeypatch):
    """Build review C1: each scan is a pass over the whole picture, so a small file repeating one scan
    thousands of times held the one worker for minutes. Pillow's progressive JPEG has 10 scans."""
    progressive = picture((2000, 1500), progressive=True)
    assert progressive.count(b"\xff\xda") == 10
    assert bi.prepare(repeated_scan(progressive, bi.MAX_SCANS - 10)).width == 1600          # 64 scans: taken
    monkeypatch.setattr(bi, "_prepared", lambda *args: pytest.fail("decoded"))
    with pytest.raises(InvalidInput) as raised:
        bi.prepare(repeated_scan(progressive, bi.MAX_SCANS - 9))                             # 65: refused
    assert (raised.value.message, raised.value.field) == (bi.NOT_A_PICTURE_MESSAGE, "image")


def test_a_picture_that_takes_too_long_stops_and_frees_the_worker(monkeypatch):
    """Build review C1: a started picture has PREPARE_SECONDS of the worker; the decode stops at its next
    read of the file, and the upload is told why (a 429 the page shows)."""
    monkeypatch.setattr(bi, "MAX_SCANS", 100_000)
    slow = repeated_scan(picture((2000, 1500), progressive=True), 5000)                    # about 7 s whole
    started = time.monotonic()
    with pytest.raises(RateLimited) as raised:
        bi.prepare(slow, seconds=0.3)
    assert time.monotonic() - started < 3
    assert (raised.value.message, raised.value.retry_after_seconds) == (bi.TOO_SLOW_MESSAGE, 5)
    with pytest.raises(RateLimited):
        bi.prepare(picture(), seconds=-1)                                                    # checked between steps
    assert bi.prepare(picture()).width == 400                                                # the worker is free


def test_an_upload_waits_for_its_started_picture_no_longer_than_the_total(monkeypatch):
    """Build review C1: the request is never held longer than TOTAL_WAIT_SECONDS, even by a decode that
    cannot be stopped."""
    release = threading.Event()
    monkeypatch.setattr(bi, "_prepared", lambda data, seconds: release.wait(10))
    try:
        started = time.monotonic()
        with pytest.raises(RateLimited) as raised:
            bi.prepare(picture(), wait=0.05, total=0.3)
        assert raised.value.message == bi.TOO_SLOW_MESSAGE and time.monotonic() - started < 2
    finally:
        release.set()
    assert bi.TOTAL_WAIT_SECONDS == 20


def test_a_progressive_jpeg_takes_at_most_24_million_pixels_as_a_png():
    """Build review I1: libjpeg keeps every coefficient of a progressive JPEG in memory whatever the scale it
    decodes at (300-400 MB at 50 MP), so it has the PNG's cap; a baseline JPEG (a phone's) keeps 50 MP."""
    size = (7000, 3500)                                                                     # 24.5 MP
    with pytest.raises(InvalidInput) as raised:
        bi.prepare(picture(size, mode="L", color=128, progressive=True))
    assert raised.value.message == bi.TOO_MANY_PIXELS_MESSAGE
    assert bi.prepare(picture(size, mode="L", color=128)).width == 1600
    assert bi.prepare(picture((4800, 4800), mode="L", color=128, progressive=True)).width == 1600    # 23 MP


def test_no_metadata_reaches_the_stored_picture_or_the_printed_cover():
    """Build review I2: a JPEG comment (a name or an address) was copied into the stored picture and the
    printed cover; now no comment, EXIF or XMP is written, at any size."""
    xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF/></x:xmpmeta>'
    exif = Image.Exif()
    exif[0x0110] = "Example Phone"
    for size in ((800, 600), (4000, 3000)):
        upload = picture(size, comment=b"Taken by Sam Sample", exif=exif.tobytes(), xmp=xmp)
        assert {0xFE, 0xE1} <= set(_markers(upload))
        stored = bi.prepare(upload).content
        assert opened(stored).info.keys() <= {"jfif", "jfif_version", "jfif_unit", "jfif_density", "dpi"}
        assert not {0xFE, 0xE1, 0xE2} & set(_markers(stored)) and b"Sam Sample" not in stored
        printed = bi.cover(upload, [("Matthew 22:1-14", 75)], (1550, 1250))
        assert not {0xFE, 0xE1, 0xE2} & set(_markers(printed)) and b"Sam Sample" not in printed


def test_the_band_s_font_is_loaded_once_a_size():
    """Build review M6: fitted_sizes asks for the font once a line a step."""
    lines = [("1 Corinthians 15:1-11, 12-20, 35-38 or Psalm 23", 75), ("October 11, 2026", 58)]
    bi._font.cache_clear()
    bi.cover(picture((1600, 1200)), lines, (1550, 1250))
    first = bi._font.cache_info()
    bi.cover(picture((1600, 1200)), lines, (1550, 1250))
    again = bi._font.cache_info()
    assert first.hits > 0 and again.misses == first.misses and again.hits > first.hits
