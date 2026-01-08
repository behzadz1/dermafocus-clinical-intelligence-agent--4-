#!/usr/bin/env python3
"""
Script to diagnose vector ID collisions in Pinecone
Run this first to check if you have collision issues
"""
import os
from pinecone import Pinecone
from collections import Counter

def diagnose_collisions():
    """
    Diagnose Pinecone vector ID collisions
    """
    # Load API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found in environment")
        print("   Set it with: export PINECONE_API_KEY=your_key")
        return None
    
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index("dermaai-ckpa")
    except Exception as e:
        print(f"❌ Error connecting to Pinecone: {e}")
        return None
    
    print("🔍 Diagnosing Pinecone Vector ID Collisions")
    print("=" * 70)
    
    # Get index stats
    try:
        stats = index.describe_index_stats()
        print(f"\n📊 Index Stats:")
        print(f"  Total vectors: {stats.total_vector_count}")
        print(f"  Dimensions: {stats.dimension}")
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return None
    
    # Fetch sample vectors
    vector_ids = []
    doc_counts = Counter()
    
    print(f"\n🔍 Sampling vectors...")
    
    try:
        # Query with dummy vector to get IDs
        dummy_query = [0.0] * stats.dimension
        results = index.query(
            vector=dummy_query, 
            top_k=min(10000, stats.total_vector_count),
            namespace="default",
            include_metadata=True
        )
        
        print(f"📋 Retrieved {len(results.matches)} vectors")
        
        # Analyze IDs and metadata
        for match in results.matches:
            vid = match.id
            vector_ids.append(vid)
            
            # Try to extract document name from metadata
            if match.metadata and 'document_name' in match.metadata:
                doc_counts[match.metadata['document_name']] += 1
            elif match.metadata and 'document_id' in match.metadata:
                doc_counts[match.metadata['document_id']] += 1
    
    except Exception as e:
        print(f"❌ Error querying vectors: {e}")
        return None
    
    # Analyze vector IDs
    print(f"\n🔑 Vector ID Analysis:")
    print(f"  Total IDs retrieved: {len(vector_ids)}")
    print(f"  Unique IDs: {len(set(vector_ids))}")
    
    if len(set(vector_ids)) < len(vector_ids):
        duplicates = len(vector_ids) - len(set(vector_ids))
        print(f"  ⚠️  WARNING: {duplicates} duplicate IDs detected!")
    else:
        print(f"  ✅ All sampled IDs are unique")
    
    # Check ID format patterns
    print(f"\n📝 ID Format Analysis (first 10 IDs):")
    id_patterns = {
        "composite": 0,      # Contains "::"
        "simple_chunk": 0,   # Starts with "chunk_"
        "uuid": 0,           # Looks like UUID
        "other": 0
    }
    
    for vid in vector_ids[:100]:  # Sample first 100
        if "::" in vid:
            id_patterns["composite"] += 1
        elif vid.startswith("chunk_"):
            id_patterns["simple_chunk"] += 1
        elif len(vid) == 36 and vid.count("-") == 4:
            id_patterns["uuid"] += 1
        else:
            id_patterns["other"] += 1
    
    for pattern, count in id_patterns.items():
        if count > 0:
            print(f"  {pattern}: {count}")
    
    # Show sample IDs
    print(f"\n📋 Sample Vector IDs:")
    for vid in vector_ids[:5]:
        print(f"  {vid}")
    
    # Document distribution
    print(f"\n📚 Document Distribution:")
    if doc_counts:
        print(f"  Unique documents: {len(doc_counts)}")
        print(f"\n  Top 10 documents by chunk count:")
        for doc, count in doc_counts.most_common(10):
            print(f"    {doc}: {count} chunks")
    else:
        print("  ⚠️  No document metadata found!")
        print("  This could indicate missing metadata or old uploads")
    
    # Analysis and recommendations
    print(f"\n🎯 Analysis:")
    print(f"  Expected: 30+ documents, ~135+ chunks total")
    print(f"  Actual: {len(doc_counts)} documents, {stats.total_vector_count} vectors")
    
    issues = []
    
    # Check for collision pattern
    if id_patterns["simple_chunk"] > 0:
        issues.append("collision_risk")
        print(f"\n  ❌ COLLISION RISK DETECTED:")
        print(f"     Found {id_patterns['simple_chunk']} vectors with 'chunk_X' pattern")
        print(f"     These IDs are NOT globally unique and WILL collide!")
    
    # Check document count
    if len(doc_counts) < 10 and len(doc_counts) > 0:
        issues.append("missing_documents")
        print(f"\n  ⚠️  LOW DOCUMENT COUNT:")
        print(f"     Only {len(doc_counts)} documents detected")
        print(f"     Expected: 30+ documents")
        print(f"     Possible cause: Vector ID collisions overwriting data")
    
    # Check vector count
    expected_min = 100  # Conservative estimate
    if stats.total_vector_count < expected_min:
        issues.append("low_vector_count")
        print(f"\n  ⚠️  LOW VECTOR COUNT:")
        print(f"     Only {stats.total_vector_count} vectors in index")
        print(f"     Expected: {expected_min}+ vectors")
    
    # Recommendations
    print(f"\n" + "=" * 70)
    if issues:
        print("❌ ISSUES DETECTED - ACTION REQUIRED")
        print(f"\n🔧 Recommended Actions:")
        
        if "collision_risk" in issues:
            print(f"\n  1. CRITICAL: Fix vector ID generation")
            print(f"     - Use globally unique IDs: doc_id::page::chunk::hash")
            print(f"     - See: CRITICAL_FIX_VECTOR_ID_COLLISIONS.md")
        
        if "missing_documents" in issues or "low_vector_count" in issues:
            print(f"\n  2. Re-upload all documents with fixed IDs")
            print(f"     - Run: python clean_and_reupload.py")
            print(f"     - Then: python process_documents_fixed.py")
        
        print(f"\n  3. Verify after fix:")
        print(f"     - Run this script again")
        print(f"     - Check document count matches expectations")
        print(f"     - Test RAG quality with queries")
    else:
        print("✅ NO MAJOR ISSUES DETECTED")
        print(f"\n💡 Your vector IDs appear to be properly formatted")
        print(f"   However, verify RAG quality with test queries")
    
    return {
        "total_vectors": stats.total_vector_count,
        "unique_ids_sampled": len(set(vector_ids)),
        "documents": len(doc_counts),
        "has_collision_risk": id_patterns["simple_chunk"] > 0,
        "id_patterns": id_patterns,
        "issues": issues
    }

if __name__ == "__main__":
    print()
    result = diagnose_collisions()
    print()
    
    if result:
        if result["has_collision_risk"]:
            print("⚠️  CRITICAL: Vector ID collisions detected!")
            print("   See CRITICAL_FIX_VECTOR_ID_COLLISIONS.md for fix")
            exit(1)
        elif result["issues"]:
            print("⚠️  Issues detected - review recommendations above")
            exit(1)
        else:
            print("✅ Diagnosis complete - no critical issues found")
            exit(0)
    else:
        print("❌ Diagnosis failed - check errors above")
        exit(1)
