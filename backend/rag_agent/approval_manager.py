"""
审批管理器
实现人工审批流程，用于低质量结果或关键操作的确认
"""

from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"       # 低风险：自动通过
    MEDIUM = "medium" # 中风险：异步通知，可继续
    HIGH = "high"     # 高风险：阻塞等待用户确认


@dataclass
class ApprovalRequest:
    """审批请求"""
    action: str              # 操作类型
    context: Dict            # 上下文信息
    risk_level: RiskLevel    # 风险等级
    reason: str              # 需要审批的原因
    auto_approve_after: Optional[int] = None  # 超时自动通过（秒）


@dataclass
class ApprovalResult:
    """审批结果"""
    approved: bool           # 是否通过
    feedback: Optional[str]  # 用户反馈
    auto_approved: bool      # 是否自动通过


class ApprovalManager:
    """
    审批管理器
    
    管理需要人工确认的操作，根据风险等级决定处理方式
    """
    
    def __init__(self, 
                 enabled: bool = True,
                 callback: Optional[Callable] = None):
        """
        初始化审批管理器
        
        Args:
            enabled: 是否启用审批机制
            callback: 审批回调函数（用于异步通知）
        """
        self.enabled = enabled
        self.callback = callback
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        
        logger.info(f"[ApprovalManager] 初始化，启用状态: {enabled}")
    
    def request_approval(self,
                        action: str,
                        context: Dict,
                        risk_level: RiskLevel,
                        reason: str) -> ApprovalResult:
        """
        请求审批
        
        Args:
            action: 操作类型
            context: 上下文信息
            risk_level: 风险等级
            reason: 审批原因
            
        Returns:
            ApprovalResult: 审批结果
        """
        if not self.enabled:
            logger.info(f"[ApprovalManager] 审批已禁用，自动通过: {action}")
            return ApprovalResult(
                approved=True,
                feedback=None,
                auto_approved=True
            )
        
        logger.info(f"[ApprovalManager] 收到审批请求: {action}, 风险等级: {risk_level.value}")
        
        request = ApprovalRequest(
            action=action,
            context=context,
            risk_level=risk_level,
            reason=reason
        )
        
        # 根据风险等级处理
        if risk_level == RiskLevel.LOW:
            return self._auto_approve(request)
        elif risk_level == RiskLevel.MEDIUM:
            return self._async_approve(request)
        else:  # HIGH
            return self._blocking_approve(request)
    
    def _auto_approve(self, request: ApprovalRequest) -> ApprovalResult:
        """
        自动通过（低风险）
        """
        logger.info(f"[ApprovalManager] 低风险操作，自动通过: {request.action}")
        return ApprovalResult(
            approved=True,
            feedback=None,
            auto_approved=True
        )
    
    def _async_approve(self, request: ApprovalRequest) -> ApprovalResult:
        """
        异步通知（中风险）
        
        发送通知但不阻塞，允许操作继续
        """
        logger.info(f"[ApprovalManager] 中风险操作，异步通知: {request.action}")
        
        # 调用回调函数通知用户
        if self.callback:
            try:
                self.callback(request)
            except Exception as e:
                logger.error(f"[ApprovalManager] 回调执行失败: {str(e)}")
        
        # 不阻塞，允许继续
        return ApprovalResult(
            approved=True,
            feedback="已发送通知，操作继续",
            auto_approved=False
        )
    
    def _blocking_approve(self, request: ApprovalRequest) -> ApprovalResult:
        """
        阻塞等待（高风险）
        
        实际应用中应该通过API等待用户响应
        这里简化处理，返回需要确认的标记
        """
        logger.warning(f"[ApprovalManager] 高风险操作，需要用户确认: {request.action}")
        logger.warning(f"[ApprovalManager] 原因: {request.reason}")
        
        # 在实际应用中，这里应该：
        # 1. 将请求存储到pending_approvals
        # 2. 通过WebSocket/轮询等方式通知前端
        # 3. 等待用户响应
        # 4. 返回用户的决定
        
        # 简化实现：返回拒绝，要求用户明确操作
        return ApprovalResult(
            approved=False,
            feedback=f"需要用户确认: {request.reason}",
            auto_approved=False
        )
    
    def check_quality_approval(self, 
                              results: list,
                              quality_score: any,
                              min_results: int = 2,
                              min_quality: float = 0.3) -> ApprovalResult:
        """
        检查结果质量是否需要审批
        
        Args:
            results: 检索结果
            quality_score: 质量评分
            min_results: 最少结果数
            min_quality: 最低质量阈值
            
        Returns:
            ApprovalResult: 审批结果
        """
        # 检查结果数量
        if len(results) < min_results:
            return self.request_approval(
                action="use_low_count_results",
                context={
                    "results_count": len(results),
                    "min_required": min_results
                },
                risk_level=RiskLevel.MEDIUM,
                reason=f"检索结果数量不足（{len(results)}/{min_results}），是否接受？"
            )
        
        # 检查质量分数
        if quality_score.confidence < min_quality:
            return self.request_approval(
                action="use_low_quality_results",
                context={
                    "confidence": quality_score.confidence,
                    "min_required": min_quality,
                    "weakness": quality_score.get_weakness()
                },
                risk_level=RiskLevel.HIGH,
                reason=f"结果质量较低（置信度{quality_score.confidence:.2f}），是否接受？"
            )
        
        # 质量合格，自动通过
        return ApprovalResult(
            approved=True,
            feedback=None,
            auto_approved=True
        )
    
    def check_iteration_approval(self, 
                                 iteration: int,
                                 max_iterations: int) -> ApprovalResult:
        """
        检查迭代次数是否需要审批
        
        Args:
            iteration: 当前迭代次数
            max_iterations: 最大迭代次数
            
        Returns:
            ApprovalResult: 审批结果
        """
        if iteration >= max_iterations:
            return self.request_approval(
                action="continue_iteration",
                context={
                    "current_iteration": iteration,
                    "max_iterations": max_iterations
                },
                risk_level=RiskLevel.MEDIUM,
                reason=f"已达到最大迭代次数（{iteration}/{max_iterations}），是否继续？"
            )
        
        return ApprovalResult(
            approved=True,
            feedback=None,
            auto_approved=True
        )
