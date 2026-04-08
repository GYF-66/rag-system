"""
思考过程可视化
提供Agent决策过程的可视化和详细解释
"""

from typing import List, Dict, Any
from dataclasses import asdict
import json
import logging

logger = logging.getLogger(__name__)


class ThinkingVisualizer:
    """
    思考过程可视化器
    
    将Agent的迭代过程转换为易于理解的可视化输出
    """
    
    @staticmethod
    def format_iteration(record: Any, verbose: bool = True) -> str:
        """
        格式化单次迭代记录
        
        Args:
            record: IterationRecord实例
            verbose: 是否输出详细信息
            
        Returns:
            格式化的文本
        """
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"迭代 #{record.iteration} - {record.timestamp.strftime('%H:%M:%S')}")
        lines.append(f"{'='*60}")
        
        # 查询分析
        lines.append(f"\n【思考阶段 - Think】")
        lines.append(f"  查询类型: {record.analysis.query_type}")
        lines.append(f"  复杂度: {record.analysis.complexity}")
        lines.append(f"  用户意图: {record.analysis.intent}")
        lines.append(f"  关键词: {', '.join(record.analysis.keywords[:5])}")
        if verbose:
            lines.append(f"  需要上下文: {'是' if record.analysis.requires_context else '否'}")
        
        # 策略选择
        lines.append(f"\n【决策阶段 - Decide】")
        lines.append(f"  选择策略: {record.strategy}")
        lines.append(f"  使用工具: {record.tool_used}")
        lines.append(f"  决策依据: {record.decision}")
        
        # 执行结果
        lines.append(f"\n【执行阶段 - Act】")
        lines.append(f"  检索结果数: {record.results_count}")
        
        # 质量评估
        lines.append(f"\n【观察阶段 - Observe】")
        quality = record.quality_score
        lines.append(f"  相似度: {quality.similarity:.2%} {'✓' if quality.similarity >= 0.6 else '✗'}")
        lines.append(f"  覆盖度: {quality.coverage:.2%} {'✓' if quality.coverage >= 0.5 else '✗'}")
        lines.append(f"  多样性: {quality.diversity:.2%} {'✓' if quality.diversity >= 0.4 else '✗'}")
        lines.append(f"  完整性: {quality.completeness:.2%} {'✓' if quality.completeness >= 0.5 else '✗'}")
        lines.append(f"  综合置信度: {quality.confidence:.2%} {'✓✓' if quality.confidence >= 0.7 else '✓' if quality.confidence >= 0.5 else '✗'}")
        lines.append(f"  主要弱点: {quality.get_weakness()}")
        
        # 查询改进
        if record.refined_query:
            lines.append(f"\n【查询改进】")
            lines.append(f"  改进后查询: {record.refined_query}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_thinking_process(records: List[Any], 
                                include_summary: bool = True) -> str:
        """
        格式化完整的思考过程
        
        Args:
            records: IterationRecord列表
            include_summary: 是否包含摘要
            
        Returns:
            格式化的文本
        """
        lines = []
        lines.append("\n" + "="*60)
        lines.append("Agent 思考过程可视化")
        lines.append("="*60)
        
        # 格式化每次迭代
        for record in records:
            lines.append(ThinkingVisualizer.format_iteration(record, verbose=False))
        
        # 添加摘要
        if include_summary and records:
            lines.append(ThinkingVisualizer._generate_summary(records))
        
        return '\n'.join(lines)
    
    @staticmethod
    def _generate_summary(records: List[Any]) -> str:
        """
        生成思考过程摘要
        
        Args:
            records: IterationRecord列表
            
        Returns:
            摘要文本
        """
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append("思考过程摘要")
        lines.append(f"{'='*60}")
        
        # 基本统计
        total_iterations = len(records)
        strategies_used = [r.strategy for r in records]
        final_quality = records[-1].quality_score if records else None
        
        lines.append(f"\n总迭代次数: {total_iterations}")
        lines.append(f"使用的策略: {' → '.join(strategies_used)}")
        
        # 质量演变
        lines.append(f"\n质量演变:")
        for i, record in enumerate(records, 1):
            q = record.quality_score
            bar = '█' * int(q.confidence * 20)
            lines.append(f"  迭代{i}: {bar} {q.confidence:.2%}")
        
        # 最终质量
        if final_quality:
            lines.append(f"\n最终质量评估:")
            lines.append(f"  综合置信度: {final_quality.confidence:.2%}")
            lines.append(f"  是否达标: {'✓ 是' if final_quality.is_sufficient(0.7) else '✗ 否'}")
        
        # 改进建议
        if records and not final_quality.is_sufficient(0.7):
            lines.append(f"\n改进建议:")
            weakness = final_quality.get_weakness()
            suggestions = {
                'similarity': '建议使用更精确的关键词或尝试语义相似的表达',
                'coverage': '建议扩展查询范围或使用更多关键词',
                'diversity': '建议调整检索策略以获取更多样化的结果',
                'completeness': '建议增加检索结果数量或降低过滤阈值'
            }
            lines.append(f"  - {suggestions.get(weakness, '建议重新表述查询')}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_json(records: List[Any], pretty: bool = True) -> str:
        """
        将思考过程转换为JSON格式
        
        Args:
            records: IterationRecord列表
            pretty: 是否美化输出
            
        Returns:
            JSON字符串
        """
        data = []
        for record in records:
            # 转换为字典
            record_dict = {
                'iteration': record.iteration,
                'timestamp': record.timestamp.isoformat(),
                'analysis': {
                    'query_type': record.analysis.query_type,
                    'complexity': record.analysis.complexity,
                    'intent': record.analysis.intent,
                    'keywords': record.analysis.keywords,
                    'requires_context': record.analysis.requires_context
                },
                'strategy': record.strategy,
                'tool_used': record.tool_used,
                'results_count': record.results_count,
                'quality_score': {
                    'similarity': record.quality_score.similarity,
                    'coverage': record.quality_score.coverage,
                    'diversity': record.quality_score.diversity,
                    'completeness': record.quality_score.completeness,
                    'confidence': record.quality_score.confidence,
                    'weakness': record.quality_score.get_weakness()
                },
                'decision': record.decision,
                'refined_query': record.refined_query
            }
            data.append(record_dict)
        
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def to_html(records: List[Any]) -> str:
        """
        将思考过程转换为HTML格式
        
        Args:
            records: IterationRecord列表
            
        Returns:
            HTML字符串
        """
        html_parts = []
        html_parts.append("""
        <div class="thinking-process" style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto;">
            <h2 style="color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px;">
                Agent 思考过程
            </h2>
        """)
        
        for record in records:
            quality = record.quality_score
            
            # 质量颜色
            if quality.confidence >= 0.7:
                quality_color = "#4CAF50"  # 绿色
            elif quality.confidence >= 0.5:
                quality_color = "#FF9800"  # 橙色
            else:
                quality_color = "#F44336"  # 红色
            
            html_parts.append(f"""
            <div class="iteration" style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; background: #f9f9f9;">
                <h3 style="color: #555; margin-top: 0;">
                    迭代 #{record.iteration} 
                    <span style="float: right; font-size: 0.8em; color: #888;">
                        {record.timestamp.strftime('%H:%M:%S')}
                    </span>
                </h3>
                
                <div class="phase" style="margin: 10px 0;">
                    <strong style="color: #2196F3;">🤔 Think:</strong> 
                    {record.analysis.query_type} | {record.analysis.complexity} | {record.analysis.intent}
                </div>
                
                <div class="phase" style="margin: 10px 0;">
                    <strong style="color: #9C27B0;">🎯 Decide:</strong> 
                    {record.strategy} ({record.decision})
                </div>
                
                <div class="phase" style="margin: 10px 0;">
                    <strong style="color: #FF5722;">⚡ Act:</strong> 
                    检索到 {record.results_count} 个结果
                </div>
                
                <div class="phase" style="margin: 10px 0;">
                    <strong style="color: #4CAF50;">👁 Observe:</strong>
                    <div style="margin-left: 20px; margin-top: 5px;">
                        <div style="margin: 3px 0;">
                            相似度: <span style="color: {quality_color};">{quality.similarity:.1%}</span>
                        </div>
                        <div style="margin: 3px 0;">
                            覆盖度: <span style="color: {quality_color};">{quality.coverage:.1%}</span>
                        </div>
                        <div style="margin: 3px 0;">
                            多样性: <span style="color: {quality_color};">{quality.diversity:.1%}</span>
                        </div>
                        <div style="margin: 3px 0;">
                            完整性: <span style="color: {quality_color};">{quality.completeness:.1%}</span>
                        </div>
                        <div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;">
                            <strong>综合置信度:</strong> 
                            <span style="color: {quality_color}; font-size: 1.2em; font-weight: bold;">
                                {quality.confidence:.1%}
                            </span>
                        </div>
                    </div>
                </div>
                
                {f'<div class="refinement" style="margin: 10px 0; padding: 10px; background: #fff3cd; border-radius: 4px;"><strong>🔄 查询改进:</strong> {record.refined_query}</div>' if record.refined_query else ''}
            </div>
            """)
        
        html_parts.append("</div>")
        
        return ''.join(html_parts)
    
    @staticmethod
    def create_decision_tree(records: List[Any]) -> str:
        """
        创建决策树的ASCII艺术表示
        
        Args:
            records: IterationRecord列表
            
        Returns:
            ASCII决策树
        """
        lines = []
        lines.append("\n决策树:")
        lines.append("┌─ 开始")
        
        for i, record in enumerate(records):
            is_last = (i == len(records) - 1)
            prefix = "└─" if is_last else "├─"
            continuation = "  " if is_last else "│ "
            
            quality = record.quality_score
            status = "✓" if quality.is_sufficient(0.7) else "→"
            
            lines.append(f"{prefix} 迭代{record.iteration} [{status}]")
            lines.append(f"{continuation}  ├─ Think: {record.analysis.query_type}")
            lines.append(f"{continuation}  ├─ Decide: {record.strategy}")
            lines.append(f"{continuation}  ├─ Act: {record.results_count}个结果")
            lines.append(f"{continuation}  └─ Observe: 置信度{quality.confidence:.1%}")
            
            if record.refined_query and not is_last:
                lines.append(f"{continuation}     └─ 改进查询")
        
        lines.append("└─ 结束")
        
        return '\n'.join(lines)


class DecisionExplainer:
    """
    决策解释器
    
    提供Agent决策的详细解释
    """
    
    @staticmethod
    def explain_strategy_selection(analysis: Any, strategy: str) -> str:
        """
        解释策略选择的原因
        
        Args:
            analysis: QueryAnalysis实例
            strategy: 选择的策略
            
        Returns:
            解释文本
        """
        explanations = {
            'hybrid_search': f"选择混合检索是因为查询类型为'{analysis.query_type}'，需要平衡语义理解和精确匹配",
            'vector_search': f"选择向量检索是因为查询复杂度为'{analysis.complexity}'，更适合语义理解",
            'keyword_search': f"选择关键词检索是因为查询包含明确的关键词，适合精确匹配",
            'reranker': "使用重排序工具对初排结果进行精细化排序，提高相关性"
        }
        
        return explanations.get(strategy, f"选择{strategy}策略")
    
    @staticmethod
    def explain_quality_score(quality: Any) -> Dict[str, str]:
        """
        解释质量评分
        
        Args:
            quality: QualityScore实例
            
        Returns:
            解释字典
        """
        explanations = {}
        
        # 相似度
        if quality.similarity >= 0.8:
            explanations['similarity'] = "相似度很高，结果与查询高度相关"
        elif quality.similarity >= 0.6:
            explanations['similarity'] = "相似度良好，结果基本相关"
        else:
            explanations['similarity'] = "相似度较低，可能需要改进查询"
        
        # 覆盖度
        if quality.coverage >= 0.7:
            explanations['coverage'] = "覆盖度很好，结果全面覆盖了查询要点"
        elif quality.coverage >= 0.5:
            explanations['coverage'] = "覆盖度一般，部分查询要点被覆盖"
        else:
            explanations['coverage'] = "覆盖度不足，建议扩展查询范围"
        
        # 多样性
        if quality.diversity >= 0.6:
            explanations['diversity'] = "结果多样性好，提供了不同角度的信息"
        elif quality.diversity >= 0.4:
            explanations['diversity'] = "结果多样性一般"
        else:
            explanations['diversity'] = "结果重复度较高，缺乏多样性"
        
        # 完整性
        if quality.completeness >= 0.7:
            explanations['completeness'] = "结果完整性好，信息充分"
        elif quality.completeness >= 0.5:
            explanations['completeness'] = "结果完整性一般"
        else:
            explanations['completeness'] = "结果不够完整，信息量不足"
        
        # 综合
        if quality.confidence >= 0.7:
            explanations['overall'] = "综合质量达标，可以直接使用"
        elif quality.confidence >= 0.5:
            explanations['overall'] = "综合质量一般，建议进一步改进"
        else:
            explanations['overall'] = "综合质量不足，需要重新检索"
        
        return explanations
