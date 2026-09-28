# One image, one port: FastAPI serves the API and the built React app.

# ---- Stage 1: build the React frontend (thrown away after the build) ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static \
    SEED_DEMO_DATA=true

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Run as an unprivileged user; /data holds the SQLite file and the JWT secret.
RUN useradd --create-home --uid 10001 dogfood \
 && mkdir -p /data \
 && chown dogfood:dogfood /data

COPY --chown=dogfood:dogfood backend/ ./
COPY --from=frontend --chown=dogfood:dogfood /frontend/dist ./static

USER dogfood
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
