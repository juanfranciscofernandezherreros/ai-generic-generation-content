# Despliegue en Heroku con Heroku Scheduler

Esta guía explica cómo desplegar `generateArticle.py` en Heroku como una **tarea programada** usando el add-on **Heroku Scheduler**. El script es un CLI, no una aplicación web, por lo que no se expone como proceso `web`.

---

## Prerrequisitos

- Cuenta en [Heroku](https://signup.heroku.com/)
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) instalado
- Git instalado y el repositorio clonado localmente

---

## Pasos de despliegue

### 1. Iniciar sesión en Heroku

```bash
heroku login
```

### 2. Crear la aplicación en Heroku

```bash
heroku create nombre-de-tu-app
```

O conectar una app existente:

```bash
heroku git:remote -a nombre-de-tu-app
```

### 3. Configurar las variables de entorno

Copia los valores de tu `.env` local (nunca subas el archivo `.env` al repositorio). Ejecuta los siguientes comandos sustituyendo los valores de ejemplo por los reales:

```bash
# --- Proveedor de IA ---
# Elige UNO de los tres proveedores siguientes:

# OpenAI / ChatGPT
heroku config:set OPENAIAPIKEY="sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
heroku config:set OPENAI_MODEL="gpt-4o"

# Google Gemini (cambia también OPENAI_MODEL)
heroku config:set GEMINI_API_KEY="AIzaSy-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
heroku config:set OPENAI_MODEL="gemini-2.0-flash"

# Ollama (LLM local — no recomendado en Heroku, requiere servidor accesible)
# heroku config:set OLLAMA_BASE_URL="http://tu-servidor-ollama:11434/v1"
# heroku config:set OPENAI_MODEL="llama3"

# --- Parámetros de generación ---
heroku config:set AI_TEMPERATURE_ARTICLE="0.7"
heroku config:set AI_TEMPERATURE_TITLE="0.9"
heroku config:set ARTICLE_LANGUAGE="es"

# --- Identidad del sitio y autor ---
heroku config:set SITE="https://tusitio.com"
heroku config:set AUTHOR_USERNAME="adminUser"

# --- Notificaciones por email (SMTP) — opcionales ---
heroku config:set SMTP_HOST="smtp.gmail.com"
heroku config:set SMTP_PORT="587"
heroku config:set SMTP_USER="tu_correo@gmail.com"
heroku config:set SMTP_PASS="tu_contraseña_de_aplicacion"
heroku config:set FROM_EMAIL="tu_correo@gmail.com"
heroku config:set NOTIFY_EMAIL="tu_correo@gmail.com"

# --- Comportamiento de notificaciones ---
heroku config:set NOTIFY_VERBOSE="true"
heroku config:set SEND_PROMPT_EMAIL="false"
```

Puedes verificar las variables configuradas con:

```bash
heroku config
```

### 4. Instalar el add-on Heroku Scheduler

```bash
heroku addons:create scheduler:standard
```

> **Nota:** El plan `standard` es gratuito. Requiere verificar tu cuenta con una tarjeta de crédito.

### 5. Configurar la tarea programada

Abre el panel del Scheduler:

```bash
heroku addons:open scheduler
```

En la interfaz web, añade una nueva tarea con el comando:

```
python generateArticle.py --tag "TuTag" --category "TuCategoria" --subcategory "TuSubcategoria"
```

Sustituye `TuTag`, `TuCategoria` y `TuSubcategoria` por los valores reales que quieras. Selecciona la frecuencia deseada (cada 10 minutos, cada hora, o diariamente).

**Argumentos disponibles:**

| Argumento | Descripción | Obligatorio |
|---|---|---|
| `--tag` | Tag o tema del artículo | Sí |
| `--category` | Categoría principal | Sí |
| `--subcategory` | Subcategoría | Sí |
| `--output` | Directorio de salida del JSON | No |
| `--author` | Nombre del autor | No |
| `--site` | URL base del sitio | No |
| `--language` | Código de idioma (ISO 639-1) | No |
| `--avoid-titles` | Títulos a evitar (separados por comas) | No |

### 6. Hacer el deploy

```bash
git push heroku master
```

> Si tu rama principal se llama `main`, usa: `git push heroku main`

### 6.1. Escalar el dyno worker a 0

El `Procfile` incluye un proceso `worker` mínimo solo para que Heroku no falle al arrancar. Como la ejecución real la gestiona Heroku Scheduler, debes **escalar el worker a 0** para evitar consumo innecesario de dynos:

```bash
heroku ps:scale worker=0
```

### 7. Verificar el despliegue

Comprueba los logs para asegurarte de que la aplicación se ha desplegado correctamente:

```bash
heroku logs --tail
```

Ejecuta la tarea manualmente para probarla antes de que el Scheduler la lance:

```bash
heroku run python generateArticle.py --tag "JWT" --category "Spring Boot" --subcategory "Security"
```

---

## Nota importante: seguridad del archivo `.env`

**NO** subas nunca el archivo `.env` al repositorio. Este archivo contiene tus claves de API y credenciales SMTP. Ya está incluido en `.gitignore` para evitar subidas accidentales.

Usa siempre `heroku config:set` para gestionar las variables de entorno en producción.

---

## Referencia rápida de comandos

```bash
# Ver todas las variables de entorno configuradas
heroku config

# Actualizar una variable
heroku config:set NOMBRE_VARIABLE="nuevo_valor"

# Ver logs en tiempo real
heroku logs --tail

# Ejecutar el script manualmente
heroku run python generateArticle.py --tag "MiTag" --category "MiCategoria" --subcategory "MiSubcategoria"

# Abrir el panel de Heroku Scheduler
heroku addons:open scheduler
```
