# Matomo-Tracking – onclick-Code für klickbare Anzeigen

**Stand:** Oktober 2026  
**Für:** Grafik / Prenly-Einrichtung klickbarer Anzeigen im E-Paper

---

## Wie der Code eingetragen wird

Beim Anlegen des klickbaren Bereichs in Prenly gibt es ein **onclick-Feld**.  
Dort gehört ausschließlich dieser JavaScript-Einzeiler – **kein HTML, kein `<a href>`**:

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'ZIEL-URL-HIER-EINTRAGEN']);
```

Nur die URL muss je Kunde angepasst werden. Der Rest bleibt immer gleich.

---

## Kunden mit fehlendem onclick-Code (Stand Oktober 2026)

### Kahnwald Optik-Hörgeräte

**Anzeige:** Senioren heute (HK, erschienen 11.10.2026)

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.optikkahnwald.de']);
```

> Bitte genaue Ziel-URL der Anzeige mit Verkauf klären – mit oder ohne Unterseite.

---

### MSM Walsrode GmbH & Co. KG

**Anzeige:** BZ Ausbildung 2026 (BZ, erschienen 12.09.2026)

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.msm-walsrode.com']);
```

> Die Anzeige läuft bereits seit 12.09. – ab dem nächsten Erscheinungstag werden Klicks erfasst.  
> Vergangene Klicks sind nicht mehr rekonstruierbar.

---

### Grube KG Forstgerätestelle

**Anzeige:** CrossSell Print+Online (BZ+HK, erschienen 20.09.2026)

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'https://www.grube.de/karriere/ausbildung/']);
```

> **Wichtig:** URL muss **exakt** so eingetragen werden – mit `https://`, mit `www.` und mit
> dem abschließenden `/`. Jede Abweichung führt zu 0 gemessenen Klicks, da Grube per
> Exakt-Abgleich gemessen wird.

---

## Vorlage für jeden neuen klickbaren Kunden

```javascript
var _paq=window._paq||[];_paq.push(['setCustomDimension',14,'ZIEL-URL-HIER-EINTRAGEN']);
```

**Regeln:**
- URL = die tatsächliche Ziel-URL, auf die die Anzeige verlinkt
- Keine Anführungszeichen innerhalb der URL
- Bei jedem neuen Erscheinungsdatum / jeder neuen Ausgabe erneut eintragen
