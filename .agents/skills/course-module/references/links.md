# The "En savoir plus" page

`en-savoir-plus.fr.md` closes every module (specs/LEARN.md §4.2.1): a
`links` list in the frontmatter and a short intro body (~50 words, what to
start with and why).

```yaml
---
title: En savoir plus
links:
- url: https://phet.colorado.edu/fr/simulations/ohms-law
  comment: 'Simulation PhET « Loi d''Ohm » : bouge les curseurs…'
- url: https://www.youtube.com/watch?v=R6WpdF0BO60
  comment: 'Vidéo d''un professeur de physique (collège, 4 min) : …'
  language_note: 🇫🇷 uniquement
---
```

- Keys: `url`, `comment`, `language_note`. `language_note` is required by
  the validator for YouTube, Vimeo and Dailymotion, and by this skill for
  **any** video: « 🇫🇷 uniquement », « sous-titres DE
  disponibles »…
- The comment says what the page is and what the kid will do there, and
  the level when it's a school resource (« 5e », « 3e »).
- 5–9 links. Interactive first (simulations), then pages written for young
  readers, then videos, then something deeper for the curious.

## Sources that worked for module A

- **PhET**, French versions: `https://phet.colorado.edu/fr/simulations/<slug>`
- **Vikidia** (encyclopedia for 8–13 year olds): `https://fr.vikidia.org/wiki/<Titre>`
- **Alloprof** (Quebec, free, secondary level, no geo-blocking):
  `https://www.alloprof.qc.ca/fr/eleves/bv/<matiere>/<slug>`
- **YouTube** official channels: C'est pas sorcier, Vasco (formerly
  L'Esprit Sorcier), Paul Olivier (a collège physics teacher, 4–5 min clips).

**Never use Lumni (lumni.fr) or france.tv**: their videos are geo-blocked
outside France, and this course's learners are in Luxembourg. The same
episodes are often on the official C'est pas sorcier YouTube channel.
- Worth searching for the radio modules: C'est pas sorcier (YouTube),
  fr.wikipedia.org for depth, radio-amateur associations' beginner pages
  (Luxembourg's RL, France's REF), official Luxembourg pages (ILR, guichet.lu)
  for the safety module.

Avoid pages behind a login or a paywall, forums, and anything commercial.

## Every link is opened before it is listed — never write a URL from memory

The built-in WebFetch/WebSearch tools do not work in this environment. Use:

- `mcp__parallel-search__web_search` to find candidates;
- `mcp__fetch__fetch` to read the page and confirm it says what the comment
  claims (Vikidia answers `curl` with a Cloudflare 403, but the fetch tool
  gets through; a 404 means the article doesn't exist under that title);
- `curl -sL <url> | grep -o 'og:title"[^>]*'` for pages rendered by
  JavaScript (PhET returns an empty shell to the fetch tool; its `og:title`
  and `og:description` confirm the simulation and its French name).

Drop a page that is a stub, garbled, or wrong on the physics, even if it is
on-topic (module A dropped Vikidia's « Résistance électrique » for that).
Videos must play in Luxembourg. For YouTube, confirm it from the watch page:
`curl -sL "https://www.youtube.com/watch?v=<id>" | grep -o '"availableCountries":\[[^]]*\]' | grep -c '"LU"'`
must print 1 (the same page has `"title":{"simpleText":…`, `"lengthSeconds"`
and `"ownerChannelName"` to check title, length and channel).
