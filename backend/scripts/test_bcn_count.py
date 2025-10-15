#!/usr/bin/env python3
"""Quick test to fetch documents from BCN and estimate total"""

import sys
sys.path.insert(0, '/app')

from connectors.chile_bcn_connector import ChileBCNConnector

print("=" * 80)
print("Testing BCN Chile Connector - Estimating Total Documents")
print("=" * 80)

# Test with small batch first
connector = ChileBCNConnector(config={'limit': 10})

print("\n🔌 Testing connection...")
test_result = connector.test_connection()
print(f"Connection: {'✅ Success' if test_result['success'] else '❌ Failed'}")

if not test_result['success']:
    print(f"Error: {test_result.get('error')}")
    sys.exit(1)

print("\n📊 Fetching first 10 documents to test...")
try:
    docs = connector.fetch_documents(limit=10)
    print(f"✅ Successfully fetched {len(docs)} documents")

    if docs:
        print("\nSample document:")
        print(f"  ID: {docs[0]['id']}")
        print(f"  Title: {docs[0]['title'][:80]}")
        print(f"  Content length: {len(docs[0]['content'])} chars")
        print(f"  Has full text: {docs[0]['metadata'].get('has_full_text', False)}")

    # Try to estimate total by fetching with high offset
    print("\n📈 Attempting to estimate total documents...")
    print("   (Testing with offset=10000)...")

    test_connector = ChileBCNConnector(config={'limit': 1})
    try:
        high_offset_docs = test_connector.fetch_documents(limit=1, offset=10000)
        if high_offset_docs:
            print("   ✅ Documents exist beyond offset 10,000")
            print("   Estimated minimum: 10,000+ documents")
    except:
        print("   ℹ️ Could not access offset 10,000 - testing lower offsets...")

        for offset in [5000, 2000, 1000]:
            try:
                test_docs = test_connector.fetch_documents(limit=1, offset=offset)
                if test_docs:
                    print(f"   ✅ Documents exist at offset {offset}")
                    print(f"   Estimated minimum: {offset}+ documents")
                    break
            except:
                continue

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("  - Start with batch size of 50-100 documents per job")
print("  - Schedule jobs every 10-15 minutes")
print("  - Monitor first few jobs to adjust strategy")
print("=" * 80)
