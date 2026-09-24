---
title: Le gain d'une antenne directive
---

Une lampe de poche envoie sa lumière **dans une direction**, bien plus loin
qu'une ampoule nue. Certaines antennes font pareil avec les ondes radio.

## L'antenne directive

Un dipôle rayonne de tous les côtés à la fois (sauf dans l'axe de son
fil). Une **antenne directive** (on dit aussi « directionnelle »)
concentre sa puissance dans **une direction**, qu'on appelle sa **direction
principale**. La plus connue est l'antenne **Yagi**, qui ressemble aux
antennes de télévision des toits : un dipôle, avec devant lui une rangée de
tiges, les **directeurs**, et derrière un **réflecteur**.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Vus de dessus, à gauche, un dipôle rayonne autant d'un côté que de l'autre, en deux lobes égaux. À droite, une antenne directive envoie presque toute sa puissance dans un grand lobe vers la droite, la direction principale, et très peu vers l'arrière.">
<g font-size="13" font-weight="bold" fill="#1c1f26" text-anchor="middle"><text x="80" y="16">Dipôle</text><text x="240" y="16">Antenne directive</text></g>
<path d="M80 90 C50 50 10 60 10 90 C10 120 50 130 80 90 C110 50 150 60 150 90 C150 120 110 130 80 90 Z" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<path d="M80 70 V110" stroke="#d9822b" stroke-width="4"/>
<path d="M190 90 C230 50 330 70 330 90 C330 110 230 130 190 90 Z M190 90 C180 80 170 83 170 90 C170 97 180 100 190 90 Z" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<g stroke="#d9822b" stroke-width="3"><path d="M184 76 V104 M192 78 V102 M202 80 V100 M212 81 V99"/></g>
<g stroke="#c0362c" stroke-width="2" fill="none"><path d="M240 140 H320"/><path d="M314 135 L320 140 L314 145"/></g>
<text x="280" y="160" font-size="12" fill="#c0362c" text-anchor="middle">direction principale</text>
</svg>
<figcaption>Vue de dessus : même puissance, mais l'antenne directive la concentre dans une direction.</figcaption>
</figure>

Attention : une antenne ne **fabrique** pas de puissance. Ce qu'elle envoie
en plus vers l'avant, elle ne l'envoie plus sur les côtés ni vers
l'arrière.

## Le gain

Le **gain** d'une antenne directive dit combien elle est plus forte qu'une
antenne de référence, **dans sa direction principale**, pour la même
puissance envoyée par l'émetteur. On le donne presque toujours en **dB**.
Un gain de 10 dB, c'est dix fois plus de puissance vers l'avant.

Mais quelle référence ? Il en existe deux.

> **À l'examen, la réponse attendue est** que le gain compare l'antenne
> directive à un **dipôle**, dans la direction principale ; **en réalité**,
> on rencontre aussi une autre référence : l'antenne **isotrope**, une
> antenne imaginaire qui rayonnerait pareil dans toutes les directions. Un
> dipôle fait déjà 2,15 dB de mieux qu'elle. On écrit **dBd** (par rapport
> au dipôle) ou **dBi** (par rapport à l'isotrope) : 5 dBd = 7,15 dBi. Les
> deux se valent, mais il faut toujours savoir lequel on lit.

Ne confonds pas le gain avec l'avant comparé à l'arrière (le **rapport
avant/arrière**) ou aux côtés de la même antenne : ce sont d'autres
mesures. Et le gain ne se calcule pas en comptant les directeurs !
