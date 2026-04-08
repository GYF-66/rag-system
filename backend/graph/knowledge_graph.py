# -*- coding: utf-8 -*-
"""
课程知识图谱构建器 — 基于 NetworkX 的 GraphRAG 核心模块

从现有 JSON 知识库中提取实体和关系，构建多层知识图谱：
  培养目标 → 毕业要求 → 课程 → 知识点
  课程之间：先修/后续/共修关系
  知识点之间：依赖/关联关系

参考论文：
  - Microsoft GraphRAG (arXiv:2404.16130)
  - KG-RAG: Knowledge Graph Guided RAG (南京大学&阿里 2025)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# ── 节点类型 ────────────────────────────────────────────────────────────────
NODE_TYPES = {
    'objective': '培养目标',
    'requirement': '毕业要求',
    'indicator': '指标点',
    'course': '课程',
    'concept': '知识点',
    'skill': '能力',
    'experiment': '实验/实践',
}

# ── 边类型 ────────────────────────────────────────────────────────────────
EDGE_TYPES = {
    'supports': '支撑',
    'prerequisite': '先修',
    'leads_to': '后续',
    'contains': '包含',
    'related': '关联',
    'co_required': '共修',
    'maps_to': '映射',
    'bloom_level': 'Bloom层级',
}


class CourseKnowledgeGraph:
    """课程知识图谱 — 基于 NetworkX 的多层有向图"""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self._community_summaries: Dict[int, str] = {}
        self._built = False

    # ── 构建 ────────────────────────────────────────────────────────────

    def build_from_knowledge_base(self, kb_data: Dict[str, Any]) -> None:
        """从 JSON 知识库数据构建知识图谱"""
        metadata = kb_data.get('metadata', {})
        chunks = kb_data.get('chunks', [])
        course_graph = metadata.get('course_graph', {})
        documents = metadata.get('documents', [])

        self.graph.clear()

        # 1. 从 course_graph 构建课程节点和关系
        self._build_course_nodes(course_graph)

        # 2. 从 chunks 提取知识点、实验等细粒度节点
        self._build_concept_nodes(chunks)

        # 3. 从 documents 提取文档层级关系
        self._build_document_relations(documents, course_graph)

        # 4. 推断隐含关系（知识点之间的关联）
        self._infer_concept_relations()

        # 5. 社区检测
        self._detect_communities()

        self._built = True
        logger.info(
            'GraphRAG 知识图谱构建完成: %d 节点, %d 边, %d 社区',
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
            len(self._community_summaries),
        )

    def _build_course_nodes(self, course_graph: Dict[str, Any]) -> None:
        """从 course_graph 构建课程节点和先修/后续边"""
        for doc_id, entry in course_graph.items():
            node_id = f"course:{entry.get('code', doc_id)}"
            self.graph.add_node(
                node_id,
                type='course',
                name=entry.get('name', ''),
                code=entry.get('code', ''),
                semester=entry.get('semester', ''),
                category=entry.get('category', ''),
                credits=entry.get('credits', 0),
                doc_id=doc_id,
                concepts=entry.get('knowledge_concepts', []),
                graduation_requirements=entry.get('graduation_requirements', []),
            )

            # 先修关系
            for prereq_id in entry.get('prerequisites', []):
                prereq_entry = course_graph.get(prereq_id, {})
                prereq_node = f"course:{prereq_entry.get('code', prereq_id)}"
                if prereq_node != node_id:
                    self.graph.add_edge(
                        prereq_node, node_id,
                        type='prerequisite',
                        label='先修',
                    )

            # 后续关系
            for leads_id in entry.get('leads_to', []):
                leads_entry = course_graph.get(leads_id, {})
                leads_node = f"course:{leads_entry.get('code', leads_id)}"
                if leads_node != node_id:
                    self.graph.add_edge(
                        node_id, leads_node,
                        type='leads_to',
                        label='后续',
                    )

            # 知识点节点
            for concept in entry.get('knowledge_concepts', []):
                concept_id = f"concept:{self._normalize_concept(concept)}"
                self.graph.add_node(
                    concept_id,
                    type='concept',
                    name=concept,
                )
                self.graph.add_edge(
                    node_id, concept_id,
                    type='contains',
                    label='包含',
                )

            # 毕业要求映射
            for req in entry.get('graduation_requirements', []):
                req_id = f"requirement:{self._normalize_concept(req)}"
                self.graph.add_node(
                    req_id,
                    type='requirement',
                    name=req,
                )
                self.graph.add_edge(
                    node_id, req_id,
                    type='supports',
                    label='支撑',
                )

    def _build_concept_nodes(self, chunks: List[Dict[str, Any]]) -> None:
        """从知识块中提取更细粒度的知识点关联"""
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            concepts = chunk.get('knowledge_concepts', []) or metadata.get('keywords', [])
            course_code = chunk.get('course_code', '') or metadata.get('course_code', '')
            bloom_level = chunk.get('bloom_level', '') or metadata.get('bloom_level', '')

            if not concepts:
                continue

            course_node = f"course:{course_code}" if course_code else None

            for concept in concepts:
                concept_id = f"concept:{self._normalize_concept(concept)}"
                if not self.graph.has_node(concept_id):
                    self.graph.add_node(
                        concept_id,
                        type='concept',
                        name=concept,
                        bloom_level=bloom_level,
                    )
                elif bloom_level and not self.graph.nodes[concept_id].get('bloom_level'):
                    self.graph.nodes[concept_id]['bloom_level'] = bloom_level

                # 课程-知识点关系
                if course_node and self.graph.has_node(course_node):
                    if not self.graph.has_edge(course_node, concept_id):
                        self.graph.add_edge(
                            course_node, concept_id,
                            type='contains',
                            label='包含',
                        )

    def _build_document_relations(
        self, documents: List[Dict[str, Any]], course_graph: Dict[str, Any]
    ) -> None:
        """从文档元数据推断额外关系"""
        # 相同 category 的课程建立弱关联
        category_courses: Dict[str, List[str]] = defaultdict(list)
        for doc_id, entry in course_graph.items():
            cat = entry.get('category', '')
            if cat:
                node_id = f"course:{entry.get('code', doc_id)}"
                category_courses[cat].append(node_id)

        for cat, courses in category_courses.items():
            for i in range(len(courses)):
                for j in range(i + 1, len(courses)):
                    if not self.graph.has_edge(courses[i], courses[j]):
                        self.graph.add_edge(
                            courses[i], courses[j],
                            type='related',
                            label=f'同类({cat})',
                            weight=0.3,
                        )

    def _infer_concept_relations(self) -> None:
        """推断知识点之间的隐含关联（共现关系）"""
        concept_courses: Dict[str, Set[str]] = defaultdict(set)
        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') == 'course':
                for succ in self.graph.successors(node_id):
                    if self.graph.nodes[succ].get('type') == 'concept':
                        concept_courses[succ].add(node_id)

        # 同一课程下的知识点建立关联
        course_concepts: Dict[str, List[str]] = defaultdict(list)
        for concept, courses in concept_courses.items():
            for course in courses:
                course_concepts[course].append(concept)

        for course, concepts in course_concepts.items():
            for i in range(len(concepts)):
                for j in range(i + 1, min(len(concepts), i + 8)):
                    if not self.graph.has_edge(concepts[i], concepts[j]):
                        self.graph.add_edge(
                            concepts[i], concepts[j],
                            type='related',
                            label='同课关联',
                            weight=0.5,
                        )

    def _detect_communities(self) -> None:
        """基于 Louvain 算法的社区检测"""
        undirected = self.graph.to_undirected()
        if undirected.number_of_nodes() == 0:
            return

        try:
            communities = nx.community.louvain_communities(undirected, seed=42)
        except Exception:
            # fallback: 连通分量作为社区
            communities = list(nx.connected_components(undirected))

        for idx, community in enumerate(communities):
            for node in community:
                self.graph.nodes[node]['community'] = idx

            # 生成社区摘要
            summary = self._generate_community_summary(idx, community)
            self._community_summaries[idx] = summary

    def _generate_community_summary(self, community_id: int, members: set) -> str:
        """为社区生成文本摘要"""
        courses = []
        concepts = []
        requirements = []
        for m in members:
            data = self.graph.nodes.get(m, {})
            ntype = data.get('type', '')
            name = data.get('name', m)
            if ntype == 'course':
                courses.append(name)
            elif ntype == 'concept':
                concepts.append(name)
            elif ntype == 'requirement':
                requirements.append(name)

        parts = [f"[知识社区 {community_id}]"]
        if courses:
            parts.append(f"课程：{'、'.join(courses[:8])}")
        if concepts:
            parts.append(f"核心知识点：{'、'.join(concepts[:10])}")
        if requirements:
            parts.append(f"支撑毕业要求：{'、'.join(requirements[:5])}")
        parts.append(f"节点总数：{len(members)}")
        return '\n'.join(parts)

    # ── 检索接口 ──────────────────────────────────────────────────────────

    def search_subgraph(
        self, query_keywords: List[str], max_hops: int = 2, max_nodes: int = 30,
    ) -> Dict[str, Any]:
        """
        基于查询关键词的子图提取（图谱行走检索）

        1. 定位种子节点（关键词匹配）
        2. 从种子节点扩展 max_hops 跳
        3. 返回子图 + 路径推理说明
        """
        if not self._built:
            return {'nodes': [], 'edges': [], 'summary': '', 'paths': []}

        # 定位种子节点
        seeds = self._locate_seed_nodes(query_keywords)
        if not seeds:
            return {'nodes': [], 'edges': [], 'summary': '', 'paths': []}

        # BFS 扩展子图
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(s, 0) for s in seeds]
        subgraph_nodes: Set[str] = set()

        while queue and len(subgraph_nodes) < max_nodes:
            node, depth = queue.pop(0)
            if node in visited or depth > max_hops:
                continue
            visited.add(node)
            if self.graph.has_node(node):
                subgraph_nodes.add(node)
                if depth < max_hops:
                    for neighbor in list(self.graph.successors(node)) + list(self.graph.predecessors(node)):
                        if neighbor not in visited:
                            queue.append((neighbor, depth + 1))

        # 提取子图的节点和边
        nodes_data = []
        for n in subgraph_nodes:
            data = dict(self.graph.nodes[n])
            data['id'] = n
            data['is_seed'] = n in seeds
            nodes_data.append(data)

        edges_data = []
        for u, v, data in self.graph.edges(data=True):
            if u in subgraph_nodes and v in subgraph_nodes:
                edges_data.append({
                    'source': u,
                    'target': v,
                    **data,
                })

        # 关键路径推理
        paths = self._find_reasoning_paths(seeds, subgraph_nodes)

        # 生成子图摘要
        summary = self._summarize_subgraph(nodes_data, edges_data, paths)

        return {
            'nodes': nodes_data,
            'edges': edges_data,
            'summary': summary,
            'paths': paths,
            'seed_count': len(seeds),
            'total_nodes': len(nodes_data),
            'total_edges': len(edges_data),
        }

    def search_community(self, query_keywords: List[str], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        社区级检索 — 用于全局性提问

        返回与查询最相关的 top_k 个社区及其摘要
        """
        if not self._community_summaries:
            return []

        results = []
        query_text = ' '.join(query_keywords)
        for cid, summary in self._community_summaries.items():
            # 简单关键词匹配评分
            score = sum(1 for kw in query_keywords if kw in summary)
            if score > 0:
                members = [
                    n for n, d in self.graph.nodes(data=True)
                    if d.get('community') == cid
                ]
                results.append({
                    'community_id': cid,
                    'summary': summary,
                    'score': score,
                    'member_count': len(members),
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def get_course_learning_path(self, course_keyword: str) -> Dict[str, Any]:
        """获取课程的完整学习路径（拓扑排序）"""
        target = self._find_course_node(course_keyword)
        if not target:
            return {'path': [], 'description': ''}

        # 向前追溯先修链
        prereq_chain = []
        self._trace_prereqs(target, prereq_chain, visited=set())

        # 向后追踪后续链
        leads_chain = []
        self._trace_leads(target, leads_chain, visited=set())

        path = prereq_chain + [target] + leads_chain
        path_info = []
        for p in path:
            data = self.graph.nodes.get(p, {})
            path_info.append({
                'id': p,
                'name': data.get('name', p),
                'code': data.get('code', ''),
                'semester': data.get('semester', ''),
                'is_target': p == target,
            })

        return {
            'path': path_info,
            'description': self._describe_learning_path(path_info),
        }

    def get_alignment_analysis(self) -> Dict[str, Any]:
        """
        培养方案一致性分析 — 检测知识断层和冗余

        分析维度：
        1. 毕业要求覆盖度：每个毕业要求是否有足够课程支撑
        2. 知识点冗余检测：同一知识点被多门课程重复覆盖
        3. 课程链断裂检测：是否存在缺少先修课的"悬空"课程
        """
        gaps = []       # 断层
        overlaps = []   # 冗余
        orphans = []    # 悬空

        # 1. 毕业要求覆盖分析
        req_coverage: Dict[str, List[str]] = defaultdict(list)
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'requirement':
                supporters = [
                    self.graph.nodes[pred].get('name', pred)
                    for pred in self.graph.predecessors(node)
                    if self.graph.nodes[pred].get('type') == 'course'
                ]
                req_coverage[data.get('name', node)] = supporters
                if len(supporters) < 2:
                    gaps.append({
                        'type': 'requirement_gap',
                        'requirement': data.get('name', node),
                        'supporting_courses': supporters,
                        'severity': 'high' if len(supporters) == 0 else 'medium',
                        'suggestion': f"毕业要求 [{data.get('name', '')}] 仅有 {len(supporters)} 门课程支撑，建议增加支撑课程",
                    })

        # 2. 知识点冗余检测
        concept_courses: Dict[str, List[str]] = defaultdict(list)
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'concept':
                parent_courses = [
                    self.graph.nodes[pred].get('name', pred)
                    for pred in self.graph.predecessors(node)
                    if self.graph.nodes[pred].get('type') == 'course'
                ]
                if len(parent_courses) >= 3:
                    overlaps.append({
                        'type': 'concept_overlap',
                        'concept': data.get('name', node),
                        'courses': parent_courses,
                        'count': len(parent_courses),
                        'suggestion': f"知识点 [{data.get('name', '')}] 在 {len(parent_courses)} 门课程中重复出现，建议差异化教学侧重",
                    })

        # 3. 课程链断裂检测
        for node, data in self.graph.nodes(data=True):
            if data.get('type') != 'course':
                continue
            prereqs = [
                pred for pred in self.graph.predecessors(node)
                if self.graph.edges[pred, node].get('type') == 'prerequisite'
            ]
            has_unknown_prereq = any(not self.graph.has_node(p) for p in prereqs)
            if has_unknown_prereq:
                orphans.append({
                    'type': 'orphan_course',
                    'course': data.get('name', node),
                    'suggestion': f"课程 [{data.get('name', '')}] 存在未定义的先修课程",
                })

        return {
            'total_courses': sum(1 for _, d in self.graph.nodes(data=True) if d.get('type') == 'course'),
            'total_concepts': sum(1 for _, d in self.graph.nodes(data=True) if d.get('type') == 'concept'),
            'total_requirements': sum(1 for _, d in self.graph.nodes(data=True) if d.get('type') == 'requirement'),
            'requirement_coverage': dict(req_coverage),
            'gaps': gaps,
            'overlaps': overlaps,
            'orphans': orphans,
            'gap_count': len(gaps),
            'overlap_count': len(overlaps),
        }

    def get_visualization_data(self) -> Dict[str, Any]:
        """导出完整图谱的可视化数据（前端 D3/vis-network 用）"""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'label': data.get('name', node_id),
                'type': data.get('type', 'unknown'),
                'community': data.get('community', -1),
                **{k: v for k, v in data.items() if k not in ('name', 'type', 'community')},
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                'source': u,
                'target': v,
                'type': data.get('type', 'related'),
                'label': data.get('label', ''),
                'weight': data.get('weight', 1.0),
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'communities': {
                cid: summary for cid, summary in self._community_summaries.items()
            },
            'stats': {
                'node_count': len(nodes),
                'edge_count': len(edges),
                'community_count': len(self._community_summaries),
                'node_types': self._count_by_type(nodes),
            },
        }

    # ── 内部工具 ──────────────────────────────────────────────────────────

    def _locate_seed_nodes(self, keywords: List[str]) -> List[str]:
        """通过关键词定位图谱中的种子节点"""
        seeds = []
        for node_id, data in self.graph.nodes(data=True):
            name = data.get('name', '')
            code = data.get('code', '')
            for kw in keywords:
                if len(kw) < 2:
                    continue
                if kw in name or kw in code or name in kw:
                    seeds.append(node_id)
                    break
        return seeds[:10]  # 限制种子数量

    def _find_course_node(self, keyword: str) -> Optional[str]:
        """查找匹配关键词的课程节点"""
        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') != 'course':
                continue
            name = data.get('name', '')
            code = data.get('code', '')
            if keyword in name or keyword in code or name in keyword:
                return node_id
        return None

    def _trace_prereqs(self, node: str, chain: List[str], visited: Set[str]) -> None:
        """递归追溯先修课程链"""
        if node in visited:
            return
        visited.add(node)
        for pred in self.graph.predecessors(node):
            edge_data = self.graph.edges[pred, node]
            if edge_data.get('type') == 'prerequisite' and self.graph.nodes[pred].get('type') == 'course':
                self._trace_prereqs(pred, chain, visited)
                chain.append(pred)

    def _trace_leads(self, node: str, chain: List[str], visited: Set[str]) -> None:
        """递归追踪后续课程链"""
        if node in visited:
            return
        visited.add(node)
        for succ in self.graph.successors(node):
            edge_data = self.graph.edges[node, succ]
            if edge_data.get('type') == 'leads_to' and self.graph.nodes[succ].get('type') == 'course':
                chain.append(succ)
                self._trace_leads(succ, chain, visited)

    def _find_reasoning_paths(self, seeds: List[str], subgraph_nodes: Set[str]) -> List[Dict]:
        """在子图中找出种子节点之间的推理路径"""
        paths = []
        seed_list = list(seeds)
        for i in range(len(seed_list)):
            for j in range(i + 1, min(len(seed_list), i + 4)):
                try:
                    path = nx.shortest_path(self.graph, seed_list[i], seed_list[j])
                    if all(n in subgraph_nodes for n in path):
                        path_desc = ' → '.join(
                            self.graph.nodes[n].get('name', n) for n in path
                        )
                        paths.append({
                            'from': self.graph.nodes[seed_list[i]].get('name', seed_list[i]),
                            'to': self.graph.nodes[seed_list[j]].get('name', seed_list[j]),
                            'path': path_desc,
                            'length': len(path),
                        })
                except nx.NetworkXNoPath:
                    pass
        return paths

    def _summarize_subgraph(
        self, nodes: List[Dict], edges: List[Dict], paths: List[Dict]
    ) -> str:
        """生成子图的文本摘要"""
        courses = [n['name'] for n in nodes if n.get('type') == 'course']
        concepts = [n['name'] for n in nodes if n.get('type') == 'concept']
        reqs = [n['name'] for n in nodes if n.get('type') == 'requirement']

        parts = ['[图谱检索结果]']
        if courses:
            parts.append(f"涉及课程：{'、'.join(courses[:6])}")
        if concepts:
            parts.append(f"核心知识点：{'、'.join(concepts[:10])}")
        if reqs:
            parts.append(f"关联毕业要求：{'、'.join(reqs[:5])}")
        if paths:
            parts.append('推理路径：')
            for p in paths[:3]:
                parts.append(f"  {p['path']}")
        return '\n'.join(parts)

    def _describe_learning_path(self, path_info: List[Dict]) -> str:
        """描述学习路径"""
        if not path_info:
            return ''
        parts = ['[学习路径推荐]']
        for item in path_info:
            marker = '★' if item.get('is_target') else '→'
            parts.append(
                f"  {marker} {item['name']}({item['code']}) 第{item['semester']}学期"
            )
        return '\n'.join(parts)

    @staticmethod
    def _normalize_concept(text: str) -> str:
        """归一化知识点名称作为节点 ID"""
        return re.sub(r'\s+', '', text.strip().lower())

    @staticmethod
    def _count_by_type(nodes: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for n in nodes:
            counts[n.get('type', 'unknown')] += 1
        return dict(counts)

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()
