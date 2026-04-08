"""
BM25算法实现
用于关键词检索的改进版TF-IDF算法
"""

import math
from typing import List, Dict, Set
from collections import Counter
import jieba
import logging

logger = logging.getLogger(__name__)


class BM25:
    """
    BM25算法实现
    
    BM25是TF-IDF的改进版本，考虑了文档长度归一化和词频饱和度
    公式: BM25(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1 * (1-b+b*|D|/avgdl))
    
    其中:
    - f(qi,D): 词qi在文档D中的频率
    - |D|: 文档D的长度
    - avgdl: 平均文档长度
    - k1: 控制词频饱和度的参数（通常1.2-2.0）
    - b: 控制文档长度归一化的参数（通常0.75）
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        初始化BM25
        
        Args:
            k1: 词频饱和度参数（1.2-2.0）
            b: 文档长度归一化参数（0-1）
        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.corpus_size = 0
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        
        logger.info(f"[BM25] 初始化: k1={k1}, b={b}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        分词
        
        Args:
            text: 文本
            
        Returns:
            词列表
        """
        return list(jieba.cut(text))
    
    def fit(self, corpus: List[str]):
        """
        训练BM25模型
        
        Args:
            corpus: 文档列表
        """
        self.corpus_size = len(corpus)
        self.corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # 计算文档频率
        df = {}
        for doc in self.corpus:
            unique_words = set(doc)
            for word in unique_words:
                df[word] = df.get(word, 0) + 1
        
        # 计算IDF
        self.idf = {}
        for word, freq in df.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1)
        
        logger.info(f"[BM25] 训练完成: {self.corpus_size}个文档, 平均长度={self.avgdl:.1f}")
    
    def get_scores(self, query: str) -> List[float]:
        """
        计算查询与所有文档的BM25分数
        
        Args:
            query: 查询文本
            
        Returns:
            分数列表
        """
        query_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size
        
        for i, doc in enumerate(self.corpus):
            score = 0.0
            doc_len = self.doc_len[i]
            
            # 计算文档中每个词的频率
            doc_freqs = Counter(doc)
            
            for token in query_tokens:
                if token not in self.idf:
                    continue
                
                # 词频
                freq = doc_freqs.get(token, 0)
                
                # BM25分数
                idf = self.idf[token]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                
                score += idf * (numerator / denominator)
            
            scores[i] = score
        
        return scores
    
    def get_top_n(self, query: str, documents: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        获取Top-N相关文档
        
        Args:
            query: 查询文本
            documents: 文档列表（包含content字段）
            top_n: 返回数量
            
        Returns:
            排序后的文档列表（添加bm25_score字段）
        """
        # 提取文档内容
        corpus = [doc.get('content', '') for doc in documents]
        
        # 训练模型
        self.fit(corpus)
        
        # 计算分数
        scores = self.get_scores(query)
        
        # 添加分数到文档
        scored_docs = []
        for doc, score in zip(documents, scores):
            doc_copy = doc.copy()
            doc_copy['bm25_score'] = score
            scored_docs.append(doc_copy)
        
        # 排序并返回Top-N
        scored_docs.sort(key=lambda x: x['bm25_score'], reverse=True)
        
        logger.info(f"[BM25] Top-{top_n}分数: {[f'{d['bm25_score']:.3f}' for d in scored_docs[:top_n]]}")
        
        return scored_docs[:top_n]


class FuzzyMatcher:
    """
    模糊匹配器
    
    支持编辑距离、拼音相似度等模糊匹配方法
    """
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        计算编辑距离（Levenshtein距离）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 插入、删除、替换的代价
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """
        计算相似度（基于编辑距离）
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            相似度（0-1）
        """
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        
        if max_len == 0:
            return 1.0
        
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def fuzzy_match(query: str, candidates: List[str], threshold: float = 0.8) -> List[str]:
        """
        模糊匹配
        
        Args:
            query: 查询字符串
            candidates: 候选字符串列表
            threshold: 相似度阈值
            
        Returns:
            匹配的字符串列表
        """
        matches = []
        for candidate in candidates:
            sim = FuzzyMatcher.similarity(query.lower(), candidate.lower())
            if sim >= threshold:
                matches.append(candidate)
        
        return matches
    
    @staticmethod
    def expand_query_with_fuzzy(query: str, vocabulary: Set[str], threshold: float = 0.85) -> List[str]:
        """
        使用模糊匹配扩展查询
        
        Args:
            query: 查询文本
            vocabulary: 词汇表
            threshold: 相似度阈值
            
        Returns:
            扩展后的查询词列表
        """
        query_tokens = list(jieba.cut(query))
        expanded_tokens = set(query_tokens)
        
        for token in query_tokens:
            # 跳过单字符
            if len(token) <= 1:
                continue
            
            # 查找相似词
            similar_words = FuzzyMatcher.fuzzy_match(token, list(vocabulary), threshold)
            expanded_tokens.update(similar_words)
        
        return list(expanded_tokens)
