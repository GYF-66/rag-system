import type { App } from 'vue';
import router from '@/router';

/**
 * 统一应用错误类
 */
export class AppError extends Error {
  code: string;
  retryable: boolean;

  constructor(message: string, code: string = 'UNKNOWN', retryable: boolean = false) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.retryable = retryable;
  }
}

/**
 * 注册全局错误处理器
 */
export function setupGlobalErrorHandler(app: App) {
  // Vue 组件内错误
  app.config.errorHandler = (err, _instance, info) => {
    console.error(`[Vue Error] ${info}:`, err);
    if (err instanceof AppError) {
      handleApiError(err);
    }
  };

  // 未捕获的 Promise 异常
  window.addEventListener('unhandledrejection', (event) => {
    console.error('[Unhandled Rejection]:', event.reason);
    if (event.reason instanceof AppError) {
      handleApiError(event.reason);
    }
    event.preventDefault();
  });
}

/**
 * 统一处理 API 错误
 */
export function handleApiError(error: unknown): string {
  if (error instanceof AppError) {
    switch (error.code) {
      case 'UNAUTHORIZED':
        router.push('/login');
        return '登录已过期，请重新登录';
      case 'FORBIDDEN':
        return '您没有权限执行此操作';
      case 'NETWORK_ERROR':
        return '网络连接异常，请检查网络后重试';
      case 'TIMEOUT':
        return '请求超时，请稍后重试';
      default:
        return error.message || '发生未知错误';
    }
  }

  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return '网络连接异常，请检查网络后重试';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return '发生未知错误';
}
