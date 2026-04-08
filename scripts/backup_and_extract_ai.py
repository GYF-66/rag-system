# -*- coding: utf-8 -*-
"""
备份原始文件并提取人工智能专业培养方案内容
"""
import shutil
from pathlib import Path

# 定义文件路径（使用相对路径）
raw_text_file = Path("database/raw_text.txt")
kb_json_file = Path("database/rag_knowledge_base.json")

# 备份文件
print("Backing up original files...")
shutil.copy2(raw_text_file, str(raw_text_file) + ".backup")
print(f"[OK] Backed up: {raw_text_file}.backup")

shutil.copy2(kb_json_file, str(kb_json_file) + ".backup")
print(f"[OK] Backed up: {kb_json_file}.backup")

# 读取原始文件并提取人工智能专业内容（第1507-1851行）
print("\nExtracting AI major content...")
with open(raw_text_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in original file: {len(lines)}")

# 提取第1507-1851行（Python索引从0开始，所以是1506-1850）
ai_content = lines[1506:1851]

# 写入新的raw_text.txt
print("Writing new raw_text.txt...")
with open(raw_text_file, 'w', encoding='utf-8') as f:
    f.writelines(ai_content)

print(f"[OK] Extracted {len(ai_content)} lines")
print(f"[OK] Updated: {raw_text_file}")
print("\nBackup and extraction completed!")
