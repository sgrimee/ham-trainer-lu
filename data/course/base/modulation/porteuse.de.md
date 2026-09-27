---
title: Der Träger und die Modulation
---

Du weißt, dass eine Funkwelle eine elektromagnetische Welle ist, die
Millionen Mal pro Sekunde schwingt. Aber wie kommt deine Stimme in diese
Welle hinein?

## Die Stimme schwingt langsam

Wenn du in ein Mikrofon sprichst, verwandelt es deine Stimme in eine kleine
Spannung, die sich im selben Takt ändert wie der Schall. Der Teil der
Stimme, den man im Funk überträgt, reicht von etwa **300 Hz bis 3 kHz**:
Das ist eine **Niederfrequenz**, kurz **NF**. Die Stimme ist das
**Nutzsignal**, also das, was man übertragen will.

Und wenn man sie direkt per Funk verschickt? Unmöglich. Bei 1 kHz wäre die
Wellenlänge (1 kHz = 0,001 MHz) λ = 300 : 0,001 = 300 000 m, also
**300 km**: Man bräuchte eine riesige Antenne (warum die Größe der Antenne
von λ abhängt, siehst du später). Und alle Stationen würden auf denselben
Frequenzen sprechen.

## Eine Welle, die die Stimme trägt

Der Sender erzeugt deshalb eine Welle mit **Hochfrequenz** (**HF**), zum
Beispiel 145 MHz (siehe den Kasten am Ende): Das ist der **Träger**, auch
**Trägersignal** genannt. Wie sein Name sagt, **trägt** er die Stimme, so
wie ein Lastwagen ein Paket trägt. Allein, ohne Paket, überträgt er keine
Nachricht.

Um die Stimme aufzuladen, verändert man den Träger im Takt der Stimme: Man
sagt, man **moduliert** ihn. Das ist die **Modulation**. Der Empfänger macht
es umgekehrt: Er holt die Stimme aus der empfangenen Welle wieder heraus.

<figure>
<svg viewBox="0 -14 340 200" width="340" role="img" aria-label="Zwei Diagramme eines Signals über der Zeit, die Zeit waagerecht und das Signal senkrecht. Oben macht die Stimme, in Niederfrequenz, eine langsame Welle. Unten macht der Träger, in Hochfrequenz, in derselben Zeit sehr viele schnelle Wellen.">
<g font-size="13" font-weight="bold" fill="#1c1f26"><text x="10" y="2">Die Stimme (NF)</text><text x="10" y="92">Der Träger (HF)</text></g>
<g stroke="#1c1f26" stroke-width="1.5" fill="none"><path d="M40 78 V8"/><path d="M36 14 L40 8 L44 14"/><path d="M40 50 H330"/><path d="M324 46 L330 50 L324 54"/><path d="M40 170 V98"/><path d="M36 104 L40 98 L44 104"/><path d="M40 140 H330"/><path d="M324 136 L330 140 L324 144"/></g>
<path d="M40 50 Q87 6 133 50 Q180 94 227 50 Q273 6 320 50" fill="none" stroke="#2f5fd6" stroke-width="2"/>
<path d="M40 140 Q45 96 50 140 Q55 184 60 140 Q65 96 70 140 Q75 184 80 140 Q85 96 90 140 Q95 184 100 140 Q105 96 110 140 Q115 184 120 140 Q125 96 130 140 Q135 184 140 140 Q145 96 150 140 Q155 184 160 140 Q165 96 170 140 Q175 184 180 140 Q185 96 190 140 Q195 184 200 140 Q205 96 210 140 Q215 184 220 140 Q225 96 230 140 Q235 184 240 140 Q245 96 250 140 Q255 184 260 140 Q265 96 270 140 Q275 184 280 140 Q285 96 290 140 Q295 184 300 140 Q305 96 310 140 Q315 184 320 140" fill="none" stroke="#c0362c" stroke-width="2"/>
<g font-size="11" fill="#6b7280"><text x="47" y="14">Signal</text><text x="330" y="64" text-anchor="end">Zeit</text><text x="47" y="104">Signal</text><text x="330" y="182" text-anchor="end">Zeit</text></g>
</svg>
<figcaption>Die Stimme schwingt langsam, der Träger sehr schnell. In Wirklichkeit schwingt der Träger viele tausend Mal schneller als die Stimme, oft sogar noch viel schneller.</figcaption>
</figure>

Es gibt zwei große Arten zu modulieren: die **Höhe** der Wellenberge
des Trägers ändern oder seine **Frequenz**. Darum geht es in den nächsten beiden
Lektionen.

> **Achtung:** Im Funk hat „HF“ zwei Bedeutungen. Du kennst die
> **Familie** HF, von 3 bis 30 MHz, die Kurzwelle (KW). Man sagt aber
> auch „HF-Signal“ für **jedes** Funksignal, im Gegensatz zur **NF** der
> Stimme. Merke: Der Träger ist **HF**, die Stimme **NF**.
