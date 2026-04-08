# -*- coding: utf-8 -*-
"""
RAG 知识库构建工具
将原始文本转换为适合检索增强生成（RAG）的知识库
使用统一分块器
"""
import json
import re
import sys
from typing import List, Dict
from datetime import datetime
from pathlib import Path

# 添加 backend 到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.chunking.unified_chunker import UnifiedChunker

# 配置 - 使用相对路径
RAW_TEXT_FILE = BASE_DIR / "database" / "raw_text.txt"
OUTPUT_FILE = BASE_DIR / "database" / "rag_knowledge_base.json"

# 初始化统一分块器
chunker = UnifiedChunker(
    chunk_size=800,
    chunk_overlap=150,
    respect_sentence_boundary=True,
    min_chunk_size=50
)

def clean_text(text: str) -> str:
    """清理文本，移除不必要的字符"""
    # 移除空白页标记和特殊符号
    text = re.sub(r'[\f]+', '\n\n', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    # 移除过多的空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_into_chunks(text: str) -> List[Dict]:
    """
    使用统一分块器将文本分块
    """
    # 使用统一分块器
    chunks = chunker.chunk_text(
        text=text,
        metadata={'source': '人工智能专业知识库'}
    )
    
    # 转换为旧格式以保持兼容性
    formatted_chunks = []
    for i, chunk in enumerate(chunks):
        formatted_chunks.append({
            'id': str(i),
            'text': chunk['text'],
            'metadata': {
                'char_count': chunk['char_length'],
                'source': chunk['metadata'].get('source', '人工智能专业知识库'),
                'chunk_index': chunk['chunk_index'],
                'char_start': chunk['char_start'],
                'char_end': chunk['char_end']
            }
        })
    
    return formatted_chunks

def extract_topics(chunks: List[Dict]) -> List[str]:
    """从知识块中提取主题"""
    topics = set()

    for chunk in chunks:
        text = chunk['text']
        # 提取可能的章节标题
        chapter_patterns = [
            r'第[一二三四五六七八九十百千\d]+章',
            r'第[一二三四五六七八九十百千\d]+节',
            r'\d+\.\d+',
            r'[\u4e00-\u9fff]+制度',
            r'[\u4e00-\u9fff]+管理',
            r'[\u4e00-\u9fff]+规定'
        ]

        for pattern in chapter_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) <= 20:  # 只取较短的标题
                    topics.add(match)

    return sorted(list(topics))[:20]

def create_knowledge_base(chunks: List[Dict]) -> Dict:
    """创建知识库数据结构"""
    topics = extract_topics(chunks)
    
    # 获取分块器配置
    chunker_config = chunker.get_config()

    return {
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'metadata': {
            'source': '人工智能专业知识库',
            'total_chunks': len(chunks),
            'total_characters': sum(c['metadata']['char_count'] for c in chunks),
            'average_chunk_size': sum(c['metadata']['char_count'] for c in chunks) // len(chunks) if chunks else 0,
            'chunk_size': chunker_config['chunk_size'],
            'chunk_overlap': chunker_config['chunk_overlap'],
            'chunker': 'UnifiedChunker',
            'topics': topics
        },
        'chunks': chunks,
        'statistics': {
            'char_distribution': {
                'min': min(c['metadata']['char_count'] for c in chunks) if chunks else 0,
                'max': max(c['metadata']['char_count'] for c in chunks) if chunks else 0,
                'avg': sum(c['metadata']['char_count'] for c in chunks) // len(chunks) if chunks else 0
            }
        }
    }

def main():
    print("=" * 60)
    print("RAG 知识库构建工具")
    print("=" * 60)

    # 读取原始文本
    print(f"\n正在读取文件: {RAW_TEXT_FILE}")
    if not RAW_TEXT_FILE.exists():
        print(f"错误: 文件不存在 {RAW_TEXT_FILE}")
        return
    with open(RAW_TEXT_FILE, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    print(f"原始文本长度: {len(raw_text):,} 字符")

    # 清理文本
    print("\n正在清理文本...")
    cleaned_text = clean_text(raw_text)
    print(f"清理后长度: {len(cleaned_text):,} 字符")

    # 分块
    print(f"\n正在分块 (块大小: {CHUNK_SIZE}, 重叠: {CHUNK_OVERLAP})...")
    chunks = split_into_chunks(cleaned_text, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"生成知识块数: {len(chunks)}")

    # 创建知识库
    print("\n正在创建知识库...")
    knowledge_base = create_knowledge_base(chunks)

    # 保存知识库
    print(f"\n正在保存到: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

    # 显示统计信息
    print("\n" + "=" * 60)
    print("知识库统计:")
    print(f"  总块数: {knowledge_base['metadata']['total_chunks']:,}")
    print(f"  总字符数: {knowledge_base['metadata']['total_characters']:,}")
    print(f"  平均块大小: {knowledge_base['metadata']['average_chunk_size']:,} 字符")
    print(f"  最小块: {knowledge_base['statistics']['char_distribution']['min']} 字符")
    print(f"  最大块: {knowledge_base['statistics']['char_distribution']['max']} 字符")
    print(f"  检测主题数: {len(knowledge_base['metadata']['topics'])}")
    print("=" * 60)

    # 显示前 5 个块
    print("\n前 5 个知识块预览:")
    print("-" * 60)
    for i, chunk in enumerate(chunks[:5]):
        preview = chunk['text'][:100] + "..." if len(chunk['text']) > 100 else chunk['text']
        print(f"\n[块 {i}] ({chunk['metadata']['char_count']} 字符)")
        print(f"  {preview}")

    print("\n" + "=" * 60)
    print("知识库构建完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()