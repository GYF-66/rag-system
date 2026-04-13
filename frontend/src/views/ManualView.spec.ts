import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { reactive } from 'vue';

import ManualView from './ManualView.vue';
import { apiClient } from '@/services/api';

const replaceMock = vi.fn();
const routeState = reactive<{ path: string; query: Record<string, unknown> }>({
  path: '/manual',
  query: {},
});

vi.mock('vue-router', () => ({
  createRouter: () => ({
    beforeEach: vi.fn(),
  }),
  createWebHistory: vi.fn(),
  useRoute: () => routeState,
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      healthCheck: vi.fn(),
      streamChat: vi.fn(),
    },
  };
});

function mountView() {
  return shallowMount(ManualView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        Sidebar: true,
        TopNavbar: true,
        LibraryMasthead: true,
        MessageBubble: true,
        MobileNav: true,
      },
    },
  });
}

describe('ManualView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.clearAllMocks();
    routeState.path = '/manual';
    routeState.query = {};
  });

  it('shows empty state and input area on first render', async () => {
    vi.mocked(apiClient.healthCheck).mockResolvedValue({
      status: 'healthy',
      agent_name: 'backend',
      knowledge_base_loaded: true,
      total_chunks: 10,
      timestamp: new Date().toISOString(),
    });

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.get('[data-testid="manual-empty-state"]').text()).toContain('可解释的 RAG 链路');
    expect(wrapper.get('[data-testid="chat-input"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="chat-message-list"]').exists()).toBe(true);
  });

  it('sends a route-bootstrapped query only once', async () => {
    routeState.query = { q: 'RAG 如何减少幻觉？' };

    vi.mocked(apiClient.healthCheck).mockResolvedValue({
      status: 'healthy',
      agent_name: 'backend',
      knowledge_base_loaded: true,
      total_chunks: 10,
      timestamp: new Date().toISOString(),
    });

    vi.mocked(apiClient.streamChat).mockImplementation(async (_payload, handlers) => {
      await handlers.metadata?.({
        session_id: 'session-1',
        sources: [],
        metadata: {},
      });
      await handlers.token?.({ content: '这是回答' });
      await handlers.done?.({ total_duration_ms: 80 });
    });

    mountView();
    await flushPromises();
    await flushPromises();

    const calledMessages = vi.mocked(apiClient.streamChat).mock.calls.map(([payload]) => payload.message);
    expect(calledMessages.length).toBeGreaterThan(0);
    expect(new Set(calledMessages)).toEqual(new Set(['RAG 如何减少幻觉？']));
    expect(replaceMock).toHaveBeenCalled();
    expect(replaceMock).toHaveBeenLastCalledWith({ path: '/manual', query: {} });
  });

  it('keeps quick questions usable when health check fails', async () => {
    vi.mocked(apiClient.healthCheck).mockRejectedValue(new Error('health failed'));
    vi.mocked(apiClient.streamChat).mockImplementation(async (_payload, handlers) => {
      await handlers.metadata?.({
        session_id: 'session-2',
        sources: [],
        metadata: {},
      });
      await handlers.token?.({ content: '这是回答' });
      await handlers.done?.({ total_duration_ms: 60 });
    });

    const wrapper = mountView();
    await flushPromises();

    const status = wrapper.get('[data-testid="connection-status"]');
    expect(status.text()).toContain('仍可继续提问');
    expect(status.attributes('data-connected')).toBe('false');

    await wrapper.get('[data-testid="manual-quick-question"]').trigger('click');
    await flushPromises();

    expect(apiClient.streamChat).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[data-testid="connection-status"]').attributes('data-connected')).toBe('true');
  });
});
