# Estrategia de Ingesta Óptima para RAG Factory

## 📊 Análisis de Limitaciones

### Chile BCN (datos.bcn.cl)

**Rate Limits**:
- ❓ **DESCONOCIDO** - No documentado públicamente
- 🔍 Endpoint SPARQL es servicio público del gobierno
- ⚠️ Probablemente tiene límites para prevenir abuso
- 📝 Recomendación: **Asumir conservador: ~100-500 requests/día**

**Características de Datos**:
- 📄 Tamaño promedio: ~900 caracteres por documento
- ⚡ Velocidad: ~5-6 segundos por documento (SPARQL + XML fetch)
- ✅ Manejable para Ollama (no causa timeouts)

**Riesgos**:
- 🚫 Bloqueo de IP si excedemos límites
- ⏱️ Servicio gubernamental puede ser lento en horas pico
- 🔄 XMLs antiguos pueden fallar o no tener contenido

### USA Congress.gov API

**Rate Limits**:
- ✅ **5,000 requests/día** con DEMO_KEY (documentado)
- 📧 Con API key registrada: **5,000-10,000/día** (más estable)
- ⏱️ Recomiendan no exceder 1 request/segundo

**Características de Datos**:
- 📄 Tamaño variable: 2,000 - 9,700 caracteres por bill
- ⚡ Velocidad: ~10-15 segundos por documento (API + XML download)
- ⚠️ Bills largos (>5,000 chars) causan timeouts en Ollama

**Riesgos**:
- 💥 Worker timeout con bills muy largos
- 📊 Algunos bills no tienen texto disponible (solo metadata)
- 🔄 Rate limiting si no respetamos delays

### Ollama (Local - Embeddings)

**Limitaciones**:
- ⏱️ **Timeout actual**: 60 segundos
- 💾 **Memoria**: ~700MB en reposo, picos de 2-3GB con textos largos
- 🔥 **CPU**: 100% durante generación de embeddings
- ⚠️ **Crítico**: Textos >5,000 chars pueden causar timeout o crash

**Performance**:
- ✅ Texto corto (<1,000 chars): ~2-3 segundos
- 🟡 Texto medio (1,000-3,000 chars): ~5-10 segundos
- 🔴 Texto largo (>5,000 chars): ~15-60+ segundos (riesgo de timeout)

## 🎯 Estrategia Óptima Propuesta

### Opción 1: Enfoque Conservador y Confiable ⭐⭐⭐⭐⭐

**Para CHILE BCN**:
```yaml
Frecuencia: Cada 6 horas (4 syncs/día)
Límite por sync: 25 documentos
Total diario: ~100 documentos
Delay entre requests: 3 segundos
Timeout: 90 segundos por documento
```

**Justificación**:
- ✅ Bajo riesgo de rate limiting
- ✅ Documentos pequeños (~900 chars) → sin timeouts
- ✅ 100 docs/día es suficiente para mantenerse actualizado
- ✅ 6 horas permite 4 ventanas diarias

**Para USA CONGRESS**:
```yaml
Frecuencia: Cada 2 horas durante horas hábiles (8am-8pm = 7 syncs/día)
Límite por sync: 15 documentos
Total diario: ~105 documentos
Delay entre requests: 2 segundos
Timeout: 120 segundos por documento
Pre-filtro: Saltar bills >6,000 caracteres (ingestar solo después con chunking especial)
```

**Justificación**:
- ✅ Bien debajo del límite de 5,000/día
- ✅ Filtro evita timeouts de Ollama
- ✅ 105 bills/día cubre nueva legislación fácilmente
- ✅ Solo durante horas hábiles evita sobrecarga nocturna

### Opción 2: Enfoque Agresivo (Máximo Throughput) ⭐⭐⭐

**Para CHILE BCN**:
```yaml
Frecuencia: Cada 3 horas (8 syncs/día)
Límite por sync: 50 documentos
Total diario: ~400 documentos
```

**Para USA CONGRESS**:
```yaml
Frecuencia: Cada hora (24 syncs/día)
Límite por sync: 100 documentos
Total diario: ~2,400 documentos
```

**Riesgos**:
- ⚠️ Chile: Posible rate limiting
- ⚠️ Ollama: Sobrecarga continua
- ⚠️ Ventiladores constantemente activos

### Opción 3: Enfoque Híbrido (Recomendado) ⭐⭐⭐⭐⭐

**Lógica**:
1. **Primera ingesta completa**: Hacer una sola vez, límite de 500 docs por fuente
2. **Syncs incrementales**: Solo documentos nuevos desde última sync
3. **Horarios inteligentes**: Diferentes para cada fuente

**Schedule sugerido**:

```
Chile BCN (conservador):
- Lunes-Viernes: 9am, 3pm, 9pm (3 syncs/día)
- Sábado-Domingo: 12pm (1 sync/día)
- Límite: 30 docs/sync
- Total: ~90 docs/día laborable, ~30 docs/día fin de semana

USA Congress (agresivo en días laborables):
- Lunes-Viernes: 9am, 12pm, 3pm, 6pm, 9pm (5 syncs/día)
- Sábado-Domingo: Solo si hay actividad legislativa
- Límite: 20 docs/sync
- Total: ~100 docs/día laborable
```

## 🛠️ Soluciones Técnicas Necesarias

### 1. Chunking Inteligente para Documentos Largos

**Problema**: USA Congress bills de 9,700 chars causan timeout

**Solución**:
```python
def smart_chunking(document, max_chunk_size=2000):
    """
    Si documento > 5000 chars:
    - Dividir en chunks de 2000 chars con 200 overlap
    - Generar embeddings para cada chunk por separado
    - Procesar en lotes pequeños (5 chunks a la vez)
    """
    if len(document['content']) > 5000:
        chunks = split_into_chunks(document, size=2000, overlap=200)
        # Procesar chunks en batches
        for batch in batched(chunks, batch_size=5):
            process_batch_with_delay(batch, delay=2)
    else:
        # Documento normal, procesar directamente
        process_document(document)
```

### 2. Configuración de Sync Schedules por Source

**Schema update necesario**:
```sql
ALTER TABLE data_sources ADD COLUMN sync_schedule JSONB;

-- Ejemplo de schedule:
{
  "enabled": true,
  "frequency": "custom",
  "schedule": {
    "monday": ["09:00", "15:00", "21:00"],
    "tuesday": ["09:00", "15:00", "21:00"],
    "wednesday": ["09:00", "15:00", "21:00"],
    "thursday": ["09:00", "15:00", "21:00"],
    "friday": ["09:00", "15:00", "21:00"],
    "saturday": ["12:00"],
    "sunday": ["12:00"]
  },
  "max_docs_per_sync": 30,
  "delay_between_requests": 3
}
```

### 3. Worker Timeout y Retry Logic

**Worker updates**:
```python
# Aumentar timeout del worker
worker_timeout = 300  # 5 minutos

# Retry logic para documentos que fallan
@retry(max_attempts=2, backoff=exponential)
def process_document_with_retry(doc):
    try:
        return process_document(doc)
    except TimeoutError:
        # Si es documento largo, intentar con chunking
        if len(doc['content']) > 5000:
            return process_with_smart_chunking(doc)
        raise
```

### 4. Incremental Sync (Solo Nuevos Documentos)

**Lógica**:
```python
def incremental_sync(source_id, last_sync_timestamp):
    """
    - Chile: Filtrar por publishDate > last_sync
    - USA: Filtrar por updateDate > last_sync
    - Evita re-procesar documentos existentes
    - Reduce carga significativamente después de primera ingesta
    """
    if source_type == 'chile_fulltext':
        query_filter = f"?publishDate > '{last_sync_timestamp}'"
    elif source_type == 'congress_api':
        params = {'updateDate[gte]': last_sync_timestamp}

    new_docs = fetch_with_filter(query_filter)
    return new_docs
```

## 📋 Plan de Implementación Prioritario

### Fase 1: Fixes Críticos (HOY) ⚡
1. ✅ Aumentar worker timeout a 180 segundos
2. ✅ Implementar smart chunking para docs >5,000 chars
3. ✅ Añadir delay configurable entre requests

### Fase 2: Scheduling Flexible (MAÑANA) 📅
4. ⬜ Añadir campo `sync_schedule` a data_sources table
5. ⬜ Crear scheduler service (puede usar APScheduler o cron jobs)
6. ⬜ UI para configurar schedules por source

### Fase 3: Optimizaciones (PRÓXIMA SEMANA) 🚀
7. ⬜ Implementar incremental sync
8. ⬜ Añadir métricas de performance (tiempo/doc, errores, etc.)
9. ⬜ Dashboard de sync status

## 🎯 Recomendación Final

**Para empezar HOY**:

1. **Chile BCN**:
   - Configurar manualmente 3 syncs/día (9am, 3pm, 9pm)
   - 25-30 documentos por sync
   - Total: ~75-90 docs/día

2. **USA Congress**:
   - Configurar manualmente 2 syncs/día (10am, 4pm)
   - 15-20 documentos por sync con filtro <6,000 chars
   - Total: ~30-40 docs/día

3. **Implementar**:
   - Smart chunking (Fase 1.2)
   - Aumentar worker timeout (Fase 1.1)

**Ventajas**:
- ✅ Evita rate limiting completamente
- ✅ No sobrecarga Ollama
- ✅ ~120 documentos/día es suficiente para mantenerse actualizado
- ✅ Permite iterar y mejorar sin romper nada

**Después** de validar que funciona bien por 1 semana, podemos:
- Aumentar frecuencia gradualmente
- Implementar scheduling automático
- Añadir más fuentes de datos

---

¿Qué opinas? ¿Empezamos con la implementación de Fase 1 (fixes críticos)?
