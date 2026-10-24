FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

RUN useradd --create-home appuser
USER appuser

# Render injects PORT; default to 8000 for local runs.
CMD ["sh", "-c", "uvicorn fixwithme_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
