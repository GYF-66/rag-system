# -*- coding: utf-8 -*-
"""Pydantic models used by the backend API and agent flows."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description='用户消息')
    session_id: Optional[str] = Field(None, description='会话 ID')
    user_id: Optional[str] = Field(None, description='用户 ID')
    use_rag: bool = Field(True, description='是否启用检索增强')
    enable_thinking: bool = Field(True, description='是否返回思考过程')


class SearchRequest(BaseModel):
    query: str = Field(..., description='检索查询')
    top_k: int = Field(5, description='返回结果数量', ge=1, le=20)


class SessionRequest(BaseModel):
    session_id: Optional[str] = Field(None, description='会话 ID')
    user_id: Optional[str] = Field(None, description='用户 ID')


class ThinkingStep(BaseModel):
    step_id: int = Field(..., description='步骤 ID')
    step_name: str = Field(..., description='步骤名称')
    description: str = Field(..., description='步骤说明')
    input_data: Optional[Dict[str, Any]] = Field(None, description='输入数据')
    output_data: Optional[Dict[str, Any]] = Field(None, description='输出数据')
    reasoning: str = Field(..., description='推理说明')
    duration_ms: Optional[float] = Field(None, description='耗时毫秒')


class ReflectionResult(BaseModel):
    """Self-RAG 反思验证结果"""
    status: str = Field(..., description='验证状态: supported / partially_supported / not_supported')
    confidence: float = Field(0.0, description='置信度 0-1')
    issues: List[str] = Field(default_factory=list, description='发现的问题')
    revision_applied: bool = Field(False, description='是否应用了修正')
    duration_ms: Optional[float] = Field(None, description='反思耗时毫秒')


class ThinkingProcess(BaseModel):
    query_analysis: ThinkingStep = Field(..., description='查询分析步骤')
    retrieval: ThinkingStep = Field(..., description='检索步骤')
    reranking: ThinkingStep = Field(..., description='重排步骤')
    reasoning: ThinkingStep = Field(..., description='生成步骤')
    reflection: Optional[ThinkingStep] = Field(None, description='Self-RAG 反思步骤')
    reflection_result: Optional[ReflectionResult] = Field(None, description='反思验证结果')
    summary: str = Field(..., description='思考摘要')
    total_duration_ms: float = Field(..., description='总耗时毫秒')


class KnowledgeChunk(BaseModel):
    id: str
    text: str
    char_count: int
    similarity: Optional[float] = Field(None, description='相似度')
    rerank_score: Optional[float] = Field(None, description='重排分数')
    section: Optional[str] = Field(None, description='章节标题')
    title: Optional[str] = Field(None, description='文档标题')
    document_id: Optional[str] = Field(None, description='文档 ID')
    source_path: Optional[str] = Field(None, description='来源路径')
    page_start: Optional[int] = Field(None, description='起始页码')
    page_end: Optional[int] = Field(None, description='结束页码')
    metadata: Dict[str, Any] = Field(default_factory=dict, description='详细元数据')


class ChatResponse(BaseModel):
    response: str = Field(..., description='回答内容')
    session_id: str = Field(..., description='会话 ID')
    sources: List[KnowledgeChunk] = Field(default_factory=list, description='引用来源')
    thinking_process: Optional[ThinkingProcess] = Field(None, description='思考过程')
    cross_reasoning: Optional[str] = Field(None, description='交叉推理内容')
    is_cross_query: bool = Field(False, description='是否交叉查询')
    timestamp: datetime = Field(default_factory=datetime.now, description='响应时间')
    metadata: Dict[str, Any] = Field(default_factory=dict, description='响应元数据')


class SearchResult(BaseModel):
    query: str
    results: List[KnowledgeChunk]
    total_results: int


class SessionInfo(BaseModel):
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class Message(BaseModel):
    role: str = Field(..., description='消息角色')
    content: str = Field(..., description='消息内容')
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionDetail(BaseModel):
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[Message]


class HealthResponse(BaseModel):
    status: str
    agent_name: str
    knowledge_base_loaded: bool
    total_chunks: int
    chromadb_enabled: Optional[bool] = Field(None, description='是否启用 ChromaDB')
    reranker_enabled: Optional[bool] = Field(None, description='是否启用 reranker')
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = Field(None, description='错误码')


class SpaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=20, description='空间名称')
    description: Optional[str] = Field(None, max_length=200, description='空间描述')
    icon: str = Field(..., description='图标名')
    color: str = Field(..., description='颜色值')


class SpaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = None
    color: Optional[str] = None


class SpaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    icon: str
    color: str
    item_count: int = Field(default=0, alias='itemCount')
    updated_at: datetime = Field(alias='updatedAt')

    model_config = ConfigDict(populate_by_name=True)


class SpaceListResponse(BaseModel):
    spaces: List[SpaceResponse]
    total: int


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description='用户名')
    password: str = Field(..., min_length=6, max_length=50, description='密码')
    nickname: Optional[str] = Field(None, max_length=50, description='昵称')
    avatar: Optional[str] = Field(None, description='头像 URL')


class LoginRequest(BaseModel):
    username: str = Field(..., description='用户名')
    password: str = Field(..., description='密码')


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description='刷新令牌')


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description='昵称')
    avatar: Optional[str] = Field(None, description='头像 URL')


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description='旧密码')
    new_password: str = Field(..., min_length=6, max_length=50, description='新密码')


class UserInfo(BaseModel):
    user_id: str = Field(..., description='用户 ID')
    username: str = Field(..., description='用户名')
    nickname: Optional[str] = Field(None, description='昵称')
    avatar: Optional[str] = Field(None, description='头像 URL')
    created_at: Optional[datetime] = Field(None, description='创建时间')
    updated_at: Optional[datetime] = Field(None, description='更新时间')
    last_login: Optional[datetime] = Field(None, description='最近登录时间')


class LoginResponse(BaseModel):
    access_token: str = Field(..., description='访问令牌')
    refresh_token: str = Field(..., description='刷新令牌')
    token_type: str = Field('bearer', description='令牌类型')
    expires_in: int = Field(..., description='过期秒数')
    user: UserInfo = Field(..., description='用户信息')


class TokenResponse(BaseModel):
    access_token: str = Field(..., description='访问令牌')
    token_type: str = Field('bearer', description='令牌类型')
    expires_in: int = Field(..., description='过期秒数')


class InteractiveChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description='用户消息')
    session_id: Optional[str] = Field(None, description='会话 ID')
    user_id: Optional[str] = Field(None, description='用户 ID')
    enable_approval: bool = Field(True, description='是否启用审批')
    enable_visualization: bool = Field(True, description='是否启用可视化')
    max_iterations: Optional[int] = Field(None, description='最大迭代次数', ge=1, le=10)
    quality_threshold: Optional[float] = Field(None, description='质量阈值', ge=0.0, le=1.0)


class AgentIterationRecord(BaseModel):
    iteration: int = Field(..., description='迭代次数')
    strategy: str = Field(..., description='使用策略')
    tool_used: Optional[str] = Field(None, description='使用工具')
    results_count: int = Field(..., description='结果数量')
    quality_score: Dict[str, float] = Field(..., description='质量评分')
    decision: str = Field(..., description='决策说明')
    duration_ms: float = Field(..., description='耗时毫秒')


class ApprovalRequest(BaseModel):
    request_id: str = Field(..., description='请求 ID')
    reason: str = Field(..., description='审批原因')
    results: List[KnowledgeChunk] = Field(..., description='待审批结果')
    quality_score: Dict[str, float] = Field(..., description='质量评分')
    risk_level: str = Field(..., description='风险等级')


class InteractiveChatResponse(BaseModel):
    response: str = Field(..., description='回答内容')
    session_id: str = Field(..., description='会话 ID')
    sources: List[KnowledgeChunk] = Field(default_factory=list, description='引用来源')
    iterations: List[AgentIterationRecord] = Field(default_factory=list, description='迭代记录')
    thinking_visualization: Optional[str] = Field(None, description='思考过程可视化')
    thinking_tree: Optional[str] = Field(None, description='思考树')
    final_quality: Dict[str, float] = Field(default_factory=dict, description='最终质量评分')
    approval_required: bool = Field(False, description='是否需要审批')
    approval_request: Optional[ApprovalRequest] = Field(None, description='审批请求')
    total_duration_ms: float = Field(..., description='总耗时毫秒')
    timestamp: datetime = Field(default_factory=datetime.now, description='响应时间')
    metadata: Dict[str, Any] = Field(default_factory=dict, description='响应元数据')


class QueryRefinementRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description='原始查询')
    session_id: Optional[str] = Field(None, description='会话 ID')
    strategies: Optional[List[str]] = Field(None, description='改写策略')
    max_suggestions: int = Field(3, description='最大建议数', ge=1, le=10)


class QuerySuggestion(BaseModel):
    refined_query: str = Field(..., description='改写后的查询')
    strategy: str = Field(..., description='使用策略')
    explanation: str = Field(..., description='改写说明')
    confidence: float = Field(..., description='置信度', ge=0.0, le=1.0)


class QueryRefinementResponse(BaseModel):
    original_query: str = Field(..., description='原始查询')
    suggestions: List[QuerySuggestion] = Field(..., description='改写建议')
    analysis: Dict[str, Any] = Field(default_factory=dict, description='查询分析')
    timestamp: datetime = Field(default_factory=datetime.now, description='响应时间')


class ApprovalDecision(BaseModel):
    request_id: str = Field(..., description='请求 ID')
    approved: bool = Field(..., description='是否通过')
    feedback: Optional[str] = Field(None, description='反馈')
    selected_results: Optional[List[int]] = Field(None, description='选中的结果索引')


# ============ 多视角 Agent 模型 ============


class PerspectiveStep(BaseModel):
    step: str = Field(..., description='步骤标识')
    description: str = Field(..., description='步骤描述')
    duration_ms: Optional[float] = Field(None, description='步骤耗时毫秒')
    output: Optional[Any] = Field(None, description='步骤输出摘要')


class SupplementalSource(BaseModel):
    id: str = Field('', description='来源 ID')
    text: str = Field('', description='来源文本摘要')
    section: str = Field('', description='来源章节')
    similarity: Optional[float] = Field(None, description='相似度分数')


class PerspectiveResult(BaseModel):
    perspective: str = Field(..., description='视角标识')
    name: str = Field(..., description='视角名称')
    icon: str = Field(..., description='视角图标')
    tagline: str = Field(..., description='视角标语')
    response: str = Field(..., description='回答内容')
    duration_ms: Optional[float] = Field(None, description='耗时毫秒')
    error: Optional[str] = Field(None, description='错误信息')
    steps: Optional[List[PerspectiveStep]] = Field(None, description='推理步骤记录')
    supplemental_sources: Optional[List[SupplementalSource]] = Field(
        None, description='视角补充检索来源',
    )


class PerspectiveChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description='用户消息')
    session_id: Optional[str] = Field(None, description='会话 ID')
    user_id: Optional[str] = Field(None, description='用户 ID')
    use_rag: bool = Field(True, description='是否启用检索增强')
    perspectives: Optional[List[str]] = Field(
        None, description='要使用的视角列表，为空时使用全部视角',
    )


class PerspectiveChatResponse(BaseModel):
    perspectives: List[PerspectiveResult] = Field(..., description='各视角回答')
    session_id: str = Field(..., description='会话 ID')
    sources: List[KnowledgeChunk] = Field(default_factory=list, description='共享引用来源')
    timestamp: datetime = Field(default_factory=datetime.now, description='响应时间')
    total_duration_ms: float = Field(..., description='总耗时毫秒')
    metadata: Dict[str, Any] = Field(default_factory=dict, description='响应元数据')
