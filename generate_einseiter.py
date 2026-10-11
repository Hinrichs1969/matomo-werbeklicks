#!/usr/bin/env python3
"""Einseitige Verkaufsunterlagen für alle Online-Produkte
im Design der bestehenden DigiBeilage-/Titelseiten-Vorlagen.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage, ImageDraw
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Einseiter_Online-Produkte"
ASSETS = ROOT / "assets_verkauf"

# Seitenformat wie DigiBeilage-Vorlage (etwas höher als A4)
PAGE_W = 210 * mm
PAGE_H = 340 * mm

YELLOW = HexColor("#F0C010")
BLUE = HexColor("#0090E0")
MAGENTA = HexColor("#B05090")
DARK = HexColor("#111111")
GRAY = HexColor("#333333")

# Fonts (Hausschrift Blinker + Fedra)
FONT_DIR = Path.home() / "Library" / "Fonts"


def register_fonts() -> dict[str, str]:
    """Fedra (aus OTF konvertiert) = Hausschrift der Vorlagen.
    Blinker als Fallback für sehr fette Display-Zeilen."""
    converted = ASSETS / "fonts"
    to_register = [
        ("Fedra", converted / "Fedra-Book.ttf"),
        ("Fedra-Bold", converted / "Fedra-Bold.ttf"),
        ("Fedra-Medium", converted / "Fedra-Medium.ttf"),
        ("Fedra-Italic", converted / "Fedra-BookItalic.ttf"),
        ("Fedra-BoldItalic", converted / "Fedra-BoldItalic.ttf"),
        ("Fedra-Demi", converted / "Fedra-Demi.ttf"),
        ("Blinker", FONT_DIR / "Blinker-Regular.ttf"),
        ("Blinker-Bold", FONT_DIR / "Blinker-Bold.ttf"),
        ("Blinker-Black", FONT_DIR / "Blinker-Black.ttf"),
        ("Blinker-Semi", FONT_DIR / "Blinker-SemiBold.ttf"),
    ]
    for name, path in to_register:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            except Exception as e:
                print(f"Font skip {name}: {e}")

    names = set(pdfmetrics.getRegisteredFontNames())

    def pick(*candidates: str, fallback: str = "Helvetica") -> str:
        for c in candidates:
            if c in names:
                return c
        return fallback

    return {
        "Blinker": pick("Blinker", fallback="Helvetica"),
        "Blinker-Bold": pick("Blinker-Bold", "Fedra-Bold", fallback="Helvetica-Bold"),
        "Blinker-Black": pick("Fedra-Demi", "Blinker-Black", "Fedra-Bold", fallback="Helvetica-Bold"),
        "Blinker-Semi": pick("Fedra-Medium", "Blinker-Semi", fallback="Helvetica-Bold"),
        "Fedra": pick("Fedra", "Blinker", fallback="Helvetica"),
        "Fedra-Bold": pick("Fedra-Bold", "Blinker-Bold", fallback="Helvetica-Bold"),
        "Fedra-Medium": pick("Fedra-Medium", "Fedra-Demi", "Fedra-Bold", fallback="Helvetica-Bold"),
        "Fedra-Italic": pick("Fedra-Italic", fallback="Helvetica-Oblique"),
        "Fedra-BoldItalic": pick("Fedra-BoldItalic", "Fedra-Bold", fallback="Helvetica-BoldOblique"),
        "Fedra-Demi": pick("Fedra-Demi", "Fedra-Bold", fallback="Helvetica-Bold"),
    }


F = register_fonts()


def ensure_assets() -> None:
    """Portrait mit transparentem Kreisrand."""
    ASSETS.mkdir(exist_ok=True)
    sab_src = ASSETS / "digi_raw_0.png"
    if sab_src.exists():
        sab = PILImage.open(sab_src).convert("RGBA")
        w, h = sab.size
        mask = PILImage.new("L", (w, h), 0)
        ImageDraw.Draw(mask).ellipse([1, 1, w - 2, h - 2], fill=255)
        circ = PILImage.new("RGBA", (w, h), (0, 0, 0, 0))
        circ.paste(sab, (0, 0))
        circ.putalpha(mask)
        canvas_im = PILImage.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
        ImageDraw.Draw(canvas_im).ellipse([0, 0, w + 19, h + 19], outline=(0, 144, 224, 255), width=7)
        canvas_im.paste(circ, (10, 10), circ)
        canvas_im.save(ASSETS / "sabrina_ring.png")


LOGO_BZ = ASSETS / "logo_bz_norm.png"
LOGO_HK = ASSETS / "logo_hk_norm.png"


def draw_logo_image(c: canvas.Canvas, path: Path, cx: float, cy: float, r: float) -> None:
    """Offizielles Kreis-Logo als PNG (mit Transparenz), exakt r als Radius."""
    d = r * 2
    c.drawImage(
        str(path),
        cx - r,
        cy - r,
        width=d,
        height=d,
        mask="auto",
    )


def draw_logo_bz(c: canvas.Canvas, cx: float, cy: float, r: float) -> None:
    if LOGO_BZ.exists():
        draw_logo_image(c, LOGO_BZ, cx, cy, r)
        return
    c.setFillColor(BLUE)
    c.circle(cx, cy, r, fill=1, stroke=0)


def draw_logo_hk(c: canvas.Canvas, cx: float, cy: float, r: float) -> None:
    if LOGO_HK.exists():
        draw_logo_image(c, LOGO_HK, cx, cy, r)
        return
    c.setFillColor(MAGENTA)
    c.circle(cx, cy, r, fill=1, stroke=0)


def draw_logos(c: canvas.Canvas, mode: str) -> None:
    """mode: both | bz | hk — zentriert oben wie in der Vorlage."""
    y = PAGE_H - 26 * mm
    r = 11.5 * mm
    if mode == "both":
        # Gleich groß, nur leichte Überlappung (~2 mm); BZ liegt leicht über HK
        center_dist = 2 * r - 2.0 * mm
        draw_logo_hk(c, PAGE_W / 2 + center_dist / 2, y, r)
        draw_logo_bz(c, PAGE_W / 2 - center_dist / 2, y, r)
    elif mode == "bz":
        draw_logo_bz(c, PAGE_W / 2, y, r)
    else:
        draw_logo_hk(c, PAGE_W / 2, y, r)


def wrap_text(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_bullet(c: canvas.Canvas, x: float, y: float, r: float = 5.5) -> None:
    c.setFillColor(YELLOW)
    c.circle(x, y, r, fill=1, stroke=0)
    c.setFillColor(white)
    path = c.beginPath()
    path.moveTo(x - r * 0.25, y - r * 0.45)
    path.lineTo(x - r * 0.25, y + r * 0.45)
    path.lineTo(x + r * 0.55, y)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def draw_ribbon(c: canvas.Canvas, text: str, x: float, y: float, w: float = 62 * mm, h: float = 11 * mm) -> None:
    c.saveState()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(-8)
    c.setFillColor(YELLOW)
    c.roundRect(-w / 2, -h / 2, w, h, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(F["Fedra-Demi"], 11)
    c.drawCentredString(0, -3.2, text)
    c.restoreState()


def draw_price_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[str],
    *,
    compact: bool = False,
) -> None:
    c.setFillColor(YELLOW)
    c.roundRect(x, y, w, h, 3, fill=1, stroke=0)
    c.setFillColor(DARK)
    usable = [ln for ln in lines if ln]
    prices = [ln for ln in usable if not ln.startswith("zzgl")]
    mwst = next((ln for ln in usable if ln.startswith("zzgl")), None)
    max_tw = w - 6 * mm  # Innenabstand

    def fit_lines(text: str, font: str, size: float) -> tuple[list[str], float]:
        """Zeilen umbrechen und Schrift ggf. verkleinern, bis alles in die Box passt."""
        sz = size
        while sz >= 8:
            wrapped = wrap_text(c, text, font, sz, max_tw)
            if all(c.stringWidth(ln, font, sz) <= max_tw for ln in wrapped):
                return wrapped, sz
            sz -= 0.5
        return wrap_text(c, text, font, 8, max_tw), 8.0

    if compact:
        # DigiBeilage-Vorlage: Preise zentriert, MwSt kleiner unten rechts
        drawn: list[tuple[str, float, float]] = []  # text, size, line_h
        for ln in prices:
            parts, sz = fit_lines(ln, F["Fedra-Demi"], 11.5)
            lh = 5.2 * mm if sz >= 11 else 4.6 * mm
            for p in parts:
                drawn.append((p, sz, lh))
        total_h = sum(lh for _, _, lh in drawn)
        ty = y + h / 2 + total_h / 2 - 3.2 * mm
        for text, sz, lh in drawn:
            c.setFont(F["Fedra-Demi"], sz)
            c.drawCentredString(x + w / 2, ty, text)
            ty -= lh
        if mwst:
            c.setFont(F["Fedra"], 7.5)
            c.drawRightString(x + w - 3 * mm, y + 2.8 * mm, mwst)
        return

    drawn: list[tuple[str, str, float, float]] = []  # text, font, size, line_h
    for ln in usable:
        if ln.startswith("zzgl"):
            parts, sz = fit_lines(ln, F["Fedra"], 8)
            for p in parts:
                drawn.append((p, F["Fedra"], sz, 5.2 * mm))
        else:
            parts, sz = fit_lines(ln, F["Fedra-Demi"], 12.5)
            lh = 6.0 * mm if sz >= 11 else 4.8 * mm
            for p in parts:
                drawn.append((p, F["Fedra-Demi"], sz, lh))
    total_h = sum(lh for _, _, _, lh in drawn)
    ty = y + h / 2 + total_h / 2 - 3.8 * mm
    for text, font, sz, lh in drawn:
        c.setFont(font, sz)
        c.drawCentredString(x + w / 2, ty, text)
        ty -= lh


def price_box_height(c: canvas.Canvas, lines: list[str], box_w: float, *, compact: bool = False) -> float:
    """Mindesthöhe der Preisbox inkl. umgebrochener Zeilen."""
    usable = [ln for ln in lines if ln]
    max_tw = box_w - 6 * mm
    n = 0
    for ln in usable:
        if compact and ln.startswith("zzgl"):
            continue
        font = F["Fedra"] if ln.startswith("zzgl") else F["Fedra-Demi"]
        size = 8 if ln.startswith("zzgl") else (11.5 if compact else 12.5)
        # grob wie fit_lines
        sz = size
        while sz >= 8:
            wrapped = wrap_text(c, ln, font, sz, max_tw)
            if all(c.stringWidth(part, font, sz) <= max_tw for part in wrapped):
                n += len(wrapped)
                break
            sz -= 0.5
        else:
            n += len(wrap_text(c, ln, font, 8, max_tw))
    if compact:
        return max(24 * mm, 8 * mm + n * 5.2 * mm)
    return max(32 * mm, 10 * mm + n * 5.5 * mm)


def draw_header(c: canvas.Canvas, headline: str, sub: str, ribbon: str, logo_mode: str = "both") -> float:
    # Linker Balken durchgehend von oben bis unten (sichtbar, wie Vorlage)
    c.setFillColor(BLUE)
    c.rect(0, 0, 5 * mm, PAGE_H, fill=1, stroke=0)

    draw_logos(c, logo_mode)
    draw_ribbon(c, ribbon, PAGE_W - 72 * mm, PAGE_H - 30 * mm)

    y = PAGE_H - 48 * mm
    c.setFillColor(DARK)
    c.setFont(F["Fedra-Demi"], 16)
    for line in wrap_text(c, headline, F["Fedra-Demi"], 16, PAGE_W - 28 * mm):
        c.drawString(12 * mm, y, line)
        y -= 6.5 * mm

    c.setFont(F["Fedra-Italic"], 10.5)
    for line in wrap_text(c, sub, F["Fedra-Italic"], 10.5, PAGE_W - 28 * mm):
        c.drawString(12 * mm, y, line)
        y -= 4.8 * mm
    return y - 2.5 * mm


def draw_section_title(c: canvas.Canvas, text: str, y: float) -> float:
    c.setFillColor(DARK)
    c.setFont(F["Fedra-Demi"], 12)
    c.drawString(12 * mm, y, text.upper())
    return y - 6.5 * mm


def draw_bullets(
    c: canvas.Canvas,
    items: list[tuple[str, str]],
    y: float,
    max_width: float,
    x: float = 12 * mm,
) -> float:
    for title, body in items:
        draw_bullet(c, x + 3.5 * mm, y + 1.5)
        c.setFillColor(DARK)
        text = f"{title} {body}".strip()
        # bold title + regular body via two-pass draw if space
        c.setFont(F["Fedra-Bold"], 9.5)
        title_w = c.stringWidth(title + " ", F["Fedra-Bold"], 9.5)
        first_x = x + 10 * mm
        c.drawString(first_x, y, title)
        rest = body
        # first line after title
        c.setFont(F["Fedra"], 9.5)
        avail = max_width - title_w
        words = rest.split()
        cur = ""
        first_line_done = False
        line_y = y
        for w in words:
            test = (cur + " " + w).strip()
            limit = avail if not first_line_done else max_width
            if c.stringWidth(test, F["Fedra"], 9.5) <= limit:
                cur = test
            else:
                if not first_line_done:
                    c.drawString(first_x + title_w, line_y, cur)
                    first_line_done = True
                else:
                    c.drawString(first_x, line_y, cur)
                line_y -= 4.2 * mm
                cur = w
                avail = max_width
        if cur:
            if not first_line_done:
                c.drawString(first_x + title_w, line_y, cur)
            else:
                c.drawString(first_x, line_y, cur)
            line_y -= 4.2 * mm
        y = line_y - 2.8 * mm
    return y


def draw_intro(c: canvas.Canvas, text: str, y: float) -> float:
    c.setFillColor(GRAY)
    c.setFont(F["Fedra"], 9.5)
    for line in wrap_text(c, text, F["Fedra"], 9.5, PAGE_W - 24 * mm):
        c.drawString(12 * mm, y, line)
        y -= 4.4 * mm
    return y - 4 * mm


def draw_facts_table(c: canvas.Canvas, rows: list[tuple[str, str]], y: float) -> float:
    """Kleine Faktenzeilen unter dem Intro."""
    c.setFont(F["Fedra"], 8.5)
    for label, value in rows:
        c.setFillColor(BLUE)
        c.setFont(F["Fedra-Bold"], 8.5)
        c.drawString(12 * mm, y, label)
        c.setFillColor(DARK)
        c.setFont(F["Fedra"], 8.5)
        c.drawString(48 * mm, y, value)
        y -= 4.2 * mm
    return y - 3 * mm


def draw_footer(c: canvas.Canvas) -> None:
    # Wordmark als scharfer Vektortext (nicht als Rasterbild)
    c.setFillColor(DARK)
    c.setFont(F["Fedra-Demi"], 16)
    boehme = "Böhme"
    w1 = c.stringWidth(boehme, F["Fedra-Demi"], 16)
    c.setFont(F["Fedra"], 16)
    w2 = c.stringWidth("Zeitung", F["Fedra"], 16)
    x0 = PAGE_W / 2 - (w1 + w2) / 2
    c.setFont(F["Fedra-Demi"], 16)
    c.drawString(x0, 12 * mm, boehme)
    c.setFillColor(HexColor("#555555"))
    c.setFont(F["Fedra"], 16)
    c.drawString(x0 + w1, 12 * mm, "Zeitung")
    c.setFillColor(HexColor("#888888"))
    c.setFont(F["Fedra"], 7)
    c.drawCentredString(
        PAGE_W / 2,
        5 * mm,
        "Alle Preise zzgl. MwSt. · Stand: August 2026 · Mundschenk Nachrichtengesellschaft",
    )


def build_sheet(path: Path, data: dict) -> None:
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    y = draw_header(c, data["headline"], data["sub"], data["ribbon"], data.get("logo_mode", "both"))
    y = draw_intro(c, data["intro"], y)
    if data.get("facts"):
        y = draw_facts_table(c, data["facts"], y)

    y = draw_section_title(c, "IHRE VORTEILE AUF EINEN BLICK", y)
    y = draw_bullets(c, data["vorteile"], y, PAGE_W - 28 * mm)

    y -= 1 * mm
    y = draw_section_title(c, "IHR ANGEBOT", y)
    bullets_top = y

    offer_items = list(data["angebot"])
    # DigiBeilage: Preisbox wie Vorlage rechts neben den 3 Angebotspunkten (ohne Technik-Anhang)
    digi_layout = bool(data.get("digi_price_layout"))
    if data.get("technik") and not digi_layout:
        for t_title, t_body in data["technik"][:2]:
            offer_items.append((t_title, t_body))

    price_lines = [ln for ln in data["preise"] if ln]
    # Text endet klar vor der Preisbox (draw_bullets startet bei x+10mm)
    text_left = 12 * mm + 10 * mm
    box_gap = 18 * mm

    if digi_layout:
        box_w = 55 * mm
        box_h = price_box_height(c, data["preise"], box_w, compact=True)
        box_x = PAGE_W - 12 * mm - box_w
        offer_width = box_x - box_gap - text_left
        y_after = draw_bullets(c, offer_items, y, offer_width)
        # Kasten vertikal mittig neben dem Angebot-Block (wie DigiBeilage-Vorlage)
        block_top = bullets_top + 2 * mm
        block_bottom = y_after
        box_y = (block_top + block_bottom) / 2 - box_h / 2
        draw_price_box(c, box_x, box_y, box_w, box_h, data["preise"], compact=True)
        y = min(y_after, box_y) - 5 * mm
    else:
        box_w = 52 * mm
        box_h = price_box_height(c, data["preise"], box_w)
        box_x = PAGE_W - 10 * mm - box_w
        box_y = y - box_h + 2 * mm
        draw_price_box(c, box_x, box_y, box_w, box_h, data["preise"])
        offer_width = box_x - box_gap - text_left
        y_after = draw_bullets(c, offer_items, y, offer_width)
        y = min(y_after, box_y) - 5 * mm

    if data.get("ideal"):
        c.setFillColor(DARK)
        c.setFont(F["Blinker-Bold"], 9.5)
        c.drawString(12 * mm, y, "Ideal für: ")
        label_w = c.stringWidth("Ideal für: ", F["Blinker-Bold"], 9.5)
        c.setFillColor(GRAY)
        c.setFont(F["Fedra"], 9.5)
        ideal_lines = wrap_text(c, data["ideal"], F["Fedra"], 9.5, PAGE_W - 24 * mm - label_w)
        if ideal_lines:
            c.drawString(12 * mm + label_w, y, ideal_lines[0])
            y -= 4.2 * mm
            for line in ideal_lines[1:]:
                c.drawString(12 * mm, y, line)
                y -= 4.2 * mm

    # Ansprechpartner bewusst leer lassen (Platzhalter für spätere Ergänzung)
    draw_footer(c)
    c.save()
    print(f"Created: {path}")


PRODUCTS: list[dict] = [
    {
        "file": "01_Interstitial.pdf",
        "logo_mode": "both",
        "headline": "MAXIMALE AUFMERKSAMKEIT IM E-PAPER",
        "sub": "IHRE WERBUNG ALS VOLLBILD-SEITE MITTEN IM LESEFLUSS",
        "ribbon": "UNÜBERSEHBAR!",
        "intro": (
            "Mit dem Interstitial erscheint Ihre Werbung als eigene Vollseite direkt beim Blättern "
            "im E-Paper von Böhme-Zeitung und Heide-Kurier. Kein Randformat, kein Mitbewerb auf der Seite – "
            "volle Bildschirmfläche für Events, Image und starke Aktionen."
        ),
        "facts": [
            ("Kanal", "E-Paper BZ & HK (einzeln oder kombiniert)"),
            ("Reichweite", "1.400+ Besuche/Tag · Ø 15 Min. Lesedauer · 78 % Stammleser"),
            ("Laufzeit", "ab 1 Woche · auch in Archivausgaben im Buchungszeitraum"),
        ],
        "vorteile": [
            ("Volle Bildschirmfläche:", "Exklusive Seite im Lesefluss – Leser sind aufmerksam beim Blättern."),
            ("Bestehendes Motiv reicht:", "Print-PDF oft ausreichend, schnell umsetzbar."),
            ("Hohe Verweildauer:", "E-Paper-Leser verbringen Ø 15 Minuten in der Ausgabe."),
            ("Lokal & treu:", "78 % Stammleser (Abonnenten) im Heidekreis – keine Streuverluste."),
        ],
        "angebot": [
            ("Platzierung:", "Eigene Vollseite beim Blättern im E-Paper."),
            ("Titel:", "BZ, HK oder beide kombiniert."),
            ("Anlieferung:", "PDF, JPG oder PNG · mind. 150 dpi · max. 10 MB."),
        ],
        "preise": ["ab 299,– €", "pro Woche", "zzgl. 19% MwSt"],
        "technik": [
            ("Format:", "Vollseite (PDF oder Bild), mind. 150 dpi, max. 10 MB."),
        ],
        "ideal": "Events, Eröffnungen, Image-Kampagnen, kurzfristige Vollsichtbarkeit.",
    },
    {
        "file": "02_E-Paper-Banner.pdf",
        "logo_mode": "both",
        "headline": "IHR BANNER AM EINGANGSTOR ZUM E-PAPER",
        "sub": "FESTE POSITION AUF DER STARTSEITE – JEDER LESER SIEHT ES",
        "ribbon": "GÜNSTIGER EINSTIEG!",
        "intro": (
            "Das E-Paper-Banner steht fest unterhalb der aktuellen Ausgaben auf der Startseite. "
            "Bevor Leser eine Ausgabe öffnen, sehen sie Ihr Motiv – günstigstes E-Paper-Format "
            "mit hoher Frequenz für Aktionen, Events und Imagewerbung."
        ),
        "facts": [
            ("Kanal", "E-Paper-Startseite BZ & HK"),
            ("Reichweite", "9.000+ Besuche/Woche · 90 % sehen das Banner vollständig"),
            ("Laufzeit", "ab 1 Woche"),
        ],
        "vorteile": [
            ("Feste Position:", "Kein Wegscrollen – sichtbar vor dem Öffnen der Ausgabe."),
            ("Günstigster Einstieg:", "Starkes Preis-Leistungs-Verhältnis im E-Paper."),
            ("Beide Marken:", "Für BZ- und HK-Leser gleichermaßen sichtbar."),
            ("Schnell buchbar:", "Ideal für Saisonangebote und kurze Aktionen."),
        ],
        "angebot": [
            ("Platzierung:", "Fest auf der E-Paper-Startseite."),
            ("Anlieferung:", "JPG, PNG oder WebP · max. 5 MB je Datei."),
            ("Pflicht:", "Alle drei Varianten (Desktop, Handy, Tablet)."),
        ],
        "preise": ["199,– €", "pro Woche", "zzgl. 19% MwSt"],
        "technik": [
            ("Desktop:", "2.048 × 400 px"),
            ("Handy:", "1.024 × 400 px"),
            ("Tablet:", "2.880 × 400 px"),
        ],
        "ideal": "Aktionen, Events, Image, Saisonangebote – wenn Sichtbarkeit vor dem Lesen zählt.",
    },
    {
        "file": "03_Digitale-Beilage.pdf",
        "logo_mode": "both",
        "digi_price_layout": True,
        "headline": "IHRE PRINT-BEILAGE AUCH IM E-PAPER",
        "sub": "DIGITALER ZUSATZ ZUR GEDRUCKTEN BEILAGE – GLEICHES PDF, MEHR REICHWEITE",
        "ribbon": "ZUR PRINT-BEILAGE!",
        "intro": (
            "Buchen Sie die digitale Beilage idealerweise zusätzlich zur gedruckten Beilage: "
            "derselbe Prospekt erscheint prominent auf der E-Paper-Startseite – blätterbar, "
            "aufmerksamkeitsstark und ohne Extra-Layout. So erreichen Sie Haushalte in Print "
            "und unsere E-Paper-Leser aus einer Hand."
        ),
        "facts": [
            ("Kanal", "E-Paper-Startseite BZ & HK"),
            ("Reichweite", "9.000+ Startseitenbesuche/Woche"),
            ("Buchung", "Zusätzlich zur Print-Beilage (gleicher Prospekt)"),
        ],
        "vorteile": [
            ("Crossmedia aus einer Hand:", "Print-Beilage plus digitale Verlängerung – ein Motiv, zwei Kanäle."),
            ("Sofort im Blick:", "Zentral und unübersehbar auf der E-Paper-Startseite."),
            ("Kein Extra-Layout:", "Dasselbe PDF wie zum Druck – Format flexibel."),
            ("Nahtloses Leseerlebnis:", "Auf Wunsch direkt an die Tagesausgabe anhängbar."),
        ],
        "angebot": [
            ("Zur Print-Beilage dazu buchen", "und denselben Prospekt auch digital auf der Startseite zeigen."),
            ("Platzierung zentral", "auf der E-Paper-Startseite inkl. Anhang an die Tagesausgabe."),
            ("Einfache Anlieferung:", "Wir benötigen nur Ihr Druck-PDF."),
        ],
        "preise": ["210,– € für 1 Woche", "310,– € für 2 Wochen", "zzgl. 19% MwSt"],
        "ideal": "Gedruckte Beilagen, Prospekte und Kataloge – digital verlängern und Reichweite erhöhen.",
    },
    {
        "file": "04_Raetsel-Seite.pdf",
        "logo_mode": "bz",
        "headline": "10 MINUTEN BLICKKONTAKT PRO LESER",
        "sub": "IHRE ANZEIGE MITTEN IM KREUZWORTRÄTSEL – PRINT & E-PAPER",
        "ribbon": "NUR BÖHME-ZEITUNG!",
        "intro": (
            "Die Rätsel-Seite ist die Premium-Platzierung mit der höchsten Verweildauer: "
            "Ihre Anzeige steht mitten im Kreuzworträtsel-Spielfeld – täglich Mo–Sa in Print "
            "und E-Paper der Böhme-Zeitung. Ideal für Vertrauensprodukte und die Zielgruppe 50+."
        ),
        "facts": [
            ("Kanal", "nur Böhme-Zeitung · Print + E-Paper"),
            ("Reichweite", "900–1.300 Rätsel-Aufrufe/Tag im E-Paper"),
            ("Formate", "Woche 75×83 mm · Wochenende 82×90 mm"),
        ],
        "vorteile": [
            ("Höchste Verweildauer:", "~10 Minuten aktive Aufmerksamkeit – kein flüchtiges Scrollen."),
            ("Print + Digital:", "Ein Buchungsvorgang für Zeitung und E-Paper."),
            ("Konzentrierte Leser:", "Rätseln heißt: Zeit, Fokus, lokale Stammleser."),
            ("Premium-Umfeld:", "Ein Platz im Spielfeld – kein Mitbewerber daneben."),
        ],
        "angebot": [
            ("Platzierung:", "Mitten im Kreuzworträtsel, Mo–Sa."),
            ("Titel:", "Nur Böhme-Zeitung (nicht HK allein)."),
            ("Anlieferung:", "Druckdaten wie Print-Anzeige."),
        ],
        "preise": ["495,– €", "pro Woche", "zzgl. 19% MwSt"],
        "technik": [
            ("Woche:", "75 × 83 mm"),
            ("Wochenende:", "82 × 90 mm"),
        ],
        "ideal": "Bank, Pflege, Optik/Hören, Apotheke, Image, Arbeitgeber, komplexe Erklärprodukte.",
    },
    {
        "file": "05_Klickbare-Anzeige.pdf",
        "logo_mode": "both",
        "headline": "PRINT WIRD MESSBAR – FÜR NUR 29 EURO",
        "sub": "IHRE PRINT-ANZEIGE IM E-PAPER KLICKBAR MACHEN",
        "ribbon": "DER UPSELL!",
        "intro": (
            "Jede Print-Anzeige erscheint automatisch auch im E-Paper. Mit dem Aufpreis "
            "„Klickbare Anzeige“ erhält sie ein klickbares Symbol, das auf mehr Informationen verlinkt – "
            "direkt zu Shop, Terminbuchung, Stellenanzeige oder Aktionsseite."
        ),
        "facts": [
            ("Kanal", "E-Paper BZ oder HK (Add-on zur Print-Inseration)"),
            ("Voraussetzung", "bestehende Print-Anzeige"),
            ("Kunde liefert", "nur die Ziel-URL – kein Extra-Motiv"),
        ],
        "vorteile": [
            ("Minimaler Aufwand:", "Kein neues Motiv, kein separater Auftrag."),
            ("Sofort messbar:", "Print-Reichweite plus digitale Klicks."),
            ("Perfekter Upsell:", "Bei jeder Print-Buchung mitdenken."),
            ("Vielseitig:", "Ideal für Stellen, Aktionen, Events, Shops."),
        ],
        "angebot": [
            ("Funktion:", "Klickbares Symbol auf der Anzeige → Link zu mehr Informationen."),
            ("Anlieferung:", "Nur funktionierende Ziel-URL (https://…)."),
            ("Umsetzung:", "Wir verlinken Ihre bestehende Print-Anzeige im E-Paper."),
        ],
        "preise": ["+ 29,– €", "pro Inseration", "zzgl. 19% MwSt"],
        "technik": [
            ("Wichtig:", "URL mobil gut lesbar; Landingpage sollte laden."),
        ],
        "ideal": "Jeder Print-Kunde – besonders Stellenanzeigen, Aktionen, Terminbuchung, Online-Shop.",
    },
    {
        "file": "06_Premiumbanner.pdf",
        "logo_mode": "hk",
        "headline": "DER ERSTE BLICK AUF HEIDE-KURIER.DE",
        "sub": "EXKLUSIVES STARTSEITEN-BANNER – MAXIMALE SICHTBARKEIT",
        "ribbon": "STARTSEITE!",
        "intro": (
            "Das Premiumbanner steht prominent auf der Startseite von heide-kurier.de – "
            "der erste Blick jedes Besuchers. Ideal für kurze, intensive Aktionen: "
            "Wochenende, Event, Sale. Ad-Blocker-resistent, lokal, mit Reporting auf Wunsch."
        ),
        "facts": [
            ("Kanal", "heide-kurier.de Startseite"),
            ("Reichweite", "~1.450 Besuche/Tag · 18.600+ Nutzer/Monat"),
            ("Kontaktpreis", "~3,4 Cent pro lokalem Besuch (50 € ÷ 1.450)"),
        ],
        "vorteile": [
            ("Maximale Sichtbarkeit:", "Exklusive Startseiten-Position."),
            ("Ad-Blocker-resistent:", "Banner bleibt sichtbar."),
            ("Kurz & intensiv:", "Ab 1 Tag buchbar – perfekt für Events."),
            ("Lokal & präzise:", "100 % Heidekreis, keine Streuverluste."),
        ],
        "angebot": [
            ("Platzierung:", "Exklusiv auf der Startseite heide-kurier.de."),
            ("Laufzeit:", "Frei wählbar, Mindestbuchung 1 Tag."),
            ("Pflicht:", "Mobile- und Desktop-Version."),
        ],
        "preise": ["50,– €", "pro Tag", "zzgl. 19% MwSt"],
        "technik": [
            ("Mobile:", "1.758 × 480 px (mind. 586 × 160)"),
            ("Desktop:", "2.820 × 480 px (mind. 940 × 160)"),
            ("Datei:", "GIF/JPG/PNG · sRGB · 72 dpi · max. 2 MB"),
        ],
        "ideal": "Event-Wochenenden, Sale-Starts, Produktlaunches, starke Kurzaktionen.",
    },
    {
        "file": "07_Standardbanner.pdf",
        "logo_mode": "hk",
        "headline": "FLEXIBEL BUCHEN – PRO SICHTBAREM KONTAKT",
        "sub": "BANNER IN ARTIKELN AUF HEIDE-KURIER.DE",
        "ribbon": "AB 150 €!",
        "intro": (
            "Das Standardbanner erscheint in redaktionellen Artikeln auf heide-kurier.de. "
            "Abgerechnet wird nur die sichtbare Einblendung (0,03 €) – Budget und Laufzeit "
            "legen Sie fest. Einstieg ab 150 € (5.000 Einblendungen), volle Kontrolle, lokale Nachrichtenleser."
        ),
        "facts": [
            ("Kanal", "heide-kurier.de · in Artikeln"),
            ("Abrechnung", "0,03 € / sichtbare Einblendung (CPM)"),
            ("Minimum", "ab 150 € · 5.000 Einblendungen"),
        ],
        "vorteile": [
            ("Volle Budgetkontrolle:", "Sie bestimmen Volumen und Laufzeit."),
            ("Sichtbare Kontakte:", "Gezählt wird nur, was wirklich im Blickfeld war."),
            ("Lesekontext:", "Banner mitten in lokalen Nachrichten."),
            ("Klarer Einstieg:", "Ab 150 € für 5.000 lokale Einblendungen."),
        ],
        "angebot": [
            ("Platzierung:", "In redaktionellen Artikeln auf heide-kurier.de."),
            ("Budget:", "Ab 150 € – Auslieferung wird entsprechend dosiert."),
            ("Anlieferung:", "Ein Banner-Motiv (GIF/JPG/PNG)."),
        ],
        "preise": ["0,03 €", "pro sichtbare Einblendung", "zzgl. 19% MwSt"],
        "technik": [
            ("Rechnung:", "5.000 = 150 € · 10.000 = 300 € · 20.000 = 600 €"),
            ("Format:", "1.440 × 600 px (mind. 720 × 300) · GIF/JPG/PNG · max. 2 MB"),
        ],
        "ideal": "Dauerhafte Präsenz, planbares Mindestbudget, Testkampagnen, thematische Artikelumfelder.",
    },
    {
        "file": "08_Native-Ad.pdf",
        "logo_mode": "hk",
        "headline": "IHRE MARKE ALS LOKALE GESCHICHTE",
        "sub": "GESPONSERTER ARTIKEL AUF HEIDE-KURIER.DE",
        "ribbon": "BLEIBT ONLINE!",
        "intro": (
            "Der gesponserte Artikel (Native Ad) erzählt Ihre Story im redaktionellen Umfeld: "
            "Teaser auf der Startseite plus ausführlicher Artikel mit Bildern. "
            "Glaubwürdig, SEO-relevant und klar als Werbung gekennzeichnet. "
            "Die Platzierung läuft vier Wochen – der Artikel bleibt danach online und auffindbar."
        ),
        "facts": [
            ("Kanal", "heide-kurier.de · Teaser + Artikel"),
            ("Laufzeit", "vier Wochen"),
            ("Umsetzung", "Gestaltung & Texthilfe kostenlos auf Anfrage"),
        ],
        "vorteile": [
            ("Mehr Aufmerksamkeit:", "Storytelling statt flüchtigem Banner."),
            ("Bleibt auffindbar:", "Artikel bleibt auch nach der Platzierung online und über Google erreichbar."),
            ("Vertrauen:", "Ideal für komplexe Leistungen und Markenaufbau."),
            ("Wenig Aufwand:", "Fotos und Stichpunkte reichen – wir setzen um."),
        ],
        "angebot": [
            ("Aufbau:", "Teaser auf Startseite + ausführlicher Artikel."),
            ("Laufzeit:", "vier Wochen"),
            ("Kennzeichnung:", "Klar als „gesponserter Artikel“."),
            ("Kunde liefert:", "Thema, 3–6 Bilder, Kontaktdaten, Ziel-URL(s)."),
        ],
        "preise": ["ab 249,– €", "pro Artikel", "zzgl. 19% MwSt"],
        "technik": [
            ("Titelbild:", "910 × 339 px"),
            ("Textbild:", "880 × 660 px · 1 Titelbild + 2–5 Textbilder"),
            ("Text:", "Überschrift max. ~70 Zeichen · 400–800 Wörter oder Stichpunkte"),
        ],
        "ideal": "Jubiläen, Recruiting, Handwerk/Bau, Beratung, Markenaufbau, Vertrauensprodukte.",
    },
]


def main() -> None:
    ensure_assets()
    OUT.mkdir(exist_ok=True)
    for product in PRODUCTS:
        build_sheet(OUT / product["file"], product)
    # Sammel-PDF
    try:
        import fitz

        merger = fitz.open()
        for product in PRODUCTS:
            merger.insert_file(str(OUT / product["file"]))
        all_path = OUT / "00_Alle_Online-Produkte_Einseiter.pdf"
        merger.save(str(all_path))
        merger.close()
        print(f"Created: {all_path}")
    except Exception as e:
        print("Sammel-PDF übersprungen:", e)


if __name__ == "__main__":
    main()
