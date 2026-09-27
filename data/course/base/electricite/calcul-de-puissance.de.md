---
title: 'Eine Leistung berechnen: P = U · I'
---

Du weißt, dass die Leistung die Geschwindigkeit ist, mit der die
Elektrizität arbeitet. Aber wie rechnet man sie aus?

Überleg mal: Ein Gerät arbeitet schneller, wenn man es **stärker antreibt**
(mehr Spannung) und wenn **mehr Strom** hindurchfließt. Die Leistung hängt
also von beiden ab, und die Regel ist ganz einfach:

> **P = U · I**
>
> die Leistung (in Watt) = die Spannung (in Volt) · die Stromstärke (in Ampere)

## Ein Beispiel aus dem Amateurfunk

Ein Funkgerät, das sendet und empfängt, heißt **Transceiver**. Ein
Transceiver im Auto läuft mit **13,8 V**: Das ist die Spannung einer
Autobatterie, die gerade geladen wird. Funkamateure benutzen diese Spannung
oft für ihre Geräte, auch zu Hause. Der Strom aus der Batterie fließt immer
in dieselbe Richtung: ein **Gleichstrom**. Darum nennt die Prüfung diese
Leistung die **Gleichstromleistung**.

**Frage:** Das Gerät nimmt einen Strom von **4 A** auf. Welche Leistung
verbraucht es?

P = U · I = 13,8 · 4 = **55,2 W**.

## Vorsicht, Falle: Milliampere

Dasselbe Gerät, 13,8 V, aber es nimmt nur noch **250 mA** auf. Welche
Leistung?

**Erster Schritt: umrechnen.** Die Formel will **Ampere**, keine
Milliampere. 250 mA = 250 : 1000 = **0,25 A**.

**Zweiter Schritt: rechnen.** P = 13,8 · 0,25 = **3,45 W**.

Schau dir die zwei Arten an, sich zu vertun:

- **Das Umrechnen vergessen:** 13,8 · 250 = 3450 W. Das ist die Leistung
  eines großen Heizkörpers, nicht die eines kleinen Funkgeräts! Der gesunde
  Menschenverstand sagt, dass das falsch ist.
- **Das „Milli“ am Ende stehen lassen:** „3,45 mW“. Nein: Wenn du in Ampere
  umgerechnet hast, kommt das Ergebnis in **Watt** heraus, ohne Vorsilbe.

<figure>
<svg viewBox="0 0 360 80" width="360" role="img" aria-label="Methode in drei Schritten: in Einheiten ohne Vorsilbe umrechnen, malnehmen, mit gesundem Menschenverstand prüfen">
<g font-size="14" text-anchor="middle">
<rect x="5" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="55" y="37" fill="#1c1f26">1. umrechnen</text><text x="55" y="55" fill="#6b7280" font-size="12">mA → A</text>
<rect x="130" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="180" y="37" fill="#1c1f26">2. rechnen</text><text x="180" y="55" fill="#6b7280" font-size="12">P = U · I</text>
<rect x="255" y="15" width="100" height="50" rx="8" fill="#e6f4ea" stroke="#16803c" stroke-width="2"/>
<text x="305" y="37" fill="#1c1f26">3. prüfen</text><text x="305" y="55" fill="#6b7280" font-size="12">logisch?</text>
</g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M107 40 H126"/><path d="M120 35 L126 40 L120 45"/><path d="M232 40 H251"/><path d="M245 35 L251 40 L245 45"/></g>
</svg>
<figcaption>Die Methode für alle Rechnungen: umrechnen, rechnen, prüfen.</figcaption>
</figure>

> **In der Prüfung:** Die falschen Antworten sind genau die, die man bekommt,
> wenn man sich bei der Vorsilbe vertut. Schwankst du zwischen mW, W und kW,
> rechne in Ruhe noch einmal um und prüf dann, ob das Ergebnis für ein
> Funkgerät logisch ist.
