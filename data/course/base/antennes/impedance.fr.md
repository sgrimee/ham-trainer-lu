---
title: L'impédance d'une antenne
---

Tu connais la loi d'Ohm : R = U ÷ I. Mais une antenne est parcourue par un
courant **alternatif**. Que devient cette idée ?

## Une « résistance » pour le courant alternatif

Pour un courant alternatif, on parle d'**impédance** : même idée que la
résistance, tension divisée par courant, en **ohms** (Ω). Grande impédance : beaucoup de tension pour peu de courant.
Sa lettre est **Z**.

## Au milieu ou au bout du dipôle

Dans un dipôle demi-onde, le courant n'est pas le même partout.

- **Au bout d'un brin**, les électrons ne peuvent pas aller plus loin : le
  courant y est **nul**. En revanche, les électrons s'y entassent, puis
  repartent : la tension y est **très forte**.
- **Au milieu**, c'est l'inverse : le courant est le plus **fort**, et la
  tension **faible**.

<figure>
<svg viewBox="0 0 340 220" width="340" role="img" aria-label="Deux graphiques le long d'un dipôle demi-onde, la position le long du dipôle à l'horizontale. En haut, le courant : nul aux deux bouts, le plus fort au milieu. En bas, la tension : très forte aux deux bouts, faible au milieu.">
<g font-size="13" font-weight="bold" fill="#1c1f26"><text x="330" y="14" text-anchor="end">Le courant</text><text x="330" y="128" text-anchor="end">La tension</text></g>
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M30 95 V14"/><path d="M26 20 L30 14 L34 20"/><path d="M30 95 H328"/><path d="M322 91 L328 95 L322 99"/><path d="M30 205 V124"/><path d="M26 130 L30 124 L34 130"/><path d="M30 205 H328"/><path d="M322 201 L328 205 L322 209"/></g>
<g font-size="11" fill="#6b7280"><text x="37" y="20">courant</text><text x="37" y="130">tension</text><text x="328" y="109" text-anchor="end">le long du dipôle</text><text x="328" y="197" text-anchor="end">le long du dipôle</text></g>
<path d="M40 95 Q170 -5 300 95" fill="none" stroke="#2f5fd6" stroke-width="2"/>
<path d="M40 152 C90 152 150 178 170 198 C190 178 250 152 300 152" fill="none" stroke="#c0362c" stroke-width="2"/>
<g font-size="12" text-anchor="middle"><text x="170" y="75" fill="#2f5fd6">fort au milieu</text><text x="62" y="146" fill="#c0362c">forte</text><text x="280" y="146" fill="#c0362c">forte</text><text x="182" y="200" fill="#c0362c" text-anchor="start">faible</text></g>
</svg>
<figcaption>Le courant est fort au milieu et nul aux bouts ; la tension, c'est l'inverse.</figcaption>
</figure>

Divise la tension par le courant :

- au **milieu**, peu de tension, beaucoup de courant : l'impédance est
  **basse**, environ **50 à 75 Ω** ;
- au **bout**, beaucoup de tension, presque pas de courant : l'impédance
  est **très haute**, **plusieurs milliers d'ohms**.

C'est l'**impédance au point d'alimentation** : elle dépend de l'endroit où
l'on branche le câble.

## L'impédance du câble

Un câble coaxial a lui aussi une impédance. Elle ne vient pas de la
résistance du cuivre : elle dépend de la grosseur de l'âme, de la tresse et
de l'isolant, pas de la longueur. Les câbles des radioamateurs font
presque tous **50 Ω** (ceux de la télévision, 75 Ω).

> **À retenir :** pour que la puissance passe bien du câble à l'antenne,
> leurs impédances doivent être **proches**. C'est la question des deux
> prochaines leçons : comment brancher un câble de 50 Ω au milieu, ou au
> bout, d'un dipôle ?
