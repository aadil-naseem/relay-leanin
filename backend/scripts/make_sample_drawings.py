"""Generate the 3 synthetic sample drawings (Phase 12, task 1).

Vector PDFs WITH a text layer (ReportLab), rasterised PNGs (PyMuPDF ~200 DPI,
longest side <= 2000 px), plus one deliberately messy variant (rotated +
low-contrast). Synthetic drawings only: free-tier provider inputs may be used
by the provider, so no real customer documents are sent (R9).

Each drawing has a title block (fictional customers, drawing no., revision),
material, tolerances, finish, quantity and notes chosen to exercise every
rules-parser branch (material catalogue, tolerance formats, Ra, HRC, ISO 2768,
quantity, process keywords).

`expected.json` is the ground truth the rules-only accuracy test checks.

Usage: python scripts/make_sample_drawings.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageEnhance
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

DRAWINGS_DIR = BACKEND_DIR / "data" / "drawings"
PAGE_W, PAGE_H = landscape(A4)  # 842 x 595 pt

# ---------------------------------------------------------------- content

DRAWINGS: dict[str, dict] = {
    "pump_shaft": {
        "part_name": "Pump Shaft",
        "customer": "ACME Pumps (SAMPLE)",
        "drawing_no": "DWG-PSH-014",
        "revision": "B",
        "quantity": 200,
        "material": "EN8",
        "surface_finish_ra_um": 1.6,
        "general_tolerance_standard": "ISO 2768-m",
        "dimensions": [
            {"label": "SHAFT DIAMETER", "nominal_mm": 20.0, "tol_plus_mm": 0.02, "tol_minus_mm": 0.00, "critical": True},
            {"label": "LENGTH", "nominal_mm": 250.0, "tol_plus_mm": 0.1, "tol_minus_mm": 0.1, "critical": False},
        ],
        "tightest_tolerance_mm": 0.005,  # h7 shaft tolerance expressed as +- band? no: see notes
        "process_hints": ["TURN", "MILL"],
        "notes": [
            "GENERAL TOLERANCES: ISO 2768-m",
            "SURFACE FINISH: Ra 1.6",
            "SHAFT DIAMETER Ø20 h7 +0.02/-0.00  -  TURN",
            "KEYWAY 8 WIDE x 4 DEEP  -  MILL KEYWAY",
            "LENGTH 250 ±0.1",
            "DEBURR ALL EDGES",
        ],
        "envelope_mm": 250.0,
    },
    "piston_rod": {
        "part_name": "Hydraulic Piston Rod",
        "customer": "ACME Hydraulics (SAMPLE)",
        "drawing_no": "DWG-HPR-001",
        "revision": "A",
        "quantity": 50,
        "material": "EN24",
        "surface_finish_ra_um": 0.4,
        "general_tolerance_standard": None,
        "dimensions": [
            {"label": "ROD DIAMETER", "nominal_mm": 20.0, "tol_plus_mm": 0.005, "tol_minus_mm": 0.005, "critical": True},
            {"label": "OVERALL LENGTH", "nominal_mm": 300.0, "tol_plus_mm": 0.2, "tol_minus_mm": 0.2, "critical": False},
        ],
        "tightest_tolerance_mm": 0.005,
        "process_hints": ["TURN", "GRIND_CYL", "HEAT_TREAT", "SURFACE_TREAT"],
        "hardness_hrc": "58-62",
        "notes": [
            "MATERIAL NOTE: EN24 TO BS 970",
            "TURN FROM BAR STOCK BEFORE GRINDING",
            "ROD DIAMETER Ø20.00 ±0.005  -  CYLINDRICAL GRIND",
            "INDUCTION HARDENED HRC 58-62",
            "HARD CHROME PLATED 0.02 THICK",
            "SURFACE FINISH: Ra 0.4 ON GROUND OD",
            "OVERALL LENGTH 300 ±0.2",
        ],
        "envelope_mm": 300.0,
    },
    "valve_flange": {
        "part_name": "Valve Body Flange",
        "customer": "Delta Valves (SAMPLE)",
        "drawing_no": "DWG-VBF-207",
        "revision": "C",
        "quantity": 40,
        "material": "SS304",
        "surface_finish_ra_um": 3.2,
        "general_tolerance_standard": "ISO 2768-m",
        "dimensions": [
            {"label": "FLANGE OD", "nominal_mm": 120.0, "tol_plus_mm": 0.05, "tol_minus_mm": 0.05, "critical": True},
            {"label": "THICKNESS", "nominal_mm": 15.0, "tol_plus_mm": 0.1, "tol_minus_mm": 0.1, "critical": False},
        ],
        "tightest_tolerance_mm": 0.05,
        "process_hints": ["MILL", "DRILL_TAP"],
        "notes": [
            "GENERAL TOLERANCES: ISO 2768-m",
            "SURFACE FINISH: Ra 3.2",
            "FLANGE OD 120 ±0.05",
            "4 × M8 TAP (DRILL Ø6.8 x 12 DEEP)",
            "THICKNESS 15 ±0.1",
            "FACE MILL FINISH",
        ],
        "envelope_mm": 120.0,
    },
}

# The pump shaft's +0.02/-0.00 on a Ø20 h7 is the drawing-stated band; the
# tightest ACTUAL tolerance on that drawing is the ±0.1 length? No: +0.02 is
# tighter. Keep ground truth explicit per drawing:
DRAWINGS["pump_shaft"]["tightest_tolerance_mm"] = 0.02


# ---------------------------------------------------------------- rendering


def _title_block(c: canvas.Canvas, data: dict) -> None:
    x, y_top = PAGE_W - 250, 170
    line_h = 16
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + 110, y_top + 8, "TITLE BLOCK (SAMPLE)")
    rows = [
        f"CUSTOMER: {data['customer']}",
        f"PART: {data['part_name'].upper()}",
        f"DWG NO: {data['drawing_no']}",
        f"REV: {data['revision']}",
        f"QTY: {data['quantity']}",
        f"MATERIAL: {data['material']}",
    ]
    c.setFont("Helvetica", 10)
    for index, row in enumerate(rows):
        c.drawString(x, y_top - index * line_h, row)


def _notes_block(c: canvas.Canvas, data: dict) -> None:
    x, y_top = 40, PAGE_H - 60
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y_top, "NOTES:")
    c.setFont("Helvetica", 11)
    for index, note in enumerate(data["notes"], start=1):
        c.drawString(x + 10, y_top - 20 * index, f"{index}. {note}")


def _outline(c: canvas.Canvas, data: dict) -> None:
    """Simple credible part outline; geometry is decorative, text is the payload."""
    c.setLineWidth(1.2)
    cx, cy = PAGE_W / 2, PAGE_H / 2 - 20
    if data["drawing_no"] == "DWG-PSH-014":  # shaft: long rectangle + keyway
        c.rect(cx - 160, cy - 15, 320, 30)
        c.rect(cx - 40, cy - 15, 16, 10)  # keyway suggestion
        c.circle(cx - 160, cy, 4)
    elif data["drawing_no"] == "DWG-HPR-001":  # rod: rectangle + rod end
        c.rect(cx - 180, cy - 12, 360, 24)
        c.rect(cx - 180, cy - 24, 30, 48)
    else:  # flange: circle + bolt holes
        c.circle(cx, cy, 90)
        c.circle(cx, cy, 30)
        for angle in range(0, 360, 90):
            import math

            bx = cx + 60 * math.cos(math.radians(angle))
            by = cy + 60 * math.sin(math.radians(angle))
            c.circle(bx, by, 6)


def _make_pdf(out: Path, data: dict) -> None:
    c = canvas.Canvas(str(out), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"{data['drawing_no']} rev {data['revision']} (SAMPLE)")
    _outline(c, data)
    _notes_block(c, data)
    _title_block(c, data)
    c.showPage()
    c.save()


def _png_from_pdf(pdf: Path, out: Path, dpi: int = 200, max_side: int = 2000) -> None:
    doc = pymupdf.open(str(pdf))
    page = doc[0]
    zoom = min(dpi / 72.0, max_side / max(page.rect.width, page.rect.height))
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    pixmap.save(str(out))
    doc.close()


def _make_messy(src: Path, out: Path) -> None:
    """Rotated + low-contrast variant of the piston rod (deliberately hard)."""
    image = Image.open(src).convert("L")
    rotated = image.rotate(90, expand=True)
    low = ImageEnhance.Contrast(rotated).enhance(0.45)
    low.save(out)


def main() -> int:
    DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
    expected: dict[str, dict] = {}
    for stem, data in DRAWINGS.items():
        pdf = DRAWINGS_DIR / f"{stem}.pdf"
        png = DRAWINGS_DIR / f"{stem}.png"
        _make_pdf(pdf, data)
        _png_from_pdf(pdf, png)
        expected[stem] = {
            "pdf": pdf.name,
            "png": png.name,
            "part_name": data["part_name"],
            "customer": data["customer"],
            "drawing_no": data["drawing_no"],
            "revision": data["revision"],
            "quantity": data["quantity"],
            "material": data["material"],
            "surface_finish_ra_um": data["surface_finish_ra_um"],
            "general_tolerance_standard": data["general_tolerance_standard"],
            "tightest_tolerance_mm": data["tightest_tolerance_mm"],
            "envelope_mm": data["envelope_mm"],
            "process_hints": data["process_hints"],
            "dimensions": data["dimensions"],
            "hardness_hrc": data.get("hardness_hrc"),
        }
        print(f"made {pdf.name} + {png.name}")

    messy = DRAWINGS_DIR / "piston_rod_messy.png"
    _make_messy(DRAWINGS_DIR / "piston_rod.png", messy)
    expected["piston_rod_messy"] = {
        "png": messy.name,
        "derived_from": "piston_rod",
        "degraded": True,
        "note": "rotated 90 deg, contrast reduced to 0.45 - exercises the no-text-layer fallback",
    }
    print(f"made {messy.name}")

    out = DRAWINGS_DIR / "expected.json"
    out.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
