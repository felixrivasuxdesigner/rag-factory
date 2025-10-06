#!/bin/bash

# RAG Factory - Test Script for Search and RAG Query Endpoints
# This script demonstrates how to use the new RAG capabilities

API_URL="http://localhost:8000"
PROJECT_ID=5  # Chilean Legal Norms project

echo "========================================="
echo "RAG Factory - Search & RAG Query Tests"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1️⃣  Testing API Health..."
curl -s $API_URL/health | jq -r '"API: " + .api + ", Database: " + .database + ", Ollama: " + .ollama'
echo ""

# Test 2: Semantic Search
echo "2️⃣  Testing Semantic Search..."
echo "Query: 'security installations production'"
SEARCH_RESULT=$(curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": '$PROJECT_ID',
    "query": "security installations production",
    "top_k": 3,
    "similarity_threshold": 0.3
  }')

echo "Results found: $(echo $SEARCH_RESULT | jq '.total_results')"
echo ""
echo "Top result:"
echo $SEARCH_RESULT | jq -r '.results[0] | "  Similarity: \(.similarity * 100 | floor)%\n  Content: \(.content[:150])..."'
echo ""

# Test 3: RAG Query (Search + AI Generation)
echo "3️⃣  Testing RAG Query (Search + AI Generation with Gemma 3)..."
echo "Question: 'What is the regulation about production and security installations?'"
echo ""
echo "🤖 Generating answer with Gemma 3..."

RAG_RESULT=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": '$PROJECT_ID',
    "question": "What is the regulation about production and security installations?",
    "top_k": 3,
    "similarity_threshold": 0.3,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 400
  }')

echo "✨ AI Answer:"
echo "─────────────────────────────────────────"
echo $RAG_RESULT | jq -r '.answer'
echo "─────────────────────────────────────────"
echo ""
echo "📚 Sources used ($(echo $RAG_RESULT | jq '.sources | length') documents):"
echo $RAG_RESULT | jq -r '.sources[] | "  • Similarity: \(.similarity * 100 | floor)% - \(.content[:100])..."'
echo ""

# Test 4: RAG Query in Spanish
echo "4️⃣  Testing RAG Query in Spanish..."
echo "Pregunta: '¿Qué regulaciones existen sobre seguridad?'"
echo ""
echo "🤖 Generando respuesta..."

RAG_ES=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": '$PROJECT_ID',
    "question": "¿Qué regulaciones existen sobre seguridad?",
    "top_k": 3,
    "similarity_threshold": 0.25,
    "model": "gemma3:1b-it-qat",
    "max_tokens": 300
  }')

echo "✨ Respuesta:"
echo "─────────────────────────────────────────"
echo $RAG_ES | jq -r '.answer'
echo "─────────────────────────────────────────"
echo ""

echo "========================================="
echo "✅ All tests completed!"
echo "========================================="
echo ""
echo "💡 You can now use the frontend at http://localhost:3000"
echo "   - Select a project"
echo "   - Use the Search/RAG panel to ask questions"
echo "   - Toggle between 'Search' and 'Ask AI' modes"
echo ""
