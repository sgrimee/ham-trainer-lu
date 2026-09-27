---
title: Der Parallelschwingkreis
---

Manchmal speist man den Dipol (man sagt auch: man **erregt** ihn) lieber
an **einem Ende**, zum Beispiel wenn dieses Ende gerade am Fenster
ankommt. Dort ist die Impedanz aber **sehr
hoch**: mehrere Tausend Ohm. Ein 50-Ω-Kabel schafft das nicht, und ein
1:4-Balun kommt nur auf 200 Ω: viel zu wenig.

## Die Schaukel

Denk an eine Schaukel. Wenn du sie **im richtigen Takt** anschubst, reicht
ein kleiner Stoß bei jedem Hin und Her, und sie schwingt sehr hoch. Sie ist
in **Resonanz**: Du schubst sie mit **ihrer** Frequenz an. Es ist dasselbe
Wort wie beim **resonanten** Dipol, der die richtige Länge für seine
Frequenz hat.

Ein **Schwingkreis** macht dasselbe mit Elektrizität. Er besteht aus zwei
Bauteilen, die wir hier nicht genauer anschauen: einer **Spule** (ein
aufgewickelter Draht) und einem **Kondensator** (zwei Metallplatten, ganz
nah beieinander, durch einen Isolator getrennt). **Nebeneinander**, also
parallel geschaltet, bilden sie einen **Parallelschwingkreis**: Sie
schieben sich die Energie hin und her, wie die Schaukel, die vor und
zurück schwingt. Verstellt man eines der beiden
Bauteile, **stimmt** man dieses Hin und Her auf die gewünschte Frequenz
**ab**.

## Eine sehr hohe Impedanz

Bei seiner Resonanzfrequenz schwingt ein Parallelschwingkreis fast von
allein: Ein winziger Strom hält eine große Spannung aufrecht. Hohe Spannung,
schwacher Strom: Seine Impedanz ist **sehr hoch**, wie am Ende eines
Halbwellen-Dipols!

<figure>
<svg viewBox="0 0 340 172" width="340" role="img" aria-label="Ein Halbwellen-Dipol, an einem Ende gespeist: Der Draht geht nach rechts, vom oberen Ende eines Parallelschwingkreises aus, einer Spule und einem Kondensator nebeneinander. Das Koaxialkabel ist an ein paar Windungen unten an der Spule angeschlossen.">
<path d="M130 30 H330" stroke="#d9822b" stroke-width="4"/>
<text x="230" y="20" font-size="12" fill="#6b7280" text-anchor="middle">Halbwellen-Dipol (λ/2)</text>
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M130 30 H60 V50 M130 30 V70 M60 120 V140 H130 V90"/>
<path d="M60 50 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14"/>
<path d="M115 70 H145 M115 90 H145"/>
<path d="M60 106 H20 V150 M60 140 H40 V150"/>
</g>
<g font-size="12" fill="#1c1f26"><text x="76" y="86">Spule</text><text x="152" y="84">Kondensator</text></g>
<text x="10" y="164" font-size="11" fill="#6b7280">zum Koaxialkabel</text>
</svg>
<figcaption>Der Parallelschwingkreis, auf die Frequenz abgestimmt, hat eine sehr hohe Impedanz, wie das Ende des Dipols.</figcaption>
</figure>

Man verbindet also das Ende des Dipols mit dem oberen Ende des
Schwingkreises. Das Koaxialkabel dagegen wird an ein paar Windungen unten
an der Spule angeschlossen, wo die Impedanz niedrig ist.

> **Nicht verwechseln:** Ein **Tiefpassfilter** lässt die Frequenzen
> unterhalb einer gewählten Grenze durch und hält die darüber zurück. Er
> dient zum Beispiel dazu, dass ein Sender neben seiner Frequenz keine
> höheren Störfrequenzen aussendet. Um eine Antenne am Ende anzuschließen,
> dient er nicht.
