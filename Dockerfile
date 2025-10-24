FROM python:3.11-slim
WORKDIR /app

# Dependencias
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Código
COPY . /app

# Puerto que usa Render (variable $PORT)
ENV PORT=10000
EXPOSE 10000

# Inicia FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
