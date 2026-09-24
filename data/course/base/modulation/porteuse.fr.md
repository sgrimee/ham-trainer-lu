---
title: La porteuse et la modulation
---

Tu sais qu'une onde radio est une onde électromagnétique qui vibre des
millions de fois par seconde. Mais ta voix, elle, comment monte-t-elle
dans cette onde ?

## La voix vibre lentement

Quand tu parles dans un microphone, il transforme ta voix en une petite
tension qui change au même rythme que le son. La partie de la voix qu'on
transmet en radio va d'environ **300 Hz à 3 kHz** : c'est une **basse
fréquence**, qu'on écrit **BF**. La voix est le **signal utile**, celui
qu'on veut transmettre.

Et l'envoyer directement par radio ? Impossible. À 1 kHz, la longueur d'onde
serait (1 kHz = 0,001 MHz) λ = 300 ÷ 0,001 = 300 000 m, soit **300 km** : il
faudrait une antenne géante (tu verras plus tard pourquoi la taille de
l'antenne dépend de λ). Et toutes les stations parleraient sur les mêmes
fréquences.

## Une onde qui porte la voix

L'émetteur fabrique donc une onde de **haute fréquence** (**HF**), par exemple
145 MHz (voir l'encadré à la fin) : c'est la **porteuse**. Comme son nom le
dit, elle **porte** la voix, un peu comme un camion porte un colis. Seule,
sans colis, elle ne transmet aucun message.

Pour y charger la voix, on modifie la porteuse au rythme de la voix : on
dit qu'on la **module**. C'est la **modulation**. Le récepteur fait
l'inverse : il retrouve la voix dans l'onde reçue.

<figure>
<svg viewBox="0 -14 340 200" width="340" role="img" aria-label="Deux graphiques d'un signal en fonction du temps, le temps à l'horizontale et le signal à la verticale. En haut, la voix, en basse fréquence, fait une vague lente. En bas, la porteuse, en haute fréquence, fait beaucoup de vagues rapides pendant le même temps.">
<g font-size="13" font-weight="bold" fill="#1c1f26"><text x="10" y="2">La voix (BF)</text><text x="10" y="92">La porteuse (HF)</text></g>
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M40 78 V8"/><path d="M36 14 L40 8 L44 14"/><path d="M40 50 H330"/><path d="M324 46 L330 50 L324 54"/><path d="M40 170 V98"/><path d="M36 104 L40 98 L44 104"/><path d="M40 140 H330"/><path d="M324 136 L330 140 L324 144"/></g>
<path d="M40 50 Q87 6 133 50 Q180 94 227 50 Q273 6 320 50" fill="none" stroke="#2f5fd6" stroke-width="2"/>
<path d="M40 140 Q45 96 50 140 Q55 184 60 140 Q65 96 70 140 Q75 184 80 140 Q85 96 90 140 Q95 184 100 140 Q105 96 110 140 Q115 184 120 140 Q125 96 130 140 Q135 184 140 140 Q145 96 150 140 Q155 184 160 140 Q165 96 170 140 Q175 184 180 140 Q185 96 190 140 Q195 184 200 140 Q205 96 210 140 Q215 184 220 140 Q225 96 230 140 Q235 184 240 140 Q245 96 250 140 Q255 184 260 140 Q265 96 270 140 Q275 184 280 140 Q285 96 290 140 Q295 184 300 140 Q305 96 310 140 Q315 184 320 140" fill="none" stroke="#c0362c" stroke-width="2"/>
<g font-size="11" fill="#6b7280"><text x="47" y="14">signal</text><text x="330" y="64" text-anchor="end">temps</text><text x="47" y="104">signal</text><text x="330" y="182" text-anchor="end">temps</text></g>
</svg>
<figcaption>La voix vibre lentement, la porteuse très vite. Dans la réalité, la porteuse vibre des milliers de fois plus vite que la voix, et même plus.</figcaption>
</figure>

Il y a deux grandes façons de moduler : changer la **hauteur** de la
porteuse, ou changer sa **fréquence**. Ce sont les deux prochaines leçons.

> **Attention :** en radio, « HF » a deux sens. Tu connais la **famille**
> HF, de 3 à 30 MHz. Mais on dit aussi « signal HF » pour **tout** signal
> radio, par opposition à la **BF** de la voix. Retiens : la porteuse est
> en **HF**, la voix en **BF**.
