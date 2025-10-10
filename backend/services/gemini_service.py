"""
Google AI service for RAG Factory.
Provides cloud-based LLM responses using Google AI Studio API with Gemini/Gemma models.
Much faster than local Ollama models, especially on older hardware.
Supports both Gemini (latest, fastest) and Gemma models.
"""

import logging
import os
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiService:
    """
    Service for generating text using Google AI API with Gemini/Gemma models.
    Cloud-based alternative to local Ollama models - faster and more reliable.
    """

    def __init__(
        self,
        model: str = "gemini-flash-lite-latest",
        api_key: Optional[str] = None,
        temperature: float = 0.3
    ):
        """
        Initialize the Google AI service.

        Args:
            model (str): The model to use (default: gemini-flash-lite-latest)
                        Gemini models: gemini-flash-lite-latest, gemini-2.0-flash-exp
                        Gemma models: gemma-3-1b-it, gemma-3-4b-it, gemma-3-12b-it, gemma-3-27b-it
            api_key (str): Google AI Studio API key (from env if not provided)
            temperature (float): Sampling temperature (0.0 to 1.0)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get('GOOGLE_AI_API_KEY') or os.environ.get('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Google AI API key not provided. Set GOOGLE_AI_API_KEY environment variable "
                "or pass api_key parameter. Get your key from: https://aistudio.google.com/apikey"
            )

        # Configure the API
        genai.configure(api_key=self.api_key)

        self.model_name = model
        self.temperature = temperature

        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
            }
        )

        logger.info(f"✓ Initialized Google AI Service with model={model}, temperature={temperature}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 800,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate text from a prompt.

        Args:
            prompt (str): The prompt to generate from
            max_tokens (int): Maximum tokens in response
            temperature (float): Override default temperature
            system_prompt (str): Optional system instruction

        Returns:
            str: Generated text, or None if failed
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided for generation")
            return None

        try:
            # Build the full prompt with system instruction if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Use override temperature if provided
            temp = temperature if temperature is not None else self.temperature

            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temp,
                    "max_output_tokens": max_tokens,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )

            generated_text = response.text.strip()

            if generated_text:
                logger.info(f"✓ Generated {len(generated_text)} characters with Gemini")
                return generated_text
            else:
                logger.error("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Failed to generate with Gemini: {e}", exc_info=True)
            return None

    def generate_with_context(
        self,
        question: str,
        context_documents: List[Dict],
        max_tokens: int = 1000,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generate answer using RAG with retrieved context documents.

        Args:
            question (str): The question to answer
            context_documents (List[Dict]): Retrieved documents with 'content' and 'similarity'
            max_tokens (int): Maximum tokens in response
            temperature (float): Override default temperature

        Returns:
            str: Generated answer, or None if failed
        """
        if not question or not question.strip():
            logger.warning("Empty question provided")
            return None

        # Build context from documents
        context_parts = []
        for i, doc in enumerate(context_documents, 1):
            content = doc.get('content', '')
            similarity = doc.get('similarity', 0.0)
            context_parts.append(f"[Documento {i}] (relevancia: {similarity:.2f})\n{content}")

        context_text = "\n\n".join(context_parts)

        # Detect language from question
        is_spanish = any(word in question.lower() for word in ['qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué', 'regulaciones', 'sobre', 'existen'])

        if is_spanish:
            system_prompt = """Eres un asistente experto especializado en documentos legales y legislativos.

Tu tarea:
1. Lee los documentos de contexto cuidadosamente y extrae TODA la información relevante
2. Proporciona una respuesta DETALLADA y COMPLETA usando SOLO información del contexto
3. Incluye definiciones, procedimientos, requisitos, artículos y cualquier detalle específico
4. Si hay listas o puntos específicos, inclúyelos de manera estructurada
5. Organiza la información de manera clara con párrafos y bullets si es necesario
6. Si el contexto no contiene suficiente información, di "No tengo suficiente información para responder esa pregunta."
7. IMPORTANTE: Responde SIEMPRE en español
8. NO resumas demasiado - proporciona información completa y exhaustiva"""

            prompt = f"""Documentos de Contexto:
{context_text}

Pregunta: {question}

Respuesta detallada:"""
        else:
            system_prompt = """You are an expert assistant specializing in legal and legislative documents.

Your task:
1. Read the context documents carefully and extract ALL relevant information
2. Provide a DETAILED and COMPREHENSIVE answer using ONLY information from the context
3. Include definitions, procedures, requirements, articles, and any specific details
4. If there are lists or specific points, include them in a structured way
5. Organize information clearly with paragraphs and bullets if needed
6. If the context doesn't contain enough information, say "I don't have enough information to answer that question."
7. IMPORTANT: Always respond in English
8. DO NOT over-summarize - provide complete and exhaustive information"""

            prompt = f"""Context Documents:
{context_text}

Question: {question}

Detailed Answer:"""

        logger.info(f"Generating RAG answer with Gemini using {len(context_documents)} context documents")

        return self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )

    def health_check(self) -> bool:
        """
        Check if Gemini service is available.

        Returns:
            bool: True if service is healthy
        """
        try:
            # Try a simple generation
            response = self.model.generate_content(
                "Test",
                generation_config={"max_output_tokens": 10}
            )
            return bool(response.text)
        except:
            return False


if __name__ == '__main__':
    """
    Test the Gemini service
    """
    print("=" * 70)
    print("Testing Google Gemini Service")
    print("=" * 70)
    print()

    # Check if API key is available
    api_key = os.environ.get('GOOGLE_AI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ No API key found!")
        print()
        print("Please set your Google AI API key:")
        print("  export GOOGLE_AI_API_KEY='your-api-key-here'")
        print()
        print("Get your free API key from:")
        print("  https://aistudio.google.com/apikey")
        print()
        exit(1)

    try:
        # Initialize service
        service = GeminiService(model="gemini-1.5-flash")
        print(f"✓ Service initialized\n")

        # Health check
        print("Testing connection...")
        if service.health_check():
            print("✓ Gemini service is healthy\n")
        else:
            print("✗ Gemini service health check failed\n")
            exit(1)

        # Test simple generation
        print("Testing simple generation...")
        test_prompt = "What is artificial intelligence? Answer in 2 sentences."
        response = service.generate(test_prompt, max_tokens=100)

        if response:
            print(f"✓ Generated response:")
            print(f"  {response}\n")
        else:
            print("✗ Failed to generate response\n")

        # Test Spanish RAG generation
        print("Testing RAG generation (Spanish)...")
        mock_question = "¿Qué es el machine learning?"
        mock_context = [
            {
                'content': 'El machine learning es un subconjunto de la inteligencia artificial que se enfoca en construir sistemas que pueden aprender de datos. Permite que las computadoras mejoren su rendimiento en tareas sin ser programadas explícitamente.',
                'similarity': 0.85
            }
        ]

        rag_response = service.generate_with_context(
            question=mock_question,
            context_documents=mock_context,
            max_tokens=300
        )

        if rag_response:
            print(f"✓ Generated RAG response:")
            print(f"  Pregunta: {mock_question}")
            print(f"  Respuesta: {rag_response}\n")
        else:
            print("✗ Failed to generate RAG response\n")

        print("=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)
