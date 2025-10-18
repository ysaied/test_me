FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY entrypoint.sh ./entrypoint.sh
COPY scripts/ ./scripts/
COPY urls/ ./urls/

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "scripts/runner.py"]
