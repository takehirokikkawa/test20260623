FROM python:3.12-slim

# System deps: libpq for psycopg2, build tools for any wheels that need them.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TORCH_HOME=/opt/torch-cache

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
# Install CPU-only torch to keep the image small and avoid CUDA downloads.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 \
    && pip install -r requirements.txt

# Bake the embedding model into the image so runtime needs NO network / API key.
ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["serve"]
