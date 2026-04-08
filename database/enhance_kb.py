# -*- coding: utf-8 -*-
"""
知识库元数据增强脚本
为现有 rag_knowledge_base.json 添加：
1. education_level (macro/meso/micro) 三层分类
2. 课程关联关系 (prerequisites, leads_to)
3. 修正 chunk_type 误标
4. 修复 metadata.section_path_text 从顶层 section 同步
5. 添加 bloom_level 认知层级
"""
import json
import re
import shutil
from pathlib import Path

DB_PATH = Path(__file__).parent / 'rag_knowledge_base.json'

# ── 课程元数据 ──────────────────────────────────────────
# 主目录课程（人工智能专业核心）
COURSE_META = {
    'cse203面向对象java': {
        'code': 'CSE203', 'name': '面向对象Java', 'semester': 2,
        'prerequisites': [],
        'leads_to': ['cse308-计算机系统基础', 'cse320-数据库原理与应用-教案', 'cse319-数据处理与分析-python-教案-胡婷婷'],
        'knowledge_concepts': ['Java语言', '面向对象编程', '类与对象', '继承多态', '异常处理'],
        'mapped_objectives': ['毕业要求3', '毕业要求5'],
    },
    'cse205-计算思维导论': {
        'code': 'CSE205', 'name': '计算思维导论', 'semester': 1,
        'prerequisites': [],
        'leads_to': ['cse203面向对象java'],
        'knowledge_concepts': ['计算思维', '算法基础', '程序设计', '问题求解', '抽象与分解'],
        'mapped_objectives': ['毕业要求1', '毕业要求3'],
    },
    'cse303-操作系统原理': {
        'code': 'CSE303', 'name': '操作系统原理', 'semester': 4,
        'prerequisites': ['cse308-计算机系统基础'],
        'leads_to': [],
        'knowledge_concepts': ['进程管理', '内存管理', '文件系统', '设备管理', 'CPU调度', '死锁', '虚拟存储器'],
        'mapped_objectives': ['毕业要求2', '毕业要求3', '毕业要求5'],
    },
    'cse308-计算机系统基础': {
        'code': 'CSE308', 'name': '计算机系统基础', 'semester': 3,
        'prerequisites': ['cse203面向对象java'],
        'leads_to': ['cse303-操作系统原理'],
        'knowledge_concepts': ['计算机体系结构', '指令系统', '存储层次', '汇编语言', '数据表示'],
        'mapped_objectives': ['毕业要求1', '毕业要求3'],
    },
    'cse318-机器学习基础-教案-2024新': {
        'code': 'CSE318', 'name': '机器学习基础', 'semester': 5,
        'prerequisites': ['cse319-数据处理与分析-python-教案-胡婷婷'],
        'leads_to': ['cse324-神经网络与深度学习-教案', 'cse434-计算机视觉应用开发基础', 'cse322-模式识别'],
        'knowledge_concepts': ['监督学习', '分类', '回归', '贝叶斯', 'SVM', '决策树', '集成学习', 'AdaBoost', 'K近邻'],
        'mapped_objectives': ['毕业要求1', '毕业要求2', '毕业要求4'],
    },
    'cse319-数据处理与分析-python-教案-胡婷婷': {
        'code': 'CSE319', 'name': '数据处理与分析(Python)', 'semester': 4,
        'prerequisites': ['cse203面向对象java'],
        'leads_to': ['cse318-机器学习基础-教案-2024新'],
        'knowledge_concepts': ['Python', '数据清洗', 'Pandas', 'NumPy', '数据可视化', '统计分析'],
        'mapped_objectives': ['毕业要求3', '毕业要求5'],
    },
    'cse320-数据库原理与应用-教案': {
        'code': 'CSE320', 'name': '数据库原理与应用', 'semester': 4,
        'prerequisites': ['cse203面向对象java'],
        'leads_to': [],
        'knowledge_concepts': ['关系模型', 'SQL', '数据库设计', '规范化', '事务管理', 'ER模型'],
        'mapped_objectives': ['毕业要求3', '毕业要求5'],
    },
    'cse322-模式识别': {
        'code': 'CSE322', 'name': '模式识别', 'semester': 6,
        'prerequisites': ['cse318-机器学习基础-教案-2024新'],
        'leads_to': ['cse434-计算机视觉应用开发基础'],
        'knowledge_concepts': ['特征提取', '分类器设计', '聚类分析', '贝叶斯决策', '统计模式识别'],
        'mapped_objectives': ['毕业要求1', '毕业要求2', '毕业要求4'],
    },
    'cse324-神经网络与深度学习-教案': {
        'code': 'CSE324', 'name': '神经网络与深度学习', 'semester': 6,
        'prerequisites': ['cse318-机器学习基础-教案-2024新'],
        'leads_to': ['cse434-计算机视觉应用开发基础'],
        'knowledge_concepts': ['神经网络', '反向传播', 'CNN', 'RNN', '深度学习框架', '梯度下降'],
        'mapped_objectives': ['毕业要求1', '毕业要求2', '毕业要求4'],
    },
    'cse434-计算机视觉应用开发基础': {
        'code': 'CSE434', 'name': '计算机视觉应用开发基础', 'semester': 7,
        'prerequisites': ['cse324-神经网络与深度学习-教案', 'cse318-机器学习基础-教案-2024新'],
        'leads_to': [],
        'knowledge_concepts': ['图像处理', '目标检测', '图像分类', 'OpenCV', '卷积神经网络', '特征提取'],
        'mapped_objectives': ['毕业要求2', '毕业要求4', '毕业要求5'],
    },
    'cse435-教案': {
        'code': 'CSE435', 'name': '自然语言处理', 'semester': 6,
        'prerequisites': ['cse318-机器学习基础-教案-2024新', 'cse324-神经网络与深度学习-教案'],
        'leads_to': [],
        'knowledge_concepts': ['NLP', '文本分类', '词向量', '序列标注', '语言模型', '注意力机制'],
        'mapped_objectives': ['毕业要求1', '毕业要求2', '毕业要求4'],
    },
    'cse436教案': {
        'code': 'CSE436', 'name': '智能系统综合实践', 'semester': 7,
        'prerequisites': ['cse434-计算机视觉应用开发基础', 'cse435-教案'],
        'leads_to': [],
        'knowledge_concepts': ['AI系统集成', '项目开发', '系统设计', '模型部署', '性能优化'],
        'mapped_objectives': ['毕业要求3', '毕业要求4', '毕业要求5'],
    },
    # 大数据专业核心课程（选取有明确先修/后续关系的）
    '4-cse2709人工智能导论': {
        'code': 'CSE2709', 'name': '人工智能导论', 'semester': 3,
        'prerequisites': [],
        'leads_to': ['37-cse3003-机器学习基础-教学大纲-3-27修改版'],
        'knowledge_concepts': ['人工智能概论', '搜索算法', '知识表示', '推理', '智能体'],
        'mapped_objectives': ['毕业要求1'],
    },
    '37-cse3003-机器学习基础-教学大纲-3-27修改版': {
        'code': 'CSE3003', 'name': '机器学习基础(大数据)', 'semester': 5,
        'prerequisites': ['10-mth2008-应用统计与r语言建模-大纲-大数据-智科'],
        'leads_to': ['56-cse3705-神经网络与深度学习', '42-cse3505-数据挖掘与应用-教学大纲'],
        'knowledge_concepts': ['监督学习', '无监督学习', '回归', '分类', '聚类', '特征工程'],
        'mapped_objectives': ['毕业要求1', '毕业要求2'],
    },
    '56-cse3705-神经网络与深度学习': {
        'code': 'CSE3705', 'name': '神经网络与深度学习(大数据)', 'semester': 6,
        'prerequisites': ['37-cse3003-机器学习基础-教学大纲-3-27修改版'],
        'leads_to': ['52-cse3701-图像处理基础与计算机视觉-课程教学大纲2-0', '53-cse3702-自然语言处理技术与应用-教学大纲'],
        'knowledge_concepts': ['深度神经网络', 'CNN', 'RNN', 'LSTM', '生成模型'],
        'mapped_objectives': ['毕业要求1', '毕业要求2', '毕业要求4'],
    },
    '36-cse3009-大数据技术原理与应用-教学大纲': {
        'code': 'CSE3009', 'name': '大数据技术原理与应用', 'semester': 5,
        'prerequisites': ['15-cse3005-python程序设计-大数据'],
        'leads_to': ['46-cse3509-spark与集群技术-教学大纲', '49-cse3512-大数据系统开发与应用-教学大纲'],
        'knowledge_concepts': ['Hadoop', 'MapReduce', 'HDFS', 'HBase', '分布式计算'],
        'mapped_objectives': ['毕业要求2', '毕业要求3', '毕业要求5'],
    },
    '15-cse3005-python程序设计-大数据': {
        'code': 'CSE3005', 'name': 'Python程序设计(大数据)', 'semester': 3,
        'prerequisites': [],
        'leads_to': ['20-cse3007-网络爬虫技术-教学大纲0414', '36-cse3009-大数据技术原理与应用-教学大纲', '29-cse3503-数据预处理技术-教学大纲'],
        'knowledge_concepts': ['Python语言', '数据类型', '函数', '面向对象', '文件操作'],
        'mapped_objectives': ['毕业要求3', '毕业要求5'],
    },
    '10-mth2008-应用统计与r语言建模-大纲-大数据-智科': {
        'code': 'MTH2008', 'name': '应用统计与R语言建模', 'semester': 4,
        'prerequisites': [],
        'leads_to': ['37-cse3003-机器学习基础-教学大纲-3-27修改版', '42-cse3505-数据挖掘与应用-教学大纲'],
        'knowledge_concepts': ['统计分析', 'R语言', '概率分布', '假设检验', '回归分析'],
        'mapped_objectives': ['毕业要求1', '毕业要求3'],
    },
    '42-cse3505-数据挖掘与应用-教学大纲': {
        'code': 'CSE3505', 'name': '数据挖掘与应用', 'semester': 6,
        'prerequisites': ['37-cse3003-机器学习基础-教学大纲-3-27修改版'],
        'leads_to': ['43-cse3506-行业大数据分析与应用-教学大纲'],
        'knowledge_concepts': ['关联规则', '聚类', '分类', '预测', '文本挖掘'],
        'mapped_objectives': ['毕业要求2', '毕业要求4'],
    },
    '52-cse3701-图像处理基础与计算机视觉-课程教学大纲2-0': {
        'code': 'CSE3701', 'name': '图像处理基础与计算机视觉', 'semester': 6,
        'prerequisites': ['56-cse3705-神经网络与深度学习'],
        'leads_to': [],
        'knowledge_concepts': ['图像处理', '边缘检测', '目标检测', '图像分割', 'OpenCV'],
        'mapped_objectives': ['毕业要求2', '毕业要求4'],
    },
    '53-cse3702-自然语言处理技术与应用-教学大纲': {
        'code': 'CSE3702', 'name': '自然语言处理技术与应用', 'semester': 6,
        'prerequisites': ['56-cse3705-神经网络与深度学习'],
        'leads_to': [],
        'knowledge_concepts': ['NLP', '分词', '命名实体识别', '文本分类', '情感分析'],
        'mapped_objectives': ['毕业要求2', '毕业要求4'],
    },
    '46-cse3509-spark与集群技术-教学大纲': {
        'code': 'CSE3509', 'name': 'Spark与集群技术', 'semester': 6,
        'prerequisites': ['36-cse3009-大数据技术原理与应用-教学大纲'],
        'leads_to': ['48-cse3511-spark内存计算与应用-教学大纲'],
        'knowledge_concepts': ['Spark', 'RDD', 'SparkSQL', 'Streaming', '集群技术'],
        'mapped_objectives': ['毕业要求3', '毕业要求5'],
    },
}

# ── 布鲁姆认知层级关键词 ──────────────────────────────────
BLOOM_KEYWORDS = {
    '记忆': ['了解', '知道', '识别', '列举', '描述', '定义'],
    '理解': ['理解', '解释', '说明', '概括', '区分', '比较'],
    '应用': ['应用', '使用', '实现', '运用', '操作', '实践', '编程', '代码'],
    '分析': ['分析', '推理', '诊断', '区别', '检查', '对比', '评估'],
    '评价': ['评价', '判断', '论证', '优化', '改进'],
    '创造': ['设计', '构建', '创新', '规划', '综合', '开发'],
}


def infer_bloom_level(text: str) -> str:
    """根据文本中的动词推断布鲁姆认知层级"""
    scores = {}
    for level, keywords in BLOOM_KEYWORDS.items():
        scores[level] = sum(1 for kw in keywords if kw in text)
    if not any(scores.values()):
        return '理解'
    return max(scores, key=scores.get)


def infer_education_level(chunk: dict) -> str:
    """推断教育层级: macro(培养目标) / meso(课程大纲) / micro(教学实施)"""
    doc_kind = chunk.get('chunk_type', '') or chunk.get('metadata', {}).get('document_kind', '')
    section = chunk.get('section', '').lower()

    if doc_kind == 'program_spec':
        return 'macro'

    # 课程教案的第一个 chunk（通常是教学大纲概要）
    if '教学目的' in section or '课程目标' in section or '教学目标' in section:
        return 'meso'

    # 判断是否为具体教学实施内容
    text = chunk.get('text', '')
    if any(kw in text[:100] for kw in ['教学目的', '教学重点', '课程目标', '教学大纲']):
        return 'meso'

    if doc_kind == 'course_outline':
        return 'micro'

    return 'micro'


def fix_chunk_type(chunk: dict) -> str:
    """修正 chunk_type：从文档类型推断，而非依赖可能错误的标记"""
    doc_id = chunk.get('document_id', '')
    title = chunk.get('title', '')
    # 培养方案类文档
    if '培养方案' in doc_id or '培养方案' in title:
        return 'program_spec'
    if doc_id in COURSE_META:
        return 'course_outline'
    # 已有正确标记且不是 general 的保留
    existing = chunk.get('chunk_type', 'general')
    if existing in ('program_spec', 'course_outline'):
        return existing
    return 'course_outline'


def fix_section_path(chunk: dict) -> None:
    """从顶层 section 同步到 metadata.section_path_text"""
    section = chunk.get('section', '')
    if section and chunk.get('metadata'):
        parts = [p.strip() for p in section.split('>')]
        chunk['metadata']['section_path'] = parts
        chunk['metadata']['section_path_text'] = ' > '.join(parts)


def enhance():
    data = json.loads(DB_PATH.read_text(encoding='utf-8'))

    # 备份
    backup = DB_PATH.with_suffix('.json.pre_enhance_backup')
    if not backup.exists():
        shutil.copy2(DB_PATH, backup)
        print(f'[OK] Backup: {backup.name}')

    # 1. 在 metadata 顶层添加课程关联图
    data['metadata']['course_graph'] = {}
    for doc_id, meta in COURSE_META.items():
        data['metadata']['course_graph'][doc_id] = {
            'code': meta['code'],
            'name': meta['name'],
            'semester': meta['semester'],
            'prerequisites': meta['prerequisites'],
            'leads_to': meta['leads_to'],
            'knowledge_concepts': meta['knowledge_concepts'],
            'mapped_objectives': meta['mapped_objectives'],
        }

    # 2. 增强每个 chunk
    stats = {'type_fixed': 0, 'level_added': 0, 'bloom_added': 0, 'path_fixed': 0}

    for chunk in data['chunks']:
        doc_id = chunk.get('document_id', '')

        # 修正 chunk_type
        old_type = chunk.get('chunk_type', '')
        new_type = fix_chunk_type(chunk)
        if old_type != new_type:
            chunk['chunk_type'] = new_type
            if chunk.get('metadata'):
                chunk['metadata']['chunk_type'] = new_type
            stats['type_fixed'] += 1

        # 添加 education_level
        level = infer_education_level(chunk)
        chunk['education_level'] = level
        if chunk.get('metadata'):
            chunk['metadata']['education_level'] = level
        stats['level_added'] += 1

        # 添加 bloom_level
        bloom = infer_bloom_level(chunk.get('text', ''))
        chunk['bloom_level'] = bloom
        if chunk.get('metadata'):
            chunk['metadata']['bloom_level'] = bloom
        stats['bloom_added'] += 1

        # 修复 section_path
        fix_section_path(chunk)
        stats['path_fixed'] += 1

        # 添加课程元数据引用
        if doc_id in COURSE_META:
            meta = COURSE_META[doc_id]
            chunk['course_code'] = meta['code']
            chunk['knowledge_concepts'] = meta['knowledge_concepts']
            chunk['mapped_objectives'] = meta['mapped_objectives']
            chunk['semester'] = meta['semester']

    # 3. 更新版本号
    data['metadata']['version'] = '4.0'
    data['metadata']['enhancements'] = [
        'education_level (macro/meso/micro)',
        'bloom_level',
        'course_graph with prerequisites/leads_to (AI + Big Data majors)',
        'knowledge_concepts per chunk',
        'mapped_objectives per chunk',
        'fixed chunk_type and section_path',
    ]

    # 写回
    DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n[OK] Enhanced {len(data["chunks"])} chunks')
    print(f'  - chunk_type fixed: {stats["type_fixed"]}')
    print(f'  - education_level added: {stats["level_added"]}')
    print(f'  - bloom_level added: {stats["bloom_added"]}')
    print(f'  - section_path fixed: {stats["path_fixed"]}')
    print(f'  - course_graph entries: {len(COURSE_META)}')
    print(f'\n[OK] Version: 3.1 → 4.0')


if __name__ == '__main__':
    enhance()
