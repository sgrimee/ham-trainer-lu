---
title: Brancher un ampèremètre
---

Tu sais qu'un ampèremètre mesure le courant. Mais où faut-il le mettre dans
le circuit ? Et comment doit-il être fait à l'intérieur ?

## Le courant doit le traverser

Reprenons l'eau. Pour savoir combien d'eau coule dans un tuyau, on installe
un **compteur d'eau** : on coupe le tuyau et on place le compteur au milieu,
pour que **toute l'eau passe dedans**.

L'ampèremètre, c'est pareil. On ouvre le circuit et on l'insère dans la
boucle : le courant passe par la pile, puis par l'ampèremètre, puis par la
lampe. Ils sont **les uns à la suite des autres** : l'ampèremètre est
branché **en série**, comme les piles bout à bout.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Un circuit en boucle : une pile à gauche, une lampe à droite, et un ampèremètre, un cercle marqué A, placé dans le fil du haut, entre les deux">
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M40 75 V40 H154"/><path d="M186 40 H300 V81"/><path d="M300 109 V150 H40 V120"/>
</g>
<rect x="25" y="75" width="30" height="45" rx="4" fill="#f3d9b1" stroke="#b07a2a" stroke-width="2"/>
<circle cx="170" cy="40" r="16" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="170" y="46" font-size="16" font-weight="bold" text-anchor="middle" fill="#2f5fd6">A</text>
<circle cx="300" cy="95" r="14" fill="#ffffff" stroke="#1c1f26" stroke-width="2"/>
<g stroke="#1c1f26" stroke-width="1.5"><path d="M290 85 L310 105"/><path d="M310 85 L290 105"/></g>
<g font-size="12" fill="#6b7280">
<text x="170" y="18" text-anchor="middle">ampèremètre</text>
<text x="64" y="101">pile</text>
<text x="278" y="99" text-anchor="end">lampe</text>
</g>
</svg>
<figcaption>L'ampèremètre est dans la boucle : tout le courant de la lampe passe aussi par lui.</figcaption>
</figure>

## Il ne doit presque pas freiner

Un ampèremètre a lui aussi une résistance. S'il freinait beaucoup, il
passerait moins de courant qu'avant : il fausserait ce qu'il mesure ! Il
doit donc avoir la **plus petite résistance possible**.

Avec la loi d'Ohm, vérifions. Un ampèremètre de 0,1 Ω traversé par 0,5 A
« prend » une tension de U = R × I = 0,1 × 0,5 = **0,05 V**. Sur une pile de
6 V, c'est presque rien : la lampe ne s'aperçoit de rien.

## Le piège : le brancher en parallèle

Si tu branches l'ampèremètre **côte à côte** avec la pile, ses deux fils
directement sur ses bornes, sa toute petite résistance devient un chemin
presque libre. D'après la loi d'Ohm, le courant voudrait monter à
I = U ÷ R = 6 ÷ 0,1 = **60 A** ! C'est un **court-circuit** : le fusible de
l'appareil fond, et c'est justement pour ça qu'il est là.

> **À retenir :** l'ampèremètre se branche **en série**, et sa résistance
> doit être **la plus petite possible**.
