import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    A class to handle cleaning and processing of document data.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Performs basic text cleaning by removing extra whitespace.

        Args:
            text (str): The input string.

        Returns:
            str: The cleaned string.
        """
        if not text:
            return ""
        # Replace multiple whitespace characters with a single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def process_sparql_result(sparql_results: list) -> list[dict]:
        """
        Processes the raw results from a SPARQL query about laws/norms.
        Extracts relevant fields and cleans the text.

        Args:
            sparql_results (list): The list of binding dictionaries from a SPARQL query.

        Returns:
            list[dict]: A list of processed documents, each with a unique ID, title, and content.
        """
        processed_docs = []
        if not sparql_results:
            return processed_docs

        for result in sparql_results:
            try:
                # Try new format first (norma, id, title)
                doc_id = result.get('id', {}).get('value')
                title = result.get('title', {}).get('value')
                doc_uri = result.get('norma', {}).get('value')

                # Fallback to old format if new format not found
                if not doc_id:
                    doc_uri_old = result.get('ley', {}).get('value')
                    title = result.get('titulo', {}).get('value', 'N/A')
                    publication_date = result.get('fechaPublicacion', {}).get('value', 'N/A')
                    if not doc_uri_old:
                        continue
                    doc_id = doc_uri_old
                    doc_uri = doc_uri_old

                if not doc_id or not title:
                    continue

                cleaned_title = DocumentProcessor.clean_text(title)

                # Use title as content for now (in the future we could fetch full text)
                content = cleaned_title

                doc = {
                    'id': str(doc_id),
                    'title': cleaned_title,
                    'content': content,
                    'source': 'SPARQL-BCN'
                }

                # Add URI if available
                if doc_uri:
                    doc['uri'] = doc_uri

                # Add publication date if available (old format)
                if 'fechaPublicacion' in result:
                    doc['publication_date'] = result.get('fechaPublicacion', {}).get('value', 'N/A')

                processed_docs.append(doc)

            except Exception as e:
                logger.error(f"Error processing SPARQL result item: {result}. Error: {e}", exc_info=True)

        logger.info(f"Successfully processed {len(processed_docs)} documents.")
        return processed_docs

if __name__ == '__main__':
    # Example usage for testing purposes
    print("--- Testing DocumentProcessor ---")

    # 1. Test clean_text
    raw_text = "  Esto    es   un    texto  con \n muchos   espacios.  "
    cleaned = DocumentProcessor.clean_text(raw_text)
    print(f"Original text: '{raw_text}'")
    print(f"Cleaned text: '{cleaned}'")
    assert cleaned == "Esto es un texto con muchos espacios."
    print("clean_text test passed.\n")

    # 2. Test process_sparql_result
    sample_sparql_data = [
        {
            'ley': {'type': 'uri', 'value': 'https://datos.bcn.cl/ontologies/bcn-schema#Ley-21675'},
            'titulo': {'type': 'literal', 'value': 'MODIFICA EL CÓDIGO DEL TRABAJO PARA REGULAR EL TRABAJO A DISTANCIA Y EL TELETRABAJO'},
            'fechaPublicacion': {'type': 'literal', 'value': '2024-06-14'}
        },
        {
            'ley': {'type': 'uri', 'value': 'https://datos.bcn.cl/ontologies/bcn-schema#Ley-21674'},
            'titulo': {'type': 'literal', 'value': '    ESTABLECE EL 15 DE AGOSTO DE CADA AÑO COMO EL DÍA NACIONAL DE LAS TRABAJADORAS Y LOS TRABAJADORES DE CASA PARTICULAR    '},
            'fechaPublicacion': {'type': 'literal', 'value': '2024-06-12'}
        },
        {
            'ley': {'type': 'uri', 'value': 'https://datos.bcn.cl/ontologies/bcn-schema#Ley-21673'},
            'titulo': {'type': 'literal', 'value': 'MODIFICA LA LEY GENERAL DE SERVICIOS ELÉCTRICOS PARA PROTEGER A CLIENTES FINALES ANTE EL INCUMPLIMIENTO DE EMPRESAS GENERADORAS'},
            'fechaPublicacion': {'type': 'literal', 'value': '2024-06-10'}
        }
    ]

    processed_data = DocumentProcessor.process_sparql_result(sample_sparql_data)

    print("Processing sample SPARQL data...")
    assert len(processed_data) == 3
    assert processed_data[1]['title'] == "ESTABLECE EL 15 DE AGOSTO DE CADA AÑO COMO EL DÍA NACIONAL DE LAS TRABAJADORAS Y LOS TRABAJADORES DE CASA PARTICULAR"
    print("Processed data:")
    import json
    print(json.dumps(processed_data, indent=2, ensure_ascii=False))
    print("\nprocess_sparql_result test passed.")

    print("\n--- DocumentProcessor testing complete ---")