---
title: Brancher un voltmètre
---

La tension, c'est la poussée : une **différence** entre deux points, comme
la différence de hauteur entre deux réservoirs d'eau. Pour la mesurer, on
ne se place donc pas dans le fil : on **compare deux points**.

## Un fil de chaque côté

Pour mesurer la tension d'une lampe, on pose un fil du voltmètre sur
chacune de ses deux bornes. Le voltmètre et la lampe sont alors **côte à
côte**, reliés aux deux mêmes points : le voltmètre est branché **en
parallèle** sur l'élément à mesurer, comme deux piles en parallèle. (En
classe, on dit souvent « en **dérivation** » : c'est la même chose.) Pas
besoin d'ouvrir le circuit.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Un circuit en boucle avec une pile à gauche et une lampe à droite. Un voltmètre, un cercle marqué V, est placé à côté de la lampe : un fil part du haut de la lampe, un autre du bas.">
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
<text x="64" y="101">pile</text>
<text x="198" y="99" text-anchor="end">lampe</text>
<text x="300" y="158" text-anchor="middle">voltmètre</text>
</g>
</svg>
<figcaption>Le voltmètre est à côté de la lampe, relié à ses deux bornes : il compare les deux points.</figcaption>
</figure>

## Il ne doit presque rien laisser passer

En parallèle, le voltmètre ouvre un **deuxième chemin** à côté de la lampe.
Si ce chemin était facile, le voltmètre tirerait lui aussi du courant : il
**détournerait** du courant vers lui et changerait ce qui se passe dans le
circuit. Il doit donc avoir la **plus grande résistance possible**.

La loi d'Ohm le confirme. Un voltmètre de 10 MΩ posé sur 6 V laisse passer
I = U ÷ R = 6 ÷ 10 000 000 = **0,000 000 6 A**. Presque rien !

## Le piège : le brancher en série

Si tu mets le voltmètre **dans la boucle**, comme un ampèremètre, son énorme
résistance bloque presque tout le courant : la lampe s'éteint, et
l'appareil ne mesure plus la tension de la lampe.

> **Ne confonds pas :**
>
> - l'**ampèremètre** est **dans** le chemin : en **série**, résistance la
>   **plus petite** possible, pour ne pas freiner ;
> - le **voltmètre** est **à côté** : en **parallèle**, résistance la **plus
>   grande** possible, pour ne rien détourner.
