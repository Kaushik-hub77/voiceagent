"""
Advanced text chunking utilities for LLM processing
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass

from app.core.utils.text_utils import TextProcessor
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""
    content: str
    start_idx: int
    end_idx: int
    chunk_type: str  # "character", "sentence", "paragraph", "semantic"
    metadata: Dict[str, Any] = None


class SmartChunker:
    """Smart text chunking with multiple strategies"""

    def __init__(
        self,
        max_chunk_size: int = 2000,
        overlap: int = 200,
        preserve_sentences: bool = True
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_sentences = preserve_sentences
        self.text_processor = TextProcessor()

    def chunk_text(
        self,
        text: str,
        strategy: str = "hybrid"
    ) -> List[TextChunk]:
        """
        Chunk text using specified strategy

        Args:
            text: Input text to chunk
            strategy: Chunking strategy ("character", "sentence", "paragraph", "hybrid")

        Returns:
            List of TextChunk objects
        """

        if strategy == "character":
            return self._chunk_by_characters(text)
        elif strategy == "sentence":
            return self._chunk_by_sentences(text)
        elif strategy == "paragraph":
            return self._chunk_by_paragraphs(text)
        elif strategy == "hybrid":
            return self._chunk_hybrid(text)
        else:
            logger.warning(f"Unknown chunking strategy: {strategy}, using hybrid")
            return self._chunk_hybrid(text)

    def _chunk_by_characters(self, text: str) -> List[TextChunk]:
        """Simple character-based chunking"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.max_chunk_size

            # Find good break point
            if end < len(text):
                end = self._find_break_point(text, start, end)

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(TextChunk(
                    content=chunk_content,
                    start_idx=start,
                    end_idx=end,
                    chunk_type="character"
                ))

            start = end - self.overlap

        return chunks

    def _chunk_by_sentences(self, text: str) -> List[TextChunk]:
        """Sentence-based chunking"""
        sentences = self.text_processor.tokenize_sentences(text)

        chunks = []
        current_chunk = []
        current_length = 0
        start_idx = 0

        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)

            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = ' '.join(current_chunk)
                end_idx = start_idx + len(chunk_content)

                chunks.append(TextChunk(
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    chunk_type="sentence",
                    metadata={"sentence_count": len(current_chunk)}
                ))

                # Start new chunk with overlap
                overlap_sentences = max(1, len(current_chunk) // 4)  # 25% overlap
                current_chunk = current_chunk[-overlap_sentences:] + [sentence]
                start_idx = end_idx - len(' '.join(current_chunk[:-1]))
                current_length = len(' '.join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add remaining sentences
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_content,
                start_idx=start_idx,
                end_idx=start_idx + len(chunk_content),
                chunk_type="sentence",
                metadata={"sentence_count": len(current_chunk)}
            ))

        return chunks

    def _chunk_by_paragraphs(self, text: str) -> List[TextChunk]:
        """Paragraph-based chunking"""
        # Split by double newlines or other paragraph markers
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = []
        current_length = 0
        start_idx = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_length = len(paragraph)

            if current_length + paragraph_length > self.max_chunk_size and current_chunk:
                # Create chunk
                chunk_content = '\n\n'.join(current_chunk)
                end_idx = start_idx + len(chunk_content)

                chunks.append(TextChunk(
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    chunk_type="paragraph",
                    metadata={"paragraph_count": len(current_chunk)}
                ))

                # Start new chunk with overlap
                overlap_paragraphs = max(1, len(current_chunk) // 4)
                current_chunk = current_chunk[-overlap_paragraphs:] + [paragraph]
                start_idx = end_idx - len('\n\n'.join(current_chunk[:-1]))
                current_length = len('\n\n'.join(current_chunk))
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_length

        # Add remaining paragraphs
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_content,
                start_idx=start_idx,
                end_idx=start_idx + len(chunk_content),
                chunk_type="paragraph",
                metadata={"paragraph_count": len(current_chunk)}
            ))

        return chunks

    def _chunk_hybrid(self, text: str) -> List[TextChunk]:
        """Hybrid chunking strategy"""
        # Try paragraph-based first, fall back to sentence-based
        chunks = self._chunk_by_paragraphs(text)

        # If chunks are too small, try sentence-based
        avg_chunk_size = sum(len(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0

        if avg_chunk_size < self.max_chunk_size * 0.5:
            logger.debug("Switching to sentence-based chunking for better size distribution")
            chunks = self._chunk_by_sentences(text)

        return chunks

    def _find_break_point(self, text: str, start: int, preferred_end: int) -> int:
        """Find a good breaking point in text"""
        # Look for sentence endings first
        search_text = text[start:preferred_end + 100]
        sentence_end = search_text.rfind('.')
        if sentence_end != -1:
            return start + sentence_end + 1

        # Look for paragraph breaks
        paragraph_end = search_text.rfind('\n\n')
        if paragraph_end != -1:
            return start + paragraph_end + 2

        # Look for line breaks
        line_end = search_text.rfind('\n')
        if line_end != -1:
            return start + line_end + 1

        # Look for word boundaries
        space_end = search_text.rfind(' ')
        if space_end != -1:
            return start + space_end

        # No good break point found, use preferred end
        return min(preferred_end, len(text))

    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about chunks"""
        if not chunks:
            return {}

        sizes = [len(chunk.content) for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(sizes) / len(sizes),
            "min_chunk_size": min(sizes),
            "max_chunk_size": max(sizes),
            "chunk_types": list(set(chunk.chunk_type for chunk in chunks))
        }
