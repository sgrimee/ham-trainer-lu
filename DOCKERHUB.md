# examen-ilr

A self-hosted web trainer for the Luxembourg **ILR amateur-radio exam**
(BASE, NOVICE, HAREC). It covers all 509 questions of the February 2024
catalogue in French and German, with the formula appendix, a from-zero course
for learners, practice and mock exams, and optional LLM grading of the
open-ended questions.

Source, specs and issues: <https://github.com/sgrimee/ham-trainer-lu>.
This project is not affiliated with or endorsed by the
[ILR](https://www.ilr.lu). The exam content is the ILR's own published
material, reproduced for non-commercial study with the source credited.

## Quick start

```sh
docker run -d --name examen-ilr \
  -p 8000:8000 \
  -v examen-data:/var/lib/examen \
  sgrimee/examen-ilr
```

Then open <http://localhost:8000>. The app needs no configuration to run.
Without an LLM key, open-ended questions show the reference answer and you mark
yourself right or wrong.

## Tags

| Tag       | Contents                                          |
|-----------|---------------------------------------------------|
| `latest`  | the current `main` branch, rebuilt on every push  |
| `<sha>`   | a specific commit (short git sha), for pinning     |

Images are built for `linux/amd64` and `linux/arm64`.

## Environment variables

All are optional.

| Variable              | Default                        | Purpose |
|-----------------------|--------------------------------|---------|
| `LLM_BASE_URL`        | —                              | OpenAI-compatible API base URL, e.g. `https://inference-api.nousresearch.com/v1` or `https://api.openai.com/v1` |
| `LLM_MODEL`           | —                              | Model name at that endpoint, e.g. `openai/gpt-5.1`. It must support structured outputs. |
| `LLM_API_KEY`         | —                              | API key for the endpoint |
| `LLM_API_KEY_FILE`    | —                              | Path to a file holding the key; takes precedence over `LLM_API_KEY` (use with Docker/Compose secrets) |
| `LLM_TIMEOUT_S`       | `30`                           | Per-request grading timeout, in seconds |
| `ADMIN_PASSWORD`      | —                              | Enables the unlinked `/admin/learners` page for managing course learners. If unset, `/admin` returns 404. |
| `ADMIN_PASSWORD_FILE` | —                              | Path to a file holding the admin password; preferred over `ADMIN_PASSWORD` |
| `COURSE_DE`           | `off`                          | German version of the course: `off`, `preview` (modules that are already translated) or `on` (the full German course; the app refuses to start if any translation is missing) |
| `ATTEMPTS_DB`         | `/var/lib/examen/attempts.db`  | SQLite database with attempts, learners and progress. Leave the default so the data stays in the volume. |

LLM grading is enabled only when `LLM_BASE_URL`, `LLM_MODEL` and a key are all
set. Otherwise the app falls back to self-grading.

## Data and volumes

All state is in one SQLite file under **`/var/lib/examen`**. Mount a volume or
host directory there, or the data is lost when the container is removed. The
container runs as the unprivileged user `examen`. A bind-mounted host directory
must be writable by that user, so a named volume is the simplest option.

## Examples

With LLM grading and the admin page enabled:

```sh
docker run -d --name examen-ilr \
  -p 8000:8000 \
  -v examen-data:/var/lib/examen \
  -e LLM_BASE_URL=https://inference-api.nousresearch.com/v1 \
  -e LLM_MODEL=openai/gpt-5.1 \
  -e LLM_API_KEY=sk-... \
  -e ADMIN_PASSWORD=change-me \
  -e COURSE_DE=preview \
  sgrimee/examen-ilr
```

Using an env file instead of passing each `-e` flag:

```sh
docker run -d --name examen-ilr -p 8000:8000 \
  -v examen-data:/var/lib/examen --env-file examen.env sgrimee/examen-ilr
```

Managing course learners from the command line (no admin password needed):

```sh
docker exec examen-ilr python -m app.learners list
docker exec examen-ilr python -m app.learners add "Léa"
docker exec examen-ilr python -m app.learners delete "Léa"   # also deletes their progress, without asking
```

Updating to the latest image. Your data stays in the volume:

```sh
docker pull sgrimee/examen-ilr
docker rm -f examen-ilr
docker run -d --name examen-ilr -p 8000:8000 -v examen-data:/var/lib/examen sgrimee/examen-ilr
```

### Docker Compose, with secrets

```yaml
services:
  examen:
    image: sgrimee/examen-ilr:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      LLM_BASE_URL: https://inference-api.nousresearch.com/v1
      LLM_MODEL: openai/gpt-5.1
      LLM_API_KEY_FILE: /run/secrets/llm_api_key
      ADMIN_PASSWORD_FILE: /run/secrets/admin_password
      COURSE_DE: preview
    secrets:
      - llm_api_key
      - admin_password
    volumes:
      - examen-data:/var/lib/examen

secrets:
  llm_api_key:
    file: ./secrets/llm_api_key.txt
  admin_password:
    file: ./secrets/admin_password.txt

volumes:
  examen-data:
```

## Health and reverse proxy

The app listens on port **8000**. `GET /healthz` is the health endpoint, and the
image has a built-in `HEALTHCHECK` that uses it. The app does not handle TLS,
so put it behind a reverse proxy (Caddy, Traefik, nginx) if you expose it
publicly.

## Disclaimer

Provided "as is", with no guarantee of accuracy. This is not an official study
tool. Always check against the ILR's own published documents before an exam.
The code is MIT-licensed. The exam content is the ILR's and is not covered by
that license.
