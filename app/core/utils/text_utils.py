"""
Text processing utilities
"""

from typing import List, Dict, Any, Optional
import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import string

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """Text processing utilities"""

    def __init__(self):
        # Download required NLTK data (only if not already downloaded)
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.warning("NLTK punkt tokenizer not found, downloading...")
            nltk.download('punkt', quiet=True)

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.warning("NLTK stopwords not found, downloading...")
            nltk.download('stopwords', quiet=True)

        self.stop_words = set(stopwords.words('english'))
        self.punctuation = set(string.punctuation)

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

        return text

    def tokenize_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        try:
            return sent_tokenize(text)
        except Exception as e:
            logger.warning("Sentence tokenization failed, falling back to simple split")
            return re.split(r'[.!?]+', text)

    def tokenize_words(self, text: str) -> List[str]:
        """Split text into words"""
        try:
            return word_tokenize(text)
        except Exception as e:
            logger.warning("Word tokenization failed, falling back to simple split")
            return text.split()

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Remove stopwords from word list"""
        return [word for word in words if word.lower() not in self.stop_words]

    def remove_punctuation(self, text: str) -> str:
        """Remove punctuation from text"""
        return ''.join(char for char in text if char not in self.punctuation)

    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get basic text statistics"""
        sentences = self.tokenize_sentences(text)
        words = self.tokenize_words(text)

        return {
            "char_count": len(text),
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "avg_sentence_length": len(words) / len(sentences) if sentences else 0
        }

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using simple frequency analysis"""
        words = self.tokenize_words(text.lower())
        words = [self.remove_punctuation(word) for word in words]
        words = [word for word in words if word and len(word) > 2]
        words = self.remove_stopwords(words)

        # Count word frequencies
        from collections import Counter
        word_counts = Counter(words)

        # Return most common words
        return [word for word, _ in word_counts.most_common(max_keywords)]


class TextChunker:
    """Text chunking utilities for processing large texts"""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_by_characters(self, text: str) -> List[str]:
        """Split text into chunks by character count"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # If we're not at the end, try to find a good breaking point
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_end = min(end + 100, len(text))
                sentence_end = text.rfind('.', end, search_end)
                if sentence_end != -1:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    space_pos = text.rfind(' ', end, search_end)
                    if space_pos != -1:
                        end = space_pos

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - self.overlap

        return chunks

    def chunk_by_sentences(self, text: str, sentences_per_chunk: int = 5) -> List[str]:
        """Split text into chunks by sentence count"""
        processor = TextProcessor()
        sentences = processor.tokenize_sentences(text)

        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk = ' '.join(chunk_sentences).strip()
            if chunk:
                chunks.append(chunk)

        return chunks

    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """Split text into chunks by paragraphs"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [para.strip() for para in paragraphs if para.strip()]
