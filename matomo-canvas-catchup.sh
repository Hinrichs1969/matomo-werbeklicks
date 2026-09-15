#!/bin/bash
# matomo-canvas-catchup.sh
# Wird beim Login ausgef�hrt. Pr�ft ob das t�gliche Update heute schon lief �
# wenn nicht (z.B. weil der Mac um 8 Uhr aus war), wird es nachgeholt.

TODAY=$(date +%Y-%m-%d)
LOG="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.log"
SCRIPT="/Users/khinrichs/KI-Projekt/OKR 7:26/matomo-canvas-update.py"

# Pr�fe ob im Log ein Eintrag von heute existiert
if grep -q "\[$TODAY" "$LOG" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Update heute bereits gelaufen � kein Nachholen noetig." >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mac war um 08:00 aus � hole Update nach." >> "$LOG"
  /usr/bin/python3 "$SCRIPT"
fi
