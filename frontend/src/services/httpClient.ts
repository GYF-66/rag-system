/**
 * Lightweight HTTP client with optional auth and token refresh.
 */
import { useAuthStore } from '@/stores/auth';
import type { ApiError } from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (token: string | null) => void;
  reject: (err: unknown) => void;
}> = [];

function onRefreshed(token: string | null) {
  pendingQueue.forEach(({ resolve }) => resolve(token));
  pendingQueue = [];
}

function onRefreshFailed(err: unknown) {
  pendingQueue.forEach(({ reject }) => reject(err));
  pendingQueue = [];
}

export interface HttpOptions extends Omit<RequestInit, 'body'> {
  timeout?: number;
  skipAuth?: boolean;
  json?: unknown;
  retry?: number;
  retryDelay?: number | ((attempt: number) => number);
  shouldRetry?: (error: unknown, attempt: number) => boolean;
}

export class HttpError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: ApiError | Record<string, unknown>,
  ) {
    const message =
      (body as ApiError)?.detail ||
      (body as ApiError)?.message ||
      (body as ApiError)?.error ||
      `HTTP ${status}: ${statusText}`;
    super(message);
    this.name = 'HttpError';
  }
}

function defaultShouldRetry(error: unknown, attempt: number): boolean {
  if (attempt >= 3) return false;
  if (error instanceof HttpError) {
    return error.status >= 500 && error.status < 600;
  }
  if (error instanceof Error) {
    return error.name === 'AbortError' || error.message.includes('网络');
  }
  return false;
}

function defaultRetryDelay(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 30000);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function http<T = unknown>(path: string, options: HttpOptions = {}): Promise<T> {
  const {
    timeout = 15000,
    skipAuth = false,
    json,
    headers: customHeaders,
    retry = 0,
    retryDelay = defaultRetryDelay,
    shouldRetry = defaultShouldRetry,
    ...fetchOptions
  } = options;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retry; attempt += 1) {
    try {
      return await executeRequest<T>(path, {
        timeout,
        skipAuth,
        json,
        headers: customHeaders,
        ...fetchOptions,
      });
    } catch (error) {
      lastError = error;
      if (attempt < retry && shouldRetry(error, attempt)) {
        const delayMs = typeof retryDelay === 'function' ? retryDelay(attempt) : retryDelay;
        await delay(delayMs);
        continue;
      }
      throw error;
    }
  }

  throw lastError;
}

async function executeRequest<T>(
  path: string,
  options: {
    timeout: number;
    skipAuth: boolean;
    json?: unknown;
    headers?: HeadersInit;
    [key: string]: unknown;
  },
): Promise<T> {
  const { timeout, skipAuth, json, headers: customHeaders, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  }

  if (!skipAuth) {
    try {
      const authStore = useAuthStore();
      if (authStore.accessToken) {
        headers.Authorization = `Bearer ${authStore.accessToken}`;
      }
    } catch {
      // ignore store access errors during early boot
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

  try {
    let response = await fetch(url, {
      ...(fetchOptions as RequestInit),
      headers,
      body,
      signal: controller.signal,
    });

    if (response.status === 401 && !skipAuth) {
      response = await handleUnauthorized(url, { ...(fetchOptions as RequestInit), headers, body });
    }

    if (!response.ok) {
      const responseBody = await response.json().catch(() => ({}));
      throw new HttpError(response.status, response.statusText, responseBody);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof HttpError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleUnauthorized(url: string, init: RequestInit): Promise<Response> {
  if (isRefreshing) {
    const token = await new Promise<string | null>((resolve, reject) => {
      pendingQueue.push({ resolve, reject });
    });
    if (!token) throw new HttpError(401, 'Unauthorized', {});
    const headers = new Headers(init.headers);
    headers.set('Authorization', `Bearer ${token}`);
    return fetch(url, { ...init, headers });
  }

  isRefreshing = true;
  try {
    const authStore = useAuthStore();
    const ok = await authStore.refreshAccessToken();
    const newToken = ok ? authStore.accessToken : null;
    isRefreshing = false;

    if (!newToken) {
      onRefreshFailed(new Error('Token 刷新失败'));
      authStore.clearAuth();
      throw new HttpError(401, 'Unauthorized', {});
    }

    onRefreshed(newToken);
    const headers = new Headers(init.headers);
    headers.set('Authorization', `Bearer ${newToken}`);
    return fetch(url, { ...init, headers });
  } catch (err) {
    isRefreshing = false;
    onRefreshFailed(err);
    throw err;
  }
}

export const httpClient = {
  get: <T = unknown>(path: string, opts?: HttpOptions) => http<T>(path, { ...opts, method: 'GET' }),
  post: <T = unknown>(path: string, body?: unknown, opts?: HttpOptions) =>
    http<T>(path, { ...opts, method: 'POST', json: body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: HttpOptions) =>
    http<T>(path, { ...opts, method: 'PUT', json: body }),
  delete: <T = unknown>(path: string, opts?: HttpOptions) => http<T>(path, { ...opts, method: 'DELETE' }),
};

export default httpClient;
