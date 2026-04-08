"""
工具抽象层
将检索方法封装为独立的工具，支持Agent动态调用
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: List[Dict]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Tool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> List[Dict]:
        """
        执行工具
        
        Returns:
            List[Dict]: 检索结果列表
        """
        pass
    
    def __repr__(self):
        return f"Tool(name={self.name})"


class VectorSearchTool(Tool):
    """向量检索工具"""
    
    def __init__(self, knowledge_base):
        super().__init__(
            name="vector_search",
            description="使用向量相似度进行语义检索，适合理解查询意图"
        )
        self.kb = knowledge_base
    
    def execute(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """
        执行向量检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            logger.info(f"[VectorSearch] 查询: {query}, top_k={top_k}")
            
            # 调用ChromaDB向量检索
            if hasattr(self.kb, 'search'):
                results = self.kb.search(query, top_k=top_k)
                logger.info(f"[VectorSearch] 返回 {len(results)} 个结果")
                return results
            else:
                logger.error("[VectorSearch] 知识库不支持search方法")
                return []
                
        except Exception as e:
            logger.error(f"[VectorSearch] 执行失败: {str(e)}", exc_info=True)
            return []


class KeywordSearchTool(Tool):
    """关键词检索工具"""
    
    def __init__(self, knowledge_base):
        super().__init__(
            name="keyword_search",
            description="使用TF-IDF关键词匹配，适合精确查询"
        )
        self.kb = knowledge_base
    
    def execute(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """
        执行关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            logger.info(f"[KeywordSearch] 查询: {query}, top_k={top_k}")
            
            # 调用TF-IDF检索
            if hasattr(self.kb, 'search'):
                results = self.kb.search(query, top_k=top_k)
                logger.info(f"[KeywordSearch] 返回 {len(results)} 个结果")
                return results
            else:
                logger.error("[KeywordSearch] 知识库不支持search方法")
                return []
                
        except Exception as e:
            logger.error(f"[KeywordSearch] 执行失败: {str(e)}", exc_info=True)
            return []


class HybridSearchTool(Tool):
    """
    增强混合检索工具
    
    特性:
    - 支持BM25算法（优于TF-IDF）
    - 动态权重调整（基于查询特征）
    - 模糊匹配查询扩展
    """
    
    def __init__(self, 
                 vector_kb, 
                 keyword_kb, 
                 default_vector_weight: float = 0.6,
                 use_bm25: bool = True,
                 enable_fuzzy: bool = True,
                 enable_dynamic_weights: bool = True):
        super().__init__(
            name="hybrid_search",
            description="结合向量和关键词检索，支持BM25、动态权重和模糊匹配"
        )
        self.vector_kb = vector_kb
        self.keyword_kb = keyword_kb
        self.default_vector_weight = default_vector_weight
        self.use_bm25 = use_bm25
        self.enable_fuzzy = enable_fuzzy
        self.enable_dynamic_weights = enable_dynamic_weights
        
        # 延迟加载BM25和FuzzyMatcher
        self.bm25 = None
        self.fuzzy_matcher = None
        
        logger.info(
            f"[HybridSearch] 初始化: BM25={use_bm25}, "
            f"模糊匹配={enable_fuzzy}, 动态权重={enable_dynamic_weights}"
        )
    
    def _load_bm25(self):
        """延迟加载BM25"""
        if self.bm25 is None and self.use_bm25:
            try:
                from backend.utils.bm25 import BM25
                self.bm25 = BM25(k1=1.5, b=0.75)
                logger.info("[HybridSearch] BM25加载成功")
            except Exception as e:
                logger.warning(f"[HybridSearch] BM25加载失败: {str(e)}")
                self.use_bm25 = False
    
    def _load_fuzzy_matcher(self):
        """延迟加载模糊匹配器"""
        if self.fuzzy_matcher is None and self.enable_fuzzy:
            try:
                from backend.utils.bm25 import FuzzyMatcher
                self.fuzzy_matcher = FuzzyMatcher()
                logger.info("[HybridSearch] 模糊匹配器加载成功")
            except Exception as e:
                logger.warning(f"[HybridSearch] 模糊匹配器加载失败: {str(e)}")
                self.enable_fuzzy = False
    
    def _analyze_query(self, query: str) -> Dict[str, any]:
        """
        分析查询特征
        
        用于动态权重调整
        
        Returns:
            查询特征字典
        """
        import jieba
        
        tokens = list(jieba.cut(query))
        
        # 计算特征
        features = {
            'length': len(query),
            'token_count': len(tokens),
            'avg_token_length': sum(len(t) for t in tokens) / len(tokens) if tokens else 0,
            'has_question_mark': '?' in query or '？' in query,
            'has_keywords': any(kw in query for kw in ['什么', '如何', '怎么', '为什么', '哪些']),
            'is_short': len(query) < 10,
            'is_long': len(query) > 50
        }
        
        return features
    
    def _compute_dynamic_weights(self, query: str) -> tuple:
        """
        动态计算权重
        
        基于查询特征调整向量和关键词权重
        
        Returns:
            (vector_weight, keyword_weight)
        """
        if not self.enable_dynamic_weights:
            keyword_weight = 1.0 - self.default_vector_weight
            return self.default_vector_weight, keyword_weight
        
        features = self._analyze_query(query)
        
        # 基础权重
        vector_weight = self.default_vector_weight
        
        # 调整规则
        # 1. 短查询（<10字符）：增加关键词权重
        if features['is_short']:
            vector_weight -= 0.1
        
        # 2. 长查询（>50字符）：增加向量权重
        if features['is_long']:
            vector_weight += 0.1
        
        # 3. 包含疑问词：增加向量权重（语义理解更重要）
        if features['has_question_mark'] or features['has_keywords']:
            vector_weight += 0.05
        
        # 4. 词数少但字符多（专业术语）：增加关键词权重
        if features['token_count'] < 5 and features['avg_token_length'] > 3:
            vector_weight -= 0.1
        
        # 限制范围
        vector_weight = max(0.3, min(0.8, vector_weight))
        keyword_weight = 1.0 - vector_weight
        
        logger.info(
            f"[HybridSearch] 动态权重: 向量={vector_weight:.2f}, "
            f"关键词={keyword_weight:.2f} (查询长度={features['length']})"
        )
        
        return vector_weight, keyword_weight
    
    def _expand_query_fuzzy(self, query: str, documents: List[Dict]) -> str:
        """
        使用模糊匹配扩展查询
        
        Args:
            query: 原始查询
            documents: 文档列表（用于构建词汇表）
            
        Returns:
            扩展后的查询
        """
        if not self.enable_fuzzy or not documents:
            return query
        
        self._load_fuzzy_matcher()
        if not self.fuzzy_matcher:
            return query
        
        # 构建词汇表
        vocabulary = set()
        for doc in documents[:100]:  # 限制文档数量
            content = doc.get('content', '')
            import jieba
            tokens = jieba.cut(content)
            vocabulary.update(tokens)
        
        # 扩展查询
        expanded_tokens = self.fuzzy_matcher.expand_query_with_fuzzy(
            query, vocabulary, threshold=0.85
        )
        
        if len(expanded_tokens) > len(list(jieba.cut(query))):
            expanded_query = ' '.join(expanded_tokens)
            logger.info(f"[HybridSearch] 模糊扩展: {query} -> {expanded_query}")
            return expanded_query
        
        return query
    
    def execute(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """
        执行增强混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            logger.info(f"[HybridSearch] 查询: {query}, top_k={top_k}")
            
            # 动态计算权重
            vector_weight, keyword_weight = self._compute_dynamic_weights(query)
            
            # 向量检索
            vector_results = []
            if self.vector_kb and hasattr(self.vector_kb, 'search'):
                try:
                    vector_results = self.vector_kb.search(query, top_k=top_k * 2)
                    logger.info(f"[HybridSearch] 向量检索返回 {len(vector_results)} 个结果")
                except Exception as e:
                    logger.warning(f"[HybridSearch] 向量检索失败: {str(e)}")
            
            # 关键词检索（使用BM25或TF-IDF）
            keyword_results = []
            if self.keyword_kb:
                try:
                    if self.use_bm25:
                        # 使用BM25
                        keyword_results = self._bm25_search(query, top_k * 2)
                    elif hasattr(self.keyword_kb, 'search'):
                        # 使用TF-IDF
                        keyword_results = self.keyword_kb.search(query, top_k=top_k * 2)
                    
                    logger.info(f"[HybridSearch] 关键词检索返回 {len(keyword_results)} 个结果")
                except Exception as e:
                    logger.warning(f"[HybridSearch] 关键词检索失败: {str(e)}")
            
            # 合并结果
            merged = self._merge_results(
                vector_results, 
                keyword_results, 
                top_k,
                vector_weight,
                keyword_weight
            )
            logger.info(f"[HybridSearch] 合并后返回 {len(merged)} 个结果")
            
            return merged
            
        except Exception as e:
            logger.error(f"[HybridSearch] 执行失败: {str(e)}", exc_info=True)
            return []
    
    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        """
        使用BM25进行关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            检索结果
        """
        self._load_bm25()
        if not self.bm25:
            return []
        
        # 获取所有文档
        all_docs = []
        if hasattr(self.keyword_kb, 'chunks'):
            all_docs = self.keyword_kb.chunks
        elif hasattr(self.keyword_kb, 'get_all_documents'):
            all_docs = self.keyword_kb.get_all_documents()
        
        if not all_docs:
            logger.warning("[HybridSearch] 无法获取文档进行BM25检索")
            return []
        
        # 使用BM25检索
        results = self.bm25.get_top_n(query, all_docs, top_n=top_k)
        
        # 转换格式（将bm25_score映射为similarity）
        for result in results:
            if 'bm25_score' in result and 'similarity' not in result:
                # 归一化BM25分数到0-1范围
                max_score = max(r.get('bm25_score', 0) for r in results) if results else 1
                result['similarity'] = result['bm25_score'] / max_score if max_score > 0 else 0
        
        return results
    
    def _merge_results(self, 
                      vector_results: List[Dict], 
                      keyword_results: List[Dict],
                      top_k: int,
                      vector_weight: float,
                      keyword_weight: float) -> List[Dict]:
        """
        合并向量和关键词检索结果
        
        使用动态权重合并，去重后返回top_k结果
        """
        # 构建结果字典，以chunk_id为key
        merged_dict = {}
        
        # 处理向量检索结果
        for i, result in enumerate(vector_results):
            chunk_id = result.get('chunk_id') or result.get('id')
            if chunk_id:
                score = result.get('similarity', 0.0)
                normalized_score = score * vector_weight
                
                merged_dict[chunk_id] = {
                    **result,
                    'hybrid_score': normalized_score,
                    'vector_score': score,
                    'keyword_score': 0.0,
                    'vector_weight': vector_weight,
                    'keyword_weight': keyword_weight
                }
        
        # 处理关键词检索结果
        for i, result in enumerate(keyword_results):
            chunk_id = result.get('chunk_id') or result.get('id')
            if chunk_id:
                score = result.get('similarity', 0.0)
                normalized_score = score * keyword_weight
                
                if chunk_id in merged_dict:
                    # 已存在，累加分数
                    merged_dict[chunk_id]['hybrid_score'] += normalized_score
                    merged_dict[chunk_id]['keyword_score'] = score
                else:
                    # 新结果
                    merged_dict[chunk_id] = {
                        **result,
                        'hybrid_score': normalized_score,
                        'vector_score': 0.0,
                        'keyword_score': score,
                        'vector_weight': vector_weight,
                        'keyword_weight': keyword_weight
                    }
        
        # 按混合分数排序
        sorted_results = sorted(
            merged_dict.values(),
            key=lambda x: x['hybrid_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]


class RerankerTool(Tool):
    """重排序工具"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        super().__init__(
            name="reranker",
            description="使用Cross-Encoder模型对检索结果重排序"
        )
        self.model_name = model_name
        self.model = None  # 延迟加载
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"[Reranker] 加载模型: {self.model_name}")
                self.model = CrossEncoder(self.model_name)
                logger.info("[Reranker] 模型加载成功")
            except Exception as e:
                logger.error(f"[Reranker] 模型加载失败: {str(e)}")
                raise
    
    def execute(self, 
                query: str, 
                results: List[Dict], 
                top_k: int = 5,
                **kwargs) -> List[Dict]:
        """
        对检索结果重排序
        
        Args:
            query: 查询文本
            results: 初排结果
            top_k: 返回结果数量
            
        Returns:
            重排序后的结果
        """
        try:
            if not results:
                return []
            
            logger.info(f"[Reranker] 重排序 {len(results)} 个结果")
            
            # 加载模型
            self._load_model()
            
            # 准备query-document对
            pairs = []
            for result in results:
                content = result.get('content', '')
                pairs.append([query, content])
            
            # 计算相关性分数
            scores = self.model.predict(pairs)
            
            # 添加重排序分数
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])
            
            # 按重排序分数排序
            reranked = sorted(
                results,
                key=lambda x: x.get('rerank_score', 0),
                reverse=True
            )
            
            logger.info(f"[Reranker] 重排序完成，返回top {top_k}")
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"[Reranker] 执行失败: {str(e)}", exc_info=True)
            # 失败时返回原始结果
            return results[:top_k]


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name}")
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self.tools.keys())
