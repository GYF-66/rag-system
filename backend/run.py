# -*- coding: utf-8 -*-
"""
启动脚本 - 安装依赖并启动后端服务
"""
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """安装Python依赖"""
    print("=" * 60)
    print("安装Python依赖...")
    print("=" * 60)

    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '-r', 'requirements.txt'
        ])
        print("✓ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖安装失败: {e}")
        return False

def start_server():
    """启动FastAPI服务器"""
    print("=" * 60)
    print("启动安信工AI小助手后端服务...")
    print("=" * 60)

    try:
        import uvicorn
        from config import API_HOST, API_PORT, API_RELOAD
        uvicorn.run(
            "main:app",
            host=API_HOST,
            port=API_PORT,
            reload=API_RELOAD
        )
    except ImportError:
        print("错误: uvicorn未安装")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 切换到backend目录
    backend_dir = Path(__file__).parent
    import os
    os.chdir(backend_dir)

    # 安装依赖
    if install_dependencies():
        # 启动服务器
        start_server()
    else:
        sys.exit(1)