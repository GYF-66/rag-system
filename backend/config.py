# -*- coding: utf-8 -*-
"""
AI智能体配置文件 - 统一版本
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 知识库路径 - 使用优化后的知识库
KNOWLEDGE_BASE_PATH = BASE_DIR / "database" / "rag_knowledge_base_optimized.json"

# 数据存储路径
DATA_DIR = BASE_DIR / "backend" / "data"
DATA_DIR.mkdir(exist_ok=True)

# 会话存储路径
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# 用户记忆存储路径
MEMORY_DIR = DATA_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# API配置
API_HOST = "0.0.0.0"
API_PORT = 8001
API_RELOAD = True

# ============ RAG 检索配置 ============

# 向量检索配置
TOP_K_RESULTS = 3  # 返回最相关的Top-K个知识块（减少以提高精准度）
MIN_SIMILARITY = 0.4  # 最小相似度阈值（提高以过滤不相关内容）
SEARCH_TOP_K = 6  # 检索时获取结果数量

# ============ 智能体配置 ============
AGENT_NAME = "安信工AI小助手"
AGENT_ROLE = "学生手册智能问答助手"
AGENT_DESCRIPTION = "基于学生手册知识库的智能问答系统，可以回答关于学校规章制度、学籍管理、奖学金、考试等各类问题"

# 对话配置
MAX_CONTEXT_LENGTH = 6000  # 最大上下文长度（增大以容纳更多内容）
MAX_HISTORY_TURNS = 10  # 保留最近N轮对话历史

# ============ MongoDB 连接配置 ============
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'ai_assistant_db')

# MongoDB 连接池配置
MONGODB_MAX_POOL_SIZE = int(os.getenv('MONGODB_MAX_POOL_SIZE', '100'))
MONGODB_MIN_POOL_SIZE = int(os.getenv('MONGODB_MIN_POOL_SIZE', '10'))
MONGODB_MAX_IDLE_TIME = int(os.getenv('MONGODB_MAX_IDLE_TIME', '60000'))
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT', '30000'))

# MongoDB 集合名称
COLLECTION_USERS = 'users'
COLLECTION_SESSIONS = 'sessions'
COLLECTION_TOKENS = 'tokens'
COLLECTION_SPACES = 'spaces'

# ============ JWT 配置 ============
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production-use-openssl-rand-base64-32')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))

# ============ LLM 配置 ============
# 支持 DeepSeek / OpenAI / 通义千问 等兼容 API
LLM_API_KEY = os.getenv('LLM_API_KEY', 'sk-ca175ca22c424a859305c003bb3f499a')
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')  # 通义千问 API
LLM_MODEL = os.getenv('LLM_MODEL', 'qwen-plus')  # 通义千问 Plus 模型
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2048'))  # 最大生成 token 数
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))  # 温度参数
LLM_TIMEOUT = float(os.getenv('LLM_TIMEOUT', '60.0'))  # 请求超时时间（秒）

# ============ ChromaDB 配置 ============
CHROMA_PERSIST_DIR = BASE_DIR / "database" / "chroma_db"
CHROMA_PERSIST_DIR.mkdir(exist_ok=True)
CHROMA_COLLECTION_NAME = "student_manual_kb"

# ChromaDB 索引配置
CHROMA_HNSW_SPACE = "cosine"  # 相似度空间：cosine / l2 / ip
CHROMA_HNSW_CONSTRUCTION_EF = 200  # 构建时的搜索参数
CHROMA_HNSW_M = 16  # 连接数

# ============ Embedding 模型配置 ============
EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'simple')  # openai / huggingface / simple

EMBEDDING_MODEL = {
    'provider': EMBEDDING_PROVIDER,
    'model': os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
    'api_key': os.getenv('OPENAI_API_KEY', ''),
    'dimension': 384  # 根据模型调整
}

# 根据提供者调整配置
if EMBEDDING_PROVIDER == 'openai':
    EMBEDDING_MODEL['model'] = 'text-embedding-ada-002'
    EMBEDDING_MODEL['dimension'] = 1536
elif EMBEDDING_PROVIDER == 'huggingface':
    EMBEDDING_MODEL['dimension'] = 384  # all-MiniLM-L6-v2
else:  # simple (TF-IDF)
    EMBEDDING_MODEL['dimension'] = 5000

# ============ Rerank 配置 ============
RERANKER_USE_CROSS_ENCODER = os.getenv('RERANKER_USE_CROSS_ENCODER', 'false').lower() == 'true'
RERANKER_CROSS_ENCODER_MODEL = os.getenv('RERANKER_CROSS_ENCODER_MODEL', 'BAAI/bge-reranker-base')

# Rerank 特征权重
RERANKER_WEIGHTS = {
    'vector_similarity': 0.40,
    'keyword_overlap': 0.25,
    'exact_match': 0.15,
    'phrase_match': 0.10,
    'length_penalty': 0.05,
    'section_score': 0.03,
    'sentence_completeness': 0.01,
    'uniqueness': 0.01
}

# ============ 推理引擎配置 ============
REASONING_ENGINE_ENABLED = True
REASONING_ENGINE_LOG_STEPS = True

# ============ 检索策略配置 ============
USE_CHROMADB = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
USE_HYBRID_SEARCH = os.getenv('USE_HYBRID_SEARCH', 'false').lower() == 'true'
VECTOR_SEARCH_WEIGHT = float(os.getenv('VECTOR_SEARCH_WEIGHT', '0.7'))
KEYWORD_SEARCH_WEIGHT = float(os.getenv('KEYWORD_SEARCH_WEIGHT', '0.3'))

# ============ 性能配置 ============
MAX_RETRIEVAL_RESULTS = 50  # 最大检索结果数
MAX_RERANK_RESULTS = 20  # 最大重排序结果数
CACHE_ENABLED = True  # 是否启用缓存
CACHE_TTL = 3600  # 缓存过期时间（秒）

# ============ 日志配置 ============
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============ 监控配置 ============
ENABLE_METRICS = True
ENABLE_TRACING = False

# ============ 开发/生产环境 ============
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'