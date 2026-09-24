---
title: Réglage AC ou DC
---

Tu sais qu'il existe deux sortes de courant : le **continu** (DC), toujours
dans le même sens, et l'**alternatif** (AC), qui fait du va-et-vient. Le
multimètre doit savoir lequel tu mesures.

## Deux réglages pour chaque mesure

Sur le sélecteur, les positions V et A existent en double. Un petit dessin à
côté de la lettre indique le réglage :

<figure>
<svg viewBox="0 0 300 110" width="300" role="img" aria-label="Deux positions du sélecteur. À gauche, V suivi d'un trait plein au-dessus d'un trait en pointillés : c'est le réglage continu, DC. À droite, V suivi d'une petite vague : c'est le réglage alternatif, AC.">
<rect x="20" y="15" width="120" height="80" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<rect x="160" y="15" width="120" height="80" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<g font-size="28" font-weight="bold" text-anchor="middle" fill="#1c1f26"><text x="50" y="62">V</text><text x="190" y="62">V</text></g>
<g stroke="#1c1f26" stroke-width="2" fill="none">
<path d="M72 45 H118"/><path d="M72 55 H118" stroke-dasharray="6 4"/>
<path d="M212 50 q10 -14 20 0 t20 0"/>
</g>
<g font-size="12" text-anchor="middle" fill="#1c1f26"><text x="80" y="85">DC : continu</text><text x="220" y="85">AC : alternatif</text></g>
</svg>
<figcaption>Le trait plein et les pointillés veulent dire continu ; la vague veut dire alternatif.</figcaption>
</figure>

- Une pile, une batterie, un poste radio sur 13,8 V : réglage **DC**.
- Les prises de la maison : c'est de l'**AC**. Mais n'y mesure jamais
  toi-même : c'est dangereux, on verra pourquoi plus tard.

Sur le réglage DC, le multimètre montre aussi le **sens** : si tu inverses
les deux fils sur une pile de 1,5 V, l'écran affiche « −1,5 V ».

## Et si on se trompe de réglage ?

Imagine : tu mesures une pile de 9 V avec le voltmètre réglé sur **AC**.
Sur la plupart des multimètres, l'écran affiche **0 V**. La pile n'est pas
vide ! En réglage AC, l'appareil ne regarde que le **va-et-vient**, et le
continu n'en fait pas. Pareil pour l'ampèremètre et un courant continu.

**À l'examen, la réponse attendue est que l'appareil affiche 0 ; en
réalité, cela dépend de l'appareil.** Certains, comme de vieux appareils à
aiguille, affichent quand même un nombre, pas forcément juste.

Ce qui ne se passe pas :

- le courant dans le circuit ne change pas, rien ne grille ;
- il n'y a pas de « petit courant » pour lequel AC et DC reviendraient au
  même ;
- le signe « − » n'apparaît qu'en réglage DC, fils inversés.

> **À l'examen :** continu mesuré en réglage AC → l'appareil affiche
> **0**. Dans la vraie vie, vérifie toujours ton réglage avant de mesurer.
