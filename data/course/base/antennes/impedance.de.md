---
title: Die Impedanz einer Antenne
---

Du kennst das ohmsche Gesetz: R = U : I. Aber durch eine Antenne fließt ein
**Wechselstrom**. Was wird dann aus dieser Idee?

## Ein „Widerstand“ für den Wechselstrom

Beim Wechselstrom spricht man von **Impedanz**: dieselbe Idee wie der
Widerstand, Spannung geteilt durch Stromstärke, in **Ohm** (Ω). Große
Impedanz: viel Spannung für wenig Strom. Ihr Formelzeichen ist **Z**.

## In der Mitte oder am Ende des Dipols

In einem Halbwellen-Dipol ist der Strom nicht überall gleich.

- **Am Ende eines Arms** können die Elektronen nicht weiter: Der Strom ist
  dort **null**. Dafür stauen sich die Elektronen dort und laufen dann
  zurück: Die Spannung ist dort **sehr hoch**.
- **In der Mitte** ist es umgekehrt: Der Strom ist am **stärksten**, die
  Spannung **niedrig**.

<figure>
<svg viewBox="0 0 340 220" width="340" role="img" aria-label="Zwei Diagramme entlang eines Halbwellen-Dipols, waagerecht die Stelle entlang des Dipols. Oben der Strom: null an beiden Enden, am stärksten in der Mitte. Unten die Spannung: sehr hoch an beiden Enden, niedrig in der Mitte.">
<g font-size="13" font-weight="bold" fill="#1c1f26"><text x="330" y="14" text-anchor="end">Der Strom</text><text x="330" y="128" text-anchor="end">Die Spannung</text></g>
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M30 95 V14"/><path d="M26 20 L30 14 L34 20"/><path d="M30 95 H328"/><path d="M322 91 L328 95 L322 99"/><path d="M30 205 V124"/><path d="M26 130 L30 124 L34 130"/><path d="M30 205 H328"/><path d="M322 201 L328 205 L322 209"/></g>
<g font-size="11" fill="#6b7280"><text x="37" y="20">Strom</text><text x="37" y="130">Spannung</text><text x="328" y="109" text-anchor="end">entlang des Dipols</text><text x="328" y="197" text-anchor="end">entlang des Dipols</text></g>
<path d="M40 95 Q170 -5 300 95" fill="none" stroke="#2f5fd6" stroke-width="2"/>
<path d="M40 152 C90 152 150 178 170 198 C190 178 250 152 300 152" fill="none" stroke="#c0362c" stroke-width="2"/>
<g font-size="12" text-anchor="middle"><text x="170" y="75" fill="#2f5fd6">stark in der Mitte</text><text x="62" y="146" fill="#c0362c">hoch</text><text x="280" y="146" fill="#c0362c">hoch</text><text x="182" y="200" fill="#c0362c" text-anchor="start">niedrig</text></g>
</svg>
<figcaption>Der Strom ist in der Mitte stark und an den Enden null; bei der Spannung ist es umgekehrt.</figcaption>
</figure>

Teile die Spannung durch den Strom:

- in der **Mitte** wenig Spannung, viel Strom: Die Impedanz ist
  **niedrig**, etwa **50 bis 75 Ω**;
- am **Ende** viel Spannung, fast kein Strom: Die Impedanz ist **sehr
  hoch**, **mehrere Tausend Ohm**.

Das ist die **Impedanz am Speisepunkt** (auch Fußpunktimpedanz): Sie hängt
davon ab, wo man das Kabel anschließt.

## Die Impedanz des Kabels

Auch ein Koaxialkabel hat eine Impedanz. Sie kommt nicht vom Widerstand des
Kupfers: Sie hängt von der Dicke des Innenleiters, des Geflechts und des
Isolators ab, nicht von der Länge. Die Kabel der Funkamateure haben fast
alle **50 Ω** (die fürs Fernsehen 75 Ω).

> **Merke:** Damit die Leistung gut vom Kabel in die Antenne gelangt,
> müssen ihre Impedanzen **nahe beieinander** liegen. Darum geht es in den
> nächsten beiden Lektionen: Wie schließt man ein 50-Ω-Kabel in der Mitte
> oder am Ende eines Dipols an?
