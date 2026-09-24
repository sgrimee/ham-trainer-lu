---
title: Le balun
---

Un dipôle demi-onde se branche le plus souvent en son **centre**, avec un
câble coaxial. Mais entre les deux, il y a presque toujours un petit
boîtier : le **balun**. À quoi sert-il ?

## Symétrique ou pas ?

Regarde les deux brins du dipôle : ils sont **identiques**, et chacun
reçoit un des deux conducteurs du câble. Ils jouent exactement le même
rôle. On dit que le dipôle est **symétrique** (en anglais *balanced*).

Le câble coaxial, lui, n'est **pas symétrique** (*unbalanced*) : l'âme est
à l'intérieur, la tresse à l'extérieur, les deux conducteurs ne jouent pas
le même rôle.

Si on branche le coaxial directement, une partie du courant s'échappe sur
l'**extérieur** de la tresse : le câble se met à rayonner lui-même, comme s'il faisait
partie de l'antenne. On verra plus tard que ça peut gêner les voisins.

## Le balun fait la liaison

Le **balun** relie une ligne symétrique à une ligne qui ne l'est pas. Son
nom le dit : **BAL**anced-**UN**balanced.

<figure>
<svg viewBox="0 0 340 150" width="340" role="img" aria-label="Le câble coaxial, non symétrique, arrive par le bas dans un boîtier appelé balun. Du balun partent deux fils vers les deux brins identiques du dipôle, qui est symétrique.">
<g stroke="#d9822b" stroke-width="4"><path d="M20 30 H163"/><path d="M177 30 H320"/></g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M163 30 V70"/><path d="M177 30 V70"/></g>
<rect x="140" y="70" width="60" height="34" rx="6" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="170" y="92" font-size="13" text-anchor="middle" fill="#1c1f26">balun</text>
<rect x="164" y="104" width="12" height="40" fill="#9aa3b5" stroke="#1c1f26" stroke-width="1.5"/>
<g font-size="12" fill="#6b7280"><text x="20" y="52">dipôle : symétrique</text><text x="186" y="135">coaxial : pas symétrique</text></g>
</svg>
<figcaption>Le balun relie le câble coaxial, non symétrique, au dipôle, symétrique.</figcaption>
</figure>

## 1:1 ou 1:4 ?

Un balun peut aussi changer l'impédance. On l'indique par deux nombres :

- un balun **1:1** (« un-un ») garde la même impédance : 50 Ω d'un côté,
  50 Ω de l'autre ;
- un balun **1:4** la **multiplie par 4** : 50 Ω côté câble deviennent
  200 Ω côté antenne. Il sert pour les antennes dont l'impédance est
  d'environ 200 Ω.

On choisit celui qui rend les impédances **proches**. Au centre d'un dipôle
demi-onde, l'impédance (50 à 75 Ω) est déjà proche de celle du câble
(50 Ω) : pas besoin de la changer.

> **À retenir :** un balun rend la liaison **symétrique** ; son rapport
> (1:1, 1:4) dit s'il change aussi l'impédance. Pour choisir, regarde
> l'impédance de l'antenne **à l'endroit où tu branches le câble**.
