import { createPinia, setActivePinia } from 'pinia';

import { useChatStore } from '@/stores/chat';
import httpClient from '@/services/httpClient';

vi.mock('@/services/httpClient', () => ({
  __esModule: true,
  default: {
    post: vi.fn(),
  },
}));

describe('Chat Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('initializes with empty state when there is no draft', () => {
    const store = useChatStore();

    expect(store.messages).toEqual([]);
    expect(store.conversationId).toBe('');
    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
  });

  it('adds messages with generated ids and timestamps', () => {
    const store = useChatStore();

    store.addAssistantMessage('你好');

    expect(store.messages).toHaveLength(1);
    expect(store.messages[0].id).toBeTruthy();
    expect(store.messages[0].createdAt).toMatch(/T/);
  });

  it('sends guest chat requests and appends assistant responses', async () => {
    vi.mocked(httpClient.post).mockResolvedValue({
      response: '这是回答',
      session_id: 'session-1',
      sources: [
        {
          id: 'source-1',
          text: '知识来源',
          char_count: 4,
          section: '培养目标',
          similarity: 0.8,
          rerank_score: 0.7,
        },
      ],
      timestamp: new Date().toISOString(),
      metadata: { demo_mode: true },
    });

    const store = useChatStore();
    const result = await store.sendChat('  什么是培养目标？  ');

    expect(httpClient.post).toHaveBeenCalledWith(
      '/api/chat',
      expect.objectContaining({
        message: '什么是培养目标？',
        enable_thinking: false,
      }),
      expect.any(Object),
    );
    expect(result?.session_id).toBe('session-1');
    expect(store.conversationId).toBe('session-1');
    expect(store.messages).toHaveLength(2);
    expect(store.messages[1].sources?.[0].section).toBe('培养目标');
  });

  it('stores the last attempted message and error on failure', async () => {
    vi.mocked(httpClient.post).mockRejectedValue(new Error('接口异常'));

    const store = useChatStore();

    await expect(store.sendChat('重试问题')).rejects.toThrow('接口异常');

    expect(store.lastAttemptedMessage).toBe('重试问题');
    expect(store.error).toBe('接口异常');
    expect(store.messages[0].content).toBe('重试问题');
  });

  it('starts a new conversation and clears persisted draft state', () => {
    const store = useChatStore();
    store.addUserMessage('旧消息');
    store.conversationId = 'session-old';
    store.saveDraft();

    store.newConversation();

    expect(store.messages).toEqual([]);
    expect(store.conversationId).toBe('');
    expect(localStorage.getItem('chat_draft_messages')).toBeNull();
  });
});
