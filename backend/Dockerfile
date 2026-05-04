FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for whois / pdf / lxml / Surya OCR (Pillow + OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    whois \
    libxml2-dev \
    libxslt1-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip && pip install -e .

# Surya OCR is optional and heavy (~3GB with PyTorch). Install behind a flag
# so users who don't need PDF OCR can build a lighter image.
ARG INSTALL_SURYA=true
RUN if [ "$INSTALL_SURYA" = "true" ]; then \
        pip install "surya-ocr>=0.6.0" "torch>=2.1.0" --extra-index-url https://download.pytorch.org/whl/cpu ; \
    fi

# NLLB-200 distilled 600M for Indonesian translation. ~1.2GB int8 model.
# Disable with --build-arg INSTALL_NLLB=false to skip the download.
# Pass --build-arg HF_TOKEN=hf_xxx for authenticated downloads (faster, no rate limit).
ARG INSTALL_NLLB=true
ARG HF_TOKEN=
ENV HF_HOME=/app/data/nllb_hf
RUN if [ "$INSTALL_NLLB" = "true" ]; then \
        pip install "ctranslate2>=4.4.0" "sentencepiece>=0.2.0" "huggingface-hub>=0.25.0" "transformers>=4.45.0" && \
        mkdir -p /app/data/nllb_hf /app/data/nllb_ct2 && \
        HF_TOKEN=$HF_TOKEN HUGGING_FACE_HUB_TOKEN=$HF_TOKEN python -c "from huggingface_hub import snapshot_download; snapshot_download('facebook/nllb-200-distilled-600M', cache_dir='/app/data/nllb_hf', local_dir='/app/data/nllb_hf/snapshot')" && \
        ct2-transformers-converter \
            --model /app/data/nllb_hf/snapshot \
            --output_dir /app/data/nllb_ct2 \
            --quantization int8 \
            --copy_files tokenizer.json tokenizer_config.json sentencepiece.bpe.model special_tokens_map.json \
            --force ; \
    fi

RUN python -m playwright install chromium && python -m playwright install-deps chromium

# Crawl4AI post-install: warms up its browser bridge cache. Idempotent.
RUN crawl4ai-setup || true

RUN mkdir -p /app/data /app/logs

ENV DATA_DIR=/app/data \
    LOG_DIR=/app/logs \
    CONFIG_DIR=/app/config

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8080/metrics > /dev/null || exit 1

CMD ["crawl", "schedule", "--metrics-port", "8080"]
