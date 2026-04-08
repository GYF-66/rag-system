# -*- coding: utf-8 -*-
"""
人工智能专业培养方案和教案材料文本提取工具
支持 PDF, DOCX, DOC 格式
"""
import os
import re
from pathlib import Path
from typing import List, Dict
import PyPDF2
import docx

# 配置
BASE_DIR = Path(__file__).parent.parent
SOURCE_DIR = BASE_DIR / "人工智能专业培养方案+专业课教案材料"
OUTPUT_FILE = BASE_DIR / "database" / "raw_text.txt"

def clean_text(text: str) -> str:
    """清理提取的文本"""
    # 移除特殊字符和控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    # 移除过多的空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()

def extract_from_pdf(file_path: Path) -> str:
    """从PDF文件提取文本"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return clean_text(text)
    except Exception as e:
        print(f"  [!] PDF提取失败 {file_path.name}: {e}")
        return ""

def extract_from_docx(file_path: Path) -> str:
    """从DOCX文件提取文本"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return clean_text(text)
    except Exception as e:
        print(f"  [!] DOCX提取失败 {file_path.name}: {e}")
        return ""

def extract_from_doc(file_path: Path) -> str:
    """从DOC文件提取文本 (需要额外处理)"""
    # DOC格式较老,可能需要使用 python-docx 或其他工具
    # 这里先返回提示信息
    print(f"  [!] DOC格式需要手动转换为DOCX: {file_path.name}")
    return f"\n\n[文件: {file_path.name} - 需要手动转换]\n\n"

def process_directory(source_dir: Path) -> List[Dict[str, str]]:
    """处理目录中的所有文档"""
    documents = []
    
    if not source_dir.exists():
        print(f"[X] 错误: 源目录不存在 {source_dir}")
        return documents
    
    print(f"\n[*] 扫描目录: {source_dir}")
    
    # 支持的文件格式
    supported_extensions = {'.pdf', '.docx', '.doc'}
    files = [f for f in source_dir.iterdir() 
             if f.is_file() and f.suffix.lower() in supported_extensions]
    
    print(f"找到 {len(files)} 个文档文件\n")
    
    for file_path in sorted(files):
        print(f"[>] 处理: {file_path.name}")
        
        text = ""
        if file_path.suffix.lower() == '.pdf':
            text = extract_from_pdf(file_path)
        elif file_path.suffix.lower() == '.docx':
            text = extract_from_docx(file_path)
        elif file_path.suffix.lower() == '.doc':
            text = extract_from_doc(file_path)
        
        if text:
            documents.append({
                'filename': file_path.name,
                'text': text,
                'char_count': len(text)
            })
            print(f"  [OK] 提取成功: {len(text):,} 字符")
        else:
            print(f"  [FAIL] 提取失败或文件为空")
    
    return documents

def combine_documents(documents: List[Dict[str, str]]) -> str:
    """合并所有文档文本"""
    combined = ""
    for doc in documents:
        combined += f"\n\n{'='*60}\n"
        combined += f"文件: {doc['filename']}\n"
        combined += f"{'='*60}\n\n"
        combined += doc['text']
        combined += "\n\n"
    return combined

def main():
    print("=" * 70)
    print("人工智能专业培养方案和教案材料文本提取工具")
    print("=" * 70)
    
    # 处理文档
    documents = process_directory(SOURCE_DIR)
    
    if not documents:
        print("\n[X] 没有成功提取任何文档")
        return
    
    # 合并文本
    print(f"\n[*] 合并 {len(documents)} 个文档...")
    combined_text = combine_documents(documents)
    
    # 保存到文件
    print(f"\n[*] 保存到: {OUTPUT_FILE}")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(combined_text)
    
    # 统计信息
    total_chars = sum(doc['char_count'] for doc in documents)
    print("\n" + "=" * 70)
    print("提取完成!")
    print(f"  文档数量: {len(documents)}")
    print(f"  总字符数: {total_chars:,}")
    print(f"  平均每文档: {total_chars // len(documents):,} 字符")
    print("=" * 70)
    
    # 显示文档列表
    print("\n[*] 已处理文档:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc['filename']} ({doc['char_count']:,} 字符)")

if __name__ == '__main__':
    main()
