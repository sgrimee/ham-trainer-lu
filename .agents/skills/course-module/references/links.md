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
- url: https://www.lumni.fr/video/la-loi-dohm
  comment: 'Lumni, cours vidéo de collège (3e, 30 min) : …'
  language_note: 🇫🇷 uniquement
---
```

- Keys: `url`, `comment`, `language_note`. `language_note` is required by
  the validator for YouTube, Vimeo and Dailymotion, and by this skill for
  **any** video (Lumni included): « 🇫🇷 uniquement », « sous-titres DE
  disponibles »…
- The comment says what the page is and what the kid will do there, and
  the level when it's a school resource (« 5e », « 3e »).
- 5–9 links. Interactive first (simulations), then pages written for young
  readers, then videos, then something deeper for the curious.

## Sources that worked for module A

- **PhET**, French versions: `https://phet.colorado.edu/fr/simulations/<slug>`
- **Vikidia** (encyclopedia for 8–13 year olds): `https://fr.vikidia.org/wiki/<Titre>`
- **Lumni** (France Télévisions, school videos): `https://www.lumni.fr/video/<slug>`
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
A school video may be geo-restricted: say so in the report if you could not
confirm it plays.
