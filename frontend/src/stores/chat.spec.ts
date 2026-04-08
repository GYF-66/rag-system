import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useChatStore } from './chat';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

describe('Chat Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('初始状态正确', () => {
    const store = useChatStore();
    expect(store.messages).toEqual([]);
    expect(store.conversationId).toBe('');
    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.historyId).toBeNull();
  });

  it('hasMessages getter 正确', () => {
    const store = useChatStore();
    expect(store.hasMessages).toBe(false);
  });

  it('addUserMessage 添加用户消息', () => {
    const store = useChatStore();
    store.addUserMessage('测试消息');

    expect(store.messages).toHaveLength(1);
    expect(store.messages[0].role).toBe('user');
    expect(store.messages[0].content).toBe('测试消息');
    expect(store.messages[0].id).toBeDefined();
    expect(store.messages[0].createdAt).toBeDefined();
  });

  it('addAssistantMessage 添加助手消息及来源', () => {
    const store = useChatStore();
    const sources = [{ id: '1', text: '来源文本', char_count: 10, similarity: 0.9 }];
    store.addAssistantMessage('回复内容', sources);

    expect(store.messages).toHaveLength(1);
    expect(store.messages[0].role).toBe('assistant');
    expect(store.messages[0].content).toBe('回复内容');
    expect(store.messages[0].sources).toEqual(sources);
  });

  it('clearMessages 清空消息', () => {
    const store = useChatStore();
    store.addUserMessage('消息1');
    store.addAssistantMessage('回复1');
    expect(store.messages).toHaveLength(2);

    store.clearMessages();
    expect(store.messages).toEqual([]);
    expect(store.conversationId).toBe('');
    expect(store.historyId).toBeNull();
  });

  it('lastMessage getter 返回最后一条消息', () => {
    const store = useChatStore();
    store.addUserMessage('第一条');
    store.addAssistantMessage('第二条');
    expect(store.lastMessage.content).toBe('第二条');
  });

  it('消息 id 唯一', () => {
    const store = useChatStore();
    store.addUserMessage('消息1');
    store.addUserMessage('消息2');
    expect(store.messages[0].id).not.toBe(store.messages[1].id);
  });

  it('newConversation 开始新对话', () => {
    const store = useChatStore();
    store.addUserMessage('旧消息');
    store.newConversation();

    expect(store.messages).toEqual([]);
    expect(store.historyId).toBeNull();
    expect(store.error).toBeNull();
  });

  it('saveDraft 持久化到 localStorage', () => {
    const store = useChatStore();
    store.addUserMessage('草稿消息');

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'chat_draft_messages',
      expect.any(String),
    );
  });

  it('sendChat 设置 loading 状态并处理错误', async () => {
    const store = useChatStore();

    globalThis.fetch = vi.fn(async () => {
      throw new Error('Network error');
    });

    try {
      await store.sendChat('测试');
    } catch {
      // 预期失败
    }

    expect(store.isLoading).toBe(false);
    expect(store.error).toBe('Network error');
    expect(store.messages).toHaveLength(1); // 用户消息已添加
  });

  it('sendChat 成功时添加助手消息', async () => {
    const store = useChatStore();

    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        response: 'AI回复',
        session_id: 'sess-1',
        sources: [],
        timestamp: new Date().toISOString(),
      }),
    })) as unknown as typeof fetch;

    await store.sendChat('你好');

    expect(store.messages).toHaveLength(2);
    expect(store.messages[0].role).toBe('user');
    expect(store.messages[1].role).toBe('assistant');
    expect(store.messages[1].content).toBe('AI回复');
    expect(store.isLoading).toBe(false);
  });
});
