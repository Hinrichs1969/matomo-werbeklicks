#!/usr/bin/env python3
"""
Matomo E-Paper Werbeklicks - taegliches Canvas-Update
Laeuft taeglich um 08:00 Uhr via launchd.
"""

import urllib.request
import urllib.parse
import json
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
TOKEN    = os.environ.get("MATOMO_TOKEN", "")
SITE_ID  = 14
BASE_URL = "https://matomo.mundschenk.de/index.php"
START    = "2026-07-01"
_HERE    = os.path.dirname(os.path.abspath(__file__))
CANVAS   = os.environ.get(
    "CANVAS_PATH",
    "/Users/khinrichs/.cursor/projects/Users-khinrichs-KI-Projekt-OKR-7-26/canvases/matomo-werbekunden-klicks.canvas.tsx"
)
HTML_OUT = os.path.join(_HERE, "Werbeklicks-Report-aktuell.html")
LOG      = os.path.join(_HERE, "matomo-canvas-update.log")

TODAY    = datetime.date.today().strftime("%Y-%m-%d")
TODAY_DE = datetime.date.today().strftime("%d.%m.%Y")

ADVERTISERS = [
    # pub: "BZ" | "HK" | "both"  – aus Pipedrive-Ausgabe-Feld (Stand Okt 2026)
    # "BZ" = Böhme-Zeitung (Ausgabe 470/2507), "HK" = Heide-Kurier (2463),
    # "both" = Cross-Selling / beide Ausgaben → BZ/HK-Split nicht berechenbar
    {"key": "viavox",         "pub": "BZ",   "name": "viavox.io",                    "url": "viavox.io",                      "seg": "dimension14%3D%40viavox.io",                                                                                                                                                                        "utm": True,  "klaeren": False, "banner": True},
    {"key": "vitamin_k4",     "pub": "BZ",   "name": "vitamin-k4.de",                "url": "vitamin-k4.de",                  "seg": "dimension14%3D%3Dhttp%3A%2F%2Fwww.vitamin-k4.de",                                                                                                                                                  "utm": False, "klaeren": False},
    {"key": "smurfitkappa",   "pub": "BZ",   "name": "smurfitkappa",                 "url": "smurfitkappa.concludis.de",      "seg": "dimension14%3D%3Dhttps%3A%2F%2Fsmurfitkappa.concludis.de%2Fprj%2Fshw%2F643fb86c8172fb56d8898497eb682c27_0%2F13796%2F%3Futm_campaign%3Dsmurfitkappa",                                                "utm": True,  "klaeren": False},
    {"key": "harbort",        "pub": "BZ",   "name": "Harbort GmbH & Co. KG",        "url": "harbort.de/karriere",            "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.harbort.de%2Fkarriere%3Futm_campaign%3Dharbort",                                                                                                                "utm": True,  "klaeren": False},
    {"key": "hotel_park",     "pub": "BZ",   "name": "hotel-park-soltau",            "url": "hotel-park-soltau.de",           "seg": "dimension14%3D%3Dhttps%3A%2F%2Fhotel-park-soltau.de%2Faktuellestellenangebote%2F%3Futm_campaign%3Dhotel-park-soltau",                                                                               "utm": True,  "klaeren": False},
    {"key": "stadt_munster",  "pub": "both", "name": "stadt_munster",                "url": "bewerbung.munster.de",           "seg": "dimension14%3D%40bewerbung.munster.de",                                                                                                                                                            "utm": True,  "klaeren": False},
    {"key": "stadt_walsrode", "pub": "BZ",   "name": "stadt-walsrode",               "url": "stadt-walsrode.de/Jobs",         "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.stadt-walsrode.de%2FStadt-Rathaus%2FPolitik-Verwaltung%2FJobs-Die-Stadt-als-Arbeitgeber%2F%3Futm_campaign%3Dstadt-walsrode",                                      "utm": True,  "klaeren": False},
    {"key": "buergerliste",   "pub": "HK",   "name": "bispinger-buergerliste",       "url": "bispinger-buergerliste.de",      "seg": "dimension14%3D%3Dhttp%3A%2F%2Fwww.bispinger-buergerliste.de%3Futm_campaign%3Dbuergerliste",                                                                                                        "utm": True,  "klaeren": False},
    {"key": "wietzendorf",    "pub": "BZ",   "name": "Wietzendorf Ausbildung",       "url": "wietzendorf.de/ausbildung",      "seg": "dimension14%3D%40wietzendorf.de%2Fausbildung",                                                                                                                            "utm": True,  "klaeren": False},
    {"key": "stadtwerke_mb",  "pub": "HK",   "name": "stadtwerke-munster-bispingen", "url": "ihr-stadtwerk.de",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.ihr-stadtwerk.de%2Fde%2FMenue%2FKarriere%2F%3Futm_campaign%3DStadtwerke-Munster-Bispingen-GmbH",                                                               "utm": True,  "klaeren": False},
    {"key": "landesforsten",  "pub": "HK",   "name": "niedersaechs.-landesforsten",  "url": "landesforsten.de",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.landesforsten.de%2F%3Futm_campaign%3Dniedersaechsische-landesforsten",                                                                                          "utm": True,  "klaeren": False},
    {"key": "bundeswehr",     "pub": "HK",   "name": "bundeswehr",                   "url": "bewerbung.bundeswehr-karriere.de","seg": "dimension14%3D%3Dhttps%3A%2F%2Fbewerbung.bundeswehr-karriere.de%2F%3Futm_campaign%3Dbundeswehr",                                                                                                  "utm": True,  "klaeren": False},
    {"key": "spd",            "pub": "HK",   "name": "SPD Schneverdingen",           "url": "spd-heidekreis.de",              "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.spd-heidekreis.de%2Fwahlen-2026%2F%3Futm_campaign%3DSPD",                                                                                                      "utm": True,  "klaeren": False},
    {"key": "sushi",          "pub": "HK",   "name": "Sushi Bar Soltau",             "url": "sushi-soltau.de",                "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.sushi-soltau.de%2F%3Futm_campaign%3DSushiBar",                                                                                                                  "utm": True,  "klaeren": False},
    {"key": "grillhus",       "pub": "HK",   "name": "Grillhus",                     "url": "grillhus.de/jobs",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fgrillhus.de%2Fjobs%2F%3Futm_campaign%3Dgrillhus",                                                                                                                  "utm": True,  "klaeren": False},
    {"key": "maderos",        "pub": "BZ",   "name": "Maderos",                      "url": "maderos.de",                     "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.maderos.de%3Futm_campaign%3Dmaderos",                                                                                                                          "utm": True,  "klaeren": False},
    {"key": "hatesohl",       "pub": "BZ",   "name": "Bestattungen Hatesohl",        "url": "bestattungen-hatesohl.de",       "seg": "dimension14%3D%40bestattungen-hatesohl.de",                                                                                                                            "utm": True,  "klaeren": False},
    {"key": "nelsonpark",     "pub": "HK",   "name": "Nelson Park Terrassen",         "url": "nelsonpark",                     "seg": "dimension14%3D%40nelsonpark",                                                                                                                                                                  "utm": True,  "klaeren": False},
    {"key": "workandlife",    "pub": "both", "name": "Work & Life Heidekreis",        "url": "workandlife-heidekreis.de",      "seg": "dimension14%3D%40workandlife-heidekreis.de",                                                                                                                                                    "utm": True,  "klaeren": False},
    {"key": "schneverdingen", "pub": "BZ",   "name": "Stadt Schneverdingen",          "url": "schneverdingen.de",              "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.schneverdingen.de%2Fdesktopdefault.aspx%2Ftabid-7207%2F%3Futm_campaign%3Dstadt_schneverdingen",                                                              "utm": True,  "klaeren": False},
    {"key": "lorenzdental",   "pub": "BZ",   "name": "Lorenz Dental Soltau",          "url": "karriere-lorenzdental-soltau.de","seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.karriere-lorenzdental-soltau.de%2F%3Futm_campaign%3Dlorenzdental",                                                                                        "utm": True,  "klaeren": False},
    {"key": "haenel",         "pub": "BZ",   "name": "Haenel Kachelofenbau",          "url": "haenel-kachelofenbau.de",        "seg": "dimension14%3D%40haenel-kachelofenbau.de",                                                                                                                                                     "utm": False, "klaeren": False, "banner": True},
    {"key": "suedsee",        "pub": "HK",   "name": "Südsee-Camp",                   "url": "suedsee-camp.de",                "seg": "dimension14%3D%40suedsee-camp.de",                                                                                                                                                             "utm": True,  "klaeren": False},
    {"key": "roeders",        "pub": "BZ",   "name": "Gebrüder Röders",               "url": "gebrueder-roeders.com/karriere", "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.gebrueder-roeders.com%2Fkarriere%2Fausbildung-studium%2F%3Futm_campaign%3Dgebrueder-roeders",                                                                    "utm": True,  "klaeren": False},
    {"key": "nossol",         "pub": "BZ",   "name": "Nossol",                        "url": "nossol.org",                     "seg": "dimension14%3D%3Dhttps%3A%2F%2Fnossol.org%2F%3Futm_campaign%3Dnossol",                                                                                                 "utm": True,  "klaeren": False},
    {"key": "drk_munster",    "pub": "BZ",   "name": "DRK Alten-/Pflegeheim Munster", "url": "drk-munster.de/freie-stellen",   "seg": "dimension14%3D%40drk-munster.de%2Ffreie-stellen",                                                                                                                               "utm": True,  "klaeren": False},
    {"key": "schroeder",      "pub": "BZ",   "name": "Otto Schröder Tiefbau",          "url": "schroeder-tiefbau.de/unternehmen","seg": "dimension14%3D%40schroeder-tiefbau.de%2Funternehmen",                                                                                                                                    "utm": True,  "klaeren": False},
    {"key": "edeka_meyer",    "pub": "BZ",   "name": "Edeka Meyer Neuenkirchen",       "url": "edeka-meyer-neuenkirchen.de/karriere","seg": "dimension14%3D%40edeka-meyer-neuenkirchen.de%2Fkarriere",                                                                                                                           "utm": True,  "klaeren": False},
    {"key": "klinik_fb",      "pub": "BZ",   "name": "Klinik Fallingbostel",           "url": "klinik-fallingbostel.de/karriere","seg": "dimension14%3D%40klinik-fallingbostel.de%2Fkarriere",                                                                                                                                    "utm": False, "klaeren": False},
    {"key": "wtz_touristik",  "pub": "both", "name": "Wietzendorf Touristik (Honigfest)","url": "wietzendorf-touristik.de",     "seg": "dimension14%3D%40wietzendorf-touristik.de",                                                                                                                                     "utm": False, "klaeren": False, "banner": True},
    {"key": "covestro",       "pub": "BZ",   "name": "Covestro",                       "url": "covestro.com/de/career",         "seg": "dimension14%3D%40covestro.com%2Fde%2Fcareer",                                                                                                                                            "utm": True,  "klaeren": False},
    {"key": "pflegejobs",     "pub": "BZ",   "name": "CMS / Pflegejobs",               "url": "pflegejobs-altenpflege.de/azubi","seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.pflegejobs-altenpflege.de%2Fazubi-pflegefachfrau-mann-w-m-d%2F%3Futm_campaign%3DHaus_Zuflucht",                                                      "utm": True,  "klaeren": False},
    # Aus Pipedrive-Recherche Oktober 2026
    {"key": "grube",          "pub": "both", "name": "Grube KG Forstgerätestelle",     "url": "grube.de/karriere/ausbildung",   "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.grube.de%2Fkarriere%2Fausbildung%2F",                                                                                                          "utm": False, "klaeren": False},
    {"key": "kahnwald",       "pub": "HK",   "name": "Kahnwald Optik-Hörgeräte",       "url": "optikkahnwald.de",               "seg": "dimension14%3D%40optikkahnwald.de",                                                                                                                                             "utm": False, "klaeren": True },
    {"key": "olaf_meyer",     "pub": "BZ",   "name": "Garten- u. Landschaftsbau Meyer","url": "meyer-gartenbau-soltau.de",      "seg": "dimension14%3D%40meyer-gartenbau-soltau.de",                                                                                                                                   "utm": False, "klaeren": True,  "banner": True },
    {"key": "msm_walsrode",   "pub": "BZ",   "name": "MSM Walsrode",                   "url": "msm-walsrode.com",               "seg": "dimension14%3D%40msm-walsrode.com",                                                                                                                                             "utm": False, "klaeren": True },
    {"key": "heidekreis",     "pub": "BZ",   "name": "Landkreis Heidekreis",           "url": "heidekreis.de",                  "seg": "dimension14%3D%40heidekreis.de",                                                                                                                                                "utm": False, "klaeren": True },
]


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def matomo_post(params, retries=3, backoff=120):
    p = dict(params)
    p["token_auth"] = TOKEN
    p["idSite"]     = str(SITE_ID)
    p["format"]     = "JSON"
    data = urllib.parse.urlencode(p).encode()
    req  = urllib.request.Request(BASE_URL, data=data, method="POST")
    import time
    last_exc = None
    # Batch-Abfragen (CustomDimensions) bekommen mehr Zeit
    timeout = 360 if params.get("method","").startswith("CustomDimensions") else 180
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                log(f"  Matomo-Fehler (Versuch {attempt}/{retries}): {exc} – warte {backoff}s …")
                time.sleep(backoff)
            else:
                raise last_exc


def fetch_daily_data():
    raw = matomo_post({
        "module": "API", "method": "Events.getName",
        "period": "day", "date": f"{START},{TODAY}",
        "filter_limit": "20",
    })
    result = []
    for date_str, events in sorted(raw.items()):
        if not isinstance(events, list):
            continue
        v = c = b = 0
        for e in events:
            n = e.get("label", "")
            if n == "replica_box_link_view":  v = e.get("nb_events", 0)
            if n == "replica_box_link_click": c = e.get("nb_events", 0)
            if n == "banner_click":           b = e.get("nb_events", 0)
        if v or c:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            result.append({"date": d.strftime("%d.%m"), "views": int(v), "clicks": int(c), "banner": int(b)})
    return result


def fetch_monthly_data():
    today = datetime.date.today()
    d = datetime.date(2026, 7, 1)
    months = []
    while d <= today:
        months.append(d)
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    result = []
    for m in months:
        raw = matomo_post({
            "module": "API", "method": "Events.getName",
            "period": "month", "date": m.strftime("%Y-%m-%d"),
            "filter_limit": "20",
        })
        v = c = b = 0
        if isinstance(raw, list):
            for e in raw:
                n = e.get("label", "")
                if n == "replica_box_link_view":  v = e.get("nb_events", 0)
                if n == "replica_box_link_click": c = e.get("nb_events", 0)
                if n == "banner_click":           b = e.get("nb_events", 0)
        if m.month == today.month and m.year == today.year:
            label = f"{m.strftime('%b')} (1\u2013{today.day})"
        else:
            label = m.strftime("%b %Y")
        result.append({"month": label, "views": v, "clicks": c, "banner": b})
    return result


def fetch_advertiser_clicks(adv):
    """Liefert Klicks (klickbar + banner) für einen Werbekunden.

    banner_click-Events werden NUR gezählt wenn adv['banner']=True.
    Hintergrund: Matomo setzt dimension14 visit-scope – Klicks auf fremde
    Banner in derselben Sitzung werden fälschlicherweise dem Werbekunden
    zugeordnet, der zuletzt eine klickbare Anzeige angeklickt hat.
    """
    raw = matomo_post({
        "module": "API", "method": "Events.getName",
        "period": "range", "date": f"{START},{TODAY}",
        "filter_limit": "20",
        "segment": adv["seg"],
    })
    has_banner_product = adv.get("banner", False)
    klickbar = banner = 0
    if isinstance(raw, list):
        for e in raw:
            n = e.get("label", "")
            if n == "replica_box_link_click":
                klickbar = int(e.get("nb_events", 0))
            if n == "banner_click" and has_banner_product:
                banner = int(e.get("nb_events", 0))
    return adv["key"], {"klickbar": klickbar, "banner": banner, "total": klickbar + banner}


def compute_bz_hk_split(total, adv):
    """Berechnet BZ/HK-Split aus dem 'pub'-Feld des Advertisers (Pipedrive-Ausgabe).
    pub='BZ'  → bz=total, hk=0
    pub='HK'  → bz=0,     hk=total
    pub='both'→ bz=None,  hk=None  (Cross-Selling; kein Split möglich)
    """
    pub = adv.get("pub", "both")
    if pub == "BZ":
        return {"total": total, "bz": total, "hk": 0}
    if pub == "HK":
        return {"total": total, "bz": 0, "hk": total}
    return {"total": total, "bz": None, "hk": None}


def js_bool(v):
    return "true" if v else "false"


def generate_html(daily, monthly, adv_clicks):
    """Generiert einen druckfertigen HTML-Report zum Teilen mit Kollegen."""
    total_clicks = sum(d["clicks"] for d in daily)
    total_views  = sum(d["views"]  for d in daily)
    total_banner = sum(d["banner"] for d in daily)
    ident_clicks = sum(adv_clicks.get(a["key"], {}).get("total", 0) for a in ADVERTISERS)
    avg_ctr      = f"{(total_clicks / total_views * 100):.1f}" if total_views else "0.0"

    # BZ/HK-Split: "both"-Kunden (Cross-Selling) können nicht aufgeteilt werden
    both_names = [a["name"] for a in ADVERTISERS if a.get("pub") == "both"]
    if both_names:
        bzhk_note = (
            '<div style="font-size:10px;color:#9ca3af;margin-bottom:8px">'
            '&#8505;&nbsp;BZ/HK-Aufteilung bei Cross-Selling-Kunden (pub=both) nicht berechenbar: '
            + ", ".join(both_names) +
            '</div>'
        )
    else:
        bzhk_note = ""

    sorted_adv = sorted(ADVERTISERS, key=lambda a: adv_clicks.get(a["key"], {}).get("total", 0), reverse=True)

    # Tabellen-Zeilen
    adv_rows_html = ""
    for a in sorted_adv:
        d        = adv_clicks.get(a["key"], {"total": 0, "klickbar": 0, "banner": 0, "bz": 0, "hk": 0})
        k        = d["total"]
        klickbar = d.get("klickbar", 0)
        banner   = d.get("banner", 0)
        bz       = d["bz"]
        hk       = d["hk"]
        share    = f"{(k / total_clicks * 100):.1f}" if total_clicks else "0.0"
        utm_pill   = '<span class="pill pill-green">ja</span>'   if a["utm"]     else '<span class="pill pill-orange">nein</span>'
        klaer_pill = '<span class="pill pill-orange">klaeren</span>' if a["klaeren"] else '<span class="pill pill-green">aktiv</span>'
        bericht_url = f"berichte/{a['key']}.html"
        bz_cell = f'<span style="color:#6b7280;font-style:italic">N/V</span>' if bz is None else f"{bz:,}"
        hk_cell = f'<span style="color:#6b7280;font-style:italic">N/V</span>' if hk is None else f"{hk:,}"
        adv_rows_html += f"""
        <tr>
          <td><strong>{a["name"]}</strong><br><a href="{bericht_url}" style="font-size:10px;color:#6b7280">&#128196; Kundenbericht</a></td>
          <td class="url">{a["url"]}</td>
          <td class="right"><strong>{k:,}</strong></td>
          <td class="right" style="color:#6366f1">{klickbar:,}</td>
          <td class="right" style="color:#0891b2">{banner:,}</td>
          <td class="right bz">{bz_cell}</td>
          <td class="right hk">{hk_cell}</td>
          <td class="center">{share}&nbsp;%</td>
          <td class="center">{utm_pill}</td>
          <td class="center">{klaer_pill}</td>
        </tr>"""

    # Monatstabellen-Zeilen
    month_rows_html = ""
    for m in monthly:
        ctr = f"{(m['clicks'] / m['views'] * 100):.1f}" if m["views"] else "0.0"
        month_rows_html += f"""
        <tr>
          <td>{m["month"]}</td>
          <td class="right">{m["views"]:,}</td>
          <td class="right">{m["clicks"]:,}</td>
          <td class="right">{m["banner"]:,}</td>
          <td class="right">{ctr}&nbsp;%</td>
        </tr>"""

    # Balkendiagramm-Daten als JSON
    daily_labels = [d["date"] for d in daily]
    daily_clicks = [d["clicks"] for d in daily]
    daily_banner = [d["banner"] for d in daily]

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>E-Paper Werbeklicks &ndash; Report {TODAY_DE}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; color: #1a1a1a; background: #fff; padding: 32px 40px; max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 21px; font-weight: 700; margin-bottom: 4px; }}
  h2 {{ font-size: 14px; font-weight: 600; margin: 24px 0 10px; }}
  .meta {{ color: #666; font-size: 11px; margin-bottom: 20px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 24px; }}
  .kpi {{ background: #f5f7fa; border: 1px solid #e4e7ec; border-radius: 8px; padding: 12px 14px; }}
  .kpi-label {{ font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 3px; }}
  .kpi-value {{ font-size: 22px; font-weight: 700; }}
  .kpi.blue .kpi-value {{ color: #2563eb; }}
  .kpi.green .kpi-value {{ color: #16a34a; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 12px; }}
  thead th {{ background: #f5f7fa; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: #555; padding: 7px 10px; text-align: left; border-bottom: 2px solid #e4e7ec; }}
  thead th.right {{ text-align: right; }} thead th.center {{ text-align: center; }}
  tbody tr:nth-child(odd) {{ background: #fafbfc; }}
  tbody td {{ padding: 7px 10px; border-bottom: 1px solid #eee; vertical-align: middle; }}
  tbody td.right {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tbody td.center {{ text-align: center; }}
  tbody td.url {{ color: #666; font-size: 11px; }}
  .pill {{ display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; }}
  .pill-green {{ background: #dcfce7; color: #166534; }}
  .pill-orange {{ background: #fef3c7; color: #92400e; }}
  .bz {{ color: #1d4ed8; }}
  .hk {{ color: #15803d; }}
  .bar-chart {{ margin-bottom: 6px; }}
  .bar-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }}
  .bar-label {{ width: 44px; font-size: 10px; color: #555; text-align: right; flex-shrink: 0; }}
  .bar-track {{ flex: 1; background: #e9ecef; border-radius: 2px; height: 12px; }}
  .bar-fill {{ height: 100%; border-radius: 2px; background: #3b82f6; }}
  .bar-fill.banner {{ background: #94a3b8; }}
  .bar-val {{ width: 32px; font-size: 10px; color: #444; flex-shrink: 0; }}
  .offen {{ margin-top: 4px; }}
  .offen-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 12px; }}
  footer {{ margin-top: 28px; padding-top: 10px; border-top: 1px solid #eee; font-size: 10px; color: #999; }}
  @media print {{ @page {{ margin: 12mm 14mm; size: A4; }} body {{ padding: 0; }} }}
</style>
</head>
<body>

<h1>E-Paper Werbeklicks &ndash; Werbekundenauswertung</h1>
<p class="meta">Quelle: Matomo &middot; matomo.mundschenk.de &middot; Prenly E-Paper (Site ID 14) &middot;
Stand: {TODAY_DE} &middot; Zeitraum: 01.07.2026&ndash;{TODAY_DE} &middot; Automatisch aktualisiert</p>

<div class="kpi-grid">
  <div class="kpi"><div class="kpi-label">Einblendungen gesamt</div><div class="kpi-value">{total_views:,}</div></div>
  <div class="kpi blue"><div class="kpi-label">Klicks Klickbare Anzeigen</div><div class="kpi-value">{total_clicks:,}</div></div>
  <div class="kpi blue"><div class="kpi-label">Klicks Banner / Interstitial</div><div class="kpi-value">{total_banner:,}</div></div>
  <div class="kpi green"><div class="kpi-label">&Oslash; CTR</div><div class="kpi-value">{avg_ctr}&nbsp;%</div></div>
</div>

<div class="grid2">
  <div>
    <h2>T&auml;gliche Klicks &ndash; Klickbare Anzeigen</h2>
    <div class="bar-chart" id="chart-clicks"></div>
  </div>
  <div>
    <h2>T&auml;gliche Klicks &ndash; Banner / Interstitial</h2>
    <div class="bar-chart" id="chart-banner"></div>
  </div>
</div>

<h2>Monatsvergleich</h2>
<table>
  <thead><tr>
    <th>Monat</th>
    <th class="right">Einblendungen</th>
    <th class="right">Klicks Klickb. Anz.</th>
    <th class="right">Banner-Klicks</th>
    <th class="right">&Oslash; CTR</th>
  </tr></thead>
  <tbody>{month_rows_html}</tbody>
</table>

<h2>Werbekunden &ndash; Klicks kumuliert (01.07.2026&ndash;{TODAY_DE})</h2>
{bzhk_note}<table>
  <thead><tr>
    <th>Werbekunde</th><th>Ziel-URL</th>
    <th class="right">Klicks gesamt</th>
    <th class="right" style="color:#6366f1" title="replica_box_link_click: Klicks auf PDF-eingebettete Links (klickbare Anzeige)">Klickbar</th>
    <th class="right" style="color:#0891b2" title="banner_click: HTML-Overlay-Formate (Interstitial, E-Paper-Banner, Rätselseite) – nur für Kunden mit gebuchtem Banner-Produkt (viavox, Wietzendorf Touristik, Haenel, Olaf Meyer)">Banner &#9432;</th>
    <th class="right bz" title="Klicks aus der Böhme-Zeitung (dimension2=boehmzeitung)">davon BZ</th>
    <th class="right hk" title="Klicks aus dem Heide-Kurier (dimension2=heidekurier)">davon HK</th>
    <th class="right center">Anteil</th>
    <th class="center">UTM</th><th class="center">Status</th>
  </tr></thead>
  <tbody>{adv_rows_html}</tbody>
</table>

<div class="grid2" style="margin-top:20px">
  <div>
    <h2>Offene Punkte</h2>
    <div class="offen">
      <div class="offen-item"><span class="pill pill-orange">offen</span> onclick-Code in Volksbank-Interstitial einbauen</div>
      <div class="offen-item"><span class="pill pill-orange">offen</span> UTM ?utm_campaign=vitamin-k4 an Link erg&auml;nzen</div>
      <div class="offen-item"><span class="pill pill-orange">offen</span> wietzendorf.de/amtsblatt intern kl&auml;ren</div>
    </div>
  </div>
  <div>
    <h2>Methodik</h2>
    <p style="font-size:11px;color:#555;line-height:1.5">
      Klicks = replica_box_link_click-Events, gefiltert per destination_url-Segment.
      viavox.io: contains-Filter (alle URL-Varianten). Banner: banner_click-Event.
      R&auml;tsel-Fabrik-Links herausgefiltert. CTR = Klicks &divide; Einblendungen.
    </p>
  </div>
</div>

<footer>
  Matomo 5.11.2 &middot; https://matomo.mundschenk.de &middot; Site ID 14 &middot; Europe/Berlin &middot;
  Automatisch generiert am {TODAY_DE} um 08:00 Uhr
</footer>

<script>
const DAILY_LABELS  = {json.dumps(daily_labels)};
const DAILY_CLICKS  = {json.dumps(daily_clicks)};
const DAILY_BANNER  = {json.dumps(daily_banner)};

function renderChart(id, labels, vals, cls) {{
  const max = Math.max(...vals) || 1;
  const wrap = document.getElementById(id);
  wrap.innerHTML = labels.map((l,i) => `
    <div class="bar-row">
      <div class="bar-label">${{l}}</div>
      <div class="bar-track"><div class="bar-fill ${{cls}}" style="width:${{(vals[i]/max*100).toFixed(1)}}%"></div></div>
      <div class="bar-val">${{vals[i]}}</div>
    </div>`).join('');
}}
renderChart('chart-clicks', DAILY_LABELS, DAILY_CLICKS, '');
renderChart('chart-banner', DAILY_LABELS, DAILY_BANNER, 'banner');
</script>
</body>
</html>
"""


def generate_canvas(daily, monthly, adv_clicks):
    total_clicks = sum(d["clicks"] for d in daily)
    total_views  = sum(d["views"]  for d in daily)
    ident_clicks = sum(adv_clicks.get(a["key"], {}).get("total", 0) for a in ADVERTISERS)
    avg_ctr      = f"{(total_clicks / total_views * 100):.1f}" if total_views else "0.0"

    top_adv = sorted(ADVERTISERS, key=lambda a: adv_clicks.get(a["key"], {}).get("total", 0), reverse=True)
    top3 = ", ".join(
        f'{a["name"]} ({adv_clicks.get(a["key"], {}).get("total", 0):,})'.replace(",", ".")
        for a in top_adv[:3]
    )

    daily_rows = "\n  ".join(
        f'{{ date: "{d["date"]}", views: {d["views"]}, clicks: {d["clicks"]}, banner: {d["banner"]} }},'
        for d in daily
    )
    monthly_rows = "\n  ".join(
        f'{{ month: "{m["month"]}", views: {m["views"]}, clicks: {m["clicks"]}, banner: {m["banner"]} }},'
        for m in monthly
    )
    adv_rows = "\n  ".join(
        f'{{ name: "{a["name"]}", url: "{a["url"]}", klicks: {adv_clicks.get(a["key"], {}).get("total", 0)}, bz: {adv_clicks.get(a["key"], {}).get("bz") or "null"}, hk: {adv_clicks.get(a["key"], {}).get("hk") or "null"}, utm: {js_bool(a["utm"])}, klaeren: {js_bool(a["klaeren"])} }},'
        for a in ADVERTISERS
    )

    return f"""import {{
  Grid, H1, H2, H3, Row, Stack, Stat, Text, Table,
  Callout, Pill, Divider, BarChart, useHostTheme,
}} from "cursor/canvas";

// Automatisch generiert - {TODAY_DE} - matomo-canvas-update.py

const DAILY_DATA = [
  {daily_rows}
];

const MONTHLY_DATA = [
  {monthly_rows}
];

const ADVERTISER_DATA = [
  {adv_rows}
];

export default function MatomoWerbekundenDashboard() {{
  useHostTheme();

  const totalClicks = DAILY_DATA.reduce((s, d) => s + d.clicks, 0);
  const totalViews  = DAILY_DATA.reduce((s, d) => s + d.views,  0);
  const totalBanner = DAILY_DATA.reduce((s, d) => s + d.banner, 0);
  const identKlicks = ADVERTISER_DATA.reduce((s, a) => s + a.klicks, 0);
  const avgCTR      = ((totalClicks / totalViews) * 100).toFixed(1);

  const dCategories   = DAILY_DATA.map((d) => d.date);
  const dClicksSeries = DAILY_DATA.map((d) => d.clicks);
  const dViewsSeries  = DAILY_DATA.map((d) => d.views);
  const dBannerSeries = DAILY_DATA.map((d) => d.banner);
  const mCategories   = MONTHLY_DATA.map((d) => d.month);
  const mClicksSeries = MONTHLY_DATA.map((d) => d.clicks);
  const mBannerSeries = MONTHLY_DATA.map((d) => d.banner);

  return (
    <Stack gap={{24}} style={{{{ padding: "28px 32px", maxWidth: 1100 }}}}>

      <Stack gap={{4}}>
        <H1>E-Paper Werbeklicks &ndash; Werbekundenauswertung</H1>
        <Text tone="secondary">
          Quelle: Matomo &middot; matomo.mundschenk.de &middot; Prenly E-Paper (ID 14) &middot;
          Stand: {TODAY_DE} &middot; Zeitraum: 01.07.2026&ndash;{TODAY_DE} &middot;
          Automatisch aktualisiert t&auml;glich 08:00 Uhr
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{16}}>
        <Stat label="Einblendungen gesamt"         value={{totalViews.toLocaleString("de-DE")}} />
        <Stat label="Klicks Klickbare Anzeigen"    value={{totalClicks.toLocaleString("de-DE")}} tone="info" />
        <Stat label="Klicks Banner / Interstitial" value={{totalBanner.toLocaleString("de-DE")}} tone="info" />
        <Stat label="&Oslash; CTR"                 value={{`${{avgCTR}}\u00a0%`}} tone="success" />
      </Grid>

      <Grid columns={{2}} gap={{24}}>
        <Stack gap={{12}}>
          <H2>T&auml;gliche Klicks &ndash; Klickbare Anzeigen</H2>
          <BarChart categories={{dCategories}}
            series={{[{{ name: "Klicks", data: dClicksSeries, tone: "info" }}]}}
            height={{200}} />
        </Stack>
        <Stack gap={{12}}>
          <H2>T&auml;gliche Klicks &ndash; Banner / Interstitial</H2>
          <BarChart categories={{dCategories}}
            series={{[{{ name: "Banner-Klicks", data: dBannerSeries }}]}}
            height={{200}} />
        </Stack>
      </Grid>

      <Stack gap={{12}}>
        <H2>Monatsvergleich</H2>
        <BarChart categories={{mCategories}}
          series={{[
            {{ name: "Klickbare Anzeigen", data: mClicksSeries, tone: "info" }},
            {{ name: "Banner-Klicks", data: mBannerSeries }},
          ]}}
          height={{160}} />
      </Stack>

      <Divider />

      <Stack gap={{16}}>
        <H2>Klickbare Anzeigen &ndash; Werbekunden kumuliert</H2>
        <Callout tone="success"
          title={{`${{identKlicks.toLocaleString("de-DE")}} von ${{totalClicks.toLocaleString("de-DE")}} Klicks zugeordnet \u00b7 \u00d8 CTR ${{avgCTR}}\u00a0%`}}>
          Top 3: {top3}. vitamin-k4.de und wietzendorf.de ohne UTM.
        </Callout>
        <Table
          headers={{["Werbekunde", "Ziel-URL", "Klicks kumuliert", "UTM", "Status"]}}
          rows={{[...ADVERTISER_DATA].sort((a, b) => b.klicks - a.klicks).map((a) => [
            a.name, a.url,
            a.klicks.toLocaleString("de-DE"),
            a.utm     ? <Pill tone="success" size="sm" active>ja</Pill>       : <Pill tone="warning" size="sm">nein</Pill>,
            a.klaeren ? <Pill tone="warning" size="sm">kl&auml;ren</Pill>     : <Pill tone="success" size="sm" active>aktiv</Pill>,
          ])}}
          columnAlign={{["left", "left", "right", "center", "center"]}}
          striped
        />
      </Stack>

      <Divider />

      <Grid columns={{2}} gap={{24}}>
        <Stack gap={{12}}>
          <H3>Offen</H3>
          <Stack gap={{8}}>
            {{["onclick-Code in Volksbank-Interstitial einbauen",
              "UTM ?utm_campaign=vitamin-k4 erg\u00e4nzen",
              "wietzendorf.de/amtsblatt intern kl\u00e4ren"].map((item) => (
              <Row key={{item}} gap={{8}} align="center">
                <Pill tone="warning" size="sm">offen</Pill>
                <Text>{{item}}</Text>
              </Row>
            ))}}
          </Stack>
        </Stack>
        <Stack gap={{12}}>
          <H3>Methodik</H3>
          <Text tone="secondary" size="small">
            Klickbare Anzeigen: replica_box_link_click via destination_url-Segment.
            viavox.io: contains-Filter. R&auml;tsel-Fabrik herausgefiltert.
            Banner: banner_click. Auto-Update t&auml;glich 08:00 via launchd.
          </Text>
        </Stack>
      </Grid>

      <Text tone="secondary" size="small">
        Matomo 5.11.2 &middot; https://matomo.mundschenk.de &middot; Site ID 14 &middot; Europe/Berlin
        &middot; Zuletzt: {TODAY_DE} 08:00
      </Text>
    </Stack>
  );
}}
"""


def generate_customer_html(adv, clicks):
    """Generiert einen druckfertigen Einzelbericht pro Werbekunde."""
    name     = adv["name"]
    url_disp = adv["url"]
    total    = clicks.get("total", 0)
    klickbar = clicks.get("klickbar", 0)
    banner   = clicks.get("banner", 0)
    has_banner_product = adv.get("banner", False)
    bz_raw   = clicks.get("bz")   # None wenn Batch nicht verfügbar
    hk_raw   = clicks.get("hk")   # None wenn Batch nicht verfügbar
    split_available = bz_raw is not None and hk_raw is not None
    bz       = bz_raw if split_available else 0
    hk       = hk_raw if split_available else 0
    mag      = max(0, total - bz - hk) if split_available else 0

    def pct(v):
        return f"{(v / total * 100):.0f}" if total else "–"

    def bar(v, max_v, color):
        w = round(v / max_v * 100) if max_v else 0
        return f'<div style="background:{color};height:12px;border-radius:3px;width:{w}%;min-width:2px"></div>'

    max_pub = max(bz, hk, mag, 1)

    # Pre-computed Ausgabewerte für den Publikations-Split
    if split_available:
        pub_unavail_note = ""
        pub_bar_bz  = bar(bz,  max_pub, "#1d4ed8")
        pub_bar_hk  = bar(hk,  max_pub, "#16a34a")
        pub_bar_mag = bar(mag, max_pub, "#9ca3af")
        pub_val_bz  = f"{bz:,}"
        pub_val_hk  = f"{hk:,}"
        pub_val_mag = f"{mag:,}"
        pub_pct_bz  = f"{pct(bz)}&thinsp;%"
        pub_pct_hk  = f"{pct(hk)}&thinsp;%"
        pub_pct_mag = f"{pct(mag)}&thinsp;%"
    else:
        pub_unavail_note = '<div class="note" style="margin-bottom:12px">Aufteilung BZ&nbsp;/&nbsp;HK aktuell nicht verf&uuml;gbar (Matomo-Server-Einschr&auml;nkung). Gesamt-Klicks sind korrekt.</div>'
        pub_bar_bz = pub_bar_hk = pub_bar_mag = ""
        pub_val_bz = pub_val_hk = pub_val_mag = "&ndash;"
        pub_pct_bz = pub_pct_hk = pub_pct_mag = ""

    # KPI-Block und Format-Split für Banner nur wenn Banner-Produkt gebucht
    if has_banner_product:
        kpi_grid_cols = "repeat(3,1fr)"
        banner_kpi_block = f"""  <div class="kpi">
    <div class="kpi-label">Banner / Interstitial</div>
    <div class="kpi-value" style="color:#0891b2">{banner:,}</div>
    <div class="kpi-sub">banner_click</div>
  </div>"""
        format_split_section = f"""<div class="section">
  <div class="section-title">Verteilung nach Anzeigenformat</div>
  <div class="split-row">
    <div class="split-label">Klickbare Anzeige</div>
    <div class="split-bar">{bar(klickbar, max(klickbar, banner, 1), "#6366f1")}</div>
    <div class="split-val">{klickbar:,}</div>
    <div class="split-pct">{pct(klickbar)}&thinsp;%</div>
  </div>
  <div class="split-row">
    <div class="split-label">Banner / Interstitial</div>
    <div class="split-bar">{bar(banner, max(klickbar, banner, 1), "#0891b2")}</div>
    <div class="split-val">{banner:,}</div>
    <div class="split-pct">{pct(banner)}&thinsp;%</div>
  </div>
</div>"""
    else:
        kpi_grid_cols = "repeat(2,1fr)"
        banner_kpi_block = ""
        format_split_section = ""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Klick-Bericht – {name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         font-size: 13px; color: #1a1a1a; background: #fff; padding: 36px 44px; max-width: 720px; margin: 0 auto; }}
  .logo-bar {{ display:flex; align-items:center; gap:12px; margin-bottom:24px; border-bottom:2px solid #e4e7ec; padding-bottom:14px; }}
  .logo-text {{ font-size:15px; font-weight:700; color:#1e40af; letter-spacing:-.01em; }}
  .logo-sub  {{ font-size:10px; color:#6b7280; text-transform:uppercase; letter-spacing:.06em; }}
  h1 {{ font-size:20px; font-weight:700; margin-bottom:4px; }}
  .subtitle {{ font-size:12px; color:#6b7280; margin-bottom:24px; }}
  .kpi-grid {{ display:grid; grid-template-columns:{kpi_grid_cols}; gap:12px; margin-bottom:28px; }}
  .kpi {{ border:1px solid #e4e7ec; border-radius:10px; padding:14px 16px; background:#f8fafc; }}
  .kpi-label {{ font-size:10px; color:#6b7280; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }}
  .kpi-value {{ font-size:26px; font-weight:800; }}
  .kpi-sub   {{ font-size:10px; color:#9ca3af; margin-top:2px; }}
  .section {{ margin-bottom:24px; }}
  .section-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em;
                    color:#6b7280; border-bottom:1px solid #e4e7ec; padding-bottom:6px; margin-bottom:12px; }}
  .split-row {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
  .split-label {{ width:120px; font-size:12px; font-weight:600; flex-shrink:0; }}
  .split-bar   {{ flex:1; background:#f1f5f9; border-radius:3px; height:12px; overflow:hidden; }}
  .split-val   {{ width:50px; text-align:right; font-size:12px; font-variant-numeric:tabular-nums; }}
  .split-pct   {{ width:36px; text-align:right; font-size:11px; color:#9ca3af; }}
  .note {{ background:#f0f9ff; border-left:3px solid #0ea5e9; padding:10px 14px;
           font-size:11px; color:#0c4a6e; border-radius:0 6px 6px 0; margin-bottom:20px; }}
  footer {{ margin-top:30px; padding-top:10px; border-top:1px solid #e4e7ec;
            font-size:10px; color:#9ca3af; line-height:1.6; }}
  .print-btn {{ display:inline-block; margin-bottom:18px; padding:8px 18px; background:#1d4ed8;
               color:#fff; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer;
               border:none; text-decoration:none; }}
  @media print {{ .print-btn {{ display:none; }} @page {{ margin:14mm 16mm; size:A4; }} }}
</style>
</head>
<body>

<div class="logo-bar">
  <div>
    <div class="logo-text">Böhme-Zeitung / Heide-Kurier</div>
    <div class="logo-sub">Prenly E-Paper &middot; Online-Werbung</div>
  </div>
</div>

<button class="print-btn" onclick="window.print()">&#128438; Als PDF speichern / Drucken</button>

<h1>Klick-Bericht: {name}</h1>
<p class="subtitle">Zeitraum: 01.07.2026 – {TODAY_DE} &middot; Ziel-URL: {url_disp} &middot; Stand: {TODAY_DE}</p>

<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">Klicks gesamt</div>
    <div class="kpi-value">{total:,}</div>
    <div class="kpi-sub">seit 01.07.2026</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Klickbare Anzeige</div>
    <div class="kpi-value" style="color:#6366f1">{klickbar:,}</div>
    <div class="kpi-sub">replica_box_link_click</div>
  </div>
{banner_kpi_block}
</div>

<div class="section">
  <div class="section-title">Verteilung nach Publikation</div>
  {pub_unavail_note}
  <div class="split-row">
    <div class="split-label">Böhme-Zeitung</div>
    <div class="split-bar">{pub_bar_bz}</div>
    <div class="split-val">{pub_val_bz}</div>
    <div class="split-pct">{pub_pct_bz}</div>
  </div>
  <div class="split-row">
    <div class="split-label">Heide-Kurier</div>
    <div class="split-bar">{pub_bar_hk}</div>
    <div class="split-val">{pub_val_hk}</div>
    <div class="split-pct">{pub_pct_hk}</div>
  </div>
  <div class="split-row">
    <div class="split-label">Magazin</div>
    <div class="split-bar">{pub_bar_mag}</div>
    <div class="split-val">{pub_val_mag}</div>
    <div class="split-pct">{pub_pct_mag}</div>
  </div>
</div>

<div class="section">
{format_split_section}

<div class="note">
  Alle Klick-Daten stammen aus Matomo (matomo.mundschenk.de, Site&nbsp;ID&nbsp;14). 
  Erfasst werden ausschlie&szlig;lich Interaktionen im Prenly-E-Paper der 
  B&ouml;hme-Zeitung und des Heide-Kuriers. Der Bericht wird t&auml;glich automatisch aktualisiert.
</div>

<footer>
  B&ouml;hme-Zeitung / Heide-Kurier &middot; Prenly E-Paper &middot;
  Generiert am {TODAY_DE} &middot; matomo.mundschenk.de &middot; Site ID 14
</footer>

</body>
</html>
"""


def generate_all_customer_pages(adv_clicks):
    """Schreibt pro Werbekunde eine individuelle HTML-Seite nach berichte/<key>.html."""
    berichte_dir = os.path.join(_HERE, "berichte")
    os.makedirs(berichte_dir, exist_ok=True)
    for a in ADVERTISERS:
        clicks = adv_clicks.get(a["key"], {"total": 0, "klickbar": 0, "banner": 0, "bz": 0, "hk": 0})
        html   = generate_customer_html(a, clicks)
        path   = os.path.join(berichte_dir, f"{a['key']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    log(f"  {len(ADVERTISERS)} Kundenberichte gespeichert in {berichte_dir}")


def main():
    log("=== Matomo Canvas Update gestartet ===")
    log(f"Zeitraum: {START} - {TODAY}")

    try:
        log("Hole taegliche Daten...")
        daily = fetch_daily_data()
        log(f"  {len(daily)} Tage geladen")

        log("Hole Monatsdaten...")
        monthly = fetch_monthly_data()
        log(f"  {len(monthly)} Monate geladen")

        log("Hole Werbekunden-Klicks (parallel)...")
        adv_clicks_raw = {}
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(fetch_advertiser_clicks, a): a for a in ADVERTISERS}
            for future in as_completed(futures):
                key, data = future.result()
                adv_clicks_raw[key] = data
                log(f"  {key}: klickbar={data['klickbar']} banner={data['banner']}")

        adv_clicks = {}
        for a in ADVERTISERS:
            raw = adv_clicks_raw.get(a["key"], {"klickbar": 0, "banner": 0, "total": 0})
            split = compute_bz_hk_split(raw["total"], a)
            adv_clicks[a["key"]] = {**raw, "bz": split["bz"], "hk": split["hk"]}
            c = adv_clicks[a["key"]]
            log(f"  {a['key']}: gesamt={c['total']} klickbar={c['klickbar']} banner={c['banner']} BZ={c['bz']} HK={c['hk']}")

        log("Generiere und schreibe Canvas...")
        canvas_code = generate_canvas(daily, monthly, adv_clicks)
        canvas_dir = os.path.dirname(CANVAS)
        if canvas_dir and os.path.isdir(canvas_dir):
            with open(CANVAS, "w", encoding="utf-8") as f:
                f.write(canvas_code)
            log(f"Canvas gespeichert: {CANVAS}")
        else:
            log("Canvas-Verzeichnis nicht vorhanden – Canvas-Ausgabe übersprungen.")

        log("Generiere HTML-Report...")
        html_code = generate_html(daily, monthly, adv_clicks)
        with open(HTML_OUT, "w", encoding="utf-8") as f:
            f.write(html_code)
        log(f"HTML gespeichert: {HTML_OUT}")

        log("Generiere individuelle Kundenberichte...")
        generate_all_customer_pages(adv_clicks)
        log("=== Update erfolgreich abgeschlossen ===")

    except Exception as e:
        log(f"FEHLER: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
