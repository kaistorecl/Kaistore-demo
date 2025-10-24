# Etapa 1: construir el frontend (si tienes carpeta /frontend)
FROM node:18-slim AS frontend
WORKDIR /src
COPY frontend/ ./frontend
WORKDIR /src/frontend
RUN npm install && npm run build || echo "No frontend folder, skipping"

# Etapa 2: backend Python con FastAPI
FROM python:3.11-slim AS backend
WORKDIR /app

# Copiar backend (los .py que tienes en raíz)
COPY . /app

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar frontend compilado (si existe)
COPY --from=frontend /src/frontend/out /app/static

# Variables de entorno
ENV CURRENCY=CLP
ENV LOCALE=es-CL
ENV PORT=8000

# Exponer puerto
EXPOSE 8000

# Comando de inicio FastAPI
CMD ["python", "-m", "main"]
