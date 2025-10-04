# Next Steps for RAG Factory

## Current Status (Actualizado: 2025-10-03)
✅ MVP Backend completado y funcionando
✅ Infraestructura Docker configurada (PostgreSQL:5433, Redis:6380, Ollama:11434, API:8000)
✅ Base de datos inicializada con schema completo
✅ API respondiendo correctamente en http://localhost:8000
✅ Health check pasando: API, Database, Redis, Ollama
✅ **Backend completamente probado y funcionando**
✅ **Pipeline de ingesta funcionando end-to-end**
✅ **pgvector habilitado y vectores almacenados correctamente**
✅ **Modelo mxbai-embed-large (1024 dims) descargado en contenedor Ollama**

### Tests Backend Completados ✅
- ✅ Ejecutar test completo del backend
- ✅ Crear proyecto de prueba (ID: 3 - "Test Project")
- ✅ Agregar fuente de datos file_upload con 3 documentos
- ✅ Ejecutar job de ingesta (Job ID: 7 - 3/3 documentos exitosos)
- ✅ Verificar vectores en base de datos (tabla test_vectors con 3 vectores)
- ✅ Validar deduplicación por hash SHA-256
- ✅ Validar tracking de documentos en BD interna

### Correcciones Aplicadas
- ✅ Fixed: Importaciones relativas → absolutas en ingestion_tasks.py
- ✅ Fixed: RQ enqueue call con argumentos posicionales
- ✅ Added: Soporte para source_type 'file_upload'
- ✅ Commit: `05d1ad9` - Backend fixes and testing complete

## Pendiente para próxima sesión

### 1. Búsqueda de Similitud (Opcional)
- [ ] Implementar endpoint de búsqueda semántica
- [ ] Probar consultas de similitud con vectores almacenados

### 2. Frontend
- [ ] Arreglar problema de Node.js version (requiere 20.19+, actual 18.20.8)
  - Opción 1: Actualizar Node en Dockerfile frontend
  - Opción 2: Degradar versión de Vite
- [ ] Levantar frontend en http://localhost:3000
- [ ] Conectar con API backend
- [ ] Probar flujo completo desde UI

### 3. Documentación
- [ ] Actualizar README con instrucciones de uso
- [ ] Documentar ejemplos de uso con curl
- [ ] Agregar troubleshooting común

## Comandos útiles

### Iniciar servicios
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Ver logs
```bash
docker logs api
docker logs rag-worker
docker logs rag-factory-db
```

### Ejecutar tests
```bash
python3 test_api.py
```

### Verificar health
```bash
curl http://localhost:8000/health | jq
```

## Notas importantes
- PostgreSQL RAG Factory en puerto **5433** (no 5432)
- Redis en puerto **6380** (no 6379)
- Credenciales DB: user=`user`, password=`password`, db=`rag_factory_db`
- **NO usar infraestructura de JourneyLaw** - todo separado
- **Docker aislamiento**: Cada contenedor tiene su propio filesystem y almacenamiento
  - Ollama en Docker ≠ Ollama local (modelos separados)
  - Los modelos deben descargarse dentro del contenedor: `docker exec ollama ollama pull model-name`
- **Arquitectura actual**: Todo autocontenido en Docker Compose
  - Base de datos interna para tracking (rag_factory_db)
  - Base de datos del usuario para vectores (configurable por proyecto)
  - En tests: ambas apuntan a la misma BD pero con tablas diferentes

## Aprendizajes de Docker
- ✅ Cada contenedor es un universo aislado
- ✅ Puedes replicar esta arquitectura para otros proyectos (JourneyLaw, ProFactura)
- ✅ No contamina el sistema local
- ✅ Reproducible en cualquier máquina
- ✅ Portabilidad completa del stack
