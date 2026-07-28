FROM python:3.12-slim

WORKDIR /eris

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ portaudio19-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080 8765 8888

HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]
