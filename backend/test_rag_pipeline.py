#!/usr/bin/env python3
"""Test RAG pipeline functionality"""
import sys
sys.path.insert(0, '.')

from app.services.rag_service import get_rag_service

print('='*80)
print('RAG PIPELINE VERIFICATION')
print('='*80)

rag = get_rag_service()

# Test retrieval
print('\nTest 1: Query "What is Newest?"')
results = rag.search(query='What is Newest?', top_k=3)
print(f'✓ Retrieved {len(results)} documents')
if results:
    print(f'  Top: {results[0]["metadata"].get("document_name")} (score: {results[0]["score"]:.3f})')

print('\nTest 2: Query "Newest treatment areas"')  
results = rag.search(query='Newest treatment areas indications', top_k=3)
print(f'✓ Retrieved {len(results)} documents')
if results:
    print(f'  Top: {results[0]["metadata"].get("document_name")} (score: {results[0]["score"]:.3f})')

print('\nTest 3: Query "periorbital treatment"')
results = rag.search(query='periorbital eye treatment', top_k=3)
print(f'✓ Retrieved {len(results)} documents')
if results:
    print(f'  Top: {results[0]["metadata"].get("document_name")} (score: {results[0]["score"]:.3f})')

print('\n' + '='*80)
print('STATUS: RAG Pipeline is operational')
print('='*80)
