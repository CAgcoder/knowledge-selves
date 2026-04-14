FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/Python_Agent/data/huggingface \
    TORCH_HOME=/app/Python_Agent/data/torch \
    XDG_CACHE_HOME=/app/Python_Agent/data/cache

WORKDIR /app/Python_Agent

RUN mkdir -p /app/Python_Agent/data /app/Obsidian_Vault

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY Python_Agent/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY Python_Agent/ ./

HEALTHCHECK --interval=30s --timeout=5s --start-period=10m --retries=3 \
    CMD ["python", "healthcheck.py"]

CMD ["python", "main.py"]
