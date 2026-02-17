# -*- coding: utf-8 -*-
"""诊断脚本 - 分析 RAG 检索问题"""
import httpx
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://localhost:8000/api/chat'
test_queries = [
    '请假流程是怎样的',
    '奖学金有哪些类型',
]

print("=" * 60)
print("RAG 系统诊断")
print("=" * 60)

for query in test_queries:
    print(f"\n【测试问题】: {query}")
    print("-" * 50)
    
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(url, json={'message': query})
            result = response.json()
            
            answer = result.get('response', '无回答')
            sources = result.get('sources', [])
            
            print(f"【回答】(前300字):\n{answer[:300]}...\n")
            
            print(f"【知识来源】: {len(sources)} 条")
            for i, src in enumerate(sources[:3]):
                sim = src.get('similarity', 0)
                tfidf = src.get('tfidf_score', 0)
                kw = src.get('keyword_score', 0)
                text = src.get('text', '')[:100].replace('\n', ' ')
                print(f"  来源{i+1}:")
                print(f"    综合分: {sim:.3f}, TF-IDF: {tfidf:.3f}, 关键词: {kw:.3f}")
                print(f"    内容: {text}...")
                
    except Exception as e:
        print(f"错误: {e}")

print("\n" + "=" * 60)
print("诊断完成")
