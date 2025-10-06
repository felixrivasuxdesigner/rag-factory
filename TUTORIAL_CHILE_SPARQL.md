# 🇨🇱 Tutorial: Probar RAG Factory con SPARQL - Leyes Chilenas

Este tutorial te guía para crear un proyecto RAG usando el endpoint SPARQL de la **Biblioteca del Congreso Nacional de Chile** para ingestar normas y leyes chilenas.

## 🆚 Diferencia con el Tutorial de USA

| Aspecto | USA (Congress.gov) | Chile (BCN) |
|---------|-------------------|-------------|
| **Tecnología** | REST API | SPARQL Endpoint |
| **Formato** | JSON | RDF/SPARQL |
| **Datos** | Bills del Congreso | Normas/Leyes |
| **UI en RAG Factory** | File Upload | SPARQL Endpoint |

---

## Paso 1: Entender el Endpoint SPARQL (2 minutos)

### 📍 Endpoint
```
https://datos.bcn.cl/sparql
```

**Nota importante**:
- El endpoint real es `https://datos.bcn.cl/sparql`
- La URL `https://datos.bcn.cl/es/endpoint-sparql` es solo la página de documentación
- Al probar queries en la interfaz web de Virtuoso, **dejar el campo "Default Data Set Name (Graph IRI)" VACÍO**

### 📚 ¿Qué datos tiene?
- **Normas/Leyes**: LEY (Ley), DTO (Decreto), ORZ (Ordenanza)
- **Proyectos de Ley**: En tramitación
- **Documentos Legislativos**: Informes, mociones, mensajes
- **Metadata**: Ministerios, fechas, temas, autores

### 🔗 Ontología
- Prefijo: `bcnnorms` → Normas chilenas
- Prefijo: `dc` → Dublin Core (metadatos)
- URI Pattern: `cl/{tipo}/{org}/{fecha}/{numero}`

---

## Paso 2: Query SPARQL Diseñada (Lista para usar)

Esta query obtiene **10 normas chilenas** con toda la información relevante para RAG:

```sparql
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?norma
WHERE {
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
}
LIMIT 10
```

### 📝 ¿Qué obtiene esta query?

- `?norma` → URI del recurso (ej: `http://datos.bcn.cl/recurso/cl/ley/minjusticia/2024/21595`)
- `?id` → Identificador único (ej: "632434")
- `?title` → Título de la ley/norma

**Nota**: El prefijo de ontología es `http://` (no `https://`). Esta es la versión simplificada y verificada que funciona con el endpoint real.

---

## Paso 3: Crear Proyecto en RAG Factory (3 minutos)

1. Abre **http://localhost:3000**

2. Click **"+ New Project"**

3. Llena el formulario:

   **Básico**:
   - Project Name: `Chilean Legal Norms`
   - Description: `Normas y leyes de Chile vía SPARQL`

   **Vector Database** (misma DB interna):
   - Host: `db`
   - Port: `5432`
   - Database Name: `rag_factory_db`
   - User: `user`
   - Password: `password`
   - Vector Table Name: `chile_norms_vectors` ← **IMPORTANTE**

   **Embedding Model**:
   - Model: `mxbai-embed-large (1024 dims)`

4. Click **"Create Project"** ✅

---

## Paso 4: Crear Data Source con SPARQL (2 minutos)

1. Selecciona el proyecto `Chilean Legal Norms`

2. Click **"+ New Source"**

3. Llena el formulario:

   **Información Básica**:
   - Source Name: `BCN Normas - 2024`
   - Source Type: **`SPARQL Endpoint`** ← IMPORTANTE

   **Configuración SPARQL**:
   - SPARQL Endpoint URL: `https://datos.bcn.cl/sparql`

   - SPARQL Query: **Copia y pega esta query completa** ↓

```sparql
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?norma
WHERE {
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
}
LIMIT 10
```

   - Document Limit: `10`

   **Opcional** (metadata adicional):
   - Country Code: `CL`
   - Region: `Chile`

4. Click **"Create Source"** ✅

---

## Paso 5: Ejecutar Ingestion (1 minuto)

1. En **Data Sources**, verás tu source `BCN Normas - 2024`

2. Click **"▶ Run Ingestion"**

3. Espera ~15-30 segundos (SPARQL puede ser más lento que REST)

4. **Refresca la página** (F5)

5. Verifica **Project Statistics**:
   - ✅ Total Documents: 10
   - ✅ Documents Completed: 10
   - ✅ Jobs Completed: 1

---

## Paso 6: Verificar Vectores en Base de Datos (2 minutos)

Conecta a PostgreSQL:

```bash
docker exec rag-factory-db psql -U user -d rag_factory_db
```

### Queries de verificación:

```sql
-- Ver cuántos vectores tienes
SELECT COUNT(*) FROM chile_norms_vectors;
-- Debería mostrar: 10

-- Ver las primeras 3 normas
SELECT id, LEFT(content, 120) as preview
FROM chile_norms_vectors
LIMIT 3;

-- Ver metadata completa de una norma
SELECT id, metadata
FROM chile_norms_vectors
LIMIT 1;

-- Comparar con proyecto USA
SELECT
  'Chile' as source, COUNT(*) as total FROM chile_norms_vectors
UNION ALL
SELECT
  'USA' as source, COUNT(*) as total FROM congress_vectors;

-- Salir
\q
```

---

## Paso 7: Búsqueda Semántica Multi-Proyecto (5 minutos)

Ahora tienes **2 proyectos RAG** en la misma base de datos:
- `congress_vectors` (USA - 5 bills)
- `chile_norms_vectors` (Chile - 10 normas)

### Script Python para búsqueda en ambos:

```python
import requests
import psycopg2

# Generar embedding de la query
query = "What laws are about firearms and weapons?"

response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "mxbai-embed-large", "prompt": query}
)
embedding = response.json()['embedding']

# Conectar a la base de datos
conn = psycopg2.connect(
    host="localhost", port=5433, database="rag_factory_db",
    user="user", password="password"
)
cur = conn.cursor()

print(f"\n🔍 Query: {query}\n")
print("=" * 80)

# Buscar en USA Congress Bills
print("\n🇺🇸 USA CONGRESS BILLS:")
print("-" * 80)
cur.execute("""
    SELECT id, content, 1 - (embedding <=> %s::vector) as similarity
    FROM congress_vectors
    ORDER BY embedding <=> %s::vector
    LIMIT 3
""", (embedding, embedding))

for doc_id, content, sim in cur.fetchall():
    print(f"\n[{sim:.3f}] {doc_id}")
    print(content[:200])

# Buscar en Chilean Norms
print("\n\n🇨🇱 CHILEAN LEGAL NORMS:")
print("-" * 80)
cur.execute("""
    SELECT id, content, 1 - (embedding <=> %s::vector) as similarity
    FROM chile_norms_vectors
    ORDER BY embedding <=> %s::vector
    LIMIT 3
""", (embedding, embedding))

for doc_id, content, sim in cur.fetchall():
    print(f"\n[{sim:.3f}] {doc_id}")
    print(content[:200])

cur.close()
conn.close()
```

**Ejecuta**:
```bash
python3 query_multi_rag.py
```

---

## 🎯 Comparación: USA vs Chile

| Proyecto | Tecnología | Documentos | Tabla | País |
|----------|-----------|------------|-------|------|
| US Congress Bills | REST API | 5 bills | `congress_vectors` | 🇺🇸 |
| Chilean Legal Norms | SPARQL | 10 normas | `chile_norms_vectors` | 🇨🇱 |

**Ambos comparten**:
- ✅ Misma base de datos (`rag_factory_db`)
- ✅ Mismo modelo embeddings (mxbai-embed-large 1024d)
- ✅ Mismo sistema de deduplicación
- ✅ Misma infraestructura Docker

**Diferencias**:
- ❗ Fuente de datos (API REST vs SPARQL)
- ❗ Formato original (JSON vs RDF)
- ❗ Idioma (Inglés vs Español)

---

## 🚀 Expandir el Proyecto Chilean Norms

### Agregar más normas:

1. **Cambiar el LIMIT** en la query:
   ```sparql
   LIMIT 50  # En lugar de LIMIT 10
   ```

2. **Filtrar por tipo de norma**:
   ```sparql
   WHERE {
     ?norma rdf:type bcnnorms:Norm .
     ?norma dc:identifier ?id .
     ?norma dc:title ?titulo .
     ?norma bcnnorms:hasTipoNorma bcnnorms:LEY .  # Solo leyes
   }
   ```

3. **Filtrar por año**:
   ```sparql
   WHERE {
     ?norma rdf:type bcnnorms:Norm .
     ?norma dc:identifier ?id .
     ?norma dc:title ?titulo .
     ?norma dcterms:issued ?fecha .
     FILTER(YEAR(?fecha) = 2024)  # Solo 2024
   }
   ```

4. **Filtrar por ministerio**:
   ```sparql
   WHERE {
     ?norma rdf:type bcnnorms:Norm .
     ?norma dc:identifier ?id .
     ?norma dc:title ?titulo .
     ?norma bcnnorms:issuedBy ?org .
     ?org dc:title ?orgName .
     FILTER(CONTAINS(LCASE(?orgName), "justicia"))  # Ministerio de Justicia
   }
   ```

### Crear múltiples sources:

- **Source 1**: "Leyes 2024" → Solo LEY del 2024
- **Source 2**: "Decretos Educación" → Solo DTO de Ministerio de Educación
- **Source 3**: "Normas Ambientales" → Filtro por tema ambiental

RAG Factory **deduplicará automáticamente** cualquier norma repetida.

---

## 🔗 Recursos SPARQL de BCN

- **Endpoint**: https://datos.bcn.cl/es/endpoint-sparql
- **Documentación**: https://datos.bcn.cl/es/documentacion
- **Queries de ejemplo**: https://datos.bcn.cl/es/documentacion/consultas-sparql
- **Ontología Norms**: https://datos.bcn.cl/ontologies/bcn-norms/
- **Ontología Resources**: https://datos.bcn.cl/ontologies/bcn-resources/

---

## ✅ Checklist de Éxito

- [ ] Proyecto "Chilean Legal Norms" creado
- [ ] Source SPARQL configurada con endpoint BCN
- [ ] Query SPARQL pegada correctamente
- [ ] Ingestion completada (10 documentos)
- [ ] Tabla `chile_norms_vectors` verificada en DB
- [ ] Búsqueda semántica funcionando
- [ ] Comparación USA vs Chile probada

---

## 🆘 Troubleshooting

### Error: "SPARQL query timeout"
- El endpoint BCN puede ser lento
- Reduce el LIMIT de 10 a 5
- Simplifica la query (elimina OPTIONAL)

### Error: "No results from SPARQL"
- Verifica que la query tenga los prefijos correctos
- Prueba la query directamente en: https://datos.bcn.cl/es/endpoint-sparql
- Chequea que el endpoint esté disponible

### Solo 0 documentos procesados
- Ver logs: `docker-compose -f docker/docker-compose.yml logs worker -f`
- El worker muestra errores de parsing SPARQL
- Verifica sintaxis de la query (especialmente quotes)

### Embeddings muy lentos
- Ollama está generando 1024-dim vectors para 10 docs
- Tiempo esperado: 1-2 segundos por documento
- Total ~15-30 segundos para 10 normas

---

## 🎉 ¡Listo!

Ahora tienes un **sistema RAG multi-proyecto y multi-idioma**:
- 🇺🇸 Legislación de USA (REST API)
- 🇨🇱 Normas de Chile (SPARQL)

**Próximos pasos**:
1. Implementar búsqueda desde la UI
2. Agregar más países/fuentes
3. Integrar con LLM para Q&A
4. Crear API pública para queries

---

**¿Preguntas?** Revisa la documentación de BCN o el tutorial de USA para comparar.
