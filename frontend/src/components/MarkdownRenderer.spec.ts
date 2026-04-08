import { mount } from '@vue/test-utils';

import MarkdownRenderer from './MarkdownRenderer.vue';

describe('MarkdownRenderer', () => {
  it('splits dense chinese paragraphs into multiple paragraphs', () => {
    const wrapper = mount(MarkdownRenderer, {
      props: {
        content: '人工智能专业培养强调数学基础与工程能力。课程体系覆盖机器学习、深度学习和数据分析。实践教学包括课程实验、课程设计和毕业设计。学生需要具备解决复杂工程问题的能力。',
      },
    });

    expect(wrapper.findAll('p').length).toBeGreaterThan(1);
  });

  it('recognizes inline ordered items as a markdown list', () => {
    const wrapper = mount(MarkdownRenderer, {
      props: {
        content: '回答可以概括为：1. 核心课程覆盖机器学习。2. 实践环节包含课程实验。3. 毕业设计安排在高年级。',
      },
    });

    const items = wrapper.findAll('li');
    expect(items).toHaveLength(3);
    expect(items[0].text()).toContain('核心课程');
  });

  it('separates bold pseudo headings from body content', () => {
    const wrapper = mount(MarkdownRenderer, {
      props: {
        content: '**培养目标** 学生应具备数学基础。学生应具备工程实践能力。',
      },
    });

    expect(wrapper.html()).toContain('<strong>培养目标</strong>');
    expect(wrapper.findAll('p').length).toBeGreaterThan(1);
  });
});
