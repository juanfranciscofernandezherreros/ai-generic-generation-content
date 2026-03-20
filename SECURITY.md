# Política de seguridad

## Versiones con soporte

Las correcciones de seguridad se aplican sobre el código más reciente de la rama `master`.

## Información sensible en este proyecto

Este proyecto maneja las siguientes credenciales y datos sensibles. **Nunca deben incluirse en el código fuente ni en el control de versiones:**

| Variable | Descripción |
|---|---|
| `OPENAIAPIKEY` | Clave de API de OpenAI (`sk-...`) |
| `GEMINI_API_KEY` | Clave de API de Google Gemini |
| `SMTP_PASS` | Contraseña del servidor SMTP (o contraseña de aplicación de Gmail) |
| `SMTP_USER` | Usuario del servidor SMTP |

Todas estas variables deben configurarse en el fichero **`.env`** local (nunca commiteado) o mediante un gestor de secretos.

### Buenas prácticas de gestión de credenciales

- En **Kubernetes**: usa [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) (ver `k8s/secret.yaml`). Considera cifrarlos con [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) o [External Secrets Operator](https://external-secrets.io/).
- En **Google Cloud**: usa [Secret Manager](https://cloud.google.com/secret-manager) para almacenar y rotar credenciales de forma segura.
- En **CI/CD**: usa las variables de entorno cifradas de tu plataforma (GitHub Actions Secrets, GitLab CI Variables, etc.).
- **Nunca** incluyas credenciales reales en ficheros YAML, Dockerfiles, ni en el histórico de Git.

## Cómo reportar una vulnerabilidad

Por favor, reporta las vulnerabilidades de seguridad de forma **privada**.

- **No** abras un Issue público en GitHub para reportar vulnerabilidades de seguridad.
- Contacto: **security@example.com** *(dirección de ejemplo — placeholder; sustituir por el contacto real del mantenedor)*

Incluye en tu reporte:
- Descripción del problema y su impacto potencial
- Pasos para reproducirlo (prueba de concepto si es posible)
- Versiones afectadas / SHA del commit
- Posible remediación sugerida

## Tiempos de respuesta (según disponibilidad)

- **Acuse de recibo:** en un plazo de 7 días
- **Actualización de estado:** en un plazo de 14 días
- **Corrección / publicación:** en el menor tiempo razonablemente posible

