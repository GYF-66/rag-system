# -*- coding: utf-8 -*-
"""
推理引擎模块 - Reasoning-RAG 核心组件
负责记录和生成完整的思考过程
"""
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from models import ThinkingStep, ThinkingProcess


class ReasoningEngine:
    """推理引擎"""

    def __init__(self):
        self.steps = []
        self.start_time = None

    def start(self):
        """开始推理过程"""
        self.start_time = time.time()
        self.steps = []

    def add_step(
        self,
        step_id: int,
        step_name: str,
        description: str,
        reasoning: str,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None
    ):
        """添加推理步骤"""
        step = ThinkingStep(
            step_id=step_id,
            step_name=step_name,
            description=description,
            reasoning=reasoning,
            input_data=input_data,
            output_data=output_data,
            duration_ms=None  # 稍后计算
        )
        self.steps.append(step)

    def end(self, is_cross_query: bool = False, cross_thinking_content: str = None) -> ThinkingProcess:
        """结束推理过程并生成完整思考对象

        Args:
            is_cross_query: 是否为交叉查询
            cross_thinking_content: 交叉推理的 thinking 内容
        """
        if self.start_time is None:
            raise ValueError("推理过程未开始，请先调用 start()")

        total_duration = time.time() - self.start_time
        total_duration_ms = total_duration * 1000

        # 计算每个步骤的耗时
        step_count = len(self.steps)
        if step_count > 0:
            avg_duration = total_duration_ms / step_count
            for step in self.steps:
                step.duration_ms = avg_duration

        # 构建思考过程
        if step_count >= 4:
            # 如果是交叉查询，添加交叉推理内容
            if is_cross_query and cross_thinking_content:
                # 将交叉推理内容添加到最后一个步骤的 reasoning 中
                if self.steps:
                    self.steps[-1].reasoning = cross_thinking_content

            thinking_process = ThinkingProcess(
                query_analysis=self.steps[0],
                retrieval=self.steps[1],
                reranking=self.steps[2],
                reasoning=self.steps[3],
                summary=self._generate_summary(),
                total_duration_ms=total_duration_ms
            )
        else:
            # 如果步骤不足，创建默认步骤
            thinking_process = self._create_default_process(total_duration_ms)

        # 如果是交叉查询，添加 cross_thinking_content 到 summary
        if is_cross_query and cross_thinking_content:
            thinking_process.summary = f"【交叉推理】{cross_thinking_content[:200]}..."

        return thinking_process

    def _generate_summary(self) -> str:
        """生成思考过程总结"""
        if not self.steps:
            return "推理过程未完成"

        summary_parts = []

        # 查询分析总结
        if len(self.steps) > 0:
            summary_parts.append(f"1. 查询分析：{self.steps[0].reasoning[:100]}")

        # 检索总结
        if len(self.steps) > 1:
            output = self.steps[1].output_data or {}
            summary_parts.append(f"2. 检索到 {output.get('retrieved_count', 0)} 个相关文档")

        # 重排序总结
        if len(self.steps) > 2:
            output = self.steps[2].output_data or {}
            summary_parts.append(f"3. 重排序后保留 {output.get('reranked_count', 0)} 个最相关文档")

        # 推理总结
        if len(self.steps) > 3:
            summary_parts.append(f"4. 基于检索结果生成回答")

        return " | ".join(summary_parts)

    def _create_default_process(self, total_duration_ms: float) -> ThinkingProcess:
        """创建默认思考过程（当步骤不足时）"""
        default_step = ThinkingStep(
            step_id=1,
            step_name="默认推理",
            description="默认推理步骤",
            reasoning="推理过程详情未记录",
            duration_ms=total_duration_ms
        )

        return ThinkingProcess(
            query_analysis=default_step,
            retrieval=default_step,
            reranking=default_step,
            reasoning=default_step,
            summary="推理过程未完整记录",
            total_duration_ms=total_duration_ms
        )

    def analyze_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None
    ) -> Tuple[str, Dict]:
        """
        分析查询，提取关键信息和意图

        Args:
            query: 用户查询
            session_history: 会话历史

        Returns:
            (查询分析结果, 分析元数据)
        """
        import jieba
        import re

        # 提取关键词
        keywords = list(jieba.cut(query))
        keywords = [k for k in keywords if len(k) > 1]

        # 识别查询类型
        query_type = self._classify_query_type(query)

        # 识别实体（如奖学金类型、考试类型等）
        entities = self._extract_entities(query)

        # 分析上下文依赖
        context_dependent = self._analyze_context_dependency(query, session_history)

        analysis = {
            'query': query,
            'query_type': query_type,
            'keywords': keywords,
            'entities': entities,
            'context_dependent': context_dependent,
            'has_history': bool(session_history and len(session_history) > 0)
        }

        reasoning = f"识别查询类型为「{query_type}」，提取关键词「{', '.join(keywords[:5])}」"
        if entities:
            reasoning += f"，识别实体「{', '.join(entities)}」"
        if context_dependent:
            reasoning += "，需要结合对话历史上下文"

        return reasoning, analysis

    def _classify_query_type(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()

        # 问候
        greetings = ['你好', '您好', 'hello', 'hi', '嗨']
        if any(g in query_lower for g in greetings):
            return '问候'

        # 帮助
        helps = ['帮助', 'help', '能做什么', '功能']
        if any(h in query_lower for h in helps):
            return '帮助'

        # 奖学金相关
        scholarships = ['奖学金', '助学金', '资助', '补助', '奖励']
        if any(s in query_lower for s in scholarships):
            if '申请' in query_lower or '怎么' in query_lower:
                return '奖学金申请'
            if '条件' in query_lower or '要求' in query_lower:
                return '奖学金条件'
            if '挂科' in query_lower or '不及格' in query_lower:
                return '奖学金与成绩'
            return '奖学金'

        # 考试相关
        if '补考' in query_lower or '不及格' in query_lower:
            return '补考'
        if '重修' in query_lower:
            return '重修'
        if '成绩' in query_lower or '绩点' in query_lower or 'gpa' in query_lower:
            return '成绩查询'
        if '考试' in query_lower:
            return '考试'

        # 纪律相关
        disciplines = ['违纪', '处分', '警告', '记过', '开除']
        if any(d in query_lower for d in disciplines):
            return '违纪处分'

        # 宿舍相关
        accommodations = ['宿舍', '住宿', '寝室', '水电']
        if any(a in query_lower for a in accommodations):
            return '宿舍管理'

        # 默认为通用查询
        return '通用查询'

    def _extract_entities(self, query: str) -> List[str]:
        """提取实体"""
        entities = []

        # 奖学金类型
        scholarship_types = ['国家奖学金', '励志奖学金', '优秀学生奖学金', '助学金']
        for st in scholarship_types:
            if st in query:
                entities.append(st)

        # 考试类型
        exam_types = ['补考', '重修', '期末考试', '期中考试']
        for et in exam_types:
            if et in query:
                entities.append(et)

        # 处分类型
        discipline_types = ['警告', '严重警告', '记过', '留校察看', '开除学籍']
        for dt in discipline_types:
            if dt in query:
                entities.append(dt)

        return entities

    def _analyze_context_dependency(
        self,
        query: str,
        session_history: Optional[List[Dict]]
    ) -> bool:
        """分析查询是否依赖上下文"""
        if not session_history or len(session_history) == 0:
            return False

        # 检查代词
        pronouns = ['它', '这个', '那个', '怎么样', '如何']
        for pronoun in pronouns:
            if pronoun in query:
                return True

        # 检查是否是追问
        follow_up_patterns = ['还有呢', '然后呢', '那', '另外']
        for pattern in follow_up_patterns:
            if pattern in query:
                return True

        return False

    def generate_reasoning(
        self,
        query: str,
        context: str,
        sources: List[Dict],
        analysis: Dict
    ) -> str:
        """
        生成推理过程说明

        Args:
            query: 用户查询
            context: 检索到的上下文
            sources: 检索到的来源
            analysis: 查询分析结果

        Returns:
            推理过程说明
        """
        reasoning_parts = []

        # 查询意图分析
        reasoning_parts.append(f"根据查询「{query}」，识别意图为 {analysis.get('query_type', '通用查询')}")

        # 检索过程
        if sources:
            reasoning_parts.append(f"从知识库检索到 {len(sources)} 个相关文档，经过关键词匹配、章节相关性等特征评估")
        else:
            reasoning_parts.append("知识库未检索到相关文档，将使用通用回答")

        # 上下文整合
        if context:
            reasoning_parts.append("对检索结果进行内容合并和去重，提取关键信息")
        else:
            reasoning_parts.append("无上下文信息，基于常识和规则生成回答")

        # 答案生成策略
        query_type = analysis.get('query_type', '通用查询')
        if query_type in ['奖学金申请', '奖学金条件', '奖学金与成绩']:
            reasoning_parts.append("采用奖学金专用生成策略，重点突出申请条件、流程和注意事项")
        elif query_type in ['补考', '重修', '考试', '成绩查询']:
            reasoning_parts.append("采用考试相关生成策略，重点说明相关规定、流程和补救措施")
        elif query_type == '违纪处分':
            reasoning_parts.append("采用纪律处分生成策略，重点阐述处分类型、认定标准和解除程序")
        else:
            reasoning_parts.append("采用通用生成策略，提取关键句子并组织成自然语言回答")

        return "。".join(reasoning_parts) + "。"

    def merge_context(self, sources: List[Dict]) -> str:
        """
        合并检索到的上下文

        Args:
            sources: 检索到的文档

        Returns:
            合并后的上下文文本
        """
        if not sources:
            return ""

        context_parts = []

        # 按章节分组
        section_groups = {}
        for source in sources:
            section = source.get('section', '')
            if section not in section_groups:
                section_groups[section] = []
            section_groups[section].append(source.get('text', ''))

        # 合并同一章节的内容
        for section, texts in section_groups.items():
            merged_text = '\n\n'.join(texts)
            context_parts.append(merged_text)

        return '\n\n---\n\n'.join(context_parts)


# 全局推理引擎实例
reasoning_engine = ReasoningEngine()