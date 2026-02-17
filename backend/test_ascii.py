# -*- coding: utf-8 -*-
"""
Simple ASCII test for cross retrieval engine
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 60)
print("Cross Retrieval Engine Test")
print("=" * 60)

# Test import
print("\n[Test 1] Import Module")
print("-" * 60)

try:
    from cross_retrieval_engine_improved import cross_retrieval_engine_improved
    print("OK: cross_retrieval_engine_improved imported")
except Exception as e:
    print(f"FAIL: Import error - {e}")
    sys.exit(1)

# Test query detection
print("\n[Test 2] Query Detection")
print("-" * 60)

test_cases = [
    ("挂科对奖学金申请有影响吗？", True),
    ("软件著作权可以加分吗？", True),
    ("你好", False),
    ("奖学金怎么申请？", False),
    ("转专业需要什么条件？", True)
]

engine = cross_retrieval_engine_improved

for query, expected in test_cases:
    is_cross, pattern = engine.is_cross_query(query)
    status = "OK" if is_cross == expected else "FAIL"
    print(f"{status}: '{query}' -> is_cross={is_cross}")

# Test content extraction
print("\n[Test 3] Content Extraction")
print("-" * 60)

test_texts = [
    "Short text.",
    "This is a longer text with multiple sentences. This is sentence two. This is sentence three.",
    "A very long text that contains many different pieces of information. First sentence is here. Second sentence follows. Third sentence completes the section. Fourth sentence ends it.",
    ""
]

for i, text in enumerate(test_texts, 1):
    content = engine._extract_key_content(text, max_chars=150)
    truncated = "YES" if "..." in content else "NO"
    print(f"Text {i}: {len(content)} chars, truncated={truncated}")

# Test patterns
print("\n[Test 4] Pattern Coverage")
print("-" * 60)

patterns = engine.cross_query_patterns
print(f"Total patterns: {len(patterns)}")
for name in patterns.keys():
    print(f"  - {name}")

print("\n" + "=" * 60)
print("Test Completed")
print("=" * 60)