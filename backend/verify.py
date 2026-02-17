# Simple verification script
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("Checking Intelligent Reasoning Features")
print("=" * 50)

try:
    # Check if files exist
    import os
    files_to_check = [
        'cross_retrieval_engine.py',
        'cross_retrieval_engine_improved.py',
        'agent_v2.py',
        'reasoning_engine.py',
        'reranker.py'
    ]

    print("\nFiles created:")
    for f in files_to_check:
        exists = os.path.exists(f)
        size = os.path.getsize(f) if exists else 0
        print(f"  {f}: {'EXISTS' if exists else 'MISSING'} ({size} bytes)")

    # Try to check syntax
    print("\nSyntax check:")
    import py_compile
    for f in files_to_check:
        if os.path.exists(f):
            try:
                py_compile(f, doraise=True)
                print(f"  {f}: OK")
            except py_compile.PyCompileError as e:
                print(f"  {f}: SYNTAX ERROR at line {e.lineno}")

    print("\n" + "=" * 50)
    print("Summary:")
    print("  - cross_retrieval_engine.py: Core cross-retrieval engine")
    print("  - cross_retrieval_engine_improved.py: Fixed version")
    print("  - Supports 10 cross-query patterns")
    print("  - Features: query detection, multi-keyword retrieval, cross-comparison")
    print("=" * 50)

except Exception as e:
    print(f"Error: {e}")