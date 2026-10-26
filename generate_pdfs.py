#!/usr/bin/env python3
"""Generate print-ready PDFs from Online-Werbung sales materials."""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).parent
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# Brand colors
COLOR_PRIMARY = (0, 82, 120)
COLOR_ACCENT = (200, 80, 30)
COLOR_LIGHT = (245, 247, 250)
COLOR_TEXT = (30, 30, 30)
COLOR_MUTED = (100, 100, 100)


class SalesPDF(FPDF):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("Arial", "", FONT_REG)
        self.add_font("Arial", "B", FONT_BOLD)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "B", 8)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 8, self.doc_title, align="L")
        self.cell(0, 8, f"Seite {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "", 7)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 8, "Alle Preise zzgl. MwSt. · Stand: Juli 2026 · Mundschenk Nachrichtengesellschaft", align="C")

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 55, style="F")
        self.set_y(18)
        self.set_font("Arial", "B", 22)
        self.set_text_color(255, 255, 255)
        self.multi_cell(0, 10, self.doc_title, align="L")
        if self.doc_subtitle:
            self.ln(2)
            self.set_font("Arial", "", 12)
            self.multi_cell(0, 7, self.doc_subtitle, align="L")
        self.ln(20)
        self.set_text_color(*COLOR_TEXT)
        self.set_font("Arial", "", 10)
        self.multi_cell(
            0,
            6,
            "Verkaufsunterlage für Außendienst und Werbeberatung\n"
            "Böhme-Zeitung E-Paper · Heide-Kurier Online",
        )
        self.ln(8)
        self.set_font("Arial", "B", 10)
        self.set_text_color(*COLOR_ACCENT)
        self.cell(0, 8, "Intern · Nur für Mitarbeitende", new_x="LMARGIN", new_y="NEXT")

    def h1(self, text: str):
        self.ln(4)
        self.set_font("Arial", "B", 14)
        self.set_text_color(*COLOR_PRIMARY)
        self.multi_cell(0, 8, self.clean(text))
        self.set_draw_color(*COLOR_PRIMARY)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(5)

    def h2(self, text: str):
        self.ln(3)
        self.set_font("Arial", "B", 11)
        self.set_text_color(*COLOR_PRIMARY)
        self.multi_cell(0, 7, self.clean(text))
        self.ln(2)

    def h3(self, text: str):
        self.ln(2)
        self.set_font("Arial", "B", 10)
        self.set_text_color(*COLOR_TEXT)
        self.multi_cell(0, 6, self.clean(text))
        self.ln(1)

    def paragraph(self, text: str):
        if not text.strip():
            return
        self.set_font("Arial", "", 9)
        self.set_text_color(*COLOR_TEXT)
        self.multi_cell(0, 5, self.clean(text))
        self.ln(2)

    def quote(self, text: str):
        self.set_fill_color(*COLOR_LIGHT)
        self.set_font("Arial", "", 9)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_x(14)
        self.multi_cell(182, 5, self.clean(text), fill=True)
        self.ln(3)

    def bullet(self, text: str, indent: int = 0):
        self.set_font("Arial", "", 9)
        self.set_text_color(*COLOR_TEXT)
        x = 12 + indent
        self.set_x(x)
        self.cell(4, 5, "-")
        self.multi_cell(190 - indent, 5, self.clean(text))
        self.ln(1)

    def checkbox(self, text: str):
        self.set_font("Arial", "", 9)
        self.set_x(12)
        self.cell(5, 5, "[ ]")
        self.multi_cell(183, 5, self.clean(text))
        self.ln(1)

    def _split_lines(self, text: str, width_mm: float, bold: bool = False) -> list[str]:
        self.set_font("Arial", "B" if bold else "", 8)
        if not text:
            return [""]
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.get_string_width(test) <= width_mm:
                current = test
            else:
                if current:
                    lines.append(current)
                if self.get_string_width(word) > width_mm:
                    # Einzelnes Wort breiter als Spalte: trotzdem übernehmen
                    lines.append(word)
                    current = ""
                else:
                    current = word
        if current:
            lines.append(current)
        return lines or [""]

    def render_table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        if not rows:
            return

        n = len(headers)
        if col_widths is None:
            total = 190
            col_widths = [total // n] * n
            col_widths[-1] = total - sum(col_widths[:-1])

        line_h = 4.5
        x0 = 10
        all_rows = [headers] + rows

        for row_idx, row in enumerate(all_rows):
            if self.get_y() > 250:
                self.add_page()

            is_header = row_idx == 0
            cell_lines: list[list[str]] = []
            max_lines = 1

            for i, cell in enumerate(row):
                lines = self._split_lines(self.clean(cell), col_widths[i] - 3, bold=is_header)
                cell_lines.append(lines)
                max_lines = max(max_lines, len(lines))

            row_h = max(max_lines * line_h + 3, 7)
            y0 = self.get_y()

            for i, lines in enumerate(cell_lines):
                x = x0 + sum(col_widths[:i])
                w = col_widths[i]

                if is_header:
                    self.set_fill_color(*COLOR_PRIMARY)
                    self.set_text_color(255, 255, 255)
                    self.set_font("Arial", "B", 8)
                    style = "DF"
                else:
                    if row_idx % 2 == 0:
                        self.set_fill_color(*COLOR_LIGHT)
                        style = "DF"
                    else:
                        self.set_fill_color(255, 255, 255)
                        style = "D"
                    self.set_text_color(*COLOR_TEXT)
                    self.set_font("Arial", "", 8)

                self.rect(x, y0, w, row_h, style=style)
                text_y = y0 + 1.5
                for line in lines:
                    self.set_xy(x + 1.5, text_y)
                    self.cell(w - 3, line_h, line)
                    text_y += line_h

            self.set_xy(x0, y0 + row_h)

        self.ln(3)

    def code_block(self, text: str):
        self.set_fill_color(248, 248, 248)
        self.set_font("Arial", "", 7.5)
        self.set_text_color(*COLOR_TEXT)
        for line in text.splitlines():
            self.set_x(12)
            self.cell(186, 4, line[:110], fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def hr(self):
        self.ln(2)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def clean(self, text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = text.replace("→", "->")
        text = text.replace("·", " - ")
        text = text.replace("€", " EUR")
        text = text.replace("–", "-")
        text = text.replace("—", "-")
        text = text.replace("\u201e", '"').replace("\u201c", '"').replace("\u201a", "'")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u2026", "...")
        return text.strip()


def table_col_widths(num_cols: int, kind: str = "default") -> list[int]:
    presets = {
        2: [55, 135],
        3: [45, 55, 90],
        4: {
            "default": [32, 38, 52, 68],
            "products": [34, 28, 38, 90],
            "compare": [30, 38, 38, 84],
        },
        5: {
            "default": [34, 48, 32, 28, 48],
            "specs": [32, 50, 30, 26, 52],
        },
    }
    if num_cols == 4 and kind in presets[4]:
        return presets[4][kind]
    if num_cols == 5:
        return presets[5].get(kind, presets[5]["default"])
    if num_cols in presets and not isinstance(presets[num_cols], dict):
        return presets[num_cols]
    w = 190 // num_cols
    return [w] * num_cols


def detect_table_kind(headers: list[str]) -> str:
    joined = " ".join(headers).lower()
    if "was der kunde" in joined or "besonderheit" in joined:
        return "specs"
    if "produkt" in joined:
        return "products"
    if "print" in joined or "facebook" in joined:
        return "compare"
    return "default"


def parse_markdown_table(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    if len(lines) < 2:
        return None
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        if not line.strip().startswith("|"):
            break
        rows.append([c.strip() for c in line.strip("|").split("|")])

    # Key-Value-Tabellen normalisieren: | | | mit 2-spaltigen Daten -> 2 Spalten
    if rows and len(headers) != len(rows[0]):
        if all(h == "" for h in headers) and len(rows[0]) == 2:
            headers = ["", ""]
        elif headers and headers[0] == "" and len(headers) > len(rows[0]):
            headers = headers[: len(rows[0])]

    # Zeilen auf Header-Spaltenanzahl auffüllen oder kürzen
    width = len(headers)
    rows = [(row + [""] * width)[:width] for row in rows]
    return headers, rows


def markdown_to_pdf(
    md_path: Path,
    pdf_path: Path,
    title: str,
    subtitle: str = "",
    with_cover: bool = True,
    skip_intro: bool = True,
):
    content = md_path.read_text(encoding="utf-8")
    pdf = SalesPDF(title, subtitle)
    skip_until_section = False
    if with_cover:
        pdf.cover_page()
        pdf.add_page()  # Inhalt beginnt sauber auf Seite 2
        skip_until_section = skip_intro
    else:
        pdf.add_page()

    lines = content.splitlines()
    i = 0
    in_code = False
    code_lines: list[str] = []
    table_lines: list[str] = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                pdf.code_block("\n".join(code_lines))
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Deckblatt-Metadaten überspringen (Titel, Untertitel, Stand, Quellen)
        if skip_until_section:
            if line.startswith("## ") and re.match(r"## \d+\.", line):
                skip_until_section = False
            else:
                i += 1
                continue

        if line.strip().startswith("|"):
            table_lines.append(line)
            i += 1
            if i >= len(lines) or not lines[i].strip().startswith("|"):
                parsed = parse_markdown_table(table_lines)
                if parsed:
                    headers, rows = parsed
                    if len(headers) == 2 and headers[0] == "":
                        pdf.render_table(["", ""], rows, [55, 135])
                    else:
                        kind = detect_table_kind(headers)
                        pdf.render_table(headers, rows, table_col_widths(len(headers), kind))
                table_lines = []
            continue

        if line.strip() == "---":
            pdf.hr()
            i += 1
            continue

        if line.startswith("# "):
            i += 1
            continue  # Titel nur auf dem Deckblatt
        elif line.startswith("## "):
            pdf.h2(line[3:])
        elif line.startswith("### "):
            # Kundenblöcke in Cross-Sell-Dokument: optional Seitenumbruch
            if pdf.get_y() > 220 and "Cross-Selling" in pdf.doc_title:
                pdf.add_page()
            pdf.h3(line[4:])
        elif line.startswith("> "):
            pdf.quote(line[2:])
        elif re.match(r"^- \[ \] ", line):
            pdf.checkbox(line[6:])
        elif line.startswith("- "):
            pdf.bullet(line[2:])
        elif re.match(r"^\d+\.\s", line):
            pdf.bullet(re.sub(r"^\d+\.\s", "", line), indent=2)
        elif line.strip() and not line.startswith("#"):
            pdf.paragraph(line)

        i += 1

    pdf.output(str(pdf_path))
    print(f"Created: {pdf_path}")


def main():
    docs = [
        (
            ROOT / "Verkaufsunterlage_Online-Werbung.md",
            ROOT / "Verkaufsunterlage_Online-Werbung.pdf",
            "Online-Werbung",
            "Vollständige Verkaufsunterlage",
            True,
            True,
        ),
        (
            ROOT / "Verkaufsunterlage_Online-Werbung_Kurzversion.md",
            ROOT / "Verkaufsunterlage_Online-Werbung_Kurzversion.pdf",
            "Online-Werbung – Kurzversion",
            "Spickzettel für den Außendienst",
            True,
            False,
        ),
        (
            ROOT / "Schulungsskript_Online-Werbung.md",
            ROOT / "Schulungsskript_Online-Werbung.pdf",
            "Schulungsskript Online-Werbung",
            "Intern · Dauer ca. 60-75 Minuten",
            True,
            False,
        ),
        (
            ROOT / "Einwand-Karte_Zahlen-zu-niedrig.md",
            ROOT / "Einwand-Karte_Zahlen-zu-niedrig.pdf",
            "Einwand-Karte: Die Zahlen sind zu niedrig",
            "HK-Online · 1 Seite · Handout fuer den Aussendienst",
            False,
            False,
        ),
        (
            ROOT / "CrossSell_50_Online-Angebote.md",
            ROOT / "CrossSell_50_Online-Angebote.pdf",
            "Cross-Selling Online-Werbung",
            "50 individuelle Kundenangebote",
            True,
            False,
        ),
        (
            ROOT / "CrossSell_50_Print-Online-Verknuepfung.md",
            ROOT / "CrossSell_50_Print-Online-Verknuepfung.pdf",
            "Cross-Selling Print + Online",
            "50 verknuepfte Kundenangebote - Online on top",
            True,
            False,
        ),
        (
            ROOT / "Raetselseite_Zielkunden_Argumente.md",
            ROOT / "Raetselseite_Zielkunden_Argumente.pdf",
            "Rätsel-Seite BZ: Zielkunden",
            "62 Kunden mit individueller Argumentation",
            True,
            False,
        ),
        (
            ROOT / "Technische_Erfordernisse_Online-Werbeprodukte.md",
            ROOT / "Technische_Erfordernisse_Online-Werbeprodukte.pdf",
            "Technische Erfordernisse",
            "Online-Werbeprodukte · Specs für Verkäufer",
            True,
            True,
        ),
        (
            ROOT / "Einseiter_Handel_Erfolg_HK.md",
            ROOT / "Einseiter_Handel_Erfolg_HK.pdf",
            "Handel-Erfolg · Heide-Kurier",
            "1-Pager Außendienst · Leitprodukte Kompakt & Plus Monat",
            False,
            False,
        ),
        (
            ROOT / "Einseiter_Handel_Erfolg_BZ.md",
            ROOT / "Einseiter_Handel_Erfolg_BZ.pdf",
            "Handel-Erfolg · Böhme-Zeitung",
            "1-Pager Außendienst · Leitprodukte Kompakt & Plus Monat",
            False,
            False,
        ),
        (
            ROOT / "Handel_Erfolg_Pakete.md",
            ROOT / "Handel_Erfolg_Pakete.pdf",
            "Handel-Erfolg-Pakete",
            "Standardisierte Pakete HK & BZ · KR live",
            True,
            False,
        ),
        (
            ROOT / "Handel_Erfolg_Pipedrive_Produkte.md",
            ROOT / "Handel_Erfolg_Pipedrive_Produkte.pdf",
            "Pipedrive-Produkte · Handel-Erfolg",
            "Angebotstexte zum Anlegen · Leit- und Upsell-Produkte",
            True,
            False,
        ),
        (
            ROOT / "Einseiter_Handel_Erfolg_Kombi.md",
            ROOT / "Einseiter_Handel_Erfolg_Kombi.pdf",
            "Handel-Erfolg · Kombi BZ + HK",
            "1-Pager Außendienst · Start Kombi & Plus Dauer Kombi",
            False,
            False,
        ),
    ]

    for md, pdf, title, subtitle, cover, skip_intro in docs:
        if not md.exists():
            print(f"Skip (missing): {md}")
            continue
        markdown_to_pdf(md, pdf, title, subtitle, cover, skip_intro)


if __name__ == "__main__":
    main()
