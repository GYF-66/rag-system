# -*- coding: utf-8 -*-
"""Adaptive-RAG 三级路由对比测试"""
import requests
import time

API = 'http://localhost:8001/api/chat'

tests = [
    ('SIMPLE',   '什么是人工智能'),
    ('SIMPLE',   'Python课几学分'),
    ('STANDARD', '人工智能专业有哪些实践环节和实习要求'),
    ('STANDARD', '大数据技术和Python程序设计课程分别在哪个学期开设'),
    ('COMPLEX',  '请比较机器学习和深度学习课程的培养目标差异，分析课程衔接关系和先修要求'),
    ('COMPLEX',  '从培养方案角度分析AI专业课程体系与行业需求的一致性，评价知识覆盖度和断层'),
]

print('=' * 70)
print('  Adaptive-RAG 三级路由对比测试 (BGE-M3 + AdaptiveRouter)')
print('=' * 70)

for expected, query in tests:
    t0 = time.time()
    try:
        r = requests.post(API, json={
            'message': query,
            'session_id': f'bench-{time.time()}'
        }, timeout=60)
        d = r.json()
        m = d.get('metadata', {})
        elapsed = (time.time() - t0) * 1000

        route = m.get('adaptive_route', '?')
        method = m.get('retrieval_method', '?')
        hyde = 'Y' if m.get('hyde_used') else 'N'
        sources = m.get('source_count', '?')
        crag = m.get('crag_evaluation')
        crag_str = f"score={crag['quality_score']:.2f}" if crag else 'skipped'
        match_icon = '\u2705' if route == expected.lower() else '\u274c'

        print(f"\n{match_icon} [{expected:8s}] {query[:40]}")
        print(f"   路由={route:8s} | 方法={method:20s} | HyDE={hyde} | CRAG={crag_str:12s} | 来源={sources} | {elapsed:.0f}ms")
    except Exception as e:
        print(f"\n\u274c [{expected:8s}] {query[:40]} -> ERROR: {e}")

print('\n' + '=' * 70)
print('  测试完成')
print('=' * 70)
