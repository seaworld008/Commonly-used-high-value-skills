"""Real local-image -> PDF rendering retains transparent raster backgrounds."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")
Image = pytest.importorskip("PIL.Image")
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/office-white-collar/pdf/scripts/md_to_pdf.py"


@pytest.mark.parametrize("kind", ["png", "webp", "gif", "palette-png"])
def test_authorized_raster_alpha_survives_real_pdf_render(tmp_path, kind):
    path = tmp_path / ("logo." + ("png" if kind == "palette-png" else kind))
    if kind in {"gif", "palette-png"}:
        image = Image.new("P", (40, 40), 0)
        image.putpalette([0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255] + [0] * (768 - 12))
        for y in range(40):
            for x in range(40):
                image.putpixel((x, y), (0 if x < 20 else 1) if y < 20 else (2 if x < 20 else 3))
        image.save(path, format="GIF" if kind == "gif" else "PNG", transparency=0)
    else:
        image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        for y in range(40):
            for x in range(40):
                if x >= 20:
                    image.putpixel((x, y), (255, 0, 0, 255) if y < 20 else (0, 0, 255, 255))
                elif y >= 20:
                    image.putpixel((x, y), (0, 255, 0, 128))
        image.save(path, format=kind.upper(), **({"lossless": True, "exact": True} if kind == "webp" else {}))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    source = tmp_path / "source.md"
    source.write_text(f"![transparent logo]({path.name})\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("alpha_markdown_pdf", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "out.pdf"
    module.markdown_to_pdf(source, output, resource_root=tmp_path)
    with pymupdf.open(output) as document:
        page = document[0]
        images = page.get_images(full=True)
        assert images and any(item[1] for item in images), "Transparency mask was discarded"
        rect = page.get_image_rects(images[0][0])[0]
        pixmap = page.get_pixmap(alpha=False)
        def sample(x, y):
            point = (rect.x0 + rect.width * x, rect.y0 + rect.height * y)
            return pixmap.pixel(round(point[0] * pixmap.width / page.rect.width),
                                round(point[1] * pixmap.height / page.rect.height))
        assert min(sample(.25, .25)) >= 250, "Transparent black must show the white page"
        if kind in {"png", "webp"}:
            green = sample(.25, .75)
            assert 100 <= green[0] <= 150 and green[1] >= 250 and 100 <= green[2] <= 150
        red = sample(.75, .25)
        assert red[0] > 220 and red[1] < 40 and red[2] < 40
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert not list(tmp_path.glob(".markdown-pdf-*"))
