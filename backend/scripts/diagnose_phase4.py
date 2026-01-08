#!/usr/bin/env python3
"""
Diagnostic Script for Phase 4 Issues
Investigates Performance and Source Citation problems
"""

import requests
import time
import json

API_URL = "http://localhost:8000"

def print_header(text):
    print(f"\n{'='*70}")
    print(f"{text.center(70)}")
    print(f"{'='*70}\n")

def diagnose_performance():
    """Diagnose performance issues"""
    print_header("Performance Diagnostics")
    
    questions = [
        "What is Plinest?",
        "What are the benefits of dermal fillers?",
        "How should Newest be administered?"
    ]
    
    times = []
    details = []
    
    for i, question in enumerate(questions, 1):
        print(f"Test {i}/3: {question}")
        
        start = time.time()
        try:
            response = requests.post(
                f"{API_URL}/api/chat",
                json={"question": question},
                timeout=30
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                times.append(elapsed)
                details.append({
                    "question": question,
                    "time": elapsed,
                    "sources": len(data.get('sources', [])),
                    "confidence": data.get('confidence', 0),
                    "answer_length": len(data.get('answer', ''))
                })
                print(f"  ✓ Time: {elapsed:.2f}s")
                print(f"  - Sources: {len(data.get('sources', []))}")
                print(f"  - Confidence: {data.get('confidence', 0):.2f}")
            else:
                print(f"  ✗ Failed: {response.status_code}")
                print(f"  - Error: {response.text[:100]}")
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout (>30s)")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    print("\n" + "-"*70)
    print("Performance Summary:")
    print("-"*70)
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"Average: {avg_time:.2f}s")
        print(f"Min: {min_time:.2f}s")
        print(f"Max: {max_time:.2f}s")
        
        print("\nPerformance Analysis:")
        if avg_time > 5.0:
            print("❌ SLOW: Average response time >5s")
            print("\nPossible causes:")
            print("  1. Pinecone search is slow (check network)")
            print("  2. Claude API is slow (check API status)")
            print("  3. Too many chunks being retrieved")
            print("  4. OpenAI embedding generation is slow")
            print("\nSuggested fixes:")
            print("  - Reduce VECTOR_SEARCH_TOP_K (try 3 instead of 5)")
            print("  - Reduce CLAUDE_MAX_TOKENS")
            print("  - Check internet connection speed")
        elif avg_time > 3.0:
            print("⚠️  ACCEPTABLE: Average response time 3-5s")
            print("   This is normal for RAG systems with external APIs")
        else:
            print("✓ GOOD: Average response time <3s")
    else:
        print("❌ No successful requests")
    
    return times, details

def diagnose_sources():
    """Diagnose source citation issues"""
    print_header("Source Citation Diagnostics")
    
    # Test with specific question about Plinest
    question = "What is the composition of Plinest?"
    
    print(f"Question: {question}\n")
    
    try:
        response = requests.post(
            f"{API_URL}/api/chat",
            json={"question": question}
        )
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get('sources', [])
            
            print(f"Response received:")
            print(f"  - Answer length: {len(data.get('answer', ''))} chars")
            print(f"  - Sources found: {len(sources)}")
            print(f"  - Confidence: {data.get('confidence', 0):.2f}")
            
            if len(sources) == 0:
                print("\n❌ PROBLEM: No sources returned")
                print("\nPossible causes:")
                print("  1. No vectors in Pinecone")
                print("  2. Query not matching documents")
                print("  3. min_score threshold too high")
                
                # Check if vectors exist
                print("\nChecking Pinecone...")
                stats_response = requests.get(f"{API_URL}/api/search/stats")
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    total_vectors = stats.get('total_vectors', 0)
                    print(f"  Total vectors in Pinecone: {total_vectors}")
                    
                    if total_vectors == 0:
                        print("\n❌ CRITICAL: No vectors in Pinecone!")
                        print("   Run: python3 scripts/upload_vectors.py --verify")
                    else:
                        print(f"  ✓ Vectors exist ({total_vectors})")
                        print("\n  Testing direct search...")
                        
                        # Try direct search
                        search_response = requests.post(
                            f"{API_URL}/api/search/semantic",
                            params={"query": question, "top_k": 5}
                        )
                        
                        if search_response.status_code == 200:
                            search_data = search_response.json()
                            search_results = search_data.get('results', [])
                            print(f"  Direct search found: {len(search_results)} results")
                            
                            if len(search_results) > 0:
                                print("\n  ✓ Search works, but chat endpoint has issue")
                                print("  Problem likely in RAG service context preparation")
                            else:
                                print("\n  ✗ Direct search also found nothing")
                                print("  Problem: Documents don't match query")
                                print("  Try broader query like: 'dermal filler'")
            else:
                print(f"\n✓ Sources found: {len(sources)}")
                print("\nSource details:")
                for i, source in enumerate(sources, 1):
                    print(f"\n{i}. Document: {source.get('document', 'unknown')}")
                    print(f"   Page: {source.get('page', 'N/A')}")
                    print(f"   Relevance: {source.get('relevance_score', 0):.2f}")
                    snippet = source.get('text_snippet', '')
                    print(f"   Snippet: {snippet[:100]}...")
                
                # Check relevance scores
                avg_relevance = sum(s.get('relevance_score', 0) for s in sources) / len(sources)
                
                print(f"\nAverage relevance score: {avg_relevance:.2f}")
                
                if avg_relevance < 0.6:
                    print("⚠️  LOW RELEVANCE: Sources may not be very relevant")
                    print("   This could mean:")
                    print("   - Documents don't contain specific info about this topic")
                    print("   - Need more/better documents")
                    print("   - Query phrasing doesn't match document language")
                elif avg_relevance < 0.7:
                    print("⚠️  ACCEPTABLE: Sources are somewhat relevant")
                else:
                    print("✓ GOOD: Sources are highly relevant")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def check_system_health():
    """Check overall system health"""
    print_header("System Health Check")
    
    checks = [
        ("Backend", f"{API_URL}/api/health"),
        ("Detailed Health", f"{API_URL}/api/health/detailed"),
        ("Pinecone Stats", f"{API_URL}/api/search/stats")
    ]
    
    for name, url in checks:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: OK")
                if "stats" in url:
                    data = response.json()
                    print(f"  Vectors: {data.get('total_vectors', 0)}")
            else:
                print(f"✗ {name}: {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")

def run_diagnostics():
    """Run all diagnostics"""
    print("="*70)
    print("DermaAI CKPA - Phase 4 Diagnostics")
    print("="*70)
    
    # System health
    check_system_health()
    
    # Performance
    times, details = diagnose_performance()
    
    # Sources
    diagnose_sources()
    
    # Summary
    print_header("Diagnostic Summary")
    
    issues = []
    fixes = []
    
    # Analyze performance
    if times and sum(times) / len(times) > 5.0:
        issues.append("Slow performance (>5s average)")
        fixes.append("Reduce VECTOR_SEARCH_TOP_K and CLAUDE_MAX_TOKENS in .env")
    
    # Check sources
    print("\nRecommended Actions:")
    print("-"*70)
    
    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  ❌ {issue}")
        
        print("\nSuggested fixes:")
        for fix in fixes:
            print(f"  → {fix}")
    else:
        print("✓ No major issues detected")
    
    print("\nNext steps:")
    print("  1. Check if vectors are uploaded: curl http://localhost:8000/api/search/stats")
    print("  2. Try manual search: curl -X POST 'http://localhost:8000/api/search/semantic?query=test'")
    print("  3. Check logs: tail -50 backend/logs/app.log")
    print("  4. Verify API keys: curl http://localhost:8000/api/health/detailed")

if __name__ == "__main__":
    run_diagnostics()
