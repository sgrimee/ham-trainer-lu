---
title: Ein Amperemeter anschließen
---

Du weißt, dass ein Amperemeter die Stromstärke misst. Aber wo muss es im
Stromkreis hin? Und wie muss es innen gebaut sein?

## Der Strom muss hindurchfließen

Nehmen wir wieder das Wasser. Um zu wissen, wie viel Wasser durch ein Rohr
fließt, baut man eine **Wasseruhr** ein: Man schneidet das Rohr auf und
setzt die Uhr dazwischen, damit **das ganze Wasser hindurchfließt**.

Beim Amperemeter ist es genauso. Man öffnet den Stromkreis und setzt es in
die Schleife ein: Der Strom fließt durch die Batterie, dann durch das
Amperemeter, dann durch die Lampe. Sie liegen **hintereinander**: Das
Amperemeter wird **in Reihe** geschaltet, wie Batterien in Reihe.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Ein Stromkreis als Schleife: links eine Batterie, rechts eine Lampe, und ein Amperemeter, ein Kreis mit dem Buchstaben A, in der oberen Leitung zwischen beiden">
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M40 75 V40 H154"/><path d="M186 40 H300 V81"/><path d="M300 109 V150 H40 V120"/>
</g>
<rect x="25" y="75" width="30" height="45" rx="4" fill="#f3d9b1" stroke="#b07a2a" stroke-width="2"/>
<circle cx="170" cy="40" r="16" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="170" y="46" font-size="16" font-weight="bold" text-anchor="middle" fill="#2f5fd6">A</text>
<circle cx="300" cy="95" r="14" fill="#ffffff" stroke="#1c1f26" stroke-width="2"/>
<g stroke="#1c1f26" stroke-width="1.5"><path d="M290 85 L310 105"/><path d="M310 85 L290 105"/></g>
<g font-size="12" fill="#6b7280">
<text x="170" y="18" text-anchor="middle">Amperemeter</text>
<text x="64" y="101">Batterie</text>
<text x="278" y="99" text-anchor="end">Lampe</text>
</g>
</svg>
<figcaption>Das Amperemeter liegt in der Schleife: Der ganze Strom der Lampe fließt auch durch das Amperemeter.</figcaption>
</figure>

## Es darf fast nicht bremsen

Auch ein Amperemeter hat einen Widerstand. Würde es stark bremsen, flösse
weniger Strom als vorher: Es würde verfälschen, was es misst! Sein
Widerstand muss darum **so klein wie möglich** sein. Man sagt: Das
Amperemeter soll **möglichst niederohmig** sein („wenige Ohm“).

Prüfen wir das mit dem ohmschen Gesetz. Ein Amperemeter mit 0,1 Ω, durch das
0,5 A fließen, „nimmt“ sich eine Spannung von U = R · I = 0,1 · 0,5 =
**0,05 V**. An einer 6-V-Batterie ist das fast nichts: Die Lampe merkt davon
nichts.

## Die Falle: es parallel anschließen

Schließt du das Amperemeter **neben** der Batterie an, seine beiden
Messleitungen direkt an ihren Polen, wird sein winziger Widerstand zu einem
fast freien Weg. Nach dem ohmschen Gesetz würde der Strom auf
I = U : R = 6 : 0,1 = **60 A** steigen! Das ist ein **Kurzschluss**: Die
Sicherung des Messgeräts brennt durch, und genau dafür ist sie da.

> **Merke:** Das Amperemeter wird **in Reihe** geschaltet, und es soll
> **möglichst niederohmig** sein.

In der Prüfung heißt „in Reihe“ auch **seriell**: Das ist dasselbe. Und dort
steht manchmal „Ampèremeter“, mit einem französischen Akzent: Das ist
dasselbe Gerät.
