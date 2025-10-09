"""
Comparison script for testing multilingual embedding models.
Compares EmbeddingGemma vs Jina v2 Base ES for Spanish-English bilingual support.
"""

import requests
import time
from typing import List, Dict
import json

class ModelComparison:
    """Compare different embedding models for performance and quality."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.embed_endpoint = f"{ollama_url}/api/embeddings"

    def generate_embedding(self, text: str, model: str) -> Dict:
        """
        Generate embedding and measure performance.

        Returns:
            Dict with embedding, time, and metadata
        """
        start_time = time.time()

        try:
            response = requests.post(
                self.embed_endpoint,
                json={"model": model, "prompt": text},
                timeout=60
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                embedding = result.get('embedding')

                return {
                    'success': True,
                    'embedding': embedding,
                    'dimension': len(embedding) if embedding else 0,
                    'time_seconds': elapsed,
                    'model': model
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'time_seconds': elapsed,
                    'model': model
                }

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'success': False,
                'error': str(e),
                'time_seconds': elapsed,
                'model': model
            }

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def test_semantic_similarity(self, model: str, test_cases: List[Dict]) -> List[Dict]:
        """
        Test semantic similarity for given test cases.

        Args:
            model: Model name
            test_cases: List of dicts with 'query' and 'documents' keys

        Returns:
            List of results with similarities
        """
        results = []

        for case in test_cases:
            query = case['query']
            documents = case['documents']
            expected_best = case.get('expected_best', 0)

            # Generate query embedding
            query_result = self.generate_embedding(query, model)

            if not query_result['success']:
                print(f"  ❌ Failed to embed query: {query_result['error']}")
                continue

            query_embedding = query_result['embedding']

            # Generate document embeddings and calculate similarities
            doc_similarities = []
            total_time = query_result['time_seconds']

            for i, doc in enumerate(documents):
                doc_result = self.generate_embedding(doc, model)
                total_time += doc_result['time_seconds']

                if doc_result['success']:
                    similarity = self.cosine_similarity(query_embedding, doc_result['embedding'])
                    doc_similarities.append({
                        'document': doc,
                        'similarity': similarity,
                        'index': i
                    })

            # Sort by similarity
            doc_similarities.sort(key=lambda x: x['similarity'], reverse=True)

            # Check if expected best matches actual best
            best_match_index = doc_similarities[0]['index'] if doc_similarities else -1
            correct_ranking = best_match_index == expected_best

            results.append({
                'query': query,
                'model': model,
                'rankings': doc_similarities,
                'correct_ranking': correct_ranking,
                'total_time': total_time,
                'expected_best': expected_best,
                'actual_best': best_match_index
            })

        return results


def print_results(results: List[Dict]):
    """Pretty print comparison results."""
    print("\n" + "="*80)
    for result in results:
        print(f"\nQuery: \"{result['query']}\"")
        print(f"Model: {result['model']}")
        print(f"Time: {result['total_time']:.3f}s")
        print(f"Correct Ranking: {'✓' if result['correct_ranking'] else '✗'}")
        print(f"Expected best: {result['expected_best']}, Got: {result['actual_best']}")
        print("\nDocument Rankings:")
        for i, ranking in enumerate(result['rankings'], 1):
            print(f"  {i}. [{ranking['similarity']:.4f}] {ranking['document'][:60]}...")
        print("-"*80)


def main():
    print("\n" + "="*80)
    print(" EMBEDDING MODEL COMPARISON: EmbeddingGemma vs Jina v2 Base ES")
    print("="*80)

    comparator = ModelComparison()

    # Test cases: Spanish queries
    spanish_test_cases = [
        {
            'query': '¿Cómo funciona la inteligencia artificial?',
            'documents': [
                'La inteligencia artificial es un campo de la informática que se centra en crear máquinas inteligentes.',
                'Cooking recipes for traditional Chilean dishes',
                'Artificial intelligence is a branch of computer science focused on intelligent machines.'
            ],
            'expected_best': 0
        },
        {
            'query': 'Recetas de cocina chilena',
            'documents': [
                'Machine learning algorithms for data analysis',
                'Recetas tradicionales de Chile incluyen empanadas, cazuela y pastel de choclo.',
                'La inteligencia artificial se utiliza en medicina.'
            ],
            'expected_best': 1
        },
        {
            'query': 'Tecnología de base de datos vectoriales',
            'documents': [
                'Las bases de datos vectoriales almacenan embeddings para búsquedas semánticas.',
                'Traditional music instruments from South America',
                'Vector databases store embeddings for semantic search capabilities.'
            ],
            'expected_best': 0
        }
    ]

    # Test cases: English queries
    english_test_cases = [
        {
            'query': 'How does machine learning work?',
            'documents': [
                'Machine learning uses algorithms to learn patterns from data automatically.',
                'Recetas de cocina tradicional mexicana',
                'Music theory and composition basics'
            ],
            'expected_best': 0
        },
        {
            'query': 'Best practices for API development',
            'documents': [
                'Historia del arte moderno',
                'API development requires proper documentation, versioning, and error handling.',
                'Recipes for Italian pasta dishes'
            ],
            'expected_best': 1
        }
    ]

    # Test models
    models = [
        'embeddinggemma',
        'jina/jina-embeddings-v2-base-es'
    ]

    all_results = {}

    for model in models:
        print(f"\n{'='*80}")
        print(f" Testing Model: {model}")
        print(f"{'='*80}\n")

        print("📊 Testing Spanish queries...")
        spanish_results = comparator.test_semantic_similarity(model, spanish_test_cases)

        print("\n📊 Testing English queries...")
        english_results = comparator.test_semantic_similarity(model, english_test_cases)

        all_results[model] = {
            'spanish': spanish_results,
            'english': english_results
        }

    # Print detailed results
    print("\n" + "="*80)
    print(" DETAILED RESULTS")
    print("="*80)

    for model in models:
        print(f"\n{'='*80}")
        print(f" Model: {model}")
        print(f"{'='*80}")

        print("\n🇪🇸 SPANISH QUERIES")
        print_results(all_results[model]['spanish'])

        print("\n🇬🇧 ENGLISH QUERIES")
        print_results(all_results[model]['english'])

    # Summary comparison
    print("\n" + "="*80)
    print(" SUMMARY COMPARISON")
    print("="*80 + "\n")

    for model in models:
        spanish_results = all_results[model]['spanish']
        english_results = all_results[model]['english']

        spanish_accuracy = sum(r['correct_ranking'] for r in spanish_results) / len(spanish_results) * 100
        english_accuracy = sum(r['correct_ranking'] for r in english_results) / len(english_results) * 100

        spanish_avg_time = sum(r['total_time'] for r in spanish_results) / len(spanish_results)
        english_avg_time = sum(r['total_time'] for r in english_results) / len(english_results)

        # Get dimension from first result
        dimension = spanish_results[0]['rankings'][0].get('dimension', 'N/A') if spanish_results else 'N/A'

        print(f"Model: {model}")
        print(f"  Dimensions: {dimension}")
        print(f"  Spanish Accuracy: {spanish_accuracy:.1f}%")
        print(f"  English Accuracy: {english_accuracy:.1f}%")
        print(f"  Avg Spanish Query Time: {spanish_avg_time:.3f}s")
        print(f"  Avg English Query Time: {english_avg_time:.3f}s")
        print(f"  Overall Accuracy: {(spanish_accuracy + english_accuracy) / 2:.1f}%")
        print()

    print("="*80)
    print("✓ Comparison completed!")
    print("="*80)


if __name__ == '__main__':
    main()
