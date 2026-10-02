# ERIS AI — Dockerfile para despliegue en contenedor

# Build stage: instala dependencias Python
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar deps del sistema (para compilar paquetes Python nativos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libasound2-dev \
    libpulse-dev \
    libdbus-1-dev \
    libxcb1-dev \
    libxkbcommon-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar Python deps
COPY requirements-linux.txt .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements-linux.txt \
    && pip install --no-cache-dir -r requirements.txt \
    || true

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Deps del sistema en runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    libpulse-dev \
    libdbus-1-dev \
    libxcb1-dev \
    libxkbcommon-dev \
    libgl1 \
    libdbus-1-3 \
    libxcb1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar el venv desde el builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código de ERIS
COPY . /app/

# Permisos
RUN chmod +x /app/run_eris.sh \
    && mkdir -p /app/data /app/memory /app/eris_workspace \
    && chmod 777 /app/data /app/memory /app/eris_workspace

# Variables de entorno
ENV PYTHONIOENCODING=utf-8
ENV QT_QPA_PLATFORM=offscreen
ENV ERIS_WORKSPACE=/app/eris_workspace
ENV ERIS_OBSIDIAN_VAULT=/app/obsidian_vault

# Puerto para servidor web (Flask)
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

# Entrypoint
ENTRYPOINT ["/app/run_eris.sh"]
# CMD por defecto: ejecutar ERIS en modo CLI
CMD ["--cli"]
