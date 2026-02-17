# -*- coding: utf-8 -*-
"""
知识库管理模块
负责加载、索引和检索RAG知识库
优化版：使用混合检索（TF-IDF + 关键词匹配 + 语义增强）
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from config import KNOWLEDGE_BASE_PATH, TOP_K_RESULTS

# 重要问题关键词映射（用于查询扩展）
KEYWORD_EXPANSION = {
    '请假': ['请假', '假条', '病假', '事假', '销假', '请销假', '缺勤', '旷课'],
    '奖学金': ['奖学金', '助学金', '励志奖学金', '国家奖学金', '评选', '奖励'],
    '学分': ['学分', '绩点', '成绩', '考试', '补考', '重修', '挂科'],
    '住宿': ['住宿', '宿舍', '床位', '住宿费', '退宿', '走读'],
    '毕业': ['毕业', '学位', '毕业证', '学位证', '结业', '肄业'],
    '处分': ['处分', '纪律', '警告', '记过', '留校察看', '开除'],
    '转专业': ['转专业', '专业调整', '院系调整'],
    '休学': ['休学', '复学', '保留学籍', '停学'],
    '选课': ['选课', '课程', '必修', '选修', '公选课'],
    '费用': ['费用', '学费', '住宿费', '缴费', '退费', '欠费'],
}


class KnowledgeBase:
    """知识库类"""

    def __init__(self, kb_path: Path = KNOWLEDGE_BASE_PATH):
        self.kb_path = kb_path
        self.metadata = {}
        self.chunks = []
        self.vectorizer = None
        self.chunk_vectors = None
        self._loaded = False

    def load(self) -> bool:
        """加载知识库"""
        try:
            if not self.kb_path.exists():
                print(f"警告: 知识库文件不存在: {self.kb_path}")
                return False

            with open(self.kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.metadata = data.get('metadata', {})
            self.chunks = data.get('chunks', [])

            if not self.chunks:
                print("警告: 知识库中没有知识块")
                return False

            # 构建TF-IDF向量
            self._build_vectors()

            self._loaded = True
            print(f"知识库加载成功: {len(self.chunks)} 个知识块")
            return True

        except Exception as e:
            print(f"加载知识库失败: {e}")
            return False

    def _build_vectors(self):
        """构建TF-IDF向量"""
        # 提取所有知识块文本
        texts = [chunk['text'] for chunk in self.chunks]

        # 使用jieba进行中文分词
        def chinese_tokenizer(text):
            words = jieba.cut(text)
            return ' '.join(words)

        # 构建TF-IDF向量器
        self.vectorizer = TfidfVectorizer(
            tokenizer=chinese_tokenizer,
            max_features=5000,
            ngram_range=(1, 2)
        )

        # 转换为向量
        self.chunk_vectors = self.vectorizer.fit_transform(texts)

    def search(
        self,
        query: str,
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = 0.1
    ) -> List[Dict]:
        """
        混合检索知识库（TF-IDF + 关键词匹配增强）

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            匹配的知识块列表，按相似度排序
        """
        if not self._loaded:
            print("警告: 知识库未加载")
            return []

        try:
            # 1. 查询扩展（添加同义词）
            expanded_query = self._expand_query(query)
            
            # 2. TF-IDF 向量检索
            def chinese_tokenizer(text):
                words = jieba.cut(text)
                return ' '.join(words)

            query_vector = self.vectorizer.transform([chinese_tokenizer(expanded_query)])
            tfidf_similarities = cosine_similarity(query_vector, self.chunk_vectors).flatten()

            # 3. 关键词匹配增强
            keyword_scores = self._calculate_keyword_scores(query)
            
            # 4. 混合得分（TF-IDF 70% + 关键词匹配 30%）
            combined_scores = 0.7 * tfidf_similarities + 0.3 * keyword_scores

            # 获取Top-K结果
            top_indices = np.argsort(combined_scores)[::-1][:top_k * 2]  # 多取一些再过滤

            # 过滤低相似度结果
            results = []
            for idx in top_indices:
                similarity = float(combined_scores[idx])
                if similarity >= min_similarity:
                    chunk = self.chunks[idx].copy()
                    chunk['similarity'] = similarity
                    chunk['tfidf_score'] = float(tfidf_similarities[idx])
                    chunk['keyword_score'] = float(keyword_scores[idx])
                    results.append(chunk)
                    if len(results) >= top_k:
                        break

            return results

        except Exception as e:
            print(f"搜索失败: {e}")
            return []

    def _expand_query(self, query: str) -> str:
        """查询扩展 - 添加同义词"""
        expanded_terms = [query]
        
        for keyword, synonyms in KEYWORD_EXPANSION.items():
            if keyword in query:
                # 添加所有同义词
                expanded_terms.extend(synonyms)
                
        return ' '.join(expanded_terms)

    def _calculate_keyword_scores(self, query: str) -> np.ndarray:
        """计算每个知识块的关键词匹配得分"""
        scores = np.zeros(len(self.chunks))
        
        # 提取查询关键词
        query_keywords = set(jieba.cut(query))
        # 过滤停用词
        stopwords = {'的', '是', '在', '了', '有', '和', '与', '个', '可以', '什么', '怎样', '如何', '哪些', '怎么'}
        query_keywords = query_keywords - stopwords
        
        for i, chunk in enumerate(self.chunks):
            text = chunk.get('text', '')
            chunk_keywords = set(jieba.cut(text))
            
            # 计算关键词重叠度
            overlap = len(query_keywords & chunk_keywords)
            if query_keywords:
                scores[i] = overlap / len(query_keywords)
                
            # 精确匹配加分
            for kw in query_keywords:
                if len(kw) >= 2 and kw in text:
                    scores[i] += 0.2
                    
        # 归一化到 [0, 1]
        if scores.max() > 0:
            scores = scores / scores.max()
            
        return scores

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """根据ID获取知识块"""
        for chunk in self.chunks:
            if chunk.get('id') == chunk_id:
                return chunk.copy()
        return None

    def get_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5
    ) -> List[Dict]:
        """获取相似的知识块"""
        target_chunk = self.get_chunk_by_id(chunk_id)
        if not target_chunk:
            return []

        return self.search(target_chunk['text'], top_k=top_k)

    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        if not self._loaded:
            return {}

        total_chars = sum(chunk.get('char_count', 0) for chunk in self.chunks)
        avg_chunk_size = total_chars / len(self.chunks) if self.chunks else 0

        return {
            'total_chunks': len(self.chunks),
            'total_characters': total_chars,
            'average_chunk_size': avg_chunk_size,
            'keywords': self.metadata.get('keywords', []),
            'source': self.metadata.get('source', ''),
            'version': self.metadata.get('version', '')
        }

    def is_loaded(self) -> bool:
        """检查知识库是否已加载"""
        return self._loaded


# 全局知识库实例
knowledge_base = KnowledgeBase()