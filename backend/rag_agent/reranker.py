"""
Cross-Encoder重排序器
使用Cross-Encoder模型对检索结果进行精确重排序
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-Encoder重排序器
    
    使用BAAI/bge-reranker-base模型对初排结果重排序
    提供比向量检索更精确的相关性评分
    """
    
    def __init__(self, 
                 model_name: str = "BAAI/bge-reranker-base",
                 batch_size: int = 32,
                 max_length: int = 512):
        """
        初始化重排序器
        
        Args:
            model_name: 模型名称
            batch_size: 批处理大小
            max_length: 最大序列长度
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.model = None  # 延迟加载
        
        logger.info(f"[Reranker] 初始化重排序器: {model_name}")
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"[Reranker] 开始加载模型: {self.model_name}")
                self.model = CrossEncoder(
                    self.model_name,
                    max_length=self.max_length
                )
                logger.info("[Reranker] 模型加载成功")
            except ImportError:
                logger.error("[Reranker] sentence-transformers未安装")
                raise ImportError("请安装: pip install sentence-transformers")
            except Exception as e:
                logger.error(f"[Reranker] 模型加载失败: {str(e)}")
                raise
    
    def rerank(self, 
               query: str, 
               results: List[Dict], 
               top_k: Optional[int] = None) -> List[Dict]:
        """
        对检索结果重排序
        
        Args:
            query: 查询文本
            results: 初排结果列表
            top_k: 返回结果数量（None表示返回全部）
            
        Returns:
            重排序后的结果列表
        """
        if not results:
            logger.warning("[Reranker] 结果为空，跳过重排序")
            return []
        
        try:
            logger.info(f"[Reranker] 开始重排序 {len(results)} 个结果")
            
            # 加载模型
            self._load_model()
            
            # 准备query-document对
            pairs = []
            for result in results:
                content = result.get('content', '')
                if not content:
                    logger.warning(f"[Reranker] 结果缺少content字段: {result.get('chunk_id', 'unknown')}")
                    content = result.get('text', '')  # 尝试备用字段
                pairs.append([query, content])
            
            # 批量计算相关性分数
            logger.debug(f"[Reranker] 计算 {len(pairs)} 个query-document对的分数")
            scores = self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False
            )
            
            # 添加重排序分数到结果
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])
                # 保留原始分数
                if 'original_score' not in result:
                    result['original_score'] = result.get('similarity', 0.0)
            
            # 按重排序分数排序
            reranked = sorted(
                results,
                key=lambda x: x.get('rerank_score', 0),
                reverse=True
            )
            
            # 返回top_k结果
            if top_k is not None:
                reranked = reranked[:top_k]
            
            logger.info(f"[Reranker] 重排序完成，返回 {len(reranked)} 个结果")
            
            # 记录分数变化
            if reranked:
                top_result = reranked[0]
                logger.debug(
                    f"[Reranker] Top1: 原始分数={top_result.get('original_score', 0):.3f}, "
                    f"重排序分数={top_result.get('rerank_score', 0):.3f}"
                )
            
            return reranked
            
        except Exception as e:
            logger.error(f"[Reranker] 重排序失败: {str(e)}", exc_info=True)
            # 失败时返回原始结果
            logger.warning("[Reranker] 降级：返回原始结果")
            return results[:top_k] if top_k else results
    
    def batch_rerank(self,
                    queries: List[str],
                    results_list: List[List[Dict]],
                    top_k: Optional[int] = None) -> List[List[Dict]]:
        """
        批量重排序
        
        Args:
            queries: 查询列表
            results_list: 结果列表的列表
            top_k: 每个查询返回的结果数量
            
        Returns:
            重排序后的结果列表的列表
        """
        reranked_list = []
        for query, results in zip(queries, results_list):
            reranked = self.rerank(query, results, top_k)
            reranked_list.append(reranked)
        
        return reranked_list
