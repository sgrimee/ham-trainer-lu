# The application and data/, nothing else (specs/APP.md §11.2). extract/ and
# its PyMuPDF dependency never ship -- the image serves data/, it doesn't
# rebuild it. reference/ does ship despite what that section says: the
# question-to-guide links (app/templates/_feedback.html) serve those PDFs
# straight from disk at /reference/<filename>, a feature added after §11.2
# was written.

FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups


FROM python:3.13-slim

RUN groupadd --system examen && useradd --system --gid examen --home-dir /app examen

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY app/ app/
COPY data/ data/
COPY reference/documents.yaml reference/
COPY reference/*.pdf reference/

ENV PATH="/app/.venv/bin:${PATH}" \
    ATTEMPTS_DB=/var/lib/examen/attempts.db

# The only writable state (specs/APP.md §5.1); owned by the user that runs
# the process, which is what reliably breaks on first deploy otherwise.
RUN mkdir -p /var/lib/examen && chown examen:examen /var/lib/examen
VOLUME /var/lib/examen

EXPOSE 8000
USER examen

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
