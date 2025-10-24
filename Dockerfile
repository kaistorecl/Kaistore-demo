FROM python:3.11-slim
WORKDIR /app

# Dependencias
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Código (archivos .py en la raíz + carpeta routers/)
COPY . /app

# Render usa $PORT. Elegimos 10000 por compatibilidad
ENV PORT=10000
EXPOSE 10000

# Inicia FastAPI (main.py está en la raíz del repo)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
