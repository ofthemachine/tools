#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Render PDF pages to high-resolution PNG images for visual inspection, slide viewing, or multimodal agent review.
#: when=Use when the user wants to see the visual layout of a PDF, inspect slides or figures, or convert PDF pages to PNG images.
#: network=none
#: stdin=none
#: param=pdf_source:required:file:d=PDF file mounted at /input/pdf_source
#: param=page:default=1:d=1-indexed page number to render to page.png, or 'all' to bundle every page into pages.tar.gz
#: param=scale:default=2.0:d=Render scale factor (1.0 = 72 dpi, 2.0 = 144 dpi, 3.0 = 216 dpi)
#: output=page.png
#: output=pages.tar.gz
import io
import os
import sys
import tarfile

import pypdfium2 as pdfium

source_path = os.environ.get("PDF_SOURCE", "")
page_spec = os.environ["PAGE"].strip()
scale_raw = os.environ["SCALE"].strip()

if not source_path or not os.path.exists(source_path):
    print(f"Error: pdf_source file '{source_path}' does not exist", file=sys.stderr)
    sys.exit(1)

try:
    scale = float(scale_raw)
    if scale <= 0:
        raise ValueError
except ValueError:
    print(f"Error: scale must be a positive number, got '{scale_raw}'", file=sys.stderr)
    sys.exit(1)

try:
    pdf = pdfium.PdfDocument(source_path)
except Exception as e:
    print(f"Error: cannot open PDF '{source_path}': {e}", file=sys.stderr)
    sys.exit(1)

total_pages = len(pdf)
if total_pages == 0:
    print(f"Error: PDF '{source_path}' has 0 pages", file=sys.stderr)
    sys.exit(1)

out_dir = "/output" if os.path.exists("/output") else "."

if page_spec.lower() == "all":
    tar_path = os.path.join(out_dir, "pages.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        for idx in range(total_pages):
            page_num = idx + 1
            page = pdf[idx]
            pil_img = page.render(scale=scale).to_pil()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            ti = tarfile.TarInfo(name=f"page-{page_num:03d}.png")
            ti.size = len(img_bytes)
            ti.mode = 0o644
            buf.seek(0)
            tar.addfile(ti, buf)

    file_size = os.path.getsize(tar_path)
    print(f"Rendered {total_pages} pages ({file_size:,} bytes) -> pages.tar.gz")
else:
    try:
        page_num = int(page_spec)
    except ValueError:
        print(f"Error: page must be an integer (1..{total_pages}) or 'all', got '{page_spec}'", file=sys.stderr)
        sys.exit(1)

    if page_num < 1 or page_num > total_pages:
        print(f"Error: page {page_num} out of bounds (PDF has {total_pages} pages)", file=sys.stderr)
        sys.exit(1)

    page = pdf[page_num - 1]
    pil_img = page.render(scale=scale).to_pil()
    png_path = os.path.join(out_dir, "page.png")
    pil_img.save(png_path, format="PNG")
    file_size = os.path.getsize(png_path)
    print(f"Rendered page {page_num}/{total_pages} ({pil_img.width}x{pil_img.height}, {file_size:,} bytes) -> page.png")
