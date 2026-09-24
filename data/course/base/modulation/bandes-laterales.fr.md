---
title: Les bandes latérales
---

Une porteuse seule vibre à **une seule** fréquence. Mais dès qu'on la
module, une surprise apparaît : le signal se met à occuper **plusieurs**
fréquences.

## De nouvelles fréquences, de chaque côté

Prenons une porteuse de 1000 kHz, modulée en AM par une note toute simple
de 1 kHz. Les mesures montrent que le signal émis contient alors **trois** fréquences :

- la porteuse, à **1000 kHz** ;
- une fréquence juste au-dessus : 1000 + 1 = **1001 kHz** ;
- une fréquence juste en dessous : 1000 − 1 = **999 kHz**.

Une voix, ce n'est pas une seule note, mais plein de notes mélangées,
jusqu'à environ 3 kHz. Chacune crée sa paire de fréquences. On obtient
donc deux **bandes** de fréquences, de part et d'autre de la porteuse : ce
sont les **bandes latérales** (« latéral » veut dire « sur le côté ») : la
bande latérale **supérieure** au-dessus, l'**inférieure** en dessous.

Un signal AM a donc **deux** bandes latérales. Chacune contient **toute la
voix**, l'une étant le reflet de l'autre, comme dans un miroir. La
porteuse, elle, ne transporte aucun message.

## Un nouveau genre de graphique

Pour les voir, on change de graphique : à l'horizontale, ce n'est plus le
temps mais la **fréquence**.

<figure>
<svg viewBox="0 -14 340 170" width="340" role="img" aria-label="Graphique de la puissance en fonction de la fréquence, la fréquence à l'horizontale et la puissance à la verticale. Au milieu, la porteuse est un grand trait vertical. De chaque côté, un bloc plus bas : la bande latérale inférieure à gauche, la bande latérale supérieure à droite. Une flèche sous le tout indique la largeur de bande.">
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M20 110 V-8"/><path d="M16 -2 L20 -8 L24 -2"/><path d="M20 110 H330"/><path d="M324 106 L330 110 L324 114"/></g>
<path d="M170 110 V14" stroke="#c0362c" stroke-width="4"/>
<path d="M162 110 V66 L90 86 V110 Z" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<path d="M178 110 V66 L250 86 V110 Z" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M90 128 H250"/><path d="M96 124 L90 128 L96 132"/><path d="M244 124 L250 128 L244 132"/><path d="M90 116 V134 M250 116 V134"/></g>
<text x="170" y="146" font-size="12" fill="#1c1f26" text-anchor="middle">largeur de bande</text>
<text x="178" y="12" font-size="12" fill="#c0362c">porteuse</text>
<g font-size="11" fill="#2f5fd6" text-anchor="middle"><text x="118" y="52">bande</text><text x="118" y="64">inférieure</text><text x="222" y="52">bande</text><text x="222" y="64">supérieure</text></g>
<g font-size="11" fill="#6b7280"><text x="27" y="-3">puissance</text><text x="330" y="102" text-anchor="end">fréquence</text></g>
</svg>
<figcaption>Un signal AM : la porteuse au milieu, une bande latérale de chaque côté. Ici, l'horizontale est la fréquence, pas le temps.</figcaption>
</figure>

## La largeur de bande

L'espace de fréquences que le signal occupe, de sa fréquence la plus basse
à sa plus haute, s'appelle sa **largeur de bande**. Dans notre exemple,
avec une voix jusqu'à 3 kHz, le signal va de 997 à 1003 kHz : sa largeur
de bande est de **6 kHz**.

C'est important, car les bandes sont partagées : plus un signal est
large, moins il y a de place pour les voisins.

> **À retenir :** moduler crée des **bandes latérales** de part et d'autre
> de la porteuse. Un signal **AM** en a **deux**. La **largeur de bande**,
> c'est la place qu'un signal prend en fréquences.
