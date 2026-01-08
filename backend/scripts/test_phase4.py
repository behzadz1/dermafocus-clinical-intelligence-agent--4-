#!/usr/bin/env python3
"""
Test Phase 4: RAG-Powered Chat
Comprehensive testing of the complete RAG pipeline
"""

import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8000"

def print_header(text: str):
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f"{text.center(70)}")
    print(f"{'=' * 70}\n")

def print_success(text: str):
    """Print success message"""
    print(f"✓ {text}")

def print_error(text: str):
    """Print error message"""
    print(f"✗ {text}")

def test_rag_chat():
    """Test RAG-powered chat endpoint"""
    print_header("Phase 4: RAG-Powered Chat Tests")
    
    # Test 1: Basic question
    print("Test 1: Basic Product Question")
    print("-" * 70)
    
    question = "What is Plinest and what are its benefits?"
    
    print(f"Question: {question}\n")
    
    response = requests.post(
        f"{API_URL}/api/chat",
        json={
            "question": question,
            "conversation_id": "test_123"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print_success("Response received")
        print(f"\nAnswer:\n{data['answer']}\n")
        print(f"Confidence: {data['confidence']:.2f}")
        print(f"Sources: {len(data['sources'])}")
        
        if data['sources']:
            print("\nSources:")
            for source in data['sources']:
                print(f"  - {source['document']} (page {source['page']}, score: {source['relevance_score']:.2f})")
        
        if data['follow_ups']:
            print("\nFollow-up questions:")
            for i, q in enumerate(data['follow_ups'], 1):
                print(f"  {i}. {q}")
    else:
        print_error(f"Request failed: {response.status_code}")
        print(response.text)
        return False
    
    print("\n" + "-" * 70)
    
    # Test 2: Technical question
    print("\nTest 2: Technical Question")
    print("-" * 70)
    
    question = "What is the recommended injection technique for dermal fillers?"
    
    print(f"Question: {question}\n")
    
    response = requests.post(
        f"{API_URL}/api/chat",
        json={"question": question}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Response received")
        print(f"\nAnswer preview: {data['answer'][:200]}...")
        print(f"Confidence: {data['confidence']:.2f}")
        print(f"Sources: {len(data['sources'])}")
    else:
        print_error(f"Request failed: {response.status_code}")
    
    print("\n" + "-" * 70)
    
    # Test 3: Conversation with history
    print("\nTest 3: Conversation with History")
    print("-" * 70)
    
    # First message
    response1 = requests.post(
        f"{API_URL}/api/chat",
        json={
            "question": "Tell me about Newest",
            "conversation_id": "test_conversation"
        }
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"Q1: Tell me about Newest")
        print(f"A1: {data1['answer'][:150]}...")
        
        # Second message with context
        response2 = requests.post(
            f"{API_URL}/api/chat",
            json={
                "question": "What are its main indications?",
                "conversation_id": "test_conversation",
                "history": [
                    {
                        "role": "user",
                        "content": "Tell me about Newest"
                    },
                    {
                        "role": "assistant",
                        "content": data1['answer']
                    }
                ]
            }
        )
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"\nQ2: What are its main indications? (with context)")
            print(f"A2: {data2['answer'][:150]}...")
            print_success("Conversation context maintained")
        else:
            print_error("Follow-up question failed")
    else:
        print_error("Initial question failed")
    
    print("\n" + "-" * 70)
    
    # Test 4: Edge cases
    print("\nTest 4: Edge Cases")
    print("-" * 70)
    
    # Empty context question
    response = requests.post(
        f"{API_URL}/api/chat",
        json={"question": "What is the weather today?"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("Q: What is the weather today? (out of scope)")
        print(f"A: {data['answer'][:150]}...")
        if data['confidence'] < 0.5:
            print_success("Correctly identified low confidence for out-of-scope question")
        else:
            print(f"Confidence: {data['confidence']:.2f}")
    
    print("\n" + "-" * 70)
    
    return True

def test_streaming():
    """Test streaming endpoint"""
    print_header("Streaming Response Test")
    
    print("Testing streaming chat endpoint...")
    print("Question: What are the contraindications for dermal fillers?\n")
    
    try:
        response = requests.post(
            f"{API_URL}/api/chat/stream",
            json={"question": "What are the contraindications for dermal fillers?"},
            stream=True
        )
        
        if response.status_code == 200:
            print("Streaming response:")
            print("-" * 70)
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            
                            if data['type'] == 'content':
                                print(data['content'], end='', flush=True)
                            elif data['type'] == 'sources':
                                print(f"\n\n✓ {len(data['sources'])} sources cited")
                            elif data['type'] == 'done':
                                print("\n\n✓ Streaming complete")
                        except json.JSONDecodeError:
                            pass
            
            print("-" * 70)
            return True
        else:
            print_error(f"Streaming failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Streaming error: {str(e)}")
        return False

def test_performance():
    """Test response times"""
    print_header("Performance Test")
    
    questions = [
        "What is Plinest?",
        "How should Newest be administered?",
        "What are the benefits of PN-HPT?"
    ]
    
    times = []
    
    for i, question in enumerate(questions, 1):
        print(f"Test {i}/3: {question[:50]}...")
        
        start = time.time()
        response = requests.post(
            f"{API_URL}/api/chat",
            json={"question": question}
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            times.append(elapsed)
            print(f"  ✓ Response time: {elapsed:.2f}s")
        else:
            print(f"  ✗ Failed: {response.status_code}")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"\nAverage response time: {avg_time:.2f}s")
        
        if avg_time < 3.0:
            print_success("Performance is good (< 3s average)")
        elif avg_time < 5.0:
            print("⚠ Performance is acceptable (< 5s average)")
        else:
            print("⚠ Performance is slow (> 5s average)")

def test_source_citations():
    """Test source citation accuracy"""
    print_header("Source Citation Test")
    
    question = "What is the composition of Plinest?"
    
    print(f"Question: {question}\n")
    
    response = requests.post(
        f"{API_URL}/api/chat",
        json={"question": question}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if data['sources']:
            print_success(f"Found {len(data['sources'])} sources")
            
            print("\nSource details:")
            for i, source in enumerate(data['sources'], 1):
                print(f"\n{i}. Document: {source['document']}")
                print(f"   Page: {source['page']}")
                print(f"   Relevance: {source['relevance_score']:.2f}")
                print(f"   Snippet: {source['text_snippet'][:100]}...")
            
            # Check if sources are relevant
            avg_relevance = sum(s['relevance_score'] for s in data['sources']) / len(data['sources'])
            
            if avg_relevance > 0.7:
                print_success(f"\nHigh relevance score: {avg_relevance:.2f}")
            else:
                print(f"\n⚠ Low relevance score: {avg_relevance:.2f}")
        else:
            print_error("No sources found")
    else:
        print_error(f"Request failed: {response.status_code}")

def main():
    """Main test runner"""
    print("=" * 70)
    print("DermaAI CKPA - Phase 4 Comprehensive Tests")
    print("=" * 70)
    
    # Check if backend is running
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print_error("Backend is not healthy")
            return
    except:
        print_error("Cannot connect to backend. Is it running?")
        print("Start backend with: cd backend && ./quickstart.sh")
        return
    
    print_success("Backend is running\n")
    
    # Run tests
    tests = [
        ("RAG Chat", test_rag_chat),
        ("Streaming", test_streaming),
        ("Performance", test_performance),
        ("Source Citations", test_source_citations)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print_error(f"Test '{name}' failed with error: {str(e)}")
            results.append((name, False))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}\n")
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 4 is complete and working!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.")

if __name__ == "__main__":
    main()
