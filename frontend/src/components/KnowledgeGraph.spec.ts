import { flushPromises, mount } from '@vue/test-utils';

import KnowledgeGraph from './KnowledgeGraph.vue';
import { apiClient } from '@/services/api';

const baseGraph = {
  nodes: [
    {
      id: 'course-1',
      label: '机器学习',
      type: 'course',
      code: 'AI301',
      semester: '第 5 学期',
      credits: 3,
      community: 1,
      category: '核心课',
      bloom_level: '应用',
    },
    {
      id: 'course-2',
      label: '高等数学',
      type: 'course',
      code: 'MATH101',
      semester: '第 1 学期',
      credits: 4,
      community: 1,
      category: '基础课',
    },
    {
      id: 'course-3',
      label: '深度学习',
      type: 'course',
      code: 'AI401',
      semester: '第 6 学期',
      credits: 3,
      community: 1,
      category: '方向课',
    },
    {
      id: 'course-4',
      label: '数据挖掘',
      type: 'course',
      code: 'AI302',
      semester: '第 5 学期',
      credits: 2,
      community: 1,
      category: '方向课',
    },
    {
      id: 'concept-1',
      label: '梯度下降',
      type: 'concept',
      community: 1,
      category: '数学基础',
    },
  ],
  edges: [
    {
      source: 'course-2',
      target: 'course-1',
      type: 'prerequisite',
      label: '先修',
    },
    {
      source: 'course-1',
      target: 'course-3',
      type: 'leads_to',
      label: '后续',
    },
    {
      source: 'course-1',
      target: 'course-4',
      type: 'related',
      label: '关联',
    },
    {
      source: 'course-1',
      target: 'concept-1',
      type: 'contains',
      label: '包含',
    },
  ],
  communities: { 1: '智能计算' },
  stats: {
    node_count: 5,
    edge_count: 4,
    community_count: 1,
    node_types: {
      course: 4,
      concept: 1,
    },
  },
};

const emptyGraph = {
  nodes: [],
  edges: [],
  communities: {},
  stats: {
    node_count: 0,
    edge_count: 0,
    community_count: 0,
    node_types: {},
  },
};

const searchResult = {
  nodes: [baseGraph.nodes[0], baseGraph.nodes[4]],
  edges: [baseGraph.edges[3]],
  summary: '已找到课程与知识点的直接关联',
  paths: [{ from: '机器学习', to: '梯度下降', path: '机器学习 -> 梯度下降', length: 1 }],
  seed_count: 1,
  total_nodes: 2,
  total_edges: 1,
};

const alignmentData = {
  total_courses: 24,
  total_concepts: 118,
  total_requirements: 12,
  requirement_coverage: {
    R1: ['机器学习', '数据挖掘'],
  },
  gaps: [
    {
      type: 'gap',
      requirement: '工程实践能力',
      supporting_courses: ['机器学习'],
      severity: 'high',
      suggestion: '增加跨课程项目训练与实验验证环节。',
    },
  ],
  overlaps: [
    {
      type: 'overlap',
      concept: '监督学习',
      courses: ['机器学习', '数据挖掘'],
      count: 2,
      suggestion: '合并重复讲解并把应用案例分流到不同课程。',
    },
  ],
  orphans: [
    {
      type: 'course',
      course: '学术写作',
      suggestion: '补充与毕业要求和能力指标的明确映射。',
    },
  ],
  gap_count: 1,
  overlap_count: 1,
};

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getGraphVisualization: vi.fn(),
      searchGraph: vi.fn(),
      getAlignmentAnalysis: vi.fn(),
    },
  };
});

function mountGraph() {
  return mount(KnowledgeGraph);
}

describe('KnowledgeGraph', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.getGraphVisualization).mockResolvedValue(baseGraph);
    vi.mocked(apiClient.searchGraph).mockResolvedValue(searchResult);
    vi.mocked(apiClient.getAlignmentAnalysis).mockResolvedValue(alignmentData);
  });

  it('renders the graph mode with a search-first empty workspace after loading', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    expect(wrapper.get('[data-testid="graph-canvas-card"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="graph-search-empty"]').text()).toContain('先搜索一门课程');
    expect(wrapper.get('[data-testid="graph-node-empty"]').text()).toContain('课程档案');
    expect(wrapper.emitted('state-change')?.at(-1)?.[0]).toMatchObject({
      nodeCount: 5,
      edgeCount: 4,
      communityCount: 1,
      filterLabel: '全部节点',
      activeTab: 'graph',
    });
  });

  it('shows a loading overlay while the graph request is pending', async () => {
    const deferred = createDeferred<typeof baseGraph>();
    vi.mocked(apiClient.getGraphVisualization).mockReturnValueOnce(deferred.promise);

    const wrapper = mountGraph();
    expect(wrapper.get('[data-testid="graph-loading"]').exists()).toBe(true);

    deferred.resolve(baseGraph);
    await flushPromises();
  });

  it('shows an error overlay when the graph request fails', async () => {
    vi.mocked(apiClient.getGraphVisualization).mockRejectedValueOnce(new Error('graph failed'));

    const wrapper = mountGraph();
    await flushPromises();

    expect(wrapper.get('[data-testid="graph-error"]').text()).toContain('graph failed');
  });

  it('shows an empty state when the graph has no nodes', async () => {
    vi.mocked(apiClient.getGraphVisualization).mockResolvedValueOnce(emptyGraph);

    const wrapper = mountGraph();
    await flushPromises();

    expect(wrapper.get('[data-testid="graph-empty"]').text()).toContain('当前筛选范围暂时没有图谱数据');
  });

  it('searches for a course and renders the local course map', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    await wrapper.get('input').setValue('机器学习');
    await wrapper.get('[data-testid="graph-toolbar"] button').trigger('click');
    await flushPromises();

    expect(apiClient.searchGraph).toHaveBeenCalledWith('机器学习', 2, 30);
    expect(wrapper.text()).toContain('AI301');
    expect(wrapper.text()).toContain('高等数学');
    expect(wrapper.text()).toContain('深度学习');
    expect(wrapper.text()).toContain('知识点：梯度下降');
  });

  it('reloads the graph when switching the data view filter', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    const courseFilter = wrapper.findAll('[data-testid="graph-filters-panel"] button').find((button) => button.text().includes('课程'));
    expect(courseFilter).toBeDefined();

    await courseFilter!.trigger('click');
    await flushPromises();

    expect(courseFilter!.attributes('data-active')).toBe('true');
    expect(apiClient.getGraphVisualization).toHaveBeenLastCalledWith('course');
  });

  it('switches focus when clicking a recommended related course', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    await wrapper.get('input').setValue('机器学习');
    await wrapper.get('[data-testid="graph-toolbar"] button').trigger('click');
    await flushPromises();

    const relatedButton = wrapper.findAll('button').find((button) => button.text().includes('数据挖掘'));
    expect(relatedButton).toBeDefined();

    await relatedButton!.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('AI302');
    expect(wrapper.text()).toContain('数据挖掘');
  });

  it('expands only the current neighborhood when showing details', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    await wrapper.get('input').setValue('机器学习');
    await wrapper.get('[data-testid="graph-toolbar"] button').trigger('click');
    await flushPromises();

    const before = wrapper.findAll('.atlas__node').length;
    const detailButton = wrapper.findAll('button').find((button) => button.text().includes('展开细节'));
    expect(detailButton).toBeDefined();

    await detailButton!.trigger('click');
    await flushPromises();

    const after = wrapper.findAll('.atlas__node').length;
    expect(after).toBeGreaterThan(before);
    expect(after - before).toBeLessThanOrEqual(2);
  });

  it('switches to alignment analysis and renders the diagnostics panel', async () => {
    const wrapper = mountGraph();
    await flushPromises();

    const analysisButton = wrapper.findAll('button').find((button) => button.text().includes('培养方案分析'));
    expect(analysisButton).toBeDefined();

    await analysisButton!.trigger('click');
    await flushPromises();

    expect(apiClient.getAlignmentAnalysis).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[data-testid="alignment-panel"]').text()).toContain('知识断层');
    expect(wrapper.text()).toContain('工程实践能力');
    expect(wrapper.text()).toContain('孤立课程提醒');
  });
});
