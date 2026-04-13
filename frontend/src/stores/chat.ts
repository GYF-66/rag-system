import { defineStore } from 'pinia';
import type {
  ChatMetadata,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  ChatStreamDoneEvent,
  ChatStreamMetadataEvent,
  ChatStreamReflectionEvent,
  KnowledgeChunk,
  PerspectiveChatResponse,
  PerspectiveResult,
  ThinkingProcess,
  ThinkingStepStatusMap,
} from '@/types';
import { useHistoryStore } from './history';
import httpClient from '@/services/httpClient';
import { apiClient } from '@/services/api';

const DRAFT_KEY = 'chat_draft_messages';
const DRAFT_CID_KEY = 'chat_draft_cid';
const SEEDED_ASSISTANT_PATTERNS = ['欢迎体验免登录演示版 RAG'];

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

function buildDraftThinkingProcess(metadata?: ChatMetadata): ThinkingProcess {
  const queryRewrite = metadata?.query_rewrite;
  const retrievalMethod = typeof metadata?.retrieval_method === 'string' ? metadata.retrieval_method : 'hybrid';
  const route = typeof metadata?.adaptive_route === 'string' ? metadata.adaptive_route : 'standard';
  const sourceCount = typeof metadata?.source_count === 'number' ? metadata.source_count : 0;
  const cragEvaluation = metadata?.crag_evaluation ?? undefined;

  return {
    query_analysis: {
      step_id: 1,
      step_name: '问题理解',
      description: '规范化问题、抽取关键词并识别用户意图。',
      reasoning: queryRewrite?.normalized_query || '正在分析问题并准备检索…',
      output_data: {
        variants: queryRewrite?.variants ?? [],
      },
    },
    retrieval: {
      step_id: 2,
      step_name: '证据检索',
      description: '执行多路检索并召回候选证据。',
      reasoning: `已进入 ${route} 路由，检索方式为 ${retrievalMethod}。`,
      output_data: {
        retrieved_count: sourceCount,
      },
    },
    reranking: {
      step_id: 3,
      step_name: '上下文整理',
      description: '对片段进行去重、重排和质量判断。',
      reasoning: typeof cragEvaluation?.quality_score === 'number'
        ? `CRAG 质量分为 ${cragEvaluation.quality_score.toFixed(2)}，正在整理可用证据。`
        : '正在筛选高相关片段并整理上下文…',
      output_data: {
        final_count: sourceCount,
        crag_score: cragEvaluation?.quality_score,
      },
    },
    reasoning: {
      step_id: 4,
      step_name: '回答生成',
      description: '依据证据逐步生成回答。',
      reasoning: '模型正在组织答案…',
      output_data: {},
    },
    summary: '系统已进入流式问答流程，正在持续生成回答与思考过程。',
  };
}

function mergeThinkingProcess(
  current: ThinkingProcess | undefined,
  patch: Partial<ThinkingProcess> | undefined,
): ThinkingProcess | undefined {
  if (!patch) {
    return current;
  }

  return {
    ...current,
    ...patch,
    query_analysis: patch.query_analysis ?? current?.query_analysis,
    retrieval: patch.retrieval ?? current?.retrieval,
    reranking: patch.reranking ?? current?.reranking,
    reasoning: patch.reasoning ?? current?.reasoning,
    reflection: patch.reflection ?? current?.reflection,
    reflection_result: patch.reflection_result ?? current?.reflection_result,
  };
}

function buildInitialThinkingStatuses(): ThinkingStepStatusMap {
  return {
    query_analysis: 'streaming',
    retrieval: 'waiting',
    reranking: 'waiting',
    reasoning: 'waiting',
    reflection: 'waiting',
  };
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

    updateMessage(messageId: string, patch: Partial<ChatMessage>) {
      const index = this.messages.findIndex((message) => message.id === messageId);
      if (index === -1) return;

      this.messages[index] = {
        ...this.messages[index],
        ...patch,
      };
      this.saveDraft();
    },

    setThinkingStepStatus(messageId: string, patch: Partial<ThinkingStepStatusMap>) {
      const message = this.messages.find((item) => item.id === messageId);
      if (!message) return;

      this.updateMessage(messageId, {
        thinkingStatusMap: {
          ...(message.thinkingStatusMap ?? {}),
          ...patch,
        },
      });
    },

    addUserMessage(content: string) {
      this.addMessage({ role: 'user', content });
    },

    addAssistantMessage(
      content: string,
      sources?: KnowledgeChunk[],
      metadata?: ChatMetadata,
      perspectives?: PerspectiveResult[],
      thinkingProcess?: ThinkingProcess,
      graphContext?: import('@/types').GraphContext | null,
    ) {
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

    async sendStreamingChat(message: string) {
      const trimmed = message.trim();
      if (!trimmed) return null;

      this.isLoading = true;
      this.error = null;
      this.lastAttemptedMessage = trimmed;

      let assistantMessageId = '';

      try {
        this.addUserMessage(trimmed);
        this.addMessage({
          role: 'assistant',
          content: '',
          metadata: {},
          sources: [],
          streaming: true,
          streamStatus: 'streaming',
          streamedContent: '',
          thinkingStatusMap: buildInitialThinkingStatuses(),
        });
        assistantMessageId = this.messages[this.messages.length - 1].id;

        const streamState: {
          sessionId: string;
          metadata: ChatMetadata;
          responseText: string;
          sources: KnowledgeChunk[];
          graphContext: ChatMessage['graphContext'];
          thinkingProcess?: ThinkingProcess;
        } = {
          sessionId: this.conversationId || '',
          metadata: {},
          responseText: '',
          sources: [],
          graphContext: null,
        };

        const applyThinkingProcess = (process: ThinkingProcess | undefined) => {
          streamState.thinkingProcess = process;
          this.updateMessage(assistantMessageId, {
            thinkingProcessDraft: process,
            thinkingProcess: process,
          });
        };

        const handleMetadata = async (event: ChatStreamMetadataEvent) => {
          streamState.sessionId = event.session_id || streamState.sessionId;
          streamState.metadata = event.metadata || {};
          streamState.sources = event.sources || [];
          streamState.graphContext = event.graph_context ?? null;
          const draftProcess = buildDraftThinkingProcess(streamState.metadata);
          applyThinkingProcess(mergeThinkingProcess(streamState.thinkingProcess, draftProcess));
          this.updateMessage(assistantMessageId, {
            metadata: streamState.metadata,
            sources: streamState.sources,
            graphContext: streamState.graphContext,
          });
          this.setThinkingStepStatus(assistantMessageId, {
            query_analysis: 'done',
            retrieval: 'done',
            reranking: 'done',
            reasoning: 'streaming',
          });
        };

        const handleToken = async (event: { content?: string }) => {
          if (!event.content) return;

          streamState.responseText += event.content;
          applyThinkingProcess(mergeThinkingProcess(streamState.thinkingProcess, {
            reasoning: {
              ...(streamState.thinkingProcess?.reasoning ?? {
                step_id: 4,
                step_name: '回答生成',
                description: '依据证据逐步生成回答。',
              }),
              reasoning: streamState.responseText,
            },
          }));

          this.updateMessage(assistantMessageId, {
            content: streamState.responseText,
            streamedContent: streamState.responseText,
            streaming: true,
            streamStatus: 'streaming',
          });
          this.setThinkingStepStatus(assistantMessageId, { reasoning: 'streaming' });
        };

        const handleReflection = async (event: ChatStreamReflectionEvent) => {
          streamState.metadata = {
            ...streamState.metadata,
            self_rag_reflection: event.status,
            self_rag: {
              mode: 'llm_reflection',
              status: event.status,
              confidence: event.confidence,
              issues_count: event.issues.length,
              revision_applied: event.revision_applied,
              evidence_count: streamState.metadata.self_rag?.evidence_count ?? Math.min(streamState.sources.length, 5),
            },
          };

          applyThinkingProcess(mergeThinkingProcess(streamState.thinkingProcess, {
            reflection: {
              step_id: 5,
              step_name: 'Self-RAG 校验',
              description: '检查回答与来源证据的一致性，并在必要时修订。',
              reasoning: event.issues.length
                ? `发现 ${event.issues.length} 个需要关注的问题，正在确认答案可信度。`
                : '暂未发现明显证据冲突，正在整理最终校验结果。',
              output_data: {
                status: event.status,
                confidence: event.confidence,
                revision_applied: event.revision_applied,
              },
            },
            reflection_result: event,
          }));

          this.updateMessage(assistantMessageId, {
            metadata: streamState.metadata,
          });
          this.setThinkingStepStatus(assistantMessageId, { reflection: 'streaming' });
        };

        const handleDone = async (event: ChatStreamDoneEvent) => {
          if (event.total_duration_ms != null) {
            streamState.metadata = {
              ...streamState.metadata,
              total_duration_ms: event.total_duration_ms,
            };
          }

          this.updateMessage(assistantMessageId, {
            metadata: streamState.metadata,
            sources: streamState.sources,
            graphContext: streamState.graphContext,
            content: streamState.responseText,
            streamedContent: streamState.responseText,
            streaming: false,
            streamStatus: 'done',
          });
          this.setThinkingStepStatus(assistantMessageId, {
            query_analysis: 'done',
            retrieval: 'done',
            reranking: 'done',
            reasoning: 'done',
            reflection: streamState.thinkingProcess?.reflection ? 'done' : 'waiting',
          });
        };

        await apiClient.streamChat(
          {
            message: trimmed,
            session_id: this.conversationId || undefined,
            use_rag: true,
            enable_thinking: true,
          } as ChatRequest,
          {
            metadata: handleMetadata,
            token: handleToken,
            answer_replace: async ({ content }) => {
              streamState.responseText = content || streamState.responseText;
              this.updateMessage(assistantMessageId, {
                content: streamState.responseText,
                streamedContent: streamState.responseText,
              });
            },
            reflection: handleReflection,
            thinking: async (event: ThinkingProcess) => {
              if (event.reflection_result) {
                streamState.metadata = {
                  ...streamState.metadata,
                  self_rag_reflection: event.reflection_result.status,
                  self_rag: {
                    mode: 'llm_reflection',
                    status: event.reflection_result.status,
                    confidence: event.reflection_result.confidence,
                    issues_count: event.reflection_result.issues.length,
                    revision_applied: event.reflection_result.revision_applied,
                    evidence_count: streamState.metadata.self_rag?.evidence_count ?? Math.min(streamState.sources.length, 5),
                  },
                };
              }

              applyThinkingProcess(event);
              this.setThinkingStepStatus(assistantMessageId, {
                query_analysis: 'done',
                retrieval: 'done',
                reranking: 'done',
                reasoning: 'done',
                reflection: event.reflection ? 'done' : 'waiting',
              });
              this.updateMessage(assistantMessageId, {
                metadata: streamState.metadata,
              });
            },
            done: handleDone,
            error: async ({ message: errorMessage }) => {
              throw new Error(errorMessage || '流式回答失败');
            },
          },
        );

        if (streamState.sessionId) {
          this.conversationId = streamState.sessionId;
          localStorage.setItem(DRAFT_CID_KEY, streamState.sessionId);
        }

        this.saveToHistory();
        return {
          response: streamState.responseText,
          session_id: streamState.sessionId,
          sources: streamState.sources,
          timestamp: new Date().toISOString(),
          metadata: streamState.metadata,
          thinking_process: streamState.thinkingProcess,
          graph_context: streamState.graphContext,
        } as ChatResponse;
      } catch (error) {
        this.error = error instanceof Error ? error.message : '流式发送消息失败';
        if (assistantMessageId) {
          this.updateMessage(assistantMessageId, {
            streaming: false,
            streamStatus: 'error',
          });
          this.setThinkingStepStatus(assistantMessageId, {
            reasoning: 'warning',
            reflection: 'warning',
          });
        }
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

        const firstValid = data.perspectives?.find((item) => item.response);
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

    resetGuestSession() {
      this.messages = [];
      this.conversationId = '';
      this.historyId = null;
      this.isLoading = false;
      this.error = null;
      this.lastAttemptedMessage = '';
      this.clearDraft();
    },
  },
});
