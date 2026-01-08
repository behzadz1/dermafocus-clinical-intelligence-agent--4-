#!/usr/bin/env python3
"""
Batch Document Upload Script
Process multiple documents from a directory and upload to DermaAI CKPA backend

Usage:
    python batch_upload.py <directory> [--doc-type TYPE] [--api-url URL]

Example:
    python batch_upload.py ../data/dermafocus_documents --doc-type product
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Any
import time


class BatchUploader:
    """Upload multiple documents to the backend API"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Args:
            api_url: Base URL of the API
        """
        self.api_url = api_url.rstrip('/')
        self.results = []
    
    def upload_file(
        self,
        file_path: str,
        doc_type: str = "document"
    ) -> Dict[str, Any]:
        """
        Upload a single file
        
        Args:
            file_path: Path to file
            doc_type: Type of document
            
        Returns:
            Result dictionary
        """
        filename = os.path.basename(file_path)
        print(f"Uploading: {filename} (type: {doc_type})...")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post(
                    f"{self.api_url}/api/documents/upload",
                    files=files,
                    params={'doc_type': doc_type},
                    timeout=300  # 5 minutes timeout for large files
                )
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                print(f"  ✓ Success: {data.get('message', 'Uploaded')}")
                return {
                    "success": True,
                    "file": filename,
                    "doc_id": data.get('doc_id'),
                    "status": data.get('status'),
                    "response": data
                }
            else:
                print(f"  ✗ Failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "file": filename,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            return {
                "success": False,
                "file": filename,
                "error": str(e)
            }
    
    def upload_directory(
        self,
        directory: str,
        doc_type: str = "document",
        pattern: str = "*.pdf"
    ) -> List[Dict[str, Any]]:
        """
        Upload all files matching pattern in directory
        
        Args:
            directory: Path to directory
            doc_type: Type of documents
            pattern: File pattern (glob)
            
        Returns:
            List of results
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"Error: Directory not found: {directory}")
            return []
        
        # Find all matching files
        files = list(directory_path.glob(pattern))
        
        if not files:
            print(f"No files matching '{pattern}' found in {directory}")
            return []
        
        print(f"\nFound {len(files)} file(s) to upload")
        print(f"API URL: {self.api_url}")
        print(f"Document type: {doc_type}")
        print("-" * 60)
        
        results = []
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}]")
            result = self.upload_file(str(file_path), doc_type)
            results.append(result)
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
        
        self.results = results
        return results
    
    def print_summary(self):
        """Print summary of upload results"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        
        print("\n" + "=" * 60)
        print("UPLOAD SUMMARY")
        print("=" * 60)
        print(f"Total files:  {total}")
        print(f"Successful:   {successful} ({successful/total*100:.1f}%)" if total > 0 else "Successful:   0")
        print(f"Failed:       {failed}")
        
        if failed > 0:
            print("\nFailed uploads:")
            for result in self.results:
                if not result["success"]:
                    print(f"  ✗ {result['file']}: {result.get('error', 'Unknown error')}")
        
        if successful > 0:
            print("\nSuccessful uploads:")
            for result in self.results:
                if result["success"]:
                    print(f"  ✓ {result['file']} → {result.get('doc_id')}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch upload documents to DermaAI CKPA backend"
    )
    parser.add_argument(
        "directory",
        help="Directory containing documents to upload"
    )
    parser.add_argument(
        "--doc-type",
        default="document",
        choices=["product", "protocol", "clinical_paper", "video", "case_study", "document"],
        help="Type of documents (default: document)"
    )
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="File pattern to match (default: *.pdf)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Create uploader
    uploader = BatchUploader(api_url=args.api_url)
    
    # Check if API is available
    try:
        response = requests.get(f"{args.api_url}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"Warning: API health check failed: {response.status_code}")
            print("Make sure the backend server is running!")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Cannot connect to API at {args.api_url}")
        print(f"  {str(e)}")
        print("\nMake sure the backend server is running:")
        print("  cd backend && ./quickstart.sh")
        sys.exit(1)
    
    # Upload files
    uploader.upload_directory(
        directory=args.directory,
        doc_type=args.doc_type,
        pattern=args.pattern
    )
    
    # Print summary
    uploader.print_summary()


if __name__ == "__main__":
    main()
