#!/usr/bin/env python3
from services.vector_db_writer import VectorDBWriter
import random

writer = VectorDBWriter(
    'journeylaw-postgres',
    5432,
    'journeylaw_db',
    'journeylaw',
    'journeylaw_dev_2024',
    'document_embeddings',
    768
)

if writer.connect():
    print("✓ Connected to DB")

    # Test document with chunk ID
    test_doc = {
        'id': 'test_doc_123_chunk_0',
        'content': 'This is a test document',
        'embedding': [random.random() for _ in range(768)],
        'metadata': {'country_code': 'CL', 'test': True}
    }

    try:
        count = writer.insert_vectors([test_doc])
        print(f"✓ Inserted {count} document(s)")
    except Exception as e:
        print(f"✗ Insert failed: {e}")
        import traceback
        traceback.print_exc()

    writer.close()
else:
    print("✗ Connection failed")
