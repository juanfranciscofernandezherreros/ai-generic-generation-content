# Guía de contribución

Gracias por tu interés en contribuir a este proyecto. A continuación se describen las reglas y buenas prácticas que deben seguirse.

---

## 📌 Regla obligatoria: actualizar `README.md`

> **Toda contribución que modifique funcionalidad, configuración, flujo de ejecución o estructura del proyecto DEBE actualizar el `README.md` de forma acorde.**

### ¿Cuándo actualizar el README?

| Cambio realizado | Acción requerida en `README.md` |
|---|---|
| Nuevo campo en el documento del artículo (JSON) | Actualizar la sección **Documento del artículo generado (campos SEO)** |
| Nuevo paso en el flujo de ejecución | Actualizar **Qué hace paso a paso** y el **diagrama de arquitectura** |
| Nueva variable de entorno | Actualizar la tabla de variables en **Guía rápida de ejecución** |
| Nuevo despliegue o infraestructura | Actualizar la sección correspondiente (Docker, K8s, GCloud) |
| Cambio en dependencias (`requirements.txt`) | Actualizar los requisitos previos si es necesario |
| Cambio en la estructura de categorías/tags | Actualizar **Cómo organiza los temas** |
| Nueva funcionalidad SEO | Actualizar **Funcionalidades SEO** |
| Cambio en notificaciones | Actualizar **Tipos de notificaciones que envía** |
| Cambios visuales o de output | Actualizar la sección **Ejemplo de output generado** y/o los **screenshots** |
| Nuevo argumento CLI | Actualizar la sección **Guía rápida de ejecución** con el nuevo argumento |

### ¿Qué secciones del README mantener al día?

1. **Diagrama de arquitectura** — Debe reflejar el flujo real del sistema.
2. **Ejemplo de output generado** — Debe mostrar un ejemplo representativo del HTML, FAQ y metadatos que produce el script.
3. **Screenshots** — Deben actualizarse cuando cambie la estructura del documento JSON generado o los metadatos SEO.
4. **Tabla de campos SEO** — Debe incluir todos los campos actuales del documento.
5. **Índice** — Debe incluir todas las secciones del README.

---

## 🧪 Tests

El proyecto tiene dos ficheros de test que deben pasar antes de enviar un PR:

- `test_generateArticle.py` — Tests del script principal (generación, SEO, CLI).
- `test_seed_data.py` — Tests de la taxonomía de categorías, subcategorías y tags.

Ejecuta todos los tests:

```bash
pip install -r requirements-dev.txt
python -m pytest test_generateArticle.py test_seed_data.py -v
```

Añade tests para cualquier función nueva o modificada.

---

## 🛠️ Calidad de código con ruff

El proyecto usa **[ruff](https://docs.astral.sh/ruff/)** como linter y formateador (`line-length = 100`, Python 3.10+).

Ejecuta siempre antes de enviar un PR:

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format .
```

La configuración de ruff está en `pyproject.toml`.

---

## 📝 Estilo de código

- Escribe en **Python 3.10+**.
- Usa **docstrings** en funciones públicas.
- Sigue las convenciones existentes del proyecto.

---

## 📂 Estructura de archivos

```
python-article/
├── generateArticle.py       # Script principal CLI (fachada que re-exporta los submódulos)
├── config.py                # Constantes y configuración del entorno
├── utils.py                 # Funciones auxiliares genéricas (slugify, similitud, etc.)
├── html_utils.py            # Utilidades de procesamiento HTML (count_words, reading_time)
├── seo.py                   # Funciones SEO (canonical URL, JSON-LD)
├── notifications.py         # Sistema de notificaciones y email SMTP
├── prompts.py               # Construcción de prompts para la IA
├── ai_providers.py          # Proveedores de IA (LangChain LCEL, Ollama, Gemini)
├── article_generator.py     # Generación y guardado de artículos
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
├── README.md                # Documentación principal (¡siempre actualizar!)
├── ARTICLE_GENERATION.md    # Documentación técnica detallada
├── CONTRIBUTING.md          # Esta guía
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

## 🌿 Cómo añadir nuevas categorías, subcategorías y tags

La taxonomía del proyecto se define en `seed_data.py`, en la constante `TAXONOMY`. Para añadir contenido nuevo:

1. Abre `seed_data.py`.
2. Para añadir una **nueva categoría**, agrega un nuevo objeto al array `TAXONOMY`:
   ```python
   {
       "name": "Mi Nueva Categoría",
       "description": "Descripción breve de la categoría.",
       "subcategories": [...]
   }
   ```
3. Para añadir una **nueva subcategoría**, agrega un objeto al array `subcategories` de la categoría correspondiente:
   ```python
   {
       "name": "Mi Subcategoría",
       "description": "Descripción breve.",
       "tags": ["Tag 1", "Tag 2", "Tag 3"]
   }
   ```
4. Para añadir **nuevos tags**, agrega strings al array `tags` de la subcategoría correspondiente.
5. Actualiza la sección **🧩 Cómo organiza los temas** en `README.md` si cambias la estructura.
6. Ejecuta los tests para asegurarte de que la taxonomía sigue siendo válida:
   ```bash
   python -m pytest test_seed_data.py -v
   ```

