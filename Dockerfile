# Etapa 1: construir el frontend si existe
FROM node:18-slim AS frontend
WORKDIR /src
COPY frontend/ ./frontend
WORKDIR /src/frontend
RUN npm install && npm run build || echo "No frontend folder, skipping"

# Etapa 2: backend con FastAPI
FROM python:3.11-slim AS backend
WORKDIR /app

# Copiamos solo la carpeta app y los archivos raíz necesarios
COPY app ./app
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copiamos frontend compilado si existe
COPY --from=frontend /src/frontend/out /app/app/static

# Variables de entorno
ENV CURRENCY=CLP
ENV LOCALE=es-CL
ENV PORT=8000

EXPOSE 8000

# Ejecutamos FastAPI apuntando al módulo "app.main"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
