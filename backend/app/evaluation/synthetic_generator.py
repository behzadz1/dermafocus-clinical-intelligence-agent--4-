"""
Synthetic Dataset Generator for RAG Evaluation
Generates Q&A pairs from document chunks using Claude Opus 4.5
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import asyncio
from datetime import datetime
from difflib import SequenceMatcher
import structlog
from anthropic import AsyncAnthropic

from app.config import settings
from app.evaluation.rag_eval import GoldenQACase
from app.services.cost_tracker import get_cost_tracker

logger = structlog.get_logger()


class SyntheticDatasetGenerator:
    """
    Generator for creating synthetic Q&A test cases from document chunks
    Uses Claude Opus 4.5 to generate high-quality questions
    """

    def __init__(
        self,
        model: str = "claude-opus-4-5-20251101",
        processed_dir: Optional[str] = None
    ):
        """
        Initialize synthetic dataset generator

        Args:
            model: Claude model to use for generation (default: Opus 4.5)
            processed_dir: Path to processed documents directory
        """
        self.model = model
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.processed_dir = Path(processed_dir or settings.processed_dir)
        self.cost_tracker = get_cost_tracker()

    async def generate_question_for_chunk(
        self,
        chunk: Dict[str, Any],
        doc_metadata: Dict[str, Any]
    ) -> Optional[GoldenQACase]:
        """
        Generate a single question from a chunk using Claude Opus 4.5

        Args:
            chunk: Chunk dictionary with text, metadata, etc.
            doc_metadata: Parent document metadata

        Returns:
            GoldenQACase or None if generation failed
        """
        prompt = self._build_generation_prompt(chunk, doc_metadata)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=150,  # Questions should be short
                temperature=0.7,  # Some creativity for question variety
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            question = response.content[0].text.strip()

            # Track cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.cost_tracker.record_claude_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            # Validate question
            if not self._validate_generated_question(question, chunk):
                logger.warning(
                    "Question failed validation",
                    question=question,
                    chunk_id=chunk.get("id")
                )
                return None

            # Extract keywords from chunk
            keywords = self._extract_keywords(chunk.get("text", ""))

            # Create GoldenQACase
            case = GoldenQACase(
                id=f"SYNTH-{chunk.get('id', 'unknown')}",
                question=question,
                expected_doc_ids=[doc_metadata.get("doc_id", "")],
                expected_keywords=keywords[:5],  # Top 5 keywords
                should_refuse=False,
                max_chunks=5,
                tags=["synthetic", chunk.get("chunk_type", "unknown")],
                notes=f"Generated from chunk: {chunk.get('id', 'unknown')}"
            )

            logger.info(
                "Question generated successfully",
                chunk_id=chunk.get("id"),
                question=question[:50]
            )

            return case

        except Exception as e:
            logger.error(
                "Failed to generate question",
                chunk_id=chunk.get("id"),
                error=str(e)
            )
            return None

    def _build_generation_prompt(
        self,
        chunk: Dict[str, Any],
        doc_metadata: Dict[str, Any]
    ) -> str:
        """
        Build prompt for Claude to generate a question

        Args:
            chunk: Chunk dictionary
            doc_metadata: Document metadata

        Returns:
            Prompt string
        """
        chunk_text = chunk.get("text", "")
        chunk_type = chunk.get("chunk_type", "flat")
        section = chunk.get("section", "")
        doc_id = doc_metadata.get("doc_id", "")

        # Customize prompt based on chunk type
        if chunk_type == "section":
            question_guidance = "Generate a high-level overview question about this section."
        elif chunk_type == "detail":
            question_guidance = "Generate a specific, detailed question that this content answers."
        elif chunk_type == "table":
            question_guidance = "Generate a data or comparison question about the information in this table."
        elif chunk_type == "flat":
            question_guidance = "Generate a focused question about the main topic of this content."
        else:
            question_guidance = "Generate a specific question that this content answers."

        # Truncate chunk text to 800 chars for prompt efficiency
        truncated_text = chunk_text[:800]

        prompt = f"""You are generating evaluation questions for a dermatology RAG system.

**Task**: Generate ONE specific question that the provided chunk would answer.

**Chunk Information**:
- Document: {doc_id}
- Section: {section or "N/A"}
- Type: {chunk_type}

**Chunk Text**:
{truncated_text}

**Requirements**:
1. Question must be answerable ONLY from this chunk
2. Be specific - use product names, measurements, technical terms from the chunk
3. Question should be 5-20 words
4. Use natural clinical language (as a physician or dermatologist would ask)
5. Do NOT ask meta-questions like "What does this document say about..."
6. {question_guidance}

**Examples of GOOD questions**:
- "What is the injection depth for Plinest treatments?"
- "What are the contraindications for NewGyn?"
- "How many sessions are recommended for Newest facial treatments?"

**Examples of BAD questions**:
- "What does the document say?" (too vague)
- "Tell me about the product" (too general)
- "What is mentioned here?" (meta-question)

Output ONLY the question text, nothing else. End with a question mark."""

        return prompt

    def _validate_generated_question(
        self,
        question: str,
        chunk: Dict[str, Any]
    ) -> bool:
        """
        Validate quality of generated question

        Args:
            question: Generated question text
            chunk: Source chunk

        Returns:
            True if question passes validation
        """
        # Length check: 5-50 words
        word_count = len(question.split())
        if word_count < 5 or word_count > 50:
            return False

        # Must end with question mark
        if not question.strip().endswith("?"):
            return False

        # Must not be too generic
        generic_patterns = [
            "what does this",
            "what is mentioned",
            "what does the document",
            "tell me about",
            "describe this"
        ]
        question_lower = question.lower()
        if any(pattern in question_lower for pattern in generic_patterns):
            return False

        # Should contain at least one term from chunk (specificity check)
        chunk_text = chunk.get("text", "").lower()
        question_words = set(question.lower().split())

        # Extract meaningful words (longer than 3 chars, not common words)
        common_words = {'what', 'is', 'the', 'how', 'does', 'can', 'you', 'tell', 'me',
                       'are', 'for', 'with', 'this', 'that', 'from', 'about'}
        meaningful_words = [w for w in question_words if len(w) > 3 and w not in common_words]

        # Check if at least one meaningful word appears in chunk
        if not meaningful_words:
            return True  # No meaningful words to check, accept

        has_overlap = any(word in chunk_text for word in meaningful_words[:5])

        return has_overlap

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from chunk text

        Args:
            text: Chunk text
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        import re

        # Extract product names (capitalized words, with optional ®)
        product_names = re.findall(r'\b[A-Z][a-z]+®?\b', text)

        # Extract measurements and dosages
        measurements = re.findall(r'\b\d+\s*(?:mg|ml|%|mm|sessions?)\b', text, re.IGNORECASE)

        # Extract medical terms (words longer than 5 chars)
        words = text.lower().split()
        long_words = [w for w in words if len(w) > 5 and w.isalpha()]

        # Combine and deduplicate
        keywords = []
        seen = set()

        for keyword in product_names + measurements + long_words:
            keyword_lower = keyword.lower()
            if keyword_lower not in seen:
                keywords.append(keyword.lower())
                seen.add(keyword_lower)

            if len(keywords) >= max_keywords:
                break

        return keywords[:max_keywords]

    def is_duplicate(
        self,
        new_question: str,
        existing_questions: List[str],
        threshold: float = 0.8
    ) -> bool:
        """
        Check if question is too similar to existing questions

        Args:
            new_question: New question to check
            existing_questions: List of existing questions
            threshold: Similarity threshold (0-1), default 0.8

        Returns:
            True if duplicate found
        """
        new_lower = new_question.lower()

        for existing in existing_questions:
            existing_lower = existing.lower()
            similarity = SequenceMatcher(None, new_lower, existing_lower).ratio()

            if similarity > threshold:
                logger.debug(
                    "Duplicate question detected",
                    new_question=new_question[:50],
                    existing_question=existing[:50],
                    similarity=round(similarity, 2)
                )
                return True

        return False

    async def generate_dataset_from_documents(
        self,
        output_path: str,
        chunk_types: Optional[List[str]] = None,
        doc_types: Optional[List[str]] = None,
        max_chunks: int = 0,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Generate full synthetic dataset from processed documents

        Args:
            output_path: Path to save generated dataset JSON
            chunk_types: Filter by chunk types (default: all except image)
            doc_types: Filter by document types (default: all)
            max_chunks: Limit number of chunks to process (0=all)
            batch_size: Number of concurrent API calls

        Returns:
            Generation statistics dictionary
        """
        # Default chunk types (exclude images by default)
        if chunk_types is None:
            chunk_types = ["section", "detail", "flat", "table"]

        logger.info(
            "Synthetic dataset generation started",
            output_path=output_path,
            chunk_types=chunk_types,
            doc_types=doc_types,
            max_chunks=max_chunks
        )

        # Load all processed documents
        documents = self._load_processed_documents(doc_types)
        logger.info(f"Loaded {len(documents)} documents")

        # Collect chunks
        all_chunks = []
        for doc in documents:
            doc_id = doc.get("doc_id", "")
            doc_type = doc.get("doc_type", "")
            chunks = doc.get("chunks", [])

            for chunk in chunks:
                chunk_type = chunk.get("chunk_type", "flat")

                if chunk_type in chunk_types:
                    all_chunks.append({
                        "chunk": chunk,
                        "doc_metadata": {
                            "doc_id": doc_id,
                            "doc_type": doc_type
                        }
                    })

        logger.info(f"Collected {len(all_chunks)} chunks for generation")

        # Limit chunks if requested
        if max_chunks > 0 and len(all_chunks) > max_chunks:
            all_chunks = all_chunks[:max_chunks]
            logger.info(f"Limited to {max_chunks} chunks")

        # Generate questions in batches
        cases = []
        existing_questions = []
        failed_count = 0
        duplicate_count = 0

        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_chunks) + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches}",
                chunks_in_batch=len(batch)
            )

            # Generate questions concurrently
            tasks = [
                self.generate_question_for_chunk(
                    item["chunk"],
                    item["doc_metadata"]
                )
                for item in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    continue

                if result is None:
                    failed_count += 1
                    continue

                # Check for duplicates
                if self.is_duplicate(result.question, existing_questions):
                    duplicate_count += 1
                    continue

                cases.append(result)
                existing_questions.append(result.question)

            logger.info(
                f"Batch {batch_num} complete",
                successful=len([r for r in results if not isinstance(r, Exception) and r is not None]),
                failed=sum(1 for r in results if isinstance(r, Exception) or r is None)
            )

        # Save dataset
        self._save_dataset(output_path, cases)

        stats = {
            "total_chunks_processed": len(all_chunks),
            "successful_generations": len(cases),
            "failed_generations": failed_count,
            "duplicate_questions": duplicate_count,
            "success_rate": round(len(cases) / len(all_chunks), 3) if all_chunks else 0
        }

        logger.info(
            "Synthetic dataset generation completed",
            **stats
        )

        return stats

    def _load_processed_documents(
        self,
        doc_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Load all processed documents from disk

        Args:
            doc_types: Filter by document types (optional)

        Returns:
            List of document dictionaries
        """
        documents = []

        for json_file in self.processed_dir.glob("*.json"):
            # Skip reports and metadata files
            if json_file.stem in ["validation_report", "rag_eval_report",
                                  "upload_report", "processing_report"]:
                continue

            try:
                doc = json.loads(json_file.read_text(encoding="utf-8"))

                # Filter by doc_type if specified
                if doc_types is not None:
                    doc_type = doc.get("doc_type", "")
                    if doc_type not in doc_types:
                        continue

                documents.append(doc)

            except Exception as e:
                logger.warning(
                    "Failed to load document",
                    file=str(json_file),
                    error=str(e)
                )

        return documents

    def _save_dataset(
        self,
        output_path: str,
        cases: List[GoldenQACase]
    ) -> None:
        """
        Save generated dataset to JSON file

        Args:
            output_path: Output file path
            cases: List of generated cases
        """
        # Convert cases to dictionaries
        cases_dict = []
        for i, case in enumerate(cases, 1):
            case_dict = {
                "id": f"SYNTH-{i:03d}",  # Renumber for consistency
                "question": case.question,
                "expected_doc_ids": case.expected_doc_ids,
                "expected_keywords": case.expected_keywords,
                "should_refuse": case.should_refuse,
                "max_chunks": case.max_chunks,
                "tags": case.tags,
                "notes": case.notes
            }
            cases_dict.append(case_dict)

        # Create dataset structure
        dataset = {
            "version": f"synthetic-v1.0-{datetime.now().strftime('%Y-%m-%d')}",
            "generated_at": datetime.utcnow().isoformat(),
            "generation_config": {
                "model": self.model,
                "total_cases": len(cases_dict)
            },
            "cases": cases_dict
        }

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(dataset, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        logger.info(
            "Dataset saved",
            output_path=output_path,
            total_cases=len(cases_dict)
        )
