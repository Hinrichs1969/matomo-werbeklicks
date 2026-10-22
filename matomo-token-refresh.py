#!/usr/bin/env python3
"""
matomo-token-refresh.py
Holt ein frisches Matomo-Token per Login und aktualisiert:
  1. .env.local (lokale Umgebung)
  2. GitHub Secret MATOMO_TOKEN (fuer GitHub Actions)
Wird automatisch vom Catchup-Skript aufgerufen wenn das Token 401 liefert.
"""
from __future__ import annotations
import base64, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT      = Path(__file__).resolve().parent
ENV_LOCAL = ROOT / ".env.local"

def load_env() -> dict:
    env = {}
    if ENV_LOCAL.exists():
        for line in ENV_LOCAL.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def save_token(new_token: str) -> None:
    """Schreibt das neue Token in .env.local."""
    if not ENV_LOCAL.exists():
        print("FEHLER: .env.local nicht gefunden")
        return
    content = ENV_LOCAL.read_text()
    content = re.sub(r"^MATOMO_TOKEN=.*$", f"MATOMO_TOKEN={new_token}", content, flags=re.MULTILINE)
    ENV_LOCAL.write_text(content)
    print(f"  .env.local aktualisiert")

def update_github_secret(new_token: str, github_pat: str, repo: str) -> None:
    """Aktualisiert das GitHub Secret MATOMO_TOKEN via GitHub API."""
    try:
        from nacl import encoding, public as nacl_public
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "PyNaCl", "-q"], check=True)
        from nacl import encoding, public as nacl_public

    # Public Key holen
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers={"Authorization": f"token {github_pat}", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req) as r:
        key_info = json.loads(r.read())

    pub_key_bytes = base64.b64decode(key_info["key"])
    sealed_box    = nacl_public.SealedBox(nacl_public.PublicKey(pub_key_bytes))
    encrypted_b64 = base64.b64encode(sealed_box.encrypt(new_token.encode())).decode()

    payload = json.dumps({"encrypted_value": encrypted_b64, "key_id": key_info["key_id"]}).encode()
    req2 = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/secrets/MATOMO_TOKEN",
        data=payload, method="PUT",
        headers={
            "Authorization": f"token {github_pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req2) as r:
        print(f"  GitHub Secret aktualisiert (HTTP {r.status})")

def get_new_token(user: str, password: str) -> str | None:
    """Holt ein frisches Token ueber den Matomo-Login."""
    base = "https://matomo.mundschenk.de/index.php"

    # Schritt 1: Nonce holen
    with urllib.request.urlopen(f"{base}?module=Login&action=index") as r:
        html = r.read().decode()
    m = re.search(r'name="form_nonce"\s+value="([^"]+)"', html)
    if not m:
        print("  FEHLER: Kein Login-Nonce gefunden")
        return None
    nonce = m.group(1)

    # Schritt 2: Einloggen und Cookies merken
    import http.cookiejar
    jar     = http.cookiejar.CookieJar()
    opener  = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    data    = urllib.parse.urlencode({
        "form_login": user, "form_password": password,
        "form_nonce": nonce, "form_redirect": "", "module": "Login", "action": "index"
    }).encode()
    opener.open(base, data)

    # Schritt 3: Token-Seite aufrufen und Token extrahieren
    resp = opener.open(f"{base}?module=UsersManager&action=userSecurity")
    page = resp.read().decode()
    m2   = re.search(r'"token_auth"\s*:\s*"([a-f0-9]{32})"', page)
    if m2:
        return m2.group(1)

    # Fallback: Token aus API-Antwort
    resp2 = opener.open(f"{base}?module=API&method=UsersManager.getUser&userLogin={user}&format=json")
    try:
        d = json.loads(resp2.read())
        return d.get("token_auth")
    except Exception:
        return None

def main() -> None:
    env = load_env()
    user       = env.get("MATOMO_USER", "")
    password   = env.get("MATOMO_PASS", "")
    github_pat = env.get("GITHUB_PAT", "")
    repo       = "Hinrichs1969/matomo-werbeklicks"

    if not user or not password:
        print("FEHLER: MATOMO_USER oder MATOMO_PASS fehlt in .env.local")
        return

    print(f"Hole neues Matomo-Token fuer {user}...")
    new_token = get_new_token(user, password)

    if not new_token:
        print("FEHLER: Token konnte nicht ermittelt werden – bitte manuell erneuern")
        return

    print(f"  Neues Token: {new_token[:8]}…")
    save_token(new_token)
    update_github_secret(new_token, github_pat, repo)
    # Aktuelle Session übernehmen
    os.environ["MATOMO_TOKEN"] = new_token
    print("Token-Refresh abgeschlossen.")

if __name__ == "__main__":
    main()
