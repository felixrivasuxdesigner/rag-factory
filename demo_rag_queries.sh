#!/bin/bash

# RAG Factory - Demo de Consultas para ambos proyectos
# Este script demuestra el poder del RAG con preguntas reales

API_URL="http://localhost:8000"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        RAG Factory - Demo de Consultas Inteligentes       ║"
echo "╔════════════════════════════════════════════════════════════╗"
echo ""

# ============================================================================
# PROYECTO 1: NORMAS LEGALES CHILENAS (Project ID: 5)
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📚 PROYECTO: NORMAS LEGALES CHILENAS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Pregunta 1 (Chile): Seguridad en combustibles
echo -e "${YELLOW}🔍 PREGUNTA 1 (Chile):${NC}"
echo "¿Qué regulaciones existen sobre seguridad en instalaciones de combustibles?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER1=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 5,
    "question": "What regulations exist about security in fuel installations and operations?",
    "top_k": 3,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 400
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER1" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas ($(echo "$ANSWER1" | jq '.sources | length') documentos):${NC}"
echo "$ANSWER1" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Pregunta 2 (Chile): Policía de Investigaciones
echo -e "${YELLOW}🔍 PREGUNTA 2 (Chile):${NC}"
echo "¿Hay cambios en el personal de la Policía de Investigaciones?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER2=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 5,
    "question": "Are there any changes to the Police Investigation personnel or staffing?",
    "top_k": 3,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 400
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER2" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas:${NC}"
echo "$ANSWER2" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Pregunta 3 (Chile): Normas aduaneras
echo -e "${YELLOW}🔍 PREGUNTA 3 (Chile):${NC}"
echo "¿Qué modificaciones existen en normas aduaneras?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER3=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 5,
    "question": "What modifications exist in customs regulations?",
    "top_k": 3,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 300
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER3" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas:${NC}"
echo "$ANSWER3" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo ""

# ============================================================================
# PROYECTO 2: LEGISLACIÓN USA - CONGRESO (Project ID: 4)
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🇺🇸 PROYECTO: LEGISLACIÓN USA - CONGRESO 119${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Pregunta 1 (USA): Leyes sobre armas de fuego
echo -e "${YELLOW}🔍 PREGUNTA 1 (USA):${NC}"
echo "What firearm legislation has been proposed in Congress 119?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER4=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 4,
    "question": "What firearm legislation has been proposed in Congress?",
    "top_k": 3,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 500
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER4" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas ($(echo "$ANSWER4" | jq '.sources | length') documentos):${NC}"
echo "$ANSWER4" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Pregunta 2 (USA): Constitutional Carry
echo -e "${YELLOW}🔍 PREGUNTA 2 (USA):${NC}"
echo "What is the Constitutional Concealed Carry Reciprocity Act about?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER5=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 4,
    "question": "What is the Constitutional Concealed Carry Reciprocity Act about?",
    "top_k": 2,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 400
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER5" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas:${NC}"
echo "$ANSWER5" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Pregunta 3 (USA): Tax Court
echo -e "${YELLOW}🔍 PREGUNTA 3 (USA):${NC}"
echo "Are there any bills about tax court improvements?"
echo ""
echo -e "${GREEN}🤖 Consultando RAG...${NC}"

ANSWER6=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 4,
    "question": "Are there any bills about tax court improvements?",
    "top_k": 3,
    "similarity_threshold": 0.2,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 350
  }')

echo -e "${PURPLE}📝 RESPUESTA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER6" | jq -r '.answer'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}📚 Fuentes citadas:${NC}"
echo "$ANSWER6" | jq -r '.sources[] | "  • [\(.similarity * 100 | floor)%] \(.content[:120])..."'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo ""

# ============================================================================
# BÚSQUEDAS SEMÁNTICAS (sin generación AI)
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔎 BÚSQUEDAS SEMÁNTICAS (Solo similitud, sin AI)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Búsqueda 1: Seguridad (Chile)
echo -e "${YELLOW}🔍 BÚSQUEDA 1 (Chile):${NC} 'seguridad instalaciones'"
SEARCH1=$(curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 5,
    "query": "seguridad instalaciones",
    "top_k": 3,
    "similarity_threshold": 0.2
  }')

echo -e "${GREEN}Resultados encontrados: $(echo "$SEARCH1" | jq '.total_results')${NC}"
echo "$SEARCH1" | jq -r '.results[] | "  [\(.similarity * 100 | floor)%] \(.content[:100])..."'
echo ""

# Búsqueda 2: NICS (USA)
echo -e "${YELLOW}🔍 BÚSQUEDA 2 (USA):${NC} 'NICS background check data'"
SEARCH2=$(curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 4,
    "query": "NICS background check data reporting",
    "top_k": 3,
    "similarity_threshold": 0.2
  }')

echo -e "${GREEN}Resultados encontrados: $(echo "$SEARCH2" | jq '.total_results')${NC}"
echo "$SEARCH2" | jq -r '.results[] | "  [\(.similarity * 100 | floor)%] \(.content[:100])..."'
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ Demo completado exitosamente               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${PURPLE}💡 Siguiente paso: Prueba el frontend en http://localhost:3000${NC}"
echo "   • Selecciona un proyecto"
echo "   • Ve al panel 'Search/RAG' que aparece arriba"
echo "   • Haz tus propias preguntas en modo 'Ask AI' ✨"
echo ""
