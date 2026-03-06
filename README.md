# Publicación automática semanal con IA

---

## 🚀 Guía rápida de ejecución

### Requisitos previos

| Herramienta | Versión mínima | Para qué |
|---|---|---|
| **Python** | 3.10+ | Ejecutar el script |
| **Docker** y **Docker Compose** | Docker 20+ | Levantar MongoDB |
| **Clave de OpenAI** | — | Generar artículos con IA |

### 1. Clonar el repositorio

```bash
git clone https://github.com/juanfranciscofernandezherreros/python-openai.git
cd python-openai
```

### 2. Levantar MongoDB con Docker Compose

```bash
docker compose up -d
```

Esto arranca un contenedor **MongoDB 7** en el puerto `27017` con:
- Usuario: `admin`
- Contraseña: `admin1234`
- Base de datos inicial: `blogdb`
- Volumen persistente `mongo_data` para no perder datos al reiniciar.

Comprueba que está sano:

```bash
docker compose ps
```

Deberías ver el servicio `mongodb-articles` con estado **healthy**.

### 3. Configurar las variables de entorno

Copia el fichero de ejemplo y edita los valores:

```bash
cp .env.example .env
```

Abre `.env` con tu editor y rellena, como mínimo:

| Variable | Qué poner |
|---|---|
| `OPENAIAPIKEY` | Tu clave de API de OpenAI (`sk-...`) |
| `SMTP_*` / `FROM_EMAIL` / `NOTIFY_EMAIL` | Datos de tu servidor de correo (SMTP) |
| `AUTHOR_USERNAME` | Nombre del usuario autor en tu base de datos |
| `SITE` | URL de tu web (p. ej. `https://tusitio.com`) |

> **Nota:** Si usas el `docker-compose.yml` incluido, la variable `MONGODB_URI` ya viene configurada correctamente y no necesitas cambiarla.

### 4. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 5. Sembrar categorías y tags predefinidos

Antes de generar artículos, es necesario que la base de datos tenga categorías y
tags. Puedes hacerlo de dos formas:

**Opción A – Automática (con Docker Compose)**

Al levantar el contenedor por primera vez, el script `mongo-init/init_seed.js`
se ejecuta automáticamente y siembra todos los datos. No necesitas hacer nada más.

> **Nota:** Este seed automático solo ocurre cuando el volumen `mongo_data` está
> vacío (primera vez). Si ya tienes el contenedor corriendo, usa la Opción B.

**Opción B – Manual (script Python)**

Con MongoDB ya en marcha, ejecuta:

```bash
python seed_data.py
```

El script crea (o actualiza de forma idempotente) los siguientes temas:

| Categoría padre | Subcategorías |
|---|---|
| **Spring Boot** | Spring Boot Core · Spring Security · Spring Data JPA · Spring MVC REST · Spring Boot Testing · Lombok |
| **Data & Persistencia** | JPA e Hibernate · Bases de Datos SQL · NoSQL y MongoDB · Migraciones de Esquema |
| **Inteligencia Artificial** | Spring AI · LLMs y Modelos de Lenguaje · Machine Learning con Java · Vector Databases y RAG |

Cada subcategoría incluye 8-10 tags específicos (p. ej. `@Entity y @Table`,
`JWT Authentication`, `RAG (Retrieval Augmented Generation)`).

### 6. Ejecutar el script principal

```bash
python generateArticle.py
```

El script:
1. Comprueba la configuración.
2. Se conecta a MongoDB.
3. Busca un tag sin artículo publicado.
4. Genera el artículo con OpenAI.
5. Lo guarda en la base de datos y te notifica por correo.

### 7. Ejecutar los tests

```bash
pip install pytest
python -m pytest test_generateArticle.py -v
```

### Comandos útiles de Docker Compose

```bash
# Ver logs de MongoDB
docker compose logs -f mongodb

# Parar el contenedor
docker compose down

# Parar y borrar el volumen de datos
docker compose down -v
```

---

## 📰 ¿Qué es este script?
Este programa automatiza la publicación de artículos en tu web.  
Cada semana genera **un nuevo artículo técnico**, escrito con ayuda de **inteligencia artificial (IA)**, y lo guarda directamente en tu **base de datos** (como si lo hubieras subido tú).

Además, **te avisa por correo electrónico** de todo lo que hace:  
- si empezó correctamente,  
- si publicó algo,  
- si encontró algún error,  
- o si ya no quedan temas disponibles.

---

## ⚙️ ¿Qué necesita para funcionar?

Antes de poder publicar artículos, el script necesita algunos datos y accesos:

| Tipo de dato | Para qué sirve |
|---------------|----------------|
| **Base de datos MongoDB** | Donde están las categorías, etiquetas (tags), usuarios y artículos. |
| **Clave de OpenAI** | Es la llave que permite que la IA escriba los artículos. |
| **Servidor de correo (SMTP)** | Para poder enviarte emails con las notificaciones. |
| **Usuario autor** | El nombre del usuario (por ejemplo “adminUser”) con el que se publicarán los artículos. |

Todos esos datos se guardan en un archivo oculto llamado **`.env`**, que el script lee automáticamente.

---

## 🧩 Cómo organiza los temas

Tu sitio tiene 3 niveles de estructura:

1. **Categorías** → grandes temas (por ejemplo “Spring Boot”, “Bases de datos”).  
2. **Subcategorías** → temas más concretos dentro de cada categoría (“Lombok”, “JPA”).  
3. **Tags (etiquetas)** → palabras clave específicas que definen el tema del artículo (“@Data”, “JpaRepository”, “Spring Profiles”).

👉 El artículo se genera **a partir de un tag**.  
Pero para elegirlo, el script necesita saber en qué categoría y subcategoría está ese tag.

---

## 💡 ¿Y si una categoría no tiene subcategorías?

No pasa nada.  
El script está preparado para publicar artículos también **aunque una categoría no tenga subcategorías**, siempre que **tenga tags (etiquetas)** asociados directamente.

Así puede funcionar con cualquier estructura, sencilla o compleja.

---

## 🧠 Qué hace paso a paso

### 1) Empieza y revisa la configuración
Cuando lo ejecutas, lo primero que hace es comprobar que están todas las claves y accesos necesarios:  
- OpenAI  
- MongoDB  
- SMTP (correo electrónico)  
- Colecciones (categorías, tags, usuarios y artículos)

Si falta algo, te envía un correo avisándote y **se detiene**.

### 2) Se conecta a la base de datos
Abre conexión con tu base de datos MongoDB y revisa que haya:
- Categorías
- Tags (etiquetas)
- El usuario autor que publicará los artículos.

Si no encuentra alguna de esas cosas, también te lo avisa por correo.

### 3) Comprueba el límite semanal
Antes de crear nada nuevo, revisa si **ya se publicó un artículo esta semana** (de lunes a domingo, según el horario de Madrid).

- Si **ya hay uno**, **no publica otro** y te manda un email diciendo:
  > “Ya existe un artículo esta semana, no se publicará ninguno nuevo.”

- Si **no hay ninguno**, continúa con el proceso.

### 4) Busca un tema disponible
El script examina todas las categorías y subcategorías con sus etiquetas.

- Si encuentra **algún tag que todavía no tenga artículos publicados**, lo elige aleatoriamente.
- Si **todos los tags ya tienen artículos**, te envía un correo:
  > “No queda ninguna categoría/tag sin artículos publicados. No se publicará nada.”

y termina el proceso.

### 5) Pide a la IA que escriba el artículo
Una vez que elige el tag, genera un encargo para la IA con instrucciones muy claras, por ejemplo:

> “Escribe un artículo en español sobre *@Builder* en Spring Boot.  
> Usa estructura HTML, con título, introducción, secciones, ejemplos de código,  
> una sección de preguntas frecuentes y una conclusión.”

La IA devuelve el artículo completo en formato JSON con tres partes:
- **title** (título)
- **summary** (resumen)
- **body** (contenido en HTML)

### 6) Revisa que el título sea único
Para evitar duplicados o artículos parecidos:
- Compara el nuevo título con los **50 más recientes**.
- Si es **demasiado parecido**, vuelve a pedir otro título a la IA hasta 5 veces.

Si después de varios intentos no consigue uno suficientemente diferente, te avisa por correo y no publica nada.

### 7) Guarda el artículo en la base de datos
Si todo está bien:
- Crea un **slug** (la parte final del enlace, como `/post/mi-articulo`).
- Asigna autor, fecha y estado “publicado”.
- Lo guarda en la colección de artículos de tu base de datos.

Luego te envía un email con algo así:

> ✅ **Artículo publicado**  
> Título: “Cómo usar @Builder en Spring Boot”  
> Enlace: `https://tuweb.com/post/como-usar-builder-en-spring-boot`  
> Tag: *@Builder*

### 8) Actualiza el historial y termina
Añade el nuevo título a la lista interna para no repetirlo, y finaliza el proceso con un último mensaje en pantalla y por email:
> “Proceso terminado. Artículos creados: 1 (límite semanal alcanzado).”

---

## 📨 Tipos de notificaciones que envía
Durante la ejecución, el script puede mandarte distintos tipos de mensajes por correo:

| Tipo | Ejemplo |
|------|----------|
| ℹ️ **Info** | “Inicio de proceso” o “Datos cargados correctamente”. |
| ✅ **Éxito** | “Artículo publicado con éxito”. |
| ⚠️ **Advertencia** | “Ya existe un artículo esta semana” o “No quedan tags disponibles”. |
| ❌ **Error** | “Fallo al conectar a MongoDB” o “Error generando artículo”. |

---

## 🕐 Frecuencia de publicación
- Publica **solo un artículo por semana**.
- Usa el **horario de Madrid** para definir la semana (de lunes a domingo).
- Si intentas ejecutarlo más veces dentro de la misma semana, lo detecta y se cancela automáticamente.

---

## 🔒 Seguridad y privacidad
- Las contraseñas, claves de API y datos sensibles **no están dentro del código**.  
  Se guardan en el archivo `.env`, que **no debe compartirse**.
- No envía datos a ningún sitio externo salvo a OpenAI (para generar el texto) y tu servidor de correo (para notificarte).

---

## 🧾 En resumen

| Acción | Descripción |
|--------|--------------|
| 📚 Leer categorías, subcategorías y tags | Para saber de qué temas puede escribir |
| 🔍 Buscar un tag sin artículo publicado | Para elegir un tema nuevo |
| ✍️ Generar artículo con IA | Escribe título, resumen y cuerpo en HTML |
| 🚫 Evitar repeticiones | No repite tags ni títulos similares |
| 💾 Guardar en MongoDB | Publica directamente el nuevo artículo |
| 📧 Notificar por correo | Te informa de todo lo que ha hecho |

---

## 🌟 Ejemplo de funcionamiento real

1. Lunes por la mañana se ejecuta el script.
2. Detecta que no hay artículos esta semana.
3. Encuentra el tag `@Data` sin artículos.
4. Pide a la IA un artículo sobre “Uso de @Data en Lombok”.
5. Lo publica con el usuario “adminUser”.
6. Te manda un email:
   > ✅ Artículo publicado: “Cómo simplificar tu código con @Data en Lombok”.

La próxima vez que se ejecute esa misma semana, verá que ya hay uno publicado y **no hará nada más**.
