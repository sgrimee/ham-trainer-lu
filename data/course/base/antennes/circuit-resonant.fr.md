---
title: Le circuit résonant parallèle
---

Parfois, on préfère alimenter le dipôle par **un bout**, par exemple quand
ce bout arrive à la fenêtre. Mais là, l'impédance est **très haute** :
plusieurs milliers d'ohms. Un câble de 50 Ω n'y arrive pas, et un balun
1:4 ne donne que 200 Ω : bien trop peu.

## La balançoire

Pense à une balançoire. Si tu la pousses **au bon rythme**, un petit coup
à chaque aller-retour suffit à la faire monter très haut. Elle est en
**résonance** : tu la pousses à **sa** fréquence. C'est le même mot que
pour le dipôle **résonant**, qui a la bonne longueur pour sa fréquence.

Un **circuit résonant** fait la même chose avec l'électricité. Il est fait
de deux composants qu'on ne détaillera pas ici : une **bobine** (un fil
enroulé) et un **condensateur** (deux plaques de métal très proches,
séparées par un isolant). Branchés **côte à côte**, en parallèle, ils se
renvoient l'énergie, comme la balançoire qui va et vient. En réglant l'un
d'eux, on **accorde** ce va-et-vient sur la fréquence voulue.

## Une impédance très haute

À sa fréquence de résonance, un circuit résonant parallèle se balance
presque tout seul : un tout petit courant entretient une grande tension.
Tension forte, courant faible : son impédance est **très haute**, comme au
bout d'un dipôle demi-onde !

<figure>
<svg viewBox="0 0 340 172" width="340" role="img" aria-label="Un dipôle demi-onde alimenté par un bout : le fil part vers la droite depuis le haut d'un circuit résonant parallèle, une bobine et un condensateur côte à côte. Le câble coaxial arrive sur quelques spires en bas de la bobine.">
<path d="M130 30 H330" stroke="#d9822b" stroke-width="4"/>
<text x="230" y="20" font-size="12" fill="#6b7280" text-anchor="middle">dipôle demi-onde (λ ÷ 2)</text>
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M130 30 H60 V50 M130 30 V70 M60 120 V140 H130 V90"/>
<path d="M60 50 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14 a8 7 0 0 1 0 14"/>
<path d="M115 70 H145 M115 90 H145"/>
<path d="M60 106 H20 V150 M60 140 H40 V150"/>
</g>
<g font-size="12" fill="#1c1f26"><text x="76" y="86">bobine</text><text x="152" y="84">condensateur</text></g>
<text x="10" y="164" font-size="11" fill="#6b7280">vers le coaxial</text>
</svg>
<figcaption>Le circuit résonant parallèle, accordé sur la fréquence, présente une impédance très haute, comme le bout du dipôle.</figcaption>
</figure>

On relie donc le bout du dipôle au haut du circuit résonant. Le câble
coaxial, lui, se branche sur quelques spires en bas de la bobine, où
l'impédance est basse.

> **Ne confonds pas :** un **filtre passe-bas** laisse passer les
> fréquences en dessous d'un seuil choisi et arrête celles au-dessus. Il
> sert par exemple à empêcher un émetteur d'envoyer, en plus de sa
> fréquence, des fréquences parasites plus hautes. Il ne sert pas à
> brancher une antenne par le bout.
