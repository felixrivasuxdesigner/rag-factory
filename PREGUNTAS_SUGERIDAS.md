# 🎯 Preguntas Sugeridas para Probar RAG Factory

Este documento contiene preguntas optimizadas para probar el sistema RAG con los datos actuales.

## 📊 Estado de los Proyectos

### Proyecto: Chilean Legal Norms (ID: 5)
- **Documentos:** 5 normas chilenas
- **Contenido:** Títulos de decretos, leyes y resoluciones
- **Temas:** Seguridad en combustibles, policía, aduanas, IVA

### Proyecto: US Congress Bills (ID: 4)
- **Documentos:** 5 bills del Congreso 119
- **Contenido:** Títulos y metadata de bills
- **Temas:** Armas de fuego, impuestos, agricultura

---

## 🇨🇱 Preguntas para Proyecto Chileno

### ✅ Preguntas con Alta Probabilidad de Éxito

**1. Seguridad en Instalaciones**
```
What regulations exist about security in fuel installations?
```
**Esperado:** Respuesta sobre el reglamento de seguridad para combustibles líquidos
**Similitud esperada:** >70%

**2. Policía de Investigaciones**
```
Are there any changes to the Police Investigation personnel?
```
**Esperado:** Información sobre aumento de dotación de personal
**Similitud esperada:** >60%

**3. Normas Aduaneras**
```
Are there modifications to customs regulations?
```
**Esperado:** Información sobre cambios al compendio de normas aduaneras
**Similitud esperada:** >65%

**4. Búsqueda General**
```
What types of regulations are in this database?
```
**Esperado:** Resumen de diferentes tipos de normas

---

## 🇺🇸 Preguntas para Proyecto USA

### ✅ Preguntas con Alta Probabilidad de Éxito

**1. Constitutional Carry (MEJOR PREGUNTA)**
```
What is the Constitutional Concealed Carry Reciprocity Act?
```
**Esperado:** Descripción del H.R. 38
**Similitud esperada:** >75%

**2. Legislación de Armas**
```
What bills are related to firearms and gun rights?
```
**Esperado:** Lista de bills relacionados (H.R. 38, H.R. 2184, H.R. 2267)
**Similitud esperada:** >60%

**3. NICS Data**
```
Is there any legislation about background check data reporting?
```
**Esperado:** Información sobre H.R. 2267 - NICS Data Reporting Act
**Similitud esperada:** >55%

**4. Tax Court**
```
What bill discusses tax court improvements?
```
**Esperado:** H.R. 5349 - Tax Court Improvement Act
**Similitud esperada:** >75%

**5. Búsqueda Específica**
```
What is bill H.R. 38 about?
```
**Esperado:** Respuesta directa sobre Constitutional Concealed Carry
**Similitud esperada:** >80%

---

## 🔍 Tips para Mejores Resultados

### ✅ DO (Hacer):
- Usa términos específicos de los documentos
- Pregunta por temas concretos (armas, impuestos, aduanas)
- Usa nombres de bills si los conoces (H.R. 38)
- Pregunta por "regulations", "bills", "acts"

### ❌ DON'T (No hacer):
- Preguntas muy generales ("tell me about laws")
- Preguntas sobre contenido detallado (solo tenemos títulos)
- Preguntas sobre temas no relacionados con los datos
- Preguntas que requieren razonamiento complejo

---

## 🎮 Cómo Probar en el Frontend

1. **Abre** http://localhost:3000
2. **Selecciona** un proyecto (Chilean Legal Norms o US Congress Bills)
3. **Ve al panel** "Search/RAG" que aparece arriba
4. **Elige modo:**
   - **Search**: Solo muestra documentos similares
   - **Ask AI** ✨: Usa RAG con Gemma 3 para generar respuesta
5. **Escribe** una pregunta de las sugeridas arriba
6. **Observa:**
   - La respuesta generada por AI
   - Los documentos fuente con % de similitud
   - El número de documentos usados como contexto

---

## 📈 Ejemplos de Resultados Esperados

### Ejemplo 1: Alta Calidad
**Pregunta:** "What is the Constitutional Concealed Carry Reciprocity Act?"

**Respuesta esperada:**
```
The Constitutional Concealed Carry Reciprocity Act of 2025 is a bill
that promotes constitutional concealed carry reciprocity.

Sources:
• [80%] Constitutional Concealed Carry Reciprocity Act of 2025
  Bill Number: H.R. 38, Congress: 119
```

### Ejemplo 2: Búsqueda sin Generación
**Query:** "firearm legislation"

**Resultados esperados:**
```
Results (3):
• [75%] Constitutional Concealed Carry Reciprocity Act of 2025
• [68%] Firearm Due Process Protection Act of 2025
• [62%] NICS Data Reporting Act of 2025
```

---

## 🚀 Próximos Pasos para Mejorar

1. **Ingestar documentos completos** (no solo títulos)
2. **Agregar más documentos** de diferentes temas
3. **Usar Gemma 3 4B** para respuestas más elaboradas
4. **Ajustar chunking** para textos largos

---

## 💡 Preguntas Experimentales

Estas preguntas pueden o no funcionar bien con los datos actuales:

```
Compare firearm legislation in this Congress
What are the most recent bills proposed?
How many regulations are about security?
What changes were made to police departments?
```

---

**¡Prueba diferentes preguntas y descubre el poder del RAG!** 🎯
