"""
Reindex all PDFs under backend/data/uploads into Pinecone.
"""

import asyncio
from pathlib import Path

from app.config import settings
from app.api.routes.documents import index_chunks_to_pinecone
from app.utils.document_processor import DocumentProcessor


def infer_doc_type(file_path: Path) -> str:
    path_lower = str(file_path).lower()
    if "fact sheets" in path_lower:
        return "product"
    if "treatment techniques" in path_lower or "protocols" in path_lower:
        return "protocol"
    if "case studies" in path_lower:
        return "case_study"
    if "clinical papers" in path_lower:
        return "clinical_paper"
    if "brochures" in path_lower:
        return "product"
    return "other"


async def reindex_uploads() -> None:
    upload_root = Path(settings.upload_dir)
    pdf_files = list(upload_root.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found under {upload_root}")
        return

    processor = DocumentProcessor()
    print(f"Found {len(pdf_files)} PDFs to index.")

    for pdf_path in pdf_files:
        doc_id = pdf_path.stem
        doc_type = infer_doc_type(pdf_path)
        print(f"Indexing {pdf_path} (doc_id={doc_id}, doc_type={doc_type})")

        try:
            result = processor.process_pdf(str(pdf_path), doc_id=doc_id, doc_type=doc_type)
            num_indexed = await index_chunks_to_pinecone(
                chunks=result["chunks"],
                doc_id=doc_id,
                doc_type=doc_type,
                namespace="default"
            )
            print(f"  -> chunks={result['stats']['num_chunks']} indexed={num_indexed}")
        except Exception as exc:
            print(f"  -> failed: {exc}")


if __name__ == "__main__":
    asyncio.run(reindex_uploads())
