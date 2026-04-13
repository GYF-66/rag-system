import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';

import Sidebar from './Sidebar.vue';
import { useAuthStore } from '@/stores/auth';

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ name: 'manual', path: '/manual' }),
}));

vi.mock('@/router', () => ({
  DEMO_MODE: true,
}));

describe('Sidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    push.mockReset();
  });

  it('shows demo-safe navigation by default', () => {
    const wrapper = mount(Sidebar);

    expect(wrapper.text()).toContain('发起新问答');
    expect(wrapper.text()).toContain('安信工 AI 助手');
    expect(wrapper.text()).toContain('首页');
    expect(wrapper.text()).not.toContain('会话历史');
    expect(wrapper.text()).not.toContain('知识空间');
  });

  it('navigates to the graph workspace when clicking the graph menu item', async () => {
    const wrapper = mount(Sidebar);
    const graphButton = wrapper.findAll('button').find((button) => button.text().includes('知识图谱'));

    expect(graphButton).toBeTruthy();
    await graphButton!.trigger('click');

    expect(push).toHaveBeenCalledWith('/graph');
  });

  it('emits new-chat when the primary button is clicked', async () => {
    const wrapper = mount(Sidebar);

    await wrapper.get('button[title="新建对话"]').trigger('click');

    expect(wrapper.emitted('new-chat')).toBeTruthy();
    expect(push).toHaveBeenCalledWith('/manual');
  });

  it('emits a quick-question when selecting a sample prompt', async () => {
    const wrapper = mount(Sidebar);
    const quickQuestionButton = wrapper.findAll('button').find((button) => button.text().includes('人工智能专业的核心课程与实践环节如何安排'));

    expect(quickQuestionButton).toBeTruthy();
    await quickQuestionButton!.trigger('click');

    expect(wrapper.emitted('quick-question')?.[0]).toEqual(['人工智能专业的核心课程与实践环节如何安排？']);
  });

  it('shows logout action for authenticated users', async () => {
    const authStore = useAuthStore();
    authStore.isAuthenticated = true;
    authStore.accessToken = 'token';

    const wrapper = mount(Sidebar);
    const menuToggle = wrapper.findAll('button').at(-1);

    await menuToggle!.trigger('click');

    expect(wrapper.text()).toContain('退出登录');
  });
});
