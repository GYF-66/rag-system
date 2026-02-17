# -*- coding: utf-8 -*-
"""
AI智能体核心模块
负责生成回复、整合检索结果和管理对话上下文
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import re
import asyncio

from knowledge_base import knowledge_base
from models import KnowledgeChunk
from config import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_DESCRIPTION,
    TOP_K_RESULTS,
    SEARCH_TOP_K,
    MAX_CONTEXT_LENGTH,
    MIN_SIMILARITY
)

# 延迟导入 LLM 服务避免循环依赖
_llm_service = None

def get_llm_service():
    """获取 LLM 服务实例（延迟加载）"""
    global _llm_service
    if _llm_service is None:
        try:
            from llm_service import llm_service
            _llm_service = llm_service
        except ImportError:
            _llm_service = None
    return _llm_service



class StudentManualAgent:
    """学生手册智能问答智能体"""

    def __init__(self):
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.description = AGENT_DESCRIPTION

        # 章节标题模式 - 用于识别章节结构
        self.chapter_patterns = [
            r'第[一二三四五六七八九十]+[编章节]',
            r'第\d+[编章节]',
            r'第[一二三四五六七八九十]+[条]',
            r'第\d+[条]',
            r'安徽信息工程学院[^\n]+（实施）办法',
            r'安徽信息工程学院[^\n]+管理[办法细则条例]',
        ]

    def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True
    ) -> Dict:
        """
        处理用户查询

        Args:
            query: 用户查询
            session_history: 会话历史
            use_rag: 是否使用RAG检索

        Returns:
            包含回复和知识来源的字典
        """
        # 1. 从知识库检索更多信息以进行智能合并
        sources = []
        context = ""

        if use_rag and knowledge_base.is_loaded():
            # 检索更多结果以便合并连续内容
            sources = knowledge_base.search(query, top_k=SEARCH_TOP_K)
            # 合并连续的知识块
            merged_sources = self._merge_continuous_chunks(sources)
            context = self._build_context(merged_sources)
            sources = merged_sources

        # 2. 生成回复
        response = self._generate_response(query, context, session_history, sources)

        return {
            'response': response,
            'sources': sources,
            'context_used': len(sources) > 0
        }

    async def process_query_async(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True,
        use_llm: bool = True
    ) -> Dict:
        """
        异步处理用户查询（支持 LLM）

        Args:
            query: 用户查询
            session_history: 会话历史
            use_rag: 是否使用RAG检索
            use_llm: 是否使用LLM生成回复

        Returns:
            包含回复和知识来源的字典
        """
        # 1. 从知识库检索相关内容
        sources = []
        context = ""

        if use_rag and knowledge_base.is_loaded():
            sources = knowledge_base.search(query, top_k=SEARCH_TOP_K)
            merged_sources = self._merge_continuous_chunks(sources)
            context = self._build_context(merged_sources)
            sources = merged_sources

        # 2. 尝试使用 LLM 生成回复
        response = ""
        used_llm = False

        if use_llm:
            llm = get_llm_service()
            if llm and llm.is_available():
                try:
                    response = await llm.chat(query, context, session_history)
                    if response:
                        used_llm = True
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"LLM 调用失败: {e}")
                    response = ""

        # 3. 如果 LLM 没有返回结果，使用规则回复
        if not response:
            response = self._generate_response(query, context, session_history, sources)

        return {
            'response': response,
            'sources': sources,
            'context_used': len(sources) > 0,
            'used_llm': used_llm
        }

    def _merge_continuous_chunks(self, sources: List[Dict]) -> List[Dict]:
        """
        合并连续的知识块，提取完整信息
        智能过滤掉碎片化的内容（深度优化）
        """
        if not sources:
            return []

        # 按相似度排序
        sorted_sources = sorted(sources, key=lambda x: x.get('similarity', 0), reverse=True)

        # 第一步：深度清理和过滤（包含相似度过滤）
        cleaned_sources = []
        for source in sorted_sources:
            # 【关键】过滤低于相似度阈值的结果
            similarity = source.get('similarity', 0)
            if similarity < MIN_SIMILARITY:
                continue
                
            text = source.get('text', '')
            if not text:
                continue

            # 深度清理碎片
            cleaned_text = self._deep_clean_text(text)

            # 严格过滤
            if not self._is_valid_content(cleaned_text):
                continue

            cleaned_sources.append({
                'id': source.get('id', ''),
                'text': cleaned_text,
                'char_count': len(cleaned_text),
                'similarity': source.get('similarity', 0),
                'section': self._extract_section_title(cleaned_text)
            })

        # 第二步：智能合并连续内容
        merged = []
        buffer_texts = []  # 存储待合并的文本
        buffer_id = None
        buffer_sim = 0
        buffer_section = ''  # 当前缓冲区的章节

        for source in cleaned_sources:
            text = source['text']
            section = source.get('section', '')

            # 如果是新章节标题，先输出当前buffer
            if section and section != buffer_section:
                if buffer_texts and len(''.join(buffer_texts)) > 200:
                    merged_content = ''.join(buffer_texts)
                    merged.append({
                        'id': buffer_id,
                        'text': merged_content,
                        'char_count': len(merged_content),
                        'similarity': buffer_sim,
                        'section': buffer_section
                    })
                buffer_texts = []
                buffer_id = source['id']
                buffer_sim = source['similarity']
                buffer_section = section

            buffer_texts.append(text)
            if not buffer_id:
                buffer_id = source['id']
                buffer_sim = source['similarity']
            if not buffer_section:
                buffer_section = section

            # 检查是否是完整的段落
            if text.rstrip().endswith(('。', '！', '？', '\n')):
                full_text = ''.join(buffer_texts)
                if len(full_text) > 150 and self._is_valid_content(full_text):
                    merged.append({
                        'id': buffer_id,
                        'text': full_text,
                        'char_count': len(full_text),
                        'similarity': buffer_sim,
                        'section': buffer_section
                    })
                buffer_texts = []
                buffer_id = None
                buffer_sim = 0
                buffer_section = ''

        # 处理剩余buffer
        if buffer_texts and len(''.join(buffer_texts)) > 200:
            merged_content = ''.join(buffer_texts)
            merged.append({
                'id': buffer_id,
                'text': merged_content,
                'char_count': len(merged_content),
                'similarity': buffer_sim,
                'section': buffer_section
            })

        # 第三步：智能去重
        unique_merged = []
        seen_fingerprints = set()

        for item in merged:
            text = item['text']
            # 使用更精确的指纹（前200个中文字符 + 关键词）
            fingerprint = self._get_content_fingerprint(text)
            if fingerprint and fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                unique_merged.append(item)

        return unique_merged[:TOP_K_RESULTS]

    def _deep_clean_text(self, text: str) -> str:
        """深度清理文本碎片"""
        # 分行处理
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 跳过纯噪音行
            if self._is_noise_line(line):
                continue

            # 清理行首碎片
            line = self._clean_line_prefix(line)

            if line:
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines)

        # 全局清理
        result = re.sub(r'\n{3,}', '\n\n', result)  # 合并多余空行
        result = re.sub(r'[，。！？]{2,}', lambda m: m.group(0)[0], result)  # 合并重复标点
        result = result.strip()

        return result

    def _is_noise_line(self, line: str) -> bool:
        """判断是否为噪音行"""
        # 纯页码、行号
        if re.match(r'^[\d\s\.\,\-\uff0c\u3001]*$', line):
            return True

        # 省略号
        if re.match(r'^[\.\s\u2026\u22EF\uff0e]+$', line):
            return True

        # 目录项（省略号结尾）
        if line.endswith('......................') and len(line) < 100:
            return True

        # 碎片模式：数字开头+非中文内容+很短
        if re.match(r'^\d+[\.\、\uff0c]\s*[^\u4e00-\u9fff]{0,40}$', line):
            return True

        # "行，"开头且很短
        if re.match(r'^行\s*[\uff0c\u3002]+\s*[^\u4e00-\u9fff]{0,20}$', line):
            return True

        # 英文/数字开头且中文很少
        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', line))
        if re.match(r'^[a-zA-Z0-9]+', line) and chinese_count < 5 and len(line) < 50:
            return True

        return False

    def _clean_line_prefix(self, line: str) -> str:
        """清理行首碎片前缀"""
        # 移除各种碎片前缀
        patterns_to_remove = [
            r'^\s*\d+[\.\、\uff0c]\s*[^\u4e00-\u9fff]{0,50}',  # "1. 行，若上级要求"
            r'^\s*\d+\.\d+\s*[^\u4e00-\u9fff]{0,30}',  # "1.0、四级 1.5"
            r'^\s*行\s*[\uff0c\u3002]+\s*',  # "行，"
            r'^\s*级\s*[^\u4e00-\u9fff]{0,20}',  # "级考试"
            r'^\s*[，。、\uff0c\u3001\uff1b\uff1a]+\s*',  # 标点开头
        ]

        for pattern in patterns_to_remove:
            line = re.sub(pattern, '', line)

        return line.strip()

    def _is_valid_content(self, text: str) -> bool:
        """判断内容是否有效"""
        if not text or len(text) < 100:
            return False

        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_count < 20:
            return False

        # 检查是否以碎片模式开头
        fragment_patterns = [
            r'^[\s\d]*[\.、行级]+[^\u4e00-\u9fff]*\s*[^\u4e00-\u9fff]{10,}',
            r'^\d+\.\d+\s*[^\u4e00-\u9fff]{10,}',
            r'^行\s*[\uff0c\u3002]+\s*[^\u4e00-\u9fff]{10,}',
        ]
        for pattern in fragment_patterns:
            if re.match(pattern, text.strip()):
                return False

        # 检查内容密度
        unique_chars = len(set(text))
        if unique_chars < len(text) * 0.25:
            return False

        return True

    def _get_content_fingerprint(self, text: str) -> str:
        """获取内容指纹用于去重"""
        # 提取前200个中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        chinese_part = ''.join(chinese_chars[:200])

        # 提取关键词（2-4个字且重复出现）
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        word_freq = {}
        for word in words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1

        # 取出现频率最高的3个关键词
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        keywords = ''.join([k[0] for k in top_keywords])

        return chinese_part + keywords

    def _extract_section_title(self, text: str) -> str:
        """从文本中提取章节标题"""
        for pattern in self.chapter_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        # 尝试提取以"安徽信息工程学院"开头的标题
        if text.startswith('安徽信息工程学院'):
            lines = text.split('\n')
            for line in lines[:3]:
                if '（实施）办法' in line or '管理' in line:
                    return line[:50]

        return ''

    def _remove_fragment_prefix(self, text: str) -> str:
        """移除碎片前缀（如"1. 行，"）"""
        # 移除类似"1. 行，"、"2. 级考试"这样的碎片前缀
        text = re.sub(r'^[\s\d]*(?:[\.、行级]+[^\u4e00-\u9fff]*)+\s*', '', text)
        return text.strip()

    def _is_valid_meaningful_text(self, text: str) -> bool:
        """严格判断文本是否有意义"""
        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))

        # 中文内容太少
        if chinese_count < 20:
            return False

        # 文本长度不合理
        if len(text) < 100 or len(text) > 3000:
            return False

        # 不应该只是重复的内容
        unique_chars = len(set(text))
        if unique_chars < len(text) * 0.3:
            return False

        # 检查是否以明显的碎片模式开头
        fragment_starts = [
            r'^\d+\s*[\.\、]\s*[^，。！？]{0,20}[，。]',
            r'^行\s*[，，]\s*[^，。]{0,20}',
            r'^级\s*[^，。]{0,30}[，。]',
            r'^[\da-zA-Z]+\s*[\.、，]\s*[^，。\u4e00-\u9fff]{10,}',
        ]
        for pattern in fragment_starts:
            if re.match(pattern, text.strip()):
                return False

        return True

    def _clean_fragments(self, text: str) -> str:
        """清理文本碎片，移除明显不完整的内容"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()

            # 跳过空行
            if not line_stripped:
                continue

            # 跳过纯数字或标点开头的短行
            if len(line_stripped) < 50 and re.match(r'^[\d\s\.\,\-\uff0c\u3001]+$', line_stripped):
                continue

            # 跳过省略号行
            if re.match(r'^[\.\s\u2026\u22EF\uff0e]+$', line_stripped):
                continue

            # 清理行首的数字列表残留（如"1. 行，"）
            # 匹配：数字+标点+非中文字符（最多20个）
            line_stripped = re.sub(r'^\s*\d+[\.\、\uff0c]\s*[^\u4e00-\u9fff]{0,30}', '', line_stripped)

            # 移除行首的标点符号残留
            line_stripped = re.sub(r'^\s*[\uff0c\u3002\u3001\uff1b\uff1a]+\s*', '', line_stripped)

            # 移除"行，"这样的碎片
            line_stripped = re.sub(r'^\s*行\s*[\uff0c\u3002]+\s*', '', line_stripped)

            if line_stripped:
                cleaned_lines.append(line_stripped)

        return '\n'.join(cleaned_lines)

    def _extract_main_content(self, text: str) -> str:
        """提取主要内容，移除列表项前缀等"""
        # 移除中文数字或阿拉伯数字开头的列表项
        text = re.sub(r'^[\s\u3000]*[一二三四五六七八九十]+\s*[、.]\s*', '', text)
        text = re.sub(r'^[\s\u3000]*\d+\s*[、.]\s*', '', text)
        return text.strip()

    def _is_fragment_pattern(self, text: str) -> bool:
        """判断是否为碎片模式"""
        patterns = [
            r'^[\s\u3000]*\d+[\.\、]\s*[^\u4e00-\u9fff]{0,30}$',  # "1. 行，"
            r'^[\s\u3000]*[，。]\s*\S{0,30}$',  # 标点开头且很短
            r'^[\s\u3000]*[a-zA-Z0-9]+\s*[^\u4e00-\u9fff]{0,50}$',  # 英文数字开头且中文很少
            r'^[\s\u3000]*级\s*\S{0,20}$',  # "级考试"开头且很短
        ]
        return any(re.match(p, text) for p in patterns)

    def _is_meaningful_text(self, text: str) -> bool:
        """判断文本是否有意义（已弃用，使用 _is_valid_meaningful_text）"""
        return self._is_valid_meaningful_text(text)

    def _is_metadata_or_noise(self, text: str) -> bool:
        """
        判断是否为元数据或噪音内容（目录、页码、分隔符等）
        """
        text_stripped = text.strip()

        # 检查是否为章节标题（以"第"开头的短文本）
        if re.match(r'^第[一二三四五六七八九十]+[编章节条]', text_stripped) and len(text_stripped) < 20:
            return True

        # 检查是否为纯页码或行号
        if re.match(r'^[\d\s\.\,\-\uff0c\u3001]*$', text_stripped):
            return True

        # 检查是否为省略号或分隔符
        if re.match(r'^[\.\s\u2026\u22EF\uff0e]+$', text_stripped):
            return True

        # 检查是否为目录项（以省略号结尾的标题）
        if text_stripped.endswith('......................') and '。' not in text_stripped:
            return True

        # 检查是否包含大量页码引用但没有实际内容
        if re.search(r'第\d+页|page\s*\d+|\.\.\.\d+', text_stripped):
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text_stripped))
            if chinese_count < len(text_stripped) * 0.3:
                return True

        # 检查是否为编号列表的开头但没有内容
        if re.match(r'^[\s\u3000]*[\d\-]+[\.、\uff0c]?.*$', text_stripped) and len(text_stripped) < 100:
            return True

        return False

    def _get_chinese_fingerprint(self, text: str, length: int = 80) -> str:
        """获取中文指纹用于去重"""
        # 提取指定数量的中文字符作为指纹
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return ''.join(chinese_chars[:length])

    def _extract_section_info(self, text: str) -> Tuple[str, str]:
        """从文本中提取章节和页码信息"""
        # 尝试提取章节信息（如"第一章"、"第一条"等）
        section_pattern = r'(?:第[一二三四五六七八九十]+[编章节条])|(?:第\d+[条节])'
        sections = re.findall(section_pattern, text)
        section = sections[0] if sections else ""

        # 尝试提取页码信息（如"第8页"、"page 8"等）
        page_pattern = r'(?:第?\d+\s*页)|(?:p\.\s*\d+)'
        pages = re.findall(page_pattern, text)
        page = pages[0] if pages else ""

        return section, page

    def _build_context(self, sources: List[Dict]) -> str:
        """构建上下文，包含来源信息（使用章节信息）"""
        if not sources:
            return ""

        context_parts = []
        for i, source in enumerate(sources):
            text = source.get('text', '')
            section = source.get('section', '')

            # 使用章节信息作为来源标注
            source_info = f"\n\n——来源{i+1}"
            if section:
                source_info += f"《{section[:30]}》"  # 限制章节标题长度
            else:
                # 尝试从文本中提取章节
                extracted_section = self._extract_section_title(text)
                if extracted_section:
                    source_info += f"《{extracted_section[:30]}》"
                else:
                    source_info += " 学生手册"

            context_parts.append(text + source_info)

        return "\n\n".join(context_parts)

    def _generate_response(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]],
        sources: List[Dict]
    ) -> str:
        """生成AI回复"""

        # 简单的问答生成逻辑（实际生产中可以使用大语言模型）
        if not sources or not context:
            return self._generate_fallback_response(query)

        # 根据查询类型分类
        query_type = self._classify_query(query)

        if query_type == 'greeting':
            return self._generate_greeting_response()
        elif query_type == 'help':
            return self._generate_help_response()
        elif query_type == 'scholarship':
            return self._generate_scholarship_response(query, sources)
        elif query_type == 'scholarship_application':
            return self._generate_scholarship_application_response(sources)
        elif query_type == 'scholarship_condition':
            return self._generate_scholarship_condition_response(sources)
        elif query_type == 'scholarship_grade':
            return self._generate_scholarship_grade_response(sources)
        elif query_type == 'exam':
            return self._generate_general_exam_response(sources)
        elif query_type == 'exam_makeup':
            return self._generate_makeup_exam_response(sources)
        elif query_type == 'exam_retake':
            return self._generate_retake_exam_response(sources)
        elif query_type == 'exam_grade':
            return self._generate_grade_response(sources)
        elif query_type == 'discipline':
            return self._generate_discipline_response(query, sources)
        elif query_type == 'accommodation':
            return self._generate_accommodation_response(query, sources)
        elif query_type == 'general':
            return self._generate_general_response(query, sources)
        else:
            return self._generate_fallback_response(query)

    def _classify_query(self, query: str) -> str:
        """精细分类用户查询（包含细分类型）"""
        query_lower = query.lower()

        # 问候
        greetings = ['你好', '您好', 'hello', 'hi', '嗨']
        if any(g in query_lower for g in greetings):
            return 'greeting'

        # 帮助
        helps = ['帮助', 'help', '能做什么', '功能']
        if any(h in query_lower for h in helps):
            return 'help'

        # 奖学金 - 细分：申请流程、申请条件、评选标准、挂科影响
        scholarships = ['奖学金', '助学金', '资助', '补助', '奖励']
        if any(s in query_lower for s in scholarships):
            if '申请' in query_lower or '怎么' in query_lower:
                return 'scholarship_application'
            if '条件' in query_lower or '要求' in query_lower:
                return 'scholarship_condition'
            if '挂科' in query_lower or '不及格' in query_lower:
                return 'scholarship_grade'
            return 'scholarship'

        # 考试 - 细分：补考、重修、成绩、绩点
        if '补考' in query_lower or '不及格' in query_lower:
            return 'exam_makeup'
        if '重修' in query_lower:
            return 'exam_retake'
        if '成绩' in query_lower or '绩点' in query_lower or 'gpa' in query_lower:
            return 'exam_grade'
        exams = ['考试', '测验']
        if any(e in query_lower for e in exams):
            return 'exam'

        # 纪律
        disciplines = ['违纪', '处分', '警告', '记过', '开除']
        if any(d in query_lower for d in disciplines):
            return 'discipline'

        # 宿舍
        accommodations = ['宿舍', '住宿', '寝室', '水电']
        if any(a in query_lower for a in accommodations):
            return 'accommodation'

        return 'general'

    def _generate_greeting_response(self) -> str:
        """生成问候回复"""
        return f"""您好！我是{self.name}，很高兴为您服务！

我可以帮您解答关于学生手册的各种问题，比如：
- 学籍管理（转专业、延期毕业、学籍预警等）
- 奖学金和助学金的申请条件和流程
- 考试相关规定（补考、重修、绩点计算等）
- 违纪处分的认定和解除
- 宿舍管理和生活服务指南

请直接告诉我你想了解的问题，我会根据《学生手册2024版》为你查找相关信息！"""

    def _generate_help_response(self) -> str:
        """生成帮助回复"""
        return f"""我是{self.name}，基于《学生手册2024版》为您提供服务！

我可以帮你解答：

📚 学习与成绩
转专业、延期毕业、学分认定、毕业论文等

💰 奖助学金
国家奖学金、励志奖学金、优秀学生奖学金、助学金等

📝 考试事项
考试纪律、补考政策、重修申请、成绩查询等

⚖️ 纪律处分
违纪行为、处分种类、处分解除程序等

🏠 生活服务
宿舍管理、一卡通使用、报修系统等

想知道什么就尽管问吧！"""

    def _generate_scholarship_response(self, query: str, sources: List[Dict]) -> str:
        """生成奖学金通用回复"""
        return self._generate_scholarship_application_response(sources)

    def _generate_scholarship_application_response(self, sources: List[Dict]) -> str:
        """生成奖学金申请流程回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于奖学金申请流程的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        # 智能提取和整理信息
        response_parts = []

        # 检索到的内容分类
        conditions = []
        procedures = []
        types = []

        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')

            # 分类提取信息
            if any(k in text for k in ['条件', '要求', '标准', '符合']):
                conditions.append({'text': text, 'section': section})
            elif any(k in text for k in ['申请', '评定', '流程', '程序', '步骤']):
                procedures.append({'text': text, 'section': section})
            elif any(k in text for k in ['奖学金', '助学金', '奖励']):
                if len(types) < 2:
                    types.append({'text': text, 'section': section})

        # 构建自然对话式回复
        if conditions or procedures or types:
            response_parts.append("根据学生手册，关于奖学金申请的相关信息如下：")

            # 如果有条件信息
            if conditions:
                response_parts.append("\n**申请条件**")
                for item in conditions[:2]:
                    # 提取关键句子
                    sentences = self._extract_key_sentences(item['text'], 3)
                    for sent in sentences:
                        response_parts.append(f"\n• {sent}")
                    if item['section']:
                        response_parts.append(f"\n  （来源：{item['section']}）")

            # 如果有流程信息
            if procedures:
                response_parts.append("\n**申请流程**")
                for item in procedures[:2]:
                    sentences = self._extract_key_sentences(item['text'], 3)
                    for sent in sentences:
                        response_parts.append(f"\n• {sent}")
                    if item['section']:
                        response_parts.append(f"\n  （来源：{item['section']}）")

            # 如果有类型信息
            if types:
                response_parts.append("\n**奖学金类型**")
                for item in types[:1]:
                    sentences = self._extract_key_sentences(item['text'], 2)
                    for sent in sentences:
                        response_parts.append(f"\n• {sent}")

            # 添加实用建议
            response_parts.append("\n\n**实用建议**")
            response_parts.append("\n• 不同奖学金的申请时间和要求可能不同，请关注学校通知")
            response_parts.append("\n• 建议提前准备相关证明材料（成绩单、获奖证书等）")
            response_parts.append("\n• 有疑问可以咨询辅导员或学生工作处")

        else:
            # 没有分类信息，直接展示最相关的内容
            response_parts.append("根据学生手册，相关信息如下：")
            for i, source in enumerate(sources[:2], 1):
                text = source.get('text', '')
                section = source.get('section', '')
                sentences = self._extract_key_sentences(text, 4)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if section:
                    response_parts.append(f"\n  （来源{i}：{section}）")

        return '\n'.join(response_parts)

    def _extract_key_sentences(self, text: str, max_sentences: int = 3) -> List[str]:
        """从文本中提取关键句子"""
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？\n]', text)

        # 过滤和清理
        key_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            # 过滤掉太短的句子
            if len(sent) < 10:
                continue

            # 过滤掉目录项
            if '......................' in sent:
                continue

            # 过滤掉页码行
            if re.match(r'^[\d\s\.\-\uff0c\u3001]*$', sent):
                continue

            key_sentences.append(sent)
            if len(key_sentences) >= max_sentences:
                break

        return key_sentences

    def _build_source_tag(self, index: int, section: str = "", page: str = "") -> str:
        """构建来源标注"""
        parts = [f"\n\n——来源{index}"]
        if section:
            parts.append(f"《{section}》")
        if page:
            parts.append(f"{page}")
        if not section and not page:
            parts.append("学生手册")
        return "".join(parts)

    def _generate_scholarship_condition_response(self, sources: List[Dict]) -> str:
        """生成奖学金申请条件回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于奖学金申请条件的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于奖学金申请条件，根据学生手册的相关规定：")

        # 提取条件相关内容
        conditions = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')
            if any(keyword in text for keyword in ['条件', '要求', '标准', '符合', '满足']):
                if len(conditions) < 3:
                    conditions.append({'text': text, 'section': section})

        if conditions:
            response_parts.append("\n**主要申请条件**")
            for i, item in enumerate(conditions, 1):
                sentences = self._extract_key_sentences(item['text'], 3)
                if sentences:
                    response_parts.append(f"\n• {sentences[0]}")
                    for sent in sentences[1:]:
                        response_parts.append(f"  {sent}")
                    if item['section']:
                        response_parts.append(f"  （来源：{item['section']}）")
        else:
            # 没有明确的条件信息，展示最相关的内容
            for i, source in enumerate(sources[:2], 1):
                text = source.get('text', '')
                section = source.get('section', '')
                sentences = self._extract_key_sentences(text, 3)
                if sentences:
                    response_parts.append(f"\n**来源{i}：{section if section else '学生手册'}**")
                    for sent in sentences:
                        response_parts.append(f"\n• {sent}")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 不同类型的奖学金（国家奖学金、励志奖学金、优秀学生奖学金等）有不同的申请条件")
        response_parts.append("\n• 建议先了解各类奖学金的具体要求，根据自己的成绩和综合素质情况选择最适合的类型")
        response_parts.append("\n• 家庭经济困难的同学可以重点关注国家助学金和励志奖学金")

        return '\n'.join(response_parts)

    def _generate_scholarship_grade_response(self, sources: List[Dict]) -> str:
        """生成挂科与奖学金关系回复（更智能、更自然）"""
        if not sources:
            return "关于挂科对奖学金的影响，建议您咨询辅导员或查看《学生手册2024版》中关于奖学金评定的具体规定。"

        response_parts = []
        response_parts.append("关于挂科对奖学金申请的影响，我帮你查了一下：")

        # 分析检索到的内容
        has_grade_requirements = False
        has_fail_effect = False
        requirements_text = []
        effects_text = []

        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')

            # 查找成绩要求相关信息
            if any(k in text for k in ['智育成绩', '综合测评', '班级前', '排名', '绩点']):
                if not has_grade_requirements:
                    sentences = self._extract_key_sentences(text, 3)
                    requirements_text.extend(sentences)
                    has_grade_requirements = True

            # 查找挂科影响相关信息
            if any(k in text for k in ['不及格', '挂科', '补考', '重修']):
                if not has_fail_effect:
                    sentences = self._extract_key_sentences(text, 3)
                    effects_text.extend(sentences)
                    has_fail_effect = True

        # 构建回复
        if has_grade_requirements:
            response_parts.append("\n\n**奖学金申请通常需要满足以下条件：**")
            for req in requirements_text[:3]:
                response_parts.append(f"\n• {req}")

        if has_fail_effect:
            response_parts.append("\n\n**关于挂科的影响：**")
            for effect in effects_text[:3]:
                response_parts.append(f"\n• {effect}")
        else:
            # 如果没有找到明确的挂科影响信息，给出一般性说明
            response_parts.append("\n\n**关于挂科的影响：**")
            response_parts.append("\n• 挂科（不及格）会直接影响你的智育成绩和综合测评排名")
            response_parts.append("\n• 大部分奖学金都要求成绩排名在班级前50%左右")
            response_parts.append("\n• 建议通过补考或重修来改善成绩")

        # 添加实用建议
        response_parts.append("\n\n**给你的建议：**")
        response_parts.append("\n1. **优先处理挂科课程**：关注补考时间，认真准备补考")
        response_parts.append("\n2. **了解重修政策**：如果补考仍不及格，需要申请重修")
        response_parts.append("\n3. **提升综合素质**：参加课外活动、竞赛等提升综合素质分")
        response_parts.append("\n4. **关注下学期机会**：即使这学期不能申请，下学期还有机会")
        response_parts.append("\n5. **咨询辅导员**：了解具体的奖学金评定细则和补救措施")

        response_parts.append("\n\n加油！挂科不是终点，及时调整心态，努力改善成绩就好。")

        return '\n'.join(response_parts)

    def _generate_exam_response(self, query: str, sources: List[Dict]) -> str:
        """生成考试相关回复"""
        # 判断是关于补考、重修还是一般考试
        query_lower = query.lower()

        if '补考' in query_lower or '不及格' in query_lower:
            return self._generate_makeup_exam_response(sources)
        elif '重修' in query_lower:
            return self._generate_retake_exam_response(sources)
        elif '成绩' in query_lower or '绩点' in query_lower:
            return self._generate_grade_response(sources)
        else:
            return self._generate_general_exam_response(sources)

    def _generate_makeup_exam_response(self, sources: List[Dict]) -> str:
        """生成补考相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于补考的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于补考的规定，我帮您整理了以下信息：")

        # 提取补考相关内容
        makeup_info = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')
            if '补考' in text and len(makeup_info) < 3:
                makeup_info.append({'text': text, 'section': section})

        if makeup_info:
            response_parts.append("\n**补考规定**")
            for item in makeup_info:
                sentences = self._extract_key_sentences(item['text'], 3)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if item['section']:
                    response_parts.append(f"  （来源：{item['section']}）")
        else:
            response_parts.append("\n• 每门课程仅有一次补考机会，补考不及格者应申请重修")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 补考时间通常在下学期开学初，请留意学校通知")
        response_parts.append("\n• 补考成绩如实记载，即使通过也不如正考成绩理想")
        response_parts.append("\n• 补考仍不及格的课程必须重修")
        response_parts.append("\n• 建议认真准备补考，争取一次通过")

        return '\n'.join(response_parts)

    def _generate_retake_exam_response(self, sources: List[Dict]) -> str:
        """生成重修相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于课程重修的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于课程重修，根据学生手册的相关规定：")

        # 提取重修相关内容
        retake_info = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')
            if '重修' in text and len(retake_info) < 3:
                retake_info.append({'text': text, 'section': section})

        if retake_info:
            response_parts.append("\n**重修规定**")
            for item in retake_info:
                sentences = self._extract_key_sentences(item['text'], 3)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if item['section']:
                    response_parts.append(f"  （来源：{item['section']}）")
        else:
            response_parts.append("\n• 补考不及格的课程应申请重修，重修课程的考核成绩按实际成绩记载")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 重修需要重新修读该课程并参加考核")
        response_parts.append("\n• 重修成绩按实际成绩记载，不会标注'重修'字样")
        response_parts.append("\n• 重修课程不给予补考机会")
        response_parts.append("\n• 建议合理安排重修课程，避免影响其他课程学习")

        return '\n'.join(response_parts)

    def _generate_grade_response(self, sources: List[Dict]) -> str:
        """生成成绩和绩点相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于成绩计算和绩点的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于成绩计算和绩点，根据学生手册的相关规定：")

        # 分类提取信息
        gpa_info = []
        grade_info = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')

            if '绩点' in text or 'GPA' in text or '学分绩点' in text:
                if len(gpa_info) < 2:
                    gpa_info.append({'text': text, 'section': section})
            elif '成绩' in text and len(grade_info) < 2:
                grade_info.append({'text': text, 'section': section})

        if gpa_info:
            response_parts.append("\n**绩点计算**")
            for item in gpa_info:
                sentences = self._extract_key_sentences(item['text'], 3)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if item['section']:
                    response_parts.append(f"  （来源：{item['section']}）")

        if grade_info:
            response_parts.append("\n**成绩记载**")
            for item in grade_info[:1]:
                sentences = self._extract_key_sentences(item['text'], 2)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 平均学分绩点(GPA)=Σ每门课程的学分绩点/Σ每门课程学分")
        response_parts.append("\n• 每门课程的成绩绩点=(该课程成绩-50)/10")
        response_parts.append("\n• 保持良好的绩点对奖学金申请、保研、就业都有帮助")

        return '\n'.join(response_parts)

    def _generate_general_exam_response(self, sources: List[Dict]) -> str:
        """生成一般考试相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于考试规定的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于考试的相关规定，我帮您整理了以下信息：")

        for i, source in enumerate(sources[:3], 1):
            text = source.get('text', '')
            section = source.get('section', '')
            sentences = self._extract_key_sentences(text, 3)
            if sentences:
                response_parts.append(f"\n**来源{i}：{section if section else '学生手册'}**")
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 请务必遵守考试纪律，诚信应考")
        response_parts.append("\n• 如有考试不及格，注意补考时间安排")
        response_parts.append("\n• 考试违纪或作弊将受到纪律处分")

        return '\n'.join(response_parts)

    def _generate_discipline_response(self, query: str, sources: List[Dict]) -> str:
        """生成纪律处分相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于违纪处分的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于违纪处分，根据学生手册的相关规定：")

        # 分类提取信息
        discipline_types = []
        discipline_procedures = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')

            if any(k in text for k in ['警告', '记过', '留校察看', '开除', '处分种类']):
                if len(discipline_types) < 2:
                    discipline_types.append({'text': text, 'section': section})
            elif any(k in text for k in ['程序', '流程', '申诉', '解除']):
                if len(discipline_procedures) < 2:
                    discipline_procedures.append({'text': text, 'section': section})

        if discipline_types:
            response_parts.append("\n**处分种类**")
            for item in discipline_types:
                sentences = self._extract_key_sentences(item['text'], 3)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if item['section']:
                    response_parts.append(f"  （来源：{item['section']}）")

        if discipline_procedures:
            response_parts.append("\n**处分程序**")
            for item in discipline_procedures:
                sentences = self._extract_key_sentences(item['text'], 2)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 请务必遵守校规校纪，避免违纪行为")
        response_parts.append("\n• 如有违纪行为，将面临相应的纪律处分")
        response_parts.append("\n• 处分种类包括警告、严重警告、记过、留校察看、开除学籍等")
        response_parts.append("\n• 如有疑问可咨询学生工作处")

        return '\n'.join(response_parts)

    def _generate_accommodation_response(self, query: str, sources: List[Dict]) -> str:
        """生成宿舍管理相关回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到关于宿舍管理的具体信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("关于宿舍管理，根据学生手册的相关规定：")

        # 分类提取信息
        dorm_rules = []
        dorm_services = []
        for source in sources:
            text = source.get('text', '')
            section = source.get('section', '')

            if any(k in text for k in ['规定', '禁止', '要求', '纪律', '安全']):
                if len(dorm_rules) < 2:
                    dorm_rules.append({'text': text, 'section': section})
            elif any(k in text for k in ['报修', '服务', '管理', '中心']):
                if len(dorm_services) < 2:
                    dorm_services.append({'text': text, 'section': section})

        if dorm_rules:
            response_parts.append("\n**宿舍管理规定**")
            for item in dorm_rules:
                sentences = self._extract_key_sentences(item['text'], 3)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")
                if item['section']:
                    response_parts.append(f"  （来源：{item['section']}）")

        if dorm_services:
            response_parts.append("\n**宿舍服务**")
            for item in dorm_services:
                sentences = self._extract_key_sentences(item['text'], 2)
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")

        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 请遵守宿舍管理规定，保持宿舍卫生")
        response_parts.append("\n• 如有宿舍问题（如报修、更换宿舍等），请联系宿管中心")
        response_parts.append("\n• 可以使用网上报修系统快速提交维修申请")

        return '\n'.join(response_parts)

    def _generate_general_response(self, query: str, sources: List[Dict]) -> str:
        """生成通用回复（更智能、更自然）"""
        if not sources:
            return "抱歉，我没有找到相关信息。建议您咨询辅导员或查看《学生手册2024版》的完整内容。"

        response_parts = []
        response_parts.append("根据学生手册，我找到了以下相关信息：")

        # 提取关键信息并展示
        for i, source in enumerate(sources[:3], 1):
            text = source.get('text', '')
            section = source.get('section', '')

            # 提取关键句子
            sentences = self._extract_key_sentences(text, 4)
            if sentences:
                response_parts.append(f"\n**来源{i}：{section if section else '学生手册'}**")
                for sent in sentences:
                    response_parts.append(f"\n• {sent}")

        # 添加实用建议
        response_parts.append("\n\n**温馨提示**")
        response_parts.append("\n• 如需了解更多详细信息，建议查阅《学生手册2024版》完整内容")
        response_parts.append("\n• 也可以咨询相关部门（学生处、教务处、辅导员等）获取更准确的解答")

        return '\n'.join(response_parts)

    def _generate_fallback_response(self, query: str) -> str:
        """生成兜底回复"""
        return f"""抱歉，我在《学生手册2024版》中没有找到与"{query}"直接相关的信息。

这可能是因为：
1. 该问题可能不在学生手册范围内
2. 问题表述可能需要更具体一些

您可以尝试：
• 换个方式描述你的问题
• 提供更多相关的背景信息
• 直接咨询相关部门（学生处、教务处、辅导员等）

如果你有其他关于学生手册的问题，很乐意继续为你解答！"""


# 全局智能体实例
agent = StudentManualAgent()