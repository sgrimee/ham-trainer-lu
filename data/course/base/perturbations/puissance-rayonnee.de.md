---
title: Die effektive Strahlungsleistung (ERP)
---

Du weißt, dass eine Richtantenne ihre Leistung in ihre
Hauptstrahlrichtung bündelt. Für jemanden, der sich in dieser Richtung
befindet, kommt dein Signal also **stärker** an als mit einem einfachen
Dipol. Wie sagt man mit einer einzigen Zahl, „wie viel stärker“?

## Als ob …

Nehmen wir einen Sender mit **10 W**, angeschlossen an eine Yagi-Antenne
mit einem Gewinn von **10 dBd**. Du weißt: 10 dB heißt zehnmal so viel
Leistung nach vorn wie mit einem Dipol. In der Hauptstrahlrichtung ist es
also so, **als ob** ein Dipol 10 · 10 = **100 W** bekäme.

Diese 100 W heißen die **effektive Strahlungsleistung**, auf Englisch
*effective radiated power*, abgekürzt **ERP**. „Effektiv“, weil es um die
**Wirkung** geht: Die Antenne erzeugt keine Leistung, der Sender liefert
immer noch nur 10 W. Aber in der Hauptstrahlrichtung ist die Wirkung
dieselbe wie mit 100 W in einem Dipol.

<figure>
<svg viewBox="0 0 360 80" width="360" role="img" aria-label="Die Berechnung der ERP in drei Kästchen: Die Leistung, die an der Antenne ankommt, 10 Watt, malgenommen mit dem Gewinn als Faktor, 10, ergibt die ERP, 100 Watt.">
<g font-size="13" text-anchor="middle">
<rect x="5" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="55" y="37" fill="#1c1f26">Leistung</text><text x="55" y="55" fill="#6b7280" font-size="12">10 W</text>
<rect x="130" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="180" y="37" fill="#1c1f26">· Gewinn</text><text x="180" y="55" fill="#6b7280" font-size="12">10 dBd → 10-mal</text>
<rect x="255" y="15" width="100" height="50" rx="8" fill="#e6f4ea" stroke="#16803c" stroke-width="2"/>
<text x="305" y="37" fill="#1c1f26">= ERP</text><text x="305" y="55" fill="#6b7280" font-size="12">100 W</text>
</g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M107 40 H126"/><path d="M120 35 L126 40 L120 45"/><path d="M232 40 H251"/><path d="M245 35 L251 40 L245 45"/></g>
</svg>
<figcaption>Die ERP ist die Leistung, die an der Antenne ankommt, malgenommen mit dem Gewinn der Antenne.</figcaption>
</figure>

## Vergiss das Kabel nicht

Es zählt die Leistung, die **an der Antenne ankommt**. Ein Sender mit
50 W, ein Kabel, das 3 dB verliert: Es kommen nur 25 W an. Die Antenne hat
einen Gewinn von 6 dBd, also etwa 4-mal so viel. ERP = 25 · 4 = **100 W**. Das ist
logisch: Das Kabel hat die Leistung halbiert, dann hat die Antenne sie
vervierfacht, aber nur in ihrer Hauptstrahlrichtung.

Mit einem Gewinn in dBi (bezogen auf den isotropen Strahler) bekommt man
die **EIRP** (*equivalent isotropically radiated power*, äquivalente
isotrope Strahlungsleistung): 2,15 dB mehr als die ERP, weil der isotrope
Strahler schwächer ist als der Dipol.

> **Merke:** Die ERP beschreibt die **Wirkung** deiner Station in der
> Hauptstrahlrichtung: als ob ein Dipol diese Leistung bekäme. Sie hängt
> von **zwei** Dingen ab: von der Leistung, die an der Antenne ankommt, und
> vom Gewinn der Antenne. Du wirst sie brauchen, um Störungen zu bekämpfen.
