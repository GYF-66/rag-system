# -*- coding: utf-8 -*-
"""
安信工AI小助手 - FastAPI主应用
提供人工智能专业智能问答服务的RESTful API
"""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import logging
import os
import time

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from rate_limit import limiter
from middleware.security import SecurityHeadersMiddleware
from monitoring.metrics import metrics, MetricsMiddleware
from exceptions import register_exception_handlers, QueryProcessingError, KnowledgeBaseError, SessionNotFoundError

from auth import get_current_user, get_optional_current_user
from config import API_HOST, API_PORT, AGENT_NAME, USE_CHROMADB


def _to_knowledge_chunk(s: dict, *, trim_text: bool = False) -> 'KnowledgeChunk':
    """将原始搜索结果字典转换为 KnowledgeChunk，保留来源元数据。"""
    text = s.get('text', '')
    if trim_text:
        from agents.base_agent import trim_to_complete_sentence
        text = trim_to_complete_sentence(text)
    meta = s.get('metadata', {})
    return KnowledgeChunk(
        id=s.get('id', ''),
        text=text,
        char_count=s.get('char_count', len(text)),
        similarity=s.get('similarity'),
        rerank_score=s.get('rerank_score'),
        section=s.get('section') or meta.get('section_path_text') or meta.get('section_title'),
        title=s.get('title') or meta.get('title'),
        document_id=s.get('document_id') or meta.get('document_id'),
        source_path=s.get('source_path') or meta.get('source_path'),
        page_start=s.get('page_start') or meta.get('page_start'),
        page_end=s.get('page_end') or meta.get('page_end'),
    )
try:
    from retrieval.chroma_knowledge_base import chroma_knowledge_base
except ImportError:
    chroma_knowledge_base = None
try:
    from retrieval.hybrid_retriever import hybrid_retriever
except ImportError:
    hybrid_retriever = None
from models import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResult,
    SessionRequest,
    SessionInfo,
    SessionDetail,
    HealthResponse,
    ErrorResponse,
    KnowledgeChunk,
    InteractiveChatRequest,
    InteractiveChatResponse,
    AgentIterationRecord,
    ApprovalRequest,
    QueryRefinementRequest,
    QueryRefinementResponse,
    QuerySuggestion,
    ApprovalDecision,
    PerspectiveChatRequest,
    PerspectiveChatResponse,
    PerspectiveResult,
)
from retrieval.knowledge_base import knowledge_base

# v1 Agent（基础 RAG，作为 v2 不可用时的降级路径）
from agent_v1 import agent

# 导入新的Agent组件
try:
    from rag_agent.rag_agent import RAGAgent
    from rag_agent.query_refiner import QueryRefiner
    from rag_agent.approval_manager import ApprovalManager
    from rag_agent.visualization import ThinkingVisualizer, DecisionExplainer
    from rag_agent.tools import VectorSearchTool, KeywordSearchTool, HybridSearchTool
    from rag_agent.evaluator import ResultEvaluator
    from rag_agent.reranker import CrossEncoderReranker
    RAG_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"新Agent组件导入失败: {e}")
    RAG_AGENT_AVAILABLE = False
    RAGAgent = None
    QueryRefiner = None
    ApprovalManager = None
    ThinkingVisualizer = None

# 导入 Reasoning-RAG 组件
try:
    from agent_v2 import agent_v2
    AGENT_V2_AVAILABLE = True
except ImportError:
    AGENT_V2_AVAILABLE = False
    agent_v2 = None

try:
    from retrieval.reranker import reranker
except ImportError:
    reranker = None

# 导入多视角 Agent
try:
    from agents import multi_perspective_agent
    MULTI_PERSPECTIVE_AVAILABLE = True
except ImportError:
    MULTI_PERSPECTIVE_AVAILABLE = False
    multi_perspective_agent = None

from session_manager import session_manager, memory_manager
from routers import spaces_router, auth_router, graph_router
from database import close_database, check_connection


# ============ 应用生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时加载知识库
    logger.info("=" * 60)
    logger.info(f"Starting {AGENT_NAME}...")
    logger.info("=" * 60)

    if knowledge_base.load():
        logger.info("[OK] Knowledge base loaded successfully")
    else:
        logger.error("[FAIL] Failed to load knowledge base")

    logger.info(f"[OK] Database connection: MongoDB")
    logger.info(f"[OK] Server starting: http://{API_HOST}:{API_PORT}")

    # 加载 ChromaDB（如果启用）
    if USE_CHROMADB and chroma_knowledge_base:
        if chroma_knowledge_base.load():
            logger.info("[OK] ChromaDB knowledge base loaded successfully")
        else:
            logger.error("[FAIL] Failed to load ChromaDB knowledge base")

    # 加载混合检索器（如果启用）
    if hybrid_retriever:
        logger.info("[OK] Hybrid retriever enabled")
        stats = hybrid_retriever.get_statistics()
        logger.info(f"  - Vector search: {'Enabled' if stats.get('use_chroma') else 'Disabled'}")
        logger.info(f"  - Keyword search: {'Enabled' if stats.get('use_tfidf') else 'Disabled'}")

    logger.info("=" * 60)

    yield

    # 关闭时的清理工作
    logger.info("Server shutting down...")
    await close_database()


# ============ 速率限制 ============

# ============ 创建FastAPI应用 ============

app = FastAPI(
    title=AGENT_NAME,
    description="基于人工智能专业知识库的智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 注册速率限制异常处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置CORS - 从环境变量读取，支持开发/生产环境区分
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Length"],
    max_age=3600,
)

# 添加安全响应头中间件
app.add_middleware(SecurityHeadersMiddleware)

# 添加性能指标采集中间件
app.add_middleware(MetricsMiddleware)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(spaces_router, prefix="/api/v1", tags=["spaces"])
app.include_router(auth_router)
app.include_router(graph_router)


# ============ 健康检查端点 ============

@app.get("/", response_model=HealthResponse, tags=["系统"])
async def root():
    """根路径 - 健康检查"""
    return HealthResponse(
        status="healthy",
        agent_name=AGENT_NAME,
        knowledge_base_loaded=knowledge_base.is_loaded(),
        total_chunks=len(knowledge_base.chunks) if knowledge_base.is_loaded() else 0,
        timestamp=datetime.now()
    )


@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        agent_name=AGENT_NAME,
        knowledge_base_loaded=knowledge_base.is_loaded(),
        total_chunks=len(knowledge_base.chunks) if knowledge_base.is_loaded() else 0,
        timestamp=datetime.now()
    )


@app.get("/stats", tags=["系统"])
async def get_statistics():
    """获取系统统计信息"""
    stats = knowledge_base.get_statistics()

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "knowledge_base": stats,
        "agent": {
            "name": AGENT_NAME,
            "role": agent.role,
            "description": agent.description
        },
        "features": {
            "chromadb_enabled": USE_CHROMADB,
            "hybrid_search": hybrid_retriever is not None
        }
    }


@app.get("/health/db", tags=["系统"])
async def database_health_check():
    """数据库健康检查"""
    db_status = await check_connection()
    return db_status


# ============ 性能指标端点 ============

@app.get("/metrics", tags=["系统"])
async def prometheus_metrics():
    """Prometheus 格式性能指标"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=metrics.format_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ============ 聊天端点 ============

@app.post("/api/chat", tags=["聊天"])
@limiter.limit("30/minute")
async def chat(payload: ChatRequest, request: Request, current_user: dict | None = Depends(get_optional_current_user)):
    """
    智能问答接口

    - **message**: 用户消息
    - **session_id**: 会话ID（可选）
    - **user_id**: 用户ID（可选）
    - **use_rag**: 是否使用RAG检索（默认true）
    - **enable_thinking**: 是否显示思考过程（默认true）
    """
    try:
        # 从认证信息获取 user_id（支持免登录）
        user_id = (current_user or {}).get('user_id', payload.user_id) or 'anonymous'

        # 获取或创建会话
        if not payload.session_id:
            session_id = await session_manager.create_session(user_id)
        else:
            session_id = payload.session_id
            if not await session_manager.get_session(session_id):
                session_id = await session_manager.create_session(user_id)

        # 获取会话历史
        history = await session_manager.get_session_history(session_id)

        # 处理查询 - 优先使用 LLM（异步）
        if AGENT_V2_AVAILABLE and agent_v2:
            enable_thinking = getattr(payload, 'enable_thinking', True)
            result = await agent_v2.process_query(
                query=payload.message,
                session_history=history,
                use_rag=payload.use_rag,
                enable_thinking=enable_thinking
            )
        else:
            result = await agent.process_query_async(
                query=payload.message,
                session_history=history,
                use_rag=payload.use_rag,
                use_llm=True
            )

        # 更新会话
        await session_manager.update_session(
            session_id=session_id,
            user_message=payload.message,
            assistant_message=result['response']
        )

        # 转换知识来源格式
        sources = [_to_knowledge_chunk(s) for s in result.get('sources', [])]

        response_data = {
            "response": result['response'],
            "session_id": session_id,
            "sources": sources,
            "timestamp": datetime.now()
        }

        if AGENT_V2_AVAILABLE and agent_v2:
            response_data.update({
                "thinking_process": result.get('thinking_process'),
                "cross_reasoning": result.get('cross_reasoning'),
                "is_cross_query": result.get('is_cross_query', False),
                "graph_context": result.get('graph_context'),
                "metadata": result.get('metadata', {
                    'retrieval_method': 'chromadb' if agent_v2.use_chromadb else 'tfidf',
                    'rerank_method': 'cross_encoder' if (reranker and reranker.use_cross_encoder) else 'rule_based',
                    'is_cross_query': result.get('is_cross_query', False),
                }),
            })

        return response_data

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"聊天处理失败: {e}\n{tb}")
        print(f"\n{'='*60}\n[CHAT ERROR] {e}\n{tb}\n{'='*60}", flush=True)
        raise QueryProcessingError("处理请求时发生内部错误，请稍后重试")


# ============ SSE 流式聊天端点 ============

@app.post("/api/chat/stream", tags=["聊天"])
@limiter.limit("30/minute")
async def chat_stream(payload: ChatRequest, request: Request, current_user: dict | None = Depends(get_optional_current_user)):
    """
    SSE 流式智能问答接口 — 逐 token 返回 LLM 生成结果

    事件类型:
    - **metadata**: 检索阶段结果（sources, thinking_process, graph_context）
    - **token**: LLM 生成的文本 token
    - **reflection**: Self-RAG 反思验证结果
    - **done**: 流结束信号
    - **error**: 错误信息
    """
    import json as _json
    from fastapi.responses import StreamingResponse

    async def event_generator():
        try:
            # ── 会话管理（与 /api/chat 一致）──
            user_id = payload.user_id
            if current_user:
                user_id = user_id or current_user.get('sub') or current_user.get('user_id')

            session_id = payload.session_id
            if not session_id:
                session_id = await session_manager.create_session(user_id)
            elif not await session_manager.get_session(session_id):
                session_id = await session_manager.create_session(user_id)

            history = await session_manager.get_session_history(session_id)

            if not (AGENT_V2_AVAILABLE and agent_v2):
                yield _sse('error', {'message': 'Agent v2 not available'})
                yield _sse('done', {})
                return

            # ── 检索 + 预处理（非流式部分）──
            import time as _time
            total_start = _time.time()

            query_analysis = agent_v2._analyze_query(payload.message)
            sources, retrieval_info = await agent_v2._retrieve_sources(payload.message, payload.use_rag, query_analysis)

            # CRAG
            crag_info: dict = {}
            from config import SEARCH_TOP_K
            from pipeline.adaptive_router import ROUTE_SIMPLE
            adaptive_k = query_analysis.get('adaptive_top_k', SEARCH_TOP_K)
            route = retrieval_info.get('route', 'standard')
            try:
                from retrieval.crag_evaluator import quality_evaluator, apply_corrections
            except Exception:
                quality_evaluator = None
                apply_corrections = None
            if quality_evaluator and sources and route != ROUTE_SIMPLE:
                crag_eval = quality_evaluator.evaluate(payload.message, sources, query_analysis)
                crag_info = crag_eval
                if crag_eval.get('action') != 'accept' and apply_corrections:
                    retriever = agent_v2._hybrid_retriever or (chroma_knowledge_base if agent_v2.use_chromadb else knowledge_base)
                    sources, correction_result = apply_corrections(payload.message, sources, crag_eval, retriever=retriever, top_k=adaptive_k)
                    crag_info['correction'] = correction_result

            sources = agent_v2._prepare_sources(payload.message, sources, query_analysis)
            context = agent_v2._build_context(sources)
            graph_supplement, graph_context = agent_v2._build_course_graph_supplement(payload.message, query_analysis)
            if graph_supplement:
                context = f"{context}\n\n{graph_supplement}" if context else graph_supplement

            retrieval_duration = (_time.time() - total_start) * 1000

            # ── 发送 metadata 事件 ──
            from retrieval.reranker import reranker
            metadata_payload = {
                'session_id': session_id,
                'sources': [_to_knowledge_chunk(s).model_dump(mode='json') for s in sources],
                'graph_context': graph_context,
                'metadata': {
                    'retrieval_method': retrieval_info.get('method', 'tfidf'),
                    'adaptive_route': retrieval_info.get('route', 'standard'),
                    'hyde_used': retrieval_info.get('hyde_used', False),
                    'graph_rag_used': agent_v2._graph_retriever is not None,
                    'cot_used': True,
                    'source_count': len(sources),
                    'rerank_method': 'cross_encoder' if reranker and reranker.use_cross_encoder else 'rule_based',
                    'crag_evaluation': {'quality_score': crag_info.get('quality_score'), 'action': crag_info.get('action')} if crag_info else None,
                },
            }
            yield _sse('metadata', metadata_payload)

            # ── 构建 CoT prompt ──
            cot_prompt = agent_v2._build_cot_system_prompt(query_analysis, sources)

            # ── 流式 LLM 生成 ──
            from llm_service import llm_service
            if not llm_service or not llm_service.is_available():
                # fallback 非流式
                response_text = agent_v2._response_gen.generate(payload.message, context, sources)
                yield _sse('token', {'content': response_text})
                yield _sse('done', {'total_duration_ms': (_time.time() - total_start) * 1000})
                return

            full_response = ''
            async for chunk in llm_service.chat_stream(payload.message, context, history, system_prompt=cot_prompt):
                if chunk:
                    full_response += chunk
                    yield _sse('token', {'content': chunk})

            # ── 解析 CoT 响应 ──
            final_answer, cot_reasoning = agent_v2._parse_cot_response(full_response)

            # 如果 CoT 解析提取了 answer（不含 thinking），发送替换事件
            if final_answer != full_response:
                yield _sse('answer_replace', {'content': final_answer})

            # ── Self-RAG 反思 ──
            reflection_data = None
            if sources:
                try:
                    from models import ReflectionResult
                    reflection_result, _ = await agent_v2._self_rag_reflect(
                        payload.message, final_answer, sources, llm_service,
                    )
                    reflection_data = reflection_result.model_dump(mode='json')
                    yield _sse('reflection', reflection_data)
                except Exception:
                    pass

            # ── 构建思维过程 ──
            generation_duration = (_time.time() - total_start) * 1000 - retrieval_duration
            thinking_process = agent_v2._build_thinking_process(
                query_analysis, sources, [],
                [0, retrieval_duration, 0, generation_duration, 0],
                retrieval_info, crag_info,
                cot_reasoning=cot_reasoning,
                reflection_result=reflection_result if reflection_data else None,
            )
            yield _sse('thinking', thinking_process.model_dump(mode='json'))

            # ── 更新会话 ──
            await session_manager.update_session(session_id, payload.message, final_answer)

            total_duration = (_time.time() - total_start) * 1000
            metadata_payload['metadata']['total_duration_ms'] = total_duration
            metadata_payload['metadata']['self_rag_reflection'] = reflection_result.status if reflection_data else None
            yield _sse('done', {'total_duration_ms': total_duration})

        except Exception as exc:
            import traceback
            logger.error(f"SSE chat error: {exc}\n{traceback.format_exc()}")
            yield _sse('error', {'message': str(exc)})

    return StreamingResponse(event_generator(), media_type='text/event-stream')


def _sse(event: str, data: dict) -> str:
    """格式化 SSE 事件"""
    import json as _json
    return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@app.post("/api/chat/perspectives", response_model=PerspectiveChatResponse, tags=["多视角聊天"])
@limiter.limit("15/minute")
async def chat_perspectives(
    payload: PerspectiveChatRequest,
    request: Request,
    current_user: dict | None = Depends(get_optional_current_user),
):
    """
    多视角智能问答接口 —— 学霸 + 教师并行分析

    - **message**: 用户消息
    - **session_id**: 会话ID（可选）
    - **perspectives**: 要使用的视角列表（可选，默认全部）
    """
    if not MULTI_PERSPECTIVE_AVAILABLE or not multi_perspective_agent:
        raise QueryProcessingError("多视角 Agent 不可用")

    try:
        user_id = (current_user or {}).get('user_id', payload.user_id) or 'anonymous'

        # 会话管理
        if not payload.session_id:
            session_id = await session_manager.create_session(user_id)
        else:
            session_id = payload.session_id
            if not await session_manager.get_session(session_id):
                session_id = await session_manager.create_session(user_id)

        history = await session_manager.get_session_history(session_id)

        # 1. 复用 agent_v2 / agent 做 RAG 检索获取上下文
        start_time = time.time()
        if AGENT_V2_AVAILABLE and agent_v2 and payload.use_rag:
            rag_result = await agent_v2.process_query(
                query=payload.message,
                session_history=history,
                use_rag=True,
                enable_thinking=False,
            )
        elif payload.use_rag:
            rag_result = await agent.process_query_async(
                query=payload.message,
                session_history=history,
                use_rag=True,
                use_llm=False,
            )
        else:
            rag_result = {'sources': [], 'response': ''}

        # 构建共享上下文
        raw_sources = rag_result.get('sources', [])
        context_parts = []
        for i, s in enumerate(raw_sources, 1):
            text = s.get('text', '')
            section = s.get('section', '')
            context_parts.append(f"[来源{i}] {section}\n{text}")
        context = '\n\n'.join(context_parts)

        # 2. 根据请求的 perspectives 并行调用各 Agent
        if payload.perspectives:
            import asyncio
            tasks = [
                multi_perspective_agent.generate_perspective(
                    p, payload.message, context, history,
                    shared_sources=raw_sources,
                )
                for p in payload.perspectives
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            perspective_results = list(results)
        else:
            perspective_results = await multi_perspective_agent.generate_dual(
                payload.message, context, history,
                shared_sources=raw_sources,
            )

        total_duration = (time.time() - start_time) * 1000

        # 3. 更新会话 —— 取第一个有效回答作为助手消息
        first_valid = next(
            (r for r in perspective_results if r.get('response')), None,
        )
        if first_valid:
            await session_manager.update_session(
                session_id=session_id,
                user_message=payload.message,
                assistant_message=first_valid['response'],
            )

        # 4. 构建响应
        sources = [_to_knowledge_chunk(s, trim_text=True) for s in raw_sources]

        return PerspectiveChatResponse(
            perspectives=[
                PerspectiveResult(**r) for r in perspective_results
            ],
            session_id=session_id,
            sources=sources,
            timestamp=datetime.now(),
            total_duration_ms=total_duration,
            metadata={
                'retrieval_method': 'chromadb' if (AGENT_V2_AVAILABLE and agent_v2 and agent_v2.use_chromadb) else 'tfidf',
                'perspective_count': len(perspective_results),
            },
        )

    except Exception as e:
        logger.error(f"多视角聊天处理失败: {e}")
        raise QueryProcessingError("处理多视角请求时发生内部错误，请稍后重试")


@app.post("/api/search", response_model=SearchResult, tags=["搜索"])
async def search(request: SearchRequest, current_user: dict | None = Depends(get_optional_current_user)):
    """
    知识库搜索接口

    - **query**: 搜索查询
    - **top_k**: 返回结果数量（默认5）
    """
    try:
        if not knowledge_base.is_loaded():
            raise KnowledgeBaseError()

        results = knowledge_base.search(
            query=request.query,
            top_k=request.top_k
        )

        chunks = [_to_knowledge_chunk(r) for r in results]

        return SearchResult(
            query=request.query,
            results=chunks,
            total_results=len(chunks)
        )

    except KnowledgeBaseError:
        raise
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise QueryProcessingError("搜索时发生内部错误，请稍后重试")


# ============ 交互式Agent端点 ============

@app.post("/api/chat/interactive", response_model=InteractiveChatResponse, tags=["交互式聊天"])
@limiter.limit("20/minute")
async def interactive_chat(payload: InteractiveChatRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    交互式智能问答接口（带Agent Loop可视化）
    
    - **message**: 用户消息
    - **session_id**: 会话ID（可选）
    - **enable_approval**: 是否启用审批机制
    - **enable_visualization**: 是否显示思考过程可视化
    - **max_iterations**: 最大迭代次数
    - **quality_threshold**: 质量阈值
    """
    try:
        if not RAG_AGENT_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="交互式Agent功能暂不可用，请使用标准聊天接口"
            )
        
        # 从认证信息获取 user_id
        user_id = current_user.get('user_id', payload.user_id)
        
        # 获取或创建会话
        if not payload.session_id:
            session_id = await session_manager.create_session(user_id)
        else:
            session_id = payload.session_id
            if not await session_manager.get_session(session_id):
                session_id = await session_manager.create_session(user_id)
        
        # 获取会话历史
        history = await session_manager.get_session_history(session_id)
        
        # 初始化Agent组件
        vector_tool = VectorSearchTool(knowledge_base)
        keyword_tool = KeywordSearchTool(knowledge_base)
        hybrid_tool = HybridSearchTool(knowledge_base, knowledge_base)
        
        evaluator = ResultEvaluator()
        cross_reranker = CrossEncoderReranker() if reranker else None
        approval_manager = ApprovalManager() if payload.enable_approval else None
        
        # 创建RAG Agent
        rag_agent = RAGAgent(
            tools=[vector_tool, keyword_tool, hybrid_tool],
            evaluator=evaluator,
            reranker=cross_reranker,
            approval_manager=approval_manager,
            max_iterations=payload.max_iterations,
            quality_threshold=payload.quality_threshold
        )
        
        # 执行Agent查询
        start_time = time.time()
        agent_result = await rag_agent.process_query(
            query=payload.message,
            session_history=history
        )
        total_duration = (time.time() - start_time) * 1000
        
        # 转换迭代记录
        iterations = [
            AgentIterationRecord(
                iteration=record.iteration,
                strategy=record.strategy,
                tool_used=record.tool_used,
                results_count=len(record.results),
                quality_score={
                    'similarity': record.quality.similarity,
                    'coverage': record.quality.coverage,
                    'diversity': record.quality.diversity,
                    'completeness': record.quality.completeness,
                    'overall': record.quality.overall
                },
                decision=record.decision,
                duration_ms=record.duration_ms
            )
            for record in agent_result.iteration_records
        ]
        
        # 生成可视化
        thinking_visualization = None
        thinking_tree = None
        if request.enable_visualization and ThinkingVisualizer:
            visualizer = ThinkingVisualizer()
            thinking_visualization = visualizer.format_thinking_process(
                agent_result.iteration_records,
                include_summary=True
            )
            thinking_tree = visualizer.create_decision_tree(agent_result.iteration_records)
        
        # 转换知识来源
        sources = [_to_knowledge_chunk(s) for s in agent_result.final_results]
        
        # 检查是否需要审批
        approval_required = agent_result.needs_approval
        approval_request_data = None
        
        if approval_required and agent_result.approval_request:
            approval_request_data = ApprovalRequest(
                request_id=agent_result.approval_request.get('request_id', ''),
                reason=agent_result.approval_request.get('reason', ''),
                results=sources,
                quality_score={
                    'similarity': agent_result.final_quality.similarity,
                    'coverage': agent_result.final_quality.coverage,
                    'diversity': agent_result.final_quality.diversity,
                    'completeness': agent_result.final_quality.completeness,
                    'overall': agent_result.final_quality.overall
                },
                risk_level=agent_result.approval_request.get('risk_level', 'medium')
            )
        
        # 生成回复（如果不需要审批）
        response_text = agent_result.response if not approval_required else "等待人工审批..."
        
        # 更新会话
        if not approval_required:
            await session_manager.update_session(
                session_id=session_id,
                user_message=payload.message,
                assistant_message=response_text
            )
        
        return InteractiveChatResponse(
            response=response_text,
            session_id=session_id,
            sources=sources,
            iterations=iterations,
            thinking_visualization=thinking_visualization,
            thinking_tree=thinking_tree,
            final_quality={
                'similarity': agent_result.final_quality.similarity,
                'coverage': agent_result.final_quality.coverage,
                'diversity': agent_result.final_quality.diversity,
                'completeness': agent_result.final_quality.completeness,
                'overall': agent_result.final_quality.overall
            },
            approval_required=approval_required,
            approval_request=approval_request_data,
            total_duration_ms=total_duration,
            timestamp=datetime.now(),
            metadata={
                'total_iterations': len(iterations),
                'final_strategy': agent_result.final_strategy,
                'tools_used': list(set(r.tool_used for r in agent_result.iteration_records if r.tool_used))
            }
        )
        
    except Exception as e:
        logger.error(f"交互式聊天处理失败: {e}", exc_info=True)
        raise QueryProcessingError("处理交互式请求时发生内部错误，请稍后重试")


@app.post("/api/chat/refine", response_model=QueryRefinementResponse, tags=["交互式聊天"])
@limiter.limit("30/minute")
async def refine_query(payload: QueryRefinementRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    查询改进建议接口
    
    - **query**: 原始查询
    - **session_id**: 会话ID（可选）
    - **strategies**: 指定使用的改进策略（可选）
    - **max_suggestions**: 最大建议数量
    """
    try:
        if not RAG_AGENT_AVAILABLE or not QueryRefiner:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="查询改进功能暂不可用"
            )
        
        # 获取会话历史（如果提供了session_id）
        history = []
        if payload.session_id:
            history = await session_manager.get_session_history(payload.session_id)
        
        # 初始化查询改进器
        refiner = QueryRefiner()
        
        # 分析查询
        analysis = refiner.analyze_query(payload.query)
        
        # 生成改进建议
        suggestions = []
        strategies_to_use = payload.strategies or ['keyword_expansion', 'llm_rewrite', 'decomposition']
        
        for strategy in strategies_to_use[:payload.max_suggestions]:
            if strategy == 'keyword_expansion':
                refined = refiner.expand_keywords(payload.query)
                suggestions.append(QuerySuggestion(
                    refined_query=refined,
                    strategy='keyword_expansion',
                    explanation='通过添加同义词和相关术语扩展查询',
                    confidence=0.8
                ))
            elif strategy == 'llm_rewrite':
                refined = await refiner.rewrite_with_llm(payload.query, history)
                suggestions.append(QuerySuggestion(
                    refined_query=refined,
                    strategy='llm_rewrite',
                    explanation='使用LLM重写查询以提高清晰度',
                    confidence=0.9
                ))
            elif strategy == 'decomposition':
                sub_queries = refiner.decompose_query(payload.query)
                if sub_queries:
                    suggestions.append(QuerySuggestion(
                        refined_query=' + '.join(sub_queries),
                        strategy='decomposition',
                        explanation=f'将复杂查询分解为{len(sub_queries)}个子查询',
                        confidence=0.85
                    ))
        
        return QueryRefinementResponse(
            original_query=payload.query,
            suggestions=suggestions[:payload.max_suggestions],
            analysis={
                'length': analysis.get('length', 0),
                'complexity': analysis.get('complexity', 'medium'),
                'intent': analysis.get('intent', 'unknown'),
                'keywords': analysis.get('keywords', [])
            },
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"查询改进失败: {e}", exc_info=True)
        raise QueryProcessingError("生成查询改进建议时发生内部错误，请稍后重试")


@app.post("/api/chat/approve", tags=["交互式聊天"])
@limiter.limit("30/minute")
async def approve_results(decision: ApprovalDecision, request: Request, current_user: dict = Depends(get_current_user)):
    """
    审批决策接口
    
    - **request_id**: 请求ID
    - **approved**: 是否批准
    - **feedback**: 用户反馈（可选）
    - **selected_results**: 用户选择的结果索引（可选）
    """
    try:
        if not RAG_AGENT_AVAILABLE or not ApprovalManager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="审批功能暂不可用"
            )
        
        # 这里应该从缓存或数据库中获取待审批的请求
        # 简化实现：直接返回决策结果
        
        return {
            "status": "success",
            "request_id": decision.request_id,
            "approved": decision.approved,
            "message": "审批决策已记录" if decision.approved else "已拒绝，请重新查询",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"审批处理失败: {e}", exc_info=True)
        raise QueryProcessingError("处理审批决策时发生内部错误，请稍后重试")


# ============ 会话管理端点 ============

@app.post("/api/sessions", response_model=SessionInfo, tags=["会话"])
async def create_session(request: SessionRequest, current_user: dict = Depends(get_current_user)):
    """
    创建新会话

    - **user_id**: 用户ID（可选）
    """
    try:
        if request.session_id:
            # 如果提供了session_id，尝试获取现有会话
            existing_session = await session_manager.get_session(request.session_id)
            if existing_session:
                return SessionInfo(
                    session_id=existing_session['session_id'],
                    user_id=existing_session.get('user_id'),
                    created_at=datetime.fromisoformat(existing_session['created_at']),
                    updated_at=datetime.fromisoformat(existing_session['updated_at']),
                    message_count=len(existing_session.get('messages', []))
                )

        # 创建新会话
        session_id = await session_manager.create_session(request.user_id)
        session_data = await session_manager.get_session(session_id)

        return SessionInfo(
            session_id=session_data['session_id'],
            user_id=session_data.get('user_id'),
            created_at=datetime.fromisoformat(session_data['created_at']),
            updated_at=datetime.fromisoformat(session_data['updated_at']),
            message_count=len(session_data.get('messages', []))
        )

    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建会话时发生内部错误"
        )


@app.get("/api/sessions/{session_id}", response_model=SessionDetail, tags=["会话"])
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    获取会话详情

    - **session_id**: 会话ID
    """
    try:
        session_data = await session_manager.get_session(session_id)

        if not session_data:
            raise SessionNotFoundError(session_id)

        messages = [
            {
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': datetime.fromisoformat(msg['timestamp'])
            }
            for msg in session_data.get('messages', [])
        ]

        return SessionDetail(
            session_id=session_data['session_id'],
            user_id=session_data.get('user_id'),
            created_at=datetime.fromisoformat(session_data['created_at']),
            updated_at=datetime.fromisoformat(session_data['updated_at']),
            messages=messages
        )

    except SessionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        raise QueryProcessingError("获取会话时发生内部错误，请稍后重试")


@app.delete("/api/sessions/{session_id}", tags=["会话"])
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    删除会话

    - **session_id**: 会话ID
    """
    try:
        success = await session_manager.delete_session(session_id)

        if not success:
            raise SessionNotFoundError(session_id)

        return {"status": "success", "message": "会话已删除"}

    except SessionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise QueryProcessingError("删除会话时发生内部错误，请稍后重试")


@app.get("/api/users/{user_id}/sessions", tags=["会话"])
async def list_user_sessions(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    列出用户的所有会话

    - **user_id**: 用户ID
    """
    try:
        sessions = await session_manager.list_user_sessions(user_id)

        # 转换为响应格式
        session_list = []
        for sess in sessions:
            session_list.append(SessionInfo(
                session_id=sess['session_id'],
                user_id=user_id,
                created_at=datetime.fromisoformat(sess['created_at']),
                updated_at=datetime.fromisoformat(sess['updated_at']),
                message_count=sess['message_count']
            ))

        return {
            "user_id": user_id,
            "sessions": session_list,
            "total": len(session_list)
        }

    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="列出会话时发生内部错误"
        )


# ============ 启动服务器 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )


