# -*- coding: utf-8 -*-
"""
数据模型定义 - 统一版本
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from typing import ForwardRef


# ============ 请求模型 ============

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，首次对话可不提供")
    user_id: Optional[str] = Field(None, description="用户ID")
    use_rag: bool = Field(True, description="是否使用RAG检索")
    enable_thinking: bool = Field(True, description="是否显示思考过程")


class SearchRequest(BaseModel):
    """知识库搜索请求"""
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)


class SessionRequest(BaseModel):
    """会话请求"""
    session_id: Optional[str] = Field(None, description="会话ID，不提供则创建新会话")
    user_id: Optional[str] = Field(None, description="用户ID")


# ============ 思考过程模型 ============

class ThinkingStep(BaseModel):
    """思考步骤"""
    step_id: int = Field(..., description="步骤ID")
    step_name: str = Field(..., description="步骤名称")
    description: str = Field(..., description="步骤描述")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    reasoning: str = Field(..., description="推理过程说明")
    duration_ms: Optional[float] = Field(None, description="耗时（毫秒）")


class ThinkingProcess(BaseModel):
    """完整思考过程"""
    query_analysis: ThinkingStep = Field(..., description="查询分析步骤")
    retrieval: ThinkingStep = Field(..., description="检索步骤")
    reranking: ThinkingStep = Field(..., description="重排序步骤")
    reasoning: ThinkingStep = Field(..., description="推理步骤")
    summary: str = Field(..., description="思考过程总结")
    total_duration_ms: float = Field(..., description="总耗时（毫秒）")


# ============ 响应模型 ============

class KnowledgeChunk(BaseModel):
    """知识块"""
    id: str
    text: str
    char_count: int
    similarity: Optional[float] = Field(None, description="向量检索相似度")
    rerank_score: Optional[float] = Field(None, description="重排序分数")
    section: Optional[str] = Field(None, description="章节标题")


class ChatResponse(BaseModel):
    """聊天响应 - 统一版本"""
    response: str = Field(..., description="AI回复")
    session_id: str = Field(..., description="会话ID")
    sources: List[KnowledgeChunk] = Field(default_factory=list, description="引用的知识来源（重排序后）")
    thinking_process: Optional[ThinkingProcess] = Field(None, description="思考过程（可选显示）")
    cross_reasoning: Optional[str] = Field(None, description="交叉推理内容（<thinking>标签内的内容）")
    is_cross_query: bool = Field(False, description="是否为交叉查询")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SearchResult(BaseModel):
    """搜索结果"""
    query: str
    results: List[KnowledgeChunk]
    total_results: int


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class Message(BaseModel):
    """消息"""
    role: str = Field(..., description="角色：user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionDetail(BaseModel):
    """会话详情"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[Message]


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    agent_name: str
    knowledge_base_loaded: bool
    total_chunks: int
    chromadb_enabled: Optional[bool] = Field(None, description="ChromaDB是否启用")
    reranker_enabled: Optional[bool] = Field(None, description="重排序是否启用")
    timestamp: datetime


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = Field(None, description="错误代码")


# ============ Space 相关模型 ============

class SpaceCreate(BaseModel):
    """创建空间请求"""
    name: str = Field(..., min_length=1, max_length=20, description="空间名称")
    description: Optional[str] = Field(None, max_length=200, description="空间描述")
    icon: str = Field(..., description="图标类名")
    color: str = Field(..., description="颜色类名")


class SpaceUpdate(BaseModel):
    """更新空间请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = None
    color: Optional[str] = None


class SpaceResponse(BaseModel):
    """空间响应"""
    id: str
    name: str
    description: Optional[str]
    icon: str
    color: str
    item_count: int = Field(default=0, alias="itemCount")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class SpaceListResponse(BaseModel):
    """空间列表响应"""
    spaces: List[SpaceResponse]
    total: int


# ============ 认证相关模型 ============

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


class LoginResponse(BaseModel):
    """登录/注册响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: 'UserInfo' = Field(..., description="用户信息")


class TokenResponse(BaseModel):
    """Token 刷新响应"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")