"""
BM25绠楁硶瀹炵幇
鐢ㄤ簬鍏抽敭璇嶆绱㈢殑鏀硅繘鐗圱F-IDF绠楁硶
"""

import math
from typing import List, Dict, Set
from collections import Counter
import jieba
import logging

logger = logging.getLogger(__name__)


class BM25:
    """
    BM25绠楁硶瀹炵幇
    
    BM25鏄疶F-IDF鐨勬敼杩涚増鏈紝鑰冭檻浜嗘枃妗ｉ暱搴﹀綊涓€鍖栧拰璇嶉楗卞拰搴?    鍏紡: BM25(D,Q) = 危 IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1 * (1-b+b*|D|/avgdl))
    
    鍏朵腑:
    - f(qi,D): 璇峲i鍦ㄦ枃妗涓殑棰戠巼
    - |D|: 鏂囨。D鐨勯暱搴?    - avgdl: 骞冲潎鏂囨。闀垮害
    - k1: 鎺у埗璇嶉楗卞拰搴︾殑鍙傛暟锛堥€氬父1.2-2.0锛?    - b: 鎺у埗鏂囨。闀垮害褰掍竴鍖栫殑鍙傛暟锛堥€氬父0.75锛?    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        鍒濆鍖朆M25
        
        Args:
            k1: 璇嶉楗卞拰搴﹀弬鏁帮紙1.2-2.0锛?            b: 鏂囨。闀垮害褰掍竴鍖栧弬鏁帮紙0-1锛?        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.corpus_size = 0
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        
        logger.info(f"[BM25] 鍒濆鍖? k1={k1}, b={b}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        鍒嗚瘝
        
        Args:
            text: 鏂囨湰
            
        Returns:
            璇嶅垪琛?        """
        return list(jieba.cut(text))
    
    def fit(self, corpus: List[str]):
        """
        璁粌BM25妯″瀷
        
        Args:
            corpus: 鏂囨。鍒楄〃
        """
        self.corpus_size = len(corpus)
        self.corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # 璁＄畻鏂囨。棰戠巼
        df = {}
        for doc in self.corpus:
            unique_words = set(doc)
            for word in unique_words:
                df[word] = df.get(word, 0) + 1
        
        # 璁＄畻IDF
        self.idf = {}
        for word, freq in df.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1)
        
        logger.info(f"[BM25] 璁粌瀹屾垚: {self.corpus_size}涓枃妗? 骞冲潎闀垮害={self.avgdl:.1f}")
    
    def get_scores(self, query: str) -> List[float]:
        """
        璁＄畻鏌ヨ涓庢墍鏈夋枃妗ｇ殑BM25鍒嗘暟
        
        Args:
            query: 鏌ヨ鏂囨湰
            
        Returns:
            鍒嗘暟鍒楄〃
        """
        query_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size
        
        for i, doc in enumerate(self.corpus):
            score = 0.0
            doc_len = self.doc_len[i]
            
            # Compute per-document token frequencies for BM25 scoring.
            doc_freqs = Counter(doc)
            
            for token in query_tokens:
                if token not in self.idf:
                    continue
                
                # 璇嶉
                freq = doc_freqs.get(token, 0)
                
                # BM25鍒嗘暟
                idf = self.idf[token]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                
                score += idf * (numerator / denominator)
            
            scores[i] = score
        
        return scores
    
    def get_top_n(self, query: str, documents: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        鑾峰彇Top-N鐩稿叧鏂囨。
        
        Args:
            query: 鏌ヨ鏂囨湰
            documents: 鏂囨。鍒楄〃锛堝寘鍚玞ontent瀛楁锛?            top_n: 杩斿洖鏁伴噺
            
        Returns:
            鎺掑簭鍚庣殑鏂囨。鍒楄〃锛堟坊鍔燽m25_score瀛楁锛?        """
        # 鎻愬彇鏂囨。鍐呭
        corpus = [doc.get('content', '') for doc in documents]
        
        # 璁粌妯″瀷
        self.fit(corpus)
        
        # 璁＄畻鍒嗘暟
        scores = self.get_scores(query)
        
        # 娣诲姞鍒嗘暟鍒版枃妗?        scored_docs = []
        for doc, score in zip(documents, scores):
            doc_copy = doc.copy()
            doc_copy['bm25_score'] = score
            scored_docs.append(doc_copy)
        
        # 鎺掑簭骞惰繑鍥濼op-N
        scored_docs.sort(key=lambda x: x['bm25_score'], reverse=True)
        
        top_scores = [f"{doc['bm25_score']:.3f}" for doc in scored_docs[:top_n]]
        logger.info(f"[BM25] Top-{top_n}鍒嗘暟: {top_scores}")
        return scored_docs[:top_n]


class FuzzyMatcher:
    """
    妯＄硦鍖归厤鍣?    
    鏀寔缂栬緫璺濈銆佹嫾闊崇浉浼煎害绛夋ā绯婂尮閰嶆柟娉?    """
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        璁＄畻缂栬緫璺濈锛圠evenshtein璺濈锛?        
        Args:
            s1: 瀛楃涓?
            s2: 瀛楃涓?
            
        Returns:
            缂栬緫璺濈
        """
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 鎻掑叆銆佸垹闄ゃ€佹浛鎹㈢殑浠ｄ环
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """
        璁＄畻鐩镐技搴︼紙鍩轰簬缂栬緫璺濈锛?        
        Args:
            s1: 瀛楃涓?
            s2: 瀛楃涓?
            
        Returns:
            鐩镐技搴︼紙0-1锛?        """
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        
        if max_len == 0:
            return 1.0
        
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def fuzzy_match(query: str, candidates: List[str], threshold: float = 0.8) -> List[str]:
        """
        妯＄硦鍖归厤
        
        Args:
            query: 鏌ヨ瀛楃涓?            candidates: 鍊欓€夊瓧绗︿覆鍒楄〃
            threshold: 鐩镐技搴﹂槇鍊?            
        Returns:
            鍖归厤鐨勫瓧绗︿覆鍒楄〃
        """
        matches = []
        for candidate in candidates:
            sim = FuzzyMatcher.similarity(query.lower(), candidate.lower())
            if sim >= threshold:
                matches.append(candidate)
        
        return matches
    
    @staticmethod
    def expand_query_with_fuzzy(query: str, vocabulary: Set[str], threshold: float = 0.85) -> List[str]:
        """Expand query tokens with fuzzy-matched vocabulary items."""
        query_tokens = list(jieba.cut(query))
        expanded_tokens = set(query_tokens)

        for token in query_tokens:
            if len(token) <= 1:
                continue

            similar_words = FuzzyMatcher.fuzzy_match(token, list(vocabulary), threshold)
            expanded_tokens.update(similar_words)

        return list(expanded_tokens)
