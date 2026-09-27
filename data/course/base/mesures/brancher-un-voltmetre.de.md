---
title: Ein Voltmeter anschließen
---

Die Spannung ist der Antrieb: ein **Unterschied** zwischen zwei Stellen, wie
der Höhenunterschied zwischen zwei Wasserbehältern. Um sie zu messen, baut
man das Messgerät also nicht in die Leitung ein: Man **vergleicht zwei
Stellen**.

## Eine Messleitung auf jeder Seite

Um die Spannung an einer Lampe zu messen, hält man eine Messleitung des
Voltmeters an jeden ihrer beiden Anschlüsse. Voltmeter und Lampe liegen dann
**nebeneinander**, mit denselben zwei Stellen verbunden: Das Voltmeter wird
**parallel** zu dem Bauteil geschaltet, das man messen will, wie zwei
Batterien parallel. (Die Prüfung nennt dieses Bauteil das **Messobjekt**.)
Den Stromkreis muss man dafür nicht öffnen.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Ein Stromkreis als Schleife mit einer Batterie links und einer Lampe rechts. Ein Voltmeter, ein Kreis mit dem Buchstaben V, liegt neben der Lampe: Eine Leitung geht oben von der Lampe ab, eine andere unten.">
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M40 75 V40 H220 V81"/><path d="M220 109 V150 H40 V120"/>
<path d="M220 60 H300 V79"/><path d="M300 111 V130 H220"/>
</g>
<g fill="#1c1f26"><circle cx="220" cy="60" r="3"/><circle cx="220" cy="130" r="3"/></g>
<rect x="25" y="75" width="30" height="45" rx="4" fill="#f3d9b1" stroke="#b07a2a" stroke-width="2"/>
<circle cx="220" cy="95" r="14" fill="#ffffff" stroke="#1c1f26" stroke-width="2"/>
<g stroke="#1c1f26" stroke-width="1.5"><path d="M210 85 L230 105"/><path d="M230 85 L210 105"/></g>
<circle cx="300" cy="95" r="16" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="300" y="101" font-size="16" font-weight="bold" text-anchor="middle" fill="#2f5fd6">V</text>
<g font-size="12" fill="#6b7280">
<text x="64" y="101">Batterie</text>
<text x="198" y="99" text-anchor="end">Lampe</text>
<text x="300" y="158" text-anchor="middle">Voltmeter</text>
</g>
</svg>
<figcaption>Das Voltmeter liegt neben der Lampe, mit ihren beiden Anschlüssen verbunden: Es vergleicht die zwei Stellen.</figcaption>
</figure>

## Es darf fast nichts durchlassen

Parallel geschaltet öffnet das Voltmeter einen **zweiten Weg** neben der
Lampe. Wäre dieser Weg leicht, würde auch das Voltmeter Strom ziehen: Es
würde Strom zu sich **umleiten** und verändern, was im Stromkreis passiert.
Sein Widerstand muss darum **so groß wie möglich** sein: Das Voltmeter soll
**möglichst hochohmig** sein („viele Ohm“).

Das ohmsche Gesetz bestätigt es. Ein Voltmeter mit 10 MΩ an 6 V lässt
I = U : R = 6 : 10 000 000 = **0,000 000 6 A** durch. Fast nichts!

## Die Falle: es in Reihe anschließen

Setzt du das Voltmeter **in die Schleife**, wie ein Amperemeter, sperrt sein
riesiger Widerstand fast den ganzen Strom: Die Lampe geht aus, und das Gerät
misst nicht mehr die Spannung an der Lampe.

> **Nicht verwechseln:**
>
> - Das **Amperemeter** liegt **im** Weg: **in Reihe**, **möglichst
>   niederohmig**, damit es nicht bremst.
> - Das **Voltmeter** liegt **daneben**: **parallel**, **möglichst
>   hochohmig**, damit es nichts umleitet.
