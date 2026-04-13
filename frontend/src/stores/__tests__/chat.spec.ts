import { createPinia, setActivePinia } from 'pinia';

import { apiClient } from '@/services/api';
import httpClient from '@/services/httpClient';
import { useChatStore } from '@/stores/chat';

vi.mock('@/services/httpClient', () => ({
  __esModule: true,
  default: {
    post: vi.fn(),
  },
}));

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api');
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      streamChat: vi.fn(),
    },
  };
});

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
    const result = await store.sendChat('  什么是培养目标？ ');

    expect(httpClient.post).toHaveBeenCalledWith(
      '/api/chat',
      expect.objectContaining({
        message: '什么是培养目标？',
        enable_thinking: true,
      }),
      expect.any(Object),
    );
    expect(result?.session_id).toBe('session-1');
    expect(store.conversationId).toBe('session-1');
    expect(store.messages).toHaveLength(2);
    expect(store.messages[1].sources?.[0].section).toBe('培养目标');
  });

  it('streams assistant responses into a single placeholder message', async () => {
    vi.mocked(apiClient.streamChat).mockImplementation(async (_payload, handlers) => {
      await handlers.metadata?.({
        request_id: 'req-stream-success',
        session_id: 'stream-session',
        sources: [],
        metadata: {
          request_id: 'req-stream-success',
          retrieval_method: 'hybrid',
          adaptive_route: 'standard',
          source_count: 2,
        },
      });
      await handlers.token?.({ content: '这是' });
      await handlers.token?.({ content: '流式回答' });
      await handlers.reflection?.({
        request_id: 'req-stream-success',
        status: 'supported',
        confidence: 0.92,
        issues: [],
        revision_applied: false,
      });
      await handlers.thinking?.({
        query_analysis: { step_name: '问题理解', reasoning: '已完成问题理解' },
        retrieval: { step_name: '证据检索', reasoning: '已完成证据检索' },
        reranking: { step_name: '上下文整理', reasoning: '已完成上下文整理' },
        reasoning: { step_name: '回答生成', reasoning: '这是流式回答' },
        reflection: { step_name: 'Self-RAG 校验', reasoning: '一致' },
        reflection_result: {
          status: 'supported',
          confidence: 0.92,
          issues: [],
          revision_applied: false,
        },
      });
      await handlers.done?.({ request_id: 'req-stream-success', total_duration_ms: 320 });
    });

    const store = useChatStore();
    const result = await store.sendStreamingChat('流式问题');

    expect(result?.session_id).toBe('stream-session');
    expect(store.messages).toHaveLength(2);
    expect(store.messages[1].content).toBe('这是流式回答');
    expect(store.messages[1].streamStatus).toBe('done');
    expect(store.messages[1].thinkingProcess?.reasoning?.reasoning).toBe('这是流式回答');
    expect(store.messages[1].metadata?.request_id).toBe('req-stream-success');
  });

  it('stores the last attempted message and error on failure', async () => {
    vi.mocked(httpClient.post).mockRejectedValue(new Error('接口异常'));

    const store = useChatStore();

    await expect(store.sendChat('重试问题')).rejects.toThrow('接口异常');

    expect(store.lastAttemptedMessage).toBe('重试问题');
    expect(store.error).toBe('接口异常');
    expect(store.messages[0].content).toBe('重试问题');
  });

  it('marks streaming steps as warning when the SSE channel fails', async () => {
    vi.mocked(apiClient.streamChat).mockImplementation(async (_payload, handlers) => {
      await handlers.metadata?.({
        request_id: 'req-stream-error',
        session_id: 'stream-error-session',
        sources: [],
        metadata: { request_id: 'req-stream-error' },
      });
      await handlers.token?.({ content: '部分回答' });
      await handlers.error?.({ message: '流式异常', request_id: 'req-stream-error' });
    });

    const store = useChatStore();

    await expect(store.sendStreamingChat('流式异常')).rejects.toThrow('流式异常');

    expect(store.error).toBe('流式异常');
    expect(store.messages).toHaveLength(2);
    expect(store.messages[1].streamStatus).toBe('error');
    expect(store.messages[1].thinkingStatusMap?.reasoning).toBe('warning');
    expect(store.messages[1].thinkingStatusMap?.reflection).toBe('warning');
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
