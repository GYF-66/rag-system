import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useHistoryStore } from './history';
import type { ChatMessage } from '@/types';

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

function makeMessages(content: string): ChatMessage[] {
  return [
    { id: '1', role: 'user', content },
    { id: '2', role: 'assistant', content: `回复: ${content}` },
  ];
}

describe('History Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('初始状态为空', () => {
    const store = useHistoryStore();
    expect(store.items).toEqual([]);
    expect(store.totalCount).toBe(0);
    expect(store.searchQuery).toBe('');
  });

  it('saveConversation 保存对话', () => {
    const store = useHistoryStore();
    const messages = makeMessages('你好');
    const id = store.saveConversation(messages);

    expect(id).toBeDefined();
    expect(store.items).toHaveLength(1);
    expect(store.items[0].title).toContain('你好');
    expect(store.items[0].messages).toHaveLength(2);
    expect(store.totalCount).toBe(1);
  });

  it('saveConversation 更新已有对话', () => {
    const store = useHistoryStore();
    const id = store.saveConversation(makeMessages('第一轮'));
    expect(store.items).toHaveLength(1);

    const newMessages = [...makeMessages('第一轮'), ...makeMessages('第二轮')];
    store.saveConversation(newMessages, id);

    expect(store.items).toHaveLength(1);
    expect(store.items[0].messages).toHaveLength(4);
  });

  it('deleteItem 删除指定对话', () => {
    const store = useHistoryStore();
    const id1 = store.saveConversation(makeMessages('对话1'));
    const id2 = store.saveConversation(makeMessages('对话2'));
    expect(store.items).toHaveLength(2);

    store.deleteItem(id1);
    expect(store.items).toHaveLength(1);
    expect(store.items[0].id).toBe(id2);
  });

  it('clearAll 清空所有历史', () => {
    const store = useHistoryStore();
    store.saveConversation(makeMessages('对话1'));
    store.saveConversation(makeMessages('对话2'));
    expect(store.items).toHaveLength(2);

    store.clearAll();
    expect(store.items).toHaveLength(0);
    expect(store.totalCount).toBe(0);
  });

  it('getItem 获取指定对话', () => {
    const store = useHistoryStore();
    const id = store.saveConversation(makeMessages('查找我'));

    const item = store.getItem(id);
    expect(item).toBeDefined();
    expect(item?.title).toContain('查找我');
  });

  it('getItem 返回 undefined 当 id 不存在', () => {
    const store = useHistoryStore();
    expect(store.getItem('nonexistent')).toBeUndefined();
  });

  it('renameItem 重命名对话', () => {
    const store = useHistoryStore();
    const id = store.saveConversation(makeMessages('原始标题'));
    store.renameItem(id, '新标题');

    expect(store.items[0].title).toBe('新标题');
  });

  it('filteredItems 按关键词过滤', () => {
    const store = useHistoryStore();
    store.saveConversation(makeMessages('奖学金申请'));
    store.saveConversation(makeMessages('宿舍管理'));

    store.searchQuery = '奖学金';
    expect(store.filteredItems).toHaveLength(1);
    expect(store.filteredItems[0].title).toContain('奖学金');

    store.searchQuery = '';
    expect(store.filteredItems).toHaveLength(2);
  });

  it('groupedItems 按时间分组', () => {
    const store = useHistoryStore();
    store.saveConversation(makeMessages('今天的对话'));

    const groups = store.groupedItems;
    expect(groups.length).toBeGreaterThan(0);
    expect(groups[0].label).toBe('今天');
    expect(groups[0].items).toHaveLength(1);
  });

  it('persist 保存到 localStorage', () => {
    const store = useHistoryStore();
    store.saveConversation(makeMessages('持久化测试'));

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'chat_history',
      expect.any(String),
    );
  });

  it('新保存的对话在列表最前面', () => {
    const store = useHistoryStore();
    store.saveConversation(makeMessages('第一个'));
    store.saveConversation(makeMessages('第二个'));

    expect(store.items[0].title).toContain('第二个');
    expect(store.items[1].title).toContain('第一个');
  });
});
