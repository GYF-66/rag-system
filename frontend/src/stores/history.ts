import { defineStore } from 'pinia';
import type { ChatHistory, ChatMessage, HistoryGroup } from '@/types';

const STORAGE_KEY = 'chat_history';

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function generateTitle(messages: ChatMessage[]): string {
  const firstUserMessage = messages.find((message) => message.role === 'user');
  if (!firstUserMessage) {
    return '新对话';
  }

  return firstUserMessage.content.slice(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '');
}

function loadFromStorage(): ChatHistory[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveToStorage(items: ChatHistory[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export const useHistoryStore = defineStore('history', {
  state: () => ({
    items: loadFromStorage() as ChatHistory[],
    searchQuery: '',
  }),

  getters: {
    filteredItems(state): ChatHistory[] {
      if (!state.searchQuery.trim()) {
        return state.items;
      }

      const query = state.searchQuery.toLowerCase();
      return state.items.filter(
        (item) => item.title.toLowerCase().includes(query) || item.messages.some((message) => message.content.toLowerCase().includes(query)),
      );
    },

    groupedItems(): HistoryGroup[] {
      const filtered = this.filteredItems;
      if (!filtered.length) {
        return [];
      }

      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const yesterday = today - 86400000;
      const weekAgo = today - 7 * 86400000;

      const groups: Record<string, ChatHistory[]> = {
        今天: [],
        昨天: [],
        '最近 7 天': [],
        更早: [],
      };

      for (const item of filtered) {
        const timestamp = new Date(item.updatedAt).getTime();
        if (timestamp >= today) {
          groups['今天'].push(item);
        } else if (timestamp >= yesterday) {
          groups['昨天'].push(item);
        } else if (timestamp >= weekAgo) {
          groups['最近 7 天'].push(item);
        } else {
          groups['更早'].push(item);
        }
      }

      return Object.entries(groups)
        .filter(([, items]) => items.length > 0)
        .map(([label, items]) => ({ label, items }));
    },

    totalCount(state): number {
      return state.items.length;
    },
  },

  actions: {
    saveConversation(messages: ChatMessage[], existingId?: string): string {
      const now = new Date().toISOString();

      if (existingId) {
        const index = this.items.findIndex((item) => item.id === existingId);
        if (index !== -1) {
          this.items[index].messages = [...messages];
          this.items[index].title = generateTitle(messages);
          this.items[index].updatedAt = now;
          this.persist();
          return existingId;
        }
      }

      const history: ChatHistory = {
        id: generateId(),
        title: generateTitle(messages),
        messages: [...messages],
        createdAt: now,
        updatedAt: now,
      };

      this.items.unshift(history);
      this.persist();
      return history.id;
    },

    deleteItem(id: string) {
      this.items = this.items.filter((item) => item.id !== id);
      this.persist();
    },

    clearAll() {
      this.items = [];
      this.persist();
    },

    getItem(id: string): ChatHistory | undefined {
      return this.items.find((item) => item.id === id);
    },

    renameItem(id: string, title: string) {
      const item = this.items.find((historyItem) => historyItem.id === id);
      if (item) {
        item.title = title;
        this.persist();
      }
    },

    persist() {
      saveToStorage(this.items);
    },
  },
});
