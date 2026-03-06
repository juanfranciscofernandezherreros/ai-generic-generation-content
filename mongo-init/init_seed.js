// mongo-init/init_seed.js
// ────────────────────────────────────────────────────────────────────────────
// Script de inicialización de MongoDB.
// Se ejecuta automáticamente la PRIMERA VEZ que se crea el contenedor
// (cuando el volumen mongo_data está vacío).
//
// Siembra categorías, subcategorías y tags predefinidos sobre:
//   · Spring Boot
//   · Data & Persistencia
//   · Inteligencia Artificial
//
// Nota: Este script corre con privilegios de root (initdb), por lo que no
// necesita autenticación adicional.
// ────────────────────────────────────────────────────────────────────────────

const DB_NAME       = "blogdb";
const CAT_COLL      = "categories";
const TAGS_COLL     = "tags";
const USERS_COLL    = "users";
const AUTHOR_USER   = "adminUser";

const db = db.getSiblingDB(DB_NAME);
const now = new Date();

// ─── helper: upsert por nombre ────────────────────────────────────────────────
function upsertByName(coll, doc) {
    const result = coll.findOneAndUpdate(
        { name: doc.name },
        { $setOnInsert: { _id: new ObjectId() }, $set: doc },
        { upsert: true, returnDocument: "after" }
    );
    return result._id;
}

// ─── usuario admin ────────────────────────────────────────────────────────────
db[USERS_COLL].updateOne(
    { username: AUTHOR_USER },
    {
        $setOnInsert: {
            _id: new ObjectId(),
            username: AUTHOR_USER,
            email: AUTHOR_USER + "@example.com",
            role: "admin",
            createdAt: now,
            updatedAt: now,
        }
    },
    { upsert: true }
);
print("✅ Usuario '" + AUTHOR_USER + "' listo.");

// ─── taxonomía ────────────────────────────────────────────────────────────────
const TAXONOMY = [
    {
        name: "Spring Boot",
        description: "Desarrollo de aplicaciones Java con el framework Spring Boot.",
        subcategories: [
            {
                name: "Spring Boot Core",
                description: "Fundamentos y configuración automática de Spring Boot.",
                tags: [
                    "@SpringBootApplication", "Auto-configuration", "Spring Profiles",
                    "application.yml", "application.properties", "CommandLineRunner",
                    "@ConditionalOnProperty", "Embedded Tomcat",
                    "Spring Boot Actuator", "Spring Boot DevTools",
                ],
            },
            {
                name: "Spring Security",
                description: "Autenticación y autorización con Spring Security.",
                tags: [
                    "JWT Authentication", "OAuth2 y OpenID Connect",
                    "Spring Security Filter Chain", "@PreAuthorize", "@Secured",
                    "CORS Configuration", "CSRF Protection",
                    "UserDetailsService", "BCryptPasswordEncoder", "Method Security",
                ],
            },
            {
                name: "Spring Data JPA",
                description: "Persistencia de datos con Spring Data JPA e Hibernate.",
                tags: [
                    "@Entity y @Table", "JpaRepository", "@Query personalizada",
                    "@Transactional", "@OneToMany y @ManyToOne",
                    "Paginación con Pageable", "Criteria API", "Projections y DTOs",
                    "@ManyToMany", "Spring Data Specifications",
                ],
            },
            {
                name: "Spring MVC REST",
                description: "Creación de APIs REST con Spring MVC.",
                tags: [
                    "@RestController", "@GetMapping y @PostMapping",
                    "@RequestBody y @ResponseBody", "@PathVariable y @RequestParam",
                    "ResponseEntity", "@ControllerAdvice", "@Valid y Bean Validation",
                    "HATEOAS", "OpenAPI y Swagger", "Content Negotiation",
                ],
            },
            {
                name: "Spring Boot Testing",
                description: "Pruebas de integración y unitarias en Spring Boot.",
                tags: [
                    "@SpringBootTest", "@WebMvcTest", "@DataJpaTest",
                    "@MockBean y Mockito", "Testcontainers", "@ParameterizedTest",
                    "MockMvc", "WireMock", "@TestConfiguration", "JUnit 5 con Spring",
                ],
            },
            {
                name: "Lombok",
                description: "Reducción de código boilerplate Java con Lombok.",
                tags: [
                    "@Data", "@Builder", "@NoArgsConstructor y @AllArgsConstructor",
                    "@Getter y @Setter", "@Slf4j", "@Value",
                    "@RequiredArgsConstructor", "@EqualsAndHashCode",
                    "@ToString", "@SuperBuilder",
                ],
            },
        ],
    },
    {
        name: "Data & Persistencia",
        description: "Gestión y persistencia de datos en aplicaciones Java.",
        subcategories: [
            {
                name: "JPA e Hibernate",
                description: "Mapeo objeto-relacional con JPA e Hibernate.",
                tags: [
                    "Hibernate Caching L1 y L2", "Problema N+1 y soluciones",
                    "FetchType LAZY vs EAGER", "Inheritance Strategies",
                    "Native Queries", "HQL (Hibernate Query Language)",
                    "@Embeddable y @Embedded", "@MappedSuperclass",
                    "Hibernate Envers (auditoría)", "Connection Pooling HikariCP",
                ],
            },
            {
                name: "Bases de Datos SQL",
                description: "Integración de Spring Boot con bases de datos relacionales.",
                tags: [
                    "PostgreSQL con Spring Boot", "MySQL con Spring Boot",
                    "H2 Database (testing)", "Índices y optimización SQL",
                    "Stored Procedures con JPA", "Spring JDBC Template",
                    "Transacciones distribuidas", "Multi-datasource en Spring Boot",
                    "QueryDSL", "jOOQ con Spring Boot",
                ],
            },
            {
                name: "NoSQL y MongoDB",
                description: "Bases de datos NoSQL con Spring Boot.",
                tags: [
                    "Spring Data MongoDB", "@Document y @Field", "MongoRepository",
                    "Aggregation Pipeline con Spring", "Spring Data Redis",
                    "Caché con Redis y Spring", "Spring Data Elasticsearch",
                    "Cassandra con Spring Boot", "@DBRef en MongoDB",
                    "GridFS con Spring",
                ],
            },
            {
                name: "Migraciones de Esquema",
                description: "Versionado y migración de esquemas de base de datos.",
                tags: [
                    "Flyway con Spring Boot", "Liquibase con Spring Boot",
                    "Versionado de migraciones SQL", "Rollback con Flyway",
                    "Baseline en Flyway", "Checksum en Liquibase",
                    "Migraciones en entornos CI/CD", "Flyway Callbacks",
                ],
            },
        ],
    },
    {
        name: "Inteligencia Artificial",
        description: "Integración de IA y Machine Learning con Java y Spring.",
        subcategories: [
            {
                name: "Spring AI",
                description: "Integración nativa de modelos de IA con Spring AI.",
                tags: [
                    "Spring AI Overview", "ChatClient con Spring AI",
                    "Prompt Templates en Spring AI", "Function Calling con Spring AI",
                    "Spring AI y Ollama", "Spring AI Advisors",
                    "Spring AI con OpenAI", "Spring AI con Azure OpenAI",
                    "Spring AI con Mistral", "Multimodalidad en Spring AI",
                ],
            },
            {
                name: "LLMs y Modelos de Lenguaje",
                description: "Uso de grandes modelos de lenguaje (LLMs) en aplicaciones Java.",
                tags: [
                    "OpenAI API con Java", "GPT-4 y modelos avanzados",
                    "Tokens y Context Window", "Streaming de respuestas LLM",
                    "Fine-tuning de modelos", "Prompt Engineering avanzado",
                    "Chain of Thought (CoT)", "Few-shot Learning",
                    "LangChain4j", "Integración con Hugging Face",
                ],
            },
            {
                name: "Machine Learning con Java",
                description: "Algoritmos y frameworks de ML para aplicaciones Java.",
                tags: [
                    "Deeplearning4j", "Weka con Java", "ONNX Runtime en Java",
                    "TensorFlow Java", "Tribuo (Oracle ML)", "Clasificación con Smile",
                    "Regresión lineal en Java", "Árboles de decisión en Java",
                    "Cross-validation en Java", "Pipeline de datos ML en Java",
                ],
            },
            {
                name: "Vector Databases y RAG",
                description: "Búsqueda semántica, embeddings y generación aumentada por recuperación (RAG).",
                tags: [
                    "Embeddings con Spring AI", "Pinecone con Java",
                    "Qdrant con Spring AI", "RAG (Retrieval Augmented Generation)",
                    "Chroma DB con Spring", "Búsqueda semántica",
                    "VectorStore en Spring AI", "pgvector con Spring Boot",
                    "Weaviate con Spring", "Milvus con Java",
                ],
            },
        ],
    },
];

// ─── seed loop ────────────────────────────────────────────────────────────────
let totalCats = 0;
let totalTags = 0;

TAXONOMY.forEach(function(parentDef) {
    const parentDoc = {
        name:        parentDef.name,
        description: parentDef.description || "",
        parent:      null,
        createdAt:   now,
        updatedAt:   now,
    };
    const parentId = upsertByName(db[CAT_COLL], parentDoc);
    totalCats++;
    print("  [parent] " + parentDef.name + " → " + parentId);

    (parentDef.subcategories || []).forEach(function(subDef) {
        const subDoc = {
            name:             subDef.name,
            description:      subDef.description || "",
            parent:           parentId,
            parentName:       parentDef.name,
            createdAt:        now,
            updatedAt:        now,
        };
        const subId = upsertByName(db[CAT_COLL], subDoc);
        totalCats++;
        print("    [subcat] " + subDef.name + " → " + subId);

        const tagIds = [];
        (subDef.tags || []).forEach(function(tagName) {
            const tagDoc = {
                name:               tagName,
                tag:                tagName,
                categoryId:         subId,
                categoryName:       subDef.name,
                parentCategoryId:   parentId,
                parentCategoryName: parentDef.name,
                createdAt:          now,
                updatedAt:          now,
            };
            const tid = upsertByName(db[TAGS_COLL], tagDoc);
            tagIds.push(tid);
            totalTags++;
            print("      [tag] " + tagName + " → " + tid);
        });

        // Actualizar subcategoría con los IDs de sus tags
        if (tagIds.length > 0) {
            db[CAT_COLL].updateOne(
                { _id: subId },
                { $set: { tags: tagIds, updatedAt: now } }
            );
        }
    });
});

print("");
print("========================================");
print("✅ Seed completado:");
print("   Categorías/subcategorías: " + totalCats);
print("   Tags:                     " + totalTags);
print("========================================");
