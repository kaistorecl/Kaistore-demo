# Multi-stage build: build Next.js, then run FastAPI and serve Next export
FROM node:18-slim AS frontend
WORKDIR /src
COPY frontend ./frontend
WORKDIR /src/frontend
RUN npm install && npm run build

FROM python:3.11-slim AS backend
WORKDIR /app
COPY app ./app
RUN pip install --no-cache-dir -r app/requirements.txt
# Copy static export from Next
COPY --from=frontend /src/frontend/out ./static
# Default envs
ENV CURRENCY=CLP LOCALE=es-CL
# Expose port for Render (uses $PORT)
ENV PORT=10000
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
