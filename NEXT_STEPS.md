# Next Steps for RAG Factory

## Current Status
✅ MVP Backend completado y funcionando
✅ Infraestructura Docker configurada (PostgreSQL:5433, Redis:6380, Ollama:11434, API:8000)
✅ Base de datos inicializada con schema completo
✅ API respondiendo correctamente en http://localhost:8000
✅ Health check pasando: API, Database, Redis, Ollama

## Pendiente para próxima sesión

### 1. Probar Backend Completo
- [ ] Ejecutar test completo: `python3 test_api.py`
- [ ] Crear proyecto de prueba
- [ ] Agregar fuente de datos (archivos locales)
- [ ] Ejecutar job de ingesta
- [ ] Verificar vectores en base de datos
- [ ] Probar búsqueda de similitud

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
