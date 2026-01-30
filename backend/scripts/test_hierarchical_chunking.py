#!/usr/bin/env python3
"""
Test script for hierarchical chunking implementation.
Processes sample documents and shows chunking results.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.hierarchical_chunking import (
    ChunkingStrategyFactory,
    DocumentType,
    HierarchicalChunker,
    AdaptiveChunker,
    StepAwareChunker,
    SectionBasedChunker,
    chunk_document_hybrid
)
from app.utils.document_processor import DocumentProcessor


def test_document_type_detection():
    """Test document type detection from various inputs"""
    print("\n" + "="*60)
    print("TEST: Document Type Detection")
    print("="*60)

    test_cases = [
        {"folder_name": "Clinical Papers", "expected": DocumentType.CLINICAL_PAPER},
        {"folder_name": "Case Studies", "expected": DocumentType.CASE_STUDY},
        {"folder_name": "Fact Sheets", "expected": DocumentType.FACTSHEET},
        {"folder_name": "Brochures ", "expected": DocumentType.BROCHURE},
        {"folder_name": "Treatment Techniques & Protocols", "expected": DocumentType.PROTOCOL},
        {"text": "ABSTRACT Introduction Methods Results Discussion", "expected": DocumentType.CLINICAL_PAPER},
        {"text": "Case Report: Patient presented with...", "expected": DocumentType.CASE_STUDY},
        {"text": "Step 1: Prepare the injection site. Step 2:", "expected": DocumentType.PROTOCOL},
        {"text": "Composition: Polynucleotides. Indications:", "expected": DocumentType.FACTSHEET},
    ]

    for case in test_cases:
        detected = ChunkingStrategyFactory.detect_document_type(
            text=case.get("text"),
            folder_name=case.get("folder_name")
        )
        status = "✓" if detected == case["expected"] else "✗"
        print(f"{status} Input: {case.get('folder_name') or case.get('text')[:50]}...")
        print(f"   Expected: {case['expected'].value}, Got: {detected.value}")


def test_hierarchical_chunking():
    """Test hierarchical chunking on clinical paper text"""
    print("\n" + "="*60)
    print("TEST: Hierarchical Chunking (Clinical Paper)")
    print("="*60)

    sample_text = """
ABSTRACT
This study evaluates the efficacy of polynucleotides for skin rejuvenation.
Patients showed significant improvement in skin texture and hydration levels.

INTRODUCTION
Skin aging is a complex process involving multiple factors.
Polynucleotides have emerged as a promising treatment option.
This study aims to evaluate their effectiveness in clinical settings.

METHODS
A total of 50 patients were enrolled in this prospective study.
Patients received three treatment sessions at four-week intervals.
Assessments were performed at baseline, 4 weeks, 8 weeks, and 12 weeks.
The injection technique involved using a 30G needle with microdroplet delivery.

RESULTS
At 12 weeks, 85% of patients showed improvement in skin texture.
Hydration levels increased by an average of 35% from baseline.
No serious adverse events were reported during the study period.

DISCUSSION
These findings suggest that polynucleotides are effective for skin rejuvenation.
The treatment protocol used in this study proved to be safe and well-tolerated.
Further studies with larger sample sizes are recommended.

CONCLUSION
Polynucleotides represent a promising option for skin rejuvenation treatments.
    """

    chunker = HierarchicalChunker(
        parent_chunk_size=500,
        child_chunk_size=200,
        child_overlap=30
    )

    chunks = chunker.chunk(
        text=sample_text,
        doc_id="test_clinical_paper",
        doc_type="clinical_paper"
    )

    print(f"\nTotal chunks created: {len(chunks)}")
    print(f"Parent (section) chunks: {sum(1 for c in chunks if c.chunk_type.value == 'section')}")
    print(f"Child (detail) chunks: {sum(1 for c in chunks if c.chunk_type.value == 'detail')}")

    print("\nChunk hierarchy:")
    for chunk in chunks:
        if chunk.chunk_type.value == "section":
            print(f"\n[PARENT] {chunk.section}")
            print(f"   ID: {chunk.id}")
            print(f"   Children: {len(chunk.children_ids)}")
            print(f"   Text preview: {chunk.text[:100]}...")
        else:
            print(f"   [CHILD] Section: {chunk.section}")
            print(f"      ID: {chunk.id}")
            print(f"      Parent: {chunk.parent_id}")
            print(f"      Text preview: {chunk.text[:80]}...")


def test_section_based_chunking():
    """Test section-based chunking on factsheet text"""
    print("\n" + "="*60)
    print("TEST: Section-Based Chunking (Factsheet)")
    print("="*60)

    sample_text = """
Product Name: Newest®

Composition: Polynucleotides HPT combined with Hyaluronic Acid.
Each syringe contains 2ml of product.

Indications: Treatment of skin aging, improvement of skin texture,
hydration restoration for face, neck, and hands.

Contraindications: Known hypersensitivity to any components.
Active skin infections at treatment site.
Pregnancy and breastfeeding.

Dosage: 1-2ml per treatment area.
Three sessions recommended at 4-week intervals.

Storage: Store at room temperature (15-25°C).
Keep away from direct sunlight.
Do not freeze.
    """

    chunker = SectionBasedChunker(chunk_size=300, min_chunk_size=50)

    chunks = chunker.chunk(
        text=sample_text,
        doc_id="test_factsheet",
        doc_type="factsheet"
    )

    print(f"\nTotal chunks created: {len(chunks)}")

    for chunk in chunks:
        print(f"\n[{chunk.section}]")
        print(f"   ID: {chunk.id}")
        print(f"   Length: {len(chunk.text)} chars")
        print(f"   Text: {chunk.text[:150]}...")


def test_step_aware_chunking():
    """Test step-aware chunking on protocol text"""
    print("\n" + "="*60)
    print("TEST: Step-Aware Chunking (Protocol)")
    print("="*60)

    sample_text = """
Hand Rejuvenation Treatment Protocol

Step 1: Patient Preparation
Clean the treatment area with antiseptic solution.
Apply topical anesthetic if desired.
Wait 15-20 minutes for numbness.

Step 2: Injection Technique
Use a 30G or 32G needle.
Employ microdroplet technique in grid pattern.
Deposit 0.02ml per injection point.

Step 3: Post-Treatment Care
Apply gentle massage to distribute product.
Advise patient to avoid sun exposure for 24 hours.
Schedule follow-up in 4 weeks.

Session 2 (Week 4): Reinforcement
Repeat the injection protocol.
Assess results from first session.
Adjust technique if needed.

Session 3 (Week 8): Consolidation
Final treatment session.
Evaluate overall improvement.
Discuss maintenance schedule.
    """

    chunker = StepAwareChunker(chunk_size=400, keep_steps_together=True)

    chunks = chunker.chunk(
        text=sample_text,
        doc_id="test_protocol",
        doc_type="protocol"
    )

    print(f"\nTotal chunks created: {len(chunks)}")

    for chunk in chunks:
        print(f"\n[{chunk.section}]")
        print(f"   ID: {chunk.id}")
        print(f"   Step: {chunk.metadata.get('step_number', 'N/A')}")
        print(f"   Length: {len(chunk.text)} chars")
        print(f"   Text preview: {chunk.text[:100]}...")


def test_chunking_factory():
    """Test the chunking factory with automatic type detection"""
    print("\n" + "="*60)
    print("TEST: Chunking Strategy Factory")
    print("="*60)

    sample_text = "Sample document text for testing..."

    test_cases = [
        ("Clinical Papers", "clinical_paper"),
        ("Case Studies", "case_study"),
        ("Fact Sheets", "factsheet"),
        ("Protocols", "protocol"),
        ("Brochures ", "brochure"),
    ]

    for folder_name, expected_type in test_cases:
        chunks, detected_type = ChunkingStrategyFactory.chunk_document(
            text=sample_text,
            doc_id="test_doc",
            folder_name=folder_name
        )

        chunker = ChunkingStrategyFactory.get_chunker(detected_type)
        strategy_name = chunker.__class__.__name__

        status = "✓" if detected_type.value == expected_type else "✗"
        print(f"{status} Folder: '{folder_name}'")
        print(f"   Detected type: {detected_type.value}")
        print(f"   Strategy: {strategy_name}")


def test_full_document_processing():
    """Test full document processing with hierarchical chunking"""
    print("\n" + "="*60)
    print("TEST: Full Document Processing Pipeline")
    print("="*60)

    # Check if we have sample documents
    upload_dir = Path(__file__).parent.parent / "data" / "uploads"
    clinical_papers_dir = upload_dir / "Clinical Papers"

    if clinical_papers_dir.exists():
        pdf_files = list(clinical_papers_dir.glob("*.pdf"))
        if pdf_files:
            test_file = pdf_files[0]
            print(f"\nProcessing: {test_file.name}")

            processor = DocumentProcessor(use_hierarchical=True)

            try:
                result = processor.process_pdf(
                    str(test_file),
                    folder_name="Clinical Papers"
                )

                print(f"\nResults:")
                print(f"   Document type: {result['doc_type']}")
                print(f"   Detected type: {result['detected_type']}")
                print(f"   Chunking strategy: {result['chunking_strategy']}")
                print(f"   Total chunks: {result['stats']['num_chunks']}")
                print(f"   Parent chunks: {result['stats']['num_parent_chunks']}")
                print(f"   Child chunks: {result['stats']['num_child_chunks']}")
                print(f"   Flat chunks: {result['stats']['num_flat_chunks']}")
                print(f"   Total characters: {result['stats']['total_chars']}")

                # Show sample chunks
                if result['chunks']:
                    print(f"\nSample chunk:")
                    sample = result['chunks'][0]
                    print(f"   Type: {sample.get('chunk_type', 'N/A')}")
                    print(f"   Section: {sample.get('section', 'N/A')}")
                    print(f"   Text: {sample.get('text', '')[:200]}...")

            except Exception as e:
                print(f"   Error processing: {e}")
        else:
            print("No PDF files found in Clinical Papers directory")
    else:
        print(f"Clinical Papers directory not found: {clinical_papers_dir}")
        print("Skipping full document processing test")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("HIERARCHICAL CHUNKING TEST SUITE")
    print("="*60)

    test_document_type_detection()
    test_hierarchical_chunking()
    test_section_based_chunking()
    test_step_aware_chunking()
    test_chunking_factory()
    test_full_document_processing()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()
