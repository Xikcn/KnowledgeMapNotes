import tiktoken
from typing import List, Dict, Tuple, Optional

class CharacterTextSplitter:
    def __init__(self, separator: str = "</end>", keep_separator: bool = False, max_tokens: int = 512, min_tokens: int = 128, overlap_tokens: int = 0):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.separator = separator
        self.keep_separator = keep_separator
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens

    def split_text(self, text: str, doc_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        基于特殊标记（如</end>）分割文本，可选择是否保留标记
        """
        chunks = []
        start_pos = 0
        chunk_counter = 1
        total_length = len(text)

        while start_pos < total_length:
            # 查找下一个分隔符位置
            next_sep_pos = text.find(self.separator, start_pos)
            if next_sep_pos == -1:
                # 没有更多分隔符，处理剩余文本
                remaining_text = text[start_pos:]
                tokens = self.encoder.encode(remaining_text)
                if len(tokens) <= self.max_tokens:
                    chunk_text = remaining_text
                else:
                    chunk_text = self.encoder.decode(tokens[:self.max_tokens])
                bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
                chunks.append((bid, chunk_text.strip()))
                break

            # 提取当前块文本
            chunk_text = text[start_pos:next_sep_pos]
            if self.keep_separator:
                chunk_text += self.separator

            # 检查令牌数
            tokens = self.encoder.encode(chunk_text)
            if len(tokens) > self.max_tokens:
                # 如果超出最大令牌数，按最大令牌数截断
                chunk_text = self.encoder.decode(tokens[:self.max_tokens])

            # 生成块ID并添加到结果
            bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
            chunks.append((bid, chunk_text.strip()))

            # 更新位置和计数器
            chunk_counter += 1
            start_pos = next_sep_pos + len(self.separator)

        return chunks

    def _generate_block_id(self, text: str, counter: int, doc_id: Optional[str]) -> str:
        """生成块ID"""
        prefix = f"{doc_id}_" if doc_id else ""
        return f"{prefix}block_{counter}_{hash(text[:50])}"
