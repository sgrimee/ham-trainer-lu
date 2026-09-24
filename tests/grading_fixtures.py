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
