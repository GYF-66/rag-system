import httpClient from '@/services/httpClient';
import type {
  AlignmentAnalysis,
  ChatRequest,
  ChatResponse,
  ChatStreamEventMap,
  GraphSearchResult,
  GraphVisualizationData,
  Space,
  SpaceListResponse,
} from '@/types';

interface HealthResponse {
  status: string;
  agent_name: string;
  knowledge_base_loaded: boolean;
  total_chunks: number;
  timestamp: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

type SpaceApiPayload = {
  id: string;
  name: string;
  description?: string;
  icon: string;
  color: string;
  itemCount?: number;
  item_count?: number;
  updatedAt?: string;
  updated_at?: string;
};

function normalizeSpace(space: SpaceApiPayload): Space {
  return {
    id: space.id,
    name: space.name,
    description: space.description,
    icon: space.icon,
    color: space.color,
    itemCount: space.itemCount ?? space.item_count ?? 0,
    updatedAt: space.updatedAt ?? space.updated_at ?? new Date().toISOString(),
  };
}

function normalizeSpaceList(response: { spaces?: SpaceApiPayload[]; total?: number }): SpaceListResponse {
  const spaces = Array.isArray(response.spaces) ? response.spaces.map(normalizeSpace) : [];
  return {
    spaces,
    total: response.total ?? spaces.length,
  };
}

let currentSessionId = '';

function resolveApiUrl(path: string) {
  return path.startsWith('http') ? path : `${API_BASE}${path}`;
}

async function parseSseStream<TEvent extends keyof ChatStreamEventMap>(
  response: Response,
  handlers: Partial<{ [K in TEvent]: (payload: ChatStreamEventMap[K]) => void | Promise<void> }>,
) {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('流式响应不可用');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  const flushEvent = async (chunk: string) => {
    const lines = chunk.split('\n');
    let eventName = 'message';
    const dataLines: string[] = [];

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (!dataLines.length) return;

    const payload = JSON.parse(dataLines.join('\n')) as ChatStreamEventMap[TEvent];
    const handler = handlers[eventName as TEvent];
    if (handler) {
      await handler(payload);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = buffer.replace(/\r\n/g, '\n');

    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const eventChunk = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (eventChunk) {
        await flushEvent(eventChunk);
      }
      boundary = buffer.indexOf('\n\n');
    }

    if (done) {
      const trailing = buffer.trim();
      if (trailing) {
        await flushEvent(trailing);
      }
      break;
    }
  }
}

export const apiClient = {
  setSession(sessionId?: string | null) {
    currentSessionId = sessionId?.trim() ?? '';
  },

  async chat(message: string): Promise<ChatResponse> {
    return httpClient.post<ChatResponse>(
      '/api/chat',
      {
        message,
        session_id: currentSessionId || undefined,
        use_rag: true,
        enable_thinking: true,
      },
      { timeout: 120000 },
    );
  },

  async streamChat(
    payload: ChatRequest,
    handlers: Partial<{ [K in keyof ChatStreamEventMap]: (data: ChatStreamEventMap[K]) => void | Promise<void> }>,
  ): Promise<void> {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 120000);
    const headers = new Headers({
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    });

    const accessToken = localStorage.getItem('auth_access_token');
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }

    try {
      const response = await fetch(resolveApiUrl('/api/chat/stream'), {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const requestId = response.headers.get('x-request-id') || '';

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const message = (body as { detail?: string; message?: string }).detail
          || (body as { detail?: string; message?: string }).message
          || `HTTP ${response.status}`;
        throw new Error(requestId ? `${message}（请求 ID: ${requestId}）` : message);
      }

      await parseSseStream(response, handlers);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('流式请求超时，请稍后重试');
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },

  async healthCheck(): Promise<HealthResponse> {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch(resolveApiUrl('/health'), {
        method: 'GET',
        headers: {
          Accept: 'application/json, text/plain;q=0.9, */*;q=0.8',
        },
        signal: controller.signal,
      });
      const requestId = response.headers.get('x-request-id') || '';

      if (!response.ok) {
        const baseMessage = `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(requestId ? `${baseMessage}（请求 ID: ${requestId}）` : baseMessage);
      }

      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        return (await response.json()) as HealthResponse;
      }

      const statusText = (await response.text()).trim() || 'healthy';
      return {
        status: statusText,
        agent_name: 'frontend-proxy',
        knowledge_base_loaded: true,
        total_chunks: 0,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('健康检查超时');
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },

  async getSpaces(): Promise<SpaceListResponse> {
    const response = await httpClient.get<{ spaces: SpaceApiPayload[]; total: number }>('/api/v1/spaces');
    return normalizeSpaceList(response);
  },

  async getSpaceById(spaceId: string): Promise<Space> {
    const response = await httpClient.get<SpaceApiPayload>(`/api/v1/spaces/${spaceId}`);
    return normalizeSpace(response);
  },

  async getGraphVisualization(nodeType?: string): Promise<GraphVisualizationData> {
    const query = nodeType ? `?node_type=${encodeURIComponent(nodeType)}` : '';
    return httpClient.get<GraphVisualizationData>(`/api/graph/visualization${query}`);
  },

  async searchGraph(query: string, maxHops = 2, maxNodes = 30): Promise<GraphSearchResult> {
    return httpClient.post<GraphSearchResult>('/api/graph/search', {
      query,
      max_hops: maxHops,
      max_nodes: maxNodes,
    });
  },

  async getAlignmentAnalysis(): Promise<AlignmentAnalysis> {
    return httpClient.get<AlignmentAnalysis>('/api/graph/alignment');
  },
};

export type { Space };

export default apiClient;
