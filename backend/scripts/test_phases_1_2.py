#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phases 1 & 2
Tests all functionality before proceeding to Phase 3
"""

import requests
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class TestSuite:
    """Comprehensive test suite for DermaAI CKPA backend"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}{text.center(70)}{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}\n")
    
    def print_test(self, name: str):
        """Print test name"""
        print(f"Testing: {name}...", end=" ")
    
    def print_pass(self, message: str = "PASS"):
        """Print pass message"""
        print(f"{GREEN}✓ {message}{RESET}")
        self.passed += 1
    
    def print_fail(self, message: str = "FAIL"):
        """Print fail message"""
        print(f"{RED}✗ {message}{RESET}")
        self.failed += 1
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{YELLOW}⚠ {message}{RESET}")
        self.warnings += 1
    
    def test_phase1_backend_running(self) -> bool:
        """Test: Backend server is running"""
        self.print_test("Phase 1 - Backend server running")
        try:
            response = requests.get(f"{self.api_url}/api/health", timeout=5)
            if response.status_code == 200:
                self.print_pass("Backend is running")
                return True
            else:
                self.print_fail(f"Backend returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Cannot connect to backend: {str(e)}")
            return False
    
    def test_phase1_health_checks(self) -> bool:
        """Test: All health check endpoints"""
        self.print_test("Phase 1 - Health check endpoints")
        
        endpoints = [
            "/api/health",
            "/api/health/detailed",
            "/api/health/ready",
            "/api/health/live"
        ]
        
        all_pass = True
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                if response.status_code != 200:
                    print(f"\n  {RED}✗ {endpoint} returned {response.status_code}{RESET}")
                    all_pass = False
            except Exception as e:
                print(f"\n  {RED}✗ {endpoint} failed: {str(e)}{RESET}")
                all_pass = False
        
        if all_pass:
            self.print_pass(f"All {len(endpoints)} health endpoints working")
            return True
        else:
            self.print_fail("Some health endpoints failed")
            return False
    
    def test_phase1_api_documentation(self) -> bool:
        """Test: API documentation accessible"""
        self.print_test("Phase 1 - API documentation")
        try:
            response = requests.get(f"{self.api_url}/docs", timeout=5)
            if response.status_code == 200:
                self.print_pass("API docs accessible at /docs")
                return True
            else:
                self.print_fail(f"API docs returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Cannot access API docs: {str(e)}")
            return False
    
    def test_phase1_cors_config(self) -> bool:
        """Test: CORS configuration"""
        self.print_test("Phase 1 - CORS configuration")
        try:
            response = requests.options(
                f"{self.api_url}/api/health",
                headers={"Origin": "http://localhost:5173"},
                timeout=5
            )
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            if cors_header:
                self.print_pass(f"CORS configured: {cors_header}")
                return True
            else:
                self.print_warning("CORS headers not found (might be OK)")
                return True
        except Exception as e:
            self.print_warning(f"CORS check inconclusive: {str(e)}")
            return True
    
    def test_phase1_chat_endpoint(self) -> bool:
        """Test: Chat endpoint responds"""
        self.print_test("Phase 1 - Chat endpoint")
        try:
            payload = {
                "question": "Test question",
                "conversation_id": "test_123",
                "history": []
            }
            response = requests.post(
                f"{self.api_url}/api/chat",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "answer" in data:
                    self.print_pass("Chat endpoint working (placeholder)")
                    return True
                else:
                    self.print_fail("Chat response missing 'answer' field")
                    return False
            else:
                self.print_fail(f"Chat endpoint returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Chat endpoint failed: {str(e)}")
            return False
    
    def test_phase2_document_endpoints(self) -> bool:
        """Test: Document endpoints exist"""
        self.print_test("Phase 2 - Document endpoints")
        try:
            response = requests.get(f"{self.api_url}/api/documents/", timeout=5)
            if response.status_code == 200:
                self.print_pass("Document endpoints responding")
                return True
            else:
                self.print_fail(f"Document endpoint returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Document endpoints failed: {str(e)}")
            return False
    
    def test_phase2_directories_exist(self) -> bool:
        """Test: Required directories exist"""
        self.print_test("Phase 2 - Required directories")
        
        # Assume we're running from backend directory
        required_dirs = [
            "data/uploads",
            "data/processed",
            "logs"
        ]
        
        all_exist = True
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                print(f"\n  {RED}✗ Missing: {dir_path}{RESET}")
                all_exist = False
        
        if all_exist:
            self.print_pass("All required directories exist")
            return True
        else:
            self.print_fail("Some directories missing")
            return False
    
    def test_phase2_chunking_module(self) -> bool:
        """Test: Chunking module works"""
        self.print_test("Phase 2 - Text chunking module")
        try:
            # Try to import and use chunking module
            sys.path.insert(0, os.getcwd())
            from app.utils.chunking import chunk_text_simple
            
            test_text = "This is a test sentence. " * 100
            chunks = chunk_text_simple(test_text, chunk_size=200)
            
            if len(chunks) > 0:
                self.print_pass(f"Chunking works ({len(chunks)} chunks created)")
                return True
            else:
                self.print_fail("Chunking returned no chunks")
                return False
        except ImportError as e:
            self.print_fail(f"Cannot import chunking module: {str(e)}")
            return False
        except Exception as e:
            self.print_fail(f"Chunking failed: {str(e)}")
            return False
    
    def test_phase2_document_processor(self) -> bool:
        """Test: Document processor module exists"""
        self.print_test("Phase 2 - Document processor module")
        try:
            from app.utils.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            self.print_pass("Document processor initialized")
            return True
        except ImportError as e:
            self.print_fail(f"Cannot import document processor: {str(e)}")
            return False
        except Exception as e:
            self.print_fail(f"Document processor failed: {str(e)}")
            return False
    
    def test_phase2_processed_documents(self) -> bool:
        """Test: Check if any documents are processed"""
        self.print_test("Phase 2 - Processed documents")
        
        processed_dir = Path("data/processed")
        if not processed_dir.exists():
            self.print_warning("Processed directory doesn't exist")
            return True
        
        processed_files = list(processed_dir.glob("*_processed.json"))
        
        if len(processed_files) > 0:
            self.print_pass(f"Found {len(processed_files)} processed document(s)")
            return True
        else:
            self.print_warning("No processed documents found (upload some to test)")
            return True
    
    def test_phase2_document_list_api(self) -> bool:
        """Test: Document list API returns data"""
        self.print_test("Phase 2 - Document list API")
        try:
            response = requests.get(f"{self.api_url}/api/documents/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "documents" in data:
                    num_docs = len(data["documents"])
                    self.print_pass(f"API lists {num_docs} document(s)")
                    return True
                else:
                    self.print_fail("Response missing 'documents' field")
                    return False
            else:
                self.print_fail(f"List API returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Document list API failed: {str(e)}")
            return False
    
    def test_phase2_stats_endpoint(self) -> bool:
        """Test: Stats endpoint works"""
        self.print_test("Phase 2 - Statistics endpoint")
        try:
            response = requests.get(
                f"{self.api_url}/api/documents/stats/summary",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.print_pass(f"Stats: {data.get('total_uploaded', 0)} uploaded, "
                              f"{data.get('total_processed', 0)} processed")
                return True
            else:
                self.print_fail(f"Stats endpoint returned {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"Stats endpoint failed: {str(e)}")
            return False
    
    def test_configuration(self) -> bool:
        """Test: Configuration is properly set"""
        self.print_test("Configuration - Environment variables")
        
        config_issues = []
        
        # Check if .env exists
        if not os.path.exists(".env"):
            config_issues.append(".env file not found")
        
        # Check health/detailed for API key status
        try:
            response = requests.get(f"{self.api_url}/api/health/detailed", timeout=5)
            if response.status_code == 200:
                data = response.json()
                deps = data.get("dependencies", {})
                
                # Check API keys
                for service in ["anthropic", "pinecone", "openai"]:
                    if service in deps:
                        if not deps[service].get("key_present"):
                            config_issues.append(f"{service.upper()} API key not set")
        except:
            pass
        
        if config_issues:
            self.print_warning(f"Config issues: {', '.join(config_issues)}")
            print(f"  {YELLOW}Note: API keys needed for Phase 3+{RESET}")
            return True
        else:
            self.print_pass("Configuration looks good")
            return True
    
    def test_dependencies(self) -> bool:
        """Test: Required Python packages installed"""
        self.print_test("Dependencies - Python packages")
        
        required = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "structlog",
            "PyPDF2",
            "pdfplumber"
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package.lower().replace("-", "_"))
            except ImportError:
                missing.append(package)
        
        if missing:
            self.print_fail(f"Missing packages: {', '.join(missing)}")
            return False
        else:
            self.print_pass("All required packages installed")
            return True
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"\n{BLUE}╔{'═' * 68}╗{RESET}")
        print(f"{BLUE}║{'DermaAI CKPA - Comprehensive Test Suite'.center(68)}║{RESET}")
        print(f"{BLUE}║{'Phases 1 & 2 Verification'.center(68)}║{RESET}")
        print(f"{BLUE}╚{'═' * 68}╝{RESET}")
        
        # Phase 1 Tests
        self.print_header("PHASE 1: Backend Foundation Tests")
        self.test_phase1_backend_running()
        self.test_phase1_health_checks()
        self.test_phase1_api_documentation()
        self.test_phase1_cors_config()
        self.test_phase1_chat_endpoint()
        
        # Phase 2 Tests
        self.print_header("PHASE 2: Document Processing Tests")
        self.test_phase2_directories_exist()
        self.test_phase2_document_endpoints()
        self.test_phase2_chunking_module()
        self.test_phase2_document_processor()
        self.test_phase2_processed_documents()
        self.test_phase2_document_list_api()
        self.test_phase2_stats_endpoint()
        
        # Configuration & Dependencies
        self.print_header("Configuration & Dependencies")
        self.test_configuration()
        self.test_dependencies()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}{'TEST SUMMARY'.center(70)}{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")
        print(f"\n  Total Tests:  {total}")
        print(f"  {GREEN}Passed:       {self.passed} ({pass_rate:.1f}%){RESET}")
        print(f"  {RED}Failed:       {self.failed}{RESET}")
        print(f"  {YELLOW}Warnings:     {self.warnings}{RESET}")
        
        print(f"\n{BLUE}{'=' * 70}{RESET}\n")
        
        if self.failed == 0:
            print(f"{GREEN}✓ ALL TESTS PASSED!{RESET}")
            print(f"{GREEN}✓ Ready to proceed to Phase 3{RESET}\n")
            return 0
        else:
            print(f"{RED}✗ SOME TESTS FAILED{RESET}")
            print(f"{RED}✗ Fix issues before proceeding to Phase 3{RESET}\n")
            return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Phases 1 & 2")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Run tests
    suite = TestSuite(api_url=args.api_url)
    exit_code = suite.run_all_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
