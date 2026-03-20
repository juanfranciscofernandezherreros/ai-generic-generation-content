# Publicación automática semanal con IA — Optimizado para SEO

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)
![LangChain](https://img.shields.io/badge/LangChain-LCEL-purple)

Generador **CLI** de artículos técnicos SEO con salida a **JSON local** (sin base de datos), usando **LangChain** (LCEL) con soporte para **OpenAI GPT / Google Gemini / Ollama**. Optimizado para **SEO on-page**, con datos estructurados **Schema.org**, metadatos **Open Graph** y gestión completa de **categorías**, **subcategorías** y **tags**.

> **Última actualización:** 2026-03-20

---

## 📑 Índice

- [🚀 Guía rápida de ejecución](#-guía-rápida-de-ejecución)
- [🤖 Proveedores de IA](#-proveedores-de-ia)
- [🐳 Despliegue con Docker](#-despliegue-con-docker)
- [☸️ Despliegue en Kubernetes](#️-despliegue-en-kubernetes)
- [☁️ Despliegue en Google Cloud (GCloud)](#️-despliegue-en-google-cloud-gcloud)
- [📂 Estructura del proyecto](#-estructura-del-proyecto)
- [📰 ¿Qué es este script?](#-qué-es-este-script)
- [🏗️ Diagrama de arquitectura](#️-diagrama-de-arquitectura)
- [🔍 Funcionalidades SEO](#-funcionalidades-seo)
- [⚙️ ¿Qué necesita para funcionar?](#️-qué-necesita-para-funcionar)
- [🧩 Cómo organiza los temas: Categorías, Subcategorías y Tags](#-cómo-organiza-los-temas-categorías-subcategorías-y-tags)
- [🧠 Qué hace paso a paso](#-qué-hace-paso-a-paso)
- [📄 Documento del artículo generado (campos SEO)](#-documento-del-artículo-generado-campos-seo)
- [📤 Ejemplo de output generado](#-ejemplo-de-output-generado)
- [📸 Screenshots](#-screenshots)
- [📨 Tipos de notificaciones que envía](#-tipos-de-notificaciones-que-envía)
- [🕐 Frecuencia de publicación](#-frecuencia-de-publicación)
- [🔒 Seguridad y privacidad](#-seguridad-y-privacidad)
- [⚙️ Constantes y configuración interna](#️-constantes-y-configuración-interna)
- [🛠️ Calidad de código](#️-calidad-de-código)
- [🧾 En resumen](#-en-resumen)
- [🌟 Ejemplo de funcionamiento real](#-ejemplo-de-funcionamiento-real)
- [🤝 Contribuir](#-contribuir)

---

## 🚀 Guía rápida de ejecución

### Requisitos previos

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| **Python** | 3.10+ | Ejecutar el script |
| **Clave OpenAI**, **Gemini** o **Ollama** | — | Generar artículos con IA (al menos un proveedor) |
| **Docker** y **Docker Compose** | Docker 20+ | Ejecutar el generador en contenedor (opcional) |

> **No se requiere MongoDB.** El artículo generado se exporta directamente a un fichero JSON local.

### 1. Clonar el repositorio

```bash
git clone https://github.com/juanfranciscofernandezherreros/python-article.git
cd python-article
```

### 2. Configurar las variables de entorno

Copia el fichero de ejemplo y edita los valores:

```bash
cp .env.example .env
```

Abre `.env` con tu editor y configura el proveedor de IA que quieras usar (ver sección [🤖 Proveedores de IA](#-proveedores-de-ia) para ejemplos completos):

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `OPENAI_MODEL` | ✅ | `gpt-4o` | Modelo de IA a usar. Determina el proveedor: modelos `gpt-*` → OpenAI; modelos `gemini-*` → Google Gemini; cualquier modelo cuando `OLLAMA_BASE_URL` está definida → Ollama. |
| `OPENAIAPIKEY` | ✅ si usas OpenAI | — | Clave de API de OpenAI (`sk-...`). [Crear API key](https://platform.openai.com/api-keys). No requerida con Gemini ni con Ollama. |
| `GEMINI_API_KEY` | ✅ si usas Gemini | — | Clave de API de Google Gemini. [Obtener clave](https://aistudio.google.com/app/apikey). Necesaria cuando `OPENAI_MODEL` es un modelo `gemini-*`. |
| `OLLAMA_BASE_URL` | ✅ si usas Ollama | — | URL base del servidor Ollama local (ej. `http://localhost:11434/v1`). Sin coste ni clave de API. |
| `SITE` | ⚠️ recomendada | `""` | URL base de tu web **sin barra final** (ej. `https://tusitio.com`). Imprescindible para generar `canonicalUrl` y JSON-LD correctos. |
| `AUTHOR_USERNAME` | ⚠️ recomendada | `adminUser` | Username o nombre del autor del artículo generado. |
| `ARTICLE_LANGUAGE` | ⚠️ recomendada | `es` | Código ISO 639-1 del idioma. Valores: `es` `en` `fr` `de` `it` `pt` `nl` `pl` `ru` `zh` `ja` `ar`. |
| `AI_TEMPERATURE_ARTICLE` | ❌ opcional | `0.7` | Creatividad del artículo (0.0 = determinista, 1.0 = muy creativo). |
| `AI_TEMPERATURE_TITLE` | ❌ opcional | `0.9` | Creatividad del título (valor más alto → títulos más variados). |
| `SMTP_HOST` | ❌ opcional | — | Servidor SMTP para notificaciones (ej. `smtp.gmail.com`). |
| `SMTP_PORT` | ❌ opcional | `587` | Puerto SMTP. Habituales: `587` (STARTTLS), `465` (SSL). |
| `SMTP_USER` | ❌ opcional | — | Usuario SMTP / dirección de correo del remitente. |
| `SMTP_PASS` | ❌ opcional | — | Contraseña SMTP. Para Gmail, usa una [contraseña de aplicación](https://myaccount.google.com/apppasswords). |
| `FROM_EMAIL` | ❌ opcional | valor de `SMTP_USER` | Dirección de origen del email de notificación. |
| `NOTIFY_EMAIL` | ❌ opcional | — | Dirección de destino de las notificaciones. |
| `NOTIFY_VERBOSE` | ❌ opcional | `true` | Enviar emails detallados (`true`/`false`). |
| `SEND_PROMPT_EMAIL` | ❌ opcional | `false` | Enviar el prompt por email antes de llamar a la IA (útil para depuración). |

### 3. Crear el entorno virtual e instalar dependencias

Crea el entorno virtual (`.venv`):

```bash
python3 -m venv .venv
```

Actívalo:

```bash
source .venv/bin/activate
```

> Verás que ahora tu terminal muestra `(.venv)` al principio de la línea.

Instala las dependencias:

```bash
pip install -r requirements.txt
```

### 4. Ejecutar el script principal

El script requiere el argumento `--tag` (tema del artículo). El resto son opcionales:

```bash
python3 generateArticle.py \
  --tag "JWT Authentication" \
  --category "Spring Boot" \
  --subcategory "Spring Security" \
  --output article.json \
  --language es
```

#### Argumentos CLI disponibles

| Argumento | Obligatorio | Descripción | Por defecto |
|---|---|---|---|
| `--tag` / `-t` | ✅ | Tema o tag del artículo | — |
| `--category` / `-c` | ❌ | Nombre de la categoría padre | `General` |
| `--subcategory` / `-s` | ❌ | Nombre de la subcategoría | `General` |
| `--output` / `-o` | ❌ | Ruta del fichero JSON de salida | `article.json` |
| `--username` / `--author` / `-u` / `-a` | ❌ | Username/nombre del autor | valor de `AUTHOR_USERNAME` |
| `--site` / `-S` | ❌ | URL base del sitio para URLs canónicas | valor de `SITE` |
| `--language` / `-l` | ❌ | Código de idioma ISO 639-1 (`es`, `en`, `fr`…) | valor de `ARTICLE_LANGUAGE` |
| `--avoid-titles` | ❌ | Títulos a evitar (separados por `;`). El script compara el nuevo título con esta lista y regenera si la similitud supera el umbral 0.86 | `""` |

El script:
1. Valida la configuración (clave de API disponible).
2. Genera el artículo con IA (OpenAI o Google Gemini, optimizado para SEO).
3. Genera metadatos SEO: `metaTitle`, `metaDescription`, `canonicalUrl`, datos estructurados JSON-LD y Open Graph.
4. Guarda el documento completo en el fichero JSON indicado por `--output`.
5. Notifica el resultado por correo (si hay SMTP configurado).

### 5. Ejecutar los tests

```bash
pip install pytest
python -m pytest test_generateArticle.py test_seed_data.py -v
```

---

## 🤖 Proveedores de IA

El script soporta **tres proveedores de IA** que se seleccionan automáticamente mediante las variables de entorno. Solo necesitas configurar el proveedor que vayas a usar.

### Comparativa de proveedores

| Proveedor | Variable clave | Clave de API | Coste | Privacidad | Modelos destacados |
|---|---|---|---|---|---|
| **OpenAI (GPT)** | `OPENAIAPIKEY` | Sí (`sk-...`) | De pago por uso | Cloud | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| **Google Gemini** | `GEMINI_API_KEY` | Sí (`AIzaSy-...`) | Nivel gratuito disponible | Cloud | `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash` |
| **Ollama (local)** | `OLLAMA_BASE_URL` | No necesaria | Gratuito (local) | 100% local | `llama3`, `mistral`, `codellama`, `gemma`, `phi3` |

---

### Opción A — OpenAI (GPT)

1. Obtén tu clave en [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Configura en tu `.env`:

```dotenv
OPENAI_MODEL=gpt-4o
OPENAIAPIKEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Modelos disponibles: `gpt-4o` (recomendado) · `gpt-4-turbo` · `gpt-3.5-turbo`

---

### Opción B — Google Gemini

1. Obtén tu clave en [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (tiene nivel gratuito).
2. Configura en tu `.env`:

```dotenv
OPENAI_MODEL=gemini-2.0-flash
GEMINI_API_KEY=AIzaSy-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Modelos disponibles: `gemini-2.0-flash` (rápido y gratuito) · `gemini-1.5-pro` · `gemini-1.5-flash`

> **Nota:** `OPENAIAPIKEY` no se necesita cuando usas Gemini.

---

### Opción C — Ollama (LLM local, sin coste ni internet)

Ollama te permite correr modelos de lenguaje completamente en tu máquina, sin enviar datos a ningún servidor externo y sin coste adicional.

1. Instala Ollama desde [ollama.com](https://ollama.com).
2. Descarga el modelo que quieras usar (solo la primera vez):

```bash
ollama pull llama3       # ~4 GB — recomendado para la mayoría de casos
# ollama pull mistral    # alternativa más ligera
# ollama pull codellama  # especializado en código
# ollama pull gemma      # de Google, muy eficiente
# ollama pull phi3       # de Microsoft, muy ligero
```

3. Configura en tu `.env`:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3
```

> **Nota:** `OPENAIAPIKEY` y `GEMINI_API_KEY` **no se necesitan** con Ollama.

4. Ejecuta el script normalmente:

```bash
python generateArticle.py --tag "JWT Authentication" --category "Spring Boot"
```

---

## 🐳 Despliegue con Docker

### Construir la imagen

```bash
docker build -t article-generator:latest .
```

### Ejecutar pasando el fichero `.env`

El modo más sencillo: todas las variables del `.env` se inyectan en el contenedor con `--env-file`. Pasa el tema a generar como argumentos al final:

```bash
docker run --rm --env-file .env article-generator:latest \
  --tag "JWT Authentication" \
  --category "Spring Boot" \
  --subcategory "Spring Security"
```

El artículo se guarda en `article.json` dentro del contenedor. Para conservarlo en el host, monta un volumen:

```bash
docker run --rm --env-file .env \
  -v $(pwd)/output:/app/output \
  article-generator:latest \
  --tag "JWT Authentication" --output /app/output/article.json
```

### Ejecutar con variables individuales (`-e`)

Útil en CI/CD o cuando las credenciales vienen de un gestor de secretos:

```bash
docker run --rm \
  -e OPENAIAPIKEY="sk-XXXXXXXXXXXXXXXXXXXX" \
  -e OPENAI_MODEL=gpt-4o \
  -e GEMINI_API_KEY="AIzaSy-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" \
  -e SITE="https://tusitio.com" \
  -e AUTHOR_USERNAME=adminUser \
  -e SMTP_HOST=smtp.gmail.com \
  -e SMTP_PORT=587 \
  -e SMTP_USER="tu_correo@gmail.com" \
  -e SMTP_PASS="tu_contraseña_de_aplicacion" \
  -e FROM_EMAIL="tu_correo@gmail.com" \
  -e NOTIFY_EMAIL="tu_correo@gmail.com" \
  -e NOTIFY_VERBOSE=true \
  -e ARTICLE_LANGUAGE=es \
  -e AI_TEMPERATURE_ARTICLE=0.7 \
  -e AI_TEMPERATURE_TITLE=0.9 \
  article-generator:latest \
  --tag "@Data" --category "Spring Boot" --subcategory "Lombok"
```

### Usar Docker Compose

```bash
# Ejecutar el generador de artículos con argumentos CLI
docker compose run --rm app --tag "@Data" --category "Spring Boot" --subcategory "Lombok"
```

### Usar con Ollama (LLM local)

Para usar un modelo local con [Ollama](https://ollama.com), instala y arranca Ollama en tu máquina y luego ejecuta:

```bash
# 1. Instalar Ollama y descargar un modelo (solo la primera vez)
# Visita https://ollama.com para la instalación
ollama pull llama3

# 2. Ejecutar el generador con Ollama
OLLAMA_BASE_URL=http://localhost:11434/v1 OPENAI_MODEL=llama3 \
  python generateArticle.py --tag "JWT Authentication" --category "Spring Boot" --subcategory "Spring Security"
```

Con Docker, usa `--network host` (Linux) o `host.docker.internal` (macOS/Windows) para acceder al servidor Ollama del host:

```bash
# Linux: --network host para acceder a localhost del host
docker run --rm --network host \
  -e OLLAMA_BASE_URL="http://localhost:11434/v1" \
  -e OPENAI_MODEL=llama3 \
  article-generator:latest \
  --tag "JWT Authentication" --category "Spring Boot" --subcategory "Spring Security"

# macOS / Windows: usar host.docker.internal
docker run --rm \
  -e OLLAMA_BASE_URL="http://host.docker.internal:11434/v1" \
  -e OPENAI_MODEL=llama3 \
  article-generator:latest \
  --tag "JWT Authentication" --category "Spring Boot" --subcategory "Spring Security"
```

---

## ☸️ Despliegue en Kubernetes

El directorio `k8s/` contiene los manifiestos necesarios para ejecutar el generador como un **CronJob semanal** en Kubernetes.

```
k8s/
├── configmap.yaml   # Variables no sensibles (SMTP_HOST, SITE, etc.)
├── secret.yaml      # Plantilla para variables sensibles (OPENAIAPIKEY, GEMINI_API_KEY…)
└── cronjob.yaml     # CronJob – se ejecuta cada lunes a las 08:00 (Europe/Madrid)
```

> **Nota:** Edita el campo `command` en `k8s/cronjob.yaml` para configurar el tema (`--tag`, `--category`, `--subcategory`) que el CronJob generará en cada ejecución.

### Paso 1 – Publicar la imagen en un registry

```bash
# Ejemplo con Docker Hub
docker tag article-generator:latest <tu-usuario>/article-generator:latest
docker push <tu-usuario>/article-generator:latest
```

Actualiza el campo `image:` en `k8s/cronjob.yaml` con la ruta completa de tu registry.

### Paso 2 – Configurar el ConfigMap

Edita `k8s/configmap.yaml` con los valores adecuados para tu entorno y aplícalo:

```bash
kubectl apply -f k8s/configmap.yaml
```

### Paso 3 – Configurar el Secret

Codifica cada valor sensible en base64 y rellena `k8s/secret.yaml` (o crea `k8s/secret.local.yaml`, que ya está en `.gitignore`, para no modificar la plantilla):

```bash
# Generar los valores codificados
echo -n "sk-XXXX"          | base64  # OPENAIAPIKEY (OpenAI)
echo -n "AIzaSy-XXXX"      | base64  # GEMINI_API_KEY (Google Gemini, si aplica)
echo -n "correo@gmail.com" | base64
echo -n "contraseña_app"   | base64
```

Rellena `k8s/secret.yaml` (o `secret.local.yaml`) con los valores y aplícalo:

```bash
kubectl apply -f k8s/secret.yaml   # o secret.local.yaml
```

### Paso 4 – Aplicar el CronJob

```bash
kubectl apply -f k8s/cronjob.yaml
```

Comprueba que se ha creado:

```bash
kubectl get cronjob article-generator
```

### Ejecutar el CronJob manualmente

```bash
kubectl create job article-generator-manual \
  --from=cronjob/article-generator
```

Consulta los logs:

```bash
kubectl logs -l app=article-generator --tail=100
```

### Limpiar todos los recursos

```bash
kubectl delete -f k8s/
```

---

## ☁️ Despliegue en Google Cloud (GCloud)

Sí, **también funciona en Google Cloud**. El directorio `gcloud/` contiene los ficheros necesarios para dos estrategias:

```
gcloud/
├── cloudbuild.yaml      # Cloud Build – construye y sube la imagen a Artifact Registry
└── cloud-run-job.yaml   # Cloud Run Job – ejecuta el generador sin necesidad de un clúster K8s
```

Puedes elegir entre:

| Estrategia | Cuándo usarla |
|---|---|
| **GKE** (Google Kubernetes Engine) | Ya tienes un clúster K8s en GCP — usa directamente los manifiestos de `k8s/` |
| **Cloud Run Jobs** | Quieres una solución serverless sin gestionar clústeres |

---

### Opción A – GKE (usar los manifiestos `k8s/` existentes)

GKE es Kubernetes gestionado por Google, por lo que los manifiestos de `k8s/` funcionan sin cambios.

#### 1. Autenticarse y configurar kubectl

```bash
gcloud auth login
gcloud container clusters get-credentials <NOMBRE_CLUSTER> \
  --region=<REGION> --project=<PROJECT_ID>
```

#### 2. Publicar la imagen en Artifact Registry

```bash
# Configurar Docker para autenticarse con Artifact Registry
gcloud auth configure-docker <REGION>-docker.pkg.dev

# Construir y subir la imagen
docker build -t <REGION>-docker.pkg.dev/<PROJECT_ID>/article-generator/article-generator:latest .
docker push <REGION>-docker.pkg.dev/<PROJECT_ID>/article-generator/article-generator:latest
```

O usa Cloud Build para automatizarlo:

```bash
gcloud builds submit \
  --config=gcloud/cloudbuild.yaml \
  --substitutions=_REGION=europe-west1,_REPOSITORY=article-generator,_IMAGE=article-generator \
  .
```

#### 3. Actualizar la imagen en `k8s/cronjob.yaml`

Sustituye `article-generator:latest` por la ruta completa de Artifact Registry:

```
image: <REGION>-docker.pkg.dev/<PROJECT_ID>/article-generator/article-generator:latest
```

#### 4. Aplicar los manifiestos

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml   # rellena los valores base64 antes
kubectl apply -f k8s/cronjob.yaml
```

---

### Opción B – Cloud Run Jobs (serverless)

Cloud Run Jobs es la opción nativa de Google Cloud para ejecutar tareas en contenedores sin gestionar infraestructura. Se programa con **Cloud Scheduler**.

#### 1. Crear los secretos en Secret Manager

```bash
# Crear cada secreto con el valor real (sin salto de línea final)
echo -n "sk-XXXX"           | gcloud secrets create OPENAIAPIKEY --data-file=- --project=<PROJECT_ID>
echo -n "AIzaSy-XXXX"       | gcloud secrets create GEMINI_API_KEY --data-file=- --project=<PROJECT_ID>
echo -n "correo@gmail.com"  | gcloud secrets create SMTP_USER    --data-file=- --project=<PROJECT_ID>
echo -n "contraseña_app"    | gcloud secrets create SMTP_PASS    --data-file=- --project=<PROJECT_ID>
```

#### 2. Construir y subir la imagen

```bash
gcloud builds submit \
  --config=gcloud/cloudbuild.yaml \
  --substitutions=_REGION=europe-west1,_REPOSITORY=article-generator,_IMAGE=article-generator \
  .
```

#### 3. Editar `gcloud/cloud-run-job.yaml`

Sustituye los marcadores `<PROJECT_ID>` y `<REGION>` en el fichero por tus valores reales.

#### 4. Desplegar el Cloud Run Job

```bash
gcloud run jobs replace gcloud/cloud-run-job.yaml --region=<REGION>
```

#### 5. Programar ejecución semanal con Cloud Scheduler

```bash
# Crear una cuenta de servicio para que el Scheduler invoque el Job
gcloud iam service-accounts create article-generator-sa \
  --display-name="Article Generator SA" \
  --project=<PROJECT_ID>

# Dar permisos para invocar Cloud Run Jobs
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:article-generator-sa@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Crear el job de Cloud Scheduler (cada lunes a las 08:00 Europe/Madrid)
gcloud scheduler jobs create http article-generator-weekly \
  --location=<REGION> \
  --schedule="0 8 * * 1" \
  --time-zone="Europe/Madrid" \
  --uri="https://<REGION>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/article-generator:run" \
  --http-method=POST \
  --oauth-service-account-email="article-generator-sa@<PROJECT_ID>.iam.gserviceaccount.com" \
  --project=<PROJECT_ID>
```

#### 6. Ejecutar manualmente

```bash
gcloud run jobs execute article-generator --region=<REGION>
```

Consulta los logs:

```bash
gcloud logging read \
  'resource.type="cloud_run_job" AND resource.labels.job_name="article-generator"' \
  --limit=50 --project=<PROJECT_ID>
```

---

## 📂 Estructura del proyecto

```
python-article/
├── generateArticle.py       # Script principal CLI
├── seed_data.py             # Taxonomía: categorías, subcategorías y tags
├── test_generateArticle.py  # Tests del script principal
├── test_seed_data.py        # Tests de la taxonomía
├── Dockerfile               # Imagen Docker (python:3.12-slim)
├── docker-compose.yml       # Compose para ejecutar el generador
├── pyproject.toml           # Configuración del proyecto (ruff, pytest)
├── requirements.in          # Dependencias runtime (fuente)
├── requirements.txt         # Dependencias runtime (compiladas)
├── requirements-dev.in      # Dependencias de desarrollo (fuente)
├── requirements-dev.txt     # Dependencias de desarrollo (compiladas)
├── .env.example             # Plantilla de variables de entorno
├── README.md                # Documentación principal
├── ARTICLE_GENERATION.md    # Documentación técnica detallada
├── CONTRIBUTING.md          # Guía de contribución
├── SECURITY.md              # Política de seguridad
├── LICENSE                  # Licencia MIT
├── k8s/                     # Manifiestos Kubernetes (CronJob)
│   ├── configmap.yaml
│   ├── secret.yaml
│   └── cronjob.yaml
└── gcloud/                  # Ficheros Google Cloud
    ├── cloudbuild.yaml
    └── cloud-run-job.yaml
```

---

## 📰 ¿Qué es este script?

Este programa automatiza la generación de artículos técnicos, **optimizados para SEO desde su generación**, mediante argumentos de línea de comandos.

Dado un tema (tag), categoría y subcategoría, genera **un artículo técnico completo** con ayuda de **inteligencia artificial (IA)** y lo exporta a un **fichero JSON** con todos los metadatos necesarios para posicionamiento en buscadores.

Además, **te avisa por correo electrónico** de todo lo que hace:
- si empezó correctamente,
- si generó el artículo con éxito,
- si encontró algún error.

---

## 🏗️ Diagrama de arquitectura

La generación de artículos usa **LangChain Expression Language (LCEL)** como capa principal: `ChatPromptTemplate | llm | StrOutputParser()` (encapsulado en la clase `LLMChain` del proyecto), con fallback al SDK de OpenAI en caso de error. Los proveedores soportados son OpenAI, Google Gemini y Ollama.

```mermaid
flowchart TD
    A["⏰ Scheduler\n(K8s CronJob / Cloud Scheduler)"] -->|"Cada lunes 08:00 Madrid"| B
    B["🐍 generateArticle.py\n--tag --category --subcategory"] --> C["🔍 Validación\n(.env + clave API)"]
    C --> F["🤖 LangChain LCEL\n(ChatPromptTemplate | llm | StrOutputParser)\n→ OpenAI / Gemini / Ollama\n[fallback: OpenAI SDK directo]"]
    F -->|"Título + Body + Keywords + FAQ"| G["📝 Post-procesado SEO\n(metaTitle, canonicalUrl,\nJSON-LD, Open Graph)"]
    G --> H["💾 Fichero JSON local\n(article.json)"]
    H --> I["📧 Notificación email\n(SMTP)"]
    I --> J["🌐 Blog\n(importa el JSON generado)"]

    style A fill:#f59e0b,stroke:#d97706,color:#000
    style B fill:#3b82f6,stroke:#2563eb,color:#fff
    style F fill:#10b981,stroke:#059669,color:#fff
    style H fill:#6366f1,stroke:#4f46e5,color:#fff
    style J fill:#ec4899,stroke:#db2777,color:#fff
```

**Flujo resumido:**

```
Scheduler (CronJob)
       ↓
generateArticle.py --tag ... --category ... --subcategory ...
       ↓
  ┌─── Validación de entorno ──────────────────────────────┐
  │         ↓                                               │
  │    LangChain LCEL (ChatPromptTemplate | llm | Parser)  │
  │    → OpenAI / Gemini / Ollama                          │
  │    [fallback: OpenAI SDK directo]                      │
  │         ↓                                               │
  │    SEO post-procesado                                   │
  │         ↓                                               │
  │    Fichero JSON local (salida)                          │
  │         ↓                                               │
  └─── Email notificación ─────────────────────────────────┘
       ↓
     Blog (importa el JSON)
```

---

## 🔍 Funcionalidades SEO

El script implementa múltiples capas de optimización SEO que se aplican automáticamente en cada artículo generado:

### SEO On-Page (contenido)

| Característica | Descripción |
|---|---|
| **Título SEO** (`metaTitle`) | Máximo 60 caracteres, con la palabra clave principal al inicio. Optimizado para CTR en resultados de búsqueda. |
| **Meta descripción** (`metaDescription`) | Máximo 160 caracteres, incluye keyword y llamada a la acción implícita. |
| **Palabras clave** (`keywords`) | 5-7 keywords en minúsculas, incluyendo variaciones long-tail. |
| **HTML semántico** | Estructura jerárquica `<h1>` → `<h2>` → `<h3>`, uso de `<strong>` y `<em>` para énfasis. |
| **Sección FAQ** | Preguntas frecuentes redactadas como búsquedas reales de usuarios (mejora visibilidad en "People also ask"). |
| **Párrafos cortos** | 3-4 líneas máximo para mejorar legibilidad y reducir tasa de rebote. |
| **Código funcional** | Bloques `<pre><code>` con comentarios descriptivos y `class="language-..."` para resaltado. |

### SEO Técnico (metadatos)

| Campo | Tipo | Descripción |
|---|---|---|
| `canonicalUrl` | `string` | URL canónica completa del artículo (`{SITE}/post/{slug}`). Evita contenido duplicado. |
| `structuredData` | `object` | Datos estructurados **JSON-LD** con Schema.org tipo `TechArticle`. Mejora rich snippets en Google. |
| `ogTitle` | `string` | Título para Open Graph (Facebook, LinkedIn, Twitter). |
| `ogDescription` | `string` | Descripción para Open Graph. |
| `ogType` | `string` | Tipo Open Graph (`article`). |
| `metaTitle` | `string` | Título SEO optimizado (≤ 60 caracteres). |
| `metaDescription` | `string` | Meta descripción SEO (≤ 160 caracteres). |

### Datos estructurados JSON-LD (Schema.org)

Cada artículo incluye un objeto `structuredData` con formato JSON-LD listo para inyectar en el `<head>` de la página. Ejemplo:

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cómo usar @Data en Lombok",
  "description": "Aprende a reducir el código boilerplate con @Data de Lombok.",
  "author": { "@type": "Person", "name": "adminUser" },
  "publisher": { "@type": "Organization", "name": "tusitio.com", "url": "https://tusitio.com" },
  "datePublished": "2025-06-15T08:00:00+00:00",
  "dateModified": "2025-06-15T08:00:00+00:00",
  "url": "https://tusitio.com/post/como-usar-data-en-lombok",
  "mainEntityOfPage": { "@type": "WebPage", "@id": "https://tusitio.com/post/como-usar-data-en-lombok" },
  "wordCount": 1240,
  "timeRequired": "PT6M",
  "inLanguage": "es",
  "keywords": "lombok, @data, java, boilerplate, spring boot",
  "articleSection": "Lombok",
  "about": [{ "@type": "Thing", "name": "@Data" }]
}
```

Para usarlo en tu frontend, inyéctalo en el HTML de la página del artículo:

```html
<script type="application/ld+json">
  {{ article.structuredData | json }}
</script>
```

### Relación entre SEO y la jerarquía Categoría → Subcategoría → Tag

La estructura de tres niveles no solo organiza el contenido, sino que refuerza el SEO:

| Nivel | Rol SEO |
|---|---|
| **Categoría padre** | Define el **silo temático** (cluster de contenido). Los buscadores premian sitios con contenido agrupado temáticamente. |
| **Subcategoría** | Define el **campo `articleSection`** en los datos estructurados y la clasificación del artículo. |
| **Tag** | Define la **palabra clave principal** del artículo. Es la semilla del prompt que genera el contenido. |

---

## ⚙️ ¿Qué necesita para funcionar?

Para generar artículos, el script necesita los siguientes datos y accesos:

| Tipo de dato | Para qué sirve |
|---------------|----------------|
| **Clave de API de IA** | `OPENAIAPIKEY` para OpenAI (GPT) o `GEMINI_API_KEY` para Google Gemini. Al menos una es necesaria según el modelo elegido en `OPENAI_MODEL`. |
| **Argumento `--tag`** | El tema del artículo a generar. Se pasa como argumento CLI al ejecutar el script. |
| **Servidor de correo (SMTP)** | Para enviarte emails con las notificaciones (opcional). |
| **Username del autor (`--username`)** | Username/nombre del autor del artículo. Puede configurarse también con `AUTHOR_USERNAME` en el `.env`. `--author` / `-a` funciona como alias para compatibilidad con versiones anteriores. |
| **URL del sitio (`--site`)** | Necesaria para generar URLs canónicas y datos estructurados correctos. Puede configurarse con `SITE` en el `.env`. |

Todos los datos de configuración se guardan en un archivo oculto llamado **`.env`**, que el script lee automáticamente. Los argumentos CLI sobreescriben los valores del `.env`.

### Dependencias principales (`requirements.in`)

| Paquete | Versión mínima | Para qué |
|---|---|---|
| `openai` | `>=1.0.0` | SDK de OpenAI (fallback y proveedor GPT) |
| `python-dotenv` | `>=1.0.0` | Cargar variables de entorno desde `.env` |
| `langchain-openai` | `>=1.1.11` | LangChain con ChatOpenAI para LCEL |
| `langchain-core` | `>=1.2.19` | Núcleo de LangChain (ChatPromptTemplate, StrOutputParser) |
| `langchain-google-genai` | `>=2.0.0` | LangChain con Google Gemini |

---

## 🧩 Cómo organiza los temas: Categorías, Subcategorías y Tags

Tu sitio tiene **3 niveles de estructura jerárquica**:

```
Categoría padre (ej. "Spring Boot")
  └── Subcategoría (ej. "Lombok")
        └── Tag (ej. "@Data")
              └── Artículo generado
```

### Nivel 1 — Categorías padre

Son los grandes pilares temáticos del blog. Actualmente hay **3 categorías padre**:

| Categoría | Descripción | Subcategorías |
|---|---|---|
| **Spring Boot** | Desarrollo de aplicaciones Java con el framework Spring Boot | 6 subcategorías |
| **Data & Persistencia** | Gestión y persistencia de datos en aplicaciones Java | 4 subcategorías |
| **Inteligencia Artificial** | Integración de IA y Machine Learning con Java y Spring | 4 subcategorías |

### Nivel 2 — Subcategorías

Temas más concretos dentro de cada categoría. Cada subcategoría:
- Tiene un campo `parent` que apunta a la categoría padre.
- Tiene un array `tags` con los IDs de sus tags.
- Define la sección del artículo (`articleSection` en datos estructurados).

**Spring Boot:**
| Subcategoría | Nº de Tags | Ejemplo de tags |
|---|---|---|
| Spring Boot Core | 10 | `@SpringBootApplication`, `Auto-configuration`, `Spring Profiles` |
| Spring Security | 10 | `JWT Authentication`, `OAuth2 y OpenID Connect`, `CORS Configuration` |
| Spring Data JPA | 10 | `@Entity y @Table`, `JpaRepository`, `@Transactional` |
| Spring MVC REST | 10 | `@RestController`, `ResponseEntity`, `OpenAPI y Swagger` |
| Spring Boot Testing | 10 | `@SpringBootTest`, `Testcontainers`, `MockMvc` |
| Lombok | 10 | `@Data`, `@Builder`, `@Slf4j`, `@SuperBuilder` |

**Data & Persistencia:**
| Subcategoría | Nº de Tags | Ejemplo de tags |
|---|---|---|
| JPA e Hibernate | 10 | `Hibernate Caching L1 y L2`, `Problema N+1 y soluciones`, `FetchType LAZY vs EAGER` |
| Bases de Datos SQL | 10 | `PostgreSQL con Spring Boot`, `MySQL con Spring Boot`, `QueryDSL` |
| NoSQL y MongoDB | 10 | `Spring Data MongoDB`, `@Document y @Field`, `Aggregation Pipeline con Spring` |
| Migraciones de Esquema | 8 | `Flyway con Spring Boot`, `Liquibase con Spring Boot`, `Rollback con Flyway` |

**Inteligencia Artificial:**
| Subcategoría | Nº de Tags | Ejemplo de tags |
|---|---|---|
| Spring AI | 10 | `Spring AI Overview`, `ChatClient con Spring AI`, `Function Calling con Spring AI` |
| LLMs y Modelos de Lenguaje | 10 | `OpenAI API con Java`, `GPT-4 y modelos avanzados`, `Prompt Engineering avanzado` |
| Machine Learning con Java | 10 | `Deeplearning4j`, `TensorFlow Java`, `ONNX Runtime en Java` |
| Vector Databases y RAG | 10 | `RAG (Retrieval Augmented Generation)`, `Embeddings con Spring AI`, `Pinecone con Java` |

### Nivel 3 — Tags

Los tags son las **palabras clave específicas** que definen el tema del artículo. Cada tag:
- Tiene un `categoryId` que apunta a su subcategoría.
- Tiene un `parentCategoryId` que apunta a la categoría padre.
- Es la **semilla** a partir de la cual la IA genera el artículo.
- Se convierte en la **keyword principal** del contenido generado.

### ¿Y si una categoría no tiene subcategorías?

No pasa nada. El script está preparado para publicar artículos también **aunque una categoría no tenga subcategorías**, siempre que **tenga tags** asociados directamente.

---

## 🧠 Qué hace paso a paso

### 1) Empieza y revisa la configuración
Cuando lo ejecutas, lo primero que hace es comprobar que están todas las claves y accesos necesarios:
- OpenAI o Google Gemini (según `OPENAI_MODEL`)
- SMTP (correo electrónico, opcional)

Si falta la clave de API, te envía un correo avisándote y **se detiene**.

### 2) Recibe el tema a generar
El script recibe el tema mediante argumentos CLI:
- `--tag` (obligatorio): el tema o tag del artículo
- `--category` y `--subcategory`: clasificación del artículo
- `--language`: idioma de generación

### 3) Pide a la IA que escriba el artículo (optimizado para SEO)
Genera un encargo para la IA con instrucciones SEO detalladas usando **LangChain LCEL** (`ChatPromptTemplate | llm | StrOutputParser()`):

> "Escribe un artículo SEO en español sobre *@Builder* (categoría: Spring Boot, subcategoría: Lombok).
> Título optimizado para SEO y CTR (máx. 60 caracteres), con keyword principal al inicio.
> Meta-descripción SEO (máx. 160 caracteres), con keyword y CTA implícita.
> 5-7 keywords SEO long-tail en minúsculas.
> HTML semántico con h1, h2, h3, `<strong>`, `<em>`, código funcional, FAQ y conclusión con CTA."

La IA devuelve el artículo completo en formato JSON:
- **title** — título optimizado para SEO (≤ 60 caracteres)
- **summary** — meta descripción (≤ 160 caracteres)
- **body** — contenido completo en HTML semántico
- **keywords** — 5-7 palabras clave SEO

### 4) Revisa que el título sea único
Para evitar duplicados o artículos parecidos:
- Compara el nuevo título con los títulos pasados en `--avoid-titles` usando `difflib.SequenceMatcher`.
- Si es **demasiado parecido** (ratio ≥ 0.86), regenera solo el título (no el artículo entero) hasta 5 veces.

Si después de varios intentos no consigue uno suficientemente diferente, te avisa por correo y no guarda nada.

### 5) Genera metadatos SEO y guarda el artículo en JSON
Si todo está bien:
- Crea un **slug** SEO-friendly (ej. `como-usar-builder-en-spring-boot`).
- Calcula `wordCount` y `readingTime`.
- Genera la **URL canónica** (`canonicalUrl`).
- Genera los **datos estructurados JSON-LD** (Schema.org `TechArticle`).
- Genera los metadatos **Open Graph** (`ogTitle`, `ogDescription`, `ogType`).
- Asigna autor, fecha y estado "publicado".
- Lo guarda en el fichero JSON indicado por `--output`.

Luego te envía un email con algo así:

> ✅ **Artículo guardado**
> Título: "Cómo usar @Builder en Spring Boot"
> Enlace: `https://tuweb.com/post/como-usar-builder-en-spring-boot`
> Tag: *@Builder*

### 6) Termina
Finaliza el proceso con un último mensaje en pantalla y por email:
> "Proceso terminado. Artículo guardado en 'article.json'."

---

## 📄 Documento del artículo generado (campos SEO)

El artículo se exporta a un fichero JSON con la siguiente estructura:

```json
{
  "title":           "Cómo usar @Data en Lombok",
  "slug":            "como-usar-data-en-lombok",
  "summary":         "Aprende a reducir el código boilerplate con @Data de Lombok.",
  "body":            "<h1>...</h1><p>...</p>...",
  "category":        "Lombok",
  "tags":            ["@Data"],
  "author":          "adminUser",
  "status":          "published",
  "likes":           [],
  "favoritedBy":     [],
  "isVisible":       true,
  "publishDate":     "2025-06-15T08:00:00+00:00",
  "generatedAt":     "2025-06-15T08:00:00+00:00",
  "createdAt":       "2025-06-15T08:00:00+00:00",
  "updatedAt":       "2025-06-15T08:00:00+00:00",
  "images":          null,
  "wordCount":       1240,
  "readingTime":     6,
  "keywords":        ["lombok", "@data", "java", "boilerplate", "pojo"],
  "metaTitle":       "Cómo usar @Data en Lombok",
  "metaDescription": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
  "canonicalUrl":    "https://tusitio.com/post/como-usar-data-en-lombok",
  "ogTitle":         "Cómo usar @Data en Lombok",
  "ogDescription":   "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
  "ogType":          "article",
  "structuredData":  { "@context": "https://schema.org", "@type": "TechArticle", "..." }
}
```

### Detalle de cada campo SEO

| Campo | Tipo | Límite | Descripción |
|---|---|---|---|
| `metaTitle` | `string` | ≤ 60 chars | Título optimizado para la etiqueta `<title>` de la página. Google muestra ~60 caracteres en los resultados. |
| `metaDescription` | `string` | ≤ 160 chars | Texto para la etiqueta `<meta name="description">`. Google muestra ~160 caracteres. |
| `canonicalUrl` | `string` | — | URL completa del artículo para la etiqueta `<link rel="canonical">`. Evita penalizaciones por contenido duplicado. |
| `keywords` | `[string]` | 5-7 items | Palabras clave para `<meta name="keywords">` y uso interno en la web. Incluye variaciones long-tail. |
| `ogTitle` | `string` | ≤ 60 chars | Título para Open Graph: `<meta property="og:title">`. Se muestra al compartir en redes sociales. |
| `ogDescription` | `string` | ≤ 160 chars | Descripción para Open Graph: `<meta property="og:description">`. |
| `ogType` | `string` | — | Tipo Open Graph: `article`. Para `<meta property="og:type">`. |
| `structuredData` | `object` | — | JSON-LD Schema.org `TechArticle`. Se inyecta como `<script type="application/ld+json">`. |
| `wordCount` | `int` | — | Número de palabras del contenido. Útil para mostrar al usuario y para análisis de calidad. |
| `readingTime` | `int` | — | Minutos de lectura estimados (`ceil(wordCount / 230)`). Mejora la UX y el engagement. |

---

## 📤 Ejemplo de output generado

A continuación se muestra un ejemplo representativo de lo que el script genera para el tag **@Data** (subcategoría: Lombok, categoría: Spring Boot).

### HTML del artículo (body)

```html
<h1>Cómo usar @Data en Lombok para simplificar tu código Java</h1>

<p>
  La anotación <strong>@Data</strong> de <em>Lombok</em> es una de las herramientas
  más potentes para reducir el <strong>código boilerplate</strong> en proyectos
  <strong>Spring Boot</strong>. En este artículo aprenderás a usarla de forma
  efectiva.
</p>

<h2>¿Qué genera @Data?</h2>
<p>
  Al anotar una clase con <code>@Data</code>, Lombok genera automáticamente:
</p>
<ul>
  <li><strong>Getters</strong> para todos los campos</li>
  <li><strong>Setters</strong> para todos los campos no finales</li>
  <li><strong>toString()</strong></li>
  <li><strong>equals()</strong> y <strong>hashCode()</strong></li>
  <li>Un <strong>constructor</strong> con los campos obligatorios</li>
</ul>

<h2>Ejemplo práctico</h2>
<pre><code class="language-java">
import lombok.Data;

@Data
public class User {
    private String name;
    private String email;
    private int age;
}
</code></pre>

<h2>Integración con Spring Boot</h2>
<p>
  <strong>@Data</strong> se combina perfectamente con <em>Spring Data JPA</em>.
  Puedes anotar tus entidades y reducir decenas de líneas de código.
</p>

<pre><code class="language-java">
@Data
@Entity
@Table(name = "users")
public class UserEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String username;
    private String email;
}
</code></pre>

<h2>❓ Preguntas frecuentes (FAQ)</h2>

<h3>¿Qué métodos genera @Data exactamente?</h3>
<p>Genera getters, setters, toString, equals y hashCode de forma automática.</p>

<h3>¿Puedo usar @Data con herencia?</h3>
<p>
  Sí, pero se recomienda añadir <code>@EqualsAndHashCode(callSuper = true)</code>
  para incluir los campos de la clase padre.
</p>

<h3>¿@Data es compatible con Spring Boot 3?</h3>
<p>Sí, Lombok es totalmente compatible con Spring Boot 3 y Java 17+.</p>

<h2>Conclusión</h2>
<p>
  Usa <strong>@Data</strong> en tus proyectos Spring Boot para escribir menos código
  y centrarte en la lógica de negocio. Combínalo con <code>@Builder</code> y
  <code>@Slf4j</code> para una productividad aún mayor.
</p>
```

### Metadatos SEO generados

```json
{
  "title": "Cómo usar @Data en Lombok para simplificar tu código Java",
  "slug": "como-usar-data-en-lombok-para-simplificar-tu-codigo-java",
  "summary": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot. Guía completa con ejemplos.",
  "keywords": ["lombok", "@data", "java", "boilerplate", "spring boot", "getter setter", "pojo"],
  "metaTitle": "Cómo usar @Data en Lombok | Guía Spring Boot",
  "metaDescription": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot. Guía completa con ejemplos.",
  "canonicalUrl": "https://tusitio.com/post/como-usar-data-en-lombok-para-simplificar-tu-codigo-java",
  "ogTitle": "Cómo usar @Data en Lombok para simplificar tu código Java",
  "ogDescription": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
  "ogType": "article",
  "wordCount": 1240,
  "readingTime": 6,
  "structuredData": {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "Cómo usar @Data en Lombok para simplificar tu código Java",
    "description": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
    "author": { "@type": "Person", "name": "adminUser" },
    "publisher": { "@type": "Organization", "name": "tusitio.com", "url": "https://tusitio.com" },
    "datePublished": "2025-06-15T08:00:00+00:00",
    "dateModified": "2025-06-15T08:00:00+00:00",
    "url": "https://tusitio.com/post/como-usar-data-en-lombok-para-simplificar-tu-codigo-java",
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": "https://tusitio.com/post/como-usar-data-en-lombok-para-simplificar-tu-codigo-java"
    },
    "wordCount": 1240,
    "timeRequired": "PT6M",
    "inLanguage": "es",
    "keywords": "lombok, @data, java, boilerplate, spring boot, getter setter, pojo",
    "articleSection": "Lombok"
  }
}
```

---

## 📸 Screenshots

Las siguientes capturas muestran el resultado real del sistema en funcionamiento.

> **Nota:** Reemplaza los placeholders SVG con capturas reales de tu entorno ejecutando el script y revisando el fichero JSON generado y los resultados en tu blog.

### Fichero JSON generado

Así se ve el fichero JSON generado por el script:

![Fichero JSON generado](docs/screenshots/mongodb-document.svg)

### Página del artículo generado

Vista de la página del artículo publicada en el blog con HTML semántico, FAQ y tags:

![Página del artículo generado](docs/screenshots/generated-article-page.svg)

### Metadatos SEO

Metadatos SEO completos del artículo: metaTitle, metaDescription, canonicalUrl, Open Graph, keywords y JSON-LD:

![Metadatos SEO](docs/screenshots/seo-metadata.svg)

---

## 📨 Tipos de notificaciones que envía
Durante la ejecución, el script puede mandarte distintos tipos de mensajes por correo:

| Tipo | Ejemplo |
|------|----------|
| ℹ️ **Info** | "Inicio de proceso" o "OpenAI listo". |
| ✅ **Éxito** | "Artículo guardado en 'article.json'". |
| ⚠️ **Advertencia** | "Título similar detectado, regenerando...". |
| ❌ **Error** | "Falta la variable de entorno OPENAIAPIKEY" o "Error generando artículo". |

---

## 🕐 Frecuencia de publicación
- Genera **un artículo por ejecución** (una ejecución = un artículo).
- Si usas un **CronJob semanal** (K8s o Cloud Scheduler), puedes programarlo para ejecutarse cada lunes a las 08:00.

---

## 🔒 Seguridad y privacidad
- Las contraseñas, claves de API y datos sensibles **no están dentro del código**.
  Se guardan en el archivo `.env`, que **no debe compartirse**.
- No envía datos a ningún sitio externo salvo al proveedor de IA configurado (OpenAI o Google Gemini, para generar el texto) y tu servidor de correo (para notificarte).

---

## ⚙️ Constantes y configuración interna

El script define las siguientes constantes en `generateArticle.py`:

| Constante | Valor | Descripción |
|---|---|---|
| `SIMILARITY_THRESHOLD_DEFAULT` | `0.82` | Umbral para detección genérica de títulos similares |
| `SIMILARITY_THRESHOLD_STRICT` | `0.86` | Umbral usado al reintentar generación de título único |
| `MAX_TITLE_RETRIES` | `5` | Intentos máximos para generar un título único |
| `OPENAI_MAX_RETRIES` | `3` | Reintentos para llamadas a la API de IA |
| `OPENAI_RETRY_BASE_DELAY` | `2` | Segundos base para backoff exponencial entre reintentos |
| `META_TITLE_MAX_LENGTH` | `60` | Máximo de caracteres para `metaTitle` SEO |
| `META_DESCRIPTION_MAX_LENGTH` | `160` | Máximo de caracteres para `metaDescription` SEO |
| `MAX_AVOID_TITLES_IN_PROMPT` | `5` | Máximo de títulos a incluir en el prompt (para mantener prompts cortos) |
| `OPENAI_MAX_ARTICLE_TOKENS` | `4096` | Límite de tokens de salida para artículos |
| `OPENAI_MAX_TITLE_TOKENS` | `100` | Límite de tokens de salida para títulos |

### Idiomas soportados (`ARTICLE_LANGUAGE`)

| Código | Idioma |
|---|---|
| `es` | español |
| `en` | inglés |
| `fr` | francés |
| `de` | alemán |
| `it` | italiano |
| `pt` | portugués |
| `nl` | neerlandés |
| `pl` | polaco |
| `ru` | ruso |
| `zh` | chino |
| `ja` | japonés |
| `ar` | árabe |

---

## 🛠️ Calidad de código

El proyecto usa **[ruff](https://docs.astral.sh/ruff/)** como linter y formateador, configurado en `pyproject.toml`:

- `line-length = 100`
- Target: Python 3.10+

Para ejecutar antes de un PR:

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format .
```

---

## 🧾 En resumen

| Acción | Descripción |
|--------|--------------|
| 📥 Recibir el tema por CLI | `--tag`, `--category`, `--subcategory` pasados como argumentos al ejecutar |
| ✍️ Generar artículo con IA (SEO) | Escribe título, resumen, cuerpo HTML y keywords optimizados para SEO |
| 🏷️ Generar metadatos SEO | `metaTitle`, `metaDescription`, `canonicalUrl`, JSON-LD, Open Graph |
| 🚫 Evitar repeticiones | No repite títulos similares (umbral 0.86) — usa `--avoid-titles` para pasar títulos existentes |
| 💾 Exportar a JSON | Guarda el artículo completo con todos los campos SEO en el fichero indicado por `--output` |
| 📧 Notificar por correo | Te informa de todo lo que ha hecho |

---

## 🌟 Ejemplo de funcionamiento real

```bash
python3 generateArticle.py \
  --tag "@Data" \
  --category "Spring Boot" \
  --subcategory "Lombok" \
  --output article.json \
  --language es
```

1. Valida que `OPENAIAPIKEY` (o `GEMINI_API_KEY`) está disponible.
2. Pide a la IA un artículo SEO sobre "@Data" (categoría: Spring Boot, subcategoría: Lombok).
3. Recibe: título SEO, meta descripción, HTML semántico con FAQ y keywords.
4. Genera la URL canónica, los datos estructurados JSON-LD y los metadatos Open Graph.
5. Guarda el artículo en `article.json` con el usuario "adminUser".
6. Te manda un email:
   > ✅ Artículo guardado: "Cómo simplificar tu código con @Data en Lombok".
   > Enlace: https://tusitio.com/post/como-simplificar-tu-codigo-con-data-en-lombok

---

## 🤝 Contribuir

Antes de enviar un PR, lee la [Guía de contribución](CONTRIBUTING.md).

> **Regla obligatoria:** Toda contribución que modifique funcionalidad, configuración, flujo de ejecución o estructura del proyecto **DEBE actualizar este `README.md`** de forma acorde. Consulta la tabla detallada en [CONTRIBUTING.md](CONTRIBUTING.md).
