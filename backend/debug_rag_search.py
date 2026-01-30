#!/usr/bin/env python3
"""
Debug RAG Search Issue
Check vector structure and test search with various parameters
"""
import sys
sys.path.insert(0, '.')

print('\n' + '=' * 70)
print('RAG Search Diagnostics')
print('=' * 70)

# Step 1: Check vector structure
print('\n1️⃣  Inspecting Vector Structure')
print('-' * 70)
try:
    from app.services.pinecone_service import get_pinecone_service
    from app.services.embedding_service import get_embedding_service
    
    pinecone = get_pinecone_service()
    embedding = get_embedding_service()
    
    # Get stats
    stats = pinecone.get_index_stats()
    print(f'Total vectors: {stats["total_vector_count"]}')
    print(f'Dimension: {stats["dimension"]}')
    print(f'Namespaces: {stats.get("namespaces", {})}')
    
    # Query a few random vectors
    dummy_vector = [0.0] * 1536
    sample = pinecone.query(
        query_vector=dummy_vector,
        top_k=3,
        namespace="default",
        include_metadata=True
    )
    
    print(f'\nSample vectors retrieved: {len(sample["matches"])}')
    if sample["matches"]:
        print('\nFirst vector metadata:')
        first = sample["matches"][0]
        print(f'  ID: {first["id"]}')
        print(f'  Score: {first["score"]}')
        print(f'  Metadata keys: {list(first["metadata"].keys())}')
        for key, value in first["metadata"].items():
            if key != "text":
                print(f'    {key}: {value}')
            else:
                print(f'    text: "{value[:100]}..."')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()

# Step 2: Test search with real query
print('\n2️⃣  Testing Search with Real Query')
print('-' * 70)
try:
    test_query = "What is Newest?"
    
    # Generate embedding
    query_vector = embedding.embed_query(test_query)
    print(f'Query: "{test_query}"')
    print(f'Embedding generated: {len(query_vector)} dimensions')
    
    # Test with different score thresholds
    for min_score in [0.0, 0.3, 0.5, 0.7]:
        results = pinecone.query(
            query_vector=query_vector,
            top_k=5,
            namespace="default",
            include_metadata=True
        )
        
        # Filter by score
        filtered = [r for r in results["matches"] if r["score"] >= min_score]
        
        print(f'\n  Min score {min_score:.1f}: {len(filtered)} results')
        if filtered:
            print(f'    Top score: {filtered[0]["score"]:.4f}')
            print(f'    Top doc: {filtered[0]["metadata"].get("document_name", "Unknown")}')
            print(f'    Text: "{filtered[0]["metadata"].get("text", "")[:80]}..."')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()

# Step 3: Test RAG service directly
print('\n3️⃣  Testing RAG Service Search')
print('-' * 70)
try:
    from app.services.rag_service import get_rag_service
    rag = get_rag_service()
    
    # Test with different parameters
    for min_score in [0.0, 0.3, 0.5]:
        results = rag.search(
            query="What is Newest?",
            top_k=5,
            min_score=min_score
        )
        
        print(f'\n  Min score {min_score:.1f}: {len(results)} results')
        if results:
            print(f'    Top score: {results[0]["score"]:.4f}')
            print(f'    Metadata: {results[0]["metadata"].get("document_name", "Unknown")}')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 70)
print('Diagnostics Complete')
print('=' * 70 + '\n')
