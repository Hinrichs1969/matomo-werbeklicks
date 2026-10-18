# Matomo-Tracking – onclick-Codes für klickbare Anzeigen & Interstitials

**Stand:** Oktober 2026  
**Betrifft:** Volksbank Lüneburger Heide eG, MediClin Klinikum Soltau,  
Kahnwald Optik-Hörgeräte, MSM Walsrode GmbH & Co. KG, Grube KG Forstgerätestelle

---

## Problem

Interstitials erzeugen in Matomo automatisch einen `banner_click`-Event (ausgelöst von Prenly).  
Dieser Event lässt sich aber **nicht dem einzelnen Werbetreibenden zuordnen**, weil die
Ziel-URL nicht in **Custom Dimension 14** (`destination_url`) hinterlegt wird.

Ohne diese Zuordnung: Banner-Klicks im Bericht = 0 (nicht messbar).  
Mit dieser Zuordnung: Klicks werden automatisch in den täglichen Klick-Berichten ausgewertet.

---

## Lösung: onclick-Code im Prenly-Interstitial eintragen

Im Prenly-Redaktionssystem beim Interstitial-Eintrag des jeweiligen Werbekunden
das **Link-Feld** (oder Onclick-Handler) um folgenden JavaScript-Code ergänzen:

### Volksbank Lüneburger Heide eG

Ziel-URL: `https://www.vblh.de/homepage.html`

**onclick-Code** (kompletter Wert für das onclick-Feld in Prenly):

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.vblh.de/homepage.html']);
```

Wenn das Interstitial einen direkten `<a href>`-Link hat:

```html
<a href="https://www.vblh.de/homepage.html"
   target="_blank"
   onclick="var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.vblh.de/homepage.html']);">
  <img src="volksbank_interstitial.jpg" alt="Volksbank Lüneburger Heide" />
</a>
```

---

### MediClin Klinikum Soltau

Ziel-URL: `http://www.klinikum-soltau.de`

**onclick-Code:**

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'http://www.klinikum-soltau.de']);
```

Als `<a href>`:

```html
<a href="http://www.klinikum-soltau.de"
   target="_blank"
   onclick="var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'http://www.klinikum-soltau.de']);">
  <img src="mediclin_interstitial.jpg" alt="MediClin Klinikum Soltau" />
</a>
```

---

## Vorlage für zukünftige Interstitials

Für jeden neuen Interstitial-Kunden gilt dasselbe Prinzip.  
Nur die Ziel-URL muss angepasst werden:

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'ZIEL-URL-HIER-EINTRAGEN']);
```

**Wichtig:**
- Die URL muss **exakt der tatsächlichen Ziel-URL** des Interstitials entsprechen
- Anführungszeichen innerhalb der URL müssen vermieden oder escaped werden
- Das Script setzt die URL als Besucher-Dimension – Prenly feuert den `banner_click`-Event selbst

---

## Was passiert danach?

Sobald der onclick-Code eingebaut ist:

1. Matomo speichert die Ziel-URL in Custom Dimension 14 für den Seitenaufruf
2. Der tägliche Klick-Bericht (läuft täglich um 10:05 Uhr via GitHub Actions) erfasst
   die Klicks automatisch und ordnet sie dem Werbekunden zu
3. Der individuelle Kundenbericht unter  
   `https://hinrichs1969.github.io/matomo-werbeklicks/berichte/volksbank.html`  
   bzw. `.../berichte/mediclin.html` wird täglich aktualisiert

---

## Rückwirkend (bereits gelaufene Kampagnen)

| Kampagne | Erscheinungsdaten | Reichweite (E-Paper-Öffnungen) | Klicks |
|---|---|---|---|
| Volksbank – Interstitial BZ 1/3 | 24.08.2026 | ~2.625 | **nicht messbar** |
| Volksbank – Interstitial BZ 2/3 | 31.08.2026 | ~2.721 | **nicht messbar** |
| Volksbank – Interstitial BZ 3/3 | 07.09.2026 | ~2.616 | **nicht messbar** |
| MediClin – Interstitial BZ | 04.09.2026 | ~2.518 | **nicht messbar** |

Die Reichweite (E-Paper-Öffnungen) wurde aus dem `publication_open`-Event in Matomo ermittelt
und entspricht der Anzahl der Sitzungen, in denen das E-Paper geöffnet wurde.  
Klickzahlen für vergangene Schaltungen können nachträglich **nicht mehr** ermittelt werden.

---

## Klickbare Anzeigen – fehlende onclick-Codes (Stand Oktober 2026)

Bei klickbaren Anzeigen (nicht Interstitials) trägt die Grafik in Prenly beim
Anlegen des klickbaren Bereichs das **onclick-Feld** aus. Ohne diesen Code werden
weder Klicks noch Einblendungen in Matomo erfasst.

### Kahnwald Optik-Hörgeräte

**Anzeige:** Senioren heute (HK, erschienen 11.10.2026)  
**Ziel-URL:** `https://www.optikkahnwald.de` *(bitte genaue URL mit Grafik klären)*

**onclick-Code für Prenly:**
```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.optikkahnwald.de']);
```

Als `<a href>` (falls Prenly-Link-Feld genutzt wird):
```html
<a href="https://www.optikkahnwald.de"
   target="_blank"
   onclick="var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.optikkahnwald.de']);">
</a>
```

> **Hinweis:** Im Tracking-System ist die Domain `optikkahnwald.de` hinterlegt.  
> Die genaue Ziel-URL (mit oder ohne `www.`, mit oder ohne Unterseite) muss mit der
> tatsächlichen Zielseite der Anzeige übereinstimmen.

---

### MSM Walsrode GmbH & Co. KG

**Anzeige:** BZ Ausbildung 2026 (BZ, erschienen 12.09.2026)  
**Ziel-URL:** `https://www.msm-walsrode.com` *(bitte genaue URL mit Grafik klären)*

**onclick-Code für Prenly:**
```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.msm-walsrode.com']);
```

Als `<a href>`:
```html
<a href="https://www.msm-walsrode.com"
   target="_blank"
   onclick="var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.msm-walsrode.com']);">
</a>
```

> **Hinweis:** Die Anzeige läuft bereits seit 12.09. (über 30 Tage). Sobald der Code
> eingetragen ist, werden ab dem nächsten Erscheinungstag Klicks erfasst.
> Vergangene Klicks sind nicht mehr rekonstruierbar.

---

### Grube KG Forstgerätestelle

**Anzeige:** CrossSell Print+Online (BZ+HK, erschienen 20.09.2026)  
**Ziel-URL:** `https://www.grube.de/karriere/ausbildung/`

**onclick-Code für Prenly:**
```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.grube.de/karriere/ausbildung/']);
```

Als `<a href>`:
```html
<a href="https://www.grube.de/karriere/ausbildung/"
   target="_blank"
   onclick="var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.grube.de/karriere/ausbildung/']);">
</a>
```

> **Wichtig – exakte URL:** Grube wird im System mit **striktem Exakt-Abgleich** (`==`)
> gemessen, nicht nur Domain-Matching. Der onclick-Code muss die URL **exakt so** enthalten:
> `https://www.grube.de/karriere/ausbildung/` – mit `www.`, mit `https://` und mit
> abschließendem `/`. Jede Abweichung führt zu 0 gemessenen Klicks.
