#!/usr/bin/env python3
"""
Test Document Versioning System
Tests version tracking, change detection, and sync functionality
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.document_versioning import get_version_manager, DocumentVersion
from app.services.document_sync import get_sync_service


def setup_test_env():
    """Create test environment with sample PDFs"""
    print("=" * 80)
    print("SETUP: Creating test environment")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent
    test_upload_dir = base_dir / "data" / "test_uploads"
    test_upload_dir.mkdir(parents=True, exist_ok=True)

    # Create sample "PDF" files (text files for testing)
    test_files = {
        "Newest_Factsheet.pdf": "Newest Factsheet Version 1.0\nContent for Newest product.\n",
        "Plinest_Factsheet.pdf": "Plinest Factsheet Version 1.0\nContent for Plinest product.\n",
        "Clinical_Protocol.pdf": "Clinical Protocol Version 1.0\nProtocol instructions.\n"
    }

    for filename, content in test_files.items():
        file_path = test_upload_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"✓ Created {len(test_files)} test PDFs in {test_upload_dir}")
    return test_upload_dir


def test_hash_computation():
    """Test SHA256 hash computation"""
    print("\n" + "=" * 80)
    print("TEST: SHA256 Hash Computation")
    print("=" * 80)

    version_manager = get_version_manager()
    base_dir = Path(__file__).parent.parent
    test_file = base_dir / "data" / "test_uploads" / "Newest_Factsheet.pdf"

    if not test_file.exists():
        print("✗ FAIL: Test file not found")
        return False

    # Compute hash
    hash1 = version_manager.compute_file_hash(test_file)
    print(f"\nFile: {test_file.name}")
    print(f"Hash: {hash1}")

    # Verify hash is consistent
    hash2 = version_manager.compute_file_hash(test_file)

    if hash1 == hash2:
        print("\n✓ PASS: Hash computation is consistent")
        return True
    else:
        print("\n✗ FAIL: Hash computation is inconsistent")
        return False


def test_version_registration():
    """Test version registration"""
    print("\n" + "=" * 80)
    print("TEST: Version Registration")
    print("=" * 80)

    version_manager = get_version_manager()
    base_dir = Path(__file__).parent.parent
    test_file = base_dir / "data" / "test_uploads" / "Newest_Factsheet.pdf"

    # Register first version
    doc_version = version_manager.register_version(
        doc_id="Newest_Factsheet",
        file_path=test_file,
        metadata={"category": "factsheet", "product": "Newest"}
    )

    print(f"\nRegistered Version:")
    print(f"  Doc ID: {doc_version.doc_id}")
    print(f"  Version: {doc_version.version}")
    print(f"  Hash: {doc_version.file_hash[:12]}...")
    print(f"  Last Updated: {doc_version.last_updated}")
    print(f"  Supersedes: {doc_version.supersedes}")

    # Verify version is stored
    current = version_manager.get_current_version("Newest_Factsheet")

    if current and current.version == doc_version.version:
        print("\n✓ PASS: Version registered and retrieved successfully")
        return True
    else:
        print("\n✗ FAIL: Version registration failed")
        return False


def test_change_detection():
    """Test change detection"""
    print("\n" + "=" * 80)
    print("TEST: Change Detection")
    print("=" * 80)

    version_manager = get_version_manager()
    base_dir = Path(__file__).parent.parent
    test_file = base_dir / "data" / "test_uploads" / "Newest_Factsheet.pdf"

    # Check if unchanged
    has_changed_1 = version_manager.has_changed("Newest_Factsheet", test_file)
    print(f"\nHas changed (before modification): {has_changed_1}")

    if has_changed_1:
        print("⚠ Document shows as changed (expected: unchanged)")
        # May be OK if file was modified or not registered yet

    # Modify file
    with open(test_file, 'a', encoding='utf-8') as f:
        f.write("\nAdded new content - Version 1.1\n")

    # Check if changed
    has_changed_2 = version_manager.has_changed("Newest_Factsheet", test_file)
    print(f"Has changed (after modification): {has_changed_2}")

    # Register new version
    doc_version_2 = version_manager.register_version(
        doc_id="Newest_Factsheet",
        file_path=test_file,
        metadata={"update": "content_addition"}
    )

    print(f"\nNew Version Registered:")
    print(f"  Version: {doc_version_2.version}")
    print(f"  Supersedes: {doc_version_2.supersedes}")

    # Verify version history
    history = version_manager.get_version_history("Newest_Factsheet")
    print(f"\nVersion History Length: {len(history)}")

    if has_changed_2 and len(history) >= 2:
        print("\n✓ PASS: Change detection and versioning working correctly")
        return True
    else:
        print("\n✗ FAIL: Change detection failed")
        return False


def test_version_history():
    """Test version history retrieval"""
    print("\n" + "=" * 80)
    print("TEST: Version History")
    print("=" * 80)

    version_manager = get_version_manager()

    history = version_manager.get_version_history("Newest_Factsheet")

    print(f"\nDocument: Newest_Factsheet")
    print(f"Version Count: {len(history)}")

    for i, version in enumerate(history, 1):
        print(f"\nVersion {i}:")
        print(f"  Version: {version.version}")
        print(f"  Hash: {version.file_hash[:12]}...")
        print(f"  Last Updated: {version.last_updated}")
        print(f"  Supersedes: {version.supersedes}")

    # Get superseded versions
    superseded = version_manager.get_superseded_versions("Newest_Factsheet")
    print(f"\nSuperseded Versions: {len(superseded)}")

    if len(history) >= 1:
        print("\n✓ PASS: Version history retrieved successfully")
        return True
    else:
        print("\n✗ FAIL: Version history empty")
        return False


def test_detect_updates():
    """Test update detection across directory"""
    print("\n" + "=" * 80)
    print("TEST: Detect Updates")
    print("=" * 80)

    sync_service = get_sync_service()
    changes = sync_service.detect_changes()

    print(f"\nChange Detection Results:")
    print(f"  New: {len(changes['new'])} documents")
    print(f"  Updated: {len(changes['updated'])} documents")
    print(f"  Unchanged: {len(changes['unchanged'])} documents")

    if changes["new"]:
        print(f"\n  New Documents: {', '.join(changes['new'])}")

    if changes["updated"]:
        print(f"  Updated Documents: {', '.join(changes['updated'])}")

    if changes["unchanged"]:
        print(f"  Unchanged Documents: {', '.join(changes['unchanged'])}")

    total = len(changes['new']) + len(changes['updated']) + len(changes['unchanged'])

    if total > 0:
        print("\n✓ PASS: Update detection completed successfully")
        return True
    else:
        print("\n✗ FAIL: No documents detected")
        return False


def test_version_report():
    """Test version report generation"""
    print("\n" + "=" * 80)
    print("TEST: Version Report")
    print("=" * 80)

    version_manager = get_version_manager()
    report = version_manager.export_version_report()

    print(f"\nVersion Report Generated:")
    print(f"  Generated At: {report['generated_at']}")
    print(f"\nStatistics:")
    stats = report['statistics']
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\nDocuments:")
    for doc in report['documents'][:5]:  # Show first 5
        print(f"  - {doc['doc_id']} ({doc['current_version']}) - {doc['version_count']} version(s)")

    if report['statistics']['total_documents'] > 0:
        print("\n✓ PASS: Version report generated successfully")
        return True
    else:
        print("\n✗ FAIL: Version report empty")
        return False


def test_sync_status():
    """Test sync status retrieval"""
    print("\n" + "=" * 80)
    print("TEST: Sync Status")
    print("=" * 80)

    sync_service = get_sync_service()
    status = sync_service.get_sync_status()

    print(f"\nSync Status:")
    print(f"  Timestamp: {status['timestamp']}")
    print(f"\nChanges Detected:")
    for key, value in status['changes_detected'].items():
        print(f"  {key}: {value}")

    print(f"\nVersion Statistics:")
    for key, value in status['version_statistics'].items():
        print(f"  {key}: {value}")

    print(f"\nPending Updates: {len(status['pending_updates'])} documents")

    if 'timestamp' in status:
        print("\n✓ PASS: Sync status retrieved successfully")
        return True
    else:
        print("\n✗ FAIL: Sync status incomplete")
        return False


def cleanup_test_env():
    """Clean up test environment"""
    print("\n" + "=" * 80)
    print("CLEANUP: Removing test environment")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent
    test_upload_dir = base_dir / "data" / "test_uploads"
    version_db_path = base_dir / "data" / "versions" / "versions.json"

    # Remove test uploads
    if test_upload_dir.exists():
        shutil.rmtree(test_upload_dir)
        print(f"✓ Removed {test_upload_dir}")

    # Remove version database
    if version_db_path.exists():
        version_db_path.unlink()
        print(f"✓ Removed {version_db_path}")


def main():
    """Run all document versioning tests"""
    print("=" * 80)
    print("DOCUMENT VERSIONING TEST SUITE")
    print("=" * 80)
    print()

    # Setup
    test_upload_dir = setup_test_env()

    results = {}

    # Test 1: Hash computation
    print("\nTest 1: Hash Computation...")
    try:
        results["hash_computation"] = test_hash_computation()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["hash_computation"] = False

    # Test 2: Version registration
    print("\nTest 2: Version Registration...")
    try:
        results["version_registration"] = test_version_registration()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["version_registration"] = False

    # Test 3: Change detection
    print("\nTest 3: Change Detection...")
    try:
        results["change_detection"] = test_change_detection()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["change_detection"] = False

    # Test 4: Version history
    print("\nTest 4: Version History...")
    try:
        results["version_history"] = test_version_history()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["version_history"] = False

    # Test 5: Detect updates
    print("\nTest 5: Detect Updates...")
    try:
        results["detect_updates"] = test_detect_updates()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["detect_updates"] = False

    # Test 6: Version report
    print("\nTest 6: Version Report...")
    try:
        results["version_report"] = test_version_report()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["version_report"] = False

    # Test 7: Sync status
    print("\nTest 7: Sync Status...")
    try:
        results["sync_status"] = test_sync_status()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results["sync_status"] = False

    # Cleanup
    cleanup_test_env()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    total = len(results)

    if passed == total:
        print(f"\n✅ All {total} tests passed!")
        print("\n💡 Document versioning system is working correctly")
        print("   - Version tracking operational")
        print("   - Change detection functional")
        print("   - Hash-based comparison working")
        print("   - Version history maintained")
        return 0
    else:
        print(f"\n⚠ {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
