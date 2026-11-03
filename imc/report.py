"""PDF report of one saved calculation (ReportLab).

Typeface: Times New Roman when it is installed on the computer (macOS, Windows, Linux with the
Microsoft core fonts); otherwise Liberation Serif, which is metrically identical to Times New Roman
and is bundled with the program (SIL Open Font License, see imc/assets/fonts). Times New Roman itself
may not be redistributed, so it cannot be shipped in the public repository.
"""

import io
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String

from imc.correction import FORMS
from imc.notation import FORMULA_HTML, html as sym

ASSETS = Path(__file__).parent / "assets"
LOGO = ASSETS / "imc_logo.png"

AUTHOR = "Patrik Lukács"
UNIVERSITY = "Széchenyi István University, Győr"
RESEARCH = "Integrated Decision Support Model for Determining the Justification of Car-Sharing"
SLOGAN_A, SLOGAN_B = "Don’t risk it.", "Calculate it."

INK = colors.HexColor("#1F2330")
MUTE = colors.HexColor("#6B7080")
LINE = colors.HexColor("#D9DCE3")
SOFT = colors.HexColor("#F4F6FA")
RED = colors.HexColor("#FF4B4B")
RED_DARK = colors.HexColor("#C62F28")
BLUE = colors.HexColor("#3D6FB6")
GREEN = colors.HexColor("#2C8C4F")
ORANGE = colors.HexColor("#E08A1E")
GREY = colors.HexColor("#A3A8B5")

# ---------------------------------------------------------------- fonts
_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
     "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf",
     "Times New Roman"),
    ("C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/timesi.ttf", "C:/Windows/Fonts/timesbi.ttf",
     "Times New Roman"),
    ("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
     "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Italic.ttf",
     "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold_Italic.ttf", "Times New Roman"),
    (str(ASSETS / "fonts/LiberationSerif-Regular.ttf"), str(ASSETS / "fonts/LiberationSerif-Bold.ttf"),
     str(ASSETS / "fonts/LiberationSerif-Italic.ttf"), str(ASSETS / "fonts/LiberationSerif-BoldItalic.ttf"),
     "Liberation Serif"),
]
_FONT = {}


def serif_font():
    """Register the serif family once. Returns the name of the typeface actually used."""
    if _FONT:
        return _FONT["family"]
    for regular, bold, italic, bold_italic, family in _CANDIDATES:
        if all(Path(p).exists() for p in (regular, bold, italic, bold_italic)):
            pdfmetrics.registerFont(TTFont("Serif", regular))
            pdfmetrics.registerFont(TTFont("Serif-Bold", bold))
            pdfmetrics.registerFont(TTFont("Serif-Italic", italic))
            pdfmetrics.registerFont(TTFont("Serif-BoldItalic", bold_italic))
            pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold",
                                          italic="Serif-Italic", boldItalic="Serif-BoldItalic")
            _FONT["family"] = family
            return family
    raise RuntimeError("No serif font found (the bundled Liberation Serif files are missing).")


def _styles():
    serif_font()
    base = dict(fontName="Serif", textColor=INK, leading=14.2, fontSize=11)
    return {
        "body": ParagraphStyle("body", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 9, "leading": 11.5, "textColor": MUTE}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 9.5, "leading": 11.5}),
        "cellr": ParagraphStyle("cellr", **{**base, "fontSize": 9.5, "leading": 11.5, "alignment": TA_RIGHT}),
        "cellh": ParagraphStyle("cellh", **{**base, "fontName": "Serif-Bold", "fontSize": 9.5, "leading": 11.5}),
        "h1": ParagraphStyle("h1", **{**base, "fontName": "Serif-Bold", "fontSize": 24, "leading": 28}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": "Serif-Bold", "fontSize": 13.5, "leading": 17,
                                      "spaceBefore": 12, "spaceAfter": 5}),
        "lead": ParagraphStyle("lead", **{**base, "fontSize": 12, "leading": 15.5, "textColor": MUTE}),
        "kpi": ParagraphStyle("kpi", **{**base, "fontName": "Serif-Bold", "fontSize": 20, "leading": 23,
                                       "alignment": TA_CENTER}),
        "kpibig": ParagraphStyle("kpibig", **{**base, "fontName": "Serif-Bold", "fontSize": 30, "leading": 33,
                                          "alignment": TA_CENTER, "textColor": RED_DARK}),
        "kpil": ParagraphStyle("kpil", **{**base, "fontSize": 9, "leading": 11, "alignment": TA_CENTER,
                                         "textColor": MUTE}),
    }


def _f(v, fmt):
    if v is None:
        return "—"
    try:
        return format(v, fmt)
    except (TypeError, ValueError):
        return str(v)


def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- page decoration
class _NumberedCanvas(rl_canvas.Canvas):
    """Canvas that knows the total page count, for 'page n of m'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            self._decorate(total)
            super().showPage()
        super().save()

    def _decorate(self, total):
        w, h = A4
        meta = getattr(self, "_imc_meta", {})
        # header: logo, title, thin red rule
        if LOGO.exists():
            self.drawImage(str(LOGO), 20 * mm, h - 21 * mm, width=25.4 * mm, height=11 * mm, mask="auto")
        self.setFont("Serif-Bold", 10.5)
        self.setFillColor(INK)
        self.drawRightString(w - 20 * mm, h - 14 * mm, "Fleet-size estimate report")
        self.setFont("Serif", 9)
        self.setFillColor(MUTE)
        self.drawRightString(w - 20 * mm, h - 19 * mm, meta.get("header_right", ""))
        self.setStrokeColor(RED)
        self.setLineWidth(1.2)
        self.line(20 * mm, h - 24 * mm, w - 20 * mm, h - 24 * mm)
        # footer: rule, author line, slogan, page number
        self.setStrokeColor(LINE)
        self.setLineWidth(0.6)
        self.line(20 * mm, 19.5 * mm, w - 20 * mm, 19.5 * mm)
        # slogan, centred above the small print: "Don't risk it." in ink, "Calculate it." in red
        self.setFont("Serif-Bold", 12.5)
        wa = pdfmetrics.stringWidth(SLOGAN_A + " ", "Serif-Bold", 12.5)
        wb = pdfmetrics.stringWidth(SLOGAN_B, "Serif-Bold", 12.5)
        x0 = (w - wa - wb) / 2
        self.setFillColor(INK)
        self.drawString(x0, 13.4 * mm, SLOGAN_A + " ")
        self.setFillColor(RED_DARK)
        self.drawString(x0 + wa, 13.4 * mm, SLOGAN_B)
        self.setFont("Serif", 8)
        self.setFillColor(MUTE)
        self.drawString(20 * mm, 8.6 * mm, f"{AUTHOR} · {UNIVERSITY} · {meta.get('footer_left', '')}")
        self.drawRightString(w - 20 * mm, 8.6 * mm, f"page {self._pageNumber} of {total}")


# ---------------------------------------------------------------- charts
def _curve_chart(run, width=170 * mm, height=78 * mm):
    """Correction function f(R) with the calibration cities and the crosshair of this city."""
    r = run["result"]
    d = Drawing(width, height)
    left, bottom, pw, ph = 14 * mm, 10 * mm, width - 20 * mm, height - 15 * mm
    X = lambda v: left + v * pw
    Y = lambda v: bottom + v * ph
    for g in (0, .25, .5, .75, 1):
        d.add(Line(X(0), Y(g), X(1), Y(g), strokeColor=LINE, strokeWidth=0.4))
        d.add(String(X(0) - 3, Y(g) - 2.5, f"{g:.2f}", fontName="Serif", fontSize=7.5, fillColor=MUTE, textAnchor="end"))
    for g in (0, .2, .4, .6, .8, 1):
        d.add(String(X(g), bottom - 9, f"{g:.1f}", fontName="Serif", fontSize=7.5, fillColor=MUTE, textAnchor="middle"))
    d.add(String(X(.5), bottom - 18, "R  (0 = ideal public transport, 1 = worst)", fontName="Serif-Italic",
                 fontSize=8, fillColor=MUTE, textAnchor="middle"))
    d.add(String(X(0), Y(1) + 4, "correction f(R)", fontName="Serif-Italic", fontSize=8, fillColor=MUTE))
    lo, hi = (r.get("R_range") or [None, None])[:2] if r.get("R_range") else (None, None)
    if lo is not None:
        d.add(Rect(X(lo), Y(0), max(X(hi) - X(lo), 1.5), ph, fillColor=colors.HexColor("#E6EEF9"),
                   strokeColor=None))
    # every fittable form faintly, the chosen one strong
    for row in r.get("cascade_table", []):
        name = row["form"]
        if name == r["form"] or not row.get("params") and name != "quadratic":
            continue
        try:
            p = list(row["params"].values())
            pts = [(X(i / 100), Y(min(1, FORMS[name]["f"](i / 100, p)))) for i in range(101)]
        except Exception:
            continue
        rejected = row["status"].startswith("rejected")
        d.add(PolyLine([c for pt in pts for c in pt], strokeColor=GREY if rejected else ORANGE,
                       strokeWidth=0.8, strokeDashArray=[3, 2] if rejected else None))
    p = r.get("p") or []
    pts = [(X(i / 100), Y(min(1, FORMS[r["form"]]["f"](i / 100, p)))) for i in range(101)]
    d.add(PolyLine([c for pt in pts for c in pt], strokeColor=GREEN, strokeWidth=2.2))
    # calibration cities: their position on the f(R) scale implied by the pooled rho
    rho = r.get("rho")
    for c in run.get("calibration_cities", []):
        try:
            T = c["P"] * c["r_dmr"] * c["a0"] * c["w_cs"]
            f_obs = c["N_obs"] * c["u"] / (rho * T)
            d.add(Circle(X(c["R"]), Y(min(1, f_obs)), 2.4, fillColor=INK, strokeColor=colors.white, strokeWidth=0.6))
        except (TypeError, KeyError, ZeroDivisionError):
            pass
    # crosshair of this city
    R = r["R"]
    fR = FORMS[r["form"]]["f"](R, p)
    d.add(Line(X(R), Y(0), X(R), Y(fR), strokeColor=RED, strokeWidth=1.1))
    d.add(Line(X(R), Y(fR), X(0), Y(fR), strokeColor=RED, strokeWidth=1.1))
    d.add(Circle(X(R), Y(fR), 2.8, fillColor=RED, strokeColor=colors.white, strokeWidth=0.6))
    d.add(String(X(0) + 3, Y(fR) + 3, f"f(R) = {fR:.3f}", fontName="Serif-Bold", fontSize=8, fillColor=RED_DARK))
    d.add(String(X(R) + 3, Y(0) + 3, f"R = {R:.3f}", fontName="Serif-Bold", fontSize=8, fillColor=RED_DARK))
    return d


def _density_chart(rows, width=170 * mm):
    rows = [x for x in rows if x.get("per_1000") is not None]
    rows = sorted(rows, key=lambda x: -x["per_1000"])
    bar_h, gap = 5.2 * mm, 2.6 * mm
    height = len(rows) * (bar_h + gap) + 12 * mm
    d = Drawing(width, height)
    left = 42 * mm
    pw = width - left - 14 * mm
    vmax = max(x["per_1000"] for x in rows) * 1.1 or 1
    col = {"this city (estimate)": RED, "observed": BLUE, "synthetic (demo)": colors.HexColor("#8E7CF0"),
           "reference (entered)": colors.HexColor("#2A9D8F")}
    for i, x in enumerate(rows):
        y = height - 6 * mm - (i + 1) * (bar_h + gap) + gap
        d.add(String(left - 3, y + bar_h / 2 - 3, str(x["city"])[:30], fontName="Serif", fontSize=9,
                     fillColor=INK, textAnchor="end"))
        d.add(Rect(left, y, pw * x["per_1000"] / vmax, bar_h, fillColor=col.get(x["type"], GREY), strokeColor=None))
        d.add(String(left + pw * x["per_1000"] / vmax + 3, y + bar_h / 2 - 3, f"{x['per_1000']:.2f}",
                     fontName="Serif-Bold", fontSize=9, fillColor=INK))
    d.add(String(left, 1.5 * mm, "vehicles per 1,000 inhabitants", fontName="Serif-Italic", fontSize=8, fillColor=MUTE))
    return d


# ---------------------------------------------------------------- tables
def _table(data, widths, st, header=True, align_right=()):
    cells = []
    for r_i, row in enumerate(data):
        out = []
        for c_i, v in enumerate(row):
            style = st["cellh"] if (header and r_i == 0) else (st["cellr"] if c_i in align_right else st["cell"])
            out.append(v if not isinstance(v, str) else Paragraph(v, style))
        cells.append(out)
    t = Table(cells, colWidths=widths, hAlign="LEFT")
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK)]
    t.setStyle(TableStyle(style))
    return t


# ---------------------------------------------------------------- the report
def build_pdf(run, version=None):
    """Return the PDF report of one run as bytes."""
    st = _styles()
    r, c = run["result"], run["city"]
    version = version or run.get("app_version", "")
    saved = run.get("saved_at", "").replace("T", " ")[:16]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=30 * mm,
                            bottomMargin=25 * mm, title=f"IMC fleet-size estimate – {c['name']}",
                            author=AUTHOR, subject=RESEARCH, creator=f"IMC fleet-size model {version}")
    meta = {"header_right": f"{c['name']} · {saved}",
            "footer_left": f"IMC v{version} · calculation {run['id'][:15]}"}

    def canvasmaker(*args, **kwargs):
        cv = _NumberedCanvas(*args, **kwargs)
        cv._imc_meta = meta
        return cv

    E = []
    E.append(Paragraph(f"Fleet-size estimate: {_esc(c['name'])}", st["h1"]))
    E.append(Paragraph(f"{_esc(run.get('label', ''))} · {c.get('country') or ''} · population {c['P']:,} · "
                       f"calculated {saved}", st["lead"]))
    E.append(Spacer(1, 4))
    E.append(Paragraph(f"<b>{AUTHOR}</b> · {UNIVERSITY}<br/>Research: <i>{RESEARCH}</i> (AHP–TOPSIS–IMC model)",
                       st["small"]))
    E.append(Spacer(1, 8))
    if run.get("demo"):
        box = Table([[Paragraph("<b>DEMONSTRATION.</b> This calculation used synthetic calibration cities. "
                                "The fleet number is not a real estimate.", st["cell"])]], colWidths=[170 * mm])
        box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, RED), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF1F1")),
                                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        E += [box, Spacer(1, 8)]

    # key results
    dens = run["density"][0]
    kpi = [[Paragraph(f"{r['N']:.1f}", st["kpibig"]), Paragraph(_f(dens.get("per_1000"), ".2f"), st["kpi"]),
            Paragraph(f"{r['Ci']:.3f}", st["kpi"]), Paragraph(f"{r['R']:.3f}", st["kpi"]),
            Paragraph(_esc(r["form"]), st["kpi"])],
           [Paragraph(f"fleet size {sym('N')} (vehicles)", st["kpil"]), Paragraph("vehicles per 1,000 inhabitants", st["kpil"]),
            Paragraph(f"closeness {sym('Ci')}", st["kpil"]), Paragraph(f"deficiency {sym('R')}", st["kpil"]),
            Paragraph(f"correction form {sym('fR')}", st["kpil"])]]
    kt = Table(kpi, colWidths=[38 * mm, 34 * mm, 32 * mm, 32 * mm, 34 * mm], rowHeights=[13 * mm, 8 * mm])
    kt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, LINE), ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                            ("LINEAFTER", (0, 0), (-2, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    E += [kt, Spacer(1, 4)]
    E.append(Paragraph(f"Model: {FORMULA_HTML}. Rounded fleet: <b>{r['N_rounded']} vehicles</b>.", st["small"]))

    # 1 inputs
    E.append(Paragraph("1  City and mobility inputs", st["h2"]))
    est = run.get("estimated", {})
    rows = [["Quantity", "Symbol", "Value", "Note"]]
    for key, fmt in (("P", ",.0f"), ("r_dmr", ".4f"), ("a0", ".4f"), ("w_cs", ".4f"), ("u", ".1f"),
                     ("s", ".2f"), ("N_max", ".0f")):
        from imc.notation import name as nm
        v = c.get(key)
        note = ("estimated: " + _esc(est[key])) if key in est else ("not used" if v is None else "entered")
        rows.append([nm(key), sym(key), _f(v, fmt), note])
    E.append(_table(rows, [58 * mm, 20 * mm, 26 * mm, 66 * mm], st, align_right=(2,)))

    # 2 indicators
    E.append(Paragraph("2  Public-transport indicators (TOPSIS)", st["h2"]))
    rows = [["Code", "Indicator", "Group", "Kind", "Measured", "Worst", "Ideal"]]
    for i in run.get("indicators", []):
        rows.append([_esc(i["code"]), _esc(i["name"]), _esc(i["group"]), _esc(i["kind"]),
                     _f(i["measured"], "g"), _f(i["worst"], "g"), _f(i["ideal"], "g")])
    E.append(_table(rows, [14 * mm, 46 * mm, 28 * mm, 20 * mm, 22 * mm, 20 * mm, 20 * mm], st, align_right=(4, 5, 6)))
    E.append(Spacer(1, 3))
    E.append(Paragraph(f"Result: {sym('Ci')} = {r['Ci']:.3f}, {sym('R')} = 1 − {sym('Ci')} = {r['R']:.3f}.", st["small"]))

    # 3 weights
    E.append(Paragraph("3  Criteria weights (AHP)", st["h2"]))
    rows = [["Criterion", "Weight", "Used by an indicator"]]
    groups = {i["group"] for i in run.get("indicators", [])}
    for g, w in run.get("weights", {}).items():
        rows.append([_esc(g), f"{w:.3f}", "yes" if g in groups else "no – dropped, others rescaled"])
    E.append(_table(rows, [50 * mm, 25 * mm, 95 * mm], st, align_right=(1,)))
    E.append(Spacer(1, 3))
    E.append(Paragraph(f"Weights from: {_esc(run.get('weight_source', ''))}.", st["small"]))

    # 4 how the number was built
    steps = [["Step", "Vehicles"]] + [[_esc(s), f"{v:.1f}"] for s, v in r.get("steps", [])]
    E.append(KeepTogether([Paragraph("4  How the number was built", st["h2"]),
                           _table(steps, [140 * mm, 30 * mm], st, align_right=(1,))]
                          + [Paragraph(_esc(n), st["small"]) for n in r.get("notes", [])]))

    # 5 correction function
    E.append(Paragraph("5  Correction function and its selection", st["h2"]))
    E.append(_curve_chart(run))
    E.append(Paragraph("Green: chosen form · orange: passed · grey dashed: rejected · dots: calibration cities · "
                       "shaded: their R range · red: this city.", st["small"]))
    E.append(Spacer(1, 4))
    rows = [["Form", "Status", "Parameters", "Leave-one-out error", "Score"]]
    for row in r.get("cascade_table", []):
        params = ", ".join(f"{k} = {v:.3f}" for k, v in (row.get("params") or {}).items()) or "—"
        rows.append([_esc(row["form"]), _esc(row["status"] + (f" ({row['why']})" if row.get("why") else "")), params,
                     _f(row.get("loo_median"), ".1%"), _f(row.get("score"), ".1%")])
    E.append(_table(rows, [24 * mm, 62 * mm, 34 * mm, 28 * mm, 22 * mm], st, align_right=(3, 4)))
    E.append(Spacer(1, 3))
    E.append(Paragraph(f"Pooled calibration factor {sym('rho')} = {_f(r.get('rho'), '.3f')}. "
                       + ("The city lies inside the R range of the calibration cities."
                          if r.get("inside_range") else
                          "The city lies outside the R range of the calibration cities: the result is an extrapolation."),
                       st["small"]))

    # 6 calibration cities
    rows = [["City", "Country", "Population", "R", "Observed fleet", "u", "Vehicles per 1,000"]]
    for x in run.get("calibration_cities", []):
        per = (1000 * x["N_obs"] / x["P"]) if x.get("N_obs") and x.get("P") else None
        rows.append([_esc(x["name"]) + (" (synthetic)" if x.get("synthetic") else ""), _esc(x.get("country") or ""),
                     _f(x.get("P"), ",.0f"), _f(x.get("R"), ".3f"), _f(x.get("N_obs"), ".1f"), _f(x.get("u"), ".1f"),
                     _f(per, ".2f")])
    E.append(KeepTogether([Paragraph("6  Calibration cities used in this calculation", st["h2"]),
                           _table(rows, [40 * mm, 18 * mm, 24 * mm, 18 * mm, 26 * mm, 14 * mm, 30 * mm], st,
                                  align_right=(2, 3, 4, 5, 6))]))

    # 7 density
    E.append(KeepTogether([Paragraph("7  Density comparison", st["h2"]), _density_chart(run["density"]),
                           Paragraph("Vehicles per 1,000 inhabitants = 1000 · N / P. A density comparison is a "
                                     "plausibility check, not a validation: cities differ in size, public transport "
                                     "and operator strategy.", st["small"])]))

    # 8 warnings
    E.append(Paragraph("8  Warnings and assumptions", st["h2"]))
    warns = run.get("warnings", []) or ["None."]
    for w in warns:
        E.append(Paragraph("• " + _esc(w), st["body"]))
    for k, how in est.items():
        E.append(Paragraph(f"• {_esc(k)} was not given: {_esc(how)}.", st["body"]))

    # 9 citation
    E.append(Paragraph("9  Method and citation", st["h2"]))
    E.append(Paragraph(f"Calculated with the IMC fleet-size model v{_esc(version)}, the self-calibrating application of "
                       f"the thesis by {AUTHOR}, <i>{RESEARCH}</i>, {UNIVERSITY}, 2026. The model combines the Analytic "
                       f"Hierarchy Process (criteria weights), reference-based TOPSIS (public-transport quality) and the "
                       f"IMC demand model, calibrated on every stored city with an observed fleet.", st["body"]))
    E.append(Spacer(1, 4))
    E.append(Paragraph(f"Typeface: {serif_font()}. Report generated {datetime.now():%Y-%m-%d %H:%M}.", st["small"]))

    doc.build(E, canvasmaker=canvasmaker)
    return buf.getvalue()
