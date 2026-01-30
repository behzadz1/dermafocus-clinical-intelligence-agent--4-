#!/usr/bin/env python3
"""
Test LLM API Connections
Tests OpenAI (embeddings) and Anthropic (responses)
"""
import sys
sys.path.insert(0, '.')

print('\n' + '=' * 70)
print('Testing LLM API Connections')
print('=' * 70)

# Test 1: OpenAI Embeddings
print('\n1️⃣  Testing OpenAI Embeddings API')
print('-' * 70)
try:
    from app.services.embedding_service import get_embedding_service
    embedding_service = get_embedding_service()
    
    # Generate a test embedding
    test_text = 'What is Newest polynucleotide?'
    embedding = embedding_service.embed_query(test_text)
    
    print('✅ OpenAI Connection: SUCCESS')
    print(f'   Model: {embedding_service.model}')
    print(f'   Embedding dimension: {len(embedding)}')
    print(f'   Sample values: [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ...]')
except Exception as e:
    print('❌ OpenAI Connection: FAILED')
    print(f'   Error: {str(e)}')
    import traceback
    traceback.print_exc()

# Test 2: Anthropic Claude
print('\n2️⃣  Testing Anthropic Claude API')
print('-' * 70)
try:
    from anthropic import Anthropic
    import os
    
    # Direct API test
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        from app.config import settings
        api_key = settings.anthropic_api_key
    
    client = Anthropic(api_key=api_key)
    
    # Simple test message
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say 'Hello from Claude!' in one sentence."}]
    )
    
    response_text = message.content[0].text
    
    print('✅ Anthropic Connection: SUCCESS')
    print(f'   Model: claude-sonnet-4-20250514')
    print(f'   Max tokens: 100')
    print(f'   API key configured: Yes')
    print(f'\n   Test Response: "{response_text}"')
except Exception as e:
    print('❌ Anthropic Connection: FAILED')
    print(f'   Error: {str(e)}')
    import traceback
    traceback.print_exc()

# Test 3: Pinecone Vector Database
print('\n3️⃣  Testing Pinecone Vector Database')
print('-' * 70)
try:
    from app.services.pinecone_service import get_pinecone_service
    pinecone_service = get_pinecone_service()
    
    stats = pinecone_service.get_index_stats()
    
    print('✅ Pinecone Connection: SUCCESS')
    print(f'   Index: {pinecone_service.index_name}')
    print(f'   Namespace: {pinecone_service.namespace}')
    print(f'   Total vectors: {stats["total_vector_count"]}')
    print(f'   Dimension: {stats["dimension"]}')
except Exception as e:
    print('❌ Pinecone Connection: FAILED')
    print(f'   Error: {str(e)}')
    import traceback
    traceback.print_exc()

# Test 4: Full RAG Pipeline
print('\n4️⃣  Testing Full RAG Pipeline (End-to-End)')
print('-' * 70)
try:
    from app.services.rag_service import get_rag_service
    rag_service = get_rag_service()
    
    # Test search
    test_query = 'What is Newest used for?'
    results = rag_service.search(query=test_query, top_k=3)
    
    print('✅ RAG Pipeline: SUCCESS')
    print(f'   Test Query: "{test_query}"')
    print(f'   Results found: {len(results)}')
    
    if results:
        print(f'\n   Top Result:')
        print(f'     - Score: {results[0]["score"]:.4f}')
        print(f'     - Document: {results[0]["metadata"].get("document_name", "Unknown")}')
        print(f'     - Text preview: "{results[0]["text"][:100]}..."')
    else:
        print('   ⚠️  No results found (database may be empty)')
        
except Exception as e:
    print('❌ RAG Pipeline: FAILED')
    print(f'   Error: {str(e)}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 70)
print('✅ All Connection Tests Complete!')
print('=' * 70 + '\n')
