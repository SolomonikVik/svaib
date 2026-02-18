#!/usr/bin/env python3
"""
Overlay stamp and signature on PDF pages.
Seal images: ~/Projects/_secrets/seal/

Usage:
    python3 sign_pdf.py "invoice.pdf" --preset invoice
    python3 sign_pdf.py "doc.pdf" --stamp-dx 85 --sign-dy -28.35
"""

import argparse
import io
import os
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

CM = 28.35  # 1 cm in PDF points
SEAL_DIR = Path.home() / "Projects" / "_secrets" / "seal"

# Presets: pre-calibrated positions for known document types
# Coordinates in PDF points, visual space (origin = bottom-left of displayed page)
PRESETS = {
    "invoice": {
        "description": "Счёт-фактура — ИП area, bottom-left, all pages",
        "size_cm": 4.5,
        "sign_x": 168.0,
        "sign_y": 24.0,
        "stamp_x": 67.0,
        "stamp_y": 34.0,
        "pages": None,  # all
    },
}

DEFAULT_PRESET = {
    "size_cm": 4.5,
    "sign_x": 168.0,
    "sign_y": 24.0,
    "stamp_x": 67.0,
    "stamp_y": 34.0,
    "pages": None,
}


def make_white_transparent(img_path, threshold=240):
    img = Image.open(img_path).convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > threshold and g > threshold and b > threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def img_to_buf(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def create_overlay(page_w, page_h, stamp_buf, sign_buf, img_size,
                   sign_x, sign_y, stamp_x, stamp_y):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    stamp_buf.seek(0)
    sign_buf.seek(0)
    c.drawImage(ImageReader(stamp_buf), stamp_x, stamp_y,
                width=img_size, height=img_size, mask="auto")
    c.drawImage(ImageReader(sign_buf), sign_x, sign_y,
                width=img_size, height=img_size, mask="auto")
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def sign_pdf(pdf_path, output_path=None, preset_name=None, pages=None,
             size_cm=None, sign_dx=0, sign_dy=0, stamp_dx=0, stamp_dy=0,
             stamp_path=None, signature_path=None):

    # Resolve preset
    preset = PRESETS.get(preset_name, DEFAULT_PRESET) if preset_name else DEFAULT_PRESET

    # Resolve paths
    stamp_file = stamp_path or str(SEAL_DIR / "stamp.png")
    sign_file = signature_path or str(SEAL_DIR / "signature.png")

    for path, label in [(pdf_path, "PDF"), (stamp_file, "Stamp"), (sign_file, "Signature")]:
        if not os.path.exists(path):
            print(f"Error: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    if not output_path:
        base, ext = os.path.splitext(pdf_path)
        output_path = f"{base} (подписан){ext}"

    # Resolve parameters (CLI overrides > preset)
    img_size = (size_cm or preset["size_cm"]) * CM
    sign_x = preset["sign_x"] + sign_dx
    sign_y = preset["sign_y"] + sign_dy
    stamp_x = preset["stamp_x"] + stamp_dx
    stamp_y = preset["stamp_y"] + stamp_dy
    target_pages = pages or preset.get("pages")

    # Process images
    stamp_buf = img_to_buf(make_white_transparent(stamp_file))
    sign_buf = img_to_buf(make_white_transparent(sign_file))

    # Process PDF
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    pages_to_sign = (
        set(range(len(reader.pages)))
        if target_pages is None
        else {p - 1 for p in target_pages}
    )

    for i, page in enumerate(reader.pages):
        if i in pages_to_sign:
            if page.get("/Rotate", 0):
                page.transfer_rotation_to_content()
            box = page.mediabox
            eff_w, eff_h = float(box.width), float(box.height)
            stamp_buf.seek(0)
            sign_buf.seek(0)
            overlay = create_overlay(eff_w, eff_h, stamp_buf, sign_buf,
                                     img_size, sign_x, sign_y, stamp_x, stamp_y)
            page.merge_page(overlay)
            print(f"Page {i + 1}: signed ({eff_w:.0f}x{eff_h:.0f})")
        else:
            print(f"Page {i + 1}: skipped")
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Output: {output_path}")


def parse_pages(value):
    return [int(p.strip()) for p in value.split(",")]


def main():
    parser = argparse.ArgumentParser(description="Overlay stamp and signature on PDF")
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--preset", default=None,
                        help=f"Preset name ({', '.join(PRESETS.keys())})")
    parser.add_argument("--pages", type=parse_pages, default=None, help="Pages (e.g. 1,2)")
    parser.add_argument("--size", type=float, default=None, help="Image size in cm")
    parser.add_argument("--sign-dx", type=float, default=0, help="Signature X offset (pt)")
    parser.add_argument("--sign-dy", type=float, default=0, help="Signature Y offset (pt)")
    parser.add_argument("--stamp-dx", type=float, default=0, help="Stamp X offset (pt)")
    parser.add_argument("--stamp-dy", type=float, default=0, help="Stamp Y offset (pt)")
    parser.add_argument("--stamp", default=None, help="Override stamp path")
    parser.add_argument("--signature", default=None, help="Override signature path")
    parser.add_argument("--output", default=None, help="Output path")
    args = parser.parse_args()

    sign_pdf(
        pdf_path=args.pdf, output_path=args.output, preset_name=args.preset,
        pages=args.pages, size_cm=args.size,
        sign_dx=args.sign_dx, sign_dy=args.sign_dy,
        stamp_dx=args.stamp_dx, stamp_dy=args.stamp_dy,
        stamp_path=args.stamp, signature_path=args.signature,
    )


if __name__ == "__main__":
    main()
