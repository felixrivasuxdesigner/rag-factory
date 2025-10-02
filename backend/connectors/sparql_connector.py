import logging
from SPARQLWrapper import SPARQLWrapper, JSON

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SparqlConnector:
    """
    Handles the connection and data fetching from a SPARQL endpoint.
    """
    def __init__(self, endpoint_url: str):
        """
        Initializes the SparqlConnector with a specific SPARQL endpoint.

        Args:
            endpoint_url (str): The URL of the SPARQL endpoint.
        """
        self.endpoint_url = endpoint_url
        self.sparql = SPARQLWrapper(self.endpoint_url)
        # Set a common User-Agent to avoid being blocked by the server
        self.sparql.agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"

    def get_leyes(self, limit: int = 10):
        """
        Fetches a list of 'leyes' (laws) from the BCN Chile endpoint.

        Args:
            limit (int): The maximum number of results to return.

        Returns:
            list: A list of results from the SPARQL query, or an empty list if an error occurs.
        """
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX bcn-schema: <https://datos.bcn.cl/ontologies/bcn-schema#>

        SELECT ?ley ?fechaPublicacion ?titulo
        WHERE {{
          ?ley rdf:type <https://datos.bcn.cl/ontologies/bcn-schema#Ley>;
               bcn-schema:fechaPublicacion ?fechaPublicacion;
               rdfs:label ?titulo.
        }}
        ORDER BY DESC(?fechaPublicacion)
        LIMIT {limit}
        """
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)

        try:
            logger.info(f"Querying SPARQL endpoint: {self.endpoint_url}")
            results = self.sparql.query()
            # The convert() method will fail if the response is not JSON,
            # so we handle the raw response in the except block.
            json_results = results.convert()
            logger.info(f"Successfully fetched {len(json_results['results']['bindings'])} records.")
            return json_results["results"]["bindings"]
        except Exception as e:
            logger.error(f"Failed to convert SPARQL response to JSON. Error: {e}")
            try:
                # Read the raw response to see the error message from the server
                raw_response = results.response.read().decode('utf-8')
                logger.error(f"Raw response from server:\n{raw_response}")
            except Exception as read_e:
                logger.error(f"Could not even read the raw response. Error: {read_e}")
            return []

if __name__ == '__main__':
    # Example usage for testing purposes
    BCN_ENDPOINT = "https://datos.bcn.cl/es/endpoint-sparql"
    connector = SparqlConnector(endpoint_url=BCN_ENDPOINT)
    leyes = connector.get_leyes(limit=5)

    if leyes:
        print(f"Successfully retrieved {len(leyes)} laws:")
        for ley in leyes:
            titulo = ley.get('titulo', {}).get('value', 'N/A')
            fecha = ley.get('fechaPublicacion', {}).get('value', 'N/A')
            print(f"- {titulo} (Publicada: {fecha})")
    else:
        print("Failed to retrieve laws from BCN endpoint.")