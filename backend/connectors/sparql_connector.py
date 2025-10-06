import logging
from SPARQLWrapper import SPARQLWrapper, JSON

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SparqlConnector:
    """
    Handles the connection and data fetching from a SPARQL endpoint.
    """
    def __init__(self, endpoint_url: str = "https://datos.bcn.cl/sparql"):
        """
        Initializes the SparqlConnector with a specific SPARQL endpoint.

        Args:
            endpoint_url (str): The URL of the SPARQL endpoint. Defaults to BCN Chile endpoint.
        """
        self.endpoint_url = endpoint_url
        self.sparql = SPARQLWrapper(self.endpoint_url)
        # Set a common User-Agent to avoid being blocked by the server
        self.sparql.agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"

    def execute_query(self, query: str):
        """
        Executes a custom SPARQL query.

        Args:
            query (str): The SPARQL query to execute.

        Returns:
            list: A list of results from the SPARQL query, or an empty list if an error occurs.
        """
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)

        try:
            logger.info(f"Querying SPARQL endpoint: {self.endpoint_url}")
            results = self.sparql.query()
            json_results = results.convert()
            logger.info(f"Successfully fetched {len(json_results['results']['bindings'])} records.")
            return json_results["results"]["bindings"]
        except Exception as e:
            logger.error(f"Failed to execute SPARQL query. Error: {e}")
            try:
                raw_response = results.response.read().decode('utf-8')
                logger.error(f"Raw response from server:\n{raw_response}")
            except Exception as read_e:
                logger.error(f"Could not read the raw response. Error: {read_e}")
            return []

    def get_leyes(self, limit: int = 10, custom_query: str = None):
        """
        Fetches a list of 'leyes' (laws) from the BCN Chile endpoint.

        Args:
            limit (int): The maximum number of results to return.
            custom_query (str): Optional custom SPARQL query. If not provided, uses default query.

        Returns:
            list: A list of results from the SPARQL query, or an empty list if an error occurs.
        """
        if custom_query:
            # Use custom query but replace LIMIT if present
            query = custom_query
            if 'LIMIT' not in query.upper():
                query += f"\nLIMIT {limit}"
        else:
            # Default query using the verified BCN ontology
            query = f"""
PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?id ?title ?norma
WHERE {{
    ?norma dc:identifier ?id .
    ?norma dc:title ?title .
    ?norma a bcnnorms:Norm .
}}
LIMIT {limit}
"""

        return self.execute_query(query)

if __name__ == '__main__':
    # Example usage for testing purposes
    BCN_ENDPOINT = "https://datos.bcn.cl/sparql"
    connector = SparqlConnector(endpoint_url=BCN_ENDPOINT)
    leyes = connector.get_leyes(limit=5)

    if leyes:
        print(f"Successfully retrieved {len(leyes)} norms:")
        for ley in leyes:
            titulo = ley.get('title', {}).get('value', 'N/A')
            doc_id = ley.get('id', {}).get('value', 'N/A')
            norma = ley.get('norma', {}).get('value', 'N/A')
            print(f"- ID: {doc_id}")
            print(f"  Title: {titulo}")
            print(f"  URI: {norma}\n")
    else:
        print("Failed to retrieve norms from BCN endpoint.")