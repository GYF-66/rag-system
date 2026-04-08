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

  it('renders assistant answer blocks with lists and formatted source snippets', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          id: 'assistant-1',
          role: 'assistant',
          content: '回答可以概括为：1. 核心课程覆盖机器学习。2. 实践环节包含课程实验。',
          createdAt: new Date().toISOString(),
          sources: [
            {
              id: 'source-1',
              text: '课程体系包括数学基础、编程基础和机器学习核心课程。实践教学包括课程实验、课程设计和毕业设计。',
              char_count: 28,
              section: '课程体系',
              similarity: 0.91,
              rerank_score: 0.88,
            },
          ],
        },
      },
    });

    expect(wrapper.get('[data-testid="answer-block"]').text()).toContain('回答可以概括为');
    expect(wrapper.findAll('[data-testid="answer-block"] li')).toHaveLength(2);
    expect(wrapper.get('[data-testid="source-block"]').text()).toContain('课程体系');
    expect(wrapper.findAll('[data-testid="source-card"]')).toHaveLength(1);
    expect(wrapper.get('[data-testid="source-snippet"]').attributes('class')).toContain('whitespace-pre-line');
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
});
