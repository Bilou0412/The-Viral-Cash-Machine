# VCM Studio — image unique : FastAPI (API) + front React buildé, servis ensemble.

# ---- Stage 1 : build du front React (Vite) ----
FROM node:22-slim AS frontend
WORKDIR /front
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /front/dist

# ---- Stage 2 : runtime Python (API + statique + montage) ----
FROM python:3.11-slim
# ffmpeg : montage MoviePy ; libgl/glib : Pillow/OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# le front buildé, servi par FastAPI (cf. app.py : mount si frontend/dist existe)
COPY --from=frontend /front/dist ./frontend/dist

ENV PYTHONPATH=/app:/app/src \
    VCM_OUTPUT_DIR=/data/studio_output \
    VCM_STUDIO_DB=sqlite:////data/studio.db
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/projects')" || exit 1

CMD ["python", "-m", "uvicorn", "src.studio.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
