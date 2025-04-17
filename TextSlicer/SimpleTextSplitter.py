import tiktoken
from typing import List, Dict, Tuple, Optional

class SemanticTextSplitter:
    def __init__(self, max_tokens: int = 512, min_tokens: int = 128,
                 overlap_tokens: int = 0):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.SPLIT_PUNCTUATION = [".", "!", "?", "\n\n", ";", "。", "！", "？", "；"]

    def split_text(self, text: str, doc_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Split text based on token count and punctuation boundaries.

        Args:
            text: Text to split
            doc_id: Optional document identifier

        Returns:
            List of tuples (block_id, chunk_text)
        """
        chunks = []
        start_pos = 0
        chunk_counter = 1
        total_length = len(text)

        while start_pos < total_length:
            # Calculate remaining text
            remaining_text = text[start_pos:]

            # Find the initial end position based on max_tokens
            tokens = self.encoder.encode(remaining_text)
            if len(tokens) <= self.max_tokens:
                # If remaining text fits, use it all
                chunk_text = remaining_text
                end_pos = total_length
            else:
                # Find the last punctuation mark within the max_tokens range
                chunk_text = self.encoder.decode(tokens[:self.max_tokens])
                end_pos_in_chunk = self._find_last_punctuation(chunk_text)

                if end_pos_in_chunk >= self.min_tokens:
                    # Adjust chunk to end at punctuation
                    chunk_text = self.encoder.decode(tokens[:end_pos_in_chunk])
                    end_pos = start_pos + len(self.encoder.encode(chunk_text))
                else:
                    # If no good punctuation found, just split at max_tokens
                    chunk_text = self.encoder.decode(tokens[:self.max_tokens])
                    end_pos = start_pos + self.max_tokens

            # Generate block ID and add to results
            bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
            chunks.append((bid, chunk_text.strip()))

            # Update positions and counter
            chunk_counter += 1
            start_pos = end_pos - self.overlap_tokens if (end_pos - self.overlap_tokens) > start_pos else end_pos

        return chunks

    def _find_last_punctuation(self, text: str) -> int:
        """
        Find the last occurrence of any splitting punctuation in the text.
        Returns the position in tokens.
        """
        # Find all punctuation positions
        punct_positions = []
        for punct in self.SPLIT_PUNCTUATION:
            pos = text.rfind(punct)
            if pos != -1:
                punct_positions.append(pos + len(punct))  # Include the punctuation

        if not punct_positions:
            return len(self.encoder.encode(text))

        # Get the last position
        last_pos = max(punct_positions)
        tokens_up_to_pos = self.encoder.encode(text[:last_pos])
        return len(tokens_up_to_pos)

    def _generate_block_id(self, text: str, counter: int, doc_id: Optional[str]) -> str:
        """Generate block ID"""
        prefix = f"{doc_id}_" if doc_id else ""
        return f"{prefix}block_{counter}_{hash(text[:50])}"