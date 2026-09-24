---
title: La puissance apparente rayonnée (ERP)
---

Tu sais qu'une antenne directive concentre sa puissance dans sa direction
principale. Pour quelqu'un qui se trouve dans cette direction, ton signal
arrive donc **plus fort** qu'avec un simple dipôle. Comment dire « combien
plus fort » avec un seul nombre ?

## Comme si…

Prenons un émetteur de **10 W**, branché sur une antenne Yagi de gain
**10 dBd**. Tu sais que 10 dB, c'est dix fois plus de puissance vers
l'avant qu'avec un dipôle. Dans la direction principale, tout se passe donc
**comme si** un dipôle recevait 10 × 10 = **100 W**.

Ces 100 W s'appellent la **puissance apparente rayonnée**, en anglais
*effective radiated power*, abrégé **ERP**. « Apparente », parce que
l'antenne ne fabrique pas de puissance : l'émetteur n'en fournit toujours
que 10 W. Mais dans la direction principale, l'effet est le même qu'avec
100 W dans un dipôle.

<figure>
<svg viewBox="0 0 360 80" width="360" role="img" aria-label="Calcul de l'ERP en trois cases : la puissance qui arrive à l'antenne, 10 watts, multipliée par le gain en fois, 10, donne l'ERP, 100 watts.">
<g font-size="13" text-anchor="middle">
<rect x="5" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="55" y="37" fill="#1c1f26">puissance</text><text x="55" y="55" fill="#6b7280" font-size="12">10 W</text>
<rect x="130" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="180" y="37" fill="#1c1f26">× gain</text><text x="180" y="55" fill="#6b7280" font-size="12">10 dBd = × 10</text>
<rect x="255" y="15" width="100" height="50" rx="8" fill="#e6f4ea" stroke="#16803c" stroke-width="2"/>
<text x="305" y="37" fill="#1c1f26">= ERP</text><text x="305" y="55" fill="#6b7280" font-size="12">100 W</text>
</g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M107 40 H126"/><path d="M120 35 L126 40 L120 45"/><path d="M232 40 H251"/><path d="M245 35 L251 40 L245 45"/></g>
</svg>
<figcaption>L'ERP, c'est la puissance qui arrive à l'antenne multipliée par le gain de l'antenne.</figcaption>
</figure>

## N'oublie pas le câble

Ce qui compte, c'est la puissance qui **arrive à l'antenne**. Un émetteur
de 50 W, avec un câble qui perd 3 dB : il n'arrive que 25 W. L'antenne a
un gain de 6 dBd, environ × 4. ERP = 25 × 4 = **100 W**. C'est logique : le
câble a divisé par deux, puis l'antenne a multiplié par quatre, dans sa
direction principale seulement.

Avec un gain en dBi (par rapport à l'isotrope), on obtient la PIRE (EIRP
en anglais) : 2,15 dB de plus que l'ERP, car l'isotrope est plus faible que
le dipôle.

> **À retenir :** l'ERP dit l'**effet** de ta station dans la direction
> principale : comme si un dipôle recevait cette puissance. Elle dépend de
> **deux** choses : la puissance qui arrive à l'antenne et le gain de
> l'antenne. Tu t'en serviras pour lutter contre le brouillage.
