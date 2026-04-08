from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_PATH = BASE_DIR / 'database' / 'rag_knowledge_base.json'

DATA_DIR = BASE_DIR / 'backend' / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_DIR = DATA_DIR / 'sessions'
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_DIR = DATA_DIR / 'memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8001'))
API_RELOAD = _as_bool(os.getenv('API_RELOAD'), True)

TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '3'))
MIN_SIMILARITY = float(os.getenv('MIN_SIMILARITY', '0.15'))
SEARCH_TOP_K = int(os.getenv('SEARCH_TOP_K', '12'))

AGENT_NAME = os.getenv('AGENT_NAME', '安信工 AI 助手')
AGENT_ROLE = os.getenv('AGENT_ROLE', '人工智能专业知识库智能问答助手')
AGENT_DESCRIPTION = os.getenv(
    'AGENT_DESCRIPTION',
    '基于人工智能专业培养方案和课程资料的知识库问答系统，可回答培养目标、课程体系、教学内容与实践环节等问题。',
)
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')

MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '6000'))
MAX_HISTORY_TURNS = int(os.getenv('MAX_HISTORY_TURNS', '10'))

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').strip().lower()
DEBUG = ENVIRONMENT == 'development'
IS_PRODUCTION = ENVIRONMENT == 'production'
STRICT_PRODUCTION_MODE = _as_bool(
    os.getenv('STRICT_PRODUCTION_MODE'),
    default=IS_PRODUCTION,
)

SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ValueError('SECRET_KEY must be set in production')
    SECRET_KEY = secrets.token_urlsafe(32)
    logging.getLogger(__name__).warning('SECRET_KEY is not set; generated a temporary development key.')

ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'ai_assistant_db')
MONGODB_MAX_POOL_SIZE = int(os.getenv('MONGODB_MAX_POOL_SIZE', '100'))
MONGODB_MIN_POOL_SIZE = int(os.getenv('MONGODB_MIN_POOL_SIZE', '10'))
MONGODB_MAX_IDLE_TIME = int(os.getenv('MONGODB_MAX_IDLE_TIME', '60000'))
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT', '30000'))
MONGODB_REQUIRED = _as_bool(os.getenv('MONGODB_REQUIRED'), default=IS_PRODUCTION)

COLLECTION_USERS = os.getenv('COLLECTION_USERS', 'users')
COLLECTION_SESSIONS = os.getenv('COLLECTION_SESSIONS', 'sessions')
COLLECTION_TOKENS = os.getenv('COLLECTION_TOKENS', 'tokens')
COLLECTION_SPACES = os.getenv('COLLECTION_SPACES', 'spaces')

LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL', 'https://spark-api-open.xf-yun.com/v1')
LLM_MODEL = os.getenv('LLM_MODEL', 'lite')
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2048'))
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))
LLM_TIMEOUT = float(os.getenv('LLM_TIMEOUT', '60.0'))
LLM_REQUIRED = _as_bool(os.getenv('LLM_REQUIRED'), default=False)
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')  # 'api' or 'ollama'

# ── Ollama 本地 GPU 推理配置 ─────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct-q4_K_M')
OLLAMA_NUM_CTX = int(os.getenv('OLLAMA_NUM_CTX', '4096'))

CHROMA_PERSIST_DIR = BASE_DIR / 'database' / 'chroma_db'
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'ai_specialty_kb')
CHROMA_HNSW_SPACE = os.getenv('CHROMA_HNSW_SPACE', 'cosine')
CHROMA_HNSW_CONSTRUCTION_EF = int(os.getenv('CHROMA_HNSW_CONSTRUCTION_EF', '200'))
CHROMA_HNSW_M = int(os.getenv('CHROMA_HNSW_M', '16'))

EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'simple')
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'BAAI/bge-m3')
EMBEDDING_DEVICE = os.getenv('EMBEDDING_DEVICE', 'cuda')  # 'cuda' or 'cpu'
EMBEDDING_MODEL = {
    'provider': EMBEDDING_PROVIDER,
    'model': EMBEDDING_MODEL_NAME,
    'api_key': os.getenv('OPENAI_API_KEY', ''),
    'dimension': 1024,
}
if EMBEDDING_PROVIDER == 'openai':
    EMBEDDING_MODEL['model'] = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')
    EMBEDDING_MODEL['dimension'] = 1536
elif EMBEDDING_PROVIDER == 'huggingface':
    EMBEDDING_MODEL['dimension'] = 1024
else:
    EMBEDDING_MODEL['dimension'] = 1024

RERANKER_USE_CROSS_ENCODER = _as_bool(os.getenv('RERANKER_USE_CROSS_ENCODER'), True)
RERANKER_CROSS_ENCODER_MODEL = os.getenv('RERANKER_CROSS_ENCODER_MODEL', 'BAAI/bge-reranker-base')
RERANKER_BATCH_SIZE = int(os.getenv('RERANKER_BATCH_SIZE', '32'))
RERANKER_MAX_LENGTH = int(os.getenv('RERANKER_MAX_LENGTH', '512'))
RERANKER_WEIGHTS = {
    'vector_similarity': 0.40,
    'keyword_overlap': 0.25,
    'exact_match': 0.15,
    'phrase_match': 0.10,
    'length_penalty': 0.05,
    'section_score': 0.03,
    'sentence_completeness': 0.01,
    'uniqueness': 0.01,
}

REASONING_ENGINE_ENABLED = _as_bool(os.getenv('REASONING_ENGINE_ENABLED'), True)
REASONING_ENGINE_LOG_STEPS = _as_bool(os.getenv('REASONING_ENGINE_LOG_STEPS'), True)

USE_CHROMADB = _as_bool(os.getenv('USE_CHROMADB'), True)
USE_HYBRID_SEARCH = _as_bool(os.getenv('USE_HYBRID_SEARCH'), True)
VECTOR_SEARCH_WEIGHT = float(os.getenv('VECTOR_SEARCH_WEIGHT', '0.7'))
KEYWORD_SEARCH_WEIGHT = float(os.getenv('KEYWORD_SEARCH_WEIGHT', '0.3'))

MAX_RETRIEVAL_RESULTS = int(os.getenv('MAX_RETRIEVAL_RESULTS', '50'))
MAX_RERANK_RESULTS = int(os.getenv('MAX_RERANK_RESULTS', '20'))
QUERY_VARIANT_LIMIT = int(os.getenv('QUERY_VARIANT_LIMIT', '3'))
FIRST_STAGE_CANDIDATE_K = int(os.getenv('FIRST_STAGE_CANDIDATE_K', '16'))
RERANK_CANDIDATE_K = int(os.getenv('RERANK_CANDIDATE_K', '10'))
FINAL_CONTEXT_K = int(os.getenv('FINAL_CONTEXT_K', '4'))
SECTION_DIVERSITY_LIMIT = int(os.getenv('SECTION_DIVERSITY_LIMIT', '2'))
MIN_EFFECTIVE_CHUNK_LENGTH = int(os.getenv('MIN_EFFECTIVE_CHUNK_LENGTH', '12'))
LOW_QUALITY_CHUNK_FILTER_ENABLED = _as_bool(os.getenv('LOW_QUALITY_CHUNK_FILTER_ENABLED'), True)

CACHE_ENABLED = _as_bool(os.getenv('CACHE_ENABLED'), True)
CACHE_TYPE = os.getenv('CACHE_TYPE', 'memory')
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))
CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REDIS_SESSION_TTL = int(os.getenv('REDIS_SESSION_TTL', '86400'))
REDIS_REQUIRED = _as_bool(os.getenv('REDIS_REQUIRED'), default=False)

SEMANTIC_CACHE_ENABLED = _as_bool(os.getenv('SEMANTIC_CACHE_ENABLED'), True)
SEMANTIC_CACHE_SIMILARITY_THRESHOLD = float(os.getenv('SEMANTIC_CACHE_SIMILARITY_THRESHOLD', '0.88'))
SEMANTIC_CACHE_MAX_SIZE = int(os.getenv('SEMANTIC_CACHE_MAX_SIZE', '1000'))
SEMANTIC_CACHE_TTL = int(os.getenv('SEMANTIC_CACHE_TTL', '3600'))

# ── CRAG 检索质量评估阈值 ──────────────────────────────────────────────────────
CRAG_QUALITY_THRESHOLD_HIGH = float(os.getenv('CRAG_QUALITY_THRESHOLD_HIGH', '0.6'))
CRAG_QUALITY_THRESHOLD_LOW = float(os.getenv('CRAG_QUALITY_THRESHOLD_LOW', '0.3'))

ENABLE_PARALLEL_RETRIEVAL = _as_bool(os.getenv('ENABLE_PARALLEL_RETRIEVAL'), True)
ENABLE_ADAPTIVE_WEIGHTS = _as_bool(os.getenv('ENABLE_ADAPTIVE_WEIGHTS'), True)
TARGET_LATENCY_MS = int(os.getenv('TARGET_LATENCY_MS', '2000'))
ENABLE_EARLY_STOPPING = _as_bool(os.getenv('ENABLE_EARLY_STOPPING'), True)
EARLY_STOPPING_THRESHOLD = float(os.getenv('EARLY_STOPPING_THRESHOLD', '0.9'))

EVALUATION_ENABLED = _as_bool(os.getenv('EVALUATION_ENABLED'), True)
EVALUATION_TEST_DATASET = BASE_DIR / 'backend' / 'evaluation' / 'test_dataset.json'
EVALUATION_OUTPUT_DIR = BASE_DIR / 'evaluation_results'
EVALUATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_METRICS = {
    'retrieval': ['precision@k', 'recall@k', 'mrr', 'ndcg'],
    'generation': ['token_overlap', 'faithfulness', 'answer_length_ratio'],
    'end_to_end': ['answer_relevance', 'context_relevance', 'groundedness'],
}
EVALUATION_K_VALUES = [1, 3, 5, 10]

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ENABLE_METRICS = _as_bool(os.getenv('ENABLE_METRICS'), True)
ENABLE_TRACING = _as_bool(os.getenv('ENABLE_TRACING'), False)

MEMORY_CONFIG = {
    'enable_pagination': True,
    'page_size': int(os.getenv('MEMORY_PAGE_SIZE', '100')),
    'enable_lazy_embedding': True,
    'max_buffer_size': int(os.getenv('MAX_BUFFER_SIZE', '10')),
    'max_buffer_chars': int(os.getenv('MAX_BUFFER_CHARS', '5000')),
    'enable_tfidf_cache': True,
    'tfidf_cache_dir': os.getenv('TFIDF_CACHE_DIR', 'cache/tfidf'),
    'enable_memory_monitor': True,
    'memory_warning_threshold': int(os.getenv('MEMORY_WARNING_THRESHOLD', '50')),
}

AGENT_MAX_ITERATIONS = int(os.getenv('AGENT_MAX_ITERATIONS', '3'))
AGENT_QUALITY_THRESHOLD = float(os.getenv('AGENT_QUALITY_THRESHOLD', '0.7'))
AGENT_ENABLE_QUERY_REFINEMENT = _as_bool(os.getenv('AGENT_ENABLE_QUERY_REFINEMENT'), True)
AGENT_ENABLE_RERANKING = _as_bool(os.getenv('AGENT_ENABLE_RERANKING'), True)
AGENT_TOOLS = {
    'vector_search': {'enabled': True, 'priority': 1, 'timeout': 5.0},
    'keyword_search': {'enabled': True, 'priority': 2, 'timeout': 3.0},
    'hybrid_search': {'enabled': True, 'priority': 0, 'timeout': 8.0},
    'reranker': {'enabled': RERANKER_USE_CROSS_ENCODER, 'priority': 3, 'timeout': 10.0},
}

APPROVAL_ENABLED = _as_bool(os.getenv('APPROVAL_ENABLED'), True)
APPROVAL_MIN_RESULTS = int(os.getenv('APPROVAL_MIN_RESULTS', '2'))
APPROVAL_MIN_QUALITY = float(os.getenv('APPROVAL_MIN_QUALITY', '0.3'))
APPROVAL_TIMEOUT = int(os.getenv('APPROVAL_TIMEOUT', '300'))
APPROVAL_RISK_LEVELS = {
    'low': {'auto_approve': True, 'notify': False},
    'medium': {'auto_approve': False, 'notify': True, 'async_mode': True},
    'high': {'auto_approve': False, 'notify': True, 'async_mode': False, 'require_confirmation': True},
}

# ── GraphRAG 知识图谱配置 ────────────────────────────────────────────────────
GRAPH_RAG_ENABLED = _as_bool(os.getenv('GRAPH_RAG_ENABLED'), True)
GRAPH_RAG_MAX_HOPS = int(os.getenv('GRAPH_RAG_MAX_HOPS', '2'))
GRAPH_RAG_MAX_NODES = int(os.getenv('GRAPH_RAG_MAX_NODES', '30'))
GRAPH_RAG_WEIGHT = float(os.getenv('GRAPH_RAG_WEIGHT', '0.25'))
GRAPH_RAG_COMMUNITY_TOP_K = int(os.getenv('GRAPH_RAG_COMMUNITY_TOP_K', '3'))

RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
RETRY_INITIAL_DELAY = float(os.getenv('RETRY_INITIAL_DELAY', '1.0'))
RETRY_EXPONENTIAL_BASE = float(os.getenv('RETRY_EXPONENTIAL_BASE', '2.0'))
RETRY_MAX_DELAY = float(os.getenv('RETRY_MAX_DELAY', '60.0'))
RETRY_JITTER = _as_bool(os.getenv('RETRY_JITTER'), True)
RETRY_EXCEPTIONS = ['ConnectionError', 'TimeoutError', 'HTTPError', 'RequestException']

METRICS_ENABLED = _as_bool(os.getenv('METRICS_ENABLED'), True)
METRICS_WINDOW_SIZE = int(os.getenv('METRICS_WINDOW_SIZE', '1000'))
METRICS_EXPORT_INTERVAL = int(os.getenv('METRICS_EXPORT_INTERVAL', '60'))
METRICS_CONFIG = {
    'latency': {'enabled': True, 'percentiles': [50, 90, 95, 99]},
    'throughput': {'enabled': True, 'window_seconds': 60},
    'error_rate': {'enabled': True, 'threshold': 0.05},
    'cache_hit_rate': {'enabled': True, 'threshold': 0.3},
}

STRUCTURED_LOGGING = _as_bool(os.getenv('STRUCTURED_LOGGING'), True)
LOG_TO_FILE = _as_bool(os.getenv('LOG_TO_FILE'), True)
LOG_FILE_PATH = BASE_DIR / 'logs' / 'rag_system.log'
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

QUERY_REFINEMENT_STRATEGIES = {
    'keyword_expansion': {'enabled': True, 'max_synonyms': 3},
    'llm_rewrite': {'enabled': True, 'fallback_to_rules': True},
    'decomposition': {'enabled': True, 'max_subqueries': 3},
    'simplification': {'enabled': True, 'remove_stopwords': True},
}

RESULT_EVALUATION_WEIGHTS = {
    'similarity': 0.35,
    'coverage': 0.30,
    'diversity': 0.20,
    'completeness': 0.15,
}
EVALUATION_THRESHOLDS = {
    'similarity': 0.6,
    'coverage': 0.5,
    'diversity': 0.4,
    'completeness': 0.5,
}

PUBLIC_DEMO_MODE = _as_bool(
    os.getenv('PUBLIC_DEMO_MODE'),
    default=not IS_PRODUCTION,
)

SESSION_BACKEND = os.getenv('SESSION_BACKEND', 'auto').strip().lower()
CORS_ORIGINS = _split_csv(os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000'))
KNOWLEDGE_BASE_REQUIRED = _as_bool(os.getenv('KNOWLEDGE_BASE_REQUIRED'), default=IS_PRODUCTION)


def get_cors_origins() -> List[str]:
    return CORS_ORIGINS or ['http://localhost:5173', 'http://localhost:3000']


def validate_runtime_settings() -> List[str]:
    issues: List[str] = []

    if IS_PRODUCTION and PUBLIC_DEMO_MODE:
        issues.append('PUBLIC_DEMO_MODE must be disabled in production.')

    if STRICT_PRODUCTION_MODE and IS_PRODUCTION:
        if SESSION_BACKEND == 'file':
            issues.append('SESSION_BACKEND=file is not allowed when STRICT_PRODUCTION_MODE is enabled.')
        if MONGODB_REQUIRED and not MONGODB_URL:
            issues.append('MONGODB_URL is required in strict production mode.')
        if REDIS_REQUIRED and not REDIS_URL:
            issues.append('REDIS_URL is required when REDIS_REQUIRED=true.')
        if LLM_REQUIRED and not LLM_API_KEY:
            issues.append('LLM_API_KEY is required when LLM_REQUIRED=true.')

    return issues
