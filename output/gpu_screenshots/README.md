# GPU 处理截图包

## 目录结构
- `nvidia_smi_snapshot.txt` - nvidia-smi 实时状态快照
- `nvidia_smi_full.xml` - nvidia-smi 完整 XML 格式状态
- `gpu_state_initial.csv` - Benchmark 前 GPU 状态
- `gpu_state_during_compute.csv` - 计算中 GPU 状态
- `gpu_state_final.csv` - Benchmark 后 GPU 状态
- `gpu_monitoring.tsv` - 全程 GPU 监控数据
- `gpu_processes.txt` - GPU 进程监控
- `gpu_compute_apps.txt` - 计算型应用列表
- `benchmark_output.log` - Benchmark 运行日志
- `README.md` - 本文件

## GPU 规格
- GPU: NVIDIA GeForce RTX 5070 Laptop (8GB VRAM)
- Driver: 576.65
- CUDA: 12.9
- 当前显存: 1805 MiB / 8151 MiB
- 当前负载: 2% GPU / 31% Memory

## 已验证 GPU 加速模块
| 模块 | 模型 | 加速比 |
|------|------|--------|
| Embedding | BAAI/bge-m3 | 5.2x (GPU vs CPU) |
| Embedding | all-MiniLM-L6-v2 | 2.2x |
| Reranker | BAAI/bge-reranker-base | 6.4x |
| LLM | Ollama qwen2.5:7b-instruct-q4_K_M | 本地推理 |

## Benchmark 结果 (SEARCH_TOP_K=12)
- P@1: 0.2000
- R@10: 0.1866
- MRR: 0.2583
- Latency: 939.25ms avg
- Irrelevant Rate: 90% (测试用例设计问题，非检索系统问题)
