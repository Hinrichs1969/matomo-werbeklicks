#!/bin/bash
# matomo-canvas-catchup.sh
# Wird beim Login ausgefuehrt. Prueft ob das taegliche Update heute
# ERFOLGREICH abgeschlossen wurde – wenn nicht, wird es nachgeholt.
# Bei ungueltigem Token: holt automatisch ein frisches Token.

TODAY=$(date +%Y-%m-%d)
LOG="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.log"
SCRIPT="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.py"
ENV_LOCAL="/Users/khinrichs/KI-Projekt/OKR 7:26/.env.local"
REFRESH_SCRIPT="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-token-refresh.py"

# Lade Tokens aus .env.local
if [ -f "$ENV_LOCAL" ]; then
  export $(grep -v '^#' "$ENV_LOCAL" | xargs)
fi

# Pruefe ob Token noch gueltig ist
TOKEN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://matomo.mundschenk.de/index.php?module=API&method=Events.getName&idSite=14&period=day&date=$TODAY&token_auth=$MATOMO_TOKEN&format=json")

if [ "$TOKEN_STATUS" = "401" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Token ungueltig (401) – hole neues Token..." >> "$LOG"
  /usr/bin/python3 "$REFRESH_SCRIPT" >> "$LOG" 2>&1
  # .env.local neu laden
  export $(grep -v '^#' "$ENV_LOCAL" | xargs)
fi

# Pruefe ob heute ein ERFOLGREICHER Lauf verzeichnet ist
if grep -q "\[$TODAY.*=== Update erfolgreich abgeschlossen ===" "$LOG" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update heute bereits erfolgreich gelaufen – kein Nachholen noetig." >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Kein erfolgreicher Lauf heute – hole Update nach." >> "$LOG"
  # Zuerst Neukunden erkennen
  /usr/bin/python3 "/Users/khinrichs/KI-Projekt/OKR 7:26/entdecke_neukunden.py" >> "$LOG" 2>&1
  # Dann Report aktualisieren
  /usr/bin/python3 "$SCRIPT" 2>&1 | tee -a "$LOG"
fi
