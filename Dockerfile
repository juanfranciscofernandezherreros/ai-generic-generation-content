# ============================================================
# Dockerfile – python-openai article generator
# ============================================================
# Construir:
#   docker build -t article-generator:latest .
#
# Ejecutar (pasando variables de entorno desde un fichero .env):
#   docker run --rm --env-file .env article-generator:latest
#
# Ejecutar pasando cada variable individualmente:
#   docker run --rm \
#     -e MONGODB_URI=... \
#     -e DB_NAME=blogdb \
#     -e OPENAIAPIKEY=... \
#     article-generator:latest
# ============================================================

FROM python:3.12-slim

# Evitar ficheros .pyc y forzar salida sin buffer (útil para logs en Docker/K8s)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias primero (capa cacheada mientras no cambie requirements.txt)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY generateArticle.py ./
COPY seed_data.py ./

# El contenedor ejecuta el generador de artículos como tarea de un solo uso.
# Para sembrar datos iniciales en Mongo utiliza:
#   docker run --rm --env-file .env article-generator:latest python seed_data.py
CMD ["python", "generateArticle.py"]
