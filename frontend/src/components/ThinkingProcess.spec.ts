import { mount } from '@vue/test-utils';

import ThinkingProcess from './ThinkingProcess.vue';

describe('ThinkingProcess', () => {
  it('renders CRAG and Self-RAG method cards with dynamic details', () => {
    const wrapper = mount(ThinkingProcess, {
      props: {
        expanded: true,
        answerContent: '人工智能专业的核心课程包括机器学习、深度学习和实践教学环节。',
        process: {
          query_analysis: {
            step_id: 1,
            step_name: '问题理解',
            description: '规范化问题并识别意图',
            reasoning: '识别为培养方案查询，并抽取课程与实践两个意图。',
          },
          retrieval: {
            step_id: 2,
            step_name: '证据检索',
            description: '召回相关培养方案片段',
            reasoning: '召回 6 条相关片段。',
            output_data: {
              retrieved_count: 6,
            },
          },
          reranking: {
            step_id: 3,
            step_name: '上下文整理',
            description: '按证据质量重排',
            reasoning: '最终保留 4 条高相关证据。',
            output_data: {
              final_count: 4,
              crag_score: 0.57,
            },
          },
          reasoning: {
            step_id: 4,
            step_name: '回答生成',
            description: '按证据组织回答',
            reasoning: '正在生成回答。',
          },
          reflection: {
            step_id: 5,
            step_name: 'Self-RAG 校验',
            description: '核查回答与证据一致性',
            reasoning: '发现一条需要补充说明的问题。',
          },
          reflection_result: {
            status: 'partially_supported',
            confidence: 0.81,
            issues: ['缺少对实践学分比例的直接证据说明。'],
            revision_applied: true,
          },
          total_duration_ms: 320,
        },
        metadata: {
          adaptive_route: 'standard',
          source_count: 4,
          query_rewrite: {
            original_query: '人工智能专业课程和实践环节怎么安排？',
            normalized_query: '人工智能专业课程安排与实践环节说明',
          },
          crag_evaluation: {
            mode: 'online_heuristic',
            quality_score: 0.57,
            action: 'refine',
            details: {
              similarity: 0.72,
              keyword_coverage: 0.62,
              diversity: 0.41,
              completeness: 0.45,
            },
            thresholds: {
              low: 0.3,
              high: 0.6,
            },
            correction_hints: ['expand_top_k', 'rewrite_query'],
            correction: {
              corrected: true,
              actions_taken: ['keyword_supplement'],
            },
          },
          self_rag: {
            mode: 'llm_reflection',
            status: 'partially_supported',
            confidence: 0.81,
            issues_count: 1,
            revision_applied: true,
            evidence_count: 4,
          },
        },
      },
    });

    expect(wrapper.text()).toContain('CRAG 技术方法');
    expect(wrapper.text()).toContain('Self-RAG 技术方法');
    expect(wrapper.text()).toContain('0.35 similarity + 0.30 keyword_coverage + 0.15 diversity + 0.20 completeness');
    expect(wrapper.get('[data-testid="crag-metric-similarity"]').attributes('style')).toContain('72%');
    expect(wrapper.get('[data-testid="self-rag-status"]').text()).toContain('部分支持');
    expect(wrapper.get('[data-testid="reflection-issues"]').text()).toContain('缺少对实践学分比例的直接证据说明');
  });

  it('shows waiting Self-RAG status during streaming before reflection arrives', () => {
    const wrapper = mount(ThinkingProcess, {
      props: {
        expanded: true,
        streamStatus: 'streaming',
        answerContent: '正在输出回答',
        stepStatuses: {
          query_analysis: 'done',
          retrieval: 'done',
          reranking: 'done',
          reasoning: 'streaming',
          reflection: 'waiting',
        },
        process: {
          query_analysis: {
            step_id: 1,
            step_name: '问题理解',
            description: '完成问题分析',
            reasoning: '问题已规范化。',
          },
          reasoning: {
            step_id: 4,
            step_name: '回答生成',
            description: '继续输出回答',
            reasoning: '回答正在流式输出。',
          },
        },
        metadata: {
          self_rag: {
            mode: 'llm_reflection',
            status: 'waiting',
            confidence: null,
            issues_count: 0,
            revision_applied: false,
            evidence_count: 3,
          },
        },
      },
    });

    expect(wrapper.get('[data-testid="trace-status"]').text()).toContain('进行中');
    expect(wrapper.get('[data-testid="self-rag-status"]').text()).toContain('等待校验');
    expect(wrapper.text()).toContain('等待 Self-RAG 校验');
  });
});
