"""
Tests for Document Processing
"""

import pytest
import os
from pathlib import Path

from app.utils.chunking import TextChunker, chunk_text_simple
from app.utils.document_processor import DocumentProcessor


class TestTextChunking:
    """Test text chunking functionality"""
    
    def test_basic_chunking(self):
        """Test basic text chunking"""
        text = "This is a test. " * 100  # ~1600 characters
        chunks = chunk_text_simple(text, chunk_size=500, chunk_overlap=100)
        
        assert len(chunks) > 0
        assert all(len(chunk["text"]) <= 600 for chunk in chunks)  # Allow some overage
    
    def test_sentence_awareness(self):
        """Test that chunks split on sentence boundaries"""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunker = TextChunker(chunk_size=30, chunk_overlap=10)
        chunks = chunker.chunk_text(text)
        
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should end with proper punctuation
        for chunk in chunks:
            assert chunk.text.endswith('.') or chunk.text.endswith('?') or chunk.text.endswith('!')
    
    def test_overlap(self):
        """Test that chunks have proper overlap"""
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        chunker = TextChunker(chunk_size=40, chunk_overlap=20)
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that some text appears in multiple chunks
            chunk_texts = [c.text for c in chunks]
            # At least one word should appear in consecutive chunks
            assert any(
                word in chunk_texts[i+1]
                for i in range(len(chunk_texts) - 1)
                for word in chunk_texts[i].split()
            )
    
    def test_metadata_preservation(self):
        """Test that metadata is preserved in chunks"""
        text = "Test document content."
        metadata = {"doc_id": "test_123", "page": 1}
        
        chunks = chunk_text_simple(text, metadata=metadata)
        
        assert all("doc_id" in chunk["metadata"] for chunk in chunks)
        assert all(chunk["metadata"]["doc_id"] == "test_123" for chunk in chunks)


class TestDocumentProcessor:
    """Test document processing functionality"""
    
    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """Create a sample PDF for testing"""
        # Note: In real tests, you'd create or use actual PDFs
        # For now, we'll skip PDF tests if file doesn't exist
        return None
    
    def test_processor_initialization(self):
        """Test that processor initializes correctly"""
        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
    
    def test_text_cleaning(self):
        """Test text cleaning functionality"""
        processor = DocumentProcessor()
        
        # Test whitespace cleaning
        dirty_text = "Text   with   extra    spaces"
        clean = processor._clean_text(dirty_text)
        assert "   " not in clean
        
        # Test null byte removal
        dirty_text = "Text\x00with\x00nulls"
        clean = processor._clean_text(dirty_text)
        assert "\x00" not in clean
    
    @pytest.mark.skip(reason="Requires actual PDF file")
    def test_pdf_processing(self, sample_pdf_path):
        """Test full PDF processing pipeline"""
        if not sample_pdf_path or not os.path.exists(sample_pdf_path):
            pytest.skip("No sample PDF available")
        
        processor = DocumentProcessor()
        result = processor.process_pdf(sample_pdf_path)
        
        assert "doc_id" in result
        assert "chunks" in result
        assert "stats" in result
        assert len(result["chunks"]) > 0


class TestIntegration:
    """Integration tests for document processing"""
    
    def test_end_to_end_text_processing(self):
        """Test complete text processing pipeline"""
        # Simulate document text
        text = """
        Product Name: Plinest
        
        Composition: PN-HPT® 40mg/2ml
        
        Indications: Prevention of ageing, maintaining skin quality, 
        remodeling fibrous areas/acne scars.
        
        Protocol: Every 14-21 days for 3 to 4 sessions.
        
        Technique: Microdroplet, Retrograde linear (needle).
        """
        
        # Process text
        chunks = chunk_text_simple(
            text,
            chunk_size=200,
            chunk_overlap=50,
            metadata={"doc_type": "product"}
        )
        
        assert len(chunks) > 0
        assert all("doc_type" in chunk["metadata"] for chunk in chunks)
        assert all(chunk["text"] for chunk in chunks)
    
    def test_chunking_with_sections(self):
        """Test chunking document with sections"""
        text = """
        # Introduction
        This is the introduction section.
        
        # Methods
        This is the methods section.
        
        # Results
        This is the results section.
        """
        
        chunker = TextChunker(chunk_size=100)
        chunks = chunker.chunk_by_sections(text)
        
        assert len(chunks) > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
