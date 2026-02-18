---
name: sign-pdf
description: "Overlay stamp and signature on a PDF document. Trigger when: (1) user says 'подпиши', 'поставь печать', 'sign PDF', (2) user drops a PDF and mentions signing/stamping, (3) user asks to prepare an invoice or document for sending with seal. Supports presets for known document types (счёт-фактура) with pre-calibrated positions."
---

# Sign PDF

## Dependencies

Python: `pypdf`, `reportlab`, `Pillow`. System: `poppler` (brew, for preview).

```bash
python3 -c "from pypdf import PdfReader; from reportlab.pdfgen import canvas; from PIL import Image; print('OK')"
# If missing: pip install pypdf reportlab Pillow && brew install poppler
```

## Seal images

Stamp and signature PNGs stored outside any repo:

```
~/Projects/_secrets/seal/
├── stamp.png
└── signature.png
```

## Workflow

1. Run script with PDF path and preset (if known):
```bash
python3 .claude/skills/sign-pdf/scripts/sign_pdf.py "path/to/doc.pdf" --preset invoice
```

2. Preview result:
```bash
pdftoppm -png -r 150 "path/to/doc (подписан).pdf" /tmp/signed_preview
```
Show preview to user via Read tool.

3. If user wants adjustment — convert cm to points (1 cm = 28.35 pt), rerun with offsets:
```bash
python3 .claude/skills/sign-pdf/scripts/sign_pdf.py "doc.pdf" --preset invoice --sign-dy -28.35 --stamp-dx 85
```

4. Repeat until user approves.

## Presets

| Preset | `--preset` | Description |
|--------|-----------|-------------|
| Счёт-фактура | `invoice` | 4.5 cm, bottom-left ИП area, all pages |
| Default | (none) | 4.5 cm, bottom-left, all pages |

New presets: add to `PRESETS` dict in `scripts/sign_pdf.py`.

## Arguments

| Arg | Default | Notes |
|-----|---------|-------|
| `pdf` | required | Path to PDF |
| `--preset` | none | Preset name (`invoice`) |
| `--pages` | all | e.g. `1,2` or `2` |
| `--size` | 4.5 | Image size in cm |
| `--sign-dx/dy` | 0 | Signature offset (points, +right/+up) |
| `--stamp-dx/dy` | 0 | Stamp offset (points) |
| `--stamp` | auto | Override stamp path |
| `--signature` | auto | Override signature path |
| `--output` | auto | Output path (default: original + " (подписан)") |
