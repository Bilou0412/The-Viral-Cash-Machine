# VCM Studio — image unique : FastAPI (API) + front React buildé + rendu Remotion.

# ---- Stage 1 : build du front React (Vite) ----
FROM node:22-slim AS frontend
WORKDIR /front
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /front/dist

# ---- Stage 2 : build du package Node Remotion (render/) ----
FROM node:22-slim AS render
WORKDIR /render
COPY render/package.json render/package-lock.json* ./
RUN npm ci
COPY render/ ./
RUN npm run build && npm prune --omit=dev   # -> /render/dist + node_modules de prod

# ---- Stage 3 : runtime Python (API + statique + montage + rendu Remotion) ----
FROM python:3.11-slim
# ffmpeg : montage MoviePy ; libgl/glib : Pillow/OpenCV ;
# nodejs : exécute le CLI Remotion ; chromium : moteur de rendu headless Remotion
# (apt tire ses dépendances) ; fonts-liberation : rendu texte.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
        nodejs chromium fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# le front buildé, servi par FastAPI (cf. app.py : mount si frontend/dist existe)
COPY --from=frontend /front/dist ./frontend/dist
# le package Node Remotion buildé + ses deps de prod (rendu MP4 server-side)
COPY --from=render /render/dist ./render/dist
COPY --from=render /render/node_modules ./render/node_modules
COPY --from=render /render/package.json ./render/package.json

ENV PYTHONPATH=/app:/app/src \
    VCM_OUTPUT_DIR=/data/studio_output \
    VCM_STUDIO_DB=sqlite:////data/studio.db \
    REMOTION_CHROME_EXECUTABLE=/usr/bin/chromium \
    VCM_RENDER_BASE=http://localhost:8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/projects')" || exit 1

CMD ["python", "-m", "uvicorn", "src.studio.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
