FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SWIFTFILEZ_WORKERS=4 \
    SWIFTFILEZ_QUARANTINE_DIR=/workspace/.swiftfilez-quarantine

WORKDIR /app

COPY pyproject.toml README.md ./
COPY swift_files ./swift_files
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 swiftfilez \
    && mkdir -p /workspace \
    && chown -R swiftfilez:swiftfilez /workspace

USER swiftfilez
WORKDIR /workspace

ENTRYPOINT ["swf"]
CMD ["--help"]
