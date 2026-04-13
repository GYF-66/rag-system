import { shallowMount } from '@vue/test-utils';

import GraphView from './GraphView.vue';

describe('GraphView', () => {
  it('renders the knowledge map workspace shell', () => {
    const wrapper = shallowMount(GraphView, {
      global: {
        stubs: {
          Sidebar: true,
          TopNavbar: true,
          LibraryMasthead: {
            props: ['eyebrow', 'title'],
            template: '<div><span>{{ eyebrow }}</span><span>{{ title }}</span><slot /><slot name="aside" /></div>',
          },
          KnowledgeGraph: {
            template: '<div data-testid="knowledge-graph-stub">graph</div>',
          },
        },
      },
    });

    expect(wrapper.get('[data-testid="graph-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('知识图谱工作台');
    expect(wrapper.text()).toContain('Academic Knowledge Map');
    expect(wrapper.get('[data-testid="knowledge-graph-stub"]').exists()).toBe(true);
  });
});
