---
title: Der Balun
---

Ein Halbwellen-Dipol wird meistens in seiner **Mitte** angeschlossen, mit
einem Koaxialkabel. Aber dazwischen sitzt fast immer ein kleines Kästchen:
der **Balun**. Wozu dient er?

## Symmetrisch oder nicht?

Schau dir die beiden Arme des Dipols an: Sie sind **gleich**, und jeder
bekommt einen der beiden Leiter des Kabels. Sie spielen genau dieselbe
Rolle. Man sagt, der Dipol ist **symmetrisch** (auf Englisch *balanced*).

Das Koaxialkabel dagegen ist **unsymmetrisch** (*unbalanced*): Der
Innenleiter liegt innen, der Außenleiter außen, die beiden Leiter spielen
nicht dieselbe Rolle.

Schließt man das Koaxialkabel direkt an, fließt ein Teil des Stroms auf der
**Außenseite** des Geflechts ab: Das Kabel strahlt dann selbst, als wäre es
ein Teil der Antenne. Später wirst du sehen, dass das die Nachbarn stören
kann.

## Der Balun verbindet beide

Der **Balun** verbindet eine symmetrische mit einer unsymmetrischen Leitung.
Sein Name sagt es: **BAL**anced-**UN**balanced.

<figure>
<svg viewBox="0 0 340 150" width="340" role="img" aria-label="Das unsymmetrische Koaxialkabel kommt von unten in ein Kästchen, den Balun. Vom Balun gehen zwei Drähte zu den beiden gleichen Armen des Dipols, der symmetrisch ist.">
<g stroke="#d9822b" stroke-width="4"><path d="M20 30 H163"/><path d="M177 30 H320"/></g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M163 30 V70"/><path d="M177 30 V70"/></g>
<rect x="140" y="70" width="60" height="34" rx="6" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="170" y="92" font-size="13" text-anchor="middle" fill="#1c1f26">Balun</text>
<rect x="164" y="104" width="12" height="40" fill="#9aa3b5" stroke="#1c1f26" stroke-width="1.5"/>
<g font-size="12" fill="#6b7280"><text x="20" y="52">Dipol: symmetrisch</text><text x="186" y="135"><tspan x="186" y="124">Koaxialkabel:</tspan><tspan x="186" y="139">unsymmetrisch</tspan></text></g>
</svg>
<figcaption>Der Balun verbindet das unsymmetrische Koaxialkabel mit dem symmetrischen Dipol.</figcaption>
</figure>

## 1:1 oder 1:4?

Ein Balun kann auch die Impedanz ändern. Das gibt man mit zwei Zahlen an:

- ein **1:1-Balun** („eins zu eins“) lässt die Impedanz gleich: 50 Ω auf der
  einen Seite, 50 Ω auf der anderen;
- ein **1:4-Balun** **vervierfacht** sie: 50 Ω auf der Kabelseite werden
  200 Ω auf der Antennenseite. Er dient für Antennen, deren Impedanz etwa
  200 Ω beträgt.

Man wählt den, der die Impedanzen **nahe beieinander** bringt. In der Mitte
eines Halbwellen-Dipols liegt die Impedanz (50 bis 75 Ω) schon nahe an der
des Kabels (50 Ω): Man muss sie nicht ändern.

> **Merke:** Ein Balun macht den Anschluss **symmetrisch**; sein Verhältnis
> (1:1, 1:4) sagt, ob er auch die Impedanz ändert. Zum Auswählen schau dir
> die Impedanz der Antenne **an der Stelle an, wo du das Kabel anschließt**.
