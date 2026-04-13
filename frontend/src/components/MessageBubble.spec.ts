import { mount } from '@vue/test-utils';

import MessageBubble from './MessageBubble.vue';

describe('MessageBubble', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('renders user messages as plain text', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'user-1',
          role: 'user',
          content: '用户消息',
          createdAt: new Date().toISOString(),
        },
      },
    });

    expect(wrapper.get('[data-testid="message-bubble"]').text()).toContain('用户消息');
  });

  it('renders assistant answers with typewriter typography and source snippets', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'assistant-1',
          role: 'assistant',
          content: '1. 核心课程覆盖机器学习。\n2. 实践环节包含课程实验。',
          createdAt: new Date().toISOString(),
          sources: [
            {
              id: 'source-1',
              text: '课程体系包括数学基础、编程基础和机器学习核心课程。实践教学包含课程实验和毕业设计。',
              char_count: 40,
              section: '课程体系',
              similarity: 0.91,
              rerank_score: 0.88,
            },
          ],
        },
      },
    });

    expect(wrapper.get('[data-testid="answer-block"]').text()).toContain('核心课程覆盖机器学习');
    expect(wrapper.get('[data-testid="answer-rich-text"]').classes()).toContain('markdown-typewriter');
    expect(wrapper.get('[data-testid="source-block"]').text()).toContain('课程体系');
    expect(wrapper.get('[data-testid="source-snippet"]').attributes('class')).toContain('whitespace-pre-line');
  });

  it('shows an answer placeholder while streaming before content arrives', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'assistant-streaming',
          role: 'assistant',
          content: '',
          createdAt: new Date().toISOString(),
          streaming: true,
          streamStatus: 'streaming',
        },
      },
    });

    expect(wrapper.get('[data-testid="answer-placeholder"]').text()).toContain('正在整理回答');
    expect(wrapper.get('[data-testid="streaming-cursor"]').exists()).toBe(true);
  });

  it('copies assistant content when copy button is pressed', async () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'assistant-2',
          role: 'assistant',
          content: '复制这段内容',
          createdAt: new Date().toISOString(),
        },
      },
    });

    await wrapper.get('[data-testid="copy-answer"]').trigger('click');

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('复制这段内容');
  });

  it('opens thinking details from CRAG and Self-RAG pills', async () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'assistant-3',
          role: 'assistant',
          content: '这是带有技术细节的回答。',
          createdAt: new Date().toISOString(),
          metadata: {
            cot_used: true,
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
          thinkingProcess: {
            reasoning: {
              step_id: 4,
              step_name: '回答生成',
              description: '按证据生成回答',
              reasoning: '正在组织答案内容。',
            },
          },
        },
      },
    });

    expect(wrapper.get('[data-testid="crag-pill"]').text()).toContain('0.57 · refine');
    expect(wrapper.get('[data-testid="self-rag-pill"]').text()).toContain('81% · partially_supported');
    expect(wrapper.get('[data-testid="thinking-pill"]').text()).toContain('查看思考');

    await wrapper.get('[data-testid="crag-pill"]').trigger('click');

    expect(wrapper.get('[data-testid="thinking-process-toggle"]').text()).toContain('收起');
    expect(wrapper.get('[data-testid="self-rag-method-card"]').text()).toContain('Self-RAG 技术方法');
  });
});
