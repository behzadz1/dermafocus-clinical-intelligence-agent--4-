#!/usr/bin/env python3
"""
Clean and re-upload all documents to Pinecone

WARNING: This deletes ALL vectors from your Pinecone index!
Use this when you need to start fresh with corrected vector IDs.
"""
import os
import sys
from pinecone import Pinecone
from datetime import datetime


def confirm_deletion():
    """
    Interactive confirmation to prevent accidental deletion
    """
    print("⚠️  CLEAN AND RE-UPLOAD SCRIPT")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This script will DELETE ALL VECTORS from Pinecone!")
    print()
    print("This is necessary when:")
    print("  • You have vector ID collisions (non-unique IDs)")
    print("  • You need to re-upload with corrected vector IDs")
    print("  • You want to start fresh with new documents")
    print()
    print("After deletion, you must re-upload all documents using:")
    print("  python process_documents_fixed.py")
    print()
    print("=" * 70)
    
    # First confirmation
    response1 = input("\nDo you want to DELETE ALL VECTORS? (type 'yes' to confirm): ")
    if response1.lower() != 'yes':
        print("❌ Aborted - no changes made")
        return False
    
    # Second confirmation with index name
    print("\n⚠️  FINAL CONFIRMATION")
    print("This will delete all vectors from index: dermaai-ckpa")
    response2 = input("\nType the index name to confirm: ")
    if response2 != "dermaai-ckpa":
        print("❌ Aborted - index name did not match")
        return False
    
    return True


def backup_metadata(index):
    """
    Export metadata before deletion (for reference)
    """
    print("\n📋 Exporting metadata before deletion...")
    
    try:
        # Query to get sample of metadata
        dummy_query = [0.0] * 1536  # Assuming 1536 dimensions
        results = index.query(
            vector=dummy_query,
            top_k=100,
            include_metadata=True
        )
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"pinecone_backup_{timestamp}.txt"
        
        with open(backup_file, 'w') as f:
            f.write(f"Pinecone Metadata Backup\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Index: dermaai-ckpa\n")
            f.write(f"Vectors sampled: {len(results.matches)}\n")
            f.write("=" * 70 + "\n\n")
            
            # Extract unique documents
            documents = set()
            for match in results.matches:
                if match.metadata and 'document_name' in match.metadata:
                    documents.add(match.metadata['document_name'])
            
            f.write(f"Documents found ({len(documents)}):\n")
            for doc in sorted(documents):
                f.write(f"  - {doc}\n")
            
            f.write("\n" + "=" * 70 + "\n\n")
            f.write("Sample Vector IDs:\n")
            for i, match in enumerate(results.matches[:20], 1):
                f.write(f"  {i}. {match.id}\n")
        
        print(f"✅ Metadata backed up to: {backup_file}")
        print(f"   Documents found: {len(documents)}")
        
        return backup_file
    
    except Exception as e:
        print(f"⚠️  Warning: Could not backup metadata: {e}")
        return None


def clean_pinecone_index():
    """
    Delete all vectors from Pinecone index
    """
    # Check environment variable
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found in environment")
        print("   Set it with: export PINECONE_API_KEY=your_key")
        sys.exit(1)
    
    # Get user confirmation
    if not confirm_deletion():
        sys.exit(0)
    
    # Initialize Pinecone
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index("dermaai-ckpa")
        print("\n✅ Connected to Pinecone")
    except Exception as e:
        print(f"❌ Error connecting to Pinecone: {e}")
        sys.exit(1)
    
    # Get current stats
    try:
        stats = index.describe_index_stats()
        print(f"\n📊 Current Index Stats:")
        print(f"   Total vectors: {stats.total_vector_count}")
        print(f"   Dimensions: {stats.dimension}")
        
        if stats.total_vector_count == 0:
            print("\n✅ Index is already empty - nothing to delete")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        sys.exit(1)
    
    # Backup metadata
    backup_file = backup_metadata(index)
    
    # Final pause before deletion
    print("\n⏸️  Last chance to cancel...")
    input("Press Enter to continue with deletion, or Ctrl+C to abort: ")
    
    # Delete all vectors
    print(f"\n🗑️  Deleting all {stats.total_vector_count} vectors...")
    print("   This may take a moment...")
    
    try:
        try:
            index.delete(delete_all=True, namespace="default")
        except Exception as e:
            if "Namespace not found" in str(e):
                print("   ℹ️  Namespace 'default' not found (already empty)")
            else:
                raise e
        print(f"✅ All vectors deleted from index: dermaai-ckpa")
    except Exception as e:
        print(f"❌ Error deleting vectors: {e}")
        sys.exit(1)
    
    # Verify deletion
    print(f"\n🔍 Verifying deletion...")
    try:
        import time
        time.sleep(2)  # Wait for deletion to propagate
        
        new_stats = index.describe_index_stats()
        print(f"   Vectors remaining: {new_stats.total_vector_count}")
        
        if new_stats.total_vector_count == 0:
            print(f"   ✅ Deletion confirmed")
        else:
            print(f"   ⚠️  Warning: {new_stats.total_vector_count} vectors still present")
            print(f"   This may be due to replication delay")
    except Exception as e:
        print(f"⚠️  Warning: Could not verify deletion: {e}")
    
    # Next steps
    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETE")
    print("\n📋 Next Steps:")
    print("\n1. Re-upload all documents with unique vector IDs:")
    print("   python process_documents_fixed.py")
    print("\n2. Verify the upload:")
    print("   python diagnose_vector_collisions.py")
    print("\n3. Test RAG quality:")
    print("   Ask questions and verify sources are correct")
    
    if backup_file:
        print(f"\n💾 Metadata backup saved to: {backup_file}")
        print(f"   Use this to verify all documents were re-uploaded")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print()
    try:
        clean_pinecone_index()
    except KeyboardInterrupt:
        print("\n\n❌ Aborted by user - no changes made")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
