# -*- coding: utf-8 -*-
"""
安信工AI小助手 - FastAPI主应用
提供学生手册智能问答服务的RESTful API
"""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import logging

from fastapi import FastAPI, HTTPException, status, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from config import API_HOST, API_PORT, AGENT_NAME, USE_CHROMADB
try:
    from chroma_knowledge_base import chroma_knowledge_base
except ImportError:
    chroma_knowledge_base = None
try:
    from hybrid_retriever import hybrid_retriever
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
    LoginResponse,
    TokenResponse,
    UserInfo
)
from knowledge_base import knowledge_base
from agent import agent

# 导入 Reasoning-RAG 组件
try:
    from agent_v2 import agent_v2
    AGENT_V2_AVAILABLE = True
except ImportError:
    AGENT_V2_AVAILABLE = False
    agent_v2 = None

try:
    from reranker import reranker
except ImportError:
    reranker = None

from session_manager import session_manager, memory_manager
from routers import spaces_router
from database import close_database, check_connection
from auth import auth_service, get_current_user, verify_token, decode_token, security

logger = logging.getLogger(__name__)


# ============ 应用生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时加载知识库
    print("=" * 60)
    print(f"Starting {AGENT_NAME}...")
    print("=" * 60)

    if knowledge_base.load():
        print("[OK] Knowledge base loaded successfully")
    else:
        print("[FAIL] Failed to load knowledge base")

    print(f"[OK] Database connection: MongoDB")
    print(f"[OK] Server starting: http://{API_HOST}:{API_PORT}")

    # 加载 ChromaDB（如果启用）
    if USE_CHROMADB and chroma_knowledge_base:
        if chroma_knowledge_base.load():
            print("[OK] ChromaDB knowledge base loaded successfully")
        else:
            print("[FAIL] Failed to load ChromaDB knowledge base")

    # 加载混合检索器（如果启用）
    if hybrid_retriever:
        print("[OK] Hybrid retriever enabled")
        stats = hybrid_retriever.get_statistics()
        print(f"  - Vector search: {'Enabled' if stats.get('use_chroma') else 'Disabled'}")
        print(f"  - Keyword search: {'Enabled' if stats.get('use_tfidf') else 'Disabled'}")

    print("=" * 60)

    yield

    # 关闭时的清理工作
    print("Server shutting down...")
    await close_database()


# ============ 创建FastAPI应用 ============

app = FastAPI(
    title=AGENT_NAME,
    description="基于学生手册知识库的智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(spaces_router, prefix="/api/v1", tags=["spaces"])

# 认证路由
auth_router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class UpdateProfileRequest(BaseModel):
    """更新资料请求"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


@auth_router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """
    用户注册

    - **username**: 用户名
    - **password**: 密码
    - **nickname**: 昵称（可选）
    - **avatar**: 头像URL（可选）
    """
    result = await auth_service.register(
        username=request.username,
        password=request.password,
        nickname=request.nickname,
        avatar=request.avatar
    )
    return result


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码
    """
    result = await auth_service.login(
        username=request.username,
        password=request.password
    )
    return result


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌
    """
    result = await auth_service.refresh_token(request.refresh_token)
    return result


@auth_router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    登出当前设备

    需要 Bearer Token
    """
    token = credentials.credentials
    success = await auth_service.logout(token)

    if success:
        return {"status": "success", "message": "已登出"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="登出失败"
        )


@auth_router.post("/logout-all")
async def logout_all(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    登出所有设备

    需要 Bearer Token
    """
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )

    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户信息"
        )

    count = await auth_service.logout_all(user_id)
    return {"status": "success", "message": f"已登出 {count} 个设备"}


@auth_router.get("/me", response_model=UserInfo)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    获取当前用户信息

    需要认证
    """
    return {
        "user_id": user.get('user_id'),
        "username": user.get('username'),
        "nickname": user.get('nickname'),
        "avatar": user.get('avatar'),
        "created_at": user.get('created_at'),
        "updated_at": user.get('updated_at'),
        "last_login": user.get('last_login')
    }


@auth_router.put("/profile")
async def update_profile(
    request: UpdateProfileRequest,
    user: dict = Depends(get_current_user)
):
    """
    更新用户资料

    需要 Bearer Token

    - **nickname**: 昵称（可选）
    - **avatar**: 头像URL（可选）
    """
    success = await auth_service.update_profile(
        user_id=user['user_id'],
        nickname=request.nickname,
        avatar=request.avatar
    )

    if success:
        return {"status": "success", "message": "资料更新成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新失败"
        )


@auth_router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    """
    修改密码

    需要 Bearer Token

    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    success = await auth_service.change_password(
        user_id=user['user_id'],
        old_password=request.old_password,
        new_password=request.new_password
    )

    if success:
        return {"status": "success", "message": "密码修改成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码修改失败"
        )


app.include_router(auth_router)


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


# ============ 聊天端点 ============

@app.post("/api/chat", tags=["聊天"])
async def chat(request: ChatRequest):
    """
    智能问答接口

    - **message**: 用户消息
    - **session_id**: 会话ID（可选）
    - **user_id**: 用户ID（可选）
    - **use_rag**: 是否使用RAG检索（默认true）
    - **enable_thinking**: 是否显示思考过程（默认true）
    """
    try:
        # 获取或创建会话
        if not request.session_id:
            session_id = session_manager.create_session(request.user_id)
        else:
            session_id = request.session_id
            # 验证会话是否存在
            if not session_manager.get_session(session_id):
                session_id = session_manager.create_session(request.user_id)

        # 获取会话历史
        history = session_manager.get_session_history(session_id)

        # 处理查询 - 优先使用 LLM（异步）
        if AGENT_V2_AVAILABLE and agent_v2:
            # 提取 enable_thinking 参数（从额外字段中）
            enable_thinking = getattr(request, 'enable_thinking', True)

            result = agent_v2.process_query(
                query=request.message,
                session_history=history,
                use_rag=request.use_rag,
                enable_thinking=enable_thinking
            )
        else:
            # 使用带 LLM 的异步 agent
            result = await agent.process_query_async(
                query=request.message,
                session_history=history,
                use_rag=request.use_rag,
                use_llm=True  # 启用 LLM
            )

        # 更新会话
        session_manager.update_session(
            session_id=session_id,
            user_message=request.message,
            assistant_message=result['response']
        )

        # 转换知识来源格式
        sources = []
        for source in result.get('sources', []):
            sources.append(KnowledgeChunk(
                id=source.get('id', ''),
                text=source.get('text', ''),
                char_count=source.get('char_count', 0),
                similarity=source.get('similarity')
            ))

        # 构建响应
        response_data = {
            "response": result['response'],
            "session_id": session_id,
            "sources": sources,
            "timestamp": datetime.now()
        }

        # 添加新字段（如果 agent_v2 可用）
        if AGENT_V2_AVAILABLE and agent_v2:
            response_data.update({
                "thinking_process": result.get('thinking_process'),
                "cross_reasoning": result.get('cross_reasoning'),
                "is_cross_query": result.get('is_cross_query', False),
                "metadata": {
                    'retrieval_method': 'chromadb' if agent_v2.use_chromadb else 'tfidf',
                    'rerank_method': 'cross_encoder' if reranker.use_cross_encoder else 'rule_based',
                    'is_cross_query': result.get('is_cross_query', False)
                }
            })

        return response_data

    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求时发生错误: {str(e)}"
        )


@app.post("/api/search", response_model=SearchResult, tags=["搜索"])
async def search(request: SearchRequest):
    """
    知识库搜索接口

    - **query**: 搜索查询
    - **top_k**: 返回结果数量（默认5）
    """
    try:
        if not knowledge_base.is_loaded():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="知识库未加载"
            )

        results = knowledge_base.search(
            query=request.query,
            top_k=request.top_k
        )

        # 转换为响应格式
        chunks = []
        for result in results:
            chunks.append(KnowledgeChunk(
                id=result.get('id', ''),
                text=result.get('text', ''),
                char_count=result.get('char_count', 0),
                similarity=result.get('similarity')
            ))

        return SearchResult(
            query=request.query,
            results=chunks,
            total_results=len(chunks)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索时发生错误: {str(e)}"
        )


# ============ 会话管理端点 ============

@app.post("/api/sessions", response_model=SessionInfo, tags=["会话"])
async def create_session(request: SessionRequest):
    """
    创建新会话

    - **user_id**: 用户ID（可选）
    """
    try:
        if request.session_id:
            # 如果提供了session_id，尝试获取现有会话
            existing_session = session_manager.get_session(request.session_id)
            if existing_session:
                return SessionInfo(
                    session_id=existing_session['session_id'],
                    user_id=existing_session.get('user_id'),
                    created_at=datetime.fromisoformat(existing_session['created_at']),
                    updated_at=datetime.fromisoformat(existing_session['updated_at']),
                    message_count=len(existing_session.get('messages', []))
                )

        # 创建新会话
        session_id = session_manager.create_session(request.user_id)
        session_data = session_manager.get_session(session_id)

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
            detail=f"创建会话时发生错误: {str(e)}"
        )


@app.get("/api/sessions/{session_id}", response_model=SessionDetail, tags=["会话"])
async def get_session(session_id: str):
    """
    获取会话详情

    - **session_id**: 会话ID
    """
    try:
        session_data = session_manager.get_session(session_id)

        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        # 转换消息格式
        messages = []
        for msg in session_data.get('messages', []):
            messages.append({
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': datetime.fromisoformat(msg['timestamp'])
            })

        return SessionDetail(
            session_id=session_data['session_id'],
            user_id=session_data.get('user_id'),
            created_at=datetime.fromisoformat(session_data['created_at']),
            updated_at=datetime.fromisoformat(session_data['updated_at']),
            messages=messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话时发生错误: {str(e)}"
        )


@app.delete("/api/sessions/{session_id}", tags=["会话"])
async def delete_session(session_id: str):
    """
    删除会话

    - **session_id**: 会话ID
    """
    try:
        success = session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return {"status": "success", "message": "会话已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话时发生错误: {str(e)}"
        )


@app.get("/api/users/{user_id}/sessions", tags=["会话"])
async def list_user_sessions(user_id: str):
    """
    列出用户的所有会话

    - **user_id**: 用户ID
    """
    try:
        sessions = session_manager.list_user_sessions(user_id)

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
            detail=f"列出会话时发生错误: {str(e)}"
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