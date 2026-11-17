"""Image completion receipts use synthetic bytes and an in-process fetch replacement."""

import base64
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/multimodal-media/gpt-image2/scripts/gpt-image2.mjs"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAADCAIAAAA2iEnWAAAAFElEQVR4nGMUCVjAwMDAxMDAgKAAExQBCsGXXKcAAAAASUVORK5CYII=")
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/"
    "2wBDAQgJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAADAAIDASIAAhEBAxEB/"
    "8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
    "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG"
    "x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAEC"
    "AxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOE"
    "hYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDhqKKK+yPmj//Z"
)
WEBP = base64.b64decode("UklGRjoAAABXRUJQVlA4IC4AAADwAQCdASoCAAMAAUAmJaACdLoB+AAEgwAA/vS+7/56ZrzB/k5/8pV4LG5vgAAA")
FORMATS = [(PNG, "image/png", ".png"), (JPEG, "image/jpeg", ".jpg"), (WEBP, "image/webp", ".webp")]
PRIVATE = "synthetic-private-download-marker"
URL = f"https://objects.invalid/{PRIVATE}?signature={PRIVATE}"


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png_with(ihdr=None, raster=None):
    return (PNG[:8] + png_chunk(b"IHDR", PNG[16:29] if ihdr is None else ihdr)
            + png_chunk(b"IDAT", zlib.compress(b"\x00" * 21) if raster is None else raster)
            + png_chunk(b"IEND", b""))


@pytest.fixture
def image_cli(tmp_path):
    script = shutil.copy(SCRIPT, tmp_path)
    mock = tmp_path / "fetch.cjs"
    mock.write_text(r"""
        const fs = require('node:fs');
        const fixture = JSON.parse(fs.readFileSync(process.env.FIXTURE_PATH, 'utf8'));
        global.fetch = async (url, opts) => {
          fs.appendFileSync('calls', JSON.stringify({url, method: opts.method,
            auth: new Headers(opts.headers).get('authorization'), redirect: opts.redirect}) + '\n');
          if (opts.method === 'POST') return Response.json({data: fixture.data});
          const headers = {'content-type': fixture.mime};
          if (fixture.length !== null) headers['content-length'] = fixture.length;
          return new Response(Buffer.from(fixture.raw, 'base64'), {headers});
        };
        if (process.env.FAIL_WRITE !== '0') {
          const files = require('node:fs/promises');
          const write = files.writeFile;
          let writes = 0;
          files.writeFile = async (...args) => {
            if (++writes === Number(process.env.FAIL_WRITE)) throw Error('synthetic disk failure');
            return write(...args);
          };
        }
    """)

    def invoke(raw=PNG, *, route="b64_json", data=None, n=1, mime="image/png", length=None, fail_write=False):
        if data is None:
            data = [{route: URL if route == "url" else base64.b64encode(raw).decode()}]
        fixture = {"data": data, "raw": base64.b64encode(raw).decode(), "mime": mime, "length": length}
        fixture_file = tmp_path / "network-fixture.json"
        fixture_file.write_text(json.dumps(fixture), encoding="utf-8")
        result = subprocess.run(
            ["node", "--require", mock, script, "synthetic prompt", "--base-url", "https://api.invalid/v1",
             "--api-key", "synthetic-key", "--out-dir", "out", "-n", str(n)],
            cwd=tmp_path, capture_output=True, text=True, timeout=15,
            env={"PATH": os.environ["PATH"], "TMPDIR": str(tmp_path),
                 "FIXTURE_PATH": str(fixture_file), "FAIL_WRITE": str(int(fail_write))},
        )
        calls = [json.loads(line) for line in (tmp_path / "calls").read_text().splitlines()]
        assert calls[0]["auth"] == "Bearer synthetic-key" and calls[0]["redirect"] == "error"
        for call in calls[1:]:
            assert call["auth"] is None and call["redirect"] == "error"
        assert PRIVATE not in result.stdout + result.stderr
        return result, sorted((tmp_path / "out").glob("*")), calls

    return invoke


@pytest.mark.parametrize("route", ["b64_json", "url"])
def test_png_signature_is_not_a_completed_image(image_cli, route):
    result, files, _ = image_cli(PNG[:8], route=route)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not files and "已保存 0 张" in result.stderr


@pytest.mark.parametrize("raw,mime,suffix", FORMATS)
def test_real_decoder_opens_positive_fixtures(raw, mime, suffix):
    image = pytest.importorskip("PIL.Image")
    with image.open(io.BytesIO(raw)) as decoded:
        decoded.load()
        assert decoded.size == (2, 3) and image.MIME[decoded.format] == mime


@pytest.mark.parametrize("route", ["b64_json", "url"])
@pytest.mark.parametrize("raw,mime,suffix", FORMATS)
def test_complete_images_are_saved_exactly(image_cli, route, raw, mime, suffix):
    result, files, calls = image_cli(raw, route=route, mime=mime, length=str(len(raw)))
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(files) == 1 and files[0].suffix == suffix and files[0].read_bytes() == raw
    assert "已保存 1 张，预期 1 张，缺少 0 张" in result.stdout
    assert len(calls) == (2 if route == "url" else 1)


@pytest.mark.parametrize("route", ["b64_json", "url"])
@pytest.mark.parametrize("fmt,mode,options", [
    ("PNG", "L", {}), ("PNG", "P", {}), ("PNG", "RGBA", {}), ("PNG", "I;16", {}),
    ("JPEG", "L", {}), ("JPEG", "RGB", {"progressive": True}),
    ("WEBP", "RGB", {"lossless": True}), ("WEBP", "RGBA", {}),
    ("WEBP", "RGBA", {"lossless": True}),
])
def test_real_encoder_variants_remain_accepted(image_cli, route, fmt, mode, options):
    image = pytest.importorskip("PIL.Image")
    source = image.new(mode, (9, 11))
    source.putpixel((1, 1), (50, 100, 150, 100) if mode == "RGBA" else
                    (50, 100, 150) if mode == "RGB" else 1)
    buffer = io.BytesIO()
    source.save(buffer, format=fmt, **options)
    raw = buffer.getvalue()
    with image.open(io.BytesIO(raw)) as decoded:
        decoded.load()
        assert decoded.size == source.size
    result, files, _ = image_cli(raw, route=route, mime={"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt])
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(files) == 1 and files[0].read_bytes() == raw


@pytest.mark.parametrize("route", ["b64_json", "url"])
def test_adam7_png_has_complete_pass_rows(image_cli, route):
    image = pytest.importorskip("PIL.Image")
    header = bytearray(PNG[16:29])
    header[12] = 1
    # A black 2x3 RGB image: Adam7 nonempty passes contain 4, 4, 8, 7 bytes.
    raw = png_with(ihdr=header, raster=zlib.compress(b"\x00" * 23))
    with image.open(io.BytesIO(raw)) as decoded:
        decoded.load()
        assert decoded.size == (2, 3) and set(decoded.get_flattened_data() if hasattr(decoded, "get_flattened_data") else decoded.getdata()) == {(0, 0, 0)}
    result, files, _ = image_cli(raw, route=route)
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(files) == 1 and files[0].read_bytes() == raw


def test_every_truncated_positive_fixture_fails(image_cli):
    data = [{"b64_json": base64.b64encode(raw[:cut]).decode()}
            for raw, _, _ in FORMATS for cut in range(len(raw))]
    result, files, _ = image_cli(data=data)
    assert result.returncode != 0 and not files and "已保存 0 张" in result.stderr


def malformed_images():
    ihdr = bytearray(PNG[16:29])
    ihdr[0:4] = b"\x00" * 4
    yield "png-zero-width", png_with(ihdr=ihdr), "image/png"
    ihdr = bytearray(PNG[16:29])
    ihdr[8] = 3
    yield "png-invalid-bit-depth", png_with(ihdr=ihdr), "image/png"
    for name, raw in [
        ("empty", b""), ("png-header", PNG[:8]), ("png-ihdr-only", PNG[:33]),
        ("png-no-iend", PNG[:-12]), ("png-short-iend", PNG[:-1]),
        ("png-bad-crc", PNG[:45] + bytes([PNG[45] ^ 1]) + PNG[46:]),
        ("png-wrong-chunk-length", PNG[:33] + b"\xff" * 4 + PNG[37:]),
        ("png-invalid-zlib", png_with(raster=b"not zlib")),
        ("png-wrong-raster-length", png_with(raster=zlib.compress(b"\x00\x01"))),
        ("png-invalid-filter", png_with(raster=zlib.compress((b"\x05" + b"\x00" * 6) * 3))),
        ("png-zlib-trailing-data", png_with(raster=zlib.compress((b"\x00" + b"\x00" * 6) * 3) + b"extra")),
        ("png-trailing-bytes", PNG + b"extra"),
    ]:
        yield name, raw, "image/png"
    sof = JPEG.index(b"\xff\xc0")
    sos = JPEG.index(b"\xff\xda")
    for name, raw in [
        ("jpeg-header", JPEG[:3]), ("jpeg-no-eoi", JPEG[:-2]),
        ("jpeg-only-delimiters", b"\xff\xd8\xff\xd9"),
        ("jpeg-wrong-segment-length", JPEG[:4] + b"\xff\xff" + JPEG[6:]),
        ("jpeg-zero-height", JPEG[:sof + 5] + b"\x00\x00" + JPEG[sof + 7:]),
        ("jpeg-no-scan", JPEG[:sos] + b"\xff\xd9"),
        ("jpeg-empty-scan", JPEG[:sos + 14] + b"\xff\xd9"),
        ("jpeg-trailing-bytes", JPEG + b"extra"),
    ]:
        yield name, raw, "image/jpeg"
    for name, raw in [
        ("webp-header", WEBP[:12]), ("webp-truncated", WEBP[:-1]),
        ("webp-wrong-riff-length", WEBP[:4] + b"\x00" * 4 + WEBP[8:]),
        ("webp-wrong-chunk-length", WEBP[:16] + b"\xff" * 4 + WEBP[20:]),
        ("webp-zero-width", WEBP[:26] + b"\x00\x00" + WEBP[28:]),
        ("webp-invalid-frame-code", WEBP[:20] + bytes([WEBP[20] | 1]) + WEBP[21:]),
        ("webp-invalid-frame-signature", WEBP[:23] + b"bad" + WEBP[26:]),
        ("webp-trailing-bytes", WEBP + b"extra"),
    ]:
        yield name, raw, "image/webp"


@pytest.mark.parametrize("route", ["b64_json", "url"])
@pytest.mark.parametrize("name,raw,mime", list(malformed_images()))
def test_malformed_images_never_count_as_saved(image_cli, route, name, raw, mime):
    result, files, _ = image_cli(raw, route=route, mime=mime)
    assert result.returncode != 0, name + result.stdout + result.stderr
    assert not files and "已保存 0 张" in result.stderr


@pytest.mark.parametrize("payload", ["%%%", "aGVsbG8=", "", "iVBORw0KGgo=!!",
                                     "data:image/png,not-base64", "data:image/jpeg;base64," + base64.b64encode(PNG).decode()])
def test_invalid_base64_and_declared_encoding_fail(image_cli, payload):
    result, files, _ = image_cli(data=[{"b64_json": payload}])
    assert result.returncode != 0 and not files


@pytest.mark.parametrize("route", ["b64_json", "url"])
@pytest.mark.parametrize("raw,mime", [
    (b"GIF89a", "image/gif"), (b"BM", "image/bmp"), (b"II\x2a\x00", "image/tiff"),
    (b"\x00\x00\x00\x18ftypavif", "image/avif"), (b"\x00\x00\x00\x18ftypheic", "image/heic"),
])
def test_formats_without_an_output_validator_fail_closed(image_cli, route, raw, mime):
    result, files, _ = image_cli(raw, route=route, mime=mime)
    assert result.returncode != 0 and not files and "已保存 0 张" in result.stderr


@pytest.mark.parametrize("length", ["1", str(len(PNG) + 1), "0", "-1", "not-a-length"])
def test_download_length_must_match_actual_bytes(image_cli, length):
    result, files, _ = image_cli(route="url", length=length)
    assert result.returncode != 0 and not files


@pytest.mark.parametrize("data,n,saved", [
    ([], 1, 0), ([{}], 1, 0), ([None], 1, 0),
    ([{"b64_json": base64.b64encode(PNG).decode()}], 2, 1),
    ([{}, {"b64_json": base64.b64encode(PNG).decode()}], 2, 1),
    ([{"b64_json": base64.b64encode(PNG).decode()}, {"b64_json": base64.b64encode(PNG[:8]).decode()}], 2, 1),
    ([{"b64_json": base64.b64encode(PNG).decode()}, {}], 1, 1),
    ([{"b64_json": base64.b64encode(PNG).decode()}] * 2, 1, 2),
])
def test_only_exact_complete_receipts_succeed(image_cli, data, n, saved):
    result, files, _ = image_cli(data=data, n=n)
    assert result.returncode != 0, result.stdout + result.stderr
    assert len(files) == saved and f"已保存 {saved} 张" in result.stderr


def test_all_entries_and_writes_must_succeed(image_cli):
    result, files, _ = image_cli(fail_write=True)
    assert result.returncode != 0 and not files and "已保存 0 张" in result.stderr


def test_partial_write_failure_reports_only_real_files(image_cli):
    data = [{"b64_json": base64.b64encode(PNG).decode()}] * 2
    result, files, _ = image_cli(data=data, n=2, fail_write=2)
    assert result.returncode != 0 and len(files) == 1 and files[0].read_bytes() == PNG
    assert "已保存 1 张，预期 2 张，缺少 1 张" in result.stderr


def test_valid_base64_encoding_variants(image_cli):
    data = [
        {"b64_json": "data:image/png;base64," + base64.b64encode(PNG).decode()},
        {"b64_json": base64.urlsafe_b64encode(JPEG).decode().rstrip("=")},
        {"b64_json": "\n" + base64.b64encode(WEBP).decode() + "\n"},
    ]
    result, files, _ = image_cli(data=data, n=3)
    assert result.returncode == 0, result.stdout + result.stderr
    assert [file.read_bytes() for file in files] == [PNG, JPEG, WEBP]


def test_multiple_valid_entries_match_real_saved_count(image_cli):
    data = [{"b64_json": base64.b64encode(raw).decode()} for raw, _, _ in FORMATS]
    result, files, _ = image_cli(data=data, n=3)
    assert result.returncode == 0, result.stdout + result.stderr
    assert [file.read_bytes() for file in files] == [raw for raw, _, _ in FORMATS]
    assert "已保存 3 张，预期 3 张，缺少 0 张" in result.stdout
