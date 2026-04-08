# -*- coding: utf-8 -*-
"""
移动归档文件到 scripts/archive/ 目录
"""
import shutil
from pathlib import Path

project_root = Path(__file__).parent
src_dir = project_root / "database" / "archive"
dst_dir = project_root / "scripts" / "archive"

dst_dir.mkdir(parents=True, exist_ok=True)

moved = 0
for f in src_dir.glob("*.py"):
    dst = dst_dir / f.name
    shutil.move(str(f), str(dst))
    moved += 1
    print(f"  moved: {f.name}")

print(f"\nTotal moved: {moved} files")
