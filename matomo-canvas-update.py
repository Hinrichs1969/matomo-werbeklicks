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
    {"key": "viavox",         "name": "viavox.io",                    "url": "viavox.io",                      "seg": "dimension14%3D%40viavox.io",                                                                                                                                                                        "utm": True,  "klaeren": False},
    {"key": "vitamin_k4",     "name": "vitamin-k4.de",                "url": "vitamin-k4.de",                  "seg": "dimension14%3D%3Dhttp%3A%2F%2Fwww.vitamin-k4.de",                                                                                                                                                  "utm": False, "klaeren": False},
    {"key": "smurfitkappa",   "name": "smurfitkappa",                 "url": "smurfitkappa.concludis.de",      "seg": "dimension14%3D%3Dhttps%3A%2F%2Fsmurfitkappa.concludis.de%2Fprj%2Fshw%2F643fb86c8172fb56d8898497eb682c27_0%2F13796%2F%3Futm_campaign%3Dsmurfitkappa",                                                "utm": True,  "klaeren": False},
    {"key": "harbort",        "name": "Harbort GmbH & Co. KG",        "url": "harbort.de/karriere",            "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.harbort.de%2Fkarriere%3Futm_campaign%3Dharbort",                                                                                                                "utm": True,  "klaeren": False},
    {"key": "hotel_park",     "name": "hotel-park-soltau",            "url": "hotel-park-soltau.de",           "seg": "dimension14%3D%3Dhttps%3A%2F%2Fhotel-park-soltau.de%2Faktuellestellenangebote%2F%3Futm_campaign%3Dhotel-park-soltau",                                                                               "utm": True,  "klaeren": False},
    {"key": "stadt_munster",  "name": "stadt_munster",                "url": "bewerbung.munster.de",           "seg": "dimension14%3D%40bewerbung.munster.de",                                                                                                                                                            "utm": True,  "klaeren": False},
    {"key": "stadt_walsrode", "name": "stadt-walsrode",               "url": "jobs.stadt-walsrode.de",         "seg": "dimension14%3D%3Dhttps%3A%2F%2Fjobs.stadt-walsrode.de%2Ft254r%3Futm_campaign%3Dstadt-walsrode",                                                                                                    "utm": True,  "klaeren": False},
    {"key": "buergerliste",   "name": "bispinger-buergerliste",       "url": "bispinger-buergerliste.de",      "seg": "dimension14%3D%3Dhttp%3A%2F%2Fwww.bispinger-buergerliste.de%3Futm_campaign%3Dbuergerliste",                                                                                                        "utm": True,  "klaeren": False},
    {"key": "wietzendorf",    "name": "wietzendorf.de",               "url": "wietzendorf.de/amtsblatt",       "seg": "dimension14%3D%3Dhttp%3A%2F%2Fwww.wietzendorf.de%2Famtsblatt",                                                                                                                                    "utm": False, "klaeren": True },
    {"key": "stadtwerke_mb",  "name": "stadtwerke-munster-bispingen", "url": "ihr-stadtwerk.de",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.ihr-stadtwerk.de%2Fde%2FMenue%2FKarriere%2F%3Futm_campaign%3DStadtwerke-Munster-Bispingen-GmbH",                                                               "utm": True,  "klaeren": False},
    {"key": "landesforsten",  "name": "niedersaechs.-landesforsten",  "url": "landesforsten.de",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.landesforsten.de%2F%3Futm_campaign%3Dniedersaechsische-landesforsten",                                                                                          "utm": True,  "klaeren": False},
    {"key": "bundeswehr",     "name": "bundeswehr",                   "url": "bewerbung.bundeswehr-karriere.de","seg": "dimension14%3D%3Dhttps%3A%2F%2Fbewerbung.bundeswehr-karriere.de%2F%3Futm_campaign%3Dbundeswehr",                                                                                                  "utm": True,  "klaeren": False},
    {"key": "spd",            "name": "SPD Schneverdingen",           "url": "spd-heidekreis.de",              "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.spd-heidekreis.de%2Fwahlen-2026%2F%3Futm_campaign%3DSPD",                                                                                                      "utm": True,  "klaeren": False},
    {"key": "sushi",          "name": "Sushi Bar Soltau",             "url": "sushi-soltau.de",                "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.sushi-soltau.de%2F%3Futm_campaign%3DSushiBar",                                                                                                                  "utm": True,  "klaeren": False},
    {"key": "grillhus",       "name": "Grillhus",                     "url": "grillhus.de/jobs",               "seg": "dimension14%3D%3Dhttps%3A%2F%2Fgrillhus.de%2Fjobs%2F%3Futm_campaign%3Dgrillhus",                                                                                                                  "utm": True,  "klaeren": False},
    {"key": "maderos",        "name": "Maderos",                      "url": "maderos.de",                     "seg": "dimension14%3D%3Dhttps%3A%2F%2Fwww.maderos.de%3Futm_campaign%3Dmaderos",                                                                                                                          "utm": True,  "klaeren": False},
    {"key": "hatesohl",       "name": "Bestattungen Hatesohl",        "url": "bestattungen-hatesohl.de",       "seg": "dimension14%3D%40bestattungen-hatesohl.de",                                                                                                                                                        "utm": True,  "klaeren": False},
]


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def matomo_post(params):
    p = dict(params)
    p["token_auth"] = TOKEN
    p["idSite"]     = str(SITE_ID)
    p["format"]     = "JSON"
    data = urllib.parse.urlencode(p).encode()
    req  = urllib.request.Request(BASE_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


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
    raw = matomo_post({
        "module": "API", "method": "Events.getName",
        "period": "range", "date": f"{START},{TODAY}",
        "filter_limit": "20",
        "segment": adv["seg"],
    })
    if isinstance(raw, list):
        for e in raw:
            if e.get("label") == "replica_box_link_click":
                return adv["key"], e.get("nb_events", 0)
    return adv["key"], 0


def js_bool(v):
    return "true" if v else "false"


def generate_html(daily, monthly, adv_clicks):
    """Generiert einen druckfertigen HTML-Report zum Teilen mit Kollegen."""
    total_clicks = sum(d["clicks"] for d in daily)
    total_views  = sum(d["views"]  for d in daily)
    total_banner = sum(d["banner"] for d in daily)
    ident_clicks = sum(adv_clicks.get(a["key"], 0) for a in ADVERTISERS)
    avg_ctr      = f"{(total_clicks / total_views * 100):.1f}" if total_views else "0.0"

    sorted_adv = sorted(ADVERTISERS, key=lambda a: adv_clicks.get(a["key"], 0), reverse=True)

    # Tabellen-Zeilen
    adv_rows_html = ""
    for a in sorted_adv:
        k = adv_clicks.get(a["key"], 0)
        share = f"{(k / total_clicks * 100):.1f}" if total_clicks else "0.0"
        utm_pill   = '<span class="pill pill-green">ja</span>'   if a["utm"]     else '<span class="pill pill-orange">nein</span>'
        klaer_pill = '<span class="pill pill-orange">klaeren</span>' if a["klaeren"] else '<span class="pill pill-green">aktiv</span>'
        adv_rows_html += f"""
        <tr>
          <td><strong>{a["name"]}</strong></td>
          <td class="url">{a["url"]}</td>
          <td class="right"><strong>{k:,}</strong></td>
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
<table>
  <thead><tr>
    <th>Werbekunde</th><th>Ziel-URL</th>
    <th class="right">Klicks</th><th class="right center">Anteil</th>
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
    ident_clicks = sum(adv_clicks.get(a["key"], 0) for a in ADVERTISERS)
    avg_ctr      = f"{(total_clicks / total_views * 100):.1f}" if total_views else "0.0"

    top_adv = sorted(ADVERTISERS, key=lambda a: adv_clicks.get(a["key"], 0), reverse=True)
    top3 = ", ".join(
        f'{a["name"]} ({adv_clicks.get(a["key"], 0):,})'.replace(",", ".")
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
        f'{{ name: "{a["name"]}", url: "{a["url"]}", klicks: {adv_clicks.get(a["key"], 0)}, utm: {js_bool(a["utm"])}, klaeren: {js_bool(a["klaeren"])} }},'
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
        adv_clicks = {}
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(fetch_advertiser_clicks, a): a for a in ADVERTISERS}
            for future in as_completed(futures):
                key, clicks = future.result()
                adv_clicks[key] = clicks
                log(f"  {key}: {clicks}")

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

        log("=== Update erfolgreich abgeschlossen ===")

    except Exception as e:
        log(f"FEHLER: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
