"""Golden cases for the open-answer grader (specs/TRAINER.md §7.2, §10).

Each case is a real catalogue question with a synthetic candidate answer whose
correct verdict a human examiner can state independently. They exist to answer
one question: can a given model be trusted to grade, and does a change to the
grader prompt improve or regress it?

Two of them are load-bearing:
  *-TRAP     a complete answer with one false statement added. A grader that
             calls these `correct` is lenient, and teaches the candidate
             something wrong. This is the failure mode that matters most.
  465-THREE  the question asks for three items, the reference lists five.
             A grader that diffs against the reference instead of reading the
             question marks a correct answer 60%. Questions 465 and 469 have
             this shape; 469 is BASE-tagged, so it reaches the simplest exam.

Run tests/eval_grader.py to score a model against them.
"""

import json
import pathlib

# Each case: (qid, lang, question, reference, candidate, expected_verdict, must_flag, why)
# expected_verdict: what a competent human examiner would say.
# must_flag: a substring the grader's `incorrect` list must catch (None = nothing wrong).
CASES = [
    (
        "452-ok",
        "fr",
        "Quel est le signal international de détresse en radiotéléphonie ?",
        "MAYDAY",
        "MAYDAY",
        "correct",
        None,
        "exact match",
    ),
    (
        "452-wrong",
        "fr",
        "Quel est le signal international de détresse en radiotéléphonie ?",
        "MAYDAY",
        "SOS",
        "incorrect",
        None,
        "SOS is telegraphy, not radiotelephony",
    ),
    (
        "495-ok",
        "fr",
        "Quels sont les types de certificats d'opérateur établis par l'Institut ?",
        "Les certificats sont : Le certificat de BASE, le certificat NOVICE et le certificat HAREC.",
        "BASE, NOVICE et HAREC",
        "correct",
        None,
        "all three, phrased tersely",
    ),
    (
        "495-partial",
        "fr",
        "Quels sont les types de certificats d'opérateur établis par l'Institut ?",
        "Les certificats sont : Le certificat de BASE, le certificat NOVICE et le certificat HAREC.",
        "Le certificat de BASE et le certificat HAREC.",
        "partial",
        None,
        "NOVICE missing",
    ),
    (
        "495-TRAP",
        "fr",
        "Quels sont les types de certificats d'opérateur établis par l'Institut ?",
        "Les certificats sont : Le certificat de BASE, le certificat NOVICE et le certificat HAREC.",
        "Le certificat de BASE, le certificat NOVICE, le certificat HAREC et le certificat CEPT Classe 1.",
        "partial",
        "CEPT",
        "LENIENCY TRAP: all 3 present plus an invented fourth certificate",
    ),
    (
        "495-de",
        "de",
        "Welche Arten von Funkerzertifikate werden vom Institut ausgestellt?",
        "Die Zertifikate sind : das Grundzertifikat, das NOVICE-Zertifikat und HAREC-Zertifikat.",
        "Grundzertifikat, NOVICE und HAREC",
        "correct",
        None,
        "German, all three",
    ),
    (
        "465-THREE",
        "fr",
        "Énumérez trois bandes de fréquences à utilisation primaires en dessous de 30MHz "
        "pour le service radioamateur !",
        "7000 – 7100kHz 14000 – 14250kHz 21000 – 21450kHz 24890 – 24990kHz 28000 – 29700kHz",
        "7000-7100 kHz, 14000-14250 kHz et 21000-21450 kHz",
        "correct",
        None,
        "OVER-STRICTNESS TEST: question asks for three; reference lists five. "
        "Naive element-counting gives 60%.",
    ),
    (
        "465-TRAP",
        "fr",
        "Énumérez trois bandes de fréquences à utilisation primaires en dessous de 30MHz "
        "pour le service radioamateur !",
        "7000 – 7100kHz 14000 – 14250kHz 21000 – 21450kHz 24890 – 24990kHz 28000 – 29700kHz",
        "7000-7100 kHz, 14000-14250 kHz et la bande CB 26965-27405 kHz",
        "partial",
        "CB",
        "two valid, third is Citizens Band, not an amateur allocation",
    ),
    (
        "445-ok",
        "fr",
        "Comment épelle-t-on l'indicatif d'appel \"LX6JO/MM\"?",
        "LIMA X-RAY SIX JULIETT OSCAR SLASH MARITIME MOBILE",
        "LIMA X-RAY SIX JULIETT OSCAR SLASH MARITIME MOBILE",
        "correct",
        None,
        "exact",
    ),
    (
        "445-partial",
        "fr",
        "Comment épelle-t-on l'indicatif d'appel \"LX6JO/MM\"?",
        "LIMA X-RAY SIX JULIETT OSCAR SLASH MARITIME MOBILE",
        "LIMA X-RAY SIX JULIETT OSCAR",
        "partial",
        None,
        "suffix /MM not spelled out",
    ),
    (
        "448-para",
        "fr",
        "Que signifie le Q-code suivant : QRT?",
        "Dois-je cesser la transmission ?",
        "Est-ce que je dois arrêter d'émettre ?",
        "correct",
        None,
        "PARAPHRASE TEST: same meaning, different words",
    ),
    # Expectation revised 2026-09-22, after the fact and deliberately. It was first
    # written as `partial` -- a guess that an examiner would give half marks for the
    # right topic in the wrong form. Every model graded it `correct` until the
    # speech-act rule went into the prompt, and all three then returned `incorrect`.
    # `incorrect` is the better expectation: the question asks what the Q-code MEANS,
    # the reference answer is one element, and the wrong form is the wrong meaning --
    # QRT? asks "must I stop?", QRT tells the other station to stop. Getting the
    # direction backwards is an operational error, not a wording slip. Awarding half
    # would need the single element split into topic and form; whether it should be
    # is open (specs/TRAINER.md §13).
    (
        "448-form",
        "fr",
        "Que signifie le Q-code suivant : QRT?",
        "Dois-je cesser la transmission ?",
        "J'arrête l'émission.",
        "incorrect",
        None,
        "SPEECH ACT: QRT? is interrogative; the statement form is QRT. Wrong form, wrong meaning",
    ),
]


# --- BASE parts 2 and 3 (specs/LEARN-2-3.md §4.5) ------------------------------
#
# The 17 open questions of parts 2-3 the LLM grades (440-446, spelling, are in
# spelling_fixtures.py). Question and reference are read from the catalogue and
# shaped exactly as app/session.py's grade_open_question sends them, stem and
# sub-item label included, so these cases measure what candidates get.
#
# Three expected verdicts beyond the ones above:
#   near  right in substance, but a term or name the ILR would want in its
#         official form ("la friture" for "parasites"): the grader must flag
#         it (specs/LEARN-2-3.md §4.2), and it scores as missing.
#   correct on a guide wording: where the catalogue and the ILR guide word an
#         answer differently (specs/LEARN-2-3.md §1.3), both are official.
# must_flag on a near case is not checked (it names the near word, for the
# reader); on the others it is the false statement, as above.


_QUESTIONS = {
    q["id"]: q
    for q in map(
        json.loads, (pathlib.Path(__file__).resolve().parent.parent / "data" / "questions.jsonl").open()
    )
}


def _catalogue_case(cid, qid, item_no, candidate, expected, must_flag, why):
    """`candidate` None means the reference answer itself."""
    q = _QUESTIONS[qid]
    item = next(i for i in q["answer"] if i["item_no"] == item_no)
    stem = q["text"]["fr"]
    question = f"{stem}\n{item['label']}" if item.get("label") else stem
    reference = item["text"]["fr"]
    return (cid, "fr", question, reference, candidate or reference, expected, must_flag, why)


def _reference(qid):
    """The catalogue's reference answer, which must grade as correct."""
    return _catalogue_case(f"{qid}-ref", qid, 0, None, "correct", None, "reference verbatim")


# 471's seven distinct prohibitions, advertising named once.
SEVEN = (
    "Contacter des stations non autorisées ; communiquer pour le compte d'un tiers ;"
    " faire de la publicité commerciale ; émettre de la musique ou de la radiodiffusion ;"
    " chiffrer ses communications ; porter atteinte à la sûreté de l'État, aux bonnes mœurs,"
    " aux lois ou à l'ordre public ; émettre de faux signaux de détresse"
)

C = _catalogue_case
PART_2_3 = [
    # 448: Q-code meanings, one sub-item each
    C("448.2-ref", 448, 2, "Vous êtes appelé par LX1SD.", "correct", None, "reference verbatim"),
    C("448.2-form", 448, 2, "Qui m'appelle ?", "incorrect", None, "QRZ? (question), not QRZ"),
    C("448.3-para", 448, 3, "Il est 16h30 UTC.", "correct", None, "paraphrase"),
    C("448.3-qrx", 448, 3, "Je vous rappellerai à 16:30 UTC.", "incorrect", None, "that is QRX"),
    C(
        "448.4-guide",
        448,
        4,
        "La force de vos signaux varie-t-elle ?",
        "correct",
        None,
        "GUIDE WORDING: the guide's table writes 'vos signaux' for QSB? (LEARN-2-3 §1.3)",
    ),
    C(
        "448.5-guide",
        448,
        5,
        "Je suis occupé avec une autre station. Prière de ne pas perturber.",
        "correct",
        None,
        "GUIDE WORDING: 'occupé avec …', 'ne pas perturber'",
    ),
    C("448.6-ref", 448, 6, "Je suis brouillé.", "correct", None, "reference verbatim"),
    C(
        "448.6-qrn",
        448,
        6,
        "Je suis troublé par des parasites atmosphériques.",
        "incorrect",
        None,
        "CLASSIC: QRN given for QRM",
    ),
    C("448.7-para", 448, 7, "Où se trouve votre station ?", "correct", None, "paraphrase"),
    C("448.7-form", 448, 7, "Ma position est Luxembourg.", "incorrect", None, "QTH (statement), not QTH?"),
    # 449
    C(
        "449.1-guide",
        449,
        1,
        "Devez-vous changer de fréquence de transmission ?",
        "correct",
        None,
        "GUIDE WORDING: the guide phrases QSY? as 'Devez-vous…' (LEARN-2-3 §1.3)",
    ),
    C("449.2-ref", 449, 2, "La force de vos signaux est ….", "correct", None, "reference verbatim"),
    C(
        "449.3-guide",
        449,
        3,
        "Je suis troublé par des parasites atmosphériques.",
        "correct",
        None,
        "GUIDE WORDING: 'parasites atmosphériques'",
    ),
    C("449.3-near", 449, 3, "J'ai de la friture.", "near", "friture", "NEAR: 'friture' for 'parasites'"),
    C("449.3-qrm", 449, 3, "Je suis brouillé.", "incorrect", None, "CLASSIC: QRM given for QRN"),
    C("449.4-qrp", 449, 4, "Diminuez la puissance d'émission.", "incorrect", None, "QRP, the opposite"),
    C("449.4-near", 449, 4, "Mets plus de jus !", "near", "jus", "NEAR: slang for 'puissance'"),
    C("449.5-para", 449, 5, "Pouvez-vous confirmer que vous m'avez reçu ?", "correct", None, "paraphrase"),
    C("449.6-qtr", 449, 6, "L'heure exacte est 18:45 UTC.", "incorrect", None, "that is QTR"),
    # 450, 451: abbreviations
    C("450.1-va", 450, 1, "Fin de vacation", "incorrect", None, "that is VA"),
    C("450.2-partial", 450, 2, "Lisibilité, force du signal", "partial", None, "tone missing"),
    C("450.3-ref", 450, 3, "Messages", "correct", None, "reference verbatim"),
    C("451.2-tx", 451, 2, "Émetteur", "incorrect", None, "that is TX"),
    # Decided 2026-09-25 by the project owner: only "Reçu" or "Received";
    # "Roger", the on-air word, is wrong (a note in data/official_wordings.yaml).
    C("451.3-roger", 451, 3, "Roger", "incorrect", None, "the on-air word, refused"),
    C("451.3-received", 451, 3, "Received", "correct", None, "accepted, in English"),
    # 452
    C("452-repeated", 452, 0, "MAYDAY MAYDAY MAYDAY", "correct", None, "said three times, as on the air"),
    # Revised 2026-09-25 after the first run, like 448-form: first written as
    # `near`, but the signal is a fixed word and its French origin is not it. The
    # model's `incorrect` is the better expectation.
    C("452-origin", 452, 0, "M'aidez", "incorrect", None, "the French origin of the word, not the signal"),
    # 456
    _reference(456),
    C(
        "456-para",
        456,
        0,
        "Je le dis quand je commence et quand je finis d'émettre, et au minimum toutes les 5 minutes"
        " pendant que j'émets.",
        "correct",
        None,
        "PARAPHRASE, informal but in ordinary words: must not be flagged near",
    ),
    C(
        "456-partial",
        456,
        0,
        "Au début et à la fin de chaque émission.",
        "partial",
        None,
        "5 minutes missing",
    ),
    C(
        "456-TRAP",
        456,
        0,
        "Au début et à la fin de chaque émission, et au moins toutes les dix minutes.",
        "partial",
        "dix",
        "LENIENCY TRAP: ten minutes, not five",
    ),
    # 459, 464: who allocates bands
    _reference(459),
    C("459-terse", 459, 0, "L'UIT", "correct", None, "the acronym alone"),
    # Decided 2026-09-25 by the project owner: the name needs "internationale";
    # without it, it is not the UIT's name, and the answer is wrong, not near.
    C("459-no-intl", 459, 0, "L'Union des télécoms", "incorrect", None, "the name lacks 'internationale'"),
    C("459-ilr", 459, 0, "L'ILR", "incorrect", None, "national, not international"),
    _reference(464),
    C("464-terse", 464, 0, "L'ILR", "correct", None, "the acronym alone"),
    C(
        "464-near",
        464,
        0,
        "Le régulateur luxembourgeois",
        "near",
        "régulateur",
        "NEAR: describes it, never names it",
    ),
    C("464-itu", 464, 0, "L'UIT", "incorrect", None, "international, not national"),
    # 466-468: what BASE allows
    _reference(466),
    C("466-terse", 466, 0, "10 m, 2 m et 70 cm", "correct", None, "terse"),
    C(
        "466-freq",
        466,
        0,
        "28-29,7 MHz, 144-146 MHz et 430-440 MHz",
        "correct",
        None,
        "as the guide's frequencies",
    ),
    C("466-partial", 466, 0, "10 m et 2 m", "partial", None, "70 cm missing"),
    C(
        "466-TRAP",
        466,
        0,
        "10 m, 2 m, 70 cm et 20 m",
        "partial",
        "20",
        "LENIENCY TRAP: 20 m is not a BASE band",
    ),
    _reference(467),
    C(
        "467-pep",
        467,
        0,
        "25 W PEP à la sortie de l'émetteur",
        "correct",
        None,
        "with PEP, as the guide says",
    ),
    C("467-wrong", 467, 0, "100 W", "incorrect", None, "CLASSIC: NOVICE's power"),
    _reference(468),
    C(
        "468-guide",
        468,
        0,
        "BASE 25 W PEP, NOVICE 100 W PEP, HAREC 100 W PEP la première année puis 1000 W PEP",
        "correct",
        None,
        "GUIDE: HAREC's first year is limited to 100 W (LEARN-2-3 §1.3)",
    ),
    C(
        "468-kw",
        468,
        0,
        "25 W, 100 W et 1 kW PEP",
        "correct",
        None,
        "1 kW = 1000 W; order BASE, NOVICE, HAREC",
    ),
    C(
        "468-TRAP",
        468,
        0,
        "BASE 25 W PEP, NOVICE 50 W PEP, HAREC 1000 W PEP",
        "partial",
        "50",
        "LENIENCY TRAP: NOVICE is 100 W",
    ),
    # 469: six topics of ten (the 465-THREE shape)
    C(
        "469-SIX",
        469,
        0,
        "L'électricité, l'informatique, l'astronomie, la météo, la réglementation amateur"
        " et la vie des clubs.",
        "correct",
        None,
        "OVER-STRICTNESS TEST: six asked, ten in the reference",
    ),
    C(
        "469-TRAP",
        469,
        0,
        "L'électricité, l'informatique, l'astronomie, la météo, la réglementation amateur et la politique.",
        "partial",
        "politique",
        "LENIENCY TRAP: five valid, politics is not allowed",
    ),
    # 471: prohibitions
    _reference(471),
    C(
        "471-seven",
        471,
        0,
        SEVEN + ".",
        "correct",
        None,
        "The catalogue lists advertising twice (c, e): naming it once is complete (LEARN-2-3 §1.3)",
    ),
    C(
        "471-ninth",
        471,
        0,
        SEVEN + " ; relier sa station à un réseau de télécommunications autre qu'Internet.",
        "correct",
        None,
        "The guide's ninth rule is true, not an incorrect statement",
    ),
    C(
        "471-partial",
        471,
        0,
        "Pas de publicité, pas de musique, pas de chiffrement, pas de faux appels de détresse.",
        "partial",
        None,
        "four of seven",
    ),
    C(
        "471-TRAP",
        471,
        0,
        SEVEN + " ; parler de météo.",
        "partial",
        "météo",
        "LENIENCY TRAP: weather is an allowed topic",
    ),
    # 476: the catalogue's itu.org only redirects to itu.int
    _reference(476),
    C("476-int", 476, 0, "www.itu.int", "correct", None, "GUIDE: annex 5.5 writes itu.int (LEARN-2-3 §1.3)"),
    C("476-bare-int", 476, 0, "itu.int", "correct", None, "www. optional (decision 2026-09-27)"),
    C("476-bare-org", 476, 0, "itu.org", "correct", None, "www. optional (decision 2026-09-27)"),
    C("476-ilr", 476, 0, "www.ilr.lu", "incorrect", None, "the ILR's site"),
    # 489: the minister, not the ILR
    _reference(489),
    C("489-terse", 489, 0, "Le ministre chargé des ondes radioélectriques", "correct", None, "paraphrase"),
    C("489-ilr", 489, 0, "L'ILR", "incorrect", None, "CLASSIC: what a reader of the guide answers"),
    # 490, 495: the three certificates
    _reference(490),
    C("490-partial", 490, 0, "NOVICE et HAREC", "partial", None, "BASE missing"),
    # Decided 2026-09-25 by the project owner: "BASIC" is accepted for BASE.
    C("495-basic", 495, 0, "BASIC, NOVICE et HAREC", "correct", None, "BASIC accepted; BASE is the name"),
]
del C

CASES += PART_2_3


def _german_case(cid, qid, item_no, candidate, expected, must_flag, why):
    """A German answer (specs/LEARN-DE.md §2.5): the German stem, and the
    German reference or, where the catalogue has none (452, 468, 476), the
    language-neutral cell, as `session.ref_text` sends them. `candidate`
    None means the reference answer itself."""
    q = _QUESTIONS[qid]
    item = next(i for i in q["answer"] if i["item_no"] == item_no)
    stem = q["text"]["de"]
    question = f"{stem}\n{item['label']}" if item.get("label") else stem
    reference = item["text"].get("de") or item["text"]["fr"]
    return (cid, "de", question, reference, candidate or reference, expected, must_flag, why)


# The German cases, one or more per open BASE question the LLM grades, built
# from the German audit (specs/LEARN-DE.md §3.3). "DECISION" cases rest on a
# `lang: de` entry of data/official_wordings.yaml.
G = _german_case
GERMAN = [
    G("452-de-ref", 452, 0, None, "correct", None, "neutral reference: MAYDAY"),
    G("452-de-sos", 452, 0, "SOS", "incorrect", None, "SOS is telegraphy, not voice"),
    G("476-de-ref", 476, 0, None, "correct", None, "neutral reference"),
    G("476-de-int", 476, 0, "www.itu.int", "correct", None, "DECISION: itu.int is the ITU's own address"),
    G("489-de-ref", 489, 0, None, "correct", None, "reference verbatim"),
    G("489-de-ilr", 489, 0, "Das ILR", "incorrect", None, "CLASSIC: the regulator, not the minister"),
    G("490-de-ref", 490, 0, None, "correct", None, "reference verbatim"),
    G(
        "490-de-base",
        490,
        0,
        "BASE, NOVICE und HAREC",
        "correct",
        None,
        "DECISION: BASE is the Grundzertifikat, not near",
    ),
    G("495-de-partial", 495, 0, "Das NOVICE- und das HAREC-Zertifikat.", "partial", None, "BASE missing"),
    G("459-de-ref", 459, 0, None, "correct", None, "reference verbatim: the English name"),
    G(
        "459-de-german-name",
        459,
        0,
        "Die Internationale Fernmeldeunion (ITU)",
        "correct",
        None,
        "DECISION: the German name is as right as the English one",
    ),
    G("459-de-ilr", 459, 0, "Das ILR", "incorrect", None, "national, not international"),
    G("464-de-ref", 464, 0, None, "correct", None, "reference verbatim"),
    G(
        "464-de-official",
        464,
        0,
        "Das ILR, Institut Luxembourgeois de Régulation",
        "correct",
        None,
        "DECISION: the ILR's own (French) name",
    ),
    G("466-de-ref", 466, 0, None, "correct", None, "reference verbatim"),
    G(
        "466-de-freq",
        466,
        0,
        "28-29,7 MHz, 144-146 MHz und 430-440 MHz",
        "correct",
        None,
        "DECISION: the bands as frequency ranges",
    ),
    G("466-de-80m", 466, 0, "10 m, 2 m und 80 m", "partial", "80", "70 cm replaced by 80 m"),
    G("467-de-ref", 467, 0, None, "correct", None, "reference verbatim, without PEP"),
    G(
        "467-de-pep",
        467,
        0,
        "25 W PEP am Senderausgang",
        "correct",
        None,
        "DECISION: 25 W PEP, as the guide says",
    ),
    G("467-de-100", 467, 0, "100 W", "incorrect", None, "CLASSIC: NOVICE's power"),
    G("468-de-ref", 468, 0, None, "correct", None, "neutral, half-German reference"),
    G(
        "468-de-first-year",
        468,
        0,
        "Grundzertifikat 25 W PEP, NOVICE 100 W PEP, HAREC im ersten Jahr 100 W PEP, danach 1000 W PEP",
        "correct",
        None,
        "DECISION: HAREC's first year at 100 W, from the guide",
    ),
    G("456-de-ref", 456, 0, None, "correct", None, "reference verbatim"),
    G(
        "456-de-10min",
        456,
        0,
        "Am Anfang und am Ende jeder Sendung, und währenddessen mindestens alle zehn Minuten.",
        "partial",
        "zehn",
        "ten minutes, not five",
    ),
    G("448.1-de-ref", 448, 1, None, "correct", None, "reference verbatim"),
    G(
        "448.1-de-guide",
        448,
        1,
        "Sollen Sie die Übermittlung einstellen?",
        "correct",
        None,
        "DECISION: the guide's 'Devez-vous', in German",
    ),
    G(
        "448.6-de-qrn",
        448,
        6,
        "Ich werde durch atmosphärische Störungen beeinträchtigt.",
        "incorrect",
        None,
        "QRN for QRM",
    ),
    G(
        "448.7-de-standort",
        448,
        7,
        "Wo ist Ihr Standort?",
        "correct",
        None,
        "paraphrase: Standort for Position",
    ),
    G("449.3-de-ref", 449, 3, None, "correct", None, "reference verbatim, 'Parasiten' included"),
    G(
        "449.3-de-stoerungen",
        449,
        3,
        "Ich werde durch atmosphärische Störungen beeinträchtigt.",
        "correct",
        None,
        "DECISION: the right German for the catalogue's mistranslated 'Parasiten'",
    ),
    G("449.3-de-qrm", 449, 3, "Ich werde gestört.", "incorrect", None, "CLASSIC: QRM given for QRN"),
    G("449.4-de-qrp", 449, 4, "Verringern Sie die Sendeleistung.", "incorrect", None, "QRP, the opposite"),
    G("450.2-de-partial", 450, 2, "Lesbarkeit, Signalstärke", "partial", None, "tone missing"),
    G("450.1-de-ref", 450, 1, None, "correct", None, "reference verbatim"),
    G("451.3-de-roger", 451, 3, "Roger", "incorrect", None, "DECISION: the on-air word, refused"),
    G("451.3-de-received", 451, 3, "Received", "correct", None, "DECISION: accepted, in English"),
    G("451.2-de-tx", 451, 2, "Sender", "incorrect", None, "that is TX"),
    G(
        "469-de-six",
        469,
        0,
        "Elektrizität, Informatik, Astronomie, Wetter, Amateurfunkvorschriften, Vereinsleben",
        "correct",
        None,
        "DECISION: six valid topics, in plain German",
    ),
    G(
        "469-de-TRAP",
        469,
        0,
        "Elektrizität, Informatik, Astronomie, Wetter, Politik, Vereinsleben",
        "partial",
        "Politik",
        "LENIENCY TRAP: politics is not an allowed topic",
    ),
    G(
        "471-de-nine",
        471,
        0,
        "Keine Verbindung mit nicht zugelassenen Stationen; nichts für Dritte; keine Werbung; keine Musik"
        " und kein Rundfunk; keine Verschlüsselung; nichts gegen die Sicherheit des Staates, die Moral, die"
        " Gesetze oder die öffentliche Ordnung; keine falschen Notrufe; die Station an kein"
        " Telekommunikationsnetz außer dem Internet anschließen",
        "correct",
        None,
        "the German reference's eight distinct rules, the ninth (i) included",
    ),
    G(
        "471-de-without-i",
        471,
        0,
        "Keine Verbindung mit nicht zugelassenen Stationen; nichts für Dritte; keine Werbung; keine Musik"
        " und kein Rundfunk; keine Verschlüsselung; nichts gegen die Sicherheit des Staates, die Moral, die"
        " Gesetze oder die öffentliche Ordnung; keine falschen Notrufe",
        "partial",
        None,
        "the German reference also expects (i), which the French one lacks",
    ),
]
del G

CASES += GERMAN
