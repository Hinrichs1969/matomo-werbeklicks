#!/bin/bash
# matomo-canvas-catchup.sh
# Wird beim Login ausgefuehrt. Prueft ob das taegliche Update heute
# ERFOLGREICH abgeschlossen wurde – wenn nicht, wird es nachgeholt.

TODAY=$(date +%Y-%m-%d)
LOG="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.log"
SCRIPT="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.py"
PIPEDRIVE_API_TOKEN_FILE="/Users/khinrichs/KI-Projekt/OKR 7:26/.env.local"

# Lade Tokens aus lokalem .env.local falls vorhanden
if [ -f "$PIPEDRIVE_API_TOKEN_FILE" ]; then
  export $(grep -v '^#' "$PIPEDRIVE_API_TOKEN_FILE" | xargs)
fi

# Pruefe ob heute ein ERFOLGREICHER Lauf verzeichnet ist
# (nicht bloss irgendein Eintrag – auch Fehler schreiben Eintraege)
if grep -q "\[$TODAY.*=== Update erfolgreich abgeschlossen ===" "$LOG" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update heute bereits erfolgreich gelaufen – kein Nachholen noetig." >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Kein erfolgreicher Lauf heute gefunden – hole Update nach." >> "$LOG"
  /usr/bin/python3 "$SCRIPT" 2>&1 | tee -a "$LOG"
fi
