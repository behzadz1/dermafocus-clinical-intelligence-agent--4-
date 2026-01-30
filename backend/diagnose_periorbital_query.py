#!/usr/bin/env python3
"""
Diagnostic script to understand why periorbital query returned incorrect answer
"""
import sys
sys.path.insert(0, '.')

from app.services.rag_service import get_rag_service
from app.services.claude_service import get_claude_service

print("="*80)
print("DIAGNOSTIC: Periorbital Query Analysis")
print("="*80)

query = "can newest be used for pre orbital"
print(f"\nQuery: '{query}'\n")

# Get RAG service
rag = get_rag_service()

# Step 1: What documents are retrieved?
print("\n" + "="*80)
print("STEP 1: Document Retrieval")
print("="*80)

results = rag.search(query=query, top_k=8)

print(f"\n✅ Retrieved {len(results)} documents\n")

for i, r in enumerate(results, 1):
    print(f"\n{i}. RELEVANCE SCORE: {r['score']:.4f}")
    print(f"   Document: {r['metadata'].get('document_name', 'Unknown')}")
    print(f"   Page: {r['metadata'].get('page_number', 'N/A')}")
    print(f"   Section: {r['metadata'].get('section', 'N/A')}")
    print(f"   Type: {r['metadata'].get('doc_type', 'Unknown')}")
    print(f"\n   CONTENT:\n   {r['text'][:300]}...")
    print("\n" + "-"*80)

# Step 2: What context is built?
print("\n" + "="*80)
print("STEP 2: Context Building")
print("="*80)

context_results = rag.get_context_for_query(query=query, top_k=8)
context = context_results['context']
sources = context_results['sources']

print(f"\n✅ Built context from {len(sources)} sources")
print(f"Context length: {len(context)} characters\n")

print("CONTEXT SENT TO CLAUDE:")
print("-"*80)
print(context[:1500])
print("\n[... truncated ...]")
print("-"*80)

# Step 3: Check what documents we're missing
print("\n" + "="*80)
print("STEP 3: Missing Critical Documents Analysis")
print("="*80)

print("\n⚠️  CRITICAL ISSUE IDENTIFIED:")
print("   The 'Mastelli_Aesthetic_Medicine_Portfolio' document is NOT in the database!")
print("   This document contains the definitive answer that:")
print("   - Newest® is for Face, Neck, Décolleté (NOT periorbital)")
print("   - Plinest Eye is the dedicated product for periorbital area")
print("\n   Without this document, the system retrieves generic information about")
print("   polynucleotides and periocular treatment, leading to incorrect conclusions.")

# Step 4: What documents DO we have about products?
print("\n" + "="*80)
print("STEP 4: Available Product Documents")
print("="*80)

product_query_results = rag.search(query="Newest Plinest Eye product indications", top_k=10)
product_docs = set()
for r in product_query_results:
    doc_name = r['metadata'].get('document_name', 'Unknown')
    product_docs.add(doc_name)

print(f"\nDocuments containing product information:")
for doc in sorted(product_docs):
    print(f"  - {doc}")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)
print("""
1. ADD the Mastelli_Aesthetic_Medicine_Portfolio.pdf document
   - This is the authoritative source for product indications
   - Contains clear distinction between products and their indicated areas

2. Alternatively, create a structured product metadata file
   - Define each product with its specific indications
   - Use this as a source of truth for product queries

3. Improve reranking logic
   - Prioritize "official" product documentation over case studies
   - Weight Fact Sheets and Brochures higher for product queries

4. Add negative examples
   - When retrieving context, also mention what a product is NOT indicated for
   - This helps prevent incorrect extrapolations
""")
