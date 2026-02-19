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

### Calibrated preset (invoice, etc.) — ONE step, no confirmations

If the document type has a calibrated preset, run sign + open in a single Bash call.
Do NOT ask for intermediate confirmations — presets are already tuned.

```bash
python3 .claude/skills/sign-pdf/scripts/sign_pdf.py "path/to/doc.pdf" --preset invoice && open "path/to/doc (подписан).pdf"
```

Tell user the file is ready and opened in Preview. Done.

### New/unknown document — iterative calibration

1. Run script with best-guess positioning:
```bash
python3 .claude/skills/sign-pdf/scripts/sign_pdf.py "path/to/doc.pdf" && open "path/to/doc (подписан).pdf"
```

2. If user wants adjustment — convert cm to points (1 cm = 28.35 pt), rerun with offsets:
```bash
python3 .claude/skills/sign-pdf/scripts/sign_pdf.py "doc.pdf" --sign-dy -28.35 --stamp-dx 85 && open "doc (подписан).pdf"
```

3. Repeat until user approves, then save as new preset in `PRESETS` dict.

## Presets

| Preset | `--preset` | Description |
|--------|-----------|-------------|
| Счёт-фактура | `invoice` | 4.5 cm, печать + подпись ИП (left) + подпись бухгалтера (right), all pages |
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
| `--sign2-dx/dy` | 0 | 2nd signature offset (points, for presets with sign2) |
| `--stamp` | auto | Override stamp path |
| `--signature` | auto | Override signature path |
| `--output` | auto | Output path (default: original + " (подписан)") |
