# Spring Boot Article Generator

Este repositorio contiene un **starter de Spring Boot** para generar artículos técnicos con IA y metadatos SEO.

## ¿Qué incluye?

- `springboot-article-generator/`: librería `article-generator-spring-boot-starter` con autoconfiguración.
- Servicio principal listo para inyectar: `ArticleGeneratorService`.
- Soporte de proveedores IA:
  - **OpenAI**
  - **Google Gemini**
  - **Ollama** (local)

## Requisitos

- Java 17+
- Maven 3.9+
- Spring Boot 3.x en el proyecto consumidor

## Build y tests del starter

```bash
cd springboot-article-generator
mvn test
```

---

## ¿Puedo usarlo sin integrarlo en ningún sitio?

Este repositorio publica un **starter/librería**, no una aplicación ejecutable completa.

- ✅ Sí puedes usarlo en un proyecto nuevo y mínimo de Spring Boot (aunque sea solo para probar).
- ❌ No hay un modo `standalone` tipo CLI en este repositorio para ejecutarlo “tal cual” sin proyecto consumidor.

Si quieres probarlo rápido, crea un proyecto Spring Boot vacío, añade la dependencia del starter y expón un endpoint como en el ejemplo de abajo.

---

## Cómo usarlo en **otro proyecto Spring Boot**

### 1) Instalar el starter localmente (si aún no está publicado en tu repositorio Maven)

Desde este repositorio:

```bash
cd springboot-article-generator
mvn clean install
```

Esto dejará el artefacto en tu repositorio local (`~/.m2/repository`).

### 2) Agregar dependencia en tu proyecto Spring Boot

En el `pom.xml` del **otro proyecto**:

```xml
<dependency>
    <groupId>com.github.juanfernandez</groupId>
    <artifactId>article-generator-spring-boot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 3) Configurar propiedades

En `application.yml` (recomendado):

```yaml
article-generator:
  provider: openai # openai | gemini | ollama
  model: gpt-4o
  openai-api-key: ${OPENAIAPIKEY}
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

> Puedes cambiar `provider` y credenciales según el proveedor.

#### Ejemplo con Gemini

```yaml
article-generator:
  provider: gemini
  model: gemini-2.0-flash
  gemini-api-key: ${GEMINI_API_KEY}
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Ejemplo con Ollama

```yaml
article-generator:
  provider: ollama
  model: llama3
  ollama-base-url: http://localhost:11434
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

### 4) Inyectar y usar `ArticleGeneratorService`

```java
package com.example.demo.web;

import com.github.juanfernandez.article.model.Article;
import com.github.juanfernandez.article.model.ArticleRequest;
import com.github.juanfernandez.article.service.ArticleGeneratorService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    private final ArticleGeneratorService articleGeneratorService;

    public ArticleController(ArticleGeneratorService articleGeneratorService) {
        this.articleGeneratorService = articleGeneratorService;
    }

    @PostMapping("/generate")
    public Article generate(@RequestBody GenerateArticleInput input) {
        ArticleRequest request = ArticleRequest.builder()
                .category(input.category())
                .subcategory(input.subcategory())
                .tag(input.tag())
                .language(input.language())
                .site(input.site())
                .authorUsername(input.authorUsername())
                .avoidTitles(input.avoidTitles())
                .build();

        return articleGeneratorService.generateArticle(request);
    }

    public record GenerateArticleInput(
            String category,
            String subcategory,
            String tag,
            String language,
            String site,
            String authorUsername,
            List<String> avoidTitles
    ) {}
}
```

---

## Ejemplo de uso end-to-end

### Request

```bash
curl -X POST 'http://localhost:8080/api/articles/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "category": "Spring Boot",
    "subcategory": "Spring Security",
    "tag": "JWT Authentication",
    "language": "es",
    "site": "https://mi-blog.com",
    "authorUsername": "juan",
    "avoidTitles": [
      "Introducción a JWT",
      "JWT para principiantes"
    ]
  }'
```

### Respuesta (recortada)

```json
{
  "title": "Autenticación JWT en Spring Boot 3: guía práctica",
  "slug": "autenticacion-jwt-en-spring-boot-3-guia-practica",
  "summary": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "body": "<h1>Autenticación JWT en Spring Boot 3: guía práctica</h1>...",
  "category": "Spring Security",
  "tags": ["JWT Authentication"],
  "author": "juan",
  "status": "published",
  "isVisible": true,
  "keywords": ["jwt spring boot", "spring security", "token"],
  "metaTitle": "Autenticación JWT en Spring Boot 3: guía práctica",
  "metaDescription": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "canonicalUrl": "https://mi-blog.com/post/autenticacion-jwt-en-spring-boot-3-guia-practica",
  "ogTitle": "Autenticación JWT en Spring Boot 3: guía práctica",
  "ogDescription": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "ogType": "article",
  "wordCount": 1300,
  "readingTime": 7,
  "publishDate": "2026-03-24T14:00:00Z",
  "createdAt": "2026-03-24T14:00:00Z",
  "updatedAt": "2026-03-24T14:00:00Z",
  "generatedAt": "2026-03-24T14:00:00Z"
}
```

---

## Notas rápidas

- Campo obligatorio en `ArticleRequest`: `category`.
- Si no envías `subcategory`, usa `General`.
- Si no envías `language`, `site` o `authorUsername`, usa los valores de `application.yml`.
- El starter aplica deduplicación de títulos usando `avoidTitles`.
