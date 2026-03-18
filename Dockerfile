# ============================================================
# Dockerfile – python-openai article generator
# ============================================================
# Construir:
#   docker build -t article-generator:latest .
#
# Ejecutar (pasando variables de entorno desde un fichero .env):
#   docker run --rm --env-file .env article-generator:latest \
#     --tag "@Data" --category "Spring Boot" --subcategory "Lombok"
#
# Ejecutar pasando cada variable individualmente:
#   docker run --rm \
#     -e OPENAIAPIKEY=... \
#     -e OPENAI_MODEL=gpt-4o \
#     -e SITE=https://tusitio.com \
#     article-generator:latest \
#     --tag "@Data" --category "Spring Boot" --subcategory "Lombok"
#
# Nota: --tag es obligatorio. El artículo se guarda en article.json
#       dentro del contenedor. Monta un volumen para conservarlo:
#   docker run --rm --env-file .env -v $(pwd)/output:/app/output \
#     article-generator:latest \
#     --tag "@Data" --output /app/output/article.json
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
# Pasa el tema a generar mediante argumentos CLI: --tag (requerido),
# --category, --subcategory, --output, --language, etc.
ENTRYPOINT ["python", "generateArticle.py"]
