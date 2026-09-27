---
title: Der Überspannungsschutz
---

Die Blitzschutzanlage schützt das Gebäude vor einem direkten
Blitzeinschlag. Aber der Blitz kann Schaden anrichten, **ohne** dein Haus
überhaupt zu treffen.

## Spannungsspitzen in den Leitungen

Schlägt ein Blitz ein paar hundert Meter entfernt ein, dann erzeugt sein
riesiger Strom in allen langen Drähten der Umgebung einen heftigen Stoß:
eine **Überspannung**. Sie kann Tausende Volt erreichen, für weniger als
eine tausendstel Sekunde. Das reicht völlig, um ein Funkgerät zu zerstören
oder einen Funken überspringen zu lassen.

Und eine Amateurfunkstation hat viele lange Leitungen, die von draußen
kommen:

- das **Koaxialkabel** der Antenne, eine **HF-Leitung** (sie führt
  Hochfrequenz), die vom Dach herunterkommt: Die
  Überspannung wandert in seinen Leitern, im Innenleiter wie im Geflecht;
- die **Steuerleitungen**, zum Beispiel die Drähte des kleinen Motors, der
  die Antenne dreht;
- das Netzkabel.

## Den Eingang des Gebäudes schützen

Die Abwehr sitzt **dort, wo die Leitungen ins Gebäude kommen**: ein
**Überspannungsschutz** (auch „Überspannungsableiter“ genannt) an jeder
Leitung, mit der Erde verbunden. Normalerweise lässt er das Signal
durch, ohne etwas zu ändern. Kommt eine Spitze, dann leitet er blitzschnell
und schickt die Überspannung in die Erde, statt sie bis zum Funkgerät
durchzulassen.

<figure>
<svg viewBox="0 0 340 170" width="340" role="img" aria-label="Ein Antennenkabel geht durch die Wand eines Hauses. Gleich hinter der Wand ist ein Überspannungsschutz mit der Erde verbunden: Die Spannungsspitze von draußen fließt in die Erde, statt bis zum Funkgerät zu gelangen.">
<g font-size="12" fill="#6b7280" text-anchor="middle"><text x="75" y="20">draußen</text><text x="255" y="20">drinnen</text></g>
<rect x="150" y="10" width="20" height="140" fill="#9aa3b5" stroke="#1c1f26" stroke-width="1.5"/>
<path d="M10 60 H270" stroke="#1c1f26" stroke-width="3"/>
<path d="M30 60 H50 L58 32 L66 60 H80" fill="none" stroke="#c0362c" stroke-width="2.5"/>
<text x="58" y="82" font-size="12" fill="#c0362c" text-anchor="middle">Überspannung</text>
<rect x="180" y="46" width="50" height="28" rx="4" fill="#eef2ff" stroke="#2f5fd6" stroke-width="2"/>
<text x="205" y="39" font-size="12" fill="#2f5fd6" text-anchor="middle">Schutz</text>
<path d="M205 74 V130" stroke="#16803c" stroke-width="3"/>
<g stroke="#16803c" stroke-width="2"><path d="M193 130 H217"/><path d="M197 136 H213"/><path d="M201 142 H209"/></g>
<g stroke="#c0362c" stroke-width="2" fill="none"><path d="M216 104 V126"/><path d="M211 118 L216 126 L221 118"/></g>
<text x="224" y="124" font-size="12" fill="#c0362c">zur Erde</text>
<rect x="270" y="45" width="60" height="30" rx="4" fill="#f3d9b1" stroke="#b07a2a" stroke-width="2"/>
<text x="300" y="65" font-size="12" fill="#1c1f26" text-anchor="middle">Gerät</text>
</svg>
<figcaption>Am Eingang des Gebäudes schickt der Überspannungsschutz die Spannungsspitze in die Erde, bevor sie das Funkgerät erreicht.</figcaption>
</figure>

Warum nicht etwas anderes?

- Eine **Sicherung** schaltet ab, wenn ein zu starker Strom eine Weile
  fließt: Für eine so kurze Spitze ist sie viel zu langsam, und sie
  schickt nichts in die Erde.
- Ein Rohr um die Leitung ändert nichts, auch nicht ein feuerfestes aus
  Keramik: Die Überspannung wandert **in** den Leitern, ganz innen.
- Alle Antennen sind betroffen, kleine wie große, für KW wie für UKW.

> **Merke:** Antennenleitungen und Steuerleitungen bekommen an ihrem
> Eingang ins Gebäude einen **Überspannungsschutz**. Und wenn ein Gewitter
> kommt, trenn die Antenne vom Funkgerät.
