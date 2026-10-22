#!/usr/bin/env python3
"""
Automatische Neukunden-Erkennung – täglich vor matomo-canvas-update.py

1. Liest alle Hausdienst-Links aus den letzten 14 Tagen in Matomo
2. Prüft, ob der utm_campaign-Wert bereits in ADVERTISERS oder neukunden.json erfasst ist
3. Bei neuem Kunden: Suche in Pipedrive nach dem Org-Namen
4. Trägt den Kunden in neukunden.json ein (klaeren=False wenn Pipedrive-Treffer, sonst True)
5. Committet neukunden.json via Git

matomo-canvas-update.py liest neukunden.json automatisch ein.
"""

import urllib.request, urllib.parse, json, os, re, subprocess, datetime, sys

_HERE           = os.path.dirname(os.path.abspath(__file__))
TOKEN           = os.environ.get("MATOMO_TOKEN", "")
PIPEDRIVE_TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN", "")
SITE_ID         = 14
MATOMO_BASE     = "https://matomo.mundschenk.de/index.php"
NEUKUNDEN_PATH  = os.path.join(_HERE, "neukunden.json")
LOG             = os.path.join(_HERE, "matomo-canvas-update.log")

# UTM-Werte, die KEINE Werbekunden sind (interne Links, redaktionelle Inhalte)
IGNORE_UTMS = {
    "boehme-zeitung", "mundschenk-it", "podium", "podium-landratswahl",
    "podium-kreistagswahl", "appdownload", "newsletter",
}


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Neukunden] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def matomo_post(params, timeout=90):
    p = {**params, "token_auth": TOKEN, "idSite": str(SITE_ID), "format": "JSON"}
    data = urllib.parse.urlencode(p).encode()
    req = urllib.request.Request(MATOMO_BASE, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def pipedrive_search(term):
    """Sucht Org-Name in Pipedrive. Gibt (id, name, url) oder None zurück."""
    if not PIPEDRIVE_TOKEN:
        return None
    url = (f"https://api.pipedrive.com/v1/organizations/search"
           f"?term={urllib.parse.quote(term)}&limit=3&api_token={PIPEDRIVE_TOKEN}")
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        items = (data.get("data") or {}).get("items") or []
        if items:
            best = items[0]["item"]
            custom = best.get("custom_fields") or []
            website = next((c for c in custom if c and ("http" in str(c).lower() or "www" in str(c).lower())), "")
            return {"id": best["id"], "name": best["name"], "url": website}
    except Exception as e:
        log(f"  Pipedrive-Fehler bei '{term}': {e}")
    return None


def utm_to_search_term(utm: str) -> str:
    """Wandelt utm_campaign in einen sinnvollen Suchbegriff um.
    'schlamann-autokrane' → 'Schlamann Autokrane'
    'mvg-mathe' → 'Mvg Mathe' (Pipedrive findet es trotzdem)
    """
    return " ".join(w.capitalize() for w in utm.replace("-", " ").replace("_", " ").split())


def utm_to_key(utm: str) -> str:
    return re.sub(r'[^a-z0-9]', '_', utm.lower()).strip("_")


def load_neukunden() -> list:
    if os.path.exists(NEUKUNDEN_PATH):
        with open(NEUKUNDEN_PATH) as f:
            return json.load(f)
    return []


def save_neukunden(data: list):
    with open(NEUKUNDEN_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_advertisers_segs() -> set:
    """Alle Segment-Werte aus matomo-canvas-update.py + neukunden.json extrahieren."""
    segs = set()
    try:
        with open(os.path.join(_HERE, "matomo-canvas-update.py")) as f:
            src = f.read()
        for m in re.finditer(r'"seg":\s*"([^"]+)"', src):
            segs.add(urllib.parse.unquote(m.group(1)).lower())
    except Exception:
        pass
    for entry in load_neukunden():
        segs.add(urllib.parse.unquote(entry.get("seg", "")).lower())
    return segs


def is_covered(utm: str, segs: set) -> bool:
    """Prüft ob der utm-Wert durch irgendeinen bestehenden Filter abgedeckt ist."""
    for seg in segs:
        if "=@" in seg:          # contains
            fval = seg.split("=@")[1]
            if fval in utm:
                return True
        elif "==" in seg:         # exact – Hausdienst-URL würde nicht exakt matchen
            pass
    return False


def get_recent_hausdienst_utms(days: int = 14) -> dict:
    """Gibt dict {utm_campaign: hits} für die letzten `days` Tage zurück."""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days)
    raw = matomo_post({
        "module": "API",
        "method": "CustomDimensions.getCustomDimension",
        "idDimension": "14",
        "period": "range",
        "date": f"{start},{today}",
        "filter_limit": "300",
    }, timeout=120)
    result = {}
    if not isinstance(raw, list):
        return result
    for item in raw:
        url = item.get("label", "")
        if "hausdienst" not in url.lower():
            continue
        m = re.search(r'utm_campaign=([^&\s\-]+(?:-[^&\s]+)*)', url, re.I)
        if not m:
            continue
        utm = m.group(1).lower()
        if utm in IGNORE_UTMS:
            continue
        result[utm] = result.get(utm, 0) + item.get("nb_hits", 0)
    return result


def main():
    log("=== Neukunden-Erkennung gestartet ===")

    utms = get_recent_hausdienst_utms(days=14)
    log(f"  {len(utms)} Hausdienst-UTMs der letzten 14 Tage gefunden")

    segs       = load_advertisers_segs()
    neukunden  = load_neukunden()
    existing_keys = {e["key"] for e in neukunden}
    added = 0

    for utm, hits in sorted(utms.items(), key=lambda x: -x[1]):
        if is_covered(utm, segs):
            continue  # bereits erfasst

        key = utm_to_key(utm)
        if key in existing_keys:
            continue  # bereits in neukunden.json

        log(f"  NEU entdeckt: utm_campaign={utm} ({hits} Hits) → suche in Pipedrive …")

        search_term = utm_to_search_term(utm)
        org = pipedrive_search(search_term)

        if org:
            log(f"    → Pipedrive-Treffer: {org['name']} (ID {org['id']})")
            # URL aus Pipedrive oder aus UTM ableiten
            raw_url = org["url"] or ""
            url_clean = re.sub(r'^https?://(www\.)?', '', raw_url).rstrip("/") or f"{utm}.de"
            entry = {
                "key":              key,
                "pub":              "both",   # konservativ; kann manuell korrigiert werden
                "pipedrive_org_id": org["id"],
                "name":             org["name"],
                "url":              url_clean,
                "seg":              f"dimension14%3D%40{utm}",
                "utm":              False,
                "klaeren":          False,
                "auto_discovered":  True,
            }
        else:
            log(f"    → kein Pipedrive-Treffer für '{search_term}' – als 'klaeren' markiert")
            entry = {
                "key":              key,
                "pub":              "both",
                "pipedrive_org_id": None,
                "name":             search_term,
                "url":              f"{utm}.de",
                "seg":              f"dimension14%3D%40{utm}",
                "utm":              False,
                "klaeren":          True,
                "auto_discovered":  True,
            }

        neukunden.append(entry)
        existing_keys.add(key)
        added += 1
        log(f"    → eingetragen: {entry['name']} | Filter: contains {utm} | klaeren={entry['klaeren']}")

    if added > 0:
        save_neukunden(neukunden)
        log(f"  {added} neue Kunden in neukunden.json gespeichert")
        # Git commit
        try:
            subprocess.run(["git", "-C", _HERE, "add", "neukunden.json"], check=True)
            subprocess.run(["git", "-C", _HERE, "commit", "-m",
                            f"auto: {added} Neukunde(n) entdeckt ({datetime.date.today()})"],
                           check=True)
            subprocess.run(["git", "-C", _HERE, "push", "origin", "main"], check=True)
            log("  Git-Push erfolgreich")
        except subprocess.CalledProcessError as e:
            log(f"  Git-Fehler: {e}")
    else:
        log("  Keine neuen Kunden gefunden.")

    log("=== Neukunden-Erkennung abgeschlossen ===")


if __name__ == "__main__":
    main()
