FROM python:3.12-slim
WORKDIR /app
# Install system deps for Presidio NER models and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev --frozen
COPY src/ ./src/
COPY config/ ./config/
COPY params.yaml ./
ENV PYTHONPATH=/app/src
ENV APP_ENV=production
# Pre-download Presidio NER models (avoids runtime download)
RUN python -c "from presidio_analyzer import AnalyzerEngine; AnalyzerEngine()"
# Pre-download HuggingFace embedding model specified in params.yaml
# (parametrise via build-arg)
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"
EXPOSE 8000
CMD ["uvicorn", "aegisVault.app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]