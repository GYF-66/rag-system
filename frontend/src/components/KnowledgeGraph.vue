<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { apiClient } from '@/services/api';
import type { AlignmentAnalysis, GraphEdge, GraphNode, GraphSearchResult, GraphVisualizationData } from '@/types';

type WorkspaceState = {
  nodeCount: number;
  edgeCount: number;
  communityCount: number;
  filterLabel: string;
  activeTab: 'graph' | 'alignment';
  activeTabLabel: string;
};

type CourseRelationKind = 'prerequisite' | 'next' | 'related';

type CourseRelationCard = {
  id: string;
  course: GraphNode;
  kind: CourseRelationKind;
  title: string;
  explanation: string;
};

type CourseLaneGroup = {
  key: string;
  title: string;
  kind: 'lane' | 'belt';
  x: number;
  y: number;
  width: number;
  height: number;
};

type FocusedCourseGraph = {
  center: GraphNode;
  prerequisites: GraphNode[];
  nextCourses: GraphNode[];
  relatedCourses: GraphNode[];
  detailNodes: GraphNode[];
  relationCards: CourseRelationCard[];
  laneGroups: CourseLaneGroup[];
  edges: GraphEdge[];
  matchedKnowledge: string[];
};

type RenderNode = {
  key: string;
  node: GraphNode;
  x: number;
  y: number;
  width: number;
  height: number;
  lane: string;
  emphasis: 'center' | 'course' | 'detail';
};

type RenderEdge = {
  key: string;
  path: string;
  color: string;
  kind: CourseRelationKind | 'detail';
};

const emit = defineEmits<{ (event: 'state-change', payload: WorkspaceState): void }>();

const VIEWBOX_WIDTH = 1440;
const VIEWBOX_HEIGHT = 860;
const COURSE_CARD_WIDTH = 220;
const COURSE_CARD_HEIGHT = 92;
const CENTER_CARD_WIDTH = 300;
const CENTER_CARD_HEIGHT = 130;
const DETAIL_CARD_WIDTH = 184;
const DETAIL_CARD_HEIGHT = 72;
const LANE_SIDE_WIDTH = 320;
const LANE_SIDE_HEIGHT = 420;
const LANE_CENTER_WIDTH = 300;
const LANE_CENTER_HEIGHT = 260;
const LANE_SIDE_TOP = 120;
const LANE_CENTER_TOP = 110;
const LANE_BELT_HEIGHT = 132;
const LANE_BELT_TOP = 536;
const DETAIL_BELT_HEIGHT = 100;
const DETAIL_BELT_TOP = 704;
const LANE_LEFT_X = 92;
const LANE_RIGHT_X = VIEWBOX_WIDTH - LANE_SIDE_WIDTH - 92;
const LANE_CENTER_X = (VIEWBOX_WIDTH - LANE_CENTER_WIDTH) / 2;

const NODE_COLORS: Record<string, string> = {
  course: '#8b3e2f',
  concept: '#5d734f',
  requirement: '#b6863d',
  indicator: '#5e738f',
  skill: '#8b6158',
  experiment: '#4d7a76',
};

const NODE_LABELS: Record<string, string> = {
  course: '课程',
  concept: '知识点',
  requirement: '毕业要求',
  indicator: '指标点',
  skill: '能力点',
  experiment: '实验环节',
};

const TAB_LABELS = {
  graph: '课程关系导航',
  alignment: '培养方案分析',
} satisfies Record<'graph' | 'alignment', string>;

const RELATION_TITLES: Record<CourseRelationKind, string> = {
  prerequisite: '先修课程',
  next: '后续课程',
  related: '同向课程',
};

const loading = ref(true);
const error = ref('');
const graphData = ref<GraphVisualizationData | null>(null);
const searchQuery = ref('');
const searchResult = ref<GraphSearchResult | null>(null);
const alignmentData = ref<AlignmentAnalysis | null>(null);
const activeTab = ref<'graph' | 'alignment'>('graph');
const selectedNodeType = ref('');
const graphDensityMode = ref<'overview' | 'detail'>('overview');
const focusedCourseId = ref('');
const inspectedNodeId = ref('');

const stats = computed(() => graphData.value?.stats ?? null);
const filterLabel = computed(() => (selectedNodeType.value ? (NODE_LABELS[selectedNodeType.value] || selectedNodeType.value) : '全部节点'));

const nodeTypeOptions = computed(() =>
  Object.entries(stats.value?.node_types ?? {}).map(([type, count]) => ({
    type,
    count,
    label: NODE_LABELS[type] || type,
    color: NODE_COLORS[type] || '#8c7465',
  })),
);

const graphSearchPresets = computed(() => {
  const degreeMap = buildDegreeMap(graphData.value?.edges ?? []);

  return (graphData.value?.nodes ?? [])
    .filter((node) => node.type === 'course')
    .sort((left, right) => {
      const rightDegree = degreeMap.get(right.id) ?? 0;
      const leftDegree = degreeMap.get(left.id) ?? 0;
      return rightDegree - leftDegree || left.label.localeCompare(right.label, 'zh-CN');
    })
    .slice(0, 6);
});

const combinedNodeMap = computed(() => {
  const map = new Map<string, GraphNode>();

  for (const node of graphData.value?.nodes ?? []) map.set(node.id, node);
  for (const node of searchResult.value?.nodes ?? []) map.set(node.id, { ...(map.get(node.id) ?? {}), ...node } as GraphNode);

  return map;
});

const combinedEdges = computed(() => {
  const deduped = new Map<string, GraphEdge>();

  for (const edge of [...(graphData.value?.edges ?? []), ...(searchResult.value?.edges ?? [])]) {
    deduped.set(`${edge.source}-${edge.target}-${edge.type}`, edge);
  }

  return Array.from(deduped.values());
});

const edgesByNode = computed(() => {
  const map = new Map<string, GraphEdge[]>();

  for (const edge of combinedEdges.value) {
    const sourceEdges = map.get(edge.source) ?? [];
    sourceEdges.push(edge);
    map.set(edge.source, sourceEdges);

    const targetEdges = map.get(edge.target) ?? [];
    targetEdges.push(edge);
    map.set(edge.target, targetEdges);
  }

  return map;
});

const searchMatchedNodeIds = computed(() => new Set((searchResult.value?.nodes ?? []).map((node) => node.id)));
const graphViewBox = computed(() => `0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`);

const focusedCourse = computed(() => {
  const node = combinedNodeMap.value.get(focusedCourseId.value);
  return node?.type === 'course' ? node : null;
});

const focusedGraph = computed<FocusedCourseGraph | null>(() => {
  const center = focusedCourse.value;
  if (!center) return null;

  const usedIds = new Set<string>([center.id]);
  const prerequisites: GraphNode[] = [];
  const nextCourses: GraphNode[] = [];
  const relatedCourses: GraphNode[] = [];
  const detailNodes: GraphNode[] = [];
  const relationCards: CourseRelationCard[] = [];
  const edgeKeys = new Set<string>();
  const edges: GraphEdge[] = [];

  for (const edge of edgesByNode.value.get(center.id) ?? []) {
    const otherId = getOtherNodeId(edge, center.id);
    const otherNode = combinedNodeMap.value.get(otherId);
    if (!otherNode) continue;

    if (otherNode.type === 'course') {
      const relationKind = classifyCourseRelation(edge, center.id);
      const list = relationKind === 'prerequisite' ? prerequisites : relationKind === 'next' ? nextCourses : relatedCourses;
      if (list.length < 4 && !usedIds.has(otherNode.id)) {
        list.push(otherNode);
        usedIds.add(otherNode.id);
      }

      if (!relationCards.some((card) => card.id === otherNode.id)) {
        relationCards.push({
          id: otherNode.id,
          course: otherNode,
          kind: relationKind,
          title: RELATION_TITLES[relationKind],
          explanation: buildRelationExplanation(center, otherNode, relationKind, edge),
        });
      }

      const edgeKey = `${edge.source}-${edge.target}-${edge.type}`;
      if (!edgeKeys.has(edgeKey)) {
        edgeKeys.add(edgeKey);
        edges.push(edge);
      }
    } else if (graphDensityMode.value === 'detail' && detailNodes.length < 6) {
      detailNodes.push(otherNode);
      const edgeKey = `${edge.source}-${edge.target}-${edge.type}`;
      if (!edgeKeys.has(edgeKey)) {
        edgeKeys.add(edgeKey);
        edges.push(edge);
      }
    }
  }

  if (relatedCourses.length < 4) {
    const fallbackCourses = Array.from(combinedNodeMap.value.values())
      .filter((node) => node.type === 'course' && !usedIds.has(node.id))
      .filter((node) => Boolean(center.community !== undefined && node.community === center.community) || Boolean(center.category && node.category === center.category))
      .sort((left, right) => left.label.localeCompare(right.label, 'zh-CN'))
      .slice(0, 4 - relatedCourses.length);

    for (const node of fallbackCourses) {
      relatedCourses.push(node);
      usedIds.add(node.id);
      relationCards.push({
        id: node.id,
        course: node,
        kind: 'related',
        title: RELATION_TITLES.related,
        explanation: buildFallbackRelatedExplanation(center, node),
      });
    }
  }

  const laneGroups: CourseLaneGroup[] = [
    { key: 'prerequisite', title: '先修课程', kind: 'lane', x: LANE_LEFT_X, y: LANE_SIDE_TOP, width: LANE_SIDE_WIDTH, height: LANE_SIDE_HEIGHT },
    { key: 'center', title: '当前课程', kind: 'lane', x: LANE_CENTER_X, y: LANE_CENTER_TOP, width: LANE_CENTER_WIDTH, height: LANE_CENTER_HEIGHT },
    { key: 'next', title: '后续课程', kind: 'lane', x: LANE_RIGHT_X, y: LANE_SIDE_TOP, width: LANE_SIDE_WIDTH, height: LANE_SIDE_HEIGHT },
    { key: 'related', title: '同方向关联课程', kind: 'belt', x: 240, y: LANE_BELT_TOP, width: VIEWBOX_WIDTH - 480, height: LANE_BELT_HEIGHT },
  ];

  if (graphDensityMode.value === 'detail' && detailNodes.length) {
    laneGroups.push({
      key: 'detail',
      title: '当前课程细节',
      kind: 'belt',
      x: 200,
      y: DETAIL_BELT_TOP,
      width: VIEWBOX_WIDTH - 400,
      height: DETAIL_BELT_HEIGHT,
    });
  }

  return {
    center,
    prerequisites,
    nextCourses,
    relatedCourses,
    detailNodes,
    relationCards,
    laneGroups,
    edges,
    matchedKnowledge: collectMatchedKnowledge(center.id, searchResult.value, combinedNodeMap.value),
  };
});

const renderedNodes = computed<RenderNode[]>(() => {
  const graph = focusedGraph.value;
  if (!graph) return [];

  const nodes: RenderNode[] = [];
  const centerY = LANE_CENTER_TOP + LANE_CENTER_HEIGHT / 2;

  nodes.push({
    key: graph.center.id,
    node: graph.center,
    x: VIEWBOX_WIDTH / 2,
    y: centerY,
    width: CENTER_CARD_WIDTH,
    height: CENTER_CARD_HEIGHT,
    lane: 'center',
    emphasis: 'center',
  });

  placeVerticalLane(nodes, graph.prerequisites, 'prerequisite', LANE_LEFT_X + LANE_SIDE_WIDTH / 2, centerY, COURSE_CARD_WIDTH, COURSE_CARD_HEIGHT);
  placeVerticalLane(nodes, graph.nextCourses, 'next', LANE_RIGHT_X + LANE_SIDE_WIDTH / 2, centerY, COURSE_CARD_WIDTH, COURSE_CARD_HEIGHT);
  placeHorizontalBelt(
    nodes,
    graph.relatedCourses,
    'related',
    300,
    LANE_BELT_TOP + LANE_BELT_HEIGHT / 2,
    226,
    COURSE_CARD_WIDTH,
    COURSE_CARD_HEIGHT,
  );

  if (graphDensityMode.value === 'detail') {
    placeHorizontalBelt(
      nodes,
      graph.detailNodes,
      'detail',
      260,
      DETAIL_BELT_TOP + DETAIL_BELT_HEIGHT / 2,
      196,
      DETAIL_CARD_WIDTH,
      DETAIL_CARD_HEIGHT,
      'detail',
    );
  }

  return nodes;
});

const renderedNodeMap = computed(() => new Map(renderedNodes.value.map((node) => [node.node.id, node])));

const renderedEdges = computed<RenderEdge[]>(() => {
  const graph = focusedGraph.value;
  if (!graph) return [];

  return graph.edges.flatMap((edge, index) => {
    const source = renderedNodeMap.value.get(edge.source);
    const target = renderedNodeMap.value.get(edge.target);
    if (!source || !target) return [];

    const kind = source.lane === 'detail' || target.lane === 'detail' ? 'detail' : classifyCourseRelation(edge, graph.center.id);
    return [{ key: `${edge.source}-${edge.target}-${edge.type}-${index}`, kind, path: edgePathBetween(source, target), color: edgeColor(kind) }];
  });
});

const inspectedNode = computed(() => combinedNodeMap.value.get(inspectedNodeId.value || focusedCourseId.value) ?? focusedCourse.value);

const discoverySummary = computed(() => {
  if (!focusedGraph.value) return '默认不再铺开全专业总图。先搜索一门课程，再沿先修链路查看上下游课程与知识点。';
  const graph = focusedGraph.value;
  return `已聚焦 ${graph.center.label}，当前显示 ${graph.prerequisites.length} 门先修、${graph.nextCourses.length} 门后续与 ${graph.relatedCourses.length} 门同向课程。`;
});

const recommendationCards = computed(() => focusedGraph.value?.relationCards.slice(0, 8) ?? []);

const courseDossier = computed(() => {
  const node = focusedGraph.value?.center;
  if (!node) return [];

  return [
    ['课程代码', node.code || '未标注'],
    ['课程类别', node.category || '未标注'],
    ['建议学期', node.semester || '未标注'],
    ['学分', typeof node.credits === 'number' ? `${node.credits}` : '未标注'],
    ['布鲁姆层级', node.bloom_level || '未标注'],
    ['所属社群', node.community !== undefined ? `${node.community}` : '未标注'],
  ];
});

const knowledgeSummary = computed(() => {
  const graph = focusedGraph.value;
  if (!graph) return [];
  if (graph.matchedKnowledge.length) return graph.matchedKnowledge;
  return graph.detailNodes.map((node) => `${NODE_LABELS[node.type] || node.type}：${node.label}`).slice(0, 6);
});

const relationSummary = computed(() => {
  const graph = focusedGraph.value;
  if (!graph) return [];

  return [
    { label: '先修链路', value: graph.prerequisites.length ? graph.prerequisites.map((node) => node.label).join('、') : '当前没有标注先修课程' },
    { label: '后续走向', value: graph.nextCourses.length ? graph.nextCourses.map((node) => node.label).join('、') : '当前没有标注后续课程' },
    { label: '关联方向', value: graph.relatedCourses.length ? graph.relatedCourses.map((node) => node.label).join('、') : '当前没有发现同方向课程' },
  ];
});

watch(
  [stats, filterLabel, activeTab],
  () => {
    emit('state-change', {
      nodeCount: stats.value?.node_count ?? 0,
      edgeCount: stats.value?.edge_count ?? 0,
      communityCount: stats.value?.community_count ?? 0,
      filterLabel: filterLabel.value,
      activeTab: activeTab.value,
      activeTabLabel: TAB_LABELS[activeTab.value],
    });
  },
  { immediate: true },
);

watch(activeTab, async (nextTab) => {
  if (nextTab === 'alignment' && !alignmentData.value) await loadAlignment();
});

onMounted(async () => {
  await loadGraphData();
});

async function loadGraphData() {
  loading.value = true;
  error.value = '';

  try {
    graphData.value = await apiClient.getGraphVisualization(selectedNodeType.value || undefined);
    if (focusedCourseId.value && !graphData.value.nodes.some((node) => node.id === focusedCourseId.value) && !searchResult.value) {
      focusedCourseId.value = '';
      inspectedNodeId.value = '';
    }
  } catch (cause: unknown) {
    graphData.value = null;
    error.value = (cause instanceof Error ? cause.message : '') || '加载图谱数据失败';
  } finally {
    loading.value = false;
  }
}

async function searchGraph() {
  const query = searchQuery.value.trim();
  if (!query) return;

  error.value = '';

  try {
    searchResult.value = await apiClient.searchGraph(query, 2, 30);
    const seedCourseId = resolveFocusCourse(searchResult.value);
    focusedCourseId.value = seedCourseId;
    inspectedNodeId.value = seedCourseId;
    graphDensityMode.value = 'overview';
  } catch (cause: unknown) {
    error.value = (cause instanceof Error ? cause.message : '') || '课程检索失败';
  }
}

async function loadAlignment() {
  try {
    alignmentData.value = await apiClient.getAlignmentAnalysis();
  } catch (cause: unknown) {
    error.value = (cause instanceof Error ? cause.message : '') || '加载培养方案分析失败';
  }
}

async function handleTypeSelect(type: string) {
  selectedNodeType.value = type;
  searchResult.value = null;
  searchQuery.value = '';
  focusedCourseId.value = '';
  inspectedNodeId.value = '';
  graphDensityMode.value = 'overview';
  await loadGraphData();
}

function clearSelection() {
  searchResult.value = null;
  searchQuery.value = '';
  focusedCourseId.value = '';
  inspectedNodeId.value = '';
  graphDensityMode.value = 'overview';
}

function focusCourse(node: GraphNode) {
  if (node.type !== 'course') return;
  focusedCourseId.value = node.id;
  inspectedNodeId.value = node.id;
  searchQuery.value = node.label;
}

function inspectNode(nodeId: string) {
  const node = combinedNodeMap.value.get(nodeId);
  if (!node) return;
  if (node.type === 'course') return focusCourse(node);
  inspectedNodeId.value = node.id;
}

function buildDegreeMap(edges: GraphEdge[]) {
  const map = new Map<string, number>();
  for (const edge of edges) {
    map.set(edge.source, (map.get(edge.source) ?? 0) + 1);
    map.set(edge.target, (map.get(edge.target) ?? 0) + 1);
  }
  return map;
}

function getOtherNodeId(edge: GraphEdge, nodeId: string) {
  return edge.source === nodeId ? edge.target : edge.source;
}

function resolveFocusCourse(result: GraphSearchResult) {
  const directCourse = result.nodes.find((node) => node.type === 'course' && node.is_seed) || result.nodes.find((node) => node.type === 'course');
  if (directCourse) return directCourse.id;

  const seedIds = result.nodes.filter((node) => node.is_seed).map((node) => node.id);
  const queue = [...(seedIds.length ? seedIds : result.nodes.map((node) => node.id))];
  const visited = new Set(queue);

  while (queue.length) {
    const currentId = queue.shift();
    if (!currentId) continue;

    for (const edge of edgesByNode.value.get(currentId) ?? []) {
      const nextId = getOtherNodeId(edge, currentId);
      if (visited.has(nextId)) continue;
      visited.add(nextId);
      const node = combinedNodeMap.value.get(nextId);
      if (node?.type === 'course') return node.id;
      queue.push(nextId);
    }
  }

  return '';
}

function classifyCourseRelation(edge: GraphEdge, centerId: string): CourseRelationKind {
  if (edge.type === 'prerequisite') {
    if (edge.target === centerId) return 'prerequisite';
    if (edge.source === centerId) return 'next';
  }

  if (edge.type === 'leads_to') {
    if (edge.source === centerId) return 'next';
    if (edge.target === centerId) return 'prerequisite';
  }

  if (edge.type === 'co_required' || edge.type === 'related') return 'related';
  return 'related';
}

function buildRelationExplanation(center: GraphNode, course: GraphNode, kind: CourseRelationKind, edge: GraphEdge) {
  if (kind === 'prerequisite') return `${course.label} 为 ${center.label} 提供进入本课程所需的基础能力。`;
  if (kind === 'next') return `${center.label} 完成后可自然衔接到 ${course.label}。`;
  const relationText = edge.type === 'co_required' ? '建议并行学习' : '属于同一方向或模块';
  return `${course.label} 与 ${center.label}${relationText}，适合作为横向拓展。`;
}

function buildFallbackRelatedExplanation(center: GraphNode, course: GraphNode) {
  if (center.category && course.category && center.category === course.category) {
    return `${course.label} 与 ${center.label} 同属 ${center.category}，可作为同模块延展课程。`;
  }

  if (center.community !== undefined && course.community === center.community) {
    return `${course.label} 与 ${center.label} 位于同一课程社群，可作为方向拓展入口。`;
  }

  return `${course.label} 与 ${center.label} 在当前培养图谱中保持近邻关系，适合作为下一步浏览对象。`;
}

function collectMatchedKnowledge(centerId: string, result: GraphSearchResult | null, nodes: Map<string, GraphNode>) {
  if (!result) return [];

  const linked = new Set<string>();
  for (const edge of result.edges) {
    if (edge.source === centerId) linked.add(edge.target);
    if (edge.target === centerId) linked.add(edge.source);
  }

  const labels = result.nodes
    .filter((node) => node.id !== centerId)
    .filter((node) => node.type !== 'course')
    .filter((node) => linked.has(node.id) || node.is_seed)
    .map((node) => `${NODE_LABELS[node.type] || node.type}：${nodes.get(node.id)?.label || node.label}`);

  if (labels.length) return labels.slice(0, 6);
  return result.paths.map((path) => `命中路径：${path.path}`).slice(0, 4);
}

function placeVerticalLane(target: RenderNode[], nodes: GraphNode[], lane: string, x: number, centerY: number, width: number, height: number) {
  if (!nodes.length) return;

  const gap = 118;
  const startY = centerY - ((nodes.length - 1) * gap) / 2;

  nodes.forEach((node, index) => {
    target.push({ key: node.id, node, x, y: startY + index * gap, width, height, lane, emphasis: 'course' });
  });
}

function placeHorizontalBelt(
  target: RenderNode[],
  nodes: GraphNode[],
  lane: string,
  startX: number,
  y: number,
  gap: number,
  width: number,
  height: number,
  emphasis: 'course' | 'detail' = 'course',
) {
  nodes.slice(0, 4).forEach((node, index) => {
    target.push({ key: node.id, node, x: startX + index * gap, y, width, height, lane, emphasis });
  });
}

function edgeColor(kind: CourseRelationKind | 'detail') {
  if (kind === 'prerequisite') return 'rgba(139, 62, 47, 0.36)';
  if (kind === 'next') return 'rgba(93, 115, 79, 0.32)';
  if (kind === 'detail') return 'rgba(91, 110, 136, 0.26)';
  return 'rgba(182, 134, 61, 0.28)';
}

function edgePathBetween(source: RenderNode, target: RenderNode) {
  const sourceIsLeft = source.x <= target.x;
  const sourceX = sourceIsLeft ? source.x + source.width / 2 : source.x - source.width / 2;
  const targetX = sourceIsLeft ? target.x - target.width / 2 : target.x + target.width / 2;
  const deltaX = Math.abs(targetX - sourceX);
  const controlX = Math.max(92, deltaX * 0.46);
  return `M ${sourceX} ${source.y} C ${sourceX + (sourceIsLeft ? controlX : -controlX)} ${source.y}, ${targetX - (sourceIsLeft ? controlX : -controlX)} ${target.y}, ${targetX} ${target.y}`;
}

function nodeTitle(node: GraphNode) {
  return node.label.length > 15 ? `${node.label.slice(0, 15)}…` : node.label;
}

function nodeMeta(node: GraphNode) {
  if (node.type === 'course') {
    return [node.code, node.category || `类型：${NODE_LABELS[node.type] || node.type}`, typeof node.credits === 'number' ? `${node.credits} 学分` : '']
      .filter(Boolean)
      .join(' · ');
  }

  return [NODE_LABELS[node.type] || node.type, node.category || node.semester || '当前课程邻域'].filter(Boolean).join(' · ');
}
</script>

<template>
  <section class="atlas">
    <header class="atlas__topbar">
      <div class="atlas__heading">
        <span class="atlas__seal">
          <i class="fa-solid fa-diagram-project"></i>
        </span>
        <div>
          <p class="atlas__eyebrow">Curriculum Atlas</p>
          <h2>单课程聚焦 · 先修链路课程地图</h2>
        </div>
      </div>

      <div class="atlas__tabs">
        <button class="atlas__tab" :data-active="activeTab === 'graph'" type="button" @click="activeTab = 'graph'">
          <i class="fa-solid fa-route"></i>
          <span>{{ TAB_LABELS.graph }}</span>
        </button>

        <button class="atlas__tab" :data-active="activeTab === 'alignment'" type="button" @click="activeTab = 'alignment'">
          <i class="fa-solid fa-chart-column"></i>
          <span>{{ TAB_LABELS.alignment }}</span>
        </button>
      </div>
    </header>

    <section v-if="activeTab === 'graph'" class="atlas__layout">
      <aside class="atlas__rail">
        <section class="atlas__panel" data-testid="graph-filters-panel">
          <div class="atlas__panel-head">
            <span>数据视角</span>
            <strong>{{ filterLabel }}</strong>
          </div>

          <div class="atlas__filters">
            <button class="atlas__filter" type="button" :data-active="selectedNodeType === ''" @click="handleTypeSelect('')">
              <span class="atlas__filter-dot atlas__filter-dot--all"></span>
              <span>全部节点</span>
            </button>

            <button
              v-for="option in nodeTypeOptions"
              :key="option.type"
              class="atlas__filter"
              type="button"
              :data-active="selectedNodeType === option.type"
              @click="handleTypeSelect(option.type)"
            >
              <span class="atlas__filter-dot" :style="{ background: option.color }"></span>
              <span>{{ option.label }}</span>
              <small>{{ option.count }}</small>
            </button>
          </div>
        </section>

        <section class="atlas__panel">
          <div class="atlas__panel-head">
            <span>浏览方式</span>
            <strong>{{ graphDensityMode === 'overview' ? '课程骨架' : '展开细节' }}</strong>
          </div>

          <div class="atlas__density-switch">
            <button class="atlas__density-chip" type="button" :data-active="graphDensityMode === 'overview'" @click="graphDensityMode = 'overview'">
              课程骨架
            </button>
            <button
              class="atlas__density-chip"
              type="button"
              :data-active="graphDensityMode === 'detail'"
              :disabled="!focusedGraph"
              @click="graphDensityMode = 'detail'"
            >
              展开细节
            </button>
          </div>

          <p class="atlas__copy">
            主图默认只显示课程链路，不再铺满知识点。只有你主动展开时，当前课程邻域的知识点和要求点才会出现。
          </p>
        </section>

        <section class="atlas__panel">
          <div class="atlas__panel-head">
            <span>推荐入口</span>
            <strong>{{ graphSearchPresets.length }}</strong>
          </div>

          <div class="atlas__preset-list">
            <button v-for="course in graphSearchPresets" :key="course.id" class="atlas__preset" type="button" @click="focusCourse(course)">
              {{ course.label }}
            </button>
          </div>
        </section>
      </aside>

      <div class="atlas__main">
        <section class="atlas__panel atlas__toolbar-panel" data-testid="graph-toolbar">
          <div class="atlas__toolbar">
            <label class="atlas__search">
              <i class="fa-solid fa-magnifying-glass"></i>
              <input
                v-model="searchQuery"
                type="search"
                placeholder="搜索课程名、课程代码或知识点"
                @keydown.enter.prevent="searchGraph"
              />
            </label>

            <button class="atlas__action atlas__action--primary" type="button" @click="searchGraph">
              搜索课程地图
            </button>

            <button class="atlas__action" type="button" :disabled="!focusedGraph && !searchResult" @click="clearSelection">
              重置工作台
            </button>

            <div class="atlas__meta">
              <span>当前模式</span>
              <strong>{{ graphDensityMode === 'overview' ? '单课程聚焦' : '局部细节展开' }}</strong>
            </div>
          </div>
        </section>

        <div class="atlas__workspace">
          <section class="atlas__panel atlas__canvas-card" data-testid="graph-canvas-card">
            <div class="atlas__canvas-head">
              <div>
                <p>Course Navigator</p>
                <h3>{{ focusedGraph ? focusedGraph.center.label : '课程导航工作台' }}</h3>
              </div>

              <div class="atlas__stats">
                <span>{{ discoverySummary }}</span>
              </div>
            </div>

            <div class="atlas__canvas-shell">
              <div v-if="loading" class="atlas__overlay" data-testid="graph-loading">
                <div class="atlas__overlay-card">
                  <div class="atlas__spinner"></div>
                  <p>正在整理课程关系图谱...</p>
                </div>
              </div>

              <div v-else-if="error" class="atlas__overlay" data-testid="graph-error">
                <div class="atlas__overlay-card">
                  <i class="fa-solid fa-circle-exclamation"></i>
                  <p>{{ error }}</p>
                </div>
              </div>

              <div v-else-if="!stats?.node_count" class="atlas__overlay" data-testid="graph-empty">
                <div class="atlas__overlay-card">
                  <i class="fa-solid fa-circle-nodes"></i>
                  <p>当前筛选范围暂时没有图谱数据，请切换数据视角后重试。</p>
                </div>
              </div>

              <div v-else-if="!focusedGraph" class="atlas__workspace-empty" data-testid="graph-search-empty">
                <div class="atlas__workspace-empty-card">
                  <div class="atlas__workspace-empty-badge">
                    <i class="fa-solid fa-book-open-reader"></i>
                  </div>
                  <h3>先搜索一门课程，再展开它的先修链路</h3>
                  <p>
                    首页不再默认铺开全量课程网络。输入课程名、课程代码或知识点后，系统会先定位所属课程，再只展示该课程的局部课程链路。
                  </p>

                  <div class="atlas__empty-actions">
                    <button v-for="course in graphSearchPresets" :key="course.id" class="atlas__preset" type="button" @click="focusCourse(course)">
                      {{ course.label }}
                    </button>
                  </div>

                  <div class="atlas__empty-points">
                    <span>左列展示先修课程</span>
                    <span>中列固定当前课程</span>
                    <span>右列展示后续课程</span>
                    <span>底部展示同方向关联课程</span>
                  </div>
                </div>
              </div>

              <svg v-else class="atlas__svg" :viewBox="graphViewBox" role="img" aria-label="课程先修链路图">
                <rect class="atlas__field" x="0" y="0" :width="VIEWBOX_WIDTH" :height="VIEWBOX_HEIGHT" rx="28" />

                <g class="atlas__lanes">
                  <g v-for="lane in focusedGraph.laneGroups" :key="lane.key">
                    <rect class="atlas__lane-block" :x="lane.x" :y="lane.y" :width="lane.width" :height="lane.height" rx="26" />
                    <text class="atlas__lane-label" :x="lane.x + 24" :y="lane.y + 34">
                      {{ lane.title }}
                    </text>
                  </g>
                </g>

                <g class="atlas__edges">
                  <path v-for="edge in renderedEdges" :key="edge.key" class="atlas__edge" :d="edge.path" :stroke="edge.color" />
                </g>

                <g class="atlas__nodes">
                  <g
                    v-for="node in renderedNodes"
                    :key="node.key"
                    class="atlas__node"
                    :data-center="node.emphasis === 'center'"
                    :data-matched="searchMatchedNodeIds.has(node.node.id)"
                    @click="inspectNode(node.node.id)"
                  >
                    <rect
                      class="atlas__node-card"
                      :x="node.x - node.width / 2"
                      :y="node.y - node.height / 2"
                      :width="node.width"
                      :height="node.height"
                      rx="24"
                    />
                    <circle
                      class="atlas__node-dot"
                      :cx="node.x - node.width / 2 + 22"
                      :cy="node.y - node.height / 2 + 22"
                      r="6"
                      :fill="NODE_COLORS[node.node.type] || '#8c7465'"
                    />
                    <text class="atlas__node-title" :x="node.x - node.width / 2 + 38" :y="node.y - node.height / 2 + 28">
                      {{ nodeTitle(node.node) }}
                    </text>
                    <text class="atlas__node-meta" :x="node.x - node.width / 2 + 20" :y="node.y - node.height / 2 + 54">
                      {{ nodeMeta(node.node) }}
                    </text>
                    <text v-if="node.emphasis === 'center'" class="atlas__node-badge" :x="node.x - node.width / 2 + 20" :y="node.y - node.height / 2 + 82">
                      中心课程
                    </text>
                  </g>
                </g>
              </svg>
            </div>
          </section>

          <aside class="atlas__inspectors">
            <section v-if="!focusedGraph" class="atlas__panel" data-testid="graph-node-empty">
              <div class="atlas__panel-head">
                <span>课程档案</span>
                <strong>等待选中</strong>
              </div>

              <p class="atlas__copy">
                选中课程后，这里会显示课程档案、先修关系解释、知识点摘要与可点击的相关课程推荐，帮助你按课程线索而不是按噪音看图。
              </p>
            </section>

            <template v-else>
              <section class="atlas__panel">
                <div class="atlas__panel-head">
                  <span>课程档案</span>
                  <strong>{{ focusedGraph.center.code || '课程中心' }}</strong>
                </div>

                <div class="atlas__dossier-head">
                  <h3>{{ focusedGraph.center.label }}</h3>
                  <span>{{ focusedGraph.center.category || '人工智能专业课程' }}</span>
                </div>

                <dl class="atlas__dossier-grid">
                  <div v-for="[label, value] in courseDossier" :key="label" class="atlas__dossier-item">
                    <dt>{{ label }}</dt>
                    <dd>{{ value }}</dd>
                  </div>
                </dl>
              </section>

              <section class="atlas__panel">
                <div class="atlas__panel-head">
                  <span>关系说明</span>
                  <strong>{{ recommendationCards.length }}</strong>
                </div>

                <div class="atlas__analysis-list">
                  <article v-for="item in relationSummary" :key="item.label" class="atlas__analysis">
                    <h3>{{ item.label }}</h3>
                    <p>{{ item.value }}</p>
                  </article>
                </div>
              </section>

              <section class="atlas__panel">
                <div class="atlas__panel-head">
                  <span>知识点摘要</span>
                  <strong>{{ knowledgeSummary.length }}</strong>
                </div>

                <div v-if="knowledgeSummary.length" class="atlas__analysis-list">
                  <article v-for="item in knowledgeSummary" :key="item" class="atlas__analysis">
                    <p>{{ item }}</p>
                  </article>
                </div>
                <p v-else class="atlas__copy">
                  当前课程暂未检索到额外知识点摘要。切换到“展开细节”可查看当前课程邻域中的知识点和要求点。
                </p>
              </section>

              <section class="atlas__panel">
                <div class="atlas__panel-head">
                  <span>相关课程推荐</span>
                  <strong>{{ recommendationCards.length }}</strong>
                </div>

                <div v-if="recommendationCards.length" class="atlas__recommendations">
                  <button
                    v-for="course in recommendationCards"
                    :key="course.id"
                    class="atlas__recommendation"
                    type="button"
                    @click="focusCourse(course.course)"
                  >
                    <strong>{{ course.course.label }}</strong>
                    <span>{{ course.course.code || '课程节点' }}</span>
                    <em>{{ course.title }}</em>
                    <p>{{ course.explanation }}</p>
                  </button>
                </div>
                <p v-else class="atlas__copy">
                  当前课程邻域没有更多推荐课程。你可以直接搜索另一门课程继续浏览。
                </p>
              </section>

              <section v-if="inspectedNode && inspectedNode.id !== focusedGraph.center.id" class="atlas__panel">
                <div class="atlas__panel-head">
                  <span>当前查看节点</span>
                  <strong>{{ NODE_LABELS[inspectedNode.type] || inspectedNode.type }}</strong>
                </div>
                <div class="atlas__analysis">
                  <h3>{{ inspectedNode.label }}</h3>
                  <p>{{ nodeMeta(inspectedNode) }}</p>
                </div>
              </section>
            </template>
          </aside>
        </div>
      </div>
    </section>

    <section v-else class="atlas__alignment" data-testid="alignment-panel">
      <div v-if="!alignmentData" class="atlas__alignment-loading">
        <div class="atlas__spinner"></div>
        <span>正在生成培养方案诊断...</span>
      </div>

      <template v-else>
        <div class="atlas__alignment-metrics">
          <article class="atlas__metric atlas__metric--course">
            <span>课程总数</span>
            <strong>{{ alignmentData.total_courses }}</strong>
          </article>
          <article class="atlas__metric atlas__metric--concept">
            <span>知识点总数</span>
            <strong>{{ alignmentData.total_concepts }}</strong>
          </article>
          <article class="atlas__metric atlas__metric--requirement">
            <span>毕业要求数</span>
            <strong>{{ alignmentData.total_requirements }}</strong>
          </article>
        </div>

        <div class="atlas__alignment-grid">
          <section class="atlas__panel">
            <div class="atlas__panel-head">
              <span>知识断层</span>
              <strong>{{ alignmentData.gap_count }}</strong>
            </div>
            <div v-if="alignmentData.gaps.length" class="atlas__analysis-list">
              <article v-for="gap in alignmentData.gaps" :key="`${gap.requirement}-${gap.suggestion}`" class="atlas__analysis atlas__analysis--danger">
                <h3>{{ gap.requirement }}</h3>
                <p>{{ gap.suggestion }}</p>
                <div class="atlas__tag-row">
                  <span v-for="course in gap.supporting_courses" :key="course" class="atlas__tag">{{ course }}</span>
                </div>
              </article>
            </div>
            <p v-else class="atlas__copy">当前没有发现明显的知识断层。</p>
          </section>

          <section class="atlas__panel">
            <div class="atlas__panel-head">
              <span>知识重叠</span>
              <strong>{{ alignmentData.overlap_count }}</strong>
            </div>
            <div v-if="alignmentData.overlaps.length" class="atlas__analysis-list">
              <article v-for="overlap in alignmentData.overlaps" :key="`${overlap.concept}-${overlap.suggestion}`" class="atlas__analysis atlas__analysis--warning">
                <h3>{{ overlap.concept }}</h3>
                <p>{{ overlap.suggestion }}</p>
                <div class="atlas__tag-row">
                  <span v-for="course in overlap.courses" :key="course" class="atlas__tag">{{ course }}</span>
                </div>
              </article>
            </div>
            <p v-else class="atlas__copy">当前没有发现明显的重复讲授风险。</p>
          </section>

          <section class="atlas__panel">
            <div class="atlas__panel-head">
              <span>孤立课程提醒</span>
              <strong>{{ alignmentData.orphans.length }}</strong>
            </div>
            <div v-if="alignmentData.orphans.length" class="atlas__analysis-list">
              <article v-for="orphan in alignmentData.orphans" :key="`${orphan.course}-${orphan.suggestion}`" class="atlas__analysis">
                <h3>{{ orphan.course }}</h3>
                <p>{{ orphan.suggestion }}</p>
              </article>
            </div>
            <p v-else class="atlas__copy">所有课程都已经纳入毕业要求映射网络。</p>
          </section>

          <section class="atlas__panel">
            <div class="atlas__panel-head">
              <span>要求覆盖速览</span>
              <strong>{{ Object.keys(alignmentData.requirement_coverage).length }}</strong>
            </div>
            <div class="atlas__analysis-list">
              <article v-for="(courses, requirement) in alignmentData.requirement_coverage" :key="requirement" class="atlas__analysis">
                <h3>{{ requirement }}</h3>
                <p>{{ courses.join('、') }}</p>
              </article>
            </div>
          </section>
        </div>
      </template>
    </section>
  </section>
</template>

<style scoped>
.atlas {
  display: grid;
  gap: 1rem;
  --rail-width: 260px;
  --inspector-width: 320px;
  --canvas-min-height: 720px;
  --canvas-max-height: 840px;
}

.atlas__topbar,
.atlas__panel,
.atlas__metric,
.atlas__alignment-loading {
  border: 1px solid rgba(120, 85, 63, 0.16);
  border-radius: var(--campus-radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 252, 248, 0.96), rgba(252, 246, 239, 0.92)),
    radial-gradient(circle at top right, rgba(244, 226, 197, 0.24), transparent 30%);
  box-shadow: 0 20px 54px rgba(74, 50, 38, 0.08);
  backdrop-filter: blur(16px);
}

.atlas__topbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.1rem;
}

.atlas__heading {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.atlas__seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  color: #fff8f1;
  background: linear-gradient(135deg, rgba(142, 72, 50, 0.98), rgba(198, 143, 66, 0.92));
  box-shadow: 0 16px 34px rgba(118, 63, 41, 0.18);
}

.atlas__eyebrow {
  margin: 0;
  color: rgba(93, 71, 61, 0.74);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.atlas__heading h2 {
  margin: 0.3rem 0 0;
  color: var(--campus-ink);
  font-family: var(--font-display);
  font-size: clamp(1.22rem, 2vw, 1.56rem);
}

.atlas__tabs,
.atlas__stats,
.atlas__tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.atlas__tab,
.atlas__action,
.atlas__filter,
.atlas__density-chip,
.atlas__preset {
  min-height: 44px;
  border: 1px solid rgba(120, 85, 63, 0.16);
  border-radius: 999px;
  background: rgba(255, 251, 246, 0.9);
  color: var(--campus-text);
  cursor: pointer;
  transition:
    transform var(--campus-duration-fast) var(--campus-ease),
    border-color var(--campus-duration-fast) var(--campus-ease),
    box-shadow var(--campus-duration-fast) var(--campus-ease),
    background var(--campus-duration-fast) var(--campus-ease);
}

.atlas__tab:hover,
.atlas__action:hover,
.atlas__filter:hover,
.atlas__density-chip:hover,
.atlas__preset:hover,
.atlas__recommendation:hover {
  transform: translateY(-1px);
  border-color: rgba(142, 72, 50, 0.28);
  box-shadow: 0 14px 28px rgba(80, 52, 39, 0.08);
}

.atlas__tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.72rem 0.95rem;
  font-size: 0.88rem;
  font-weight: 600;
}

.atlas__tab[data-active='true'],
.atlas__action--primary,
.atlas__density-chip[data-active='true'] {
  color: #fff8f1;
  border-color: transparent;
  background: linear-gradient(135deg, rgba(142, 72, 50, 0.98), rgba(108, 53, 38, 0.96));
}

.atlas__action:disabled,
.atlas__density-chip:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

.atlas__layout {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(240px, var(--rail-width)) minmax(0, 1fr);
}

.atlas__rail,
.atlas__inspectors,
.atlas__main,
.atlas__alignment {
  display: grid;
  gap: 1rem;
  align-content: start;
}

.atlas__panel {
  padding: 1rem;
}

.atlas__panel-head,
.atlas__canvas-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.atlas__panel-head span,
.atlas__meta span,
.atlas__dossier-item dt {
  color: var(--text-tertiary);
  font-size: 0.72rem;
}

.atlas__panel-head span {
  font-weight: 700;
  letter-spacing: 0.06em;
}

.atlas__panel-head strong,
.atlas__meta strong {
  color: var(--campus-ink);
}

.atlas__copy,
.atlas__analysis p,
.atlas__dossier-item dd,
.atlas__workspace-empty-card p,
.atlas__recommendation p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.75;
}

.atlas__filters,
.atlas__analysis-list,
.atlas__dossier-grid,
.atlas__recommendations {
  display: grid;
  gap: 0.65rem;
}

.atlas__filter {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.6rem;
  padding: 0.76rem 0.88rem;
  font-size: 0.92rem;
  font-weight: 600;
}

.atlas__filter[data-active='true'] {
  background: rgba(142, 72, 50, 0.1);
  border-color: rgba(142, 72, 50, 0.3);
}

.atlas__filter small {
  margin-left: auto;
  color: var(--text-tertiary);
  font-size: 0.72rem;
}

.atlas__filter-dot {
  width: 0.72rem;
  height: 0.72rem;
  border-radius: 999px;
  flex: none;
}

.atlas__filter-dot--all {
  background: linear-gradient(135deg, #ae5c3f, #d0a66f);
}

.atlas__density-switch,
.atlas__preset-list,
.atlas__empty-actions,
.atlas__empty-points {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.atlas__density-chip,
.atlas__preset,
.atlas__action {
  padding: 0.72rem 0.96rem;
  font-size: 0.88rem;
  font-weight: 700;
}

.atlas__toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  gap: 0.8rem;
  align-items: center;
}

.atlas__search {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 46px;
  padding: 0 1rem;
  border: 1px solid rgba(120, 85, 63, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
}

.atlas__search i {
  color: rgba(142, 72, 50, 0.72);
}

.atlas__search input {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--campus-text);
  font-size: 0.94rem;
  outline: none;
}

.atlas__meta {
  display: grid;
  gap: 0.18rem;
  justify-items: end;
  min-width: 120px;
}

.atlas__workspace {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr) minmax(300px, var(--inspector-width));
  align-items: start;
}

.atlas__canvas-card {
  padding: 0;
  overflow: hidden;
}

.atlas__canvas-head {
  flex-wrap: wrap;
  align-items: end;
  padding: 1rem 1rem 0.85rem;
  margin: 0;
}

.atlas__canvas-head p {
  margin: 0;
  color: rgba(96, 72, 61, 0.68);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.atlas__canvas-head h3 {
  margin: 0.35rem 0 0;
  color: var(--campus-ink);
  font-family: var(--font-display);
  font-size: 1.36rem;
}

.atlas__stats span,
.atlas__tag,
.atlas__empty-points span {
  padding: 0.44rem 0.74rem;
  border: 1px solid rgba(120, 85, 63, 0.14);
  border-radius: 999px;
  background: rgba(255, 251, 246, 0.8);
  color: var(--text-secondary);
  font-size: 0.74rem;
}

.atlas__canvas-shell {
  position: relative;
  min-height: var(--canvas-min-height);
  height: min(var(--canvas-max-height), 72vh);
  border-top: 1px solid rgba(120, 85, 63, 0.12);
  background:
    radial-gradient(circle at top left, rgba(247, 238, 225, 0.84), transparent 36%),
    radial-gradient(circle at bottom right, rgba(237, 228, 213, 0.76), transparent 34%),
    linear-gradient(180deg, rgba(248, 242, 236, 0.98), rgba(241, 233, 224, 0.98));
}

.atlas__svg {
  display: block;
  width: 100%;
  height: 100%;
}

.atlas__field {
  fill: rgba(248, 244, 239, 0.72);
}

.atlas__lane-block {
  fill: rgba(255, 255, 255, 0.42);
  stroke: rgba(128, 103, 86, 0.14);
  stroke-width: 1.1;
}

.atlas__lane-label {
  fill: rgba(92, 70, 58, 0.78);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.atlas__edge {
  fill: none;
  stroke-width: 4.5;
  stroke-linecap: round;
}

.atlas__node {
  cursor: pointer;
}

.atlas__node-card {
  fill: rgba(255, 252, 248, 0.97);
  stroke: rgba(132, 95, 72, 0.16);
  stroke-width: 1.4;
  filter: drop-shadow(0 14px 24px rgba(86, 59, 45, 0.08));
}

.atlas__node-dot {
  stroke: rgba(255, 255, 255, 0.92);
  stroke-width: 1.5;
}

.atlas__node-title {
  fill: var(--campus-ink);
  font-size: 14px;
  font-weight: 700;
}

.atlas__node-meta,
.atlas__node-badge {
  fill: rgba(95, 72, 61, 0.72);
  font-size: 12px;
  font-weight: 600;
}

.atlas__node[data-center='true'] .atlas__node-card {
  fill: rgba(255, 249, 242, 0.98);
  stroke: rgba(174, 92, 63, 0.42);
  stroke-width: 2;
}

.atlas__node[data-matched='true'] .atlas__node-card {
  stroke: rgba(93, 115, 79, 0.42);
  stroke-width: 2;
}

.atlas__workspace-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--canvas-min-height);
  height: min(var(--canvas-max-height), 72vh);
  padding: 1.5rem;
}

.atlas__workspace-empty-card,
.atlas__overlay-card {
  display: grid;
  justify-items: center;
  gap: 0.9rem;
  max-width: 34rem;
  padding: 1.6rem;
  border: 1px solid rgba(120, 85, 63, 0.14);
  border-radius: 1.3rem;
  background: rgba(255, 251, 246, 0.94);
  text-align: center;
}

.atlas__workspace-empty-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.6rem;
  height: 3.6rem;
  border-radius: 1.2rem;
  color: #fff8f1;
  background: linear-gradient(135deg, rgba(142, 72, 50, 0.98), rgba(198, 143, 66, 0.92));
}

.atlas__workspace-empty-card h3 {
  margin: 0;
  color: var(--campus-ink);
  font-family: var(--font-display);
  font-size: 1.42rem;
}

.atlas__overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(250, 244, 237, 0.78);
  backdrop-filter: blur(8px);
}

.atlas__spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid rgba(174, 92, 63, 0.24);
  border-top-color: rgba(174, 92, 63, 0.95);
  border-radius: 999px;
  animation: atlas-spin 0.9s linear infinite;
}

.atlas__recommendation,
.atlas__analysis,
.atlas__dossier-item {
  display: grid;
  gap: 0.32rem;
  padding: 0.82rem 0.88rem;
  border: 1px solid rgba(120, 85, 63, 0.12);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.74);
}

.atlas__recommendation {
  cursor: pointer;
  text-align: left;
  transition:
    transform var(--campus-duration-fast) var(--campus-ease),
    border-color var(--campus-duration-fast) var(--campus-ease),
    box-shadow var(--campus-duration-fast) var(--campus-ease);
}

.atlas__recommendation strong,
.atlas__analysis h3,
.atlas__dossier-head h3 {
  margin: 0;
  color: var(--campus-ink);
}

.atlas__recommendation span,
.atlas__recommendation em,
.atlas__dossier-head span {
  color: var(--text-tertiary);
  font-size: 0.8rem;
  font-style: normal;
}

.atlas__dossier-head {
  display: grid;
  gap: 0.24rem;
  margin-bottom: 0.8rem;
}

.atlas__dossier-item dd {
  font-size: 0.9rem;
  font-weight: 600;
}

.atlas__analysis--danger {
  background: rgba(181, 82, 67, 0.06);
  border-color: rgba(181, 82, 67, 0.16);
}

.atlas__analysis--warning {
  background: rgba(196, 143, 66, 0.08);
  border-color: rgba(196, 143, 66, 0.18);
}

.atlas__alignment-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  min-height: 360px;
}

.atlas__alignment-metrics {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.atlas__metric {
  display: grid;
  gap: 0.4rem;
  padding: 1.1rem;
}

.atlas__metric span {
  color: rgba(96, 72, 61, 0.78);
  font-size: 0.8rem;
  font-weight: 700;
}

.atlas__metric strong {
  color: var(--campus-ink);
  font-size: 2rem;
  line-height: 1;
}

.atlas__metric--course {
  background-color: rgba(127, 63, 47, 0.08);
}

.atlas__metric--concept {
  background-color: rgba(81, 103, 70, 0.1);
}

.atlas__metric--requirement {
  background-color: rgba(168, 117, 45, 0.12);
}

.atlas__alignment-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@keyframes atlas-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1200px) {
  .atlas__layout,
  .atlas__workspace {
    grid-template-columns: 1fr;
  }

  .atlas__rail,
  .atlas__inspectors {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }
}

@media (max-width: 900px) {
  .atlas__toolbar,
  .atlas__alignment-metrics,
  .atlas__alignment-grid {
    grid-template-columns: 1fr;
  }

  .atlas__meta {
    justify-items: start;
  }

  .atlas__canvas-shell,
  .atlas__workspace-empty {
    min-height: 600px;
    height: min(720px, 68vh);
  }

  .atlas__svg {
    height: 100%;
  }
}

@media (max-width: 640px) {
  .atlas__topbar,
  .atlas__panel,
  .atlas__metric {
    padding: 0.9rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .atlas__spinner,
  .atlas__tab,
  .atlas__action,
  .atlas__filter,
  .atlas__density-chip,
  .atlas__preset,
  .atlas__recommendation {
    animation: none;
    transition: none;
  }
}
</style>
