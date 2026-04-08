import { defineStore } from 'pinia';
import type { ChatMessage, ChatRequest, ChatResponse, KnowledgeChunk, PerspectiveChatResponse, PerspectiveResult } from '@/types';
import { useHistoryStore } from './history';
import httpClient from '@/services/httpClient';

const DRAFT_KEY = 'chat_draft_messages';
const DRAFT_CID_KEY = 'chat_draft_cid';
const SEEDED_ASSISTANT_PATTERNS = [
  '欢迎体验免登录演示版 RAG',
];

function isSeededAssistantMessage(message: ChatMessage) {
  return (
    message.role === 'assistant'
    && typeof message.content === 'string'
    && SEEDED_ASSISTANT_PATTERNS.some((pattern) => message.content.includes(pattern))
  );
}

function loadDraft(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    const parsed = raw ? (JSON.parse(raw) as ChatMessage[]) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((message) => !isSeededAssistantMessage(message));
  } catch {
    return [];
  }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: loadDraft() as ChatMessage[],
    conversationId: localStorage.getItem(DRAFT_CID_KEY) || '',
    historyId: null as string | null,
    isLoading: false,
    error: null as string | null,
    lastAttemptedMessage: '' as string,
  }),

  getters: {
    hasMessages: (state) => state.messages.length > 0,
    lastMessage: (state) => state.messages[state.messages.length - 1] ?? null,
  },

  actions: {
    addMessage(message: Omit<ChatMessage, 'id'>) {
      const newMessage: ChatMessage = {
        ...message,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        createdAt: message.createdAt || new Date().toISOString(),
      };
      this.messages.push(newMessage);
      this.saveDraft();
    },

    addUserMessage(content: string) {
      this.addMessage({ role: 'user', content });
    },

    addAssistantMessage(content: string, sources?: KnowledgeChunk[], metadata?: Record<string, unknown>, perspectives?: PerspectiveResult[], thinkingProcess?: import('@/types').ThinkingProcess, graphContext?: import('@/types').GraphContext | null) {
      this.addMessage({ role: 'assistant', content, sources, metadata, perspectives, thinkingProcess, graphContext });
    },

    clearMessages() {
      this.saveToHistory();
      this.messages = [];
      this.conversationId = '';
      this.historyId = null;
      this.error = null;
      this.lastAttemptedMessage = '';
      this.clearDraft();
    },

    newConversation() {
      if (this.hasMessages) {
        this.saveToHistory();
      }
      this.messages = [];
      this.conversationId = '';
      this.historyId = null;
      this.error = null;
      this.lastAttemptedMessage = '';
      this.clearDraft();
    },

    clearError() {
      this.error = null;
    },

    saveToHistory() {
      if (this.messages.length === 0) return;
      const historyStore = useHistoryStore();
      this.historyId = historyStore.saveConversation(this.messages, this.historyId || undefined);
    },

    restoreFromHistory(historyId: string) {
      const historyStore = useHistoryStore();
      const item = historyStore.getItem(historyId);
      if (!item) return;

      if (this.hasMessages && this.historyId !== historyId) {
        this.saveToHistory();
      }

      this.messages = [...item.messages];
      this.historyId = historyId;
      this.error = null;
      this.saveDraft();
    },

    async sendChat(message: string) {
      const trimmed = message.trim();
      if (!trimmed) return null;

      this.isLoading = true;
      this.error = null;
      this.lastAttemptedMessage = trimmed;

      try {
        this.addUserMessage(trimmed);

        const data = await httpClient.post<ChatResponse>(
          '/api/chat',
          {
            message: trimmed,
            session_id: this.conversationId || undefined,
            use_rag: true,
            enable_thinking: true,
          } as ChatRequest,
          { timeout: 120000 },
        );

        this.addAssistantMessage(
          data.response || data.message || '',
          data.sources || [],
          data.metadata || {},
          undefined,
          data.thinking_process,
          data.graph_context,
        );

        if (data.session_id) {
          this.conversationId = data.session_id;
          localStorage.setItem(DRAFT_CID_KEY, data.session_id);
        }

        this.saveToHistory();
        return data;
      } catch (error) {
        this.error = error instanceof Error ? error.message : '发送消息失败';
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    async sendPerspectiveChat(message: string) {
      const trimmed = message.trim();
      if (!trimmed) return null;

      this.isLoading = true;
      this.error = null;
      this.lastAttemptedMessage = trimmed;

      try {
        this.addUserMessage(trimmed);

        const data = await httpClient.post<PerspectiveChatResponse>(
          '/api/chat/perspectives',
          {
            message: trimmed,
            session_id: this.conversationId || undefined,
            use_rag: true,
          },
          { timeout: 120000 },
        );

        // 使用第一个有效视角的回答作为主内容
        const firstValid = data.perspectives?.find((p) => p.response);
        const mainContent = firstValid?.response || '';

        this.addAssistantMessage(
          mainContent,
          data.sources || [],
          data.metadata || {},
          data.perspectives || [],
        );

        if (data.session_id) {
          this.conversationId = data.session_id;
          localStorage.setItem(DRAFT_CID_KEY, data.session_id);
        }

        this.saveToHistory();
        return data;
      } catch (error) {
        this.error = error instanceof Error ? error.message : '发送多视角消息失败';
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    saveDraft() {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(this.messages));
      if (this.conversationId) {
        localStorage.setItem(DRAFT_CID_KEY, this.conversationId);
      }
    },

    clearDraft() {
      localStorage.removeItem(DRAFT_KEY);
      localStorage.removeItem(DRAFT_CID_KEY);
    },
  },
});
