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

- Ejecuta todos los tests antes de enviar un PR:
  ```bash
  pip install pytest
  python -m pytest test_generateArticle.py test_seed_data.py -v
  ```
- Añade tests para cualquier función nueva o modificada.

---

## 📝 Estilo de código

- Escribe en **Python 3.10+**.
- Usa **docstrings** en funciones públicas.
- Sigue las convenciones existentes del proyecto.

---

## 📂 Estructura de archivos

```
├── generateArticle.py       # Script principal (CLI, sin MongoDB)
├── seed_data.py             # Referencia de categorías/tags disponibles
├── test_generateArticle.py  # Tests del script principal
├── test_seed_data.py        # Tests de la referencia de datos
├── README.md                # Documentación principal (¡siempre actualizar!)
├── ARTICLE_GENERATION.md    # Documentación técnica detallada
├── CONTRIBUTING.md          # Esta guía
├── docs/screenshots/        # Screenshots del proyecto
├── k8s/                     # Manifiestos Kubernetes
├── gcloud/                  # Ficheros Google Cloud
└── .env.example             # Plantilla de variables de entorno
```
