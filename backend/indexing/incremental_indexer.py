# -*- coding: utf-8 -*-
"""
增量索引器
支持增量更新知识库，避免完全重建
"""
import hashlib
import json
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class IncrementalIndexer:
    """
    增量索引器
    
    特性：
    - 文档指纹追踪（基于内容哈希）
    - 增量更新（仅处理变化的文档）
    - 删除检测（移除不存在的文档）
    - 索引状态持久化
    """
    
    def __init__(
        self,
        state_file: str = "database/index_state.json",
        enable_deduplication: bool = True
    ):
        """
        初始化增量索引器
        
        Args:
            state_file: 索引状态文件路径
            enable_deduplication: 是否启用去重
        """
        self.state_file = Path(state_file)
        self.enable_deduplication = enable_deduplication
        
        # 加载索引状态
        self.state = self._load_state()
        
        logger.info(
            f"增量索引器初始化: state_file={state_file}, "
            f"tracked_docs={len(self.state.get('documents', {}))}"
        )
    
    def _load_state(self) -> Dict:
        """加载索引状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logger.info(f"加载索引状态: {len(state.get('documents', {}))} 个文档")
                return state
            except Exception as e:
                logger.warning(f"加载索引状态失败: {e}，使用空状态")
        
        return {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'documents': {},  # doc_id -> {hash, chunks, metadata}
            'statistics': {
                'total_documents': 0,
                'total_chunks': 0,
                'last_update_added': 0,
                'last_update_modified': 0,
                'last_update_deleted': 0
            }
        }
    
    def _save_state(self):
        """保存索引状态"""
        try:
            self.state['last_updated'] = datetime.now().isoformat()
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"索引状态已保存: {self.state_file}")
        except Exception as e:
            logger.error(f"保存索引状态失败: {e}")
    
    def _compute_hash(self, text: str) -> str:
        """
        计算文本哈希（用于变化检测）
        
        Args:
            text: 输入文本
            
        Returns:
            SHA256 哈希值
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def detect_changes(
        self,
        documents: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        检测文档变化
        
        Args:
            documents: 新文档列表，每个文档包含 'id', 'text', 'metadata'
            
        Returns:
            变化字典: {'added': [...], 'modified': [...], 'deleted': [...], 'unchanged': [...]}
        """
        current_doc_ids = {doc['id'] for doc in documents}
        tracked_doc_ids = set(self.state['documents'].keys())
        
        changes = {
            'added': [],
            'modified': [],
            'deleted': [],
            'unchanged': []
        }
        
        # 检测新增和修改
        for doc in documents:
            doc_id = doc['id']
            doc_hash = self._compute_hash(doc['text'])
            
            if doc_id not in tracked_doc_ids:
                # 新文档
                changes['added'].append({
                    **doc,
                    'hash': doc_hash
                })
            else:
                # 检查是否修改
                old_hash = self.state['documents'][doc_id].get('hash')
                if old_hash != doc_hash:
                    changes['modified'].append({
                        **doc,
                        'hash': doc_hash,
                        'old_hash': old_hash
                    })
                else:
                    changes['unchanged'].append(doc)
        
        # 检测删除
        deleted_ids = tracked_doc_ids - current_doc_ids
        for doc_id in deleted_ids:
            changes['deleted'].append({
                'id': doc_id,
                'metadata': self.state['documents'][doc_id].get('metadata', {})
            })
        
        logger.info(
            f"变化检测完成: 新增={len(changes['added'])}, "
            f"修改={len(changes['modified'])}, "
            f"删除={len(changes['deleted'])}, "
            f"未变={len(changes['unchanged'])}"
        )
        
        return changes
    
    def update_index(
        self,
        knowledge_base,
        documents: List[Dict],
        chunker
    ) -> Dict:
        """
        增量更新索引
        
        Args:
            knowledge_base: 知识库实例（ChromaDB或TF-IDF）
            documents: 文档列表
            chunker: 分块器实例
            
        Returns:
            更新统计信息
        """
        # 检测变化
        changes = self.detect_changes(documents)
        
        stats = {
            'added': 0,
            'modified': 0,
            'deleted': 0,
            'total_chunks_added': 0,
            'total_chunks_deleted': 0
        }
        
        # 处理删除
        if changes['deleted']:
            for doc in changes['deleted']:
                doc_id = doc['id']
                
                # 从知识库删除
                old_chunks = self.state['documents'][doc_id].get('chunk_ids', [])
                if hasattr(knowledge_base, 'delete_by_ids'):
                    knowledge_base.delete_by_ids(old_chunks)
                
                # 从状态删除
                del self.state['documents'][doc_id]
                stats['deleted'] += 1
                stats['total_chunks_deleted'] += len(old_chunks)
        
        # 处理修改（先删除旧的，再添加新的）
        if changes['modified']:
            for doc in changes['modified']:
                doc_id = doc['id']
                
                # 删除旧chunks
                old_chunks = self.state['documents'][doc_id].get('chunk_ids', [])
                if hasattr(knowledge_base, 'delete_by_ids'):
                    knowledge_base.delete_by_ids(old_chunks)
                stats['total_chunks_deleted'] += len(old_chunks)
                
                # 添加新chunks
                chunks = chunker.chunk_text(doc['text'], doc.get('metadata'))
                chunk_ids = []
                
                for chunk in chunks:
                    chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']}"
                    chunk_ids.append(chunk_id)
                    
                    # 添加到知识库
                    knowledge_base.add_document(
                        doc_id=chunk_id,
                        text=chunk['text'],
                        metadata={
                            **chunk.get('metadata', {}),
                            'parent_doc_id': doc_id
                        }
                    )
                
                # 更新状态
                self.state['documents'][doc_id] = {
                    'hash': doc['hash'],
                    'chunk_ids': chunk_ids,
                    'metadata': doc.get('metadata', {}),
                    'updated_at': datetime.now().isoformat()
                }
                
                stats['modified'] += 1
                stats['total_chunks_added'] += len(chunk_ids)
        
        # 处理新增
        if changes['added']:
            for doc in changes['added']:
                doc_id = doc['id']
                
                # 分块
                chunks = chunker.chunk_text(doc['text'], doc.get('metadata'))
                chunk_ids = []
                
                for chunk in chunks:
                    chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']}"
                    chunk_ids.append(chunk_id)
                    
                    # 添加到知识库
                    knowledge_base.add_document(
                        doc_id=chunk_id,
                        text=chunk['text'],
                        metadata={
                            **chunk.get('metadata', {}),
                            'parent_doc_id': doc_id
                        }
                    )
                
                # 更新状态
                self.state['documents'][doc_id] = {
                    'hash': doc['hash'],
                    'chunk_ids': chunk_ids,
                    'metadata': doc.get('metadata', {}),
                    'created_at': datetime.now().isoformat()
                }
                
                stats['added'] += 1
                stats['total_chunks_added'] += len(chunk_ids)
        
        # 更新统计信息
        self.state['statistics']['total_documents'] = len(self.state['documents'])
        self.state['statistics']['total_chunks'] = sum(
            len(doc['chunk_ids']) for doc in self.state['documents'].values()
        )
        self.state['statistics']['last_update_added'] = stats['added']
        self.state['statistics']['last_update_modified'] = stats['modified']
        self.state['statistics']['last_update_deleted'] = stats['deleted']
        
        # 保存状态
        self._save_state()
        
        logger.info(
            f"增量更新完成: 新增={stats['added']}文档/{stats['total_chunks_added']}块, "
            f"修改={stats['modified']}文档, "
            f"删除={stats['deleted']}文档/{stats['total_chunks_deleted']}块"
        )
        
        return stats
    
    def get_statistics(self) -> Dict:
        """获取索引统计信息"""
        return {
            **self.state['statistics'],
            'state_file': str(self.state_file),
            'last_updated': self.state.get('last_updated'),
            'tracked_documents': len(self.state['documents'])
        }
    
    def reset(self):
        """重置索引状态（用于完全重建）"""
        logger.warning("重置索引状态")
        self.state = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'documents': {},
            'statistics': {
                'total_documents': 0,
                'total_chunks': 0,
                'last_update_added': 0,
                'last_update_modified': 0,
                'last_update_deleted': 0
            }
        }
        self._save_state()


# 全局增量索引器实例
_indexer = None


def get_incremental_indexer(
    state_file: str = "database/index_state.json"
) -> IncrementalIndexer:
    """
    获取全局增量索引器实例
    
    Args:
        state_file: 状态文件路径
        
    Returns:
        增量索引器实例
    """
    global _indexer
    if _indexer is None:
        _indexer = IncrementalIndexer(state_file=state_file)
    return _indexer
