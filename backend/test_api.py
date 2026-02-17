# -*- coding: utf-8 -*-
"""简单的API测试脚本"""
import httpx
import json

url = "http://localhost:8000/api/chat"
headers = {"Content-Type": "application/json"}
data = {"message": "请假流程是怎样的"}

print("发送测试请求...")
print(f"问题: {data['message']}")
print("-" * 50)

try:
    with httpx.Client(timeout=120) as client:
        response = client.post(url, headers=headers, json=data)
        result = response.json()
    
    print("回答:")
    print(result.get("response", "无回答"))
    print("-" * 50)
    
    sources = result.get("sources", [])
    print(f"知识来源数量: {len(sources)}")
    for i, src in enumerate(sources[:3]):
        sim = src.get("similarity", 0)
        text_preview = src.get("text", "")[:100]
        print(f"  来源{i+1} (相似度: {sim:.3f}): {text_preview}...")
        
except Exception as e:
    print(f"错误: {e}")
