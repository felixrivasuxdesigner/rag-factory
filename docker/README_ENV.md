# Configuración de Variables de Entorno

## ⚡ Inicio Rápido

### 1. Edita el archivo `.env`

El archivo `.env` ya está creado en este directorio. Solo necesitas **reemplazar tu API key**:

```bash
# Abre el archivo con tu editor favorito:
nano .env
# o
code .env
# o
vim .env
```

### 2. Reemplaza el placeholder con tu API key

```bash
# ANTES:
GOOGLE_AI_API_KEY=your-api-key-here

# DESPUÉS:
GOOGLE_AI_API_KEY=AIzaSyAbc123...tu-key-real-aqui
```

### 3. Guarda y reinicia el contenedor API

```bash
docker-compose restart api
```

### 4. Verifica que Gemini se inicializó

```bash
docker-compose logs api | grep -i gemini
```

Deberías ver:
```
✓ Gemini service initialized
```

## 🔑 Obtener tu API Key de Google AI

1. **Visita**: https://aistudio.google.com/apikey
2. **Inicia sesión** con tu cuenta de Google
3. **Clic en** "Create API Key"
4. **Copia** la key (empieza con `AIza...`)
5. **Pégala** en el archivo `.env`

### Tier Gratuito Incluye:
- ✅ 15 solicitudes por minuto
- ✅ 1 millón de tokens por minuto
- ✅ 1,500 solicitudes por día
- ✅ Perfecto para desarrollo y pruebas

## ✅ Verificar la Configuración

### Opción 1: Hacer una consulta de prueba
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 11,
    "question": "¿Qué regula el Registro de Bienes Afectos a Concesiones?",
    "llm_provider": "gemini",
    "max_tokens": 1000
  }'
```

### Opción 2: Ejecutar el script de pruebas completo
```bash
cd ../.claude/internal-docs
./test_gemini_integration.sh
```

## 🔒 Seguridad

- ✅ El archivo `.env` está en `.gitignore` - **no se subirá a Git**
- ✅ Nunca compartas tu API key públicamente
- ✅ Si expones tu key accidentalmente, elimínala desde Google AI Studio

## 📁 Archivos en este directorio

- `.env` - **Tu archivo con la API key** (edita este)
- `.env.example` - Template de ejemplo (no editar)
- `README_ENV.md` - Este archivo

## 🆘 Solución de Problemas

### Error: "Gemini provider not available"

**Verifica que la API key esté configurada:**
```bash
docker exec api python -c "import os; print(os.environ.get('GOOGLE_AI_API_KEY', 'NOT SET'))"
```

Si dice "NOT SET":
1. Verifica que el `.env` tiene tu key real
2. Reinicia el contenedor: `docker-compose restart api`

### Error: 401 Unauthorized

Tu API key es inválida. Verifica que:
- Copiaste la key completa
- No tiene espacios al inicio/final
- Está activa en Google AI Studio

### Error: 429 Rate Limit

Has excedido el límite gratuito (15 req/min o 1,500 req/día). Espera un poco o revisa tu dashboard en Google AI Studio.

## 📚 Más Información

- **Guía completa**: `../.claude/internal-docs/GEMINI_SETUP.md`
- **Documentación Google AI**: https://ai.google.dev/docs
- **API Docs**: http://localhost:8000/docs
