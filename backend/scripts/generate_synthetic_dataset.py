#!/usr/bin/env python3
"""
Generate Synthetic Q&A Dataset from Document Chunks
Uses Claude Opus 4.5 to generate evaluation questions
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.synthetic_generator import SyntheticDatasetGenerator
from app.config import settings
import structlog

logger = structlog.get_logger()


async def main(args: argparse.Namespace) -> int:
    """
    Main function to generate synthetic dataset

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0=success, 1=failure)
    """
    try:
        # Initialize generator
        generator = SyntheticDatasetGenerator(
            model=args.model,
            processed_dir=args.processed_dir
        )

        logger.info(
            "Starting synthetic dataset generation",
            output=args.output,
            chunk_types=args.chunk_types,
            doc_types=args.doc_types,
            max_chunks=args.max_chunks,
            batch_size=args.batch_size,
            model=args.model
        )

        # Generate dataset
        stats = await generator.generate_dataset_from_documents(
            output_path=args.output,
            chunk_types=args.chunk_types if args.chunk_types else None,
            doc_types=args.doc_types if args.doc_types else None,
            max_chunks=args.max_chunks,
            batch_size=args.batch_size
        )

        # Print summary
        print("\n" + "=" * 60)
        print("SYNTHETIC DATASET GENERATION COMPLETE")
        print("=" * 60)
        print(f"Output: {args.output}")
        print(f"\nStatistics:")
        print(f"  Total chunks processed: {stats['total_chunks_processed']}")
        print(f"  Successful generations: {stats['successful_generations']}")
        print(f"  Failed generations: {stats['failed_generations']}")
        print(f"  Duplicate questions: {stats['duplicate_questions']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")

        # Check success criteria
        if stats['success_rate'] < 0.80:
            print(f"\n⚠️  Warning: Success rate below 80% threshold")
            print(f"   Consider reviewing failed generations")

        if stats['duplicate_questions'] > stats['successful_generations'] * 0.05:
            print(f"\n⚠️  Warning: High duplicate rate (>{5}%)")
            print(f"   Consider adjusting similarity threshold")

        print("\n✅ Generation completed successfully")
        return 0

    except Exception as e:
        logger.error("Synthetic dataset generation failed", error=str(e))
        print(f"\n❌ Error: {str(e)}")
        return 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments

    Args:
        argv: Command-line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate synthetic Q&A dataset from document chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from all chunks
  python scripts/generate_synthetic_dataset.py --output data/synthetic_dataset_v1.json

  # Filter by chunk types
  python scripts/generate_synthetic_dataset.py \\
    --chunk-types section detail flat table \\
    --output data/synthetic_dataset_v1.json

  # Limit for testing
  python scripts/generate_synthetic_dataset.py \\
    --max-chunks 100 \\
    --output data/synthetic_dataset_test.json

  # Filter by document type
  python scripts/generate_synthetic_dataset.py \\
    --doc-types factsheet protocol \\
    --output data/synthetic_dataset_factsheets.json
        """
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path (e.g., data/synthetic_dataset_v1.json)"
    )

    parser.add_argument(
        "--processed-dir",
        default=str(Path(__file__).parent.parent / "data" / "processed"),
        help="Path to processed documents directory (default: data/processed)"
    )

    parser.add_argument(
        "--chunk-types",
        nargs="+",
        default=None,
        help="Filter by chunk types (default: section detail flat table). "
             "Options: section, detail, flat, table, image"
    )

    parser.add_argument(
        "--doc-types",
        nargs="+",
        default=None,
        help="Filter by document types (default: all). "
             "Options: clinical_paper, case_study, protocol, factsheet, brochure"
    )

    parser.add_argument(
        "--max-chunks",
        type=int,
        default=0,
        help="Limit number of chunks to process (0=all, default: 0)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of concurrent API calls (default: 10)"
    )

    parser.add_argument(
        "--model",
        default="claude-opus-4-5-20251101",
        help="Claude model to use (default: claude-opus-4-5-20251101)"
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip question validation (not recommended)"
    )

    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
