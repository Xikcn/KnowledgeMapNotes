import tiktoken
from typing import List, Dict, Tuple, Optional

class SimpleTextSplitter:
    def __init__(self, max_tokens: int = 512, min_tokens: int = 128,
                 overlap_tokens: int = 0):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens  # 最大令牌数限制
        self.min_tokens = min_tokens  # 最小令牌数阈值
        self.overlap_tokens = overlap_tokens  # 块间重叠令牌数
        self.SPLIT_PUNCTUATION = [".", "!", "?", "\n\n", ";", "。", "！", "？", "；"]  # 分割标点列表

    def split_text(self, text: str, doc_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        基于令牌数量和标点边界分割文本

        参数:
            text: 待分割的文本
            doc_id: 可选文档标识符

        返回:
            元组列表 (块ID, 文本块)
        """
        chunks = []
        start_pos = 0  # 当前处理起始位置
        chunk_counter = 1  # 块计数器
        total_length = len(text)  # 文本总长度

        while start_pos < total_length:
            # 计算剩余文本
            remaining_text = text[start_pos:]

            # 根据最大令牌数确定初始结束位置
            tokens = self.encoder.encode(remaining_text)
            if len(tokens) <= self.max_tokens:
                # 剩余文本可完整容纳
                chunk_text = remaining_text
                end_pos = total_length
            else:
                # 在最大令牌范围内查找最后一个标点
                chunk_text = self.encoder.decode(tokens[:self.max_tokens])
                end_pos_in_chunk = self._find_last_punctuation(chunk_text)

                if end_pos_in_chunk >= self.min_tokens:
                    # 在标点处调整块结尾
                    chunk_text = self.encoder.decode(tokens[:end_pos_in_chunk])
                    end_pos = start_pos + len(self.encoder.encode(chunk_text))
                else:
                    # 未找到合适标点时按最大令牌数分割
                    chunk_text = self.encoder.decode(tokens[:self.max_tokens])
                    end_pos = start_pos + self.max_tokens

            # 生成块ID并添加到结果
            bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
            chunks.append((bid, chunk_text.strip()))

            # 更新位置和计数器
            chunk_counter += 1
            start_pos = end_pos - self.overlap_tokens if (end_pos - self.overlap_tokens) > start_pos else end_pos

        return chunks

    def _find_last_punctuation(self, text: str) -> int:
        """
        查找文本中最后一个分割标点的位置
        返回对应的令牌数量位置
        """
        # 查找所有标点位置
        punct_positions = []
        for punct in self.SPLIT_PUNCTUATION:
            pos = text.rfind(punct)
            if pos != -1:
                punct_positions.append(pos + len(punct))  # 包含标点符号

        if not punct_positions:
            return len(self.encoder.encode(text))

        # 获取最后一个标点位置
        last_pos = max(punct_positions)
        tokens_up_to_pos = self.encoder.encode(text[:last_pos])
        return len(tokens_up_to_pos)

    def _generate_block_id(self, text: str, counter: int, doc_id: Optional[str]) -> str:
        """生成块ID"""
        prefix = f"{doc_id}_" if doc_id else ""
        return f"{prefix}block_{counter}_{hash(text[:50])}"