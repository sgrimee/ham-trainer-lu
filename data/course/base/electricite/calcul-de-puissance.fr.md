---
title: 'Calculer une puissance : P = U × I'
---

Tu sais que la puissance est la vitesse à laquelle l'électricité travaille.
Mais comment la calculer ?

Réfléchis : un appareil travaille plus vite si on le **pousse plus fort**
(plus de tension) et si **plus de courant** le traverse. La puissance dépend
donc des deux, et la règle est toute simple :

> **P = U × I**
>
> la puissance (en watts) = la tension (en volts) × le courant (en ampères)

## Un exemple de radioamateur

Un poste radio de voiture fonctionne sous **13,8 V** : c'est la tension d'une
batterie de voiture qui est en train de se recharger. Les radioamateurs
utilisent souvent cette tension pour leurs postes, même à la maison.

**Question :** le poste consomme un courant de **4 A**. Quelle puissance
consomme-t-il ?

P = U × I = 13,8 × 4 = **55,2 W**.

## Attention au piège des milliampères

Même poste, 13,8 V, mais il ne consomme plus que **250 mA**. Quelle
puissance ?

**Première étape : convertir.** La formule attend des **ampères**, pas des
milliampères. 250 mA = 250 ÷ 1000 = **0,25 A**.

**Deuxième étape : calculer.** P = 13,8 × 0,25 = **3,45 W**.

Regarde les deux façons de se tromper :

- **Oublier de convertir :** 13,8 × 250 = 3450 W. C'est la puissance d'un
  gros radiateur, pas d'une petite radio ! Le bon sens dit que c'est faux.
- **Garder le « milli » à la fin :** « 3,45 mW ». Non : une fois converti en
  ampères, le résultat est en **watts**, sans préfixe.

<figure>
<svg viewBox="0 0 360 80" width="360" role="img" aria-label="Méthode en trois étapes : convertir en unités sans préfixe, multiplier, vérifier avec le bon sens">
<g font-size="14" text-anchor="middle">
<rect x="5" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="55" y="37" fill="#1c1f26">1. convertir</text><text x="55" y="55" fill="#6b7280" font-size="12">mA → A</text>
<rect x="130" y="15" width="100" height="50" rx="8" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="180" y="37" fill="#1c1f26">2. calculer</text><text x="180" y="55" fill="#6b7280" font-size="12">P = U × I</text>
<rect x="255" y="15" width="100" height="50" rx="8" fill="#e6f4ea" stroke="#16803c" stroke-width="2"/>
<text x="305" y="37" fill="#1c1f26">3. vérifier</text><text x="305" y="55" fill="#6b7280" font-size="12">c'est logique ?</text>
</g>
<g stroke="#1c1f26" stroke-width="2" fill="none"><path d="M107 40 H126"/><path d="M120 35 L126 40 L120 45"/><path d="M232 40 H251"/><path d="M245 35 L251 40 L245 45"/></g>
</svg>
<figcaption>La méthode pour tous les calculs : convertir, calculer, vérifier.</figcaption>
</figure>

> **À l'examen :** les réponses fausses proposées sont justement celles qu'on
> obtient en se trompant de préfixe. Si tu hésites entre des mW, des W et des
> kW, refais la conversion calmement, puis vérifie que le résultat est
> logique pour un poste radio.
