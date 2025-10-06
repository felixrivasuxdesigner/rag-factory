# 🎨 Cómo Usar el Frontend de RAG Factory

Guía paso a paso para usar la interfaz web y probar el sistema RAG completo.

---

## 🚀 Inicio Rápido

### 1. Iniciar el Sistema
```bash
cd /Users/felixrivas/Projects/vector-doc-ingestion
docker-compose -f docker/docker-compose.yml up -d
```

### 2. Verificar que Todo Esté Corriendo
```bash
curl http://localhost:8000/health | jq
```

**Esperado:**
```json
{
  "api": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "ollama": "healthy"
}
```

### 3. Abrir el Frontend
Navega a: **http://localhost:3000**

---

## 📋 Interfaz del Frontend

### Sección 1: System Health
Muestra el estado de:
- ✅ API (FastAPI backend)
- ✅ Database (PostgreSQL)
- ✅ Redis (Queue)
- ✅ Ollama (AI Models)

### Sección 2: RAG Projects
Lista de proyectos RAG disponibles:
- **Chilean Legal Norms** (Normas chilenas)
- **US Congress Bills** (Legislación USA)

**Acciones:**
- 🔄 Refresh - Actualizar lista
- ➕ New Project - Crear nuevo proyecto
- ✏️ Edit - Editar proyecto
- 🗑️ Delete - Eliminar proyecto

---

## 🎯 Usar el Panel de Búsqueda y RAG

### Paso 1: Seleccionar un Proyecto
Click en un proyecto de la lista para expandirlo.

### Paso 2: Ver el Panel Search/RAG
Cuando seleccionas un proyecto, aparece **arriba** un panel morado/azul con el título:
```
🔍 Semantic Search
```
o
```
✨ RAG Query
```

### Paso 3: Elegir el Modo

El panel tiene un **toggle** arriba a la derecha con dos opciones:

#### 🔍 **Modo SEARCH** (Búsqueda Semántica)
- Busca documentos similares usando embeddings
- NO genera respuestas con IA
- Solo muestra los documentos más relevantes
- Más rápido
- Útil para explorar qué documentos existen

**Ejemplo de uso:**
```
Query: "firearm legislation"

Resultados:
• [75%] Constitutional Concealed Carry...
• [68%] Firearm Due Process Protection...
• [62%] NICS Data Reporting Act...
```

#### ✨ **Modo ASK AI** (RAG con IA)
- Busca documentos relevantes
- Usa Gemma 3 para generar una respuesta
- Cita las fuentes usadas
- Más lento (~5-15 segundos)
- Útil para obtener respuestas específicas

**Ejemplo de uso:**
```
Question: "What is the Constitutional Concealed Carry Act about?"

AI Answer:
"The Constitutional Concealed Carry Reciprocity Act of 2025
is a bill that promotes constitutional concealed carry
reciprocity."

Sources Used:
• [80%] Constitutional Concealed Carry Reciprocity Act...
```

---

## 🎮 Tutorial Paso a Paso

### Ejemplo 1: Búsqueda Simple

1. **Selecciona** el proyecto "US Congress Bills"
2. **Click** en el toggle para modo **Search** 🔍
3. **Escribe:** `firearm`
4. **Click** en "Search"
5. **Observa:**
   - Número de resultados encontrados
   - % de similitud de cada documento
   - Contenido preview de cada resultado

### Ejemplo 2: Pregunta con IA

1. **Selecciona** el proyecto "US Congress Bills"
2. **Click** en el toggle para modo **Ask AI** ✨
3. **Escribe:** `What is the Constitutional Concealed Carry Reciprocity Act?`
4. **Click** en "Ask"
5. **Espera** ~10 segundos (se ve spinner 🔄)
6. **Observa:**
   - **Answer** (generada por Gemma 3)
   - **Sources** (documentos usados)
   - **% de similitud** de cada fuente

### Ejemplo 3: Búsqueda en Español (Chile)

1. **Selecciona** el proyecto "Chilean Legal Norms"
2. **Modo** Ask AI ✨
3. **Escribe:** `What regulations exist about fuel security?`
4. **Click** en "Ask"
5. **Observa** la respuesta y fuentes chilenas

---

## 🔧 Crear un Nuevo Proyecto

### Paso 1: Click en "New Project"
Botón verde con "➕ New Project"

### Paso 2: Llenar Formulario

**Información Básica:**
- **Project Name**: Ej. "California Laws"
- **Description**: Opcional

**Vector Database Config:**
Para testing, usa estos valores:
- **Host**: `db` (dentro de Docker)
- **Port**: `5432`
- **Database**: `rag_factory_db`
- **User**: `user`
- **Password**: `password`
- **Table Name**: `mi_tabla_vectores` (único para cada proyecto)

### Paso 3: Click "Create Project"

---

## 📥 Agregar Data Source

### Paso 1: Expandir Proyecto
Click en el proyecto donde quieres agregar datos.

### Paso 2: Click "Add Data Source"
Botón verde abajo del proyecto.

### Paso 3: Elegir Tipo

#### Opción 1: SPARQL Endpoint
Para consultar bases de datos SPARQL (como BCN Chile):
```
Name: Chilean Norms
Type: SPARQL
Endpoint URL: https://datos.bcn.cl/sparql
SPARQL Query: [tu query]
Country Code: CL (opcional)
```

#### Opción 2: File Upload
Para subir documentos manualmente:
```
Name: My Documents
Type: File Upload
Documents: [paste JSON array]

Ejemplo:
[
  {
    "id": "doc1",
    "title": "Document Title",
    "content": "Document content here..."
  }
]
```

### Paso 4: Click "Create Source"

---

## ▶️ Ejecutar Ingestion Job

### Paso 1: En el Data Source
Verás un botón **"▶ Run Job"**

### Paso 2: Click en "Run Job"
El job se encola en Redis.

### Paso 3: Monitorear Progreso
Ve a **Project Stats** abajo:
```
Documents:
• Total: 5
• Completed: 5 ✓
• Failed: 0

Jobs:
• Total: 1
• Completed: 1
• Running: 0
```

### Paso 4: Esperar
El worker procesa:
1. Fetch documentos
2. Deduplica por hash
3. Genera embeddings (Ollama)
4. Guarda vectores en PostgreSQL

**Tiempo:** ~1-2 segundos por documento

---

## 🎨 Características de la UI

### Visual Indicators
- ✅ **Verde** - Healthy, Active, Completed
- 🔴 **Rojo** - Unhealthy, Failed
- 🟡 **Amarillo** - Warning
- 🔵 **Azul** - Info

### Badges de Similitud
Los resultados muestran badges de porcentaje:
```
[80%] ← Muy relevante
[60%] ← Relevante
[40%] ← Poco relevante
```

### Loading States
- **Spinner** 🔄 cuando está procesando
- **Disabled buttons** cuando está cargando

### Modals y Confirmaciones
- Modal para crear/editar proyecto
- Modal para agregar data source
- Confirmación antes de eliminar

---

## ⚙️ Configuración Avanzada

### Ajustar Parámetros de Búsqueda

En el código del componente `SearchPanel.tsx`, puedes modificar:

```typescript
// Número de resultados
top_k: 5  // Cambiar a 10 para más resultados

// Umbral de similitud
similarity_threshold: 0.3  // Reducir a 0.2 para más permisivo

// Tokens máximos en respuesta
max_tokens: 500  // Aumentar a 1000 para respuestas más largas

// Modelo de LLM
model: "gemma3:1b-it-qat"  // Cambiar a "gemma3:4b-it-qat"
```

---

## 🐛 Troubleshooting

### Problema: "No results found"
**Solución:**
- Reduce `similarity_threshold` a 0.2 o 0.1
- Usa términos más específicos de los documentos
- Verifica que hay documentos en el proyecto

### Problema: "Error fetching"
**Solución:**
- Verifica que el API esté corriendo: `docker logs api`
- Check health: `curl http://localhost:8000/health`

### Problema: Respuesta "I don't have enough information"
**Solución:**
- Normal cuando documentos son muy cortos (solo títulos)
- Ingesta documentos con contenido completo
- Reduce threshold de similitud

### Problema: Panel de búsqueda no aparece
**Solución:**
- Asegúrate de haber **seleccionado un proyecto** primero
- Refresh la página
- Check console del browser (F12)

---

## 📊 Monitoreo

### Ver Logs en Tiempo Real

```bash
# API logs
docker logs -f api

# Worker logs
docker logs -f rag-worker

# Frontend logs
docker logs -f frontend
```

### Verificar Base de Datos

```bash
# Conectar a PostgreSQL
docker exec -it rag-factory-db psql -U user -d rag_factory_db

# Ver proyectos
SELECT id, name, status FROM rag_projects;

# Ver documentos de un proyecto
SELECT COUNT(*) FROM chile_norms_vectors;

# Ver jobs
SELECT * FROM ingestion_jobs ORDER BY created_at DESC LIMIT 5;
```

---

## 🎓 Tips y Mejores Prácticas

### Para Búsquedas:
1. **Usa términos específicos** de los documentos
2. **Empieza con Search mode** para ver qué documentos hay
3. **Luego usa Ask AI** para respuestas elaboradas

### Para Proyectos:
1. **Usa tablas diferentes** para cada proyecto
2. **Nomenclatura clara**: `proyecto_descripcion_vectors`
3. **Organiza por tema o jurisdicción**

### Para Performance:
1. **Batch ingests**: Sube muchos docs a la vez
2. **Monitorea memoria** de Ollama
3. **Usa Gemma 1B** para velocidad, 4B para calidad

---

## 🚀 Próximos Pasos

1. **Prueba con tus propios datos**
2. **Experimenta con diferentes preguntas**
3. **Ajusta parámetros** de búsqueda
4. **Descarga Gemma 3 4B** para mejores respuestas:
   ```bash
   docker exec ollama ollama pull gemma3:4b-it-qat
   ```

---

**¡Disfruta explorando RAG Factory!** 🎉
