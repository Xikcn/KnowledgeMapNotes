import re
from typing import Optional, List, Tuple
import numpy as np
import spacy
import tiktoken
from sentence_transformers import SentenceTransformer


class SemanticTextSplitter:
    """
    增强版文本分割器，结合语义分析和实体边界检测

    功能特点：
    1. 语义连贯性分析
    2. 实体边界保护
    3. 动态调整分割阈值
    4. 内容类型自适应
    5. 预加载模型提高效率
    """

    SPLIT_PUNCTUATION = [
        '\n\n', '\n', '。', '！', '？', '；', '…',
        '. ', '! ', '? ', '; ', '... ', ', ', '、'
    ]

    def __init__(self,
                 max_tokens: int = 2000,
                 min_tokens: int = 500,
                 overlap_tokens: int = 0,
                 semantic_threshold: float = 0.80,
                 enforce_entity_boundary: bool = False):
        """
        初始化文本分割器

        参数:
            max_tokens: 每个块的推荐最大token数(实际可能根据语义调整)
            min_tokens: 寻找断点的最小token数
            overlap_tokens: 块之间重叠的token数
            semantic_threshold: 语义分割的相似度阈值(0-1)
            enforce_entity_boundary: 是否强制不在实体中间分割
        """
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.semantic_threshold = semantic_threshold
        self.enforce_entity_boundary = enforce_entity_boundary

        # 预加载模型（单例）
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.nlp = spacy.load("zh_core_web_sm")

        # 参数校验
        if self.min_tokens >= self.max_tokens:
            raise ValueError("min_tokens 必须小于 max_tokens")
        if self.overlap_tokens >= self.min_tokens:
            raise ValueError("overlap_tokens 应小于 min_tokens")

    def split_text(self, text: str, doc_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        分割文本方法

        参数:
            text: 要分割的文本
            doc_id: 文档级标识符

        返回:
            元组列表，格式为 (block_id, chunk_text)
        """
        # 1. 预处理阶段
        text_clean, tags = self._preprocess_text(text)

        # 2. 实体边界检测
        entity_boundaries = self._get_entity_boundaries(text_clean) if self.enforce_entity_boundary else set()

        # 3. 主分割逻辑
        tokens = self.encoder.encode(text_clean)
        chunks = []
        start_idx = 0
        chunk_counter = 1

        while start_idx < len(tokens):
            # 动态调整实际max_tokens（±20%）
            adjusted_max = min(
                int(self.max_tokens * (1 + 0.2 * (chunk_counter % 3 - 1))),  # 波动调整
                len(tokens) - start_idx
            )
            end_idx = min(start_idx + adjusted_max, len(tokens))

            # 短内容直接作为最后一块
            if len(tokens) - start_idx <= self.min_tokens + self.overlap_tokens:
                chunk_tokens = tokens[start_idx:]
                chunk_text = self._reconstruct_text(chunk_tokens, tags)
                bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
                chunks.append((bid, chunk_text))
                break

            # 获取候选分割区间
            candidate_text = self.encoder.decode(tokens[start_idx:end_idx])
            best_split_pos = self._find_best_split_position(
                candidate_text, start_idx, end_idx, entity_boundaries
            )

            # 生成当前块
            chunk_tokens = tokens[start_idx:best_split_pos]
            chunk_text = self._reconstruct_text(chunk_tokens, tags)

            # 设置下一个块的起始位置（考虑重叠）
            next_start = max(start_idx, best_split_pos - self.overlap_tokens)

            # 添加到结果
            bid = self._generate_block_id(chunk_text, chunk_counter, doc_id)
            chunks.append((bid, chunk_text))
            chunk_counter += 1
            start_idx = next_start

        return chunks

    def _preprocess_text(self, text: str) -> Tuple[str, list]:
        """处理特殊内容并分析文档结构"""
        tag_pattern = re.compile(r'(<(img|table|code)[^>]*>.*?</\2>)', re.DOTALL)
        tags = []

        def replace_tag(match):
            tags.append(match.group(1))
            return f"__TAG_{len(tags) - 1}__"

        text_clean = tag_pattern.sub(replace_tag, text)
        return text_clean, tags

    def _analyze_semantic_breaks(self, text: str) -> List[int]:
        """使用语义相似度检测自然断点"""
        sentences = [sent.text for sent in self.nlp(text).sents]
        if len(sentences) < 2:
            return []

        embeddings = self.semantic_model.encode(sentences)
        similarities = []
        for i in range(1, len(embeddings)):
            sim = np.dot(embeddings[i - 1], embeddings[i])
            similarities.append(sim)

        # 找出语义变化大的位置
        break_points = [i for i, sim in enumerate(similarities)
                        if sim < self.semantic_threshold]
        return break_points

    def _get_entity_boundaries(self, text: str) -> set:
        """获取实体边界位置"""
        doc = self.nlp(text)
        boundaries = set()
        for ent in doc.ents:
            start = len(self.encoder.encode(text[:ent.start_char]))
            end = len(self.encoder.encode(text[:ent.end_char]))
            boundaries.update(range(start, end))
        return boundaries

    def _find_best_split_position(self, candidate_text: str, start_idx: int, end_idx: int,
                                  entity_boundaries: set) -> int:
        """寻找最佳分割位置"""
        # 优先级1：语义断点
        semantic_breaks = self._analyze_semantic_breaks(candidate_text)
        if semantic_breaks:
            semantic_pos = start_idx + len(self.encoder.encode(candidate_text[:semantic_breaks[0]]))
            if semantic_pos - start_idx >= self.min_tokens:
                return semantic_pos

        # 优先级2：标点断点
        for punct in self.SPLIT_PUNCTUATION:
            punct_pos = candidate_text.rfind(punct)
            if punct_pos != -1:
                punct_token_pos = len(self.encoder.encode(candidate_text[:punct_pos + len(punct)]))
                candidate_pos = start_idx + punct_token_pos

                # 检查是否满足最小长度且不破坏实体
                if (punct_token_pos >= self.min_tokens and
                        not any(pos in entity_boundaries for pos in range(candidate_pos - 3, candidate_pos + 3))):
                    return candidate_pos

        # 优先级3：安全位置（避开实体）
        for pos in range(end_idx, start_idx + self.min_tokens - 1, -1):
            if pos not in entity_boundaries:
                return pos

        # 最终回退策略
        return end_idx

    def _reconstruct_text(self, tokens: list, tags: list) -> str:
        """重建文本并恢复被替换的标签"""
        text = self.encoder.decode(tokens)
        for j, tag in enumerate(tags):
            text = text.replace(f"__TAG_{j}__", tag)
        return text

    def _generate_block_id(self, text: str, counter: int, doc_id: Optional[str]) -> str:
        """生成块ID"""
        prefix = f"{doc_id}_" if doc_id else ""
        return f"{prefix}block_{counter}_{hash(text[:50])}"

