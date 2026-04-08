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
    expect(wrapper.text()).toContain('专业学习工作台');
    expect(wrapper.text()).toContain('公共首页');
    expect(wrapper.text()).not.toContain('历史记录');
    expect(wrapper.text()).not.toContain('知识空间');
  });

  it('emits new-chat when the primary button is clicked', async () => {
    const wrapper = mount(Sidebar);

    await wrapper.get('button[title="新建对话"]').trigger('click');

    expect(wrapper.emitted('new-chat')).toBeTruthy();
    expect(push).toHaveBeenCalledWith('/manual');
  });

  it('emits a quick-question when selecting a sample prompt', async () => {
    const wrapper = mount(Sidebar);
    const quickQuestionButton = wrapper.findAll('button').find((button) => button.text().includes('人工智能专业的核心课程与实践如何安排'));

    expect(quickQuestionButton).toBeTruthy();
    await quickQuestionButton!.trigger('click');

    expect(wrapper.emitted('quick-question')?.[0]).toEqual(['人工智能专业的核心课程与实践如何安排？']);
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
