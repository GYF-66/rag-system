import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from './auth';

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

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('初始状态：未登录', () => {
    const store = useAuthStore();
    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
    expect(store.isLoading).toBe(false);
  });

  it('login 成功后设置认证状态', async () => {
    const mockUser = { user_id: 'u1', username: 'test' };
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        access_token: 'at-123',
        refresh_token: 'rt-456',
        token_type: 'bearer',
        user: mockUser,
      }),
    })) as unknown as typeof fetch;

    const store = useAuthStore();
    await store.login('test', 'pass');

    expect(store.isAuthenticated).toBe(true);
    expect(store.user).toEqual(mockUser);
    expect(store.accessToken).toBe('at-123');
    expect(store.refreshToken).toBe('rt-456');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_access_token', 'at-123');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_refresh_token', 'rt-456');
  });

  it('login 失败抛出错误', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      json: async () => ({ detail: '用户名或密码错误' }),
    })) as unknown as typeof fetch;

    const store = useAuthStore();
    await expect(store.login('bad', 'pass')).rejects.toThrow('用户名或密码错误');
    expect(store.isAuthenticated).toBe(false);
    expect(store.isLoading).toBe(false);
  });

  it('register 成功后设置认证状态', async () => {
    const mockUser = { user_id: 'u2', username: 'newuser' };
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        access_token: 'at-new',
        refresh_token: 'rt-new',
        token_type: 'bearer',
        user: mockUser,
      }),
    })) as unknown as typeof fetch;

    const store = useAuthStore();
    await store.register('newuser', 'password', '昵称');

    expect(store.isAuthenticated).toBe(true);
    expect(store.user?.username).toBe('newuser');
  });

  it('logout 清除认证状态', async () => {
    const store = useAuthStore();
    // 先模拟登录状态
    store.setAuth({
      access_token: 'at-1',
      refresh_token: 'rt-1',
      token_type: 'bearer',
      user: { user_id: 'u1', username: 'test' },
    });

    globalThis.fetch = vi.fn(async () => ({ ok: true })) as unknown as typeof fetch;

    await store.logout();

    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
    expect(store.accessToken).toBeNull();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_access_token');
  });

  it('clearAuth 清除所有认证数据', () => {
    const store = useAuthStore();
    store.setAuth({
      access_token: 'at-1',
      refresh_token: 'rt-1',
      token_type: 'bearer',
      user: { user_id: 'u1', username: 'test' },
    });

    store.clearAuth();

    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
    expect(store.accessToken).toBeNull();
    expect(store.refreshToken).toBeNull();
  });

  it('refreshAccessToken 无 refreshToken 时返回 false', async () => {
    const store = useAuthStore();
    const result = await store.refreshAccessToken();
    expect(result).toBe(false);
  });

  it('refreshAccessToken 成功时更新 accessToken', async () => {
    const store = useAuthStore();
    store.refreshToken = 'rt-old';

    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ access_token: 'at-new', token_type: 'bearer' }),
    })) as unknown as typeof fetch;

    const result = await store.refreshAccessToken();
    expect(result).toBe(true);
    expect(store.accessToken).toBe('at-new');
  });

  it('currentUser getter 返回用户', () => {
    const store = useAuthStore();
    expect(store.currentUser).toBeNull();

    store.user = { user_id: 'u1', username: 'test' };
    expect(store.currentUser?.username).toBe('test');
  });
});
