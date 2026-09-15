#!/usr/bin/env python3
"""Fetch Pipedrive OKR deals/activities and regenerate the HTML dashboard."""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"
HTML_PATH = ROOT / "index.html"
ENV_PATH = ROOT / ".env"

CYCLE_START = "2026-07-13"
ONLINE_RUBRIK_IDS = {"2693", "2732", "2733", "2734", "2735", "2736", "2738"}
RUBRIK_KEY = "bed1d24238b4b8c4f0feeaf8a18c26d6378dc9de"
DB_CALC_KEY = "bb4659fad0c7d06302b2dc8bc6a22ebf7b854630"
DB_SATZ_KEY = "2aa964716a95d7e3153bd2d97659fdbc5d9b93c6"
VERMITTLUNGEN_ID = "2651"
SPEZIALISTEN_ID = "2500"
PIPELINE_SONSTIGE = 34
PIPELINE_ANZEIGEN = 32
ACTIVITY_CROSS_SELLING = "cross_selling"

RUBRIK_LABELS = {
    "2693": "Rätselseite",
    "2732": "Premiumbanner HK online",
    "2733": "Standardbanner HK online",
    "2734": "Native Advertising HK online",
    "2735": "Banner E-Paper-Startseite",
    "2736": "Interstitial E-Paper",
    "2738": "klickbare Anzeige",
    "2651": "Vermittlungen",
    "2541": "jobsfuerniedersachsen",
}


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    token = os.environ["PIPEDRIVE_API_TOKEN"]
    params = {**(params or {}), "api_token": token}
    url = f"https://api.pipedrive.com/v1/{path}?{urllib.parse.urlencode(params)}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    timeout = float(os.environ.get("PIPEDRIVE_TIMEOUT", "120"))
    attempts = int(os.environ.get("PIPEDRIVE_RETRIES", "4"))
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if not payload.get("success"):
                raise RuntimeError(f"Pipedrive API error for {path}: {payload}")
            return payload
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            # 429/5xx: retry; other HTTP errors: fail immediately
            if exc.code in (429, 500, 502, 503, 504) and attempt < attempts:
                time.sleep(min(2 ** attempt, 30))
                last_exc = RuntimeError(f"Pipedrive {method} {path} failed: {exc.code} {detail}")
                continue
            raise RuntimeError(f"Pipedrive {method} {path} failed: {exc.code} {detail}") from exc
        except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"Pipedrive {method} {path} failed after {attempts} attempts: {last_exc}") from last_exc


def api_get(path: str, params: dict | None = None) -> dict:
    return api_request("GET", path, params=params)


def api_put(path: str, body: dict, params: dict | None = None) -> dict:
    return api_request("PUT", path, params=params, body=body)


def paginate(path: str, params: dict) -> list[dict]:
    items: list[dict] = []
    start = 0
    while True:
        payload = api_get(path, {**params, "start": start, "limit": 500})
        batch = payload.get("data") or []
        items.extend(batch)
        pagination = (payload.get("additional_data") or {}).get("pagination") or {}
        if not pagination.get("more_items_in_collection"):
            break
        start = pagination.get("next_start", start + len(batch))
    return items


def parse_day(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        return datetime.strptime(stamp[:10], "%Y-%m-%d")
    except ValueError:
        return None


def in_cycle(stamp: str | None) -> bool:
    day = parse_day(stamp)
    if not day:
        return False
    return day >= datetime.strptime(CYCLE_START, "%Y-%m-%d")


def week_label(stamp: str | None) -> str:
    day = parse_day(stamp)
    if not day:
        return "?"
    return f"W{day.isocalendar().week:02d}"


def fetch_filter_deals(filter_id: int) -> list[dict]:
    return paginate("deals", {"filter_id": filter_id, "status": "all_not_deleted"})


def fetch_rubrik_labels() -> dict[str, str]:
    labels = dict(RUBRIK_LABELS)
    try:
        for field in api_get("dealFields").get("data") or []:
            if field.get("key") == RUBRIK_KEY:
                for opt in field.get("options") or []:
                    labels[str(opt["id"])] = opt["label"]
    except Exception:
        pass
    return labels


def db_of(deal: dict) -> float:
    raw = deal.get(DB_CALC_KEY)
    if raw not in (None, ""):
        return float(raw)
    satz = deal.get(DB_SATZ_KEY)
    value = float(deal.get("value") or 0)
    if satz not in (None, ""):
        return value * float(satz)
    rubrik = str(deal.get(RUBRIK_KEY) or "")
    if deal.get("pipeline_id") == PIPELINE_ANZEIGEN and rubrik in ONLINE_RUBRIK_IDS:
        return value
    return 0.0


def backfill_online_db_satz(deals: list[dict]) -> dict:
    updated = 0
    skipped = 0
    errors: list[str] = []
    for deal in deals:
        if deal.get("status") != "won":
            continue
        if not in_cycle(deal.get("won_time") or deal.get("close_time") or deal.get("add_time")):
            continue
        rubrik = str(deal.get(RUBRIK_KEY) or "")
        is_online = deal.get("pipeline_id") == PIPELINE_ANZEIGEN and rubrik in ONLINE_RUBRIK_IDS
        if not is_online:
            continue
        satz = deal.get(DB_SATZ_KEY)
        if satz not in (None, "") and float(satz) == 1:
            skipped += 1
            continue
        try:
            api_put(
                f"deals/{deal['id']}",
                {DB_SATZ_KEY: 1},
            )
            updated += 1
            deal[DB_SATZ_KEY] = 1
            if deal.get(DB_CALC_KEY) in (None, ""):
                deal[DB_CALC_KEY] = float(deal.get("value") or 0)
            time.sleep(0.12)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{deal.get('id')}: {exc}")
    return {"updated": updated, "already_ok": skipped, "errors": errors[:10], "error_count": len(errors)}


def build_db_metrics(deals: list[dict], goal: float, labels: dict[str, str]) -> dict:
    buckets = defaultdict(lambda: {"n": 0, "db": 0.0, "value": 0.0, "missing_db": 0})
    weekly: dict[str, dict[str, float]] = defaultdict(
        lambda: {"vermittlungen": 0.0, "sonstige_rest": 0.0, "online_anzeigen": 0.0}
    )
    online_by_rubrik: dict[str, dict] = defaultdict(lambda: {"n": 0, "db": 0.0})

    for deal in deals:
        if deal.get("status") != "won":
            continue
        if not in_cycle(deal.get("won_time") or deal.get("close_time")):
            continue

        pipe = deal.get("pipeline_id")
        rubrik = str(deal.get(RUBRIK_KEY) or "")
        value = float(deal.get("value") or 0)
        db = db_of(deal)
        missing = deal.get(DB_CALC_KEY) in (None, "")
        week = week_label(deal.get("won_time") or deal.get("close_time"))

        if pipe == PIPELINE_SONSTIGE and rubrik == VERMITTLUNGEN_ID:
            key = "vermittlungen"
            weekly[week]["vermittlungen"] += db
        elif pipe == PIPELINE_ANZEIGEN and rubrik in ONLINE_RUBRIK_IDS:
            key = "online_anzeigen"
            weekly[week]["online_anzeigen"] += db
            label = labels.get(rubrik, RUBRIK_LABELS.get(rubrik, rubrik))
            online_by_rubrik[label]["n"] += 1
            online_by_rubrik[label]["db"] += db
        elif pipe == PIPELINE_SONSTIGE and rubrik != SPEZIALISTEN_ID:
            key = "sonstige_rest"
            weekly[week]["sonstige_rest"] += db
        elif rubrik in ONLINE_RUBRIK_IDS:
            key = "online_anzeigen"
            weekly[week]["online_anzeigen"] += db
            label = labels.get(rubrik, RUBRIK_LABELS.get(rubrik, rubrik))
            online_by_rubrik[label]["n"] += 1
            online_by_rubrik[label]["db"] += db
        else:
            continue

        buckets[key]["n"] += 1
        buckets[key]["db"] += db
        buckets[key]["value"] += value
        if missing:
            buckets[key]["missing_db"] += 1

    def seg(name: str) -> dict:
        b = buckets[name]
        return {
            "n": b["n"],
            "db": round(b["db"], 2),
            "value": round(b["value"], 2),
            "missing_db": b["missing_db"],
        }

    segments = {
        "vermittlungen": seg("vermittlungen"),
        "sonstige_rest": seg("sonstige_rest"),
        "online_anzeigen": seg("online_anzeigen"),
    }
    total = sum(s["db"] for s in segments.values())

    return {
        "goal": goal,
        "total_db": round(total, 2),
        "progress_pct": round(100 * total / goal, 1) if goal else 0,
        "remaining": round(max(goal - total, 0), 2),
        "deal_count": sum(s["n"] for s in segments.values()),
        "segments": segments,
        "online_by_rubrik": {
            k: {"n": v["n"], "db": round(v["db"], 2)}
            for k, v in sorted(online_by_rubrik.items(), key=lambda x: -x[1]["db"])
        },
        "weekly_db": [
            {
                "week": week,
                "vermittlungen": round(vals["vermittlungen"], 2),
                "sonstige_rest": round(vals["sonstige_rest"], 2),
                "online_anzeigen": round(vals["online_anzeigen"], 2),
                "total": round(
                    vals["vermittlungen"] + vals["sonstige_rest"] + vals["online_anzeigen"],
                    2,
                ),
            }
            for week, vals in sorted(weekly.items())
        ],
    }


def fetch_cross_selling_activities() -> list[dict]:
    """Company-wide: API token is user-scoped unless we iterate owners."""
    users = api_get("users").get("data") or []
    end = datetime.now().strftime("%Y-%m-%d")
    seen: set[int] = set()
    activities: list[dict] = []
    for user in users:
        if not user.get("active_flag"):
            continue
        batch = paginate(
            "activities",
            {
                "user_id": user["id"],
                "type": ACTIVITY_CROSS_SELLING,
                "start_date": CYCLE_START,
                "end_date": end,
            },
        )
        for act in batch:
            act_id = act.get("id")
            if act_id in seen:
                continue
            seen.add(act_id)
            activities.append(act)
    return activities


def build_process_metrics(deals: list[dict], activities: list[dict]) -> dict:
    act_weekly: dict[str, int] = defaultdict(int)
    for act in activities:
        # due_date or add_time
        stamp = act.get("due_date") or (act.get("add_time") or "")[:10]
        if not in_cycle(stamp):
            continue
        act_weekly[week_label(stamp)] += 1

    deal_weekly: dict[str, dict[str, int]] = defaultdict(
        lambda: {"open": 0, "won": 0, "lost": 0}
    )
    status_totals = {"open": 0, "won": 0, "lost": 0}
    for deal in deals:
        if deal.get("pipeline_id") != PIPELINE_SONSTIGE:
            continue
        stamp = deal.get("add_time")
        if not in_cycle(stamp):
            continue
        status = deal.get("status") or "open"
        if status not in status_totals:
            continue
        status_totals[status] += 1
        deal_weekly[week_label(stamp)][status] += 1

    weeks = sorted(set(act_weekly) | set(deal_weekly))
    activities_total = sum(act_weekly.values())
    deals_created_total = sum(status_totals.values())
    won = status_totals["won"]
    lost = status_totals["lost"]
    closed = won + lost

    def pct(num: float, den: float) -> float | None:
        if den <= 0:
            return None
        return round(100.0 * num / den, 1)

    weekly_conversion = []
    for w in weeks:
        acts = act_weekly.get(w, 0)
        created = (
            deal_weekly[w]["open"] + deal_weekly[w]["won"] + deal_weekly[w]["lost"]
        )
        week_won = deal_weekly[w]["won"]
        weekly_conversion.append(
            {
                "week": w,
                "activities": acts,
                "deals_created": created,
                "won": week_won,
                "to_deal_pct": pct(created, acts),
                "to_won_pct": pct(week_won, acts),
            }
        )

    return {
        "activities_total": activities_total,
        "deals_created_total": deals_created_total,
        "deals_by_status": status_totals,
        "conversion": {
            "to_deal_pct": pct(deals_created_total, activities_total),
            "to_won_pct": pct(won, activities_total),
            "win_rate_pct": pct(won, closed),
            "definition": (
                "to_deal = Sonstige-Deals neu ÷ CS-Ansprachen; "
                "to_won = gewonnen ÷ CS-Ansprachen; "
                "win_rate = gewonnen ÷ (gewonnen+verloren). "
                "Kein 1:1-Matching — Kalenderwochen-Näherung."
            ),
        },
        "weekly_activities": [{"week": w, "count": act_weekly.get(w, 0)} for w in weeks],
        "weekly_deals": [
            {
                "week": w,
                "open": deal_weekly[w]["open"],
                "won": deal_weekly[w]["won"],
                "lost": deal_weekly[w]["lost"],
                "total": deal_weekly[w]["open"] + deal_weekly[w]["won"] + deal_weekly[w]["lost"],
            }
            for w in weeks
        ],
        "weekly_conversion": weekly_conversion,
    }


def render_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OKR Werbemarkt — DB vs. 40.000 €</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --ink: #1a2421; --muted: #5c6b66; --paper: #f3efe6; --panel: rgba(255,252,246,.88);
      --line: #d5cdc0; --accent: #0f6b5c; --warn: #9a5b12;
      --vermittlung: #1f4b7a; --sonstige: #0f6b5c; --online: #b45309;
      --open: #6b8fad; --lost: #b42318; --won: #147a69; --act: #5b4b8a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; color: var(--ink);
      font-family: "Source Sans 3", system-ui, sans-serif;
      background:
        radial-gradient(1200px 600px at 10% -10%, #d9ebe4 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #f0e2c8 0%, transparent 50%),
        linear-gradient(180deg, #efe9dc 0%, var(--paper) 40%, #e7eee9 100%);
    }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    header {{ display: grid; gap: .35rem; margin-bottom: 1.5rem; }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: .12em; font-size: .75rem; font-weight: 700; color: var(--accent); }}
    h1 {{ margin: 0; font-family: Fraunces, Georgia, serif; font-weight: 700; font-size: clamp(1.8rem, 4vw, 2.5rem); line-height: 1.15; }}
    .sub {{ margin: 0; color: var(--muted); max-width: 46rem; }}
    .hero {{ display: grid; grid-template-columns: 1.45fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 1.2rem 1.3rem; backdrop-filter: blur(8px); }}
    .goal-label {{ font-size: .9rem; color: var(--muted); margin-bottom: .35rem; }}
    .big-number {{ font-family: Fraunces, Georgia, serif; font-size: clamp(2.2rem, 5vw, 3.2rem); font-weight: 700; }}
    .big-number span {{ color: var(--muted); font-size: .45em; font-weight: 500; }}
    .progress-track {{ margin-top: 1rem; height: 14px; border-radius: 999px; background: #e5ddd0; overflow: hidden; }}
    .progress-fill {{ height: 100%; width: 0; background: linear-gradient(90deg, #147a69, #1f9b84); border-radius: 999px; transition: width .6s ease; }}
    .meta-row {{ display: flex; flex-wrap: wrap; gap: .75rem 1.25rem; margin-top: .9rem; font-size: .95rem; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem; }}
    .stat h2 {{ margin: 0 0 .4rem; font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
    .stat .value {{ font-family: Fraunces, Georgia, serif; font-size: 1.75rem; font-weight: 700; }}
    .stat .hint {{ margin-top: .35rem; color: var(--muted); font-size: .9rem; }}
    .dot {{ display: inline-block; width: .65rem; height: .65rem; border-radius: 50%; margin-right: .35rem; vertical-align: middle; }}
    .dot.a {{ background: var(--vermittlung); }} .dot.b {{ background: var(--sonstige); }} .dot.c {{ background: var(--online); }}
    .dot.open {{ background: var(--open); }} .dot.lost {{ background: var(--lost); }} .dot.won {{ background: var(--won); }} .dot.act {{ background: var(--act); }}
    .charts {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
    .charts-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
    h3 {{ margin: 0 0 .85rem; font-family: Fraunces, Georgia, serif; font-size: 1.15rem; }}
    .bars {{ display: grid; gap: .42rem; min-height: 180px; }}
    .bar-row {{ display: grid; grid-template-columns: 2.6rem 1fr 4.2rem; gap: .55rem; align-items: center; font-size: .82rem; }}
    .stack {{ display: flex; height: 16px; border-radius: 6px; overflow: hidden; background: #ebe4d8; }}
    .stack > i {{ display: block; height: 100%; }}
    .stack .a {{ background: var(--vermittlung); }} .stack .b {{ background: var(--sonstige); }} .stack .c {{ background: var(--online); }}
    .stack .open {{ background: var(--open); }} .stack .lost {{ background: var(--lost); }} .stack .won {{ background: var(--won); }}
    .stack .act {{ background: var(--act); }}
    .stack .conv {{ background: var(--won); }}
    table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
    th, td {{ text-align: left; padding: .45rem 0; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-weight: 600; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    footer {{ margin-top: .5rem; color: var(--muted); font-size: .85rem; line-height: 1.45; }}
    .warn {{ margin-top: .75rem; padding: .7rem .85rem; border-radius: 10px; background: #fff4e5; color: var(--warn); font-size: .9rem; }}
    @media (max-width: 900px) {{
      .hero, .charts, .charts-3, .stat-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">Mundschenk · Werbemarkt OKR · Zyklus ab {CYCLE_START}</div>
      <h1>Deckungsbeitrag ergänzende Produkte</h1>
      <p class="sub">Abgleich zum Ziel von 40.000 € DB seit Zyklusstart. Enthält Sonstige [adpipe] und Online-Rubriken in Anzeigen [adpipe], plus Cross-Selling-Prozesskennzahlen.</p>
    </header>

    <section class="hero">
      <div class="panel">
        <div class="goal-label">Ist DB seit Zyklusstart</div>
        <div class="big-number" id="totalDb">— <span>/ 40.000 €</span></div>
        <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
        <div class="meta-row">
          <div><strong id="progressPct">—</strong> erreicht</div>
          <div>noch <strong id="remaining">—</strong></div>
          <div><strong id="dealCount">—</strong> gewonnene Deals</div>
        </div>
        <div class="warn" id="onlineWarn" hidden></div>
      </div>
      <div class="panel">
        <div class="goal-label">Aktualisiert</div>
        <div class="big-number" style="font-size:1.55rem" id="generatedAt">—</div>
        <div class="meta-row" style="margin-top:1rem">
          <div><span class="dot act"></span>CS-Aktivitäten: <strong id="actTotal">—</strong></div>
          <div>Sonstige-Deals neu: <strong id="dealCreated">—</strong></div>
          <div><span class="dot won"></span>Conv. Gewinn: <strong id="convWon">—</strong></div>
          <div>Conv. Deal: <strong id="convDeal">—</strong></div>
          <div>Abschlussquote: <strong id="winRate">—</strong></div>
        </div>
        <p class="sub" style="margin-top:.85rem" id="sourceNote"></p>
      </div>
    </section>

    <section class="stat-grid">
      <article class="panel stat">
        <h2><span class="dot a"></span>Vermittlungen (×15%)</h2>
        <div class="value" id="segA">—</div>
        <div class="hint" id="segAHint"></div>
      </article>
      <article class="panel stat">
        <h2><span class="dot b"></span>Sonstige Rest / Klickbare</h2>
        <div class="value" id="segB">—</div>
        <div class="hint" id="segBHint"></div>
      </article>
      <article class="panel stat">
        <h2><span class="dot c"></span>Online über Rubriken</h2>
        <div class="value" id="segC">—</div>
        <div class="hint" id="segCHint"></div>
      </article>
    </section>

    <section class="charts">
      <div class="panel">
        <h3>DB je Kalenderwoche (gewonnen)</h3>
        <div class="bars" id="weeklyBars"></div>
      </div>
      <div class="panel">
        <h3>Online nach Rubrik</h3>
        <table>
          <thead><tr><th>Rubrik</th><th class="num">Deals</th><th class="num">DB €</th></tr></thead>
          <tbody id="onlineTable"></tbody>
        </table>
      </div>
    </section>

    <section class="charts-3">
      <div class="panel">
        <h3><span class="dot act"></span>Cross-Selling Aktivitäten / Woche</h3>
        <div class="bars" id="actBars"></div>
      </div>
      <div class="panel">
        <h3>Deals Sonstige [adpipe] / Woche</h3>
        <div class="bars" id="dealBars"></div>
        <div class="meta-row" style="margin-top:.8rem;font-size:.85rem">
          <span><span class="dot open"></span>Offen</span>
          <span><span class="dot lost"></span>Verloren</span>
          <span><span class="dot won"></span>Gewonnen</span>
        </div>
      </div>
      <div class="panel">
        <h3><span class="dot won"></span>Conversion Gewinn / Woche</h3>
        <div class="bars" id="convBars"></div>
        <p class="sub" style="margin-top:.75rem;font-size:.82rem" id="convNote"></p>
      </div>
    </section>

    <footer id="footerNote"></footer>
  </main>
  <script>
    const DATA = {data_json};
    const euro = (n) => new Intl.NumberFormat('de-DE', {{ style:'currency', currency:'EUR', maximumFractionDigits:0 }}).format(n||0);
    const euroExact = (n) => new Intl.NumberFormat('de-DE', {{ style:'currency', currency:'EUR', maximumFractionDigits:2 }}).format(n||0);
    const pctLabel = (n) => (n == null ? '—' : `${{n.toLocaleString('de-DE')}} %`);

    document.getElementById('totalDb').innerHTML = `${{euro(DATA.total_db)}} <span>/ ${{euro(DATA.goal)}}</span>`;
    document.getElementById('progressPct').textContent = `${{DATA.progress_pct}} %`;
    document.getElementById('remaining').textContent = euro(DATA.remaining);
    document.getElementById('dealCount').textContent = DATA.deal_count;
    document.getElementById('progressFill').style.width = Math.min(DATA.progress_pct, 100) + '%';
    document.getElementById('generatedAt').textContent = new Date(DATA.generated_at).toLocaleString('de-DE');
    document.getElementById('sourceNote').textContent = DATA.sources.note;
    document.getElementById('actTotal').textContent = DATA.process.activities_total;
    document.getElementById('dealCreated').textContent = DATA.process.deals_created_total;
    const conv = DATA.process.conversion || {{}};
    document.getElementById('convWon').textContent = pctLabel(conv.to_won_pct);
    document.getElementById('convDeal').textContent = pctLabel(conv.to_deal_pct);
    document.getElementById('winRate').textContent = pctLabel(conv.win_rate_pct);
    document.getElementById('convNote').textContent = conv.definition || '';

    const a = DATA.segments.vermittlungen, b = DATA.segments.sonstige_rest, c = DATA.segments.online_anzeigen;
    document.getElementById('segA').textContent = euroExact(a.db);
    document.getElementById('segB').textContent = euroExact(b.db);
    document.getElementById('segC').textContent = euroExact(c.db);
    document.getElementById('segAHint').textContent = `${{a.n}} Deals · OKR DB A`;
    document.getElementById('segBHint').textContent = `${{b.n}} Deals · CrossSelling Sonstige`;
    document.getElementById('segCHint').textContent = `${{c.n}} Deals · Anzeigen [adpipe]`;
    if (c.missing_db > 0) {{
      const el = document.getElementById('onlineWarn');
      el.hidden = false;
      el.textContent = `${{c.missing_db}} Online-Deals ohne DB berechnet — Deal value als DB (Satz 1) verwendet.`;
    }}

    function renderStack(rows, keys, maxKey, targetId) {{
      const max = Math.max(...rows.map(r => r[maxKey] || 0), 1);
      document.getElementById(targetId).innerHTML = rows.map(r => {{
        const parts = keys.map(([cls, key]) => `<i class="${{cls}}" style="width:${{(r[key]/max)*100}}%"></i>`).join('');
        return `<div class="bar-row"><div>${{r.week}}</div><div class="stack">${{parts}}</div><div style="text-align:right">${{r[maxKey]}}</div></div>`;
      }}).join('');
    }}

    const weeksDb = DATA.weekly_db.slice(-16);
    const maxDb = Math.max(...weeksDb.map(w => w.total), 1);
    document.getElementById('weeklyBars').innerHTML = weeksDb.map(w => {{
      return `<div class="bar-row"><div>${{w.week}}</div><div class="stack">
        <i class="a" style="width:${{(w.vermittlungen/maxDb)*100}}%"></i>
        <i class="b" style="width:${{(w.sonstige_rest/maxDb)*100}}%"></i>
        <i class="c" style="width:${{(w.online_anzeigen/maxDb)*100}}%"></i>
      </div><div style="text-align:right">${{euro(w.total)}}</div></div>`;
    }}).join('');

    const rows = Object.entries(DATA.online_by_rubrik);
    document.getElementById('onlineTable').innerHTML = rows.length
      ? rows.map(([name, row]) => `<tr><td>${{name}}</td><td class="num">${{row.n}}</td><td class="num">${{euroExact(row.db)}}</td></tr>`).join('')
      : `<tr><td colspan="3">Keine Online-Rubrik-Deals im Zyklus</td></tr>`;

    const actRows = DATA.process.weekly_activities.slice(-16).map(r => ({{...r, total: r.count}}));
    renderStack(actRows, [['act','count']], 'total', 'actBars');
    const dealRows = DATA.process.weekly_deals.slice(-16);
    const maxDeals = Math.max(...dealRows.map(r => r.total), 1);
    document.getElementById('dealBars').innerHTML = dealRows.map(r => `<div class="bar-row"><div>${{r.week}}</div><div class="stack">
      <i class="open" style="width:${{(r.open/maxDeals)*100}}%"></i>
      <i class="lost" style="width:${{(r.lost/maxDeals)*100}}%"></i>
      <i class="won" style="width:${{(r.won/maxDeals)*100}}%"></i>
    </div><div style="text-align:right">${{r.total}}</div></div>`).join('');

    const convRows = (DATA.process.weekly_conversion || []).slice(-16);
    const maxConv = Math.max(...convRows.map(r => r.to_won_pct || 0), 1);
    document.getElementById('convBars').innerHTML = convRows.map(r => {{
      const val = r.to_won_pct;
      const width = val == null ? 0 : (val / maxConv) * 100;
      const label = val == null ? '—' : pctLabel(val);
      return `<div class="bar-row"><div>${{r.week}}</div><div class="stack"><i class="conv" style="width:${{width}}%"></i></div><div style="text-align:right">${{label}}</div></div>`;
    }}).join('');

    document.getElementById('footerNote').textContent =
      `Zyklus ab ${{DATA.cycle_start}} · Filter ${{DATA.sources.filter_name}} (ID ${{DATA.sources.filter_id}}) · DB-Satz-Backfill Online: ${{DATA.backfill.updated}} aktualisiert.`;
  </script>
</body>
</html>
"""


def main() -> None:
    load_env()
    if not os.environ.get("PIPEDRIVE_API_TOKEN"):
        raise SystemExit("PIPEDRIVE_API_TOKEN fehlt (.env oder Umgebung).")

    goal = float(os.environ.get("OKR_GOAL", "40000"))
    filter_id = int(os.environ.get("OKR_FILTER_ID", "38534"))
    labels = fetch_rubrik_labels()
    deals = fetch_filter_deals(filter_id)

    # Also pull Sonstige pipeline deals for process chart (created in cycle)
    sonstige_deals = paginate(
        "deals",
        {"pipeline_id": PIPELINE_SONSTIGE, "status": "all_not_deleted"},
    )
    activities = fetch_cross_selling_activities()

    # Daily auto-run: skip slow backfill unless explicitly enabled
    do_backfill = os.environ.get("OKR_BACKFILL", "0").strip() in {"1", "true", "yes"}
    if do_backfill:
        backfill = backfill_online_db_satz(deals)
        if backfill["updated"]:
            time.sleep(1.0)
            deals = fetch_filter_deals(filter_id)
    else:
        backfill = {"updated": 0, "already_ok": 0, "errors": [], "error_count": 0, "skipped": True}

    db_metrics = build_db_metrics(deals, goal, labels)
    process = build_process_metrics(sonstige_deals, activities)

    metrics = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cycle_start": CYCLE_START,
        **db_metrics,
        "process": process,
        "backfill": backfill,
        "sources": {
            "filter_id": filter_id,
            "filter_name": "OKR DB Gesamt — vs. 40.000 (ab 13.07.2026)",
            "note": f"Nur Deals mit Gewinn-Datum ab {CYCLE_START}. Spezialisten ausgeschlossen. Prozess: Cross-Selling-Aktivitäten + Deals in Sonstige [adpipe].",
        },
    }

    DATA_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    HTML_PATH.write_text(render_html(metrics))
    print(
        f"OK · Zyklus ab {CYCLE_START} · {metrics['total_db']:.2f} € / {goal:.0f} € "
        f"({metrics['progress_pct']} %) · {metrics['deal_count']} Deals · "
        f"CS-Akt. {process['activities_total']} · DB-Satz updates {backfill['updated']} · {HTML_PATH}"
    )


if __name__ == "__main__":
    main()
