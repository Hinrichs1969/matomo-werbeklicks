# -*- coding: utf-8 -*-
"""IDML-Generator: Layout/Typo an PDF-Einseiter (Fedra) angleichen.

Textrahmen: Original-Frame uee der Adobe-Vorlage klonen/skalieren
(nicht von Grund auf neu bauen), sonst bleibt Text in InDesign 2025 leer.
"""

from __future__ import annotations

import math
import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from generate_einseiter import ASSETS, LOGO_BZ, LOGO_HK, PRODUCTS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Einseiter_Online-Produkte" / "InDesign"
LINKS = OUT / "Links"
TEMPLATE = ASSETS / "idml_base" / "template_business_card.idml"
MM = 2.834645669291339
PAGE_W = 210 * MM
PAGE_H = 340 * MM

# Wie PDF-Einseiter (Fedra Sans Std liegt in ~/Library/Fonts)
FONT = "Fedra Sans Std"
DARK = "Color/WZ_Dunkel"
BLUE = "Color/WZ_Blau"
YELLOW = "Color/WZ_Gelb"
WHITE = "Color/Paper"


def esc(text: str) -> str:
    return escape(text)


def spread_y(page_y: float) -> float:
    return page_y - PAGE_H / 2


def load_template() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(TEMPLATE) as zf:
        for name in zf.namelist():
            files[name] = zf.read(name)
    return files


def patch_page_size(files: dict[str, bytes]) -> None:
    pref = files["Resources/Preferences.xml"].decode("utf-8")
    pref = re.sub(r'PageHeight="[^"]+"', f'PageHeight="{PAGE_H:.4f}"', pref, count=1)
    pref = re.sub(r'PageWidth="[^"]+"', f'PageWidth="{PAGE_W:.4f}"', pref, count=1)
    pref = re.sub(r'FacingPages="true"', 'FacingPages="false"', pref, count=1)
    files["Resources/Preferences.xml"] = pref.encode("utf-8")

    for key in ("Spreads/Spread_uc6.xml", "MasterSpreads/MasterSpread_ucd.xml"):
        t = files[key].decode("utf-8")
        t = re.sub(r'GeometricBounds="[^"]+"', f'GeometricBounds="0 0 {PAGE_H:.4f} {PAGE_W:.4f}"', t)
        t = re.sub(
            r'ItemTransform="1 0 0 1 0 -72"',
            f'ItemTransform="1 0 0 1 0 {-PAGE_H / 2:.4f}"',
            t,
        )
        files[key] = t.encode("utf-8")


def add_colors(files: dict[str, bytes]) -> None:
    g = files["Resources/Graphic.xml"].decode("utf-8")
    extras = ""
    for self_id, name, vals in [
        ("Color/WZ_Blau", "WZ_Blau", "0 144 224"),
        ("Color/WZ_Gelb", "WZ_Gelb", "240 192 16"),
        ("Color/WZ_Magenta", "WZ_Magenta", "176 80 144"),
        ("Color/WZ_Dunkel", "WZ_Dunkel", "17 17 17"),
    ]:
        if self_id in g:
            continue
        extras += (
            f'\t<Color Self="{self_id}" Model="Process" Space="RGB" ColorValue="{vals}" '
            f'ColorOverride="Normal" AlternateSpace="NoAlternateColor" AlternateColorValue="" '
            f'Name="{name}" ColorEditable="true" ColorRemovable="true" Visible="true" '
            f'SwatchCreatorID="7937" />\n'
        )
    if extras:
        g = g.replace("</idPkg:Graphic>", extras + "</idPkg:Graphic>")
        files["Resources/Graphic.xml"] = g.encode("utf-8")


def add_fedra_fonts(files: dict[str, bytes]) -> None:
    """Fedra Sans Std in Fonts.xml ergaenzen (Status Installed = Systemschrift)."""
    fonts = files["Resources/Fonts.xml"].decode("utf-8")
    if "Fedra Sans Std" in fonts:
        return
    styles = [
        ("Book", "FedraSansStd-Book"),
        ("Bold", "FedraSansStd-Bold"),
        ("Demi", "FedraSansStd-Demi"),
        ("Book Italic", "FedraSansStd-BookItalic"),
        ("Medium", "FedraSansStd-Medium"),
    ]
    block = '\t<FontFamily Self="diFedra" Name="Fedra Sans Std">\n'
    for style, ps in styles:
        block += (
            f'\t\t<Font Self="diFedraFontn{ps}" FontFamily="Fedra Sans Std" '
            f'Name="Fedra Sans Std {style}" PostScriptName="{ps}" Status="Installed" '
            f'FontStyleName="{style}" FontType="OpenTypeCFF" WritingScript="0" '
            f'FullName="Fedra Sans Std {style}" FullNameNative="Fedra Sans Std {style}" '
            f'FontStyleNameNative="{style}" PlatformName="$ID/" Version="$ID/" />\n'
        )
    block += "\t</FontFamily>\n"
    fonts = fonts.replace("</idPkg:Fonts>", block + "</idPkg:Fonts>")
    files["Resources/Fonts.xml"] = fonts.encode("utf-8")


# Span: (text, point_size, font_style, fill_color)
Span = tuple[str, float, str, str]
# Paragraph: spans, leading_pt, space_after_pt, left_indent_pt
Para = tuple[list[Span], float, float, float]


def make_story_paras(story_id: str, paragraphs: list[Para], justify_center: bool = False) -> bytes:
    """Ein ParagraphStyleRange pro Absatz mit Leading/SpaceAfter wie PDF."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<idPkg:Story xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="8.0">',
        f'\t<Story Self="{story_id}" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n">',
        '\t\t<StoryPreference OpticalMarginAlignment="false" OpticalMarginSize="12" FrameType="TextFrameType" StoryOrientation="Horizontal" StoryDirection="LeftToRightDirection" />',
        '\t\t<InCopyExportOption IncludeGraphicProxies="true" IncludeAllResources="false" />',
    ]
    for para in paragraphs:
        if len(para) == 3:
            spans, leading, space_after = para
            left_indent = 0.0
        else:
            spans, leading, space_after, left_indent = para
        if not spans:
            spans = [("", 9.5, "Book", DARK)]
            leading = leading or 8.0
        has_tab = any("\t" in (sp[0] or "") for sp in spans)
        parts.append(
            f'\t\t<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle" '
            f'Hyphenation="false" SpaceBefore="0" SpaceAfter="{space_after}" '
            f'LeftIndent="{left_indent}" FirstLineIndent="0" '
            f'Justification="{"CenterAlign" if justify_center else "LeftAlign"}">'
        )
        if has_tab:
            # PDF: Werte ab 48mm = 36mm vom Textrahmen-Links (12mm Rand)
            tab_pos = 36 * MM
            parts.append("\t\t\t<Properties>")
            parts.append('\t\t\t\t<Tabs type="list">')
            parts.append('\t\t\t\t\t<ListItem type="record">')
            parts.append('\t\t\t\t\t\t<Alignment type="enumeration">LeftAlign</Alignment>')
            parts.append('\t\t\t\t\t\t<AlignmentCharacter type="string">.</AlignmentCharacter>')
            parts.append('\t\t\t\t\t\t<Leader type="string"></Leader>')
            parts.append(f'\t\t\t\t\t\t<Position type="unit">{tab_pos:.4f}</Position>')
            parts.append("\t\t\t\t\t</ListItem>")
            parts.append("\t\t\t\t</Tabs>")
            parts.append("\t\t\t</Properties>")
        for text_s, size, style, color in spans:
            parts.append(
                f'\t\t\t<CharacterStyleRange AppliedCharacterStyle="CharacterStyle/$ID/[No character style]" '
                f'FontStyle="{style}" PointSize="{size}" FillColor="{color}" Leading="{leading}" AutoLeading="100">'
            )
            parts.append("\t\t\t\t<Properties>")
            parts.append(f'\t\t\t\t\t<AppliedFont type="string">{FONT}</AppliedFont>')
            parts.append("\t\t\t\t</Properties>")
            if text_s:
                parts.append(f"\t\t\t\t<Content>{esc(text_s)}</Content>")
            parts.append("\t\t\t</CharacterStyleRange>")
        parts.append("\t\t\t<CharacterStyleRange AppliedCharacterStyle=\"CharacterStyle/$ID/[No character style]\">")
        parts.append("\t\t\t\t<Br />")
        parts.append("\t\t\t</CharacterStyleRange>")
        parts.append("\t\t</ParagraphStyleRange>")
    parts += ["\t</Story>", "</idPkg:Story>", ""]
    return "\n".join(parts).encode("utf-8")


def make_story_spans(story_id: str, paragraphs: list[list[Span]]) -> bytes:
    """Kompatibilitaet: Listen ohne Leading -> Defaults."""
    paras: list[Para] = [((spans or [("", 9.5, "Book", DARK)]), 12.5, 0.0, 0.0) for spans in paragraphs]
    return make_story_paras(story_id, paras)


def make_story(story_id: str, paragraphs: list[tuple[str, float, str]]) -> bytes:
    """Einfache Story (Ribbon/Preis)."""
    mapped: list[Para] = []
    for content, size, style in paragraphs:
        font_style = {
            "Bold": "Demi",
            "Demi": "Demi",
            "Italic": "Book Italic",
            "Regular": "Book",
            "Book": "Book",
        }.get(style, "Book")
        color = WHITE if story_id == "udd" else DARK
        leading = size * 1.15
        mapped.append(([(content, size, font_style, color)], leading, 2.0, 0.0))
    return make_story_paras(story_id, mapped, justify_center=(story_id in ("udd", "ude", "udf")))


def mm_pt(mm_val: float) -> float:
    return mm_val * MM


def main_story_paragraphs(data: dict) -> list[Para]:
    """Absatzmasse aus PDF; Bullets mit LeftIndent 10mm (Text ab 22mm), keine Sonderzeichen."""
    L_INTRO = mm_pt(4.4)
    L_FACT = mm_pt(4.2)
    L_BULLET = mm_pt(4.2)
    # PDF: Bullet-Baselines ~7.0mm auseinander => SpaceAfter = 7.0 - 4.2 = 2.8mm
    GAP_BULLET = mm_pt(2.8)
    L_HEAD = mm_pt(8.05)
    L_SUB = mm_pt(7.58)
    AFTER_INTRO = mm_pt(4.0)
    AFTER_FACTS = mm_pt(3.0)
    L_SECTION = mm_pt(7.2)
    AFTER_IDEAL = mm_pt(8.0)
    BULLET_INDENT = mm_pt(10.0)  # 12+10=22mm wie PDF

    paras: list[Para] = []
    paras.append(([(data["headline"], 16, "Demi", DARK)], L_HEAD, 0.0, 0.0))
    paras.append(([(data["sub"], 10.5, "Book Italic", DARK)], L_SUB, mm_pt(2.5), 0.0))
    paras.append(([(data["intro"], 9.5, "Book", DARK)], L_INTRO, AFTER_INTRO, 0.0))

    facts = data.get("facts") or []
    for i, (label, value) in enumerate(facts):
        space_after = AFTER_FACTS if i == len(facts) - 1 else 0.0
        paras.append(
            (
                [
                    (label, 8.5, "Bold", BLUE),
                    ("	", 8.5, "Book", DARK),
                    (value, 8.5, "Book", DARK),
                ],
                L_FACT,
                space_after,
                0.0,
            )
        )

    paras.append(([("IHRE VORTEILE AUF EINEN BLICK", 12, "Demi", DARK)], L_SECTION, 0.0, 0.0))
    for title, body in data["vorteile"]:
        paras.append(
            (
                [
                    (f"{title} ", 9.5, "Bold", DARK),
                    (body, 9.5, "Book", DARK),
                ],
                L_BULLET,
                GAP_BULLET,
                BULLET_INDENT,
            )
        )

    paras.append(([("IHR ANGEBOT", 12, "Demi", DARK)], L_SECTION, 0.0, 0.0))
    offer = list(data["angebot"])
    if data.get("technik") and not data.get("digi_price_layout"):
        offer.extend(data["technik"][:2])
    for title, body in offer:
        paras.append(
            (
                [
                    (f"{title} ", 9.5, "Bold", DARK),
                    (body, 9.5, "Book", DARK),
                ],
                L_BULLET,
                GAP_BULLET,
                BULLET_INDENT,
            )
        )

    paras.append(
        (
            [
                ("Ideal für: ", 9.5, "Bold", DARK),
                (data["ideal"], 9.5, "Book", DARK),
            ],
            L_INTRO,
            AFTER_IDEAL,
            0.0,
        )
    )
    return paras


def footer_paragraphs() -> list[Para]:
    return [
        (
            [
                ("Böhme", 16, "Demi", DARK),
                ("Zeitung", 16, "Book", DARK),
            ],
            mm_pt(9.5),
            mm_pt(2.0),
        ),
        (
            [
                (
                    "Alle Preise zzgl. MwSt.  Stand: August 2026  Mundschenk Nachrichtengesellschaft",
                    7,
                    "Book",
                    DARK,
                )
            ],
            mm_pt(4.0),
            0,
        ),
    ]


def main_paragraphs(data: dict) -> list[tuple[str, float, str]]:
    flat: list[tuple[str, float, str]] = []
    for spans, _lead, _sa in main_story_paragraphs(data):
        flat.append(("".join(s[0] for s in spans).replace("\t", "  ").replace("?", " "), spans[0][1], "Regular"))
    return flat


def update_designmap(files: dict[str, bytes], story_ids: list[str]) -> None:
    text = files["designmap.xml"].decode("utf-8")
    text = re.sub(r'StoryList="[^"]*"', f'StoryList="{" ".join(story_ids)}"', text, count=1)
    text = re.sub(r'\s*<idPkg:Story[^>]*src="Stories/[^"]+"[^>]*/>\s*', "\n", text)
    pkgs = "\n".join(f'\t<idPkg:Story src="Stories/Story_{sid}.xml" />' for sid in story_ids)
    text = text.replace("</Document>", pkgs + "\n</Document>")
    if "<?aid " not in text:
        text = text.replace(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="8.0(370)" ?>',
            1,
        )
    files["designmap.xml"] = text.encode("utf-8")


def item_transform(x: float, y: float, angle_deg: float = 0.0) -> str:
    """InDesign ItemTransform. Y zeigt nach unten: +8 = optisch wie PDF rotate(-8)."""
    sx, sy = x, spread_y(y)
    if abs(angle_deg) < 0.01:
        return f"1 0 0 1 {sx:.4f} {sy:.4f}"
    rad = math.radians(angle_deg)
    a = math.cos(rad)
    b = math.sin(rad)
    c = -math.sin(rad)
    d = math.cos(rad)
    return f"{a:.6f} {b:.6f} {c:.6f} {d:.6f} {sx:.4f} {sy:.4f}"


def path_geometry(w: float, h: float, *, centered: bool = False) -> str:
    if centered:
        x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
    else:
        x0, y0, x1, y1 = 0.0, 0.0, w, h
    return (
        "<PathGeometry>\n"
        '\t\t\t\t\t<GeometryPathType PathOpen="false">\n'
        "\t\t\t\t\t\t<PathPointArray>\n"
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{x0:.4f} {y0:.4f}" LeftDirection="{x0:.4f} {y0:.4f}" RightDirection="{x0:.4f} {y0:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{x0:.4f} {y1:.4f}" LeftDirection="{x0:.4f} {y1:.4f}" RightDirection="{x0:.4f} {y1:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{x1:.4f} {y1:.4f}" LeftDirection="{x1:.4f} {y1:.4f}" RightDirection="{x1:.4f} {y1:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{x1:.4f} {y0:.4f}" LeftDirection="{x1:.4f} {y0:.4f}" RightDirection="{x1:.4f} {y0:.4f}" />\n'
        "\t\t\t\t\t\t</PathPointArray>\n"
        "\t\t\t\t\t</GeometryPathType>\n"
        "\t\t\t\t</PathGeometry>"
    )


def set_frame_geometry(
    frame_xml: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    angle_deg: float = 0.0,
    centered: bool = False,
) -> str:
    if centered:
        # Rotation um Mittelpunkt (wie PDF translate+rotate)
        cx, cy = x + w / 2, y + h / 2
        frame_xml = re.sub(
            r'ItemTransform="[^"]+"',
            f'ItemTransform="{item_transform(cx, cy, angle_deg)}"',
            frame_xml,
            count=1,
        )
    else:
        frame_xml = re.sub(
            r'ItemTransform="[^"]+"',
            f'ItemTransform="{item_transform(x, y, angle_deg)}"',
            frame_xml,
            count=1,
        )
    frame_xml = re.sub(
        r"<PathGeometry>.*?</PathGeometry>",
        path_geometry(w, h, centered=centered),
        frame_xml,
        count=1,
        flags=re.S,
    )
    frame_xml = re.sub(
        r"<TextFramePreference[^/]*/>",
        f'<TextFramePreference TextColumnFixedWidth="{w:.4f}" FirstBaselineOffset="AscentOffset" IgnoreWrap="true" />',
        frame_xml,
        count=1,
    )
    return frame_xml


def clone_textframe(
    template_frame: str,
    self_id: str,
    story_id: str,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    angle_deg: float = 0.0,
    centered: bool = False,
) -> str:
    frame = template_frame
    frame = re.sub(r'Self="uee"', f'Self="{self_id}"', frame, count=1)
    frame = re.sub(r'ParentStory="udc"', f'ParentStory="{story_id}"', frame, count=1)
    frame = re.sub(r'Name="[^"]*"', f'Name="{esc(name)}"', frame, count=1)
    return set_frame_geometry(frame, x, y, w, h, angle_deg=angle_deg, centered=centered)


def rect_xml(
    self_id: str,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    *,
    angle_deg: float = 0.0,
    centered: bool = False,
    text_wrap: bool = False,
) -> str:
    if centered:
        transform = item_transform(x + w / 2, y + h / 2, angle_deg)
        path = path_geometry(w, h, centered=True)
    else:
        transform = item_transform(x, y, angle_deg)
        path = path_geometry(w, h, centered=False)
    wrap = ""
    if text_wrap:
        wrap = (
            '\t\t\t<TextWrapPreference Inverse="false" ApplyToMasterPageOnly="false" '
            'TextWrapSide="LeftSide" TextWrapMode="BoundingBoxTextWrap">\n'
            "\t\t\t\t<Properties>\n"
            '\t\t\t\t\t<TextWrapOffset Top="4" Left="6" Bottom="4" Right="0" />\n'
            "\t\t\t\t</Properties>\n"
            "\t\t\t</TextWrapPreference>\n"
        )
    return (
        f'\t\t<Rectangle Self="{self_id}" ContentType="Unassigned" StoryTitle="$ID/" '
        f'ParentInterfaceChangeCount="" TargetInterfaceChangeCount="" LastUpdatedInterfaceChangeCount="" '
        f'OverriddenPageItemProps="" HorizontalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" '
        f'VerticalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" FillColor="{fill}" '
        f'StrokeWeight="0" StrokeColor="Swatch/None" GradientFillStart="0 0" GradientFillLength="0" '
        f'GradientFillAngle="0" GradientStrokeStart="0 0" GradientStrokeLength="0" GradientStrokeAngle="0" '
        f'ItemLayer="uc3" Locked="false" LocalDisplaySetting="Default" GradientFillHiliteLength="0" '
        f'GradientFillHiliteAngle="0" GradientStrokeHiliteLength="0" GradientStrokeHiliteAngle="0" '
        f'AppliedObjectStyle="ObjectStyle/$ID/[None]" Visible="true" Name="{esc(name)}" '
        f'ItemTransform="{transform}">\n'
        f"\t\t\t<Properties>\n"
        f"\t\t\t\t{path}\n"
        f"\t\t\t</Properties>\n"
        f"{wrap}"
        f"\t\t</Rectangle>\n"
    )


def oval_xml(self_id: str, name: str, x: float, y: float, d: float, fill: str) -> str:
    """Gelber Play-Bullet-Kreis (Naeherung)."""
    sx, sy = x, spread_y(y)
    r = d / 2
    return (
        f'\t\t<Oval Self="{self_id}" ContentType="Unassigned" StoryTitle="$ID/" '
        f'ParentInterfaceChangeCount="" TargetInterfaceChangeCount="" LastUpdatedInterfaceChangeCount="" '
        f'OverriddenPageItemProps="" HorizontalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" '
        f'VerticalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" FillColor="{fill}" '
        f'StrokeWeight="0" StrokeColor="Swatch/None" ItemLayer="uc3" Locked="false" '
        f'LocalDisplaySetting="Default" AppliedObjectStyle="ObjectStyle/$ID/[None]" Visible="true" '
        f'Name="{esc(name)}" ItemTransform="1 0 0 1 {sx:.4f} {sy:.4f}">\n'
        f"\t\t\t<Properties>\n"
        f"\t\t\t\t<PathGeometry>\n"
        f'\t\t\t\t\t<GeometryPathType PathOpen="false">\n'
        f"\t\t\t\t\t\t<PathPointArray>\n"
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{r:.4f} 0" LeftDirection="{-0.1*r:.4f} 0" RightDirection="{2.1*r:.4f} 0" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{d:.4f} {r:.4f}" LeftDirection="{d:.4f} {-0.1*r:.4f}" RightDirection="{d:.4f} {2.1*r:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{r:.4f} {d:.4f}" LeftDirection="{2.1*r:.4f} {d:.4f}" RightDirection="{-0.1*r:.4f} {d:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="0 {r:.4f}" LeftDirection="0 {2.1*r:.4f}" RightDirection="0 {-0.1*r:.4f}" />\n'
        f"\t\t\t\t\t\t</PathPointArray>\n"
        f"\t\t\t\t\t</GeometryPathType>\n"
        f"\t\t\t\t</PathGeometry>\n"
        f"\t\t\t</Properties>\n"
        f"\t\t</Oval>\n"
    )


def image_xml(self_id: str, name: str, x: float, y: float, size: float, path: Path) -> str:
    sx, sy = x, spread_y(y)
    uri = path.resolve().as_uri()
    return (
        f'\t\t<Rectangle Self="{self_id}" ContentType="GraphicType" StoryTitle="$ID/" '
        f'ParentInterfaceChangeCount="" TargetInterfaceChangeCount="" LastUpdatedInterfaceChangeCount="" '
        f'OverriddenPageItemProps="" HorizontalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" '
        f'VerticalLayoutConstraints="FlexibleDimension FixedDimension FlexibleDimension" FillColor="Swatch/None" '
        f'StrokeWeight="0" StrokeColor="Swatch/None" ItemLayer="uc3" Locked="false" '
        f'LocalDisplaySetting="Default" AppliedObjectStyle="ObjectStyle/$ID/[None]" Visible="true" '
        f'Name="{esc(name)}" ItemTransform="1 0 0 1 {sx:.4f} {sy:.4f}">\n'
        f"\t\t\t<Properties>\n"
        f"\t\t\t\t<PathGeometry>\n"
        f'\t\t\t\t\t<GeometryPathType PathOpen="false">\n'
        f"\t\t\t\t\t\t<PathPointArray>\n"
        f'\t\t\t\t\t\t\t<PathPointType Anchor="0 0" LeftDirection="0 0" RightDirection="0 0" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="0 {size:.4f}" LeftDirection="0 {size:.4f}" RightDirection="0 {size:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{size:.4f} {size:.4f}" LeftDirection="{size:.4f} {size:.4f}" RightDirection="{size:.4f} {size:.4f}" />\n'
        f'\t\t\t\t\t\t\t<PathPointType Anchor="{size:.4f} 0" LeftDirection="{size:.4f} 0" RightDirection="{size:.4f} 0" />\n'
        f"\t\t\t\t\t\t</PathPointArray>\n"
        f"\t\t\t\t\t</GeometryPathType>\n"
        f"\t\t\t\t</PathGeometry>\n"
        f"\t\t\t</Properties>\n"
        f'\t\t\t<Image Self="{self_id}I" Space="$ID/#Links" OverriddenPageItemProps="" '
        f'LocalDisplaySetting="HighQuality" ActualPpi="72 72" EffectivePpi="72 72" '
        f'ImageRenderingIntent="UseColorSettings" Visible="true" Name="{esc(name)}" '
        f'ItemTransform="1 0 0 1 0 0">\n'
        f"\t\t\t\t<Properties>\n"
        f'\t\t\t\t\t<GraphicBounds Left="0" Top="0" Right="{size:.4f}" Bottom="{size:.4f}" />\n'
        f"\t\t\t\t</Properties>\n"
        f'\t\t\t\t<Link Self="{self_id}L" AssetURL="$ID/" AssetID="$ID/" LinkResourceURI="{uri}" '
        f'LinkResourceFormat="LinkFormat/$ID/Portable Network Graphics (PNG)" StoredState="Normal" '
        f'LinkClassID="35906" LinkClientID="257" LinkResourceModified="false" LinkObjectModified="false" '
        f'ShowInUI="true" CanEmbed="true" CanUnembed="true" CanPackage="true" ImportPolicy="NoAutoImport" '
        f'ExportPolicy="NoAutoExport" LinkImportStamp="file 0 0" '
        f'LinkImportModificationTime="2026-08-03T12:00:00Z" LinkImportTime="2026-08-03T12:00:00Z" '
        f'LinkResourceSize="0~0" RenditionData="Actual" />\n'
        f"\t\t\t</Image>\n"
        f"\t\t</Rectangle>\n"
    )


def build_spread(files: dict[str, bytes], data: dict) -> list[str]:
    story_main, story_ribbon, story_price, story_footer = "udc", "udd", "ude", "udf"

    files[f"Stories/Story_{story_main}.xml"] = make_story_paras(story_main, main_story_paragraphs(data))
    files[f"Stories/Story_{story_ribbon}.xml"] = make_story(story_ribbon, [(data["ribbon"], 11, "Demi")])
    price_paras = []
    for ln in data["preise"]:
        if not ln:
            continue
        if ln.startswith("zzgl"):
            price_paras.append((ln, 8, "Book"))
        else:
            price_paras.append((ln, 12.5, "Demi"))
    files[f"Stories/Story_{story_price}.xml"] = make_story(story_price, price_paras)
    files[f"Stories/Story_{story_footer}.xml"] = make_story_paras(story_footer, footer_paragraphs())

    spread = files["Spreads/Spread_uc6.xml"].decode("utf-8")
    m = re.search(r'<TextFrame Self="uee".*?</TextFrame>', spread, flags=re.S)
    if not m:
        raise RuntimeError("Vorlagen-TextFrame uee fehlt")
    original_frame = m.group(0)

    # Wie PDF: Textbreite PAGE_W-24mm, Preisbox rechts mit Textumfluss
    margin = 12 * MM
    main_x, main_y = margin, 42 * MM
    main_w = PAGE_W - 24 * MM
    main_h = 250 * MM

    box_w, box_h = 52 * MM, 32 * MM
    box_x = PAGE_W - 12 * MM - box_w  # = 146mm, PDF ~148mm
    box_y = 134.6 * MM  # PDF Preiskasten

    main_frame = set_frame_geometry(original_frame, main_x, main_y, main_w, main_h)
    main_frame = re.sub(r'Name="[^"]*"', 'Name="Inhalt"', main_frame, count=1)
    # Tabstopp fuer Facts-Werte bei 48mm (von Rahmenlinks = 36mm)
    if "<TextFramePreference" in main_frame:
        main_frame = main_frame.replace(
            "<TextFramePreference",
            '<TextFramePreference TextColumnFixedWidth="%.4f" TabList="36 0 0"' % (main_w,),
            1,
        )
        # remove duplicate TextColumnFixedWidth if any later - set_frame already set it
        # Fix double attrs by cleaning
        main_frame = re.sub(
            r'<TextFramePreference[^/]*/>',
            f'<TextFramePreference TextColumnFixedWidth="{main_w:.4f}" FirstBaselineOffset="AscentOffset" />',
            main_frame,
            count=1,
        )
    spread = spread[: m.start()] + main_frame + spread[m.end() :]

    items: list[str] = []

    logo_y, logo_d = 14 * MM, 23 * MM
    mode = data.get("logo_mode", "both")
    if mode == "both":
        gap = logo_d - 2 * MM
        bx = PAGE_W / 2 - gap / 2 - logo_d / 2
        hx = PAGE_W / 2 + gap / 2 - logo_d / 2
        items.append(image_xml("uLogoHK", "Logo HK", hx, logo_y, logo_d, LINKS / "logo_hk.png"))
        items.append(image_xml("uLogoBZ", "Logo BZ", bx, logo_y, logo_d, LINKS / "logo_bz.png"))
    elif mode == "bz":
        items.append(image_xml("uLogoBZ", "Logo BZ", PAGE_W / 2 - logo_d / 2, logo_y, logo_d, LINKS / "logo_bz.png"))
    else:
        items.append(image_xml("uLogoHK", "Logo HK", PAGE_W / 2 - logo_d / 2, logo_y, logo_d, LINKS / "logo_hk.png"))

    items.append(rect_xml("uBar", "Balken links", 0, 0, 5 * MM, PAGE_H, BLUE))

    # Ribbon: PDF rotate(-8) bei y-up => InDesign +8, Rotation um Mitte
    rib_w, rib_h = 62 * MM, 11 * MM
    rib_x, rib_y = PAGE_W - 72 * MM, 19 * MM  # PDF: Oberkante ~19mm
    angle = 8.0  # InDesign Y nach unten: +8 = PDF rotate(-8) = rechte Seite tiefer
    items.append(
        rect_xml("uRibbon", "Ribbon", rib_x, rib_y, rib_w, rib_h, YELLOW, angle_deg=angle, centered=True)
    )
    items.append(
        clone_textframe(
            original_frame,
            "uFrameRibbon",
            story_ribbon,
            "Ribbon-Text",
            rib_x + 2 * MM,
            rib_y + 1.5 * MM,
            rib_w - 4 * MM,
            rib_h - 3 * MM,
            angle_deg=angle,
            centered=True,
        )
    )

    items.append(
        rect_xml(
            "uPrice",
            "Preiskasten",
            box_x,
            box_y,
            box_w,
            box_h,
            YELLOW,
            text_wrap=True,
        )
    )
    items.append(
        clone_textframe(
            original_frame,
            "uFramePrice",
            story_price,
            "Preis-Text",
            box_x + 3 * MM,
            box_y + 4 * MM,
            box_w - 6 * MM,
            box_h - 8 * MM,
        )
    )

    # Footer unten zentriert wie PDF
    foot_w, foot_h = 160 * MM, 20 * MM
    foot_x = (PAGE_W - foot_w) / 2
    foot_y = 318 * MM
    items.append(
        clone_textframe(
            original_frame,
            "uFrameFooter",
            story_footer,
            "Footer",
            foot_x,
            foot_y,
            foot_w,
            foot_h,
        )
    )

    insert = "\n".join(items) + "\n"
    spread = spread.replace("</Spread>", insert + "\t</Spread>")
    files["Spreads/Spread_uc6.xml"] = spread.encode("utf-8")
    return [story_main, story_ribbon, story_price, story_footer]


def write_package(path: Path, files: dict[str, bytes]) -> None:
    if path.exists():
        path.unlink()
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", files["mimetype"], compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            if name == "mimetype":
                continue
            zf.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


def prepare_links() -> None:
    LINKS.mkdir(parents=True, exist_ok=True)
    for dest, src in {
        "logo_bz.png": LOGO_BZ if LOGO_BZ.exists() else ASSETS / "logo_bz_norm.png",
        "logo_hk.png": LOGO_HK if LOGO_HK.exists() else ASSETS / "logo_hk_norm.png",
    }.items():
        shutil.copy2(src, LINKS / dest)


def build_one(product: dict) -> Path:
    files = load_template()
    patch_page_size(files)
    add_colors(files)
    add_fedra_fonts(files)
    story_ids = build_spread(files, product)
    update_designmap(files, story_ids)
    out = OUT / product["file"].replace(".pdf", ".idml")
    write_package(out, files)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.idml"):
        old.unlink()
    prepare_links()
    for product in PRODUCTS:
        print("Created:", build_one(product))

    files = load_template()
    add_fedra_fonts(files)
    files["Stories/Story_udc.xml"] = make_story_paras(
        "udc",
        [
            ([("TEXT-PROOF", 22, "Demi", DARK)], 28, 4),
            ([("Fedra Sans Std aktiv - Story-Bindung ok.", 12, "Book", DARK)], 16, 0),
        ],
    )
    update_designmap(files, ["udc"])
    write_package(OUT / "_PROOF_text.idml", files)
    print("Created:", OUT / "_PROOF_text.idml")

    txt_dir = OUT / "Texte_zum_Einfuegen"
    txt_dir.mkdir(exist_ok=True)
    em = "?"
    for product in PRODUCTS:
        body_lines = []
        for spans, _a, _b, *_rest in main_story_paragraphs(product):
            s = "".join(x[0] for x in spans)
            body_lines.append(s.replace("\t", "  ").replace(em, " "))
        head_lines = [product["ribbon"], " | ".join(x for x in product["preise"] if x), ""]
        (txt_dir / product["file"].replace(".pdf", ".txt")).write_text(
            "\n".join(head_lines + body_lines), encoding="utf-8"
        )

    (OUT / "README_Grafik.md").write_text(
        "\n".join([
            "# Einseiter Online-Produkte  InDesign (IDML)",
            "",
            "An PDF angeglichen: Fedra, Ribbon nach rechts (+8 Grad), Leading/SpaceAfter,",
            "volle Textbreite mit Umfluss um Preiskasten, Footer separat.",
            "",
        ]),
        encoding="utf-8",
    )
    print("Fertig:", OUT)


if __name__ == "__main__":
    main()
