import logging
import os
import ollama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Ollama client using environment variables
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'localhost')
OLLAMA_PORT = int(os.environ.get('OLLAMA_PORT', 11434))
OLLAMA_CLIENT = ollama.Client(host=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}")

DEFAULT_EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'mxbai-embed-large:latest')

class Vectorizer:
    """
    Handles the generation of text embeddings using a configured Ollama model.
    """
    def __init__(self, client=OLLAMA_CLIENT, model: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initializes the Vectorizer.

        Args:
            client: An Ollama client instance.
            model (str): The name of the embedding model to use in Ollama.
        """
        self.client = client
        self.model = model
        logger.info(f"Vectorizer initialized with model '{self.model}' on host: http://{OLLAMA_HOST}:{OLLAMA_PORT}")

    def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generates an embedding for the given text.

        Args:
            text (str): The text to embed.

        Returns:
            list[float] | None: The embedding vector, or None if an error occurs.
        """
        if not text or not text.strip():
            logger.warning("generate_embedding called with empty text.")
            return None

        try:
            response = self.client.embeddings(model=self.model, prompt=text)
            return response.get('embedding')
        except Exception as e:
            logger.error(f"Error generating embedding with Ollama: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # This block is for demonstration and requires a running Ollama service.
    print("--- Testing Vectorizer ---")

    ollama_is_running = False
    try:
        print(f"Connecting to Ollama at http://{OLLAMA_HOST}:{OLLAMA_PORT}...")
        OLLAMA_CLIENT.list()
        print("Successfully connected to Ollama.")
        ollama_is_running = True
    except Exception as e:
        print(f"Could not connect to Ollama. Please ensure it is running. Error: {e}")

    if ollama_is_running:
        vectorizer = Vectorizer()
        sample_text = "La Biblioteca del Congreso Nacional de Chile es un servicio común del Congreso Nacional."

        print(f"\nGenerating embedding for sample text: '{sample_text}'")
        embedding = vectorizer.generate_embedding(sample_text)

        if embedding:
            print(f"Successfully generated embedding of dimension: {len(embedding)}")
            print(f"Embedding preview: {embedding[:5]}...")
            assert isinstance(embedding, list)
            assert len(embedding) > 0
        else:
            print("Failed to generate embedding. This might be because the model is not available in Ollama.")
    else:
        print("Skipping Vectorizer tests.")

    print("\n--- Vectorizer testing complete ---")