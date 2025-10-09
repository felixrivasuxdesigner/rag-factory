"""
LLM service for generating text responses using Ollama models.
Supports RAG (Retrieval-Augmented Generation) with context injection.
"""

import logging
import requests
import os
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for generating text using Ollama's language models.
    """

    def __init__(
        self,
        model: str = "gemma3:1b-it-qat",
        ollama_host: str = None,
        temperature: float = 0.7
    ):
        """
        Initialize the LLM service.

        Args:
            model (str): The Ollama language model to use
            ollama_host (str): Ollama server host (default: from env or localhost)
            temperature (float): Sampling temperature (0.0 to 1.0)
        """
        self.model = model
        self.temperature = temperature

        # Get Ollama host from env or use default
        if ollama_host is None:
            ollama_host = os.environ.get('OLLAMA_HOST', 'localhost')

        # Build the full URL
        if not ollama_host.startswith('http'):
            self.ollama_url = f"http://{ollama_host}:11434"
        else:
            self.ollama_url = ollama_host

        self.generate_endpoint = f"{self.ollama_url}/api/generate"

        logger.info(f"Initialized LLMService with model={model}, ollama_url={self.ollama_url}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
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

            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature if temperature is not None else self.temperature,
                    "num_predict": max_tokens
                }
            }

            logger.info(f"Generating with model={self.model}, max_tokens={max_tokens}")

            response = requests.post(
                self.generate_endpoint,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()

                if generated_text:
                    logger.info(f"Generated {len(generated_text)} characters")
                    return generated_text
                else:
                    logger.error("Empty response from LLM")
                    return None
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate text: {e}", exc_info=True)
            return None

    def generate_with_context(
        self,
        question: str,
        context_documents: List[Dict],
        max_tokens: int = 500,
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
            context_parts.append(f"[Document {i}] (relevance: {similarity:.2f})\n{content}")

        context_text = "\n\n".join(context_parts)

        # Detect language from question and build appropriate system prompt
        # Simple heuristic: check for common Spanish words/characters
        is_spanish = any(word in question.lower() for word in ['qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué', 'regulaciones', 'sobre', 'existen'])

        if is_spanish:
            system_prompt = """Eres un asistente experto que responde preguntas basándote en los documentos de contexto proporcionados.
Tu tarea:
1. Lee los documentos de contexto cuidadosamente
2. Responde la pregunta usando SOLO información del contexto
3. Si el contexto no contiene suficiente información, di "No tengo suficiente información para responder esa pregunta."
4. Sé conciso pero completo en tu respuesta
5. Cita qué documento(s) usaste cuando sea relevante
6. IMPORTANTE: Responde SIEMPRE en español"""

            prompt = f"""Documentos de Contexto:
{context_text}

Pregunta: {question}

Respuesta:"""
        else:
            system_prompt = """You are a helpful assistant that answers questions based on the provided context documents.
Your task:
1. Read the context documents carefully
2. Answer the question using ONLY information from the context
3. If the context doesn't contain enough information, say "I don't have enough information to answer that question."
4. Be concise but complete in your answer
5. Cite which document(s) you used when relevant
6. IMPORTANT: Always respond in English"""

            prompt = f"""Context Documents:
{context_text}

Question: {question}

Answer:"""

        logger.info(f"Generating RAG answer with {len(context_documents)} context documents")

        return self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )

    def health_check(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            bool: True if service is healthy
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


if __name__ == '__main__':
    """
    Test the LLM service
    """
    print("--- Testing LLM Service ---\n")

    # Initialize service
    service = LLMService(model="gemma3:1b-it-qat")

    # Health check
    print("Checking Ollama service health...")
    if service.health_check():
        print("✓ Ollama service is healthy\n")
    else:
        print("✗ Ollama service is not available")
        print("Make sure Ollama is running: docker-compose up ollama")
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

    # Test RAG generation with mock context
    print("Testing RAG generation with context...")
    mock_question = "What is machine learning?"
    mock_context = [
        {
            'content': 'Machine learning is a subset of artificial intelligence that focuses on building systems that can learn from data. It enables computers to improve their performance on tasks without being explicitly programmed.',
            'similarity': 0.85
        },
        {
            'content': 'Deep learning is a type of machine learning that uses neural networks with multiple layers. It has been particularly successful in image recognition and natural language processing.',
            'similarity': 0.72
        }
    ]

    rag_response = service.generate_with_context(
        question=mock_question,
        context_documents=mock_context,
        max_tokens=200
    )

    if rag_response:
        print(f"✓ Generated RAG response:")
        print(f"  Question: {mock_question}")
        print(f"  Answer: {rag_response}\n")
    else:
        print("✗ Failed to generate RAG response\n")

    print("--- LLM Service test completed ---")
